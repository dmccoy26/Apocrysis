# Escape Story schema (v1)

Deliverable of todo `9ab1b420`. Defines what every generated escape
mystery declares, which of the current knowledge-model primitives
generalise, and the generation-order change the matrix needs.
Companion to `ESCAPE_STORY_LIBRARY.md` (the scenario catalogue).

## 1. The declaration

Each `MECHANISMS` entry in `src/escape.py` carries a **classification**
alongside its prose. Every value comes from a closed vocabulary
(module-level tuples), so a new mechanism can't invent an axis.

```python
"family":       one of STORY_FAMILIES        # the reasoning the player does
"discovery":    one of DISCOVERY_PATTERNS     # how the first thread appears
"reasoning":    one of REASONING_PATTERNS     # the core mental operation
"resolution":   one of RESOLUTION_PATTERNS    # the act that opens the way
"confirmation": one of CONFIRMATION_PATTERNS  # how the player knows it worked
```

At generation time `build_mystery()` copies these onto the `Mystery`
object (`m.family`, `m.discovery`, `m.reasoning`, `m.resolution`,
`m.confirmation`) and they round-trip through `to_dict`/`from_dict`.

### Vocabularies

```
STORY_FAMILIES = (
    "spatial",        # where is the route?
    "directional",    # which way should I investigate?
    "corroborative",  # which information can I trust?
    "infrastructural",# what dependency makes this work?
    "environmental",  # what must I change?
    "informational",  # what can I learn that I couldn't see before?
    "sequential",     # how do these pieces connect?
    "experimental",   # what if my interpretation is wrong?
    "transportation", # can I restore something that carries me out?
    "time_pressure",  # what stays viable before conditions change?
)

DISCOVERY_PATTERNS = (
    "see_route",         # the way out is directly visible once reached
    "find_document",     # a log / notice / record
    "find_named_place",  # arriving somewhere named in a clue
    "observe_anomaly",   # an environmental oddity (flooded road, smoke)
    "receive_information",# a response from outside (radio, signal)
    "find_object",       # a physical thing (a boat, a vehicle)
)

REASONING_PATTERNS = (
    "locate", "connect", "corroborate", "infer",
    "experiment", "revise", "sequence",
)

RESOLUTION_PATTERNS = (
    "open",      # a gate/door with a key
    "find",      # the route just has to be reached
    "repair",    # fix a broken thing
    "clear",     # remove an obstruction
    "operate",   # run a machine/vehicle
    "reveal",    # make a hidden route appear
    "follow",    # track a signal / marked path
    "respond",   # wait for / answer an external system
)

CONFIRMATION_PATTERNS = (
    "traversal",        # you walk/drive/sail out and it works
    "new_information",   # a document/response confirms it
    "environmental",     # the world visibly changed (water drained, gate lit)
    "external_response", # something outside the valley answered
    "corroboration",     # >=2 independent pieces agree
)
```

## 2. The five current mechanisms, classified

Tagging them honestly makes the core problem visible: they are almost
the same story. Families are spread just enough that the
anti-repetition rule (below) has something to bite on.

| mechanism | family | discovery | reasoning | resolution | confirmation |
|---|---|---|---|---|---|
| mountain_pass | spatial | find_named_place | locate | clear | traversal |
| rail_tunnel | spatial | find_document | locate | clear | traversal |
| service_route | infrastructural | observe_anomaly | locate | operate | traversal |
| boat_crossing | transportation | find_object | corroborate | operate | traversal |
| evac_corridor | sequential | find_document | sequence | open | traversal |

`resolution` and `confirmation` are near-identical across all five —
that is the design debt the Tier 2+ mechanisms (`c67cbd25`,
`ea1d52be`, `e0475adf`, `17f2a0ca`) exist to pay down.

## 3. Hard invariants

### 3a. No back-to-back family (enforced now)

`choose_mechanism(rng, used_mechanisms, used_families)` — the
shuffle-bag keeps its no-repeat-until-exhausted rule on the mechanism
NAME, and additionally drops any mechanism whose `family` equals the
previous expedition's family, unless that leaves the pool empty.
`_used_families` is tracked on the game class next to
`_used_mechanisms` and pushed in the same place (`mystery_mixin`'s
win path). With only 3 families across 5 mechanisms this already
prevents spatial→spatial.

### 3b. Story before geography (NOT enforced yet — Tier 2 work)

Today `generate_map()` builds terrain/settlements, THEN
`build_mystery()` places role sites on whatever buildings exist and
paints a little water for boat/dam. The target order is: pick
premise → family → mechanism → chains → confirmation → decoys FIRST,
then generate terrain to fit. That is a `generate_map()` restructure
and belongs with the Tier 2 mechanism todos, not this schema todo.
The `"terrain"` affinity key + `_paint_terrain_near()` (already there
for water) is the seam it grows from — see `a4a11df6`.

### 3c. Sparse, legible locations (partially done)

