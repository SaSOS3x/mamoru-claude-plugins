# mamoru-claude-plugins

[Русская версия](README.ru.md)

A Claude Code plugin marketplace named `mamoru-plugins`. It holds three plugins and seventeen skills. The skills grew out of real work: porting the DeceasedCraft zombie modpack to Minecraft 1.21.1 NeoForge, the Space Journey mod, large batch scripts for Windows, long projects with subagents and product searches on marketplaces. So what they record has been checked in practice. Every skill has a passport with the date and environment of its check, and whatever could not be verified is marked right in the text.

## Installation

In a terminal:

```bash
claude plugin marketplace add SaSOS3x/mamoru-claude-plugins
claude plugin install agent-workflow@mamoru-plugins
claude plugin install minecraft-modding@mamoru-plugins
claude plugin install writing-and-scripts@mamoru-plugins
```

Inside a session, the command `/plugin marketplace add SaSOS3x/mamoru-claude-plugins` and the `/plugin` panel do the same. You don't have to install everything: the plugins do not depend on each other. Skills sometimes refer to their neighbours, so they work better together, but each one still works on its own. On claude.ai, plugins are added under Customize > Plugins.

## How a skill is built

Each skill is a folder with a `SKILL.md` file. The file starts with a description: what the skill does and which words of the user should turn it on. Up front, Claude sees only these descriptions and loads the right skill by itself when a task fits, so you usually don't need to call skills by hand. The descriptions list real phrases in Russian and English, such as "лаги" (lag), "скрипт не работает" (the script doesn't work) or "на чём остановились" (where did we stop).

Inside `SKILL.md` you almost always find the same parts. First comes the order of steps, in the form that actually led to a result. Then come the traps, written as "symptom, cause, fix": they are the reason the skill exists. After that, a way to check the result, the limits of the skill and its passport. If a skill needs code, the code lives in the skill's `scripts/` folder and is called through the `CLAUDE_SKILL_DIR` variable, which Claude Code replaces with the real folder when it loads the skill. Next to `SKILL.md` lies `CHANGELOG.md` with the history of changes and their reasons. It ships with the plugin, but it is not loaded into context when the skill runs, so it costs no tokens.

## Contents

| Plugin | Skill | In short |
|---|---|---|
| agent-workflow | project-journal | running a project: tasks, a plan check, a journal entry after every step |
| | agent-delegation | which model to give a subagent, what goes into its prompt, how to check its report |
| | session-error-audit | counting failed tool calls in the session transcripts |
| | skill-forge | turning verified experience into a new skill |
| | windows-shell-claude-code (beta) | Git Bash, Python and JDK traps on Windows |
| | browse-like-user | looking up prices and delivery on websites like a regular visitor, without captchas |
| | test-mutations | proving that a check catches what it promises: an armed run and mutations |
| minecraft-modding | kubejs-neoforge-2101 | KubeJS scripts for 1.21.1 |
| | neoforge-mod-configs | mod configs: which file, when it is read, why it did not apply |
| | modpack-port-neoforge | porting a pack from 1.20.1 Forge -> 1.21.1 NeoForge with converters |
| | port-from-1182-pack | porting content from a 1.18.2 pack |
| | lostcities-biome-zones-mixin | biome zones placed by a rule and a city-free strip at their border |
| | minecraft-worldgen-density-1-21 | terrain: density functions, TerraBlender, measuring without starting the game |
| | tps-optimization-neoforge | finding and fixing lag |
| | neoforge-dev-experiments | autotests and experiments of your own mod in Gradle dev runs |
| writing-and-scripts | readable-docs | text rules for documents that people read, and the default layout of a student report in docx |
| | windows-shell-dev | large `.bat` and `.cmd` files with embedded PowerShell |

## The agent-workflow plugin

This plugin is about how Claude Code handles long work and learns from it. Four skills form one loop. project-journal keeps the tasks and the project journal, and agent-delegation hands parts of the work to subagents. Once per stage, session-error-audit shows which errors repeated, and skill-forge turns a verified fix into a skill so the error does not happen again. The fifth skill, windows-shell-claude-code, stands apart: it collects the Windows environment traps that came up in that same audit. The sixth skill, browse-like-user, also stands apart: it is about how the agent looks up data on other people's websites through a browser. The seventh skill, test-mutations, belongs to the loop again: before a check counts as green, it shows that the check can turn red.

### project-journal

Triggers when any multi-step work starts or continues: "let's start a project", "make the task list", "let's continue", "where did we stop", "what is done".

Long projects have two common problems. First, tasks are worded so that you cannot tell whether a task is done. Second, after a week nobody remembers what was tried and why it failed. The skill solves both with one short loop: write the tasks, check the plan, do a step, check the step, write it into the journal.

