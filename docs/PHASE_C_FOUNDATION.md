# Phase C foundation — freeze / checkpoint

Tag: `v5-phase-c-foundation` → **rollback point** if C.3 is rejected.
251 tests + 100 subtests green. This is the first phase where C.3 will
*intentionally* break behavioural identity, so this doc is deliberately
firm about what's locked and what C.3 may move.

## 1. The C.0 contracts (locked)

1. `World` owns geography **vocabulary**, never generation code.
2. `worldgen/` owns generation mechanics. The engine keeps movement /
   combat / survival / loot / zombie placement / the mystery model.
3. Generation produces a **connectivity graph**, not merely a rectangle.
4. **`WorldFact` is never aware of the generator.** Geography needs are
   a *mechanism* property (`DiscoveryTemplate` / `MECHANISMS`), never a
   `WorldFact` property. Geography never says "this tile exists because
   fact X is true."
5. **Deterministic structural tests**, not visual ones.

## 2. C.1 — `worldgen/` extraction — byte-identity evidence

`src/worldgen/reachable.py` (Atlas, verbatim) + `generator.py`
(`MapGenerator` — the terrain/zone/boundary/spawn/settlement pipeline
**moved verbatim** from `world_mixin.generate_map`, `self.X` →
`self.g.X`). `world_mixin` 1130 → ~720 lines.

**Evidence:** `src/tests/fixtures/worldgen_golden.json` — 21 maps
captured from the pre-refactor pipeline (7 seeds × 3
`expeditions_completed` tiers). `TestWorldgenGolden` re-derives all 21
and asserts equality on: spawn, archetype, real town centre, the full
terrain grid, and the full zone grid. **0 mismatches.** The RNG stream
is untouched.

## 3. C.2 — `MapGraph` semantics (locked)

`src/worldgen/graph.py`: `MapGraph(grid, n, nodes)` — nodes →
BFS-distance edges.

| method | meaning |
|---|---|
| `reachable(a, b)` | is node `b` in node `a`'s passable component |
| `distance(a, b)` | shortest path length in tiles, or `None` |
| `unreachable_from(root)` | node names not reachable from `root` |
| `critical_path_tiles(root, *musts)` | union of shortest-path tiles `root`→each must — the corridor a player has to be able to walk |

`generate_map` builds the graph over `{spawn, town, exit, site_<role>…}`
after the mystery is embedded. An unreachable **required** node
(`exit`, `site_*`, real `town`) raises `RuntimeError` naming it. The
zombie-free protected corridor is
`graph.critical_path_tiles('spawn', *mystery_nodes)`.

`MapGraph` is a concept later systems can use *without knowing how the
map was generated*. That's the point.

## 4. C.4 — the invariant suite (`test_worldgen_structure.py`)

- golden fixture (§2)
- same seed → same terrain grid; same seed → same `MapGraph`
  (`nodes` + `adj`)
- `worldgen/*` never imports `src.mixins` / `src.game` / `src.escape`
  (AST)
- `MapGraph` unit tests over a hand-built map
- **300-seed × 5-tier sweep**: every mystery site, escape tile, and
  real town centre reachable from spawn; boundary ring intact bar the
  one carved gap; no generation exception

## 5. Known v1 baseline metrics

Measured by `tools/geo_compare.py` (400–500 games, exp tiers
0/3/6/9/12 for geometry, 1–5 for gameplay). **These are the envelope
C.3 must stay within.** Compare *distributions*, not just means.

### Geometry (v1)

| metric | mean | p10 | p50 | p90 |
|---|---|---|---|---|
| playable % of interior | 95.8 | 88.7 | 97.2 | 100 |
| largest region % | 100.0 | 100 | 100 | 100 |
| dead-end tiles | 2.6 | 0 | 0 | 9 |
| spawn→exit (tiles) | 25.3 | 12 | 28 | 34 |
| spawn→site (mean) | 13.4 | 6.8 | 12.5 | 22.2 |
| spawn→site (max) | 24.4 | 11 | 27 | 33 |
| critical-path tiles | 38.8 | 20 | 38 | 58 |
| spawn→town | 23.4 | 8 | 24 | 36 |
| maps with no mystery | **0 / 500** | | | |

### Gameplay (v1, scripted bot, exp tiers 1–5, n=400)

| metric | mean | p10 | p90 |
|---|---|---|---|
| turns / expedition | 56.0 | 9 | 84 |
| zombies defeated | 2.9 | 0 | 5 |
| fights | 3.4 | 1 | 6 |
| min health | 52.9 | 14 | 100 |
| buildings entered | 4.5 | 0 | 11 |
| **win rate** | **50 %** | | |

(Absolute win rate is low because the bot is deliberately run across
brutal tiers; the number that matters is the **v1↔v2 delta**.)

## 6. C.3 freedoms (what C.3 MAY change)

- the rectangular map boundary → an **irregular playable mask**
- terrain **shape** (peninsulas, basins, lobes, two-lobed valleys)
- trek length / buildings encountered / zombie exposure / loot
  opportunity / hunger-thirst pressure — **measure, do not assume**;
  they must stay within the §5 envelope (win rate especially)
- player *perception* of exploration — **human test required**

## 7. C.3 prohibitions (what C.3 may NOT change)

- seed determinism (same seed → same map)
- required-node reachability (exit, every mystery site, real town)
- town existence
- terrain vocabulary
- the critical-path concept
- combat / survival / investigation mechanics
- the frozen balance numbers
- the C.0 contracts (§1)
- `world_mixin.generate_map`'s public shape (orchestrator calling
  `worldgen` then `build_mystery` then zombies)

## 8. Rollback

`git checkout v5-phase-c-foundation` restores this exact state. C.3
lives behind `Apocrysis(mapgen="v1"|"v2")` (default `"v1"`), so it is
reversible without a rollback: flipping the default back to `"v1"` is a
one-line change.

## The C.3 accept/reject question

> Did C.3 make geography feel more like a real place, while preserving
> every §7 prohibition and staying inside the §5 gameplay envelope?
