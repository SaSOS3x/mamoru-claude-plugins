#!/usr/bin/env python3
"""project_env.py - keep copies of shared skill scripts in a project's environment and notice when they drift.

The project environment is one folder of the project with everything its agents use: tasks, journal, tools.
The project's CLAUDE.md names it, and every agent (subagents too) gets CLAUDE.md, so a tool at a fixed project
path costs no skill load and no search. A shared script keeps ONE master copy in `scripts/` of a skill; the
project holds a registered copy in its tools folder. The register is TOOLS.json in that folder: file name,
skill, path inside the skill, sha256 of the copy, dates. Never edit a copy: change the master, then --update.

  python project_env.py add   TOOLS_DIR SOURCE_FILE [--skill NAME]   copy a skill script in and register it
  python project_env.py check TOOLS_DIR [--update] [--source DIR ...] compare each copy with the register and
                                                                       with the installed skill
  python project_env.py list  TOOLS_DIR
  python project_env.py -h | --help

SOURCE_FILE lies inside .../skills/<skill>/ (the skill name is taken from the path) or --skill names the skill.
check looks for the master in every --source DIR (a marketplace checkout or a skill folder) or, without --source,
in the installed plugins: the Claude desktop app copies of claude.ai account plugins and the Claude Code plugin
cache (orphaned cache versions are skipped). Result lines:
  OK          the copy equals the register and the master
  EDITED      the copy was changed by hand (move the change into the master; --update never overwrites it)
  OUTDATED    the master differs from the copy (--update copies the master in)
  DIFFERENT   installed copies of the skill disagree (e.g. the app is on an older version than the cache):
              nothing is updated; give --source to choose
  MISSING     the registered copy is gone
  NOT FOUND   no master was found (the skill is not installed here): nothing to compare
Exit 0 when only OK / NOT FOUND remain, 1 when EDITED / OUTDATED / DIFFERENT / MISSING remain, 2 usage or
register error. Stdlib only.
"""
import datetime
import glob
import hashlib
import json
import os
import pathlib
import shutil
import sys

REGISTER = 'TOOLS.json'


class UsageError(Exception):
    """Bad arguments or an unreadable register: exit 2."""


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def today():
    return datetime.date.today().isoformat()


def load(tools):
    reg = tools / REGISTER
    if not reg.exists():
        return {'tools': {}}
    try:
        data = json.loads(reg.read_text(encoding='utf-8'))
    except (OSError, ValueError) as e:
        raise UsageError(f'error: {reg} cannot be read ({e})')
    if not isinstance(data, dict) or not isinstance(data.get('tools'), dict):
        raise UsageError(f'error: {reg} has no "tools" object')
    return data


def save(tools, data):
    text = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + '\n'
    (tools / REGISTER).write_text(text, encoding='utf-8', newline='\n')


def skill_of(path):
    """('skill-name', 'scripts/x.py') when path lies under .../skills/<skill>/, else (None, None)."""
    parts = pathlib.Path(path).resolve().parts
    for i in range(len(parts) - 2, -1, -1):
        if parts[i] == 'skills' and i + 2 < len(parts):
            return parts[i + 1], '/'.join(parts[i + 2:])
    return None, None


def installed_masters(skill, rel):
    roots = []
    appdata = os.environ.get('APPDATA')
    if appdata:  # Claude desktop app: copies of the plugins installed on the claude.ai account
        roots.append(os.path.join(appdata, 'Claude', 'local-agent-mode-sessions', '*', '*', 'rpm', 'plugin_*'))
    roots.append(os.path.join(str(pathlib.Path.home()), '.claude', 'plugins', 'cache', '*', '*', '*'))  # Claude Code
    found = []
    for root in roots:
        for plugin_dir in glob.glob(root):
            if os.path.exists(os.path.join(plugin_dir, '.orphaned_at')):
                continue  # an old cache version that no session uses any more
            f = os.path.join(plugin_dir, 'skills', skill, *rel.split('/'))
            if os.path.isfile(f):
                found.append(f)
    return found


def source_masters(sources, skill, rel):
    found = []
    for d in sources:
        d = pathlib.Path(d)
        if d.name == skill and (d / rel).is_file():
            found.append(str(d / rel))
        found += glob.glob(str(d / '**' / 'skills' / skill / rel), recursive=True)
    return sorted(set(found))


