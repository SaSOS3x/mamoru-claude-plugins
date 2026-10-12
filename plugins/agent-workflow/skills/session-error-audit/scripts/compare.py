#!/usr/bin/env python3
"""Step 5 of session-error-audit: compare two audits (this stage vs the previous one) by cluster.

Usage:
  python compare.py --old OLD_DIR --new NEW_DIR [--min 1]
OLD_DIR / NEW_DIR hold summary.json from classify.py. Prints, for every REAL cluster, the count before and after,
then NEW clusters (a new kind of error: find the cause), GONE clusters (the fix worked) and the totals.
Clusters are matched by name; if you changed the rules between runs, rerun classify.py on the old rows.json first.
Absolute counts depend on how much work was done in the period: compare also the number of tool calls (printed).
A missing folder, a folder without summary.json or a summary.json of a wrong shape prints "ERROR: ..." and exits
with code 2 (no Traceback). A Git Bash path /c/x is accepted on Windows (turned into C:/x).
"""
import argparse
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


def load(d, label):
    d = Path(norm_path(d))
    if not d.is_dir():
        die("--%s is not a folder: %s" % (label, d))
    f = d / "summary.json"
    if not f.is_file():
        die("--%s: summary.json not found in %s (run classify.py on that audit first)" % (label, d))
    try:
        s = json.loads(f.read_text(encoding="utf-8"))
        meta, clusters = s["meta"], s["clusters"]
        for k in ("real", "real_hard", "real_soft"):
            meta[k]
        by = {c["type"]: c for c in clusters if c["kind"] == "real"}
        for c in by.values():
            c["count"]
    except (ValueError, OSError) as e:
        die("--%s: %s is not valid JSON (%s)" % (label, f, e))
    except (KeyError, TypeError):
        die("--%s: %s does not look like summary.json of classify.py (needs meta.real/real_hard/real_soft and clusters)" % (label, f))
    return meta, by


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--min", type=int, default=1, help="hide clusters smaller than this in both runs")
    a = ap.parse_args()
    mo, co = load(a.old, "old")
    mn, cn = load(a.new, "new")
    co_calls = mo.get("scan", {}).get("tool_calls") or 0
    cn_calls = mn.get("scan", {}).get("tool_calls") or 0
    print("calls: old %s, new %s | real: old %d (hard %d, soft %d), new %d (hard %d, soft %d)" % (
        co_calls, cn_calls, mo["real"], mo["real_hard"], mo["real_soft"], mn["real"], mn["real_hard"], mn["real_soft"]))
    if co_calls and cn_calls:
        print("real failures per 1000 calls: old %.1f, new %.1f" % (1000.0 * mo["real"] / co_calls, 1000.0 * mn["real"] / cn_calls))
    print()
    print("%6s %6s %6s  cluster" % ("old", "new", "delta"))
    for t in sorted(set(co) | set(cn), key=lambda t: -(cn.get(t, {}).get("count", 0))):
        o, n = co.get(t, {}).get("count", 0), cn.get(t, {}).get("count", 0)
        if max(o, n) < a.min:
            continue
        tag = "  NEW" if o == 0 else ("  GONE" if n == 0 else "")
        print("%6d %6d %+6d  %s%s" % (o, n, n - o, t, tag))


if __name__ == "__main__":
    main()
