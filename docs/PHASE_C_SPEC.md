# Phase C — geography (spec)

**Draft — review before implementation.** Builds on the frozen Phase A
+ B spines. Written after a full read of `world_mixin.generate_map()`
and its helpers, `escape.py`'s carve/reachability helpers, and
`APOCRYSIS_ROADMAP.md` §5.

## The question Phase C answers

**What does geography *mean* in Apocrysis v5?** — not "how do we make a
prettier map." Geography is the thing that guarantees a mystery is
physically solvable, that the way out exists, that meaningful places
can connect, and (later) that story facts can attach to real places.

## The contracts (locked before any implementation)

### 1. `World` owns geography *vocabulary*, not generation.

The A.0 seam stands. `World` keeps `terrain_symbols`, `terrain_legend`,
`map_archetypes`, `prose`. Phase C may add **declarative** vocabulary
(e.g. a `geography` block: which terrains can form a perimeter, which
archetypes bias which shapes) but `World` **never** contains generation
code. It describes; `worldgen/` decides.

### 2. `worldgen/` owns generation mechanics.

| `src/worldgen/` owns | the engine keeps |
|---|---|
| the generation algorithm & pipeline | movement (`move_and_search`) |
| chunk terrain, archetype application, zones | combat / survival |
| the mountain-boundary / playable mask | map *state* mutation at runtime |
| settlement placement & shape | loot (`find_loot`) |
| the connectivity graph | player interaction |
| reachability guarantees & carving | zombie placement *(frozen balance)* |
| structural validation | the mystery model (`escape.py`) |

`worldgen/` produces a **base map**; `world_mixin.generate_map()`
becomes a thin orchestrator: `base = worldgen.generate(self)` →
`build_mystery(self, …)` → zombie placement → flavour. Mystery
generation and zombie placement stay in the engine — the first is
`escape.py`'s concern, the second is frozen balance.

### 3. Generation produces a graph, not merely a rectangle.

```
World geography vocabulary + archetype + chapter budget
        │
        ▼
   MapGenerator
        │
        ├── terrain / zones      (as today, chunk-clustered)
        ├── playable mask        (boundary; C.3: irregular)
        ├── spawn
        ├── settlements
        └── ConnectivityGraph    ← the new artefact
                nodes: spawn, exit-candidate(s), settlement centres,
                       (later) mystery-site slots
                edges: BFS distance, chokepoint flag, terrain cost
                │
                ▼
        guarantees, computed BEFORE the mystery is embedded:
          - every required destination is reachable from spawn
          - a critical path exists within the chapter's travel budget
          - settlements connect to the spawn component
```

The graph is what makes reachability a *property that was designed in*,
not one patched afterward by `_ensure_reachable`'s L-carve.

### 4. `WorldFact` is never aware of the generator.

A `WorldFact` describes truth (`"The exodus was organised."`). It has
no coordinates, no terrain, no `needs_geography`. The relationship
stays declarative and one-directional:

```
WorldFact  ──DiscoveryTemplate──▶  mechanism / role labels
                                        │
                                        ▼
                          (C.3) mechanism declares geography needs
                                        │
                                        ▼
                                generated geography
```

Geography never says "this tile exists because `DIS_ORGANISED` is
true." A `DiscoveryTemplate` (or the mechanism it names) may declare
`needs_perimeter="water"` etc. — that's a *mechanism* property, added
to `DiscoveryTemplate`/`MECHANISMS`, never to `WorldFact`.

### 5. Deterministic structural test suite — not visual tests.

- **Same seed → identical structure.** `generate` twice with seed X →
  byte-identical terrain grid, same spawn, same settlement centres,
  same graph (node set, edge set), same critical path.
- **N-seed sweep → 0 failures.** 1000 generated maps → 1000 valid
  connectivity graphs, every required destination reachable, no
  orphaned settlement, boundary intact.
- These run in CI (`pytest`), fast (no rendering), and are the
  acceptance gate for every Phase C step.

---

## Scope split — what ships this pass, what's gated

### Ships now (behaviour-preserving or additive, no balance risk)

- **C.1 — `worldgen/` extraction.** Move terrain/zone/boundary/spawn/
  settlement generation out of `world_mixin` into `src/worldgen/`
  behind a `MapGenerator`. **Byte-identical output** for every seed
  (proven by a snapshot test against the pre-refactor grid). The
  engine's `generate_map()` shrinks to an orchestrator.
- **C.2 — `ConnectivityGraph` as a guarantee layer.** Build the graph
  from the realised map; use it to *replace* the ad-hoc
  `_ensure_reachable` L-carve and the zombie-protection BFS with
  graph-derived reachability + a single carve that closes any real gap.
  Additive: same grid, same mysteries; the graph just makes the
  guarantee legible and testable.
- **C.4 — the deterministic structural test suite** (contract 5).

### Gated on balance review — a separate focused pass

