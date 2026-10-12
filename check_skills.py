#!/usr/bin/env python3
"""check_skills.py - checks of this marketplace before a commit:  python check_skills.py

1. every skill folder has SKILL.md with a name and a description of at most 1024 characters, and a CHANGELOG.md;
2. every skill folder with changes against HEAD (staged, unstaged or new files) changed its CHANGELOG.md too:
   a change without a recorded "why" fails;
3. no CRLF in text files except .cmd / .bat / .ps1 (the local install is copied from this working folder, the
   claude.ai one from GitHub, and both must be the same bytes).
Exit 0 ok, 1 problems found, 2 git failed. Stdlib only, ASCII output.
"""
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
BYTE_EXACT = ('.cmd', '.bat', '.ps1')


def git(*args):
    r = subprocess.run(['git', *args], cwd=ROOT, capture_output=True)
    if r.returncode:
        print(f'git {" ".join(args)} failed: {r.stderr.decode("utf-8", "replace").strip()}')
        sys.exit(2)
    return [l for l in r.stdout.decode('utf-8', 'replace').splitlines() if l]


def frontmatter(text):
    m = re.match(r'---\r?\n(.*?)\r?\n---', text, re.S)
    fields = {}
    for line in (m.group(1).splitlines() if m else []):
        k, sep, v = line.partition(':')
        if sep:
            fields[k.strip()] = v.strip().strip('"\'')
    return fields


def main():
    problems = []
    skills = sorted(p.parent for p in ROOT.glob('plugins/*/skills/*/SKILL.md'))
    for d in skills:
        rel = d.relative_to(ROOT).as_posix()
        fm = frontmatter((d / 'SKILL.md').read_text(encoding='utf-8'))
        if fm.get('name') != d.name:
            problems.append(f'{rel}: SKILL.md name is {fm.get("name")!r}, the folder is {d.name!r}')
        if not fm.get('description'):
            problems.append(f'{rel}: SKILL.md has no description')
        elif len(fm['description']) > 1024:
            problems.append(f'{rel}: description is {len(fm["description"])} characters (limit 1024)')
        if not (d / 'CHANGELOG.md').is_file():
            problems.append(f'{rel}: no CHANGELOG.md')

    changed = set(git('diff', '--name-only', 'HEAD')) | set(git('ls-files', '--others', '--exclude-standard'))
    for d in skills:
        rel = d.relative_to(ROOT).as_posix() + '/'
        touched = sorted(p for p in changed if p.startswith(rel))
        if touched and rel + 'CHANGELOG.md' not in changed:
            problems.append(f'{rel}: changed ({", ".join(p[len(rel):] for p in touched[:3])}) but CHANGELOG.md was not')

    for name in git('ls-files', '--cached', '--others', '--exclude-standard'):
        p = ROOT / name
        if name.lower().endswith(BYTE_EXACT) or not p.is_file():
            continue
        data = p.read_bytes()
        if b'\x00' not in data and b'\r\n' in data:
            problems.append(f'{name}: CRLF line endings (text files are LF here)')

    for line in problems:
        print('PROBLEM', line)
    print(f'{len(skills)} skills checked, {len(changed)} changed files, {len(problems)} problems')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.stdout.reconfigure(errors='backslashreplace')
    sys.exit(main())
