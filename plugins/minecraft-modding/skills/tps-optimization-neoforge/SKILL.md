---
name: "tps-optimization-neoforge"
description: "Find and fix lag in a NeoForge 1.21.1 modpack, especially one with KubeJS 2101 scripts and many mobs (zombie / horde packs, Lost Cities, In Control, Enhanced AI): TPS drops, \"Can't keep up\", MSPT spikes, freezes, FPS drops with many mobs or hordes. Method: measure with spark (server and client), read logs/latest.log, then fix hot KubeJS scripts, Java mods and mixins, mod configs and the performance mod set. Use for \"лаги\", \"тпс упал\", \"фризы\", \"фпс просел\", \"тормозит в городе / на орде\", \"оптимизация\", \"разбери профиль\", \"спарк\", a spark link, slow chunk loading after a teleport, or a log full of Can't keep up."
---

# TPS / FPS optimization: KubeJS 2101 scripts + NeoForge 1.21.1 mods

Rule: measure first, change one thing, measure again. Code reading only gives candidates; a profile or a log
correlation decides. Related skills (same plugin, if installed): `kubejs-neoforge-2101` (script API), `neoforge-mod-configs`
(configs), `modpack-port-neoforge` (porting a pack: folders, converters). Mod facts below carry version stamps; they were
verified in the DeceasedCraft port (NeoForge 21.1.x, October 2026) - re-check them against your versions. Passages marked
"In the DeceasedCraft port" are examples of the method, not rules for every pack.

## 1. Measure
- **spark** (NeoForge 1.21.1 build in `mods/`):
  - `/spark tps`, `/spark health --upload` - overview (TPS, MSPT mean / 95th, CPU, memory); `/spark gc` - GC pauses.
  - Hitch hunting: `/spark profiler start --only-ticks-over 100 --timeout 300`, reproduce the lag (enter the
    building, wait for the horde, fly into new chunks), `/spark profiler stop` -> viewer link. Normal load:
    `/spark profiler start --timeout 120`. Allocation pressure: `--alloc`. Worker threads (chunk gen): `--thread *`.
  - Client FPS (render thread): `/sparkc profiler start --timeout 60` - the client-side spark command.
  - `/spark tickmonitor --threshold-tick 100` prints every slow tick in chat (timestamps for the log).
  - Read the tree by mod / package; KubeJS work shows as Rhino frames (`dev.latvian.mods.rhino.*`) under the event
    that called it (`EventHandler.post`, the NeoForge event class) - find the handler by the event, then bisect by
    disabling scripts.
  - **Reading a profile as data** (reliable numbers instead of clicking the viewer). Raw profile: the protobuf at
    `https://spark-usercontent.lucko.me/<id>`. Fetching `https://spark.lucko.me/<id>` without a browser returns the viewer
    page, not the data. Without own tools, open `https://spark.lucko.me/<id>?raw=1&full=true` in a browser - the viewer
    decodes the profile and shows JSON (plain `?raw=1` = metadata only); save it (Ctrl+S) or run JavaScript on the page.
    Shape: `threads[].children[]` is a FLAT node list (`className`, `methodName`, `times[]` per time window in ms,
    `childrenRefs[]` = indexes into the same list), `threads[].childrenRefs` = roots, `classSources` = class -> mod id
    (vanilla / Java classes missing), `timeWindowStatistics` = per-window TPS / MSPT / entities. inclusive = sum(times),
    self = inclusive - children; count a method once per stack (recursion / event re-entry); % of the thread's root total.
    In the DeceasedCraft port these steps are scripts (not part of the plugin): `python _port/tools/perf/spark_fetch.py <id>`
    downloads the protobuf and writes `_port/perf/profiles/<id>.json`, then `python _port/tools/perf/spark_summary.py <file>
    --grep <regex>` prints top self / inclusive methods, per mod, callers of a method.
  - `EventBus.post` with a big share is the SUM of all mod handlers of the events - split it by the frames below it.
  - A large SELF time in a tiny method = it is called in a loop by its parent (look at the callers), not slow itself.