Everything lives in one project folder, `_project/` by default. It holds the task table `TASKS.md`, the journal `JOURNAL.md`, a `tools/` folder for scripts that repeat in this project's work, and briefs for agents. If the project already has its own journal or tracker, the skill works with it and does not start a second system. The path to this folder and the verified environment traps go into `CLAUDE.md`, because every agent receives it, subagents included, as long as the project folder is the session folder or lies above it (otherwise a `CLAUDE.md` in the session folder imports it with `@path`). If the session runs in the cloud and the project files live on the user's computer, a file counts as delivered only after it is checked on the computer (added 2026-10-17): copying from the cloud output folder can silently deliver the previous version, and `sync` does not prevent it.

Each task in the table has a "done when" criterion that is checked in practice, a way to check it, its dependencies and an "unknowns and risk" field. Every unknown becomes a separate research task with a concrete question, so it does not surface in the middle of the work. Before work starts, the plan is reviewed as if someone else had written it, with six questions. Is every requirement covered? Can every task be checked? Are the dependencies free of cycles? Does each task fit into one session? Is there a research task for every "don't know"? Does the plan respect what the user forbade or required?

After each step, an entry is appended to the journal with a strict heading, `## date | task | status | title`. The "Done" and "Check" fields are required, while "Problems", "To improve", "Failed", "Lesson" and "Next" are written when there is something to say. The phrase "it should work" is banned: either there is a check result, or the status is "awaiting check" with who will check it and how. If two attempts in a row did not move a task forward, the skill says to stop, write down what was tried, and change the approach or ask the user. At the start of a new session the skill compares the plugin versions with the marketplace folder, and the latest journal entries with reality: do the mentioned files exist, does the last check still pass. A problem that shows up a second time becomes a task or a skill candidate for skill-forge.

The section "Человек в контуре" (human in the loop, added 2026-10-15) covers the part of the check that only the user can do. Before launching anything the user will see or hear, the agent says what will open, how long it takes, whether the window may be touched and what to watch, and removes sound and first-run screens beforehand, calling removed only what it has checked. What the user reports from the screen is a test result: it goes into the journal and its cause is searched for. A task whose criterion is a human impression stays "awaiting check" until the user's verdict, and at milestones the agent waits for an answer.

The journal is compacted instead of retold (added 2026-10-15; since the same day skill journals in `skills-lab/` are compacted the same way). `scripts/journal_compact.py check` runs at the start of a session; past 400 lines, `compact --keep 15` moves every older entry verbatim to `JOURNAL-архив.md` and refreshes an index at the top of the journal, writing nothing unless the moved text is found in the archive byte for byte. The agent then writes a summary of at most 30 lines in which every line ends with a reference to its source entry; `verify` rejects lines without a valid reference, and a second agent checks the meaning of each line against the archive.

### agent-delegation

Triggers before any Agent, Workflow or SendMessage call and on phrases like "run it in parallel", "which model should I use", "we're out of limits", "check the agent's work".

The core idea is that the model is chosen not by how important the task is, but by two questions. Does the task have a ready path (a script, a spec, a list of questions), and what happens if the agent gets it wrong? If the path is given, Sonnet does as well as Opus. If there is no path and a mistake is hard to notice, you need Opus. For the simplest checks, such as "does the file exist", the skill suggests Haiku, but that has not been measured yet. The skill has a table of work types with model, effort and a note on what was confirmed in the DeceasedCraft port and what was only inferred. The model is set explicitly in every call: otherwise the agent inherits the session model, usually Opus, and the limit is gone in one run.

Work of 1-3 tool calls stays with the main session, because every agent has a fixed entry cost of about 60k tokens. The main session also keeps the conversation with the user, the decisions and everything irreversible: installing, backups, git. Agents get the work that needs a lot of reading, and small tasks from one spec are merged into one agent. The prompt carries the goal with a "done when" criterion, the user's decisions word for word with dates, paths to the relevant SKILL.md files, prohibitions and the answer format. The format must include an "errors along the way" item: without it the agent quietly works around a trap, and the next agent steps into it again.

The skill does not take an agent's report on trust. The reviewer is asked to find an error, not to confirm success, and along with the report gets the 5-12 key claims of the executor and the commands to check them. When an agent made a mistake, the same agent is continued through SendMessage and asked for a post-mortem, and an error that repeats is fixed at its source. If an agent departed from the user's decision, nobody fixes it silently in either direction: the options are shown to the user as one question, and the disputed part waits for the answer.

### session-error-audit

Triggers once per stage, after a big task or workflow, or when agents keep repeating the same mistakes: "check the session errors", "error audit", "compare with the last audit".

