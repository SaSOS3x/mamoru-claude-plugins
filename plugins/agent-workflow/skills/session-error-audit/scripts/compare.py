#!/usr/bin/env python3
"""Step 5 of session-error-audit: compare two audits (this stage vs the previous one) by cluster.

Usage:
  python compare.py --old OLD_DIR --new NEW_DIR [--min 1]
OLD_DIR / NEW_DIR hold summary.json from classify.py. Prints, for every REAL cluster, the count before and after,
then NEW clusters (a new kind of error: find the cause), GONE clusters (the fix worked) and the totals.
Clusters are matched by name; if you changed the rules between runs, rerun classify.py on the old rows.json first.
Absolute counts depend on how much work was done in the period: compare also the number of tool calls (printed).
"""
import argparse
import json
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def load(d):
    s = json.loads((Path(d) / "summary.json").read_text(encoding="utf-8"))
    return s["meta"], {c["type"]: c for c in s["clusters"] if c["kind"] == "real"}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--min", type=int, default=1, help="hide clusters smaller than this in both runs")
    a = ap.parse_args()
    mo, co = load(a.old)
    mn, cn = load(a.new)
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
