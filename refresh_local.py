#!/usr/bin/env python3
"""Refresh the locally installed copies of this marketplace's plugins in Claude Code.

Claude Code does not read the plugins from this folder: it copies each plugin into
~/.claude/plugins/cache/mamoru-plugins/<plugin>/<version or commit SHA>/ at install and update
(checked 2026-10-12, Claude Code 2.1.294 on Windows). After you change a skill here:
commit, then run this script, then start a new session (/reload-plugins does not switch a
plugin that is already loaded to the new version). This is the install used by `claude` in a
terminal; the Code tab of the Claude desktop app uses the claude.ai account copies (see README).

  python refresh_local.py            update the marketplace and every plugin listed in marketplace.json
  python refresh_local.py --install  also install plugins that are listed but not installed yet
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def run(args):
    r = subprocess.run(['claude'] + args, capture_output=True, text=True, encoding='utf-8', errors='replace')
    out = (r.stdout + r.stderr).strip().splitlines()
    print(' '.join(args), '->', out[-1] if out else '(no output)')
    return r.returncode


def main():
    m = json.load(open(os.path.join(ROOT, '.claude-plugin', 'marketplace.json'), encoding='utf-8'))
    name = m['name']
    bad = run(['plugin', 'marketplace', 'update', name])
    listed = subprocess.run(['claude', 'plugin', 'list'], capture_output=True, text=True, encoding='utf-8', errors='replace').stdout
    for p in m['plugins']:
        ref = f"{p['name']}@{name}"
        if ref in listed:
            bad |= run(['plugin', 'update', ref])
        elif '--install' in sys.argv:
            bad |= run(['plugin', 'install', ref])
        else:
            print(ref, '-> not installed (use --install)')
    print('start a new terminal session to load the new copies (/reload-plugins keeps a loaded version);')
    print('the desktop app Code tab needs a push, an update on claude.ai and an app restart instead')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