Agents step on the same rakes because the lesson is written where they never look. A subagent is only guaranteed to receive `CLAUDE.md`, and only from the session folder and the folders above it (the built-in Explore and Plan agents do not get it at start); it reads journals and skills only when the prompt names them. The audit answers three questions: what failed, is it written down where every agent will see it, and what should be fixed at the source.

Scripts do the counting first, without spending a single token. The script `scan_fail.py` takes the project folder, finds the session transcripts in `~/.claude/projects/`, reads the main session and every subagent, workflow agents included, and picks out the calls that failed. Then the script `classify.py` splits them into real failures, expected answers of checks (a grep with no matches, for example) and noise. Real failures are hard, with a nonzero exit code, or soft, when the exit code is 0 but the output holds a Traceback or No such file. Soft ones matter: in the first audit they were about 58% of the real failures, because chains with `| head` or `;` hide the error code. The script `show.py` prints the rows of a cluster so the classification can be checked by eye, and `compare.py` compares an audit with the previous one by failures per 1000 calls.

Then comes the judgment step. For each large cluster you check whether a rule was written down at all, and whether that record reaches subagents. Fixes go from most to least useful. The best is to remove the cause (an environment variable, a module, a small tool). Next comes a short block in `CLAUDE.md`, then an addition to an existing skill, and only at the end a new skill. None of this is applied without the user's consent, because these are instructions for every future session. The audit results are saved next to the project journal, so the next stage has something to compare with.

### skill-forge

Triggers when a task lacks a skill, when a procedure repeats a second time, when a fix was expensive or an existing skill failed, and on requests like "learn this", "make a skill out of this", "improve the skill".

The main rule is that a skill is written after the task is done and verified, and only from what was confirmed. Skills written in advance from guesses lowered results in measurements, because they confidently led the wrong way. Hence the order: look for an existing skill, do the task while keeping a journal, decide whether a skill is needed, draft it, test it and hand it to the user to save.

The skill's journal lives in `skills-lab/<name>/JOURNAL.md` at the root of this repository and has four kinds of entries: analysis, research, development and test. Each entry keeps verified facts apart from assumptions. A skill is worth creating when the task will repeat, goes badly without a hint, and has a verified solution. The state of a specific project is not a skill: it belongs in the project journal. Knowledge about a tool that exists in only one project also goes into that project, into its CLAUDE.md or the tool's README (added 2026-10-24). A skill found elsewhere is read as plain text, its scripts are not run until they have been reviewed, and installing it is the user's call. Once a journal grows past 400 lines, it is compacted with the same script as a project journal (added 2026-10-15).

There are three tests: the original task repeated by an executor with a clean context, two or three new tasks run with and without the skill, and, when an existing skill changes, a rerun of its earlier tests. Without subagents, `claude -p` in a copy of the trial folder gives a clean executor; when that is not available either, the baseline without the skill is not acted out, and the journal says it was not measured (added 2026-10-24). A skill is accepted if it is no worse on every task and better on at least one. The user saves the skill: in the Claude app through a `propose_skills` card, in a marketplace through a commit with a `CHANGELOG.md` entry. Before any change the CHANGELOG is read, and a decision with a recorded reason is not reverted without a new argument. The file `references/tool-call.md` explains how a skill calls its own script and where the plugin ends up on disk for each way of installing it.

### windows-shell-claude-code (beta)

Triggers at the start of work in a new project on Windows, before the first python, java or javap command, and on symptoms such as UnicodeEncodeError, garbled Cyrillic, `Argument list too long` or `class not found`.

In Claude Code on Windows the Bash tool is Git Bash, while `python`, `java` and `javap` are native Windows programs. The traps sit where the two meet, and the skill collected ten of them from an audit of failed commands in the DeceasedCraft project. Heredocs and `python -c` lose backslashes. Python on Windows cannot see `/c/...` paths. The console uses cp1251, and `python -I` turns off both the `PYTHON*` variables and the packages from `pip install --user`. The exit code of a chain with `| head` lies, `python3` turns out to be a Microsoft Store stub, and PATH and `JAVA_HOME` point to different JDKs. Finally, the command line has a limit of about 32k characters, and a long classpath does not fit into it.

The method is short. The first command runs `env_probe.py`, which shows which traps will fire on this particular PC. A script longer than five lines goes into a file, not onto the command line. Paths for python and java use the `C:/...` form. Results are judged by the output text and by whether the file exists, not by the exit code. The script `eol.py` counts line endings on bytes, because in Git Bash `grep -c $'\r'` prints 0 for a CRLF file. The script `classpath_jar.py` builds a tiny jar with a long `Class-Path` in its manifest, so `javap` can handle a classpath longer than the limit. The skill is marked beta: it was checked on one PC and one project, and there has been no with-and-without comparison on new tasks yet. Writing `.bat` and `.cmd` files is out of its scope, that is what windows-shell-dev is for.

