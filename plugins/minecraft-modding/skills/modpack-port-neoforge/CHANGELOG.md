# Changelog: modpack-port-neoforge

What changed in this skill, when and why. New entries go to the end. The skill grew out of the DeceasedCraft 1.21.1 port; the
history of that work is in the port's `_port/HANDOFF.md`, which is not part of the plugin.

## 2026-10 | Created in the DeceasedCraft 1.21.1 port
What: the method and toolchain of porting a 1.20.1 Forge pack to 1.21.1 NeoForge: data-mod jar from the old pack's data,
Lost Cities buildings and palettes, loot, tags, FTB Quests chapters, replacing a mod that has no 1.21.1 version.
Why: the port repeated the same conversion steps chapter after chapter.

## 2026-10-12 | v33 and v34: method only
What: v33 moved the dated port state into `_port/reports/skills_moved_state_v33.md`; the v34 second pass rewrote the text as a
method (Cowork section and project state removed, a roles block added, examples labelled). Removed text:
`_port/reports/skills_removed_text_v34.md`.
Why: a separate review (Fable) found method and project state mixed; the skill was going into a plugin for every project.
Checked: the reworked text has not been run by a clean-context agent.

## 2026-10-12 | In the mamoru-plugins marketplace
What: the skill lives in the plugin minecraft-modding.
Why: the user's decision to keep all skills and tools in one marketplace shared by projects.

## 2026-10-12 | Folder of an_world.py
What: `an_world.py` is named with its folder `_port/tools/an_blocks/`.
Why: the plugin recheck found the script named without a path, so a reader could not find it.