- **NeoForge**: `/neoforge tps` (per dimension), `/neoforge entity list` (counts per type - look for hundreds of
  one mob, items, arrows, XP orbs).
- **Logs** (`logs/latest.log`): `Can't keep up! ... Running Nms or N ticks behind` lines; correlate each with the
  lines 0-3 s before it (advancements, chat messages like "entered a horde building", chunk / block entity errors,
  `/reload` = "Loaded N advancements" + datapack reload). False spikes: world load, "Saving and pausing game"
  (singleplayer pause; a big spike right after "Saving chunks for level ..." lines is usually Esc), first join;
  `/reload` takes ~6 s (expected).
  A log of more than ~10 MB per session = spam: every stack trace is built on the thread that logs it.
- **Reading `Can't keep up`** (MinecraftServer.runServer, MC 1.21.1): the number is the lag accumulated since the last
  warning, not a rate. It is printed only when the server is more than 1 s + 20 ticks behind (2 s at 20 TPS), at most once
  per 10 s + 100 ticks of schedule (300 ticks), and then the whole ticks of lag are written off
  (`nextTickTimeNanos += (lag / tickLength) * tickLength`). Do not read N ms as a rate (per minute or per tick): it is the
  backlog of the last ~300 ticks. Under sustained overload MSPT = wall time between two warnings / 300 = 50 + N / 300 ms,
  TPS = 1000 / MSPT. A single long tick is found in the lines 0-3 s before its warning; sustained overload builds up over the
  whole interval since the previous warning, so look at everything between the two. Example (Space Journey, 2026-10-14):
  warnings with N = 30-37 s were first read as 1-2 TPS; the real rate from their timestamps was 5.7-7.3 TPS.
- Separate server lag from client FPS: `[Server thread]` / TPS vs `[Render thread]` / FPS (a GPU / render problem
  is not a TPS problem).
- Memory: ask for the launcher's `-Xmx` and the RAM. Too small heap = frequent GC stutter, far too big = long pauses.
  Java 21: G1 (default) or Generational ZGC (`-XX:+UseZGC -XX:+ZGenerational`). There is no manual memory management
  in Java - the lever is the allocation rate (fewer temporary objects per tick), which `--alloc` shows.

## 2. Usual causes, in this order
1. Error / log spam per block, entity or tick (failed block entities in world generation, unknown registry ids in
   data, a script error inside a tick handler). Fix the data in the converter; log once.
2. Missing performance mods / configs that the ORIGINAL pack had (when the pack is a port): compare the mods folders
   first (a port often drops 20-30 of them silently) and the AI mod configs (a newer Enhanced AI with default config =
   every module on).
3. Mass spawns: horde buildings, hordes, In Control spawner bursts - N mobs x (spawn rules + AI goals + equipment +
   attribute changes + scripts on spawn) in one tick. Levers: mobs per batch / per tick, max mobs, spacing in time.
4. Pathfinding: many mobs with a target inside buildings (mining / climbing AI multiplies it), large follow range.
5. Chunk generation (Lost Cities, structure mods): worker threads + main thread chunk loading; pre-generate
   (Chunky) or lower view / simulation distance for tests.
6. Entity count growth: items / XP orbs / projectiles that never despawn, mobs that persist (name tags, picked up
   items, `persistenceRequired`).
7. Scripts and mixins on hot paths (below).

## 3. KubeJS 2101 scripts
- Tick handlers (`ServerEvents.tick`, `PlayerEvents.tick`, `LevelEvents.tick`) run 20x per second (x players).
  Throttle and return before any Java call: `if (event.server.tickCount % 20 != 0) return`; per player stagger
  `(player.tickCount + player.id) % 20`. Do the expensive part every N ticks, the cheap check every tick only if needed.