### browse-like-user

Triggers when live data has to come from a website: prices, stock, delivery dates and delivery costs on marketplaces and in shops. It also triggers on signs of site protection ("Antibot Captcha", "Проверяем браузер", "Доступ ограничен: проблема с IP") and on a request to make the requests look less automated.

The skill grew out of a search for a bed on Wildberries, Ozon, Yandex Market and Avito. Ozon put a captcha on the whole site after a series of requests to its internal API followed by a direct jump to a product page, Avito and Megamarket closed access, and a bed listed at 11,950 ₽ came to 16,000 ₽ with delivery. So the skill covers two risks. The first is looking like a bot. The agent works through the page itself, keeps pauses, sends no fetch requests to the API and never solves a captcha itself but hands it to the user. The second is answering with the price a guest sees. The region is set through the site's own interface, the user's conditions are checked on the product cards, and the answer gives the price with its condition (with a bank card or without), the delivery and a link.

The skill was checked on two new tasks with and without it, and blind judges scored the answers. With the skill, the answer about a kettle on WB scored 12 against 7: the run without it used the site's "rating 4.7+" filter instead of the requested 4.5+ and missed cheaper options. For a robot vacuum on Ozon and Yandex Market the score was 11 to 10. No run hit a captcha, so the tests did not confirm the protection side. The skill slows work down: the tests made 2-6 times more tool calls.

### test-mutations

Triggers when a new autotest or scripted check is written or extended, before a check is reported green, and on "тест всегда зелёный" (the test is always green), "докажи тест" (prove the test), "мутации" (mutations) or "проверка слепая" (the check is blind).

A check that cannot fail is worse than no check: it gives confidence without ground. The skill grew out of the Space Journey mod, where blind checks turned up more than ten times, usually found only by reviews that cost millions of tokens. A seam check compared a chunk with itself, and "0 moved wrongly" meant nothing because vanilla does not check that in creative mode. The method has two parts. First the new check is armed: it runs on the old code or on a deliberately broken copy, and exactly its line must turn red. Then comes a mutation series: one change in the checked file per mutation, the line that must turn red named beforehand, a baseline on the same arguments, only new red counts, and the source is restored even after an interrupted run. The skill lists the signs of a blind check and what to do with a mutation that stays green: the mechanism may be duplicated, so that a second line of defence closes the hole, or the check may look at a consequence that comes later.

It was tested on the repeat of its original task, which passed at the first attempt, and on two new tasks with and without it: with the skill 9 against 7 and 9 against 8, from two blind judges each.

## The minecraft-modding plugin

Eight skills for Minecraft 1.21.1 NeoForge modpacks and mods. Seven of them use one worked example, the DeceasedCraft port from 1.20.1 Forge, and neoforge-dev-experiments grew out of the Space Journey mod. Still, the skills keep the method apart from the project's state: passages with port examples are labelled, and paths and work status live in the project's own journal. The port's scripts that the skills mention are not part of the plugin, so for another pack you write them again from the step descriptions. The exception is the spark profile scripts: since 2026-10-27 they live in the `scripts/` folder of tps-optimization-neoforge. Mod facts carry version numbers and are worth re-checking after a mod update. The skills point to each other: the port skill sends you to kubejs-neoforge-2101 for the script API, to neoforge-mod-configs for configs and to lostcities-biome-zones-mixin for city borders.

### kubejs-neoforge-2101

Triggers on any work in `kubejs/startup_scripts`, `server_scripts` and `client_scripts`, on porting scripts from 1.20.1, and on `[KubeJS Server]` or `[KubeJS Startup]` errors in the log. Phrases: "the script doesn't work", "recipe", "Cannot find function", "ambiguous".

From the outside, KubeJS on 1.21.1 looks like 1.20.1, but much of what silently worked on Forge now fails or, worse, runs and crashes a mod later. The skill names five sources of such errors. First, a JS number reaches Java as a `Double`, so `IntValue.set(5)` stores a Double and the mod crashes when it reads it; the fix is `Integer.valueOf`. Second, Rhino cannot pick a method overload when a string fits both `Path` and `File`, and the skill shows how to call an overload by its signature, `obj['name(type1,type2)'](...)`. Third, which classes `Java.loadClass` can reach under the KubeJS class filter. Fourth, a table of methods that KubeJS renamed or hid (`getStringUuid`, `entity.level`, `entity.damage`, the `level.dimension` property). Fifth, when each event fires and which mod configs are already loaded at that point.

