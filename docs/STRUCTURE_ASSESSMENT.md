# Structure assessment — do we need to restructure? (2026-08-29)

Question asked at the start of v5. Short answer: **no big restructure
now.** The one restructure that matters (`worlds/` seam) is already
Phase A step 0. The second one (`world_mixin` split) is forced by
Phase C's map-v2 and should ride with it, not before it. Two small
cleanups are worth doing now. Ripping out the mixin composition is not.

## The codebase, by the numbers

~13k LOC. Engine ~7k, tests ~2.5k, balance tooling ~1.7k.

| unit | LOC | verdict |
|---|---|---|
| `src/mixins/world_mixin.py` | 1137 | **overloaded** — 6 responsibilities (below) |
| `src/escape.py` | 917 | large but coherent (MECHANISMS + `build_mystery` + validate) |
| `src/tui.py` | 909 | large; it's a Textual UI, they run big; not urgent |
| `src/mixins/ui_mixin.py` | 842 | classic-mode rendering; fine |
| `src/mixins/mystery_mixin.py` | 664 | fine |
| `src/mixins/persistence_mixin.py` | 555 | fine; the class-var + profile round-trip pattern is load-bearing for Phase A |
| `src/tests/test_apocrysis.py` | 1990 | **one monolith** — split by concern |
| `src/slice_*` + `tools/slice_playtest.py` | ~670 | **dead scaffolding** — memory says "throwaway, not a game mode" |
| `src/knowledge.py` | 215 | small — and Phase A/§3.2 wants `Deduction`/competing-hypotheses *added* here, not restructured |

## The mixin god-object

`Apocrysis(PersistenceMixin, CombatMixin, WorldMixin, ObjectivesMixin,
UIMixin, ActionsMixin, KnowledgeMixin, MysteryMixin, SliceMixin)` —
~4k lines of behaviour on one `self`, no enforced boundary between
mixins (any mixin reads/writes any attribute).

**Leave it.** It's ugly, not dangerous. Reasons not to touch it now:

- Every mixin call site already goes through `self.io` — the one
  boundary that mattered (I/O) is already abstracted.
- The `World` seam (Phase A step 0) introduces the *next* real
  boundary — world-1 content vs engine — the right way: a passed-in
  object, not a mixin. That's the pattern to extend later if wanted.
- Churning the composition risks the **frozen balance** (combat /
  hunger-thirst / encounter / loot / map growth) for zero player-facing
  or roadmap gain.
- Atlas can't safely do a change this broad on this repo (see
  `ATLAS_CAPABILITY_LOG.md`), so it'd be all hand-work.

## `world_mixin.py` — the one that actually needs splitting

Six things in one file:

1. map generation — `generate_map()` **278 lines**
2. settlement generation — `_generate_settlement`, `_pick_town_position`
3. zone tagging — `_zone_for_terrain`, `_current_zone`
4. reachability / pathfinding — `_bfs_reachable`, `_carve_path`,
   `_ensure_reachable`, `_mystery_bfs_path`, `_force_boundary_ring`
5. zombie selection — `_select_zombie_for_encounter` (**frozen balance**)
6. per-turn runtime — `move_and_search()` **~220 lines**, `find_loot()`

Generation (1–4) and runtime (5–6) are different lifecycles.
**Roadmap Phase C (map-v2) rewrites 1, 2, 4 and part of 6 anyway** —
connectivity-graph generator, irregular masks, `_carve_escape_pass`
rewrite, graph-native pacing. Splitting now then rewriting in two
months is wasted motion. Do the split **as the first commit of Phase
C**: `src/worldgen/` (topology → terrain → embedding) vs a slimmed
`world_mixin` (movement, loot, encounters). Note it in the Phase C
plan; don't pull it forward.

## Do now (cheap, no balance risk)

1. **Split `test_apocrysis.py`** (1990 lines → `test_combat.py`,
   `test_world.py`, `test_persistence.py`, `test_objectives.py`,
   `test_campaign.py`). Faster runs, clearer failures, and every Phase
   A item adds tests — better to add them to a focused file. Pure move,
   `pytest` proves equivalence.
2. **Delete the slice scaffolding** — `src/slice_dam_road.py`,
   `src/mixins/slice_mixin.py`, `tools/slice_playtest.py`, the
   `slice_mode`/`SliceMixin` hooks in `game.py`, `tools/playtest_three`
   if slice-only. Memory: "throwaway experimental scaffolding, not a
   game mode." It served its purpose (the investigation-loop eval);
   it's now ~670 lines of confusion near code Phase A touches.
   **Needs owner sign-off** — confirm nothing still runs it.
3. **The `worlds/` seam** — already Phase A step 0. This *is* the
   restructure worth doing. `worlds/silence/` takes the encounter
   table, tile vocab, prose voice, `WorldFact` DAG, ending logic; the
   engine takes a `World`.

## Do NOT do now

- Un-mixin the `Apocrysis` class.
- Pre-split `world_mixin` ahead of Phase C.
- Touch `knowledge.py`'s shape (Phase A *adds* to it per §3.2).
- Break `escape.py` up — revisit only if it passes ~1200 lines.
- Any restructure routed through Atlas — the capability log shows it
  can't do multi-file structural work here safely yet.

## One-line answer for the roadmap

> Structure is adequate for Phases A–B. The `worlds/` seam (Phase A.0)
> and a `worldgen/` split (Phase C.0) are the only two restructures on
> the path; both are already implied by the roadmap. Everything else is
> cleanup, not restructure.
