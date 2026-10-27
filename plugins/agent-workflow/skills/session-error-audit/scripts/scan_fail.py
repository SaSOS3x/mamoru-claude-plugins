#!/usr/bin/env python3
"""Step 1 of session-error-audit: collect every suspicious tool call from Claude Code transcripts.

A transcript is a JSON-lines file: ~/.claude/projects/<project>/<session>.jsonl (main session) and
~/.claude/projects/<project>/<session>/subagents/**/agent-*.jsonl (subagents, workflow agents).
Each tool_use is paired with its tool_result. A result is recorded as a row when
  - is_error is true, or
  - the text starts with "Exit code N" and N != 0 (hard failure), or
  - the text contains one of the PATTERNS (weak hit; many are noise, classify.py separates them).
Only "assistant" / "user" records are read and every call and result is counted once by its id: since Claude Code
2.1.304 (2026-10-21) a transcript also holds "api-request-blob" records without a timestamp that repeat earlier calls,
and a block of old records can be written a second time.

Usage (Windows and Linux alike, forward slashes are fine):
  python scan_fail.py --project "C:/path/to/project"  --out OUT_DIR
  python scan_fail.py --dir "~/.claude/projects/<mangled name>" --out OUT_DIR [--session SID] [--since TIME] [--until TIME]

--project  working folder of the project; the transcript folder is derived from it the way Claude Code does it
           (every character except letters and digits becomes "-"), under CLAUDE_CONFIG_DIR or ~/.claude.
--dir      the transcript folder itself (use it when --project does not find the folder).
--session  only this session id (default: every session in the folder).
--since / --until  UTC time; calls outside are skipped. Accepted forms: 2026-10-12 (= 00:00:00 of that day),
           2026-10-12T23:11, 2026-10-12T23:11:00, 2026-10-12T23:11:00.5, each with an optional Z or +00:00 / +03:00
           ending (no ending = UTC). The times are parsed, not compared as text. Use --until to repeat an old audit
           on the same slice of history. A value that is not a time stops the script (exit 2).
A session folder whose main *.jsonl was deleted (only <id>/subagents is left) is scanned too, as its own session.
Windows: a Git Bash path like /c/Users/x is turned into C:/Users/x, so it also works from PowerShell.
Wrong input (missing folder, bad time) prints "ERROR: ..." and exits with code 2. A scan that finds 0 tool calls
prints a WARNING (it is not "no failures": check the period, --session and --dir).
Writes OUT_DIR/rows.json and OUT_DIR/scan_meta.json. Needs only the standard library.
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

for _s in (sys.stdout, sys.stderr):  # cp1251 consoles on Windows must not break the output
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PATTERNS = ["Traceback", "SyntaxError", "unexpected EOF", "UnicodeEncodeError", "UnicodeDecodeError",
            "No such file", "command not found", "cannot access", "not found", "Permission denied", "denied",
            "timed out", "InputValidationError", "File has not been read", "changed on disk",
            "String to replace not found", "CRLF", "delimited by end-of-file",
            "Exception in thread", "Caused by: "]  # Java: a program whose exit code was lost (| tail, ;)
EXIT_RE = re.compile(r"^\s*Exit code (-?\d+)")
TS_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2})(?:[.,](\d{1,9}))?)?)?\s*"
                   r"(Z|[+-]\d{2}(?::?\d{2})?)?$", re.I)
TS_HELP = "use 2026-10-12, 2026-10-12T23:11Z, 2026-10-12T23:11:00Z or 2026-10-12T23:11:00+00:00 (UTC)"


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


def parse_ts(s):
    """Time text -> timezone-aware datetime in UTC, or None when it is not a time."""
    m = TS_RE.match((s or "").strip())
    if not m:
        return None
    y, mo, d, h, mi, sec, frac, tz = m.groups()
    try:
        dt = datetime(int(y), int(mo), int(d), int(h or 0), int(mi or 0), int(sec or 0),
                      int((frac or "0")[:6].ljust(6, "0")), tzinfo=timezone.utc)
        if tz and tz.upper() != "Z":
            digits = tz[1:].replace(":", "")
            off = timedelta(hours=int(digits[:2]), minutes=int(digits[2:4] or 0))
            dt = dt - off if tz[0] == "+" else dt + off
    except (ValueError, OverflowError):
        return None
    return dt


def ts_arg(s):
    if s == "":
        return None
    dt = parse_ts(s)
    if dt is None:
        raise argparse.ArgumentTypeError("%r is not a time (%s)" % (s, TS_HELP))
    return dt


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ") if dt else ""


def mangle(path):
    """Claude Code folder name for a project path: C:\\a\\.b -> C--a--b."""
    return re.sub(r"[^A-Za-z0-9]", "-", str(path))


def find_transcript_dir(project, directory):
    if directory:
        tdir = Path(os.path.expanduser(norm_path(directory)))
        if not tdir.is_dir():
            die("transcript folder not found or not a folder: %s" % tdir)
        return tdir
    base = Path(os.environ.get("CLAUDE_CONFIG_DIR") or (Path.home() / ".claude")) / "projects"
    p = os.path.abspath(os.path.expanduser(norm_path(project)))
    cand = base / mangle(p)
    if cand.is_dir():
        return cand
    # fallback: case-insensitive match (Windows drive letters) or forward-slash variants
    want = mangle(p).lower()
    if base.is_dir():
        for d in base.iterdir():
            if d.is_dir() and d.name.lower() == want:
                return d
    die("transcript folder not found: %s (check --project or give --dir)" % cand)


def text_of(c):
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return "\n".join(x.get("text", "") if isinstance(x, dict) else str(x) for x in c)
    return str(c)


def collect_files(tdir, session):
    """-> (files, orphans). orphans = session ids that have <id>/subagents but no <id>.jsonl (still scanned)."""
    mains = {m.stem: m for m in tdir.glob("*.jsonl")}
    sids, orphans = set(mains), []
    for d in tdir.iterdir():
        if d.is_dir() and d.name not in mains and (d / "subagents").is_dir():
            sids.add(d.name)
            orphans.append(d.name)
    files = []
    for sid in sorted(sids):
        if session and sid != session:
            continue
        if sid in mains:
            files.append(("main:" + sid[:8], mains[sid]))
        sub = tdir / sid / "subagents"
        if sub.is_dir():
            for p in sorted(sub.rglob("agent-*.jsonl")):
                files.append((p.stem, p))
    return files, sorted(o for o in orphans if not session or o == session)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project")
    ap.add_argument("--dir")
    ap.add_argument("--session")
    ap.add_argument("--since", type=ts_arg, default=None, metavar="TIME")
    ap.add_argument("--until", type=ts_arg, default=None, metavar="TIME")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    if not a.project and not a.dir:
        ap.error("give --project or --dir")
    if a.since and a.until and a.since > a.until:
        die("--since %s is later than --until %s: the period is empty" % (iso(a.since), iso(a.until)))
    tdir = find_transcript_dir(a.project, a.dir)
    out = Path(norm_path(a.out))
    files, orphans = collect_files(tdir, a.session)
    if not files:
        die("no *.jsonl found under %s%s" % (tdir, " for session %s" % a.session if a.session else ""))
    out.mkdir(parents=True, exist_ok=True)
    if orphans:
        print("note: %d session folder(s) have subagents but no main .jsonl (scanned as their own session): %s" % (
            len(orphans), ", ".join(o[:8] for o in orphans)))

    rows, total_calls, first_ts, last_ts = [], 0, "", ""
    for src, p in files:
        uses = {}
        seen_res = set()
        with open(p, encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if d.get("type") not in ("assistant", "user"):
                    continue  # api-request-blob repeats earlier blocks and has no timestamp
                msg = d.get("message")
                if not isinstance(msg, dict) or not isinstance(msg.get("content"), list):
                    continue
                ts = d.get("timestamp", "")
                if (a.since or a.until) and ts:
                    tsd = parse_ts(ts)
                    if tsd and ((a.since and tsd < a.since) or (a.until and tsd > a.until)):
                        continue
                if ts:
                    first_ts = ts if not first_ts or ts < first_ts else first_ts
                    last_ts = ts if ts > last_ts else last_ts
                for c in msg["content"]:
                    if not isinstance(c, dict):
                        continue
                    if c.get("type") == "tool_use":
                        if c.get("id") in uses:
                            continue  # the same call written twice (a block of old records written again)
                        uses[c.get("id")] = (c.get("name"), c.get("input") or {})
                        total_calls += 1
                    elif c.get("type") == "tool_result":
                        if c.get("tool_use_id") in seen_res:
                            continue
                        seen_res.add(c.get("tool_use_id"))
                        t = text_of(c.get("content"))
                        iserr = bool(c.get("is_error"))
                        m = EXIT_RE.match(t)
                        nonzero = bool(m and m.group(1) != "0")
                        hits = [x for x in PATTERNS if x in t]
                        if not (iserr or nonzero or hits):
                            continue
                        name, inp = uses.get(c.get("tool_use_id"), ("?", {}))
                        cmd = inp.get("command") or inp.get("file_path") or inp.get("pattern") \
                            or json.dumps(inp, ensure_ascii=False)
                        rows.append(dict(src=src, ts=ts, tool=name, cmd=str(cmd)[:3000],
                                         err=(t if len(t) < 12000 else t[:5000] + " ... " + t[-3000:]),
                                         tail=t[-600:], iserr=iserr, nonzero=nonzero, hits=hits, tlen=len(t)))
    (out / "rows.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    strong = sum(1 for r in rows if r["iserr"] or r["nonzero"])
    meta = dict(transcript_dir=str(tdir).replace("\\", "/"), files=len(files), tool_calls=total_calls, rows=len(rows),
                strong=strong, weak_only=len(rows) - strong, first_ts=first_ts, last_ts=last_ts,
                since=iso(a.since), until=iso(a.until), session=a.session or "", orphan_sessions=len(orphans))
    (out / "scan_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print("files %d calls %d rows %d strong %d weak-only %d  (%s .. %s)" % (
        len(files), total_calls, len(rows), strong, len(rows) - strong, first_ts[:16], last_ts[:16]))
    if total_calls == 0:
        print("WARNING: 0 tool calls found in %d file(s) - this is NOT 'no failures'. Check --since/--until "
              "(%s .. %s), --session and --dir (%s)." % (len(files), iso(a.since) or "start", iso(a.until) or "end", tdir))


if __name__ == "__main__":
    main()