def cmd_add(args):
    if len(args) < 2 or args[0].startswith('-') or args[1].startswith('-'):
        raise UsageError('usage: project_env.py add TOOLS_DIR SOURCE_FILE [--skill NAME]')
    tools, src = pathlib.Path(args[0]), pathlib.Path(args[1])
    if '--skill' in args and args.index('--skill') + 1 >= len(args):
        raise UsageError('--skill needs a name')
    skill = args[args.index('--skill') + 1] if '--skill' in args else None
    if not src.is_file():
        print(f'error: {src} is not a file')
        return 2
    found_skill, rel = skill_of(src)
    skill = skill or found_skill
    if not skill:
        print(f'error: {src} is not inside .../skills/<skill>/; name the skill with --skill')
        return 2
    rel = rel if found_skill == skill else f'scripts/{src.name}'
    tools.mkdir(parents=True, exist_ok=True)
    data = load(tools)
    target = tools / src.name
    entry = data['tools'].get(src.name)
    if entry and entry['skill'] != skill:
        print(f'error: {src.name} is already registered from skill {entry["skill"]}')
        return 2
    if target.exists() and not entry and sha(target) != sha(src):
        print(f'error: {target} exists, is not registered and differs from {src}: '
              'it may be a project tool of the same name; rename one of them first')
        return 2
    shutil.copyfile(src, target)
    data['tools'][src.name] = {'skill': skill, 'source': rel, 'sha256': sha(target),
                               'added': (entry or {}).get('added', today()), 'updated': today()}
    save(tools, data)
    print(f'registered {target} <- {skill}/{rel}')
    return 0


def cmd_check(args):
    if not args or args[0].startswith('-'):
        raise UsageError('usage: project_env.py check TOOLS_DIR [--update] [--source DIR ...]')
    tools = pathlib.Path(args[0])
    if not tools.is_dir():
        raise UsageError(f'error: {tools} is not a folder')
    update = '--update' in args
    sources = [args[i + 1] for i, a in enumerate(args) if a == '--source' and i + 1 < len(args)]
    data = load(tools)
    if not data['tools']:
        print(f'no registered tools in {tools / REGISTER}')
        return 0
    bad, changed = 0, False
    for name, e in sorted(data['tools'].items()):
        copy = tools / name
        tag = f'{name} ({e["skill"]}/{e["source"]})'
        if not copy.is_file():
            print(f'MISSING    {tag}: {copy} is gone')
            bad = 1
            continue
        own = sha(copy)
        if own != e['sha256']:
            print(f'EDITED     {tag}: the copy differs from the register; move the change into the skill master')
            bad = 1
            continue
        masters = source_masters(sources, e['skill'], e['source']) if sources else installed_masters(e['skill'], e['source'])
        if not masters:
            print(f'NOT FOUND  {tag}: no {"--source" if sources else "installed"} copy of the skill has this script')
            bad |= bool(sources)  # an explicit --source that holds nothing is a mistake, not "not installed"
            continue
        versions = {}
        for m in masters:
            versions.setdefault(sha(m), []).append(m)
        if len(versions) > 1:
            print(f'DIFFERENT  {tag}: the copies of the skill disagree, nothing updated; choose one with --source:')
            for h, paths in versions.items():
                mark = 'same as the copy' if h == own else 'other'
                print(f'           {mark}: {paths[0]}' + (f' (+{len(paths) - 1})' if len(paths) > 1 else ''))
            bad = 1
            continue
        (master_sha, paths), = versions.items()
        if master_sha == own:
            print(f'OK         {tag}')
        elif update:
            shutil.copyfile(paths[0], copy)
            e.update(sha256=sha(copy), updated=today())
            changed = True
            print(f'UPDATED    {tag} <- {paths[0]}')
        else:
            print(f'OUTDATED   {tag}: the skill has another version ({paths[0]}); run check --update')
            bad = 1
    if changed:
        save(tools, data)
    return bad


def cmd_list(args):
    if not args or args[0].startswith('-'):
        raise UsageError('usage: project_env.py list TOOLS_DIR')
    data = load(pathlib.Path(args[0]))
    for name, e in sorted(data['tools'].items()):
        print(f'{name}: {e["skill"]}/{e["source"]}, added {e["added"]}, updated {e["updated"]}, sha256 {e["sha256"][:12]}')
    if not data['tools']:
        print('no registered tools')
    return 0


def main(argv):
    if not argv or argv[0] in ('-h', '--help'):
        print(__doc__)
        return 0 if argv else 2
    commands = {'add': cmd_add, 'check': cmd_check, 'list': cmd_list}
    if argv[0] not in commands:
        print(f'unknown command {argv[0]}\n{__doc__}')
        return 2
    try:
        return commands[argv[0]](argv[1:])
    except UsageError as e:
        print(e)
        return 2


if __name__ == '__main__':
    sys.stdout.reconfigure(errors='backslashreplace')
    sys.exit(main(sys.argv[1:]))
