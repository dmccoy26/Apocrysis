# Phase A.0 — the `World` seam (design, authored before implementation)

Locked by the project owner. Atlas **implements** this; it does not
design it. Grounded in a full read of the current code
(`docs/STRUCTURE_ASSESSMENT.md`).

## Success condition (the whole bar)

> The engine can run World 1 through an **explicit `World` boundary**,
> with **no gameplay change** and **no speculative story-engine
> architecture**.

A.0 is a **seam extraction**, not an architecture rewrite.

## The boundary

```
┌───────────────────────────── Apocrysis Engine ──────────────────────────────┐
│ combat · survival · movement · persistence · knowledge mechanics ·          │
│ mystery mechanics · UI / actions · map generation ALGORITHM                  │
│                                                                             │
│   "here is HOW encounters / mechanisms / terrain / prose work"               │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │  game.world : World   (frozen dataclass)
┌─────────────────────────────────▼───────────────────────────────────────────┐
│                            worlds/silence/                                   │
│   identity / metadata · tile vocabulary · encounter content · prose /        │
│   voice · map archetypes · world-specific constants                          │
│                                                                             │
│   "here is WHAT encounters / mechanisms / content EXIST for this world"      │
│                                                                             │
│   later (NOT A.0): WorldFact DAG · ending logic                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### The rule that defines the seam

```
GOOD   World → "there is this encounter / mechanism / content / prose"
       Engine → "here is how encounters / mechanisms / prose work"

BAD    World subclasses the engine · overrides combat · knows persistence ·
       knows UI internals · is a god-object in a trench coat
```

`World` is **data the engine reads**. It has no methods that mutate game
state, no knowledge of `Apocrysis`'s attributes, no imports from
`src/mixins/`.

## The `World` dataclass — minimal, not predictive

```python
# src/worlds/base.py
from dataclasses import dataclass, field

@dataclass(frozen=True)
class World:
    id: str                 # "silence"
    name: str               # "Apocrysis"
    description: str         # one paragraph, the opening framing

    # tile vocabulary — the terrain types this world uses and how they
    # render / read. Engine owns the generation algorithm; world owns
    # the words.
    terrain_symbols: dict           # {'forest': 'f', ...}   (was constants.TERRAIN_SYMBOLS)
    terrain_legend: str             # the map-key prose      (was constants.TERRAIN_LEGEND)

    # map archetypes — terrain-weight profiles + flavour blurb.
    # Engine rolls one and applies the weights; world supplies the set.
    map_archetypes: dict            # (was constants.MAP_ARCHETYPES)

    # prose / voice — strings the engine prints that are world-flavoured
    # rather than mechanical. A small dict now; grows as prose is pulled
    # out of the mixins in later phases.
    prose: dict = field(default_factory=dict)
    #   { "place_name_fallback": "THE VALLEY",
    #     "leave_verb": "leave the valley", ... }

    # encounter content — the zombie types this world's encounter roll
    # draws from, and their weights by campaign progress. The ENGINE
    # keeps _select_zombie_for_encounter()'s algorithm and the frozen
    # balance numbers; the world only says which roster + weight vectors
    # feed it. (May land in A.0 or be deferred one step — see execution
    # order step 4. If deferred, it does NOT block A.0.)
    encounters: dict = field(default_factory=dict)