The skill also covers file work through `JsonIO`, which has a trap: `write(path, null)` deletes the file. It describes item changes through `ItemEvents.modification`, custom tools, tiers and shields, and Create 6 recipes through `event.custom` without the KubeJS Create addon. The last section is about script hygiene: scripts of one type share one global scope, and the `priority` and `requires` headers control load order and conditions. The workflow goes like this. Names come from the KubeJS source on branch 2101, not from the wiki, which lags behind. Java calls are wrapped in `try/catch`, and each script writes one summary line to the log. Before the game the script runs offline on the real Rhino jar, and in the game the result is read in `logs/latest.log`.

### neoforge-mod-configs

Triggers when configs are edited or shipped with a pack, and when a setting, a profile or defaultconfigs did not apply: "configs didn't apply", "the profile didn't apply", "I changed the toml and nothing happened".

A config change can fail at four points: the wrong file is edited, the file is read at a different time, the value has the wrong Java type, or another source overrides it. The skill starts with a table of the four NeoForge 21.1 config types (STARTUP, CLIENT, COMMON, SERVER): which file is read and when. One key detail: since NeoForge 20.4, SERVER configs live in the shared `config/` folder rather than in the world folder, so a world's `serverconfig/` without any `*-server.toml` is normal. Another one: `defaultconfigs/` only seeds a missing file and never overrides anything. So "defaultconfigs don't work" almost always means that `config/<file>` existed first.

This leads to a pattern for modpacks: a KubeJS script deletes the managed `config/<file>` at game start, and NeoForge itself copies a fresh file from `defaultconfigs/` with the right types and at the right time. To debug "the config didn't apply" there is a check order based on `logs/debug.log`, and for setting values from scripts the skill explains what `ConfigValue.set()` does and does not do. At the end it collects mod facts checked against sources and bytecode. Among them are the order in which Lost Cities picks a profile, what `useChunkCheck` means in Lost Souls, how The Hordes moved infection from config to data, and the Biomes O' Plenty biome toggles.

### modpack-port-neoforge

Triggers when porting a modpack from 1.20.1 Forge to 1.21.1 NeoForge: "port a chapter", "rebuild the data jar", "the world crashes", "quests don't load", "a block is missing from the palette", "a mod was updated".

The main principle is that data is not ported by hand. Every change becomes a rule in a converter, and the output is rebuilt, so the next mod update reproduces everything again. Checks go against the block and item catalogs of the real 1.21.1 instance and against mod sources, and the game log has the final word. The skill describes the folder roles: the target instance, the old pack as a read-only reference and a work folder with backups and reports. Files are replaced only while the game is closed and after a backup. The working loop is: refresh the catalogs, change a rule, rebuild, run the validator, install, create a new world and read the log.

The largest part is the set of 1.20.1 -> 1.21.1 conversion rules, each with its reason. Datapack folders became singular, `forge:` tags turned into `c:`, and item NBT into data components. Data is packed into a data-mod jar on `lowcodefml` with `ordering="AFTER"`, blocks in Lost Cities palettes are mapped to the new ones, and quests are converted to FTB Quests 2101. Separate sections cover the FTB Quests text rules (why an ampersand followed by a space shows a red "Invalid formatting!") and replacing a mod that has no 1.21.1 version with your own code under its old ids. The "lessons that cost hours" section collects the non-obvious: a mod jar is not its registry, Lost Cities silently turns an unknown block into air or drops a whole palette, and one bad entry breaks a whole loot table.

### port-from-1182-pack

Triggers when content exists only in an older 1.18.2 pack: "port it from the old pack", "from 1.18.2", "wastelands", "dimension", "portal", "onEvent doesn't work".

The skill's first rule: before porting from 1.18.2, check the newer 1.20.1 pack, because it may hold a half-finished copy of the same content. After that, content is ported as data with a script. The skill has a table that maps KubeJS 1802 events (`onEvent('player.tick')` and others) to the 2101 API. It also lists the Lost Cities JSON keys that stay compatible from 1.18 to 1.21, gives rules for blocks and loot, and packs the result as a small data mod.

A separate part covers dimensions and world generation: how to rewrite 1.18.2 `noise.sampling` and `slide` as 1.21.1 density functions, and how to prove the conversion offline with the game's own loader. These two rules reproduce Mojang's 1.21.1 Nether final density exactly, which serves as a self-test. The skill also covers portals (a small own mod instead of Custom Portal API), In Control configs with renamed mobs, replacing FX Control with KubeJS, armorsets set bonuses and Biomes O' Plenty biome changes.

### lostcities-biome-zones-mixin

Triggers on "wasteland every 10000 blocks", "biome zones", "a city of the other style inside the wasteland", "the mixin didn't work", "mod only supports lostcities", "C2ME".

