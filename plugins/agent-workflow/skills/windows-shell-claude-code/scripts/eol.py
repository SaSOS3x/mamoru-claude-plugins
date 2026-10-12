#!/usr/bin/env python3
"""eol.py - count line endings on BYTES. In Git Bash `grep -c $'\\r' file` prints 0 for a CRLF file (checked 2026-10-12),
so never use it to decide CRLF vs LF.

  python eol.py FILE [FILE ...]
  -> "FILE: CRLF n, LF-only n, CR-only n, BOM yes|no, last line terminated yes|no -> CRLF|LF|CR|MIXED|none"
Exit 1 when a file is unreadable or MIXED (CRLF together with lone LF / CR, or LF together with CR).
Stdlib only, ASCII-only output.
"""
import sys


def classify(data):
    crlf = data.count(b'\r\n')
    lf = data.count(b'\n') - crlf
    cr = data.count(b'\r') - crlf
    if crlf + lf + cr == 0:
        kind = 'none'
    elif (crlf and (lf or cr)) or (lf and cr):
        kind = 'MIXED'
    else:
        kind = 'CRLF' if crlf else 'LF' if lf else 'CR'
    return crlf, lf, cr, kind


def main(paths):
    bad = 0
    for p in paths:
        try:
            with open(p, 'rb') as f:
                data = f.read()
        except OSError as e:
            print(f'{p}: {e}')
            bad = 1
            continue
        crlf, lf, cr, kind = classify(data)
        bom = data.startswith(b'\xef\xbb\xbf')
        term = bool(data) and data[-1:] in (b'\n', b'\r')
        print(f'{p}: CRLF {crlf}, LF-only {lf}, CR-only {cr}, BOM {"yes" if bom else "no"}, '
              f'last line terminated {"yes" if term else "no"} -> {kind}')
        bad |= kind == 'MIXED'
    return bad


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1:]))
