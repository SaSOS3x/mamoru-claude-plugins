#!/usr/bin/env python3
"""Look at rows to check a classification by eye (step 2b: always read the biggest cluster and every "unclassified-strong").

Usage:
  python show.py --dir OUT_DIR --cat "unclassified"            # rows of final.json whose cluster name contains the text
  python show.py --dir OUT_DIR --cat "wrong path" --n 10 --width 300
  python show.py --dir OUT_DIR --mode strong                   # rows.json: is_error or exit != 0
  python show.py --dir OUT_DIR --mode weak                     # rows.json: pattern hit only (look for soft failures)
  python show.py --dir OUT_DIR --kind real --src agent-a1b2    # only real failures of one agent (id prefix)
  python show.py --dir OUT_DIR --cat "path" --part head        # the start of the output instead of the error part
Output line: index|source|time|tool|E(is_error)X(exit!=0)|cluster or hits|command ==> output
The output shown is the ERROR part: when the text is longer than --width, the lines around the LAST error marker
(Traceback, ...Error, No such file, not found, denied, Exit code N ...) are shown, with "..." where text is cut. So a
command that printed a file and then failed shows the failure, not the file. --part head shows the start (old behaviour).
Wrong input (missing folder, no rows.json, --cat without final.json) prints "ERROR: ..." and exits with code 2.
A Git Bash path /c/x is accepted on Windows (turned into C:/x).
"""
import argparse
import collections
import json
import os
import re
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# a line of an output that is (part of) the error itself
ERR_LINE = re.compile(r"Traceback \(most recent|[A-Za-z]*Error\b|Exception\b|No such file|not found|cannot |can't |"
                      r"denied|unexpected EOF|command not found|^\s*Exit code [1-9]|FATAL|failed|FAIL ", re.I)


def die(msg):
    print("ERROR: " + msg, file=sys.stderr)
    sys.exit(2)


def norm_path(p):
    """Git Bash form /c/x (or /cygdrive/c/x) -> C:/x. Only on Windows: a native python cannot open /c/x there."""
    if p and os.name == "nt":
        m = re.match(r"^(?:/cygdrive)?/([A-Za-z])(?:/(.*))?$", p)
        if m:
            return m.group(1).upper() + ":/" + (m.group(2) or "")
    return p


def load_rows(path, what):
    if not path.is_file():
        die("%s not found: %s (run scan_fail.py%s first)" % (path.name, path, " and classify.py" if what == "final" else ""))
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as e:
        die("%s is not valid JSON: %s (%s)" % (path.name, path, e))
    need = {"src", "ts", "tool", "cmd", "err", "iserr", "nonzero", "hits"}
    if not isinstance(rows, list) or not all(isinstance(r, dict) and need <= r.keys() for r in rows):
        die("%s does not look like a result of scan_fail.py / classify.py (a list of rows with %s)" % (path, sorted(need)))
    return rows


def error_part(text, width):
    """The part of an output worth reading: all of it if short, else the lines around the last error marker."""
    lines = text.split("\n")
    if len(" | ".join(lines)) <= width:
        return " | ".join(lines)
    idx = [i for i, ln in enumerate(lines) if ERR_LINE.search(ln)]
    if not idx:  # no marker: the end of the output is the best guess
        return "... " + " | ".join(lines)[-(width - 4):]
    last = idx[-1]
    start = max(last - 1, 0)  # one line of context before the last marker
    for i in range(last, -1, -1):  # a traceback is shown from its own "Traceback" line
        if lines[i].startswith("Traceback (most recent"):
            start = i
            break
    end = min(last + 2, len(lines))  # the marker line and one line after it
    part = " | ".join(lines[start:end])
    lead = "... " if start > 0 else ""
    tail = " ..." if end < len(lines) else ""
    if len(lead + part + tail) <= width:
        return lead + part + tail
    return "... " + part[-(width - 4 - len(tail)):] + tail  # too long: keep the end, it holds the marker line


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", required=True)
    ap.add_argument("--mode", choices=["strong", "weak"])
    ap.add_argument("--cat", help="substring of the cluster name (needs final.json)")
    ap.add_argument("--kind", choices=["real", "expected", "noise"])
    ap.add_argument("--src", help="source prefix: main or agent-xxxx")
    ap.add_argument("--n", type=int, default=0, help="show at most N rows (0 = all)")
    ap.add_argument("--width", type=int, default=200, help="characters of output per row")
    ap.add_argument("--part", choices=["error", "head"], default="error",
                    help="error (default): the lines around the last error marker; head: the start of the output")
    a = ap.parse_args()
    d = Path(norm_path(a.dir))
    if not d.is_dir():
        die("--dir is not a folder: %s" % d)
    if a.width < 20:
        die("--width must be at least 20")
    if a.mode or not (d / "final.json").exists():
        if (a.cat or a.kind) and not a.mode:
            die("--cat / --kind need final.json: run classify.py on %s first" % d)
        rows = load_rows(d / "rows.json", "rows")
        if a.mode == "weak":
            rows = [r for r in rows if not (r["iserr"] or r["nonzero"])]
            print(collections.Counter(r["tool"] for r in rows))
            rows = [r for r in rows if r["tool"] in ("Bash", "PowerShell") or r["tlen"] < 400]
        else:
            rows = [r for r in rows if r["iserr"] or r["nonzero"]]
    else:
        rows = load_rows(d / "final.json", "final")
        if a.cat:
            rows = [r for r in rows if a.cat.lower() in r["cat"].lower()]
        if a.kind:
            pref = {"noise": "NOISE", "expected": "EXPECTED"}
            rows = [r for r in rows if (r["cat"].startswith(pref[a.kind]) if a.kind in pref
                                        else not r["cat"].startswith(("NOISE", "EXPECTED")))]
    if a.src:
        rows = [r for r in rows if r["src"].startswith(a.src)]
    print(len(rows), "rows")
    for i, r in enumerate(rows[:a.n] if a.n else rows):
        e = r["err"].replace("\n", " | ")[:a.width] if a.part == "head" else error_part(r["err"], a.width)
        c = r["cmd"].replace("\n", " ")[:150]
        flag = ("E" if r["iserr"] else "") + ("X" if r["nonzero"] else "")
        info = r.get("cat") or r["hits"]
        print("%d|%s|%s|%s|%s|%s|%s  ==> %s" % (i, r["src"][:14], r["ts"][5:16], r["tool"], flag, info, c, e))


if __name__ == "__main__":
    main()
