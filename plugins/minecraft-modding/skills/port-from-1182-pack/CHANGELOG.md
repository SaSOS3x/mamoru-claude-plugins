# Changelog: port-from-1182-pack

What changed in this skill, when and why. New entries go to the end. The skill grew out of the DeceasedCraft 1.21.1 port
(wastelands 2026-10-02, Abyss 2026-10-07); the history of that work is in the port's `_port/HANDOFF.md`, which is not part of
the plugin.

## 2026-10 | Created in the DeceasedCraft 1.21.1 port
What: porting content of a 1.18.2 Forge pack as data: Lost Cities 1.18 buildings and styles, KubeJS 1802 scripts, In Control /
FX Control configs, armorsets, BOP 1.18 biomes, custom dimensions, noise settings, portals.
Why: the wastelands and the Abyss dimension of DeceasedCraft 5.5.5 had to come back in the 1.21.1 port.

## 2026-10-12 | v33 and v34: description and method only
What: v33 gave the description the phrases users actually say and moved dated port state into
`_port/reports/skills_moved_state_v33.md`; the v34 second pass added an opening label, a "typical layout" bullet and labelled
examples. Removed text: `_port/reports/skills_removed_text_v34.md`.
Why: a separate review (Fable) found no trigger phrases in the description and method mixed with project state; the skill was
going into a plugin for every project.
Checked: the reworked text has not been run by a clean-context agent.

## 2026-10-12 | In the mamoru-plugins marketplace
What: the skill lives in the plugin minecraft-modding.
Why: the user's decision to keep all skills and tools in one marketplace shared by projects.
