# Session handoff — Apocrysis v4

Last updated 2026-08-28. **Read this first in a fresh session.**

## Where things are

- **Working tree:** `projects/apocrysis/version-4/` (relative to the
  Atlas repo root). This is the only v4 working copy. Siblings
  `version-1/`..`version-3/` are read-only clones of the old branches.
- **Branch:** `version-4`, pushed to `github.com/dmccoy26/Apocrysis`.
  Current HEAD: `325ed26` (or later).
- **Run it:** `python3 apocrysis.py` (TUI), `--classic` (plain loop),
  `--slice` (the Dam Service Road tutorial), `--test` (suite),
  `--log` (start a play log).
- **Tests:** `python3 apocrysis.py --test` or
  `pytest src/tests/` — 138 pass + 40 subtests.
- **Harnesses:** `tools/balance_autoplay.py` (v4-aware bot, full
  reports), `tools/mystery_solver.py` (BFS solvability),
  `tools/slice_playtest.py` (the tutorial's three-situation test).

## Status: v4 is playable end to end

The premise change is done. `python3 apocrysis.py` generates an
investigation mystery every expedition; you win by working out the
escape route and taking it, not by reaching the Town Center.

| Stage | State |
|---|---|
| 0 slice | done, played, GO given |
| 1 gates | done (`PHASE0_KNOWLEDGE_MODEL.md`, `V3_ASSUMPTION_AUDIT.md`) |
| 2A geometry | map ceiling, mountain boundary, landmarks, spawn fix. **Deferred: organic settlements, random player class, loot bands** |
| 2B persistence | done (zombie-tile clear, dropped-item persistence, abandonment states) |
| 2C knowledge | done (`src/knowledge.py`, journal/remember/inspect/look, save/load). 2C.3 primitive only |
| 2D zones | done (zone layer, contextual zombies + loot) |
| 3 harness | `balance_autoplay.py` is v4-aware. **Not done: investigation-aware bot that uses only player-visible info (`9b336876`); B½ budget telemetry** |
| 4 generator | done — `src/escape.py` (5 mechanisms, Escape Proof, validation), `src/mixins/mystery_mixin.py`, win-condition change, mountain-pass carve |
| 5 campaign | chapters + retrospective + goal-system removal. **Deferred: People layer (`44c1449a`), balance sweep** |
| 6 README | done (player-facing) |
| H harness realism | **not done** |

## Key architecture

- `src/knowledge.py` — the four-object mystery model
  (Fact / Evidence / Deduction / Hypothesis). The four states
  (Observed/Known/Suspected/Confirmed) are **derived** from discovered
  evidence; transitions are automatic (no `confirm` command).
- `src/escape.py` — `build_mystery(game)` picks a mechanism
  (shuffle-bag), assigns 4 role sites to real building tiles, carves
  one gap in the mountain boundary as the escape route, sets the
  obstacle tile + requirement item, builds and `validate()`s the
  Escape Proof (redundancy + reachability). Called from
  `world_mixin.generate_map()`. Each role site is a **named place**
  (`m.site_labels` / `cell['site_label']`).
- `src/mixins/mystery_mixin.py` — the investigation loop for generated
  games. `mystery_arrive` auto-discovers ALL evidence at a site (no
  `search` step); `clear`/walking-in-with-the-item opens the obstacle;
  `escape` wins iff hypothesis confirmed + obstacle open + on the
  escape tile.
- `src/mixins/slice_mixin.py` — the hand-authored tutorial, on the
  same shared knowledge model.
- `src/campaign.py` — chapter intros + the campaign retrospective.
- `src/playlog.py` — `log` command / `--log` session transcript.
- Win finalisation is shared: `world_mixin.finish_expedition()`.

## Playtesting-driven decisions this session (important — these are settled)

1. **`search` is not a required verb.** Arriving at a meaningful
   location auto-discovers everything there. `search` still exists as
   optional replay. The `(there may be more here...)` prompt is gone.
2. **A found map reveals the whole valley's geography** (terrain,
   buildings, settlements, the mountain-ring gap) — not just the Town
   Center. Zombies stay hidden until visited. `map_revealed` flag.
3. **Named places, not generic buildings.** The mystery's evidence
   refers to "the harbourmaster's shed" etc.; arriving there announces
   "This is the harbourmaster's shed." This is how a clue points at a
   destination without the player searching every building.
4. **Survival retuned down:** `ZOMBIE_MAP_DENSITY` 0.10→0.04, encounter
   0.30/0.50→0.10/0.20, non-slice games start with 8 food / 8 water /
   2 medicine, `find_loot` food/water finds are +2–4. Heavy/Armored
   zombies start at weight 0 and phase in.
5. **`rest` costs 45 min of expedition time + decay** (was free).
6. **UI shows `Day N  HH:MM  Phase  Turn K`** in both panels;
   `game.turns` counts non-info commands.