- No per-tick block / entity scans in JavaScript: one Java-side query (`level.getEntitiesOfClass(cls, aabb)`,
  `ChunkAccess.findBlocks(Predicates.in(stateSet), consumer)` - palette skips empty sections), queues with a budget
  per tick (N chunks per tick, retry later, drop after M tries); never walk a whole waiting list every tick (FIFO
  queues: one for new work, one for retries with a constant delay).
- `Java.loadClass` once at the top of the file (or lazily once), never inside a handler. Cache registry lookups and
  derived tables (JS objects / Java HashMap); prefer a Java `Predicate` over a JS lambda called per element.
- Hot events: `NativeEvents.onEvent` on `ItemAttributeModifierEvent` (fires per stack per attribute query, not
  cached by NeoForge), `LivingIncomingDamageEvent` (fires for every `hurt()`, even hits blocked by invulnerability
  frames) / `EntityEvents.beforeHurt` / `afterHurt` (`LivingDamageEvent.Pre` / `Post`, every applied hit),
  `EntityJoinLevelEvent` / `EntityEvents.spawned` (every arrow, item, XP orb, bullet, and every entity loaded with a
  chunk), `PlayerEvents.inventoryChanged`. Exit on "no player involved" with the first 2-3 calls; merge handlers of
  the same event; keep the body O(1).
- **Targeted handlers**: `EntityEvents.spawned('minecraft:zombie', cb)` per type. KubeJS skips building the event
  and entering Rhino for a type only when EVERY handler of the event is targeted - one untargeted handler anywhere
  makes all types pay (`TargetedEventHandler.hasListeners`). Register per type from a list or from the registry.
- Overloaded Java methods: call the hot ones by signature (`level['playSound(net.minecraft.world.entity.player.Player,double,double,double,net.minecraft.sounds.SoundEvent,net.minecraft.sounds.SoundSource,float,float)'](...)`) - no per-call
  overload search, no ambiguity.
- No allocation-heavy work per tick: string building, `console.*`, `Text` components, JSON, NBT reads / writes
  (`persistentData`). Keep state in JS maps keyed by UUID string; write NBT on change / logout.
- `server.runCommandSilent` parses with Brigadier every call - fine for a right click, not for a tick loop; prefer the
  mod API.
- Errors: try/catch in every `NativeEvents` handler (KubeJS does not catch them and the throw repeats every tick),
  count errors, log the first ones, disable the handler after ~20. A try/catch that swallows a TypeError per call is
  itself slow (~7-9 us per exception in Rhino vs ~0.2 us for the right check) and hides bugs.
- Offline check before shipping: run the script in the Rhino harness with stubs and count Java calls per tick.

### Rhino 2101.2.8 pitfalls (verified with the real jar)
- `const` anywhere inside a `try { }` block throws `TypeError: redeclaration of var X` on EVERY call (also inside an
  `if` within the try). `const` in a loop body keeps the FIRST iteration's value (silent). Closures created in
  `for (let i ...)` all see the last `i`. `let` in the loop body and `forEach` callbacks are fine; top-level `const`
  and `const` directly in a function body are fine. Scan all scripts with an acorn AST walker (const inside
  TryStatement.block or a loop body without a function boundary in between).
- `entity.getType()` / `entity.type` is `kjs$getType()` = the id String (`.getCategory()` throws); use `e.isMonster()`
  (= category not friendly), `e.living`, `e.player`. `level.dimension` is a property (ResourceLocation).
- Load order of scripts: higher `// priority:` first, then path A-Z case-insensitive. A script that must run after
  another one's handler of the same event needs a lower priority (e.g. `// priority: -100`).

## 4. Java mods and mixins
- Mixins on hot paths (entity tick, `getEntities`, render, lighting): HEAD inject with a cheap early return, no
  allocation, no logging; cache per tick when the same answer is asked many times.