- **C.3 — the inverted pipeline** (graph-*first* generation; irregular
  playable masks; `_carve_escape_pass` rewrite; story-aware terrain;
  `build_mystery` v2). Per the roadmap this "is a branch, not a patch"
  and changes what maps *feel* like. It risks the frozen balance
  (combat / hunger-thirst / trek length) in ways that need **human
  playtesting**, not just green tests. C.3 gets its own spec section
  and its own sign-off. **Do not implement C.3 in the same pass as
  C.1/C.2/C.4.**

The acceptance test *"the same generated valley can host two different
mysteries"* belongs to C.3 and is deferred with it.

---

## C.1 — `worldgen/` extraction (detail)

New package:

```
src/worldgen/
    __init__.py          # `from src.worldgen.generator import generate`
    terrain.py           # chunk terrain + archetype caps + zones + _pick_terrain
    boundary.py          # the mountain ring / playable mask
    settlements.py       # settlement placement + shape
    reachable.py         # BFS reachability + L-carve (shared with escape.py later)
    generator.py         # MapGenerator - orchestrates the above
```

`MapGenerator(game).generate()`:
- reads `game.rng`, `game.map_size`, `game.expeditions_completed`,
  `game.world.map_archetypes`
- writes `game.map`, `game.current_position`, `game.map_archetype`,
  `game.map_archetype_blurb`
- returns `town_center` (or `None`)
- **no** `self.io` calls, **no** mystery, **no** zombies

`world_mixin.generate_map()` after C.1:

```python
def generate_map(self):
    from src.worldgen import generate
    town_center = generate(self)
    self.mystery = build_mystery(self, target_fact=self._next_target())
    if self.mystery is not None:
        self.knowledge = self.mystery.knowledge
    self._place_abandonment_flavour()
    self._ensure_reachable(self.current_position, town_center)   # C.2 folds this in
    self._place_zombies(town_center)
    return self.map
```

Everything `worldgen` needs from `game` is read-only except the three
writes above. If a helper currently reads `self.level` /
`self.expeditions_completed`, it takes them as generator inputs.

**Reachability helpers** (`_bfs_reachable`, `_carve_path`,
`_mystery_bfs_path`, `escape._reachable_from`) are near-duplicates.
C.1 consolidates them into `worldgen/reachable.py`; `escape.py` imports
from there (engine→worldgen is a fine direction; worldgen must not
import `escape`).

## C.2 — `ConnectivityGraph` (detail)

`src/worldgen/graph.py`:

```python
@dataclass
class MapGraph:
    nodes: dict          # name -> (x, y)
    adj: dict            # name -> {name: distance}   (BFS over passable terrain)

    def reachable(self, a, b): -> bool
    def distance(self, a, b): -> int | None
    def unreachable_from(self, root): -> list[str]
    def critical_path(self, root, *musts): -> list[str] | None
    def chokepoints(self): -> list[(x,y)]   # tiles whose removal splits the graph
```

Built after the mystery is embedded (C.2), from: `spawn`, `exit`
(`mystery.escape_tile`), each `mystery.sites[role]`, each settlement
centre. `generate_map` then:
- `graph.unreachable_from("spawn")` must be empty for required nodes
  (mystery sites + real town centre); if not, one targeted carve, then
  re-check → `RuntimeError` on failure (same contract as today, but
  graph-driven and reported per-node)
- the zombie-protection set becomes "every tile on
  `graph.critical_path(spawn, *required)`" instead of N separate BFS
  walks

## C.4 — the structural test suite (detail)

`src/tests/test_worldgen_structure.py`:

- `test_same_seed_same_terrain` — two `Apocrysis(seed=S)` → identical
  `[[t['terrain'] for t in row] for row in map]`, identical spawn,
  identical settlement centres
- `test_same_seed_same_graph` — identical `MapGraph.nodes` and `.adj`
- `test_sweep_all_required_destinations_reachable` — 300+ seeds ×
  a few `expeditions_completed` tiers: `graph.unreachable_from("spawn")`
  contains no required node; boundary ring intact; ≥1 settlement
- `test_sweep_no_generation_exceptions` — the sweep raises nothing
- `test_worldgen_never_imports_engine` — AST check: nothing under
  `src/worldgen/` imports `src.mixins`, `src.game`, `src.escape`

## Guardrails (Atlas + Claude)

Do not: touch the frozen balance (zombie stats, densities, move costs,
hunger/thirst); change `WorldFact` / `knowledge.py`; implement C.3;
let `worldgen` import the engine; let `World` gain generation code.
Route the small leaf modules (`graph.py`, `reachable.py`) to Atlas
first; the `generator.py` extraction and the `world_mixin` slimming are
large-file / multi-file — hand-written, logged.

## Build order

C.0 spec (this) → **C.1** extraction (byte-identical) → **C.2** graph
guarantee layer → **C.4** structural suite → *freeze C.1–C.2–C.4* →
then a separate reviewed pass for **C.3**.
