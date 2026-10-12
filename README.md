# mamoru-claude-plugins

Claude Code plugin marketplace `mamoru-plugins` (created 2026-10-12): installed locally from this folder and on claude.ai from the
GitHub copy. Master copy of the skills since then: edit here, then mirror the port skills into the DeceasedCraft port (`_port/tools/skills/`).

| Plugin | Skills |
|---|---|
| minecraft-modding | kubejs-neoforge-2101, neoforge-mod-configs, modpack-port-neoforge, port-from-1182-pack, lostcities-biome-zones-mixin, minecraft-worldgen-density-1-21, tps-optimization-neoforge |
| agent-workflow | agent-delegation, session-error-audit, skill-forge, project-journal, windows-shell-claude-code (beta: verified on one project only) |
| writing-and-scripts | readable-docs, windows-shell-dev |

Install (user scope): `claude plugin marketplace add <this folder>`, then `claude plugin install minecraft-modding@mamoru-plugins` and
`claude plugin install agent-workflow@mamoru-plugins`,
`claude plugin install writing-and-scripts@mamoru-plugins` (or `python refresh_local.py --install`).
Where a session reads the plugins from (checked 2026-10-12, Claude Code 2.1.294-2.1.295, Windows 11):
- `claude` in a terminal: the local install, a copy in `~/.claude/plugins/cache/mamoru-plugins/<plugin>/<commit SHA>/`, not this folder.
  After a change: commit, `python refresh_local.py`, new session (`/reload-plugins` does not switch a loaded plugin to the new version).
- Code tab of the Claude desktop app: the copies installed on the claude.ai account
  (`%APPDATA%/Claude/local-agent-mode-sessions/<org>/<user>/rpm/plugin_<id>/`, refreshed when the app starts); they shadow the local
  install of the same names. After a change: commit, push, update the plugins on claude.ai (Customize > Plugins), fully restart the app.

Check which version a session got by comparing the plugin folder byte by byte with the commit (`git show <sha>:<path> | cmp - <file>`).
On Windows `git hash-object` reports false differences for CRLF files (it applies core.autocrlf outside the repo).
Development journals of the skills (skill-forge) live in the port: `_port/skills-lab/<skill>/JOURNAL.md`.