The skill solves a specific problem: placing zones of one biome by a rule, such as a wasteland in every cell of a grid, so that Lost Cities cities of two styles do not mix at the border. The cause of the mixing was found in the Lost Cities code. A city's style comes from the biome at its centre, while whether a chunk belongs to a city is decided per chunk. A city with a radius of up to 240 blocks, centred on one side of a border, reaches across it. The cure is a city-free strip along the border, at least as wide as the radius of the largest city.

Zones come from a pure function of the seed and coordinates. TerraBlender regions do not fit here: they are weighted patches, not a grid. The depth function is 1-Lipschitz, so the strip width is guaranteed mathematically. The skill is honest about the price of that guarantee: with default settings about a third of the world stays free of cities, and the user has to be told. Biomes are replaced by a mixin on `MultiNoiseBiomeSource.getNoiseBiome` at HEAD with re-entry into the method. The reason is that Biolith and TerraBlender also set the value at HEAD, so any RETURN injector becomes dead code. A second mixin sets the city chance to zero inside the strip.

Before the game, everything is checked offline: the zone maths, mixin application with the real Mixin library, the handler order together with every mod that hooks the same method, an ASM verifier and an end-to-end test. Dependency version ranges get their own section: `[8.4,)` does not accept the Lost Cities version `1.21-8.4.4` and stops the game even for an optional dependency. At the end there is a checklist for installing C2ME.

### minecraft-worldgen-density-1-21

Triggers on "too mountainous", "make the terrain flatter", "fewer mountains", "cities don't fit the terrain", "more of this biome", "measure without starting the game".

First the skill explains how overworld terrain is built in 1.21.1. There is a noise router of 15 functions, and the `offset`, `factor` and `jaggedness` splines are driven by `continents`, `erosion` and `ridges`. Surface height can be estimated simply as about 63.5 + 128·s. An important consequence follows: the biome source reads the same functions, so changing them moves biomes together with the terrain.

The skill says to change functions by wrapping them, not by editing a copy. The vanilla JSON goes under your own namespace, and `overworld/offset` is replaced by a function that references the original and, for example, compresses land above a chosen height. For "more of one biome" it describes TerraBlender regions. Changes show only in a new world.

The main practical part is measuring without starting the game. The classpath is built from the instance's `libraries/`, packs are loaded with the same `RegistryDataLoader` the game uses, and heights come from `getBaseHeight` at chunk corners. This way variants are compared on the same seeds before anything is installed. At the end the skill describes how Lost Cities decides where a city can go (the profile's height window) and how to fit the terrain to that window.

### tps-optimization-neoforge

Triggers on "lag", "TPS dropped", "freezes", "FPS dropped", "it lags during a horde", a spark profile link or a log full of `Can't keep up` lines.

