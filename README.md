# mamoru-claude-plugins

Local Claude Code marketplace `mamoru-plugins` (created 2026-10-12). Master copy of the skills since then: edit here, then mirror into
the DeceasedCraft port (`_port/tools/skills/`) and re-upload the zips to claude.ai.

| Plugin | Skills |
|---|---|
| minecraft-modding | kubejs-neoforge-2101, neoforge-mod-configs, modpack-port-neoforge, port-from-1182-pack, lostcities-biome-zones-mixin, minecraft-worldgen-density-1-21, tps-optimization-neoforge |
| agent-workflow | agent-delegation, session-error-audit, windows-shell-claude-code (beta: verified on one project only) |

Install (user scope): `claude plugin marketplace add <this folder>`, then `claude plugin install minecraft-modding@mamoru-plugins` and
`claude plugin install agent-workflow@mamoru-plugins`. Edits apply at the next session start (or /reload-plugins).
Development journals of the skills (skill-forge) live in the port: `_port/skills-lab/<skill>/JOURNAL.md`.