The `!` map markers (a role site is marked once you know the fact
pointing to it, through fog of war) and the mystery-generated
OBJECTIVES panel are the current answer. The remaining gap: the
generator still scatters role sites across generic `building` tiles.
Not this todo.

### 3d. Mystery-to-exit continuity (partially done — `ea1d52be` follow-up)

**The critical path of an escape story must create geographic progress
toward the escape, and resolution must not require an unrelated
post-solution trek.**

Named after 5 playtests (2026-08-28) that all died the same way: solve
the mystery in the cluster near spawn, then a long, dangerous,
resource-draining solo march to the far-corner escape gap
(`_carve_escape_pass` deliberately picks the *farthest* reachable
boundary gap) that adds nothing to the investigation. The bot's ~86%
survival can't see this — it walks straight lines and never wastes a
turn; a human wanders, and the march is pure attrition tax that
*scales with expedition* (maps grow +3/level).

The rule is **not** "make every mystery collinear" (that would make
every map read as walk-solve-walk-leave). It's: the *critical path*
(`closed → route → obstacle → … → escape`) has momentum toward the
exit; **side** roles (`require`, `power`) can be detours. Each family
expresses the momentum differently:

| family | how the resolution lands you at / points you out |
|---|---|
| spatial | discover the pass → clear it → it **is** the exit |
| infrastructural | dead gate → trace power → restore it → the gate **is** the exit |
| experimental | operate the dam → the newly-dry road **is** the exit |
| informational | restore the tower → the response **confirms + directs** — `escape` from where you stand (done: lever A, `c816232`) |
| sequential | station → station → the trail network you assembled **is** the route |
| transportation | find the vehicle → repair → **fly/sail** out from its location |
| environmental | drain / clear → the exposed road **is** the exit |

**Done:** lever A — for `reveals_route` mysteries `H_escape.confirmed_by
= E_route_reveal`, so the response confirms and the walk is narrated,
not played.

**Next (lever B, generator-level):** `build_mystery` should place the
critical-path sites with a bias toward the escape gap (and/or
`_carve_escape_pass` should stop always choosing the farthest gap).
Combat/resource numbers stay **frozen** through this — it's pacing,
not difficulty.

## 4. Which knowledge primitives generalise

| primitive | generalises as-is? | notes |
|---|---|---|
| `Fact` / `Evidence` / `Deduction` / `Hypothesis` | **yes** | the four-state model is family-agnostic. An informational or experimental mystery is still facts derived from discovered evidence. |
| `Evidence.method` (`observe` / `search`) | yes | |
| `Evidence.location` (a role string) | yes, but the **role set** must open up | today: closed/route/obstacle/require/escape. A `sequential` mystery needs N ordered sites; an `infrastructural` one needs a dependency graph (gate←power←generator←fuel), not one `require` site. |
| `m.requirement_item` (single string) | **no** — needs to become a list/chain | `power_station` needs fuel AND a fuse; `helicopter` needs a rotor part AND fuel. Make it `requirement_items: [...]` and the obstacle opens only when all are held/used. |
| `m.obstacle_tile` + `obstacle_open` (one tile flips) | **no for environmental** | `dam_spillway` / `forest_fire` flip a REGION. Needs `m.on_resolve` = a callback/spec that mutates a set of tiles. |
| `m.escape_tile` (fixed, in the mountain ring) | mostly | `informational` mysteries reveal the tile late (it isn't a wall gap you can see). `transportation` ones "escape" from the vehicle's location, not a ring gap. Add `m.escape_kind` ∈ {gap, vehicle, revealed}. |
| `mystery_try_escape` win check (confirmed + open + on/near tile) | yes | the three conditions stay; what "open" and "on tile" mean per `escape_kind` varies. |
| `choose_mechanism` shuffle-bag | extended in 3a | |

**Summary:** the knowledge model is sound and stays. The three things
that must grow: (1) `requirement_item` → `requirement_items` chain,
(2) `obstacle_tile` flip → `on_resolve` region mutation, (3) a fixed
role set → per-family role sets. Each is scoped to the Tier 2 todo
that needs it, not front-loaded here.

## 4b. Hard rule: no vocabulary leakage

The classification (`family`, `discovery`, `reasoning`, `resolution`,
`confirmation`) is **generator metadata only**. It must never reach
the player — no `family: experimental` line, no "REASONING PATTERN:
REVISE". The player experiences *"I tried the west sluice and the
water rose — maybe that's not the one,"* not a taxonomy. See
`PLAYER_UNDERSTANDING.md` Rule 4. Anything user-facing (objective
panel, journal, banners) is phrased in the mystery's own prose, keyed
off what the player has discovered — never off these fields.

## 5. What this todo (`9ab1b420`) actually ships

1. The five vocabulary tuples + the `classification` keys on all five
   `MECHANISMS` entries (data).
2. `Mystery` carries `family` + the four patterns; `build_mystery`
   sets them; `to_dict`/`from_dict` round-trip them.
3. `choose_mechanism` + `_used_families` — no back-to-back family.
4. This document.

Everything past that is a Tier 2 mechanism todo.
