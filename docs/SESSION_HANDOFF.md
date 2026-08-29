# Session handoff — Apocrysis v4

Last updated 2026-08-28 (evening). **Read this first in a fresh session.**

## Where things are

- **Working tree:** `projects/apocrysis/version-4/` (only v4 copy;
  `version-1..3/` are read-only clones).
- **Branch:** `version-4`, pushed to `github.com/dmccoy26/Apocrysis`.
  HEAD: `d5a517b` (or later).
- **Run:** `python3 apocrysis.py` (TUI) · `--classic` · `--slice`
  (tutorial) · `--test` · `--log` (session transcript).
- **Tests:** `python3 apocrysis.py --test` (unittest) **and**
  `.venv/bin/python -m pytest -q` from the Atlas repo root — **145
  pass + 40 subtests.** Run both; the unittest runner misses async-TUI
  thread-context bugs that pytest catches.
- **Harnesses:** `tools/balance_autoplay.py` (v4-aware bot + full
  report), `tools/mystery_solver.py`, `tools/slice_playtest.py`.

## What v4 is

An investigation game. Every expedition, `build_mystery()`
(`src/escape.py`) generates an escape mystery onto the map; you win by
reconstructing the "Escape Proof" (the four-state knowledge model) and
taking the route — not by reaching a Town Center. Playable end to end,
~86–88% bot survival, median ~44-turn wins.

## Key architecture

- **`src/knowledge.py`** — the four-object model (Fact / Evidence /
  Deduction / Hypothesis). States (Observed/Known/Suspected/Confirmed)
  are *derived* from discovered evidence; transitions automatic.
- **`src/escape.py`** — `MECHANISMS` (7 escape mechanisms, each with a
  story-family **classification**; see below), `choose_mechanism`
  (shuffle-bag + no back-to-back family), `build_mystery(game)`
  (assigns role sites to building tiles, carves one gap in the
  mountain ring, builds + `validate()`s the proof). `Mystery` carries
  `family/discovery/reasoning/resolution/confirmation`, plus
  `power_role`/`power_restored` (infrastructural) and
  `controls`/`correct_control` (experimental).
- **`src/mixins/mystery_mixin.py`** — the investigation loop.
  `mystery_arrive` auto-discovers all evidence at a site;
  `_mystery_obstacle_ready()` gates the obstacle (spatial: carry the
  item · infrastructural: `power_restored` · experimental:
  `obstacle_open`, set by `pull`); `mystery_pull_control` is the
  experimental verb; `_mystery_progress_flare` fires the `★` banners.
- **`src/tui.py`** — MOVE/TYPE roguelike input, the panels,
  `_objective_steps` (the bottom-right OBJECTIVES checklist,
  **generated from the mystery**), `_status_block` (OBJECTIVES +
  WARNINGS).
- `src/mixins/ui_mixin.py` — `announce_event` (the `═══` banners:
  `kind=lead/discovery/objective/warn`), `_action_bar`,
  `_render_map_lines` + `_mystery_site_mark` (the `!` markers),
  `print_help`.
- `src/mixins/slice_mixin.py` — the hand-authored tutorial.
- `src/campaign.py`, `src/playlog.py`. Win finalisation:
  `world_mixin.finish_expedition()`.

## The escape-story matrix (the current work)

Docs: `ESCAPE_STORY_LIBRARY.md` (10 families + ~24 scenarios),
`ESCAPE_STORY_SCHEMA.md` (v1 — vocabularies, `Mystery` fields,
invariants, §4 = which primitives generalise vs need extending),
`PLAYER_UNDERSTANDING.md` (the UX rules — read this).

**7 mechanisms, by family:**

| mechanism | family | player question |
|---|---|---|
| mountain_pass, rail_tunnel | spatial | where is the route? |
| service_route | infrastructural | (light — still a fetch) |
| boat_crossing | transportation | (light) |
| evac_corridor | sequential | (light) |
| **power_station** | **infrastructural** | what dependency makes this work? (gate ← hydro ← fuel; fuel applied at the generator, not the gate) |
| **dam_valves** | **experimental** | which of these controls is it? (the obvious one is never right; pulling it says why) |

`power_station` (`docs/MECHANISM_INFRASTRUCTURAL.md`) and `dam_valves`
(`docs/MECHANISM_EXPERIMENTAL.md`) are the two genuinely-different
grammars built so far.

## >> THE THREE-MYSTERY PLAYTEST (`69d78812` / `9ae794b9`): **PASSED 2026-08-28**

Three families played blind by a human, over two rounds (round 1
exposed an action-affordance gap, 5 fixes landed, round 2 confirmed):

