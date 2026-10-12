#!/usr/bin/env python3
"""Look at rows to check a classification by eye (step 2b: always read the biggest cluster and every "unclassified-strong").

Usage:
  python show.py --dir OUT_DIR --cat "unclassified"            # rows of final.json whose cluster name contains the text
  python show.py --dir OUT_DIR --cat "wrong path" --n 10 --width 300
  python show.py --dir OUT_DIR --mode strong                   # rows.json: is_error or exit != 0
  python show.py --dir OUT_DIR --mode weak                     # rows.json: pattern hit only (look for soft failures)
  python show.py --dir OUT_DIR --kind real --src agent-a1b2    # only real failures of one agent (id prefix)
Output line: index|source|time|tool|E(is_error)X(exit!=0)|cluster or hits|command ==> output head
"""
import argparse
import collections
import json
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", required=True)
    ap.add_argument("--mode", choices=["strong", "weak"])
    ap.add_argument("--cat", help="substring of the cluster name (needs final.json)")
    ap.add_argument("--kind", choices=["real", "expected", "noise"])
    ap.add_argument("--src", help="source prefix: main or agent-xxxx")
    ap.add_argument("--n", type=int, default=0, help="show at most N rows (0 = all)")
    ap.add_argument("--width", type=int, default=200, help="characters of output per row")
    a = ap.parse_args()
    d = Path(a.dir)
    if a.mode or not (d / "final.json").exists():
        rows = json.loads((d / "rows.json").read_text(encoding="utf-8"))
        if a.mode == "weak":
            rows = [r for r in rows if not (r["iserr"] or r["nonzero"])]
            print(collections.Counter(r["tool"] for r in rows))
            rows = [r for r in rows if r["tool"] in ("Bash", "PowerShell") or r["tlen"] < 400]
        else:
            rows = [r for r in rows if r["iserr"] or r["nonzero"]]
    else:
        rows = json.loads((d / "final.json").read_text(encoding="utf-8"))
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
        e = r["err"].replace("\n", " | ")[:a.width]
        c = r["cmd"].replace("\n", " ")[:150]
        flag = ("E" if r["iserr"] else "") + ("X" if r["nonzero"] else "")
        info = r.get("cat") or r["hits"]
        print("%d|%s|%s|%s|%s|%s|%s  ==> %s" % (i, r["src"][:14], r["ts"][5:16], r["tool"], flag, info, c, e))


if __name__ == "__main__":
    main()