- Event listeners: right bus and side, filter first; `receiveCanceled = true` only when needed.
- Diagnostics (StackWalker, exceptions for stack traces): once per source (`Set` of seen keys), never per call.
- Block entities: no tick work while idle; invalid saved block entity data in structure palettes -> strip it in the
  converter (it fails again in every chunk that uses the palette).
- MCreator mobs: look for `refreshDimensions()` in `baseTick` ("model scale" feature) - an `EntityEvent.Size` post per
  mob per tick; a mixin can skip it while the scale is unchanged (only if the profile shows it).
- Broken throttles in mod tick handlers: read the bytecode of a handler that shows up every tick. Example, Lost Radar 2.0.0
  `EventHandlers.onPlayerTickEvent`: `tickCounter` starts at 10 and is never reset -> `PlayerMapKnowledge.tick` (a
  Lost Cities `getChunkInfo` of the player's chunk) runs every tick per player (a measurable share of the tick in a city).
  Fix with a mixin (reset the counter / skip while the player stays in the same chunk). Check first whether your pack
  already carries such a fix.
- Lost Cities queries from OTHER mods are a hidden cost: `ILostCityInformation.getChunkInfo` -> `BuildingInfo` ->
  `City.getCityFactor` loops over the chunks in the city radius calling `City.isCityCenter` (a `new Random` per chunk,
  not cached). Callers seen: Lost Radar, In Control `city` rule checks (`LostCitySupport.isCity`), Lost Souls per tick.
  A per-chunk cache (pure function of seed + chunk + profile) is a safe mixin target.
- Per-tick `canUse()` that runs pathfinding (MCreator goals, e.g. Undead Revamped `TheheavyEntity$2`): throttle in a
  mixin (every N ticks) if the profile shows it.
- Prove mixins apply offline (Mixin + ASM verifier harness), then profile in game.
- Mixin checklist (verified cases, DeceasedCraft port, v32): a call into ANOTHER mod's code from a tick (its container
  capability, its registry) goes inside try / catch that logs once - an exception there crashes the server tick;
  `@Pseudo` + `remap = false` for mod targets, default require = 1 when silence would hide a broken feature; a machine
  output goes only into storage blocks (#c:chests / #c:barrels / explicit ids), never into hoppers / chutes / funnels / belts - they
  may be the input of the same machine and a rejected item jams them; read the target with `javap` over the full classpath
  (in the DeceasedCraft port: `_port/tools/jp.py <class>`, `--find <part>`, `--decompile <class>`) instead of guessing
  descriptors.

## 5. Config levers (verified mod facts)
- In Control 10.3.0 spawner (`spawner.json`, bytecode): every mob of a rule's `mob` list is tried separately with
  chance persecond x weight / sum of weights (no weights: 1 / list size); each try makes `attempts` position tries;
  `maxlocal` walks ALL entities of the level per attempt (O(entities x attempts)); spots are a random column within
  `maxdist` (3D) and a random height scanned down to a floor - use `minverticaldist` / `maxverticaldist` in caves.
  `spawn.json`: every spawn walks the rules - put `mob` / `dimension` filters in each rule, deny early. A phase like
  "day 0-1 deny" explains lag that starts on day 2.
- Enhanced AI (4.x): compare with the original pack's module set; per-mob modules (Pathfinding, Climbing, Custom /
  Better nearby targeting, Teleport to target, Miner, Pick up and throw, Riding, Parkour) multiply AI cost with mob
  count; Leaders adds banner mobs with x4 health; miner / climber / target switch chances raise pathfinding cost.
  Porting a 2.6.8 config: modules map by name (Pets -> Snow Golems), tags moved from `tags/entity_types/<name>` to
  `tags/entity_type/mobs/...` (`allow_climbing` -> `mobs/can_climb`, `can_be_miner` -> `mobs/can_mine`,
  `allow_target_switch` -> `mobs/targeting/allow_target_switch`), 4.x-only features off for parity. Per-mob data
  (insanelib): key `<module ns>:<feature name lower case, spaces -> _>/<name>` stored in NeoForge persistent data
  (`NeoForgeData.enhancedai.miner_mobs.time_to_break_multiplier`), filled on join with applyIfAbsent; set it from KubeJS
  with the mod's own `EAIData.apply(mob, value)` (`Java.loadClass(...MinerMobs).TIME_TO_BREAK_MULTIPLIER`) in a TARGETED
  `EntityEvents.spawned(id, ...)` - not `entity.persistentData` (KubeJS's own tag) and not `mergeNbt` (save + load of
  the whole mob). In the DeceasedCraft port: generator `_port/tools/eai_port.py`, report `_port/reports/enhancedai.md`.
