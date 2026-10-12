#!/usr/bin/env python3
"""Step 2 of session-error-audit: sort the rows of scan_fail.py into noise / expected / real failures and cluster them.

Classes (the prefix of the cluster name):
  NOISE ...     a weak pattern ("not found", "denied", "CRLF" ...) inside a successful output, or Read content: not a failure.
  EXPECTED ...  a nonzero exit that is a normal answer (grep / ls / diff / unzip probe, an offline check that caught a real mismatch).
  anything else a real failure. "hard" = is_error or Exit code != 0; "soft" = exit code 0 but the output holds a
                Traceback / No such file / SyntaxError ... (an exit code of a chain with `;`, `| head`, `2>&1` lies).

Usage:
  python classify.py --dir OUT_DIR [--rules extra_rules.json] [--examples 3]
Reads OUT_DIR/rows.json (+ scan_meta.json). Writes OUT_DIR/final.json (every row with "cat" and "soft") and
OUT_DIR/summary.json ({"meta": {...totals...}, "clusters": [...]}), prints the table.

--rules  a JSON list of your own rules, applied BEFORE the built-in ones, e.g.
         [{"cat": "env: gh not installed", "where": "out", "pattern": "gh: command not found"},
          {"cat": "EXPECTED: my probe", "where": "cmd", "pattern": "spark_fetch"}]
         where = "out" (tool output), "cmd" (command / file path) or "tool:Name|Name2" (tool name; pattern is then
         matched against the output, an empty pattern matches every call of that tool). Use it for the causes specific
         to your project; what remains in "unclassified-strong" at the end of the table is what needs a new rule.
Input is checked first: a missing / empty --dir, a rows.json that is not from scan_fail.py, a --rules file that is
missing, not JSON, not a list or has a bad regex print "ERROR: ..." and exit with code 2 (no Traceback).
If the scan found 0 tool calls a WARNING is printed. A Git Bash path /c/x is accepted on Windows (turned into C:/x).
Soft rows (exit 0) of commands that run the audit scripts themselves are NOISE meta: otherwise the audit counts its own output.
A soft row from `cat` / `sed` of a file that merely quotes an error stays "real" on purpose (it may hide a true failure of a
background task): move such rows to noise by hand with a --rules entry on the command.
The built-in rules match Git Bash / PowerShell / python / javap / Edit / Write messages in English; unknown tools fall to
"unclassified-strong" - read them with show.py and add a rule.
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

# a line of the output that really is an error, even when the exit code is 0 (soft failure)
SOFT = re.compile(r"(?m)^\s*(Traceback \(most recent|[^\n]*: No such file or directory|ls: cannot access|"
                  r"[^\n]*command not found|Error: class not found|cp: cannot stat|caution: filename not matched|"
                  r"unzip:\s+cannot find|[^\n]*Permission denied|[^\n]*SyntaxError:|[^\n]*unexpected EOF|"
                  r"[^\n]*UnicodeEncodeError|[^\n]*UnicodeDecodeError|ModuleNotFoundError)")

# soft rows only (exit code 0): the text is a quotation, not a failure of this command
AUDIT_CMD = re.compile(r"scan_fail\.py|classify\.py|compare\.py|show\.py|rows\.json|final\.json|summary\.json")

BUILTIN = [
    # (where, regex, category)  - first match wins; order matters
    ("out", r"==> Exit code|'Traceback', 'UnicodeEncodeError'\]", "NOISE meta (an agent printed old transcript / audit text)"),
    ("tool:StructuredOutput", r"", "tool: StructuredOutput payload not valid (subagent)"),
    ("out", r"Subagents should return findings as text", "tool: Write refused - subagent may not write report files"),
    ("tool:Edit|Write|NotebookEdit", r"File has not been read", "tool: Write / Edit without prior Read"),
    ("tool:Edit|Write|NotebookEdit", r"modified since read", "tool: Write / Edit after the file changed on disk"),
    ("tool:Edit", r"String to replace not found|Found \d+ matches of the string to replace", "tool: Edit old_string mismatch"),
    ("out", r"Blocked: sleep", "tool: foreground sleep blocked"),
    ("out", r"auto mode classifier", "permission: auto-mode classifier denied the call"),
    ("out", r"exceeds maximum allowed tokens", "tool: Read file too large"),
    ("out", r"InputValidationError", "tool: wrong tool arguments (schema not loaded)"),
    ("tool:Read", r"", "NOISE Read content only"),
]


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


def read_json(path, what, hint=""):
    p = Path(path)
    if not p.is_file():
        die("%s not found: %s%s" % (what, p, hint))
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError) as e:
        die("%s is not valid JSON: %s (%s)" % (what, p, e))


def load_rules(path):
    if not path:
        return []
    rules = read_json(norm_path(path), "rules file")
    if not isinstance(rules, list):
        die("rules file must hold a JSON list of objects {cat, pattern, where}: %s" % path)
    out = []
    for i, r in enumerate(rules):
        if not isinstance(r, dict) or not isinstance(r.get("pattern"), str) or not isinstance(r.get("cat"), str):
            die("rules file %s: item %d needs string fields \"cat\" and \"pattern\"" % (path, i))
        where = r.get("where", "out")
        if not isinstance(where, str) or not (where in ("out", "cmd") or where.startswith("tool:")):
            die("rules file %s: item %d has where=%r (use \"out\", \"cmd\" or \"tool:Name|Name2\")" % (path, i, where))
        try:
            re.compile(r["pattern"])
            if where.startswith("tool:"):
                re.compile(where[5:])
        except re.error as e:
            die("rules file %s: item %d has a bad regex: %s" % (path, i, e))
        out.append((where, r["pattern"], r["cat"]))
    return out


ROW_KEYS = {"src", "ts", "tool", "cmd", "err", "iserr", "nonzero"}


def load_rows(d):
    if not d.is_dir():
        die("--dir is not a folder: %s" % d)
    rows = read_json(d / "rows.json", "rows.json", " (run scan_fail.py with --out on this folder first)")
    if not isinstance(rows, list) or not all(isinstance(r, dict) and ROW_KEYS <= r.keys() for r in rows):
        die("%s does not look like rows.json of scan_fail.py (a list of rows with %s)" % (d / "rows.json", sorted(ROW_KEYS)))
    return rows


def classify(r, extra):
    t, cmd, tool = r["err"], r["cmd"], r["tool"]
    strong = r["iserr"] or r["nonzero"]
    for where, pat, cat in extra + BUILTIN:
        if where.startswith("tool:"):
            if re.fullmatch(where[5:], tool) and (not pat or re.search(pat, t)):
                return cat
        elif re.search(pat, t if where == "out" else cmd):
            return cat
    if not strong and not SOFT.search(t):
        return "NOISE pattern text inside successful output"
    if not strong and AUDIT_CMD.search(cmd):
        return "NOISE meta (the audit scripts or old audit output printed again)"
    # bash / python messages
    if re.search(r"unexpected EOF while looking for matching", t):
        return "bash: heredoc / quote breakage (unexpected EOF)"
    if re.search(r"SyntaxError: (unterminated string|\(unicode error\))", t) or (re.search(r"SyntaxError", t) and "EOL" in t) \
            or "SyntaxError: unexpected character after line continuation" in t \
            or ("SyntaxWarning" in t and "invalid escape sequence" in t and strong):
        return "python: backslash / quote SyntaxError in inline script (Windows path or backslash)"
    if "UnicodeEncodeError" in t or "UnicodeDecodeError" in t:
        return "python: cp1251 / encoding error (no PYTHONIOENCODING)"
    if re.search(r"No such file or directory: '/[a-z]/", t) or (re.search(r"open\(r?'/[a-z]/", cmd) and "FileNotFoundError" in t):
        return "path: Git-Bash /c/ path given to Windows python"
    if "-W error" in cmd and "ResourceWarning" in t:
        return "EXPECTED intentional syntax check (python -W error)"
    if "SyntaxError: duplicate key" in t:
        return "EXPECTED genuine negative test result (an offline check caught a real mismatch)"
    if "HTTPError" in t:
        return "python: JSON decode of non-JSON file / empty HTTP response"
    if "ModuleNotFoundError" in t:
        return "env: python module missing"
    if "Error: class not found" in t or "could not open `" in t:
        return "java: javap class not found / classpath"
    if re.search(r"error: cannot find symbol|NoClassDefFoundError|Not bootstrapped|ClassNotFoundException|bad path element", t):
        return "java: compile / classpath / bootstrap error"
    if "EcmaError" in t:
        return "kubejs / rhino: harness test error in a generated script"
    if "JSONDecodeError" in t:
        return "python: JSON decode of non-JSON file / empty HTTP response"
    if "PatternError" in t:
        return "python: script bug - bad regex (unescaped chars from CLI args)"
    if re.search(r"AssertionError|substring not found", t) and "Traceback" in t:
        return "python: edit-script guard fired (anchor / assert mismatch)"
    if "Traceback" in t and re.search(r"(AttributeError|KeyError|TypeError|IndexError|ValueError|NameError|UnboundLocalError)", t):
        return "python: script bug (Attr / Key / Type / Index / Value error)"
    if "OSError: [Errno 22]" in t or "FileNotFoundError" in t:
        return "path: wrong path guess (python FileNotFoundError / doubled path)"
    if re.search(r"No such file or directory|cannot access|cannot stat|cannot find or open|can't read|cannot open", t):
        return "path: wrong path guess / glob matched nothing (shell)"
    if "tail: option used in invalid context" in t:
        return "bash: tail -3 on several files (GNU syntax)"
    if "Traceback" in t:
        return "python: other traceback"
    if "command not found" in t:
        return "env: command not found (tool not installed)"
    if "FAIL " in t and "checks," in t:
        return "EXPECTED genuine negative test result (an offline check caught a real mismatch)"
    if re.search(r"caution: filename not matched|Exit code 11", t):
        return "EXPECTED unzip: member not in jar (probe)"
    if tool == "PowerShell":
        return "EXPECTED PowerShell recursive search exit 1 (ErrorAction Silent)"
    m = re.match(r"\s*Exit code (\d+)", t)
    code = m.group(1) if m else "?"
    if re.search(r"\bdiff\b", cmd):
        return "EXPECTED diff / cmp showed differences (exit 1)"
    if re.search(r"grep|rg |\| head|2>/dev/null|\bls\b|unzip -l|\bwc\b", cmd):
        return "EXPECTED last probe command (grep / ls) exit %s with useful output" % code
    return "unclassified-strong"


def head(r, n=150):
    return r["cmd"].replace("\n", " ")[:n]


def err_head(r):
    t = r["err"]
    m = SOFT.search(t)
    if m and r["soft"]:
        t = t[m.start():]
    elif r["nonzero"] or r["iserr"]:
        for pat in [r"unexpected EOF[^\n]*", r"[A-Za-z]*Error[^\n]*", r"Error: class[^\n]*",
                    r"[^\n]*No such file[^\n]*", r"[^\n]*cannot[^\n]*"]:
            mm = re.search(pat, t)
            if mm:
                t = mm.group(0)
                break
    return re.sub(r"\s+", " ", t)[:200]


def kind(cat):
    if cat.startswith("NOISE"):
        return "noise"
    if cat.startswith("EXPECTED"):
        return "expected"
    return "real"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", required=True, help="folder with rows.json (the --out of scan_fail.py)")
    ap.add_argument("--rules")
    ap.add_argument("--examples", type=int, default=3)
    a = ap.parse_args()
    d = Path(norm_path(a.dir))
    extra = load_rules(a.rules)
    rows = load_rows(d)
    try:
        scan_meta = json.loads((d / "scan_meta.json").read_text(encoding="utf-8"))
    except Exception:
        scan_meta = {}
    if not scan_meta.get("tool_calls") and "tool_calls" in scan_meta:
        print("WARNING: the scan found 0 tool calls - an empty table here is NOT 'no failures'. "
              "Check --since/--until/--session/--dir of scan_fail.py.")

    by = collections.defaultdict(list)
    for r in rows:
        r["cat"] = classify(r, extra)
        r["soft"] = not (r["iserr"] or r["nonzero"])
        by[r["cat"]].append(r)
    (d / "final.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")

    clusters = []
    for c, rs in sorted(by.items(), key=lambda x: -len(x[1])):
        rs2 = sorted(rs, key=lambda r: r["ts"])
        srcs = collections.Counter("main" if r["src"].startswith("main") else "sub" for r in rs)
        ex, seen = [], set()
        if kind(c) != "noise":
            for r in [rs2[0], rs2[len(rs2) // 2], rs2[-1]][:a.examples]:
                k = (r["src"], r["ts"])
                if k not in seen:
                    seen.add(k)
                    ex.append("%s %s -> %s" % (r["tool"], head(r, 90), err_head(r)[:100]))
        clusters.append(dict(type=c, kind=kind(c), count=len(rs), hard=sum(1 for r in rs if not r["soft"]),
                             soft=sum(1 for r in rs if r["soft"]), main=srcs.get("main", 0), sub=srcs.get("sub", 0),
                             agents=len({r["src"] for r in rs if not r["src"].startswith("main")}),
                             first=rs2[0]["ts"][:16], last=rs2[-1]["ts"][:16], examples=ex))
    tot = collections.Counter()
    for c in clusters:
        tot[c["kind"]] += c["count"]
        if c["kind"] == "real":
            tot["real_hard"] += c["hard"]
            tot["real_soft"] += c["soft"]
    meta = dict(scan=scan_meta, rows=len(rows), real=tot["real"], real_hard=tot["real_hard"], real_soft=tot["real_soft"],
                expected=tot["expected"], noise=tot["noise"],
                unclassified=sum(c["count"] for c in clusters if c["type"] == "unclassified-strong"))
    (d / "summary.json").write_text(json.dumps(dict(meta=meta, clusters=clusters), ensure_ascii=False, indent=1), encoding="utf-8")

    for c in clusters:
        print("%4d (hard %3d, soft %3d) main=%d sub=%d/%dag  %s  [%s..%s]" % (
            c["count"], c["hard"], c["soft"], c["main"], c["sub"], c["agents"], c["type"], c["first"][5:], c["last"][5:]))
    print("-----")
    print("tool calls %s | rows %d | REAL %d (hard %d, soft %d) | expected %d | noise %d | unclassified %d" % (
        scan_meta.get("tool_calls", "?"), len(rows), meta["real"], meta["real_hard"], meta["real_soft"],
        meta["expected"], meta["noise"], meta["unclassified"]))


if __name__ == "__main__":
    main()
