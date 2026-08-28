# Session handoff — Apocrysis v4

Last updated 2026-08-28. **Read this first in a fresh session.**

## Where things are

- **Working tree:** `projects/apocrysis/version-4/` (relative to the
  Atlas repo root). This is the only v4 working copy. Siblings
  `version-1/`..`version-3/` are read-only clones of the old branches.
- **Branch:** `version-4`, pushed to `github.com/dmccoy26/Apocrysis`.
  Current HEAD: `62b5f5c` (or later).
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

## Open questions for the next playtest (the human's to answer)

- Does the mystery feel too front-loaded now that one site can surface
  most of the fact chain? (The route site often reveals F_CLOSED /
  F_ROUTE / F_OBSTACLE / F_REQUIRE at once — hypothesis is only
  "suspected" though, not confirmed.)
- Can a player, with only the info a new player gets, decide where to
  go next without visiting every building? Run the boat scenario:
  find boat → no fuel → what do you do?
- Does the empty-building texture still read as "slot machine"?
- Is combat lethality vs. investigation length right for a *human*
  (the bot solves ~85% solo; a human wanders more)?
- Should `search` be cut entirely?

## Atlas

**Do not route v4 work through Atlas.** Its generation pipeline
produced an unparseable patch on all 6 tasks tried this session
(35B MoE and 32B dense coder models both), including trivial ones.
This is a pipeline bug, not a model-size problem. Logged in the
apocrysis `.atlas/todo_list.json` (items `ad998cd0`, `ee762589`,
`16d98132`). Claude does the programming; Atlas can still be used for
verification/inspection if wanted.

## Design docs

`ESCAPE_WORLD_DESIGN_ASSESSMENT.md` (the full architecture),
`VERSION_4_BUILD_ORDER.md` (the sequence + status table),
`PHASE0_KNOWLEDGE_MODEL.md`, `V3_ASSUMPTION_AUDIT.md`,
`SLICE_PLAYTEST_MECHANICAL.md`.