- Lost Souls `lostsouls-server.toml`: `minMobs` / `maxMobs`, `spawnMaxNearby` / `spawnMaxNearbyRadius`,
  `serverTickTimeout` (time budget per tick), `checkValidSpawn`; building `haunted` chances in the pack's building data.
- The Hordes (horde size, interval, data `config/hordes`).
- Vanilla: simulation distance (server load) vs render distance (client).

## 6. Performance mods for NeoForge 1.21.1 (checked 2026-10-08; re-check versions)
Try one at a time with a profile: Lithium (official NeoForge build; test Create Aeronautics / Sable ships, fallback
`mixin.entity.collisions=false`), Immersive Optimization (entity / block entity tick rate by distance and visibility;
blacklist mobs that must keep full AI), Let Me Despawn (+ Almanac; mobs with picked-up items despawn), Entity
Culling (client), ModernFix (keep `dynamic_resources` / `dynamic_entity_renderers` off with KubeJS / Connector /
GeckoLib), FerriteCore, ImmediatelyFast (client; test with Sodium 0.8), AllTheLeaks. Alternatives / low: ServerCore
(activation range - not together with Immersive Optimization), ScalableLux, Clumps, BadOptimizations, Noisium.
Do not add: Async, Moonrise (crashes Sable), Radium / Canary / Starlight (replaced), Embeddium next to Sodium, Fabric
copies through Connector, Universal Optimization (switches collisions off, global spawn caps). MCreatorMemFix has
no 1.21.1 build and the 1.21.1 MCreator mods do not need it.

## 7. Report
MSPT mean / 95th and TPS before -> after, FPS before -> after, "Can't keep up" count per hour of play, spark top
frames (with the profile link), entity counts; what was changed (one change per test) and what is still an
assumption. Keep the profile links and findings in the project journal (see `project-journal`; in the DeceasedCraft port:
`_port/HANDOFF.md`), not in this skill.

## Project state is not kept here
Current profiles, measured numbers of one world and the order of steps belong in the project's journal and reports.
Read them before proposing a step, so as not to repeat one that is already done. In the DeceasedCraft port: `_port/reports/perf_plan.md`
(newest status at the top), `perf_spark_v*.md`, `perf_code_places.md`, `perf_mods.md`, `perf_kubejs_hotpaths.md`, and
`_port/HANDOFF.md` (Done / Queue).

## Паспорт
Создан: 2026-10 из этапа производительности порта DeceasedCraft на NeoForge 1.21.1 (профили spark, байткод модов); журнал порта -
`_port/skills-lab/` и `_port/HANDOFF.md` (в плагин не входят).
Проверен: факты о модах - по байткоду и профилям порта на NeoForge 21.1.x, даты и версии в разделах (раздел 6 - 2026-10-08).
В журнале нет записи о прогоне навыка целиком в чистом контексте по схеме skill-forge (шаг 5).
Границы: сборки без KubeJS и без большого числа мобов покрыты только разделами 1, 2, 4, 6; версии модов перепроверять.
История изменений: CHANGELOG.md в папке навыка (что, когда и почему).
