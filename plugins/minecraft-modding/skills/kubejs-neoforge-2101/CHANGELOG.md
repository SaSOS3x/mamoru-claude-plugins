# Changelog: kubejs-neoforge-2101

What changed in this skill, when and why. New entries go to the end. The skill grew out of the DeceasedCraft 1.21.1 port; the
history of that work is in the port's `_port/HANDOFF.md`, which is not part of the plugin.

## 2026-10 | Created in the DeceasedCraft 1.21.1 port
What: KubeJS 2101 / Rhino traps, renamed methods, event timing, recipes and item changes collected while porting armor, melee,
recipes, hordes and config seeding.
Why: the same Rhino and KubeJS mistakes kept costing attempts; each fact here was checked on KubeJS 2101.7.2 build.377 and
Rhino 2101.2.8 build.91 (sources and offline Rhino runs).

## 2026-10-12 | v33: project state moved out
What: dated state of the port moved into the port's report `_port/reports/skills_moved_state_v33.md`.
Why: a separate review (Fable) found method and project state mixed in the skills; state belongs in the project journal.

## 2026-10-12 | v34: portability pass
What: no hard-coded paths of one PC, project examples labelled as examples, a Passport block. Removed text is kept in
`_port/reports/skills_removed_text_v34.md`.
Why: the skill was going into a plugin used by every project.

## 2026-10-12 | In the mamoru-plugins marketplace
What: the skill lives in the plugin minecraft-modding.
Why: the user's decision to keep all skills and tools in one marketplace shared by projects.

## 2026-10-12 | History moved from the Passport into this file
What: the "Changes" line of the Passport moved here; the Passport points to this file.
Why: the user's decision to keep a changelog in every skill with "why" as its main field. The file ships with the plugin but is
not loaded when the skill runs, so the history costs no tokens.