- **A `mountain_pass` (spatial):** WON clean, no mechanic confusion.
- **B `power_station` (infrastructural):** WON.
- **C `dam_valves` (experimental):** solved via `pull` after the recap.

Each reads as a different *kind* of problem — the objective panel
alone distinguishes them (`got the forestry gate key` / `restored
power at the hydro station` / `worked out which control clears the
way`). **Apocrysis generates different problems, not different
scenery.** Tier-2 families are unblocked: `ea1d52be` informational,
`17f2a0ca` transportation, `5761c63f` time-pressure.

Balance is **FROZEN** (Atlas decision recorded) — do NOT tune combat
or resources off the bot. This playtest replaced another sweep.

**Harness ready:** `python3 tools/playtest_three.py shuffle` runs one
blind mystery; do it 3×. `A`/`B`/`C` force spatial/infrastructural/
experimental. Answer sheet + facilitator key:
`docs/PLAYTEST_three_mystery_ANSWERS.md`.

### Playtest round 1 (2026-08-28) — 2 of 3 runs, both non-spatial

Runs: B `power_station` (infra), C `dam_valves` (experimental). Both
players could *name the kind of problem* (comprehension ~passing) but
**could not execute the resolution action**, and died of attrition
while confused. One root cause: the two non-spatial families are the
only ones needing an explicit player action at a site (walk fuel back
to the power site / `pull` a control), and the game never signalled
that — every other interaction is passive (arrive = discovered).
Compounded by: revisiting a mystery site printed **nothing** (place
already named, evidence already revealed → dead silence, reads as
"empty"); and `t`/think hit a dead-end "doesn't point anywhere yet"
even with the next step fully determined.

**Fixes landed (all pushed, 145 tests + 40 subtests green):**
- `ae1a812` — revisiting a mystery site now reprints a terse recap
  (label + found evidence + action hint: `pull <name>` at the control
  room, "generator needs the {item} from {place}" at the hydro site).
- `8353a0d` — `t` synthesises the next step for infra/experimental
  instead of the dead-end line.
- `a4a9e8c` — objective panel `▸` hot line reads as an instruction
  (`▸ get the jerrycan of fuel to the hydro station`, `▸ try the
  controls one at a time - pull each`) not a past-tense achievement.

### Playtest round 2 (2026-08-28) — fixes confirmed

- **C `dam_valves`:** player read the revisit recap, typed `pull
  intake`, opened the way. **First experimental solve.** Died later to
  a zombie on the walk out (survival layer, frozen) — investigation
  bar PASSED.
- **B `power_station`:** **WON** (turn 60). Recap sent them for the
  jerrycan; walking back onto the hydro tile auto-restored power. But
  they didn't believe it worked — ~20 turns typing `fill generator` /
  `use fuel` / `pull gate` / `inspect panel`, and `t` still
  dead-ended (power on but route not yet found). Marginal pass.

Two more fixes for the B friction (pushed, 145+40 green):
- `6e18632` — `t` 4th case: power restored + route unknown → "the
  gate has power now, you still have to find where the route comes
  through."
- `55a6a65` — explicit `use`/`fill`/`refuel`/`pour`/`apply` verb at
  the power site (`mystery_apply_fix`): applies the fix like
  auto-on-arrival, or points forward if already done.

### Round 3 — A `mountain_pass` (spatial): **WON** turn 120

Clean. Got the key, objective panel tracked it, walked to the gate →
opened → confirmed → escaped. No mechanic confusion. 120 turns is a
big 18×18 map + wandering, not stuck-ness. **Gate passed.**

### Input rework (`893d0e1`)

MOVE/TYPE modes removed. The command box is always focused; arrow keys
move (priority bindings), everything else is typed + Enter. No more
wasd remap, no mode toggle/hint, `on_key` gone. Bare Enter at `>` is a
silent no-op. Numbered equip restored: `1`..`N` = weapon from `i`,
`W1`/`W2` = armor, straight from the `>` prompt.

### Eat/drink is a meal now (`01425cb`)

Playtest: "spent half the game eating." `eat`/`drink` consumed one
ration (+5) per turn vs −2/turn decay → constant nibbling. Now one
action eats up to 6 rations (+5 each, capped by the deficit), same
rations-per-point economy. Lake drink +4 → +15. Balance bot (400
games, seed 7): survival 85.5%→84.5% (noise; still 100% combat deaths,
zero starvation), median completion 46→42 turns. Frozen-balance line
held — economy unchanged, only the action tax removed.