7. **Goal/task system removed** (V3_ASSUMPTION_AUDIT #1/#8). `journal`/
   `remember`/`inspect` replace it.

## Second fix batch — 2026-08-28 PM (8 commits, `341ceca`..`325ed26`)

Driven by two `--log` playtests + a 2000-game balance sweep
(`docs/BALANCE_BASELINE_2026-08-28.md` — the frozen pre-human-test
baseline; re-run that exact scenario as a regression check).

8. **Playlog crashes fixed** — death/win wrote to a closed file
   (`I/O operation on closed file`); `--log` in the TUI hit
   `call_from_thread` on the app thread. Paths are absolute now.
9. **Map decluttered** — the `*` border and the a1/b2 coordinate ruler
   are gone (they invited edge-following). `_render_map_lines` returns
   a bare glyph grid; the `^` mountain ring is still the visible edge.
10. **Map grows 3 tiles/expedition** (was 1 — imperceptible), cap 34.
11. **Identity prompt** reworded — "Enter your name (existing or new)"
    made players type the literal word "existing" and start a junk L1
    character; now "Continue a survivor by typing their exact name…".
12. **Terrain archetypes** — `MAP_ARCHETYPES` in constants; each
    expedition rolls mixed / deep_woods / flooded_basin /
    suburban_sprawl / open_country (seeded), biasing chunk terrain, one
    scene-setting line on the first turn. Fixes "every map feels the
    same".
13. **Front-loaded mystery fixed** — `E_closed_b` and `E_require_a`
    moved off the `route` site. The noticeboard used to reveal the
    whole fact chain in one step; now it gives F_ROUTE + F_OBSTACLE,
    `suspected` also needs F_CLOSED from the closed site, and you learn
    where the key is by bumping the gate. Four discovery beats, not one.
14. **Weapon nudge** — `encounter_zombie` names a stronger weapon
    sitting unused in the pack (playtester slogged 8 fights with a
    6-dmg tool while carrying a 15-dmg one).

## Third fix batch — 2026-08-28 late (playtest-driven, `c1d1fad`..`e4eaa09`)

Two more `--log` playtests (one death-by-confusion, one win, one death
to a Heavy zombie). Findings + fixes:

15. **`◆`/`⚠` event emphasis** (`announce_event`) for the 4 state
    changes + weapon-broken. Map now marks found leads (`!`/`+`).
16. **Weapon break is loud + auto-swaps** to best usable backpack
    weapon; "badly worn" threshold line; nudge treats broken = 0 dmg.
17. **Over-capacity loot drops to the ground** instead of vanishing
    (was: "drop something then take it" had nothing to take).
18. **Building cap 22% of chunks** — 3rd "too many buildings" report.
19. **Revisit text de-dup** — first visit full, revisits terse; "spot
    a building" stops after 3; district only on change.
20. **Escape gap has a bearing** — obstacle clue ends "...toward the
    south-east edge of the valley"; gap shows `!` on a found map.
    (Playtest: "every clue said north, escape was southwest.")
21. **Water where water belongs** — boat_crossing / service_route get
    a `terrain: water` tag; `_paint_terrain_near` puts water by the
    marina / dam. (Playtest: "a marina in the middle of a forest.")

## v4.1 UI/UX pass — mostly DONE (`f4d42bc`, `76819c3`)

Built by hand this session:
- Action bar replaces the ~25-line command dump (`_action_bar()`);
  `h` still prints the full list.
- Stats panel = labelled blocks: identity + XP, day-phase glyph
  (☀/☾/◐/☼) + clock + turn, EQUIPMENT, compact BACKPACK ("n/12
  weapons", identical items collapsed), one-line supplies.
- Map location + time header ("FOREST — ☀ DAY · 09:48").
- Log is an event feed: dim in-game HH:MM on one-line narrative.
- `announce_event` draws an ASCII box (`***` / `[!]`) — item /
  hypothesis / weapon-break moments are unmissable, TUI + classic.
- Boxed victory/defeat screen with an expedition stats block.
- Objective line persists "you have the {item} - get back to the
  blocked route" while carried.

**Later same session** (`5329af2`..`d47ac3a`):
- Bottom-right STATUS block: PROGRESS checklist (fact chain ticked) +
  WARNINGS (weapon / HP / starving / parched).
- Dry ranged weapon auto-swaps to a spare mid-fight.
- Water+swamp capped (was up to 63% of a map → 34%); zombies no longer
  spawn on water; `flooded_basin` reweighted.
- `escape` works from anywhere once the route is confirmed AND open
  (playtest: solved the mystery, starved on the trek back).
- `drink` from an adjacent water tile when the pack is empty.
- Hunger or thirst at 0 now drains 2 HP/turn each (was combat-only).
  600-game sweep: 86.5% win, unchanged envelope (bot manages
  resources; this bites a human who lets the pack hit 0).

**Later same session:**
- HUD colour hierarchy; numbered `i` inventory (equip by number);
  `t`=think; static grouped `print_help`; `═` heavy-rule banners.
- **Roguelike input mode** — MOVE (box unfocused, single keys act:
  wasd/arrows move, i/m/l/j/t/g/f/o/? act) vs TYPE (Enter/`:` →
  focused box, Esc cancels). `request_input` picks: `"> "`→MOVE, any
  dialog→TYPE. Map header shows a MOVE/TYPE chip.
- Objective removed from the top HUD. The bottom-right OBJECTIVES
  panel is now the player's **external memory, generated from THIS
  mystery** — "found an evacuation-route sign / learned you need a
  barricade key — kept at the police station / reached the police
  station / got the barricade key / ▸ opened the way / ☐ escaped".
  Site labels appear only once known; ▸ marks the actionable step.
- Map: a role site is marked `!` the moment you KNOW the fact that
  points to it (F_ROUTE→route, F_REQUIRE→require), through fog of war —
  not only after visiting. A named lead is a place on the map.
- balance harness updated (drink-from-water, starvation death bucket);
  2000-game regression: ~86% win, envelope intact (see
  BALANCE_BASELINE re-run section).

**The four player-facing questions** (design rule going forward):
WHERE AM I → map · WHAT HAVE I LEARNED → journal · WHAT DO I THINK →
think · WHAT NEXT → objectives panel. If the player must remember a
fact to operate the game, the UI remembers it for them. Investigation
hard, interface easy.

**Escape story library** — `docs/ESCAPE_STORY_LIBRARY.md` rewritten
around the 10-family reasoning matrix. Atlas todos, continuity-key
`escape-story-library`: `9ab1b420` (Story Library v1 schema — DO
FIRST, gates the rest), then `e2850fa5` / `c67cbd25` / `ea1d52be` /
`e0475adf` / `17f2a0ca` / `5761c63f`.

Still open: `c359b1bb` (render the map at larger scale), `7d6046d3`
(evidence-vs-escape direction validator), `a4a11df6` (terrain affinity
for the non-water mechanisms), `45ba6b67` (hunting for food),
`91161490` (backpack-full [1]/[2] prompt). `atlas todo list`.

## Open questions for the next playtest (the human's to answer)

**Primary (the whole world-grammar hypothesis):** with only the info a
new player gets, when the world hands a *named lead* ("the keys are at
a ranger station"), do you travel toward it — or revert to searching
every building? Run a generated mystery (not `--slice`) with `--log`.
The boat scenario is the sharpest version: find boat → no fuel → what
do you do?

- Was the combat death (armored zombie) **unavoidable** / a **bad
  decision** / a **system misunderstanding** / **weapon starvation** /
  **an appropriate risk**? (Balance sweep: 100% of deaths are combat,
  clustered early + at level 1; median best weapon = the 6-dmg
  starter. Five diagnoses → five different fixes. Don't tune until the
  human read is in.)
- Does the empty-building texture still read as "slot machine"?
- Should `search` be cut entirely?
- Is the front-loading actually fixed now (item 13), or does one site
  still hand over too much?

## Atlas

**Revised 2026-08-28 PM** (model now `qwen2.5-coder-32b-instruct`, LM
Studio JIT bug fixed). Atlas now **reliably authors** small, localized,
single-file edits — value/constant/string changes, short block inserts.
It authored 6 of the 8 fixes above. It still **cannot touch a large
method** (`generate_map`, `find_loot`) without rewriting the whole
region — those two hand-written.

Workflow: `atlas request "<precise spec>" --file <f>` → `atlas review
<id>` (read the diff every time) → `atlas approve <id>`. **Trust the
verify gate** — when it rolled two changes back this session it was
correctly catching a real `call_from_thread` regression, not flaking.
Reproduce a rollback with `.venv/bin/python -m pytest -q` from the
workspace root before assuming otherwise. Atlas auto-commits verified
workflows as "Atlas repair: FEATURE_REQUEST (<id>)".

`apocrysis.py --test` is a unittest runner and misses things pytest
catches (async-TUI thread-context bugs especially) — verify with both.

## Design docs

`ESCAPE_WORLD_DESIGN_ASSESSMENT.md` (the full architecture),
`VERSION_4_BUILD_ORDER.md` (the sequence + status table),
`PHASE0_KNOWLEDGE_MODEL.md`, `V3_ASSUMPTION_AUDIT.md`,
`SLICE_PLAYTEST_MECHANICAL.md`,
`BALANCE_BASELINE_2026-08-28.md` (frozen pre-human-test sweep).
