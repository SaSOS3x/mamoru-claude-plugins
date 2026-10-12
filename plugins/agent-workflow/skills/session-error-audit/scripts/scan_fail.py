#!/usr/bin/env python3
"""Step 1 of session-error-audit: collect every suspicious tool call from Claude Code transcripts.

A transcript is a JSON-lines file: ~/.claude/projects/<project>/<session>.jsonl (main session) and
~/.claude/projects/<project>/<session>/subagents/**/agent-*.jsonl (subagents, workflow agents).
Each tool_use is paired with its tool_result. A result is recorded as a row when
  - is_error is true, or
  - the text starts with "Exit code N" and N != 0 (hard failure), or
  - the text contains one of the PATTERNS (weak hit; many are noise, classify.py separates them).

Usage (Windows and Linux alike, forward slashes are fine):
  python scan_fail.py --project "C:/path/to/project"  --out OUT_DIR
  python scan_fail.py --dir "~/.claude/projects/<mangled name>" --out OUT_DIR [--session SID] [--since ISO] [--until ISO]

--project  working folder of the project; the transcript folder is derived from it the way Claude Code does it
           (every character except letters and digits becomes "-"), under CLAUDE_CONFIG_DIR or ~/.claude.
--dir      the transcript folder itself (use it when --project does not find the folder).
--session  only this session id (default: every session in the folder).
--since / --until  ISO timestamps (UTC, e.g. 2026-10-12T00:00:00Z); calls outside are skipped. Use --until to
           repeat an old audit on the same slice of history.
Writes OUT_DIR/rows.json and OUT_DIR/scan_meta.json. Needs only the standard library.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):  # cp1251 consoles on Windows must not break the output
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PATTERNS = ["Traceback", "SyntaxError", "unexpected EOF", "UnicodeEncodeError", "UnicodeDecodeError",
            "No such file", "command not found", "cannot access", "not found", "Permission denied", "denied",
            "timed out", "InputValidationError", "File has not been read", "changed on disk",
            "String to replace not found", "CRLF"]
EXIT_RE = re.compile(r"^\s*Exit code (-?\d+)")


def mangle(path):
    """Claude Code folder name for a project path: C:\\a\\.b -> C--a--b."""
    return re.sub(r"[^A-Za-z0-9]", "-", str(path))


def find_transcript_dir(project, directory):
    if directory:
        return Path(os.path.expanduser(directory))
    base = Path(os.environ.get("CLAUDE_CONFIG_DIR") or (Path.home() / ".claude")) / "projects"
    p = os.path.abspath(os.path.expanduser(project))
    cand = base / mangle(p)
    if cand.is_dir():
        return cand
    # fallback: case-insensitive match (Windows drive letters) or forward-slash variants
    want = mangle(p).lower()
    if base.is_dir():
        for d in base.iterdir():
            if d.is_dir() and d.name.lower() == want:
                return d
    raise SystemExit("transcript folder not found: %s (try --dir)" % cand)


def text_of(c):
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return "\n".join(x.get("text", "") if isinstance(x, dict) else str(x) for x in c)
    return str(c)


def collect_files(tdir, session):
    files = []
    mains = sorted(tdir.glob("*.jsonl"))
    for m in mains:
        sid = m.stem
        if session and sid != session:
            continue
        files.append(("main:" + sid[:8], m))
        sub = tdir / sid / "subagents"
        if sub.is_dir():
            for p in sorted(sub.rglob("agent-*.jsonl")):
                files.append((p.stem, p))
    if session:  # session folder may exist without its main file
        sub = tdir / session / "subagents"
        if sub.is_dir() and not any(s == "main:" + session[:8] for s, _ in files):
            for p in sorted(sub.rglob("agent-*.jsonl")):
                files.append((p.stem, p))
    return files


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project")
    ap.add_argument("--dir")
    ap.add_argument("--session")
    ap.add_argument("--since", default="")
    ap.add_argument("--until", default="")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    if not a.project and not a.dir:
        ap.error("give --project or --dir")
    tdir = find_transcript_dir(a.project, a.dir)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    files = collect_files(tdir, a.session)
    if not files:
        raise SystemExit("no *.jsonl found under %s" % tdir)

    rows, total_calls, first_ts, last_ts = [], 0, "", ""
    for src, p in files:
        uses = {}
        with open(p, encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                msg = d.get("message")
                if not isinstance(msg, dict) or not isinstance(msg.get("content"), list):
                    continue
                ts = d.get("timestamp", "")
                if (a.since and ts and ts < a.since) or (a.until and ts and ts > a.until):
                    continue
                if ts:
                    first_ts = ts if not first_ts or ts < first_ts else first_ts
                    last_ts = ts if ts > last_ts else last_ts
                for c in msg["content"]:
                    if not isinstance(c, dict):
                        continue
                    if c.get("type") == "tool_use":
                        uses[c.get("id")] = (c.get("name"), c.get("input") or {})
                        total_calls += 1
                    elif c.get("type") == "tool_result":
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
                since=a.since, until=a.until, session=a.session or "")
    (out / "scan_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print("files %d calls %d rows %d strong %d weak-only %d  (%s .. %s)" % (
        len(files), total_calls, len(rows), strong, len(rows) - strong, first_ts[:16], last_ts[:16]))


if __name__ == "__main__":
    main()
