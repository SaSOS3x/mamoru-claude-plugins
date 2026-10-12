# Changelog: minecraft-worldgen-density-1-21

What changed in this skill, when and why. New entries go to the end. The skill grew out of the DeceasedCraft 1.21.1 port; the
history of that work is in the port's `_port/HANDOFF.md`, which is not part of the plugin.

## 2026-10 | Created in the DeceasedCraft 1.21.1 port
What: wrapping density functions, reading noise_settings, TerraBlender regions, fitting land to the Lost Cities height window,
measuring heights offline with the game's own code.
Why: the terrain was too mountainous for Lost Cities, and changes had to be measured without starting the game.

## 2026-10-12 | v33: description with trigger phrases, project state moved out
What: the description got the phrases users actually say; dated port state moved into `_port/reports/skills_moved_state_v33.md`.
Why: a separate review (Fable) found that the description had no trigger phrases and that method and project state were mixed.

## 2026-10-12 | v34: portability pass
What: offline measuring section generalised, port examples labelled. Removed text: `_port/reports/skills_removed_text_v34.md`.
Why: the skill was going into a plugin for every project.

## 2026-10-12 | In the mamoru-plugins marketplace
What: the skill lives in the plugin minecraft-modding.
Why: the user's decision to keep all skills and tools in one marketplace shared by projects.
