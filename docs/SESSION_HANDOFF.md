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

## >> THE IMMEDIATE NEXT STEP: `69d78812` — the three-mystery playtest

Three families now exist (spatial, infrastructural, experimental), so
the **phase gate is runnable**. Hand a human one generated mystery of
each family, **blind** (don't say which). Per run, the 7-question
table in `PLAYER_UNDERSTANDING.md` ("the three-mystery test"), then
the gold question: *"what did you think the game wanted you to figure
out?"* Three answers like "A: find something / B: figure out what
powers something / C: figure out which control matters" = pass →
the investigation game exists. If confused about the *kind* of
problem, the banners or objective phrasing aren't working yet.

Balance is **FROZEN** (Atlas decision recorded) — do NOT tune combat
or resources off the bot. This playtest replaces another sweep.

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
