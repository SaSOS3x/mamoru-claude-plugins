# mamoru-claude-plugins

Claude Code plugin marketplace `mamoru-plugins` (created 2026-10-12). This folder is the master copy of the skills: every change
is made and committed here. The user pushes it to GitHub (SaSOS3x/mamoru-claude-plugins) and syncs the plugins on claude.ai
(Customize > Plugins). The Code tab of the Claude desktop app loads those claude.ai copies from
`%APPDATA%/Claude/local-agent-mode-sessions/<org>/<user>/rpm/plugin_<id>/`, refreshed when the app starts (a full restart, tray >
Quit; `/reload-plugins` does not change a version already loaded). There is no local install any more: it was removed on
2026-10-12 as a third copy that could silently serve an old version.

| Plugin | Skills |
|---|---|
| minecraft-modding | kubejs-neoforge-2101, neoforge-mod-configs, modpack-port-neoforge, port-from-1182-pack, lostcities-biome-zones-mixin, minecraft-worldgen-density-1-21, tps-optimization-neoforge |
| agent-workflow | agent-delegation, session-error-audit, skill-forge, project-journal, windows-shell-claude-code (beta: verified on one project only) |
| writing-and-scripts | readable-docs, windows-shell-dev |

Projects attach this folder to their sessions (the user adds it in the app), so every agent can read the newest skill files.
At the start of a task compare the loaded claude.ai copy with this folder: `git show HEAD:<path> | cmp - <file>` for its files
(on Windows `git hash-object` reports false differences for CRLF files). If the folder is newer, work from the skill in the folder:
read its SKILL.md and in commands replace the skill-folder variable with the folder of that SKILL.md (Claude Code substitutes it
only when it loads a skill). Tell the user that the claude.ai copy is behind; he syncs it.

Development journals of the skills (skill-forge) live in the port: `_port/skills-lab/<skill>/JOURNAL.md`.

Every skill folder has a `CHANGELOG.md` next to `SKILL.md`: what changed, when and, above all, why (new entries at the end).
It ships with the plugin but is not loaded when the skill runs (`claude plugin details` showed the same on-invoke cost with it).
Read it before changing a skill: a decision with a recorded reason is not reverted without a new argument.
Before every commit run `python check_skills.py`: it fails when a changed skill has no new CHANGELOG entry.

Where a script lives depends on where it repeats: in one project's work it lives in that project (`project-journal`, section
"Среда проекта"); needed by a skill and useful in any project, it lives in the skill's `scripts/`. No copies.
