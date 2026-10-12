#!/usr/bin/env python3
"""
crlf_edit.py - edit Windows batch/PowerShell files without wrecking their bytes.

The single most common way to corrupt one of these scripts is to open it in a
tool that "helpfully" rewrites CRLF to LF, adds a BOM, or normalises trailing
whitespace. cmd is sensitive to all three. This module edits by exact
string-replacement while preserving the original line endings, encoding, and
BOM state, and it refuses to apply a replacement that doesn't match exactly
once (so an edit can never silently no-op or hit the wrong place).

Use as a library from a one-off Python edit script:

    from crlf_edit import read, write, replace_exact
    text, meta = read("PerfTweaks.cmd")
    text = replace_exact(text, OLD_BLOCK, NEW_BLOCK)        # expects exactly 1 match
    write("PerfTweaks.cmd", text, meta)

Or from the command line for a single replacement:

    python crlf_edit.py report FILE
    python crlf_edit.py replace FILE --old-file old.txt --new-file new.txt
    python crlf_edit.py replace FILE --old "goto :men" --new "goto :menu"

`read` returns the text with line endings intact (it reads with newline="" so
\\r\\n stays literal), plus a Meta describing how to write it back byte-faithfully.
"""

import argparse
import sys
from pathlib import Path

BOM = "\ufeff"


class Meta:
    def __init__(self, newline, encoding, had_bom):
        self.newline = newline      # dominant line ending: "\r\n" or "\n"
        self.encoding = encoding    # e.g. "ascii", "utf-8"
        self.had_bom = had_bom


def _detect_encoding(raw):
    """Prefer the tightest encoding that round-trips: ascii, else utf-8."""
    body = raw[3:] if raw.startswith(b"\xef\xbb\xbf") else raw
    try:
        body.decode("ascii")
        return "ascii"
    except UnicodeDecodeError:
        return "utf-8"


def read(path):
    """Return (text, meta). Line endings are preserved in `text`."""
    raw = Path(path).read_bytes()
    had_bom = raw.startswith(b"\xef\xbb\xbf")
    encoding = _detect_encoding(raw)
    crlf = raw.count(b"\r\n")
    lone_lf = raw.count(b"\n") - crlf
    newline = "\r\n" if crlf >= lone_lf and crlf > 0 else "\n"
    # newline="" keeps \r\n literal in the string so replacements see real bytes.
    text = raw.decode("utf-8-sig" if had_bom else encoding, errors="strict") \
        if encoding != "ascii" or had_bom else raw.decode("ascii")
    return text, Meta(newline, encoding, had_bom)


def write(path, text, meta):
    """Write `text` back with the recorded encoding/BOM, preserving whatever
    line endings are already in the string. We pass newline="" so Python does
    not translate; the caller's text already contains the intended endings."""
    enc = meta.encoding
    data = text
    if meta.had_bom and not data.startswith(BOM):
        data = BOM + data
    with open(path, "w", encoding=enc if enc != "ascii" else "ascii",
              newline="") as fh:
        fh.write(data)


def replace_exact(text, old, new, expect=1):
    """Replace `old` with `new`, asserting it occurs exactly `expect` times.
    Raises ValueError on any mismatch - the whole point is to fail loudly rather
    than corrupt or no-op."""
    n = text.count(old)
    if n != expect:
        raise ValueError(
            f"expected {expect} occurrence(s) of the target string, found {n}. "
            f"Refusing to edit. Widen or narrow the anchor so it is unique.")
    return text.replace(old, new, expect)


def eol_report(path):
    raw = Path(path).read_bytes()
    crlf = raw.count(b"\r\n")
    lone_lf = raw.count(b"\n") - crlf
    lone_cr = raw.count(b"\r") - crlf
    had_bom = raw.startswith(b"\xef\xbb\xbf")
    enc = _detect_encoding(raw)
    nonascii = sum(1 for b in (raw[3:] if had_bom else raw) if b > 127)
    return {
        "path": str(path),
        "bytes": len(raw),
        "crlf": crlf,
        "lone_lf": lone_lf,
        "lone_cr": lone_cr,
        "bom": had_bom,
        "encoding": enc,
        "non_ascii_bytes": nonascii,
        "ends_with_newline": raw.endswith(b"\n"),
        "uniform_crlf": crlf > 0 and lone_lf == 0 and lone_cr == 0,
    }


def _cmd_report(args):
    r = eol_report(args.file)
    width = max(len(k) for k in r)
    for k, v in r.items():
        print(f"  {k:<{width}} : {v}")
    ok = r["uniform_crlf"] and not r["bom"]
    print(f"\n  -> {'OK: uniform CRLF, no BOM' if ok else 'CHECK the flags above'}")
    return 0 if ok else 1


def _cmd_replace(args):
    old = Path(args.old_file).read_text(encoding="utf-8") if args.old_file else args.old
    new = Path(args.new_file).read_text(encoding="utf-8") if args.new_file else args.new
    if old is None or new is None:
        print("error: provide --old/--new or --old-file/--new-file", file=sys.stderr)
        return 2
    before = eol_report(args.file)
    text, meta = read(args.file)
    try:
        text = replace_exact(text, old, new, expect=args.expect)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    write(args.file, text, meta)
    after = eol_report(args.file)
    print(f"replaced {args.expect} occurrence(s).")
    if before["crlf"] and after["lone_lf"] != before["lone_lf"]:
        print("WARNING: lone-LF count changed - line endings may have shifted.",
              file=sys.stderr)
    print(f"  CRLF {before['crlf']} -> {after['crlf']}, "
          f"encoding {after['encoding']}, bom {after['bom']}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    rp = sub.add_parser("report", help="print EOL/encoding/BOM report")
    rp.add_argument("file")
    rp.set_defaults(func=_cmd_report)

    ep = sub.add_parser("replace", help="single exact-match replacement")
    ep.add_argument("file")
    ep.add_argument("--old", default=None)
    ep.add_argument("--new", default=None)
    ep.add_argument("--old-file", default=None)
    ep.add_argument("--new-file", default=None)
    ep.add_argument("--expect", type=int, default=1,
                    help="number of matches required (default 1)")
    ep.set_defaults(func=_cmd_replace)

    args = ap.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