The rule of the skill: measure first, change one thing, measure again. Reading code only gives candidates, and the profile decides. For measuring, the skill describes spark commands for server and client, catching individual long ticks, and reading a profile as data. The skill ships scripts for that: `spark_fetch.py` downloads a profile and decodes it to the viewer's JSON without a browser, `spark_summary.py` prints the top methods per thread and per mod, and `spark_chains.py` shows along the caller chain who keeps a thread waiting. Entities are counted with `/neoforge entity list`, and each `Can't keep up` line in the log is matched with what happened a few seconds before it.

Next come the usual causes in the order they are checked: from error spam in the log and performance mods lost in a port to mass spawns, pathfinding and chunk generation. For KubeJS it collects hot-path rules: throttling tick handlers, targeted event handlers per entity type, calling `Java.loadClass` once and never scanning blocks in JS every tick. There are also Rhino 2101.2.8 traps, for example a `const` inside `try` that fails on every call. For Java mods there are rules for mixins on hot paths and problems in specific mods found in their bytecode. At the end it collects config levers (In Control, Enhanced AI, Lost Souls, The Hordes) and a checked list of performance mods for 1.21.1, along with what not to install. The result goes into a report: MSPT, TPS and FPS before and after.

### neoforge-dev-experiments

Triggers on "dev-клиент из Gradle" (a dev client from Gradle), "автотест" (autotest), "тур" (a scripted tour), "runClient", "прогон висит" (the run hangs), "чёрный экран после выхода" (a black screen after leaving the world) or "dev-сервер не закрылся" (the dev server did not close).

It covers automated experiments and autotests of your own mod in NeoForge 1.21.1 dev runs from ModDevGradle: a run configuration and a folder per experiment, the folder settings before the first launch (options.txt without the accessibility screen and sound, fml.toml, server.properties), a world created from code, a scripted tour that ends by itself with a RESULT PASS or FAIL line, a limit on every wait, an exit watchdog, leftover JVMs and honest timing numbers. A reference file collects the vanilla 1.21.1 server and client facts that make such checks lie: a teleport from the player's tick is rolled back, "moved wrongly" is not checked in creative mode, the client gets fewer heightmaps than the server. Facts that belong to other skills stay there and are linked: the stop-time hang and the watchdog in tps-optimization-neoforge, Distant Horizons in neoforge-mod-configs, comparing terrain with real chunks in minecraft-worldgen-density-1-21.

The skill grew out of the Space Journey mod, which has 14 run folders and a tour for every stage. The repeat of its original task passed fully after section 7 got two concrete commands (how to see the exit code and how to find leftover java processes). On two new tasks the score with the skill was 8 against 5-6 and 9 against 3.

## The writing-and-scripts plugin

Two skills unrelated to Minecraft: one about texts for people, the other about large Windows scripts.

### readable-docs

Triggers when a document for a human reader is written or checked in any format (a report, an instruction, an article, a README), and on requests like "simplify", "rewrite it simpler", "remove the bureaucratese", "remove the dashes", "check the text".

There are four rules: lists take no more than 30-40% of the text, a plain hyphen replaces the em and en dash, the finished text is checked again, and complex phrasing is replaced with simple phrasing. The skill explains each rule. A list tears reasoning into pieces and hides the links between thoughts, so causes and conclusions are written as connected prose. Dashes come back on their own through pandoc, quotations, docx list markers and Word's autocorrect, so they are searched for in the finished file, not in the draft. For simplifying, there is a table of plain replacements for bureaucratic Russian phrases, such as "осуществляет проверку" -> "проверяет" (performs a check -> checks).

The check runs in two passes. The first is the script `check_text.py`. It reads docx, md and txt (other formats through pandoc or pdftotext), measures the share of lists and finds dashes, long sentences and bureaucratic phrases. When a hard rule is broken, it exits with code 1. Its list of heavy phrases is Russian, so for an English text that part of the report does not apply. The second pass is about meaning: words, terms, coherence, numbers and references inside the document. The user gets one line with the result of the check. This README was written and checked by the rules of this skill.

For a docx built by a program there is a second script, `fix_proofing.py` (added 2026-10-17). Word picks the spelling dictionary by the language of each text run, so when the whole text is marked Russian it underlines Windows, program names and terms such as «гипервизор» (hypervisor). The script splits the runs by word across the whole document, lists, tables and headers included. Latin words, Russian codes and abbreviations, and terms from the term lists get the "do not check spelling" mark, and the rest of the Russian text is checked by Word as usual. Words missing from the hunspell ru_RU dictionary are not exempted automatically but listed for review, because to a dictionary a typo and a correct term look the same. Common IT terms live in `terms_ru_it.txt`, project terms are passed with `--terms`. Runs where checking was already switched off (code listings, commands, quotations) are left as they are: a quotation is not edited, even if it has a typo. The script needs the lxml and spylls packages and downloads the dictionary itself. The method was checked in Word on a report and on a test document with lists and a table: only the deliberate typo stayed underlined.

For a student report in docx the skill records the default layout (added 2026-10-17). A list item is laid out like a normal paragraph: the hyphen sits at the 1.25 cm first-line indent, and wrapped lines start at the left margin. A figure, a code listing and a table with their captions are separated from the text by one blank line above and below. The same blank line goes before a level-one heading, and paragraph spacing before and after is 0. If the course guidelines or the user ask for something else, the skill follows them. The script `check_layout.py` checks these rules in the finished file and shows where they are broken, with examples.

Two more rules were added on 2026-10-23 after a report on a project network model. Arrow characters are not used in the text: an arrow is typed as "->", and in docx its hyphen is non-breaking, so the line never wraps in the middle of the arrow. In a student report, everything with variables, indices and coefficients, and every equation or calculation with them, goes in as a Word equation (OMML) rather than text with subscripts, table headers included. The skill shows how to build equations in docx-js, and the script `omml.py` turns a short linear notation into an equation for Python builds. `check_text.py` treats arrow characters as a hard rule, and `check_layout.py` finds formulas typed as text, in tables too.

### windows-shell-dev

Triggers on any large `.bat` or `.cmd`: optimizers, tweakers, ADB and registry front-ends, installers, menu-driven scripts. It also fires on a plain "fix my script", "debug my .bat" or "add a feature to my tool".

The skill is built for scripts of hundreds or thousands of lines, where a bug hides on one menu path and fires after a side effect has already happened. That is why it opens with non-negotiable habits. The file's bytes are kept as they are: CRLF, no BOM, the original encoding. The analyzer runs after every edit. New code follows the script's own style, changes are reversible and idempotent, an unconditional `[OK]` is never printed, and a `set /p` question fits on one console line. A separate section lists things a model usually gets wrong with confidence, for example that with duplicate labels `goto` jumps to the first one.

A working pass goes in a loop: read the script, take a baseline analyzer report, fix bugs with the smallest edits, add the feature in the script's style, validate again, and package with a README and a change note. The skill ships its own tools for this.

| Script | What it does |
|---|---|
| `analyze_batch.py` | static analysis: `goto` and `call` targets, block parentheses (a character-level model of how cmd parses), delayed expansion of `!`, redirects, line endings |
| `menuscan.py` | compares the items a `set /p` menu prints with the branches that handle them |
| `crlf_edit.py` | exact-match edits that keep CRLF, BOM and encoding |
| `extract_ps.py`, `Validate-Embedded.ps1` | checks for embedded PowerShell: a fast lint and the real PowerShell parser |
| `setup_pwsh.sh` | installs PowerShell in a Linux sandbox |
| `extract_baseline.py` | a sync gate for the DCX neo project only |

A catalog of 54 cmd pitfalls, each with symptom, cause and fix, lives in `references/pitfalls.md`. The analyzer catches some of them, and the rest serve as review rules. The scripts have 12 regression tests of their own in `tests/`. The skill also explains how to build a PowerShell test harness and how to test the tests with mutations: break the code in a copy and make sure the test fails.

## Development and maintenance

This section is for the author and for agents that edit the skills. The marketplace was created on 2026-10-12, and this repository is the master copy of the skills: every change is made and committed here. The user pushes it to GitHub and syncs the plugins on claude.ai (Customize > Plugins). The Code tab of the Claude desktop app loads the claude.ai copies from `%LOCALAPPDATA%/Claude-Data/claude_<account-id>/rpm/<org>/<user>/plugin_<plugin-id>/` and refreshes them when the app starts. That takes a full restart through tray > Quit, because `/reload-plugins` does not change a version that is already loaded. The path changes with the app, so the safest source is the "Base directory for this skill" line a session prints when it loads a skill. Earlier paths: `%APPDATA%/Claude/rpm/<org>/<user>/plugin_<plugin-id>/`, and before 2026-10-15 `%APPDATA%/Claude/local-agent-mode-sessions/<org>/<user>/rpm/plugin_<plugin-id>/`. Judging by the date of the marker file `.user-data-left.claude_<account-id>` left in `%APPDATA%/Claude`, the app moved its data around 2026-10-20. There is no local install any more: it was removed on 2026-10-12 as a third copy that could silently serve an old version. Versions in `plugin.json` are left out on purpose: the commit SHA serves as the version, and every push is an update.

Projects attach this folder to their sessions (the user adds it in the app), so every agent can read the newest skill files. At the start of a task the loaded claude.ai copy is compared with this folder using `git show HEAD:<path> | cmp - <file>` for the skill's files. On Windows `git hash-object` reports false differences for CRLF files, so it is no good for this check. If the folder is newer, work from the skill in the folder: the agent reads its SKILL.md and, in commands, replaces the skill-folder variable with the folder of that SKILL.md itself. Claude Code fills that variable in only when it loads a skill. Tell the user that the claude.ai copy is behind; he syncs it.

Since 2026-10-15 the development journals of the skills (skill-forge) live in this repository, in `skills-lab/<skill>/` at the root. That way every project this folder is attached to can read them, and they are kept on GitHub next to the skills without going into the plugins: the marketplace takes plugins only from `plugins/`. `skills-lab/README.md` explains the layout and how to compact a journal. The same day the journals kept in the projects moved here: from the DeceasedCraft port (agent-delegation, session-error-audit, windows-shell-claude-code and the v33 and v34 proposal material) and from Space Journey (project-journal and the change analysis `a1-2026-10-15.md`). Older CHANGELOG entries still name the old paths `_port/skills-lab/...` and `_project/skills-lab/...`: these are the same files, moved without edits. A CHANGELOG entry names the journal or analysis file that holds its evidence; older entries may not. Every skill folder has a `CHANGELOG.md` next to `SKILL.md`: what changed, when and, above all, why. New entries go at the end. The file ships with the plugin but is not loaded when the skill runs (`claude plugin details` showed the same on-invoke cost with it). Read it before changing a skill: a decision with a recorded reason is not reverted without a new argument. Before every commit run `python check_skills.py`: it fails when a changed skill has no new CHANGELOG entry.

Where a script lives depends on where it repeats. If it repeats in the work of one project, it lives in that project (the project-journal skill, section "Среда проекта", the project environment). If a skill needs it and it is useful in any project, it lives in the skill's `scripts/`. No copies.
