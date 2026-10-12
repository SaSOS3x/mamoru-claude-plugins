#!/usr/bin/env python3
"""classpath_jar.py - a tiny jar whose manifest Class-Path lists many jars/dirs (Windows 32k command-line limit).

  python classpath_jar.py OUT.jar ENTRY [ENTRY ...]
  ENTRY = a jar, a directory, a glob (mods/*.jar, libs/**/*.jar) or @listfile (one path per line).
  Then:  javap -cp OUT.jar some.pkg.Class      (javap has no @argfile; java / javac do: java @args.txt)

Why: javap / java -cp with a 35k-char classpath fails on Windows with "Argument list too long" (CreateProcess ~32767
chars). The JVM follows Class-Path of a jar on the classpath, so the long list moves into the file.
Details: entries become file:/// URLs (spaces -> %20), directories get a trailing '/', manifest lines are wrapped at
72 bytes with a leading space on continuation lines (the manifest spec). Needs only the stdlib; ASCII-only output.
Exit 0 ok, 1 usage / nothing matched.
"""
import glob
import pathlib
import sys
import zipfile


def expand(entry):
    if entry.startswith('@'):
        lines = pathlib.Path(entry[1:]).read_text(encoding='utf-8').splitlines()
        return [l.strip() for l in lines if l.strip()]
    if any(ch in entry for ch in '*?['):
        return sorted(glob.glob(entry, recursive=True))
    return [entry]


def to_url(p):
    path = pathlib.Path(p).resolve()
    url = path.as_uri()
    return url + '/' if path.is_dir() and not url.endswith('/') else url


def wrap(name, value):
    raw = (name + ': ' + value).encode('ascii')
    out, first = [], True
    while raw:
        n = 72 if first else 71
        out.append((b'' if first else b' ') + raw[:n])
        raw, first = raw[n:], False
    return b'\r\n'.join(out) + b'\r\n'


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    out, items = argv[0], []
    for e in argv[1:]:
        items += expand(e)
    items = [p for p in items if pathlib.Path(p).exists()]
    if not items:
        print('nothing matched')
        return 1
    manifest = b'Manifest-Version: 1.0\r\n' + wrap('Class-Path', ' '.join(to_url(p) for p in items)) + b'\r\n'
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('META-INF/MANIFEST.MF', manifest)
    print(f'{out}: {len(items)} entries, manifest {len(manifest)} bytes')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
