#!/usr/bin/env python3
"""check_skills.py - before a commit: every skill changed against HEAD must have a new entry in its CHANGELOG.md.
Run: python check_skills.py   Exit 0 ok, 1 a changed skill without a CHANGELOG entry, 2 git failed."""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def git(*args):
    r = subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.returncode:
        print(f'git {args[0]} failed in {ROOT}: not the marketplace repository, or git is missing')
        sys.exit(2)
    return r.stdout.splitlines()


changed = set(git('diff', '--name-only', 'HEAD')) | set(git('ls-files', '--others', '--exclude-standard'))
skills = {'/'.join(p.split('/')[:4]) for p in changed if p.startswith('plugins/') and p.split('/')[2:3] == ['skills'] and p.count('/') >= 4}
missing = sorted(s for s in skills if s + '/CHANGELOG.md' not in changed)
for s in missing:
    print(f'{s}: changed, but no new entry in CHANGELOG.md')
print(f'{len(skills)} changed skills, {len(missing)} without a CHANGELOG entry')
sys.exit(1 if missing else 0)