```

**Do not add fields speculatively.** No `world_facts`, no `causal_model`,
no `ending`, no `factions` in A.0. They arrive with the phase that needs
them.

## What moves in A.0 (the *first* genuinely world-specific content)

Ranked by safety. A.0 moves **identity + `MAP_ARCHETYPES` + the terrain
vocabulary/legend**, and if it's clean, the encounter roster. Nothing
else.

| content | today | consumed at | risk |
|---|---|---|---|
| world identity (there is none — `"Apocrysis"` / `"THE VALLEY"` are string literals) | scattered literals | `tui.py:184`, `ui_mixin.py:533` etc. | none — additive |
| `MAP_ARCHETYPES` (5 weight profiles + blurbs) | `constants.py:82` | `world_mixin.generate_map()` :112, blurb → `ui_mixin.py:133` | **low** — weights copied verbatim, one call site |
| `TERRAIN_SYMBOLS` / `TERRAIN_LEGEND` | `constants.py:22,32` | `ui_mixin.py` render + legend | low — display only |
| encounter roster + weight vectors | inline in `_select_zombie_for_encounter()` | `world_mixin.py` | **medium** (frozen balance) — do only if extraction is literally lift-and-name; otherwise defer to A.0.1 |

## What does NOT move in A.0 (explicit guardrails for Atlas)

Atlas must **not**, as part of A.0:

- un-mixin `Apocrysis`
- redesign `knowledge.py` (beyond nothing — leave it entirely)
- introduce `MechanismFamily`
- split `world_mixin.py` into `worldgen/`
- rewrite or restructure `build_mystery()`
- move `MECHANISMS` (it's world content, but it's fused to
  `build_mystery`; extracting it is Phase A.2's `MechanismFamily` work)
- introduce `WorldFact` / `DiscoveryTemplate`
- implement the causal model or any story-engine runtime
- introduce a database / `WorldStore` (see `PHASE_A_DECISIONS.md` — DB
  is a Phase C+ consideration, explicitly not now)
- refactor any code not named in "what moves" above

If a change seems to require one of these, **stop and report** — it
means the seam was drawn wrong, not that the guardrail is wrong.

## Construction shape

```python
# default stays zero-friction for every existing call site
game = Apocrysis(name="Jess")                    # uses worlds.silence.SILENCE
game = Apocrysis(name="Jess", world=SILENCE)     # explicit
```

`Game.__init__` gains `world=None` → `self.world = world or
worlds.silence.SILENCE`. Every current caller keeps working unchanged.

## Execution order (discrete Atlas jobs — see `ATLAS_CAPABILITY_LOG.md`)

Each step: committed clean tree → `atlas request`/`todo` → `atlas
review` the diff → both suites green → commit. Log every attempt.

0. **Inspect** current repo state + the Phase A todo queue.
1. **Enumerate** every world-1 content dependency embedded in engine
   files (grep-level map: file:line → what). Output is a checklist.
2. **Create** `src/worlds/__init__.py`, `src/worlds/base.py` (`World`
   dataclass above), `src/worlds/silence/__init__.py`,
   `src/worlds/silence/world.py` (`SILENCE = World(...)` populated by
   *copying* current values). Nothing consumes it yet. Add
   `src/tests/test_worlds.py` — imports, `SILENCE.id == "silence"`,
   archetype weights equal `constants.MAP_ARCHETYPES`' (proves verbatim
   copy).
3. **Move** `MAP_ARCHETYPES` + `TERRAIN_SYMBOLS` + `TERRAIN_LEGEND`:
   `constants.py` keeps a re-export shim (`from src.worlds.silence.world
   import ...`) OR the consumers switch to `game.world` — Atlas picks
   the smaller diff, but the *values* must be identical.
4. **Move** the encounter roster **only if** it's a literal lift; else
   file A.0.1 and skip.
5. **Engine consumes `World`**: `Game.__init__(world=None)`;
   `generate_map()` reads `self.world.map_archetypes`; the "THE VALLEY"
   / "Apocrysis" literals read `self.world.name` /
   `self.world.prose[...]`. Behaviour identical for `silence`.
6. **Tests** prove: (a) World 1 identical — the existing 164 + 100 all
   still pass; (b) engine files no longer define those content dicts
   (grep assertion in `test_worlds.py`); (c) a second dummy `World`
   with different `terrain_symbols` / `map_archetypes` changes the
   rendered output without touching engine code.
7. **Run both**: `python3 apocrysis.py --test` AND `pytest -q`.
8. **Review the diff for architecture creep** — any change outside
   "what moves" is a defect.
9. **On a genuine Atlas capability gap**: stop that task, record it in
   the `atlas-self` workspace todo list (what was asked, what failed,
   the minimal repro), note it in `ATLAS_CAPABILITY_LOG.md`.
10. **Then** solve that specific gap by hand in Apocrysis — never let
    Atlas fake success.

## After A.0

`worlds/silence/` exists and the engine takes a `World`. Phase A.1+
(WorldFact, DiscoveryTemplate, World Investigation) build *on* the seam.
The DB question (`WorldStore` / SQLite) is revisited at Phase C when we
know what World 1's persistent truth/history/state actually looks like —
not before.
