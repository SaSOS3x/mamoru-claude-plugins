# Changelog: neoforge-mod-configs

What changed in this skill, when and why. New entries go to the end. The skill grew out of the DeceasedCraft 1.21.1 port; the
history of that work is in the port's `_port/HANDOFF.md`, which is not part of the plugin.

## 2026-10 | Created in the DeceasedCraft 1.21.1 port
What: where each config type is read and when, defaultconfigs seeding, ModConfigSpec types, setting values from KubeJS, plus
verified blocks for Lost Cities, Lost Souls, The Hordes, Biomes O' Plenty and TerraBlender.
Why: configs of about 40 mods had to be ported and tuned, and several settings were silently ignored until the load order was
understood. Facts were checked against FancyModLoader 4.0.44, NeoForge 21.1 and the named mod versions.

## 2026-10-12 | v33: project state moved out
What: dated state of the port moved into the port's report `_port/reports/skills_moved_state_v33.md`.
Why: a separate review (Fable) found method and project state mixed in the skills.

## 2026-10-12 | v34: portability pass and Lost Cities profile precedence
What: pack script names labelled as examples, beta-pack facts labelled; the Lost Cities 8.4.4 profile order written down:
GUI choice, then the world's LostData, then the SERVER `selectedProfile`; `dimensionsWithProfiles` applies only when all three
are empty.
Why: the skill was going into a plugin for every project; the profile order had been guessed before and was settled by reading
the bytecode of lostcities-1.21-8.4.4.

## 2026-10-12 | In the mamoru-plugins marketplace
What: the skill lives in the plugin minecraft-modding.
Why: the user's decision to keep all skills and tools in one marketplace shared by projects.

## 2026-10-12 | History moved from the Passport into this file
What: the "Changes" line of the Passport moved here; the Passport points to this file.
Why: the user's decision to keep a changelog in every skill with "why" as its main field. The file ships with the plugin but is
not loaded when the skill runs.
