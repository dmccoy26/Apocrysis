# Phase A.2 — `DiscoveryTemplate` + `build_mystery(target_fact=…)`

Authored before implementation. Builds on `PHASE_A1_TRUTH.md`.

## The one architectural constraint

> `WorldFact` is authoritative authored truth. `DiscoveryTemplate` maps
> a truth to a **discovery opportunity** (an escape mechanism that can
> carry it). The resulting mystery **must remain independently solvable
> through its own evidence**. Never expose or inject a `WorldFact`
> statement as the player's answer.

```
WorldFact  ──DiscoveryTemplate──▶  Mystery  ──▶ Evidence ──▶ Knowledge
(author        (engine knows        (player still solves it by evidence;
 knows          which truth is       solving it is what SURFACES the
 the truth)     being surfaced)      fact — that wiring is A.3)
```

The fact **selects/targets** the mystery; it is not the mystery's
answer. `DiscoveryTemplate` is a routing table, not an oracle.

## Scope — minimal

### `src/worlds/base.py` — add a sibling dataclass + one `World` field

```python
@dataclass(frozen=True)
class DiscoveryTemplate:
    """Binds one authored WorldFact to an escape mechanism that can
    carry it. NOT the mystery's answer - see PHASE_A2_DISCOVERY.md."""
    world_fact_id: str
    mechanism: str            # a key of escape.MECHANISMS

@dataclass(frozen=True)
class World:
    ...
    discovery_templates: dict = field(default_factory=dict)
    #   { world_fact_id: (DiscoveryTemplate, ...) }  - >=1 route per fact
```

No `role_labels`, no `evidence_flavor` yet. If A.3 needs scenery to
reflect the fact, that field is added then, with its wiring. A.2 proves
the routing works with **mechanism choice alone**.

### `src/worlds/silence/discovery.py` — new file, content only

```python
from src.worlds.base import DiscoveryTemplate

# Each CH1/CH2 WorldFact -> the escape mechanism(s) that thematically
# carry it. Solving that mechanism's mystery is a plausible way this
# survivor would come to that conclusion. >=1 per fact.
DISCOVERY_TEMPLATES = {
    "DIS_FEW_REMAINS":    (DiscoveryTemplate("DIS_FEW_REMAINS", "mountain_pass"),),
    "DIS_MOVED_TOGETHER": (DiscoveryTemplate("DIS_MOVED_TOGETHER", "rail_tunnel"),),
    "DIS_ROUTES_PREPARED":(DiscoveryTemplate("DIS_ROUTES_PREPARED", "evac_corridor"),),
    "DIS_ORGANISED":      (DiscoveryTemplate("DIS_ORGANISED", "evac_corridor"),),
    "DEAD_WERE_LOCALS":   (DiscoveryTemplate("DEAD_WERE_LOCALS", "service_route"),),
    "DEAD_STAGES_DIFFER": (DiscoveryTemplate("DEAD_STAGES_DIFFER", "radio_tower"),),
    "DEAD_CONTAINED_FIRST":(DiscoveryTemplate("DEAD_CONTAINED_FIRST", "power_station"),),
    "DEAD_REGIONAL_CRISIS":(DiscoveryTemplate("DEAD_REGIONAL_CRISIS", "radio_tower"),),
    "DEAD_INFECTION_PREDATES_EVAC":(DiscoveryTemplate("DEAD_INFECTION_PREDATES_EVAC", "rail_tunnel"),),
}
```

`worlds/silence/world.py` imports `DISCOVERY_TEMPLATES` and passes it to
`SILENCE(discovery_templates=DISCOVERY_TEMPLATES)`.

### `src/escape.py` — the `target_fact` path

- `Mystery.__init__`: `self.world_fact_id = None`
- `Mystery.to_dict` / `from_dict`: round-trip `world_fact_id`
- `build_mystery(game, target_fact=None)`:

```python
if target_fact is not None:
    routes = game.world.discovery_templates.get(target_fact)
    if routes:
        m.mechanism = game.rng.choice(routes).mechanism
        m.world_fact_id = target_fact
    else:
        m.mechanism = choose_mechanism(game.rng, ...)   # graceful fallback
else:
    m.mechanism = choose_mechanism(game.rng, ...)       # unchanged
```

Everything downstream (`spec = MECHANISMS[m.mechanism]`, the whole
evidence/deduction/hypothesis build, `validate()`,
`_assert_directional_truth`) is **unchanged**. `world_fact_id` is a tag
on the Mystery; nothing reads it yet.

**No `MechanismFamily`.** The minimal `target_fact` path does not need
it — it only swaps which `MECHANISMS` key is used. `escape.py` is not
otherwise touched.

### `generate_map()` — unchanged

Still calls `build_mystery(game)` with no `target_fact`. The scheduler
that chooses the next fact is A.3. `target_fact` is exercised only by
tests in A.2.

## Tests — `src/tests/test_discovery.py` (new)

1. every `DiscoveryTemplate.mechanism` in `SILENCE.discovery_templates`
   is a real `escape.MECHANISMS` key
2. every CH1/CH2 `WorldFact.id` has at least one `DiscoveryTemplate`
3. `build_mystery(game, target_fact="DIS_ORGANISED")` →
   `m.world_fact_id == "DIS_ORGANISED"` and `m.mechanism == "evac_corridor"`
4. that mystery still passes `m.validate()` and its escape tile is
   reachable from spawn
5. **anti-injection**: the `WorldFact.statement` string for the target
   fact appears in **none** of the mystery's `knowledge` text
   (`fact.statement`, `evidence.text`, `deduction.text`,
   `hypothesis.statement`)
6. `build_mystery(game)` with no `target_fact` → `m.world_fact_id is None`
   (random path unchanged)
7. `Mystery.from_dict(m.to_dict()).world_fact_id == m.world_fact_id`
8. unknown `target_fact` → graceful fallback (a valid random mystery,
   `world_fact_id` stays None), no exception

## Guardrails (for Atlas — same spirit as A.0/A.1)

Do **not**: introduce `MechanismFamily`, restructure `build_mystery`,
add `role_labels`/`evidence_flavor` wiring, build the A.3 investigation
scheduler, touch `knowledge.py`, change `generate_map`'s call, or make
`WorldFact.needs` mean "player must have solved these first" (it stays
declarative: *these truths logically support this truth*).

## Routing

- `discovery.py` (new, ~15 lines structured data) → Atlas (truth.py shape).
- `base.py` edit (14-line file, add a dataclass + a field) → Atlas.
- `world.py` edit (small) → Atlas.
- `escape.py` edit (917 lines) → **expected Atlas fail** (large file);
  route it once, then hand-write.
- `test_discovery.py` (procedural) → **expected Atlas fail**; hand-write.

Log every attempt in `ATLAS_CAPABILITY_LOG.md`; append gaps to the
`atlas-self` todos. Do not shrink the design to make Atlas pass.