**Still open (all minor / post-gate):** (a) cosmetic: power site keeps
its `!` after `power_restored` (`_mystery_site_mark`, should clear);
(b) start Tier-2 families. Balance stays FROZEN (this eat/drink change
was economy-neutral, verified on the bot — not a difficulty tune).

## Design rules (settled — don't relitigate)

1. **Four panels answer four questions:** Map=WHERE · Journal=WHAT I
   LEARNED · Think=WHAT I BELIEVE · Objectives=WHAT NEXT. If the player
   must *remember* a fact to operate the game, the UI remembers it for
   them. Investigation hard, interface easy.
2. **Most text is ambient; important info interrupts** via a `═══`
   banner (`★ NEW LEAD` / `★ NEW DISCOVERY` / `★ OBJECTIVE UPDATED` /
   `⚠`). Don't make repeated text more interesting — make it recede.
3. **Objective + banners say WHAT STATE / WHY, never HOW.** "Find the
   ranger station" — not "go to 11,4, take the red key, return."
4. **The schema is for us; the story is for the player.** `family:
   experimental` / `reasoning: revise` NEVER reaches the player.
5. **No back-to-back story family** across consecutive expeditions.
6. Earlier settled: `search` is optional (arrival auto-discovers); a
   found map reveals the whole valley; named places not generic
   buildings; `rest` costs 45 min; goal/task system removed.

## Open todos (`atlas todo list`)

- `ea1d52be` informational family · `17f2a0ca` transportation ·
  `5761c63f` time-pressure (Tier-2, after the playtest passes)
- `9779d49f` NEW DISCOVERY banner (per-fact, one per arrival)
- `c359b1bb` render the map at larger scale (small grid in a big panel)
- `7d6046d3` evidence↔escape direction validator · `a4a11df6` terrain
  affinity for the non-water mechs · `45ba6b67` hunting for food ·
  `91161490` backpack-full `[1] drop / [2] leave` prompt
- Deferred: `6cffc528` (tier-1 same-family scenarios — scenery only)

## Atlas

Model: `qwen2.5-coder-32b-instruct` (local). **Reliably authors** small
localised edits (a few fields, a string, a constant, a short block —
authored 6+ this session). **Cannot** touch a large method
(`generate_map`, `build_mystery`, `_render_map_lines`) without
rewriting the region. **New failure mode 2026-08-28:** a large data
block (a 21-key `MECHANISMS` dict entry) *hung* the model for ~30 min
producing zero bytes — had to `kill` the process. So: keep Atlas
requests to a handful of fields; hand-write anything bigger.

Workflow: `atlas request "<precise spec>" --file <f>` → `atlas review
<id>` (read the diff) → `atlas approve <id>` (auto-commits as "Atlas
repair: FEATURE_REQUEST (<id>)"). Approve runs the pytest suite 3×;
**trust it** — its rollbacks this session were catching real
regressions. Reproduce with `.venv/bin/python -m pytest -q` before
assuming a flake.

## Session history (for context; detail in git log + Claude memory)

Playtest-driven, 2026-08-28, ~40 commits on `version-4`:
`341ceca`..`325ed26` (playlog crashes, map declutter, growth,
archetypes, front-loaded-mystery fix, weapon nudge) →
`c1d1fad`..`e4eaa09` (event emphasis, weapon-break auto-swap, loot to
ground, building cap, revisit de-dup, escape bearing, marina water) →
`f4d42bc`..`d47ac3a` (the v4.1 UI pass: action bar, HUD blocks,
victory screen, STATUS block, water caps, escape-from-afar,
drink-from-water, starvation drain) → `49a0904`..`36cc08e` (roguelike
input, numbered inventory, mystery-generated objectives, named-place
markers) → `b89cb7a`..`8c0d3d4` (escape story schema v1,
PLAYER_UNDERSTANDING, typed banners) → `ce54c4a`..`d5a517b`
(power_station + dam_valves — the first two different grammars).

## Design docs

`ESCAPE_WORLD_DESIGN_ASSESSMENT.md` · `VERSION_4_BUILD_ORDER.md` ·
`PHASE0_KNOWLEDGE_MODEL.md` · `V3_ASSUMPTION_AUDIT.md` ·
`SLICE_PLAYTEST_MECHANICAL.md` · `BALANCE_BASELINE_2026-08-28.md`
(frozen sweep + regression re-run) · `ESCAPE_STORY_LIBRARY.md` ·
`ESCAPE_STORY_SCHEMA.md` · `PLAYER_UNDERSTANDING.md` ·
`MECHANISM_INFRASTRUCTURAL.md` · `MECHANISM_EXPERIMENTAL.md`.
