# Phase A.3 — World Investigation persistent state

Authored before implementation. Builds on `PHASE_A1_TRUTH.md` +
`PHASE_A2_DISCOVERY.md`.

## Scope — exactly seven things, nothing else

1. `WorldInvestigation` — a class (data + derivation, no I/O, no `src/`
   imports)
2. derived per-fact status + per-thread progress
3. `next_target()` — first UNKNOWN fact whose `needs` are all KNOWN
4. resolution hook — a solved mystery tagged `world_fact_id` calls
   `mark_known(fact_id)`
5. profile persistence — the **existing** class-var + profile
   round-trip seam (as `_used_mechanisms` does it). No new abstraction.
6. save/load tests
7. DAG eligibility tests

**Not in A.3:** no UI / World Investigation screen, no database, no
evidence-provenance logic, no `knowledge.py` change, no `campaign.py`
change, no `build_mystery` scheduler call (generate_map still passes no
`target_fact`).

## The state-transition boundary (important)

```
mystery resolved (mystery_try_escape) ─▶ m.world_fact_id ─▶ WorldInvestigation.mark_known(fid)
```

**Not** "the player therefore knows the WorldFact." A.3 uses the
deliberately simplified rule: *a successfully resolved mystery
explicitly tagged with a `world_fact_id` marks that fact KNOWN.* The
transition is isolated to one 2-line hook so evidence/provenance logic
can replace it later without touching anything else.

## `src/world_investigation.py` (new)

```python
KNOWN, SUSPECTED, UNKNOWN = "known", "suspected", "unknown"

class WorldInvestigation:
    def __init__(self, facts):
        self._facts = {f.id: f for f in facts}      # insertion order == authored order
        self._status = {}                            # fid -> "known"|"suspected"; absent = unknown

    def status(self, fid): -> "known"|"suspected"|"unknown"
    def is_known(self, fid): -> bool
    def mark_known(self, fid): sets "known" (ignores unknown ids)
    def mark_suspected(self, fid): sets "suspected" unless already "known"

    def eligible(self):     # UNKNOWN facts whose needs are all KNOWN, authored order
    def next_target(self):  # eligible()[0].id or None

    def thread_progress(self):   # {thread: (known:int, total:int)}
    def milestones_known(self):  # [fid, ...] for known milestone facts

    def snapshot(self): -> {"status": {...}}     # for the profile
    def restore(self, snap): loads a snapshot (None-safe)
```

Pure. No import of `truth.py`, `game.py`, anything. Takes the facts in.

## Wiring

### `src/worlds/base.py`
`World` gains `world_facts: tuple = ()`.

### `src/worlds/silence/world.py`
`from src.worlds.silence.truth import WORLD_FACTS` → `world_facts=WORLD_FACTS`.

### `src/game.py`
- class-var `_world_investigation = {}` (the `{fid: status}` dict — same
  shape/role as `_used_mechanisms`)
- in `__init__`, after `self.world`:
  `self.world_investigation = WorldInvestigation(self.world.world_facts)`
  then `self.world_investigation.restore({"status": type(self)._world_investigation})`

### `src/mixins/mystery_mixin.py` — `mystery_try_escape`
Right after `m.escaped = True`:
```python
if m.world_fact_id:
    self.world_investigation.mark_known(m.world_fact_id)
    type(self)._world_investigation = self.world_investigation.snapshot()["status"]
```

### `src/mixins/persistence_mixin.py`
- `save_profile` dict: `"world_investigation": dict(getattr(self.__class__, "_world_investigation", {}))`
- `apply_profile`: `_wi = profile.get("world_investigation"); if _wi is not None: self.__class__._world_investigation = dict(_wi)`

**Persistence boundary (unchanged):** World Investigation status carries
in the profile (survives death / new expedition). Map, gear, current
expedition state do not — same split as today.

## Tests — `src/tests/test_world_investigation.py` (new)

**DAG eligibility**
- fresh: `next_target()` is the first root fact (`DIS_FEW_REMAINS`)
- **A-needs-B ordering**: with `DEAD_REGIONAL_CRISIS` (needs
  `DIS_ORGANISED`) and `DIS_ORGANISED` both UNKNOWN → `next_target()` is
  **not** `DEAD_REGIONAL_CRISIS`; after `mark_known("DIS_ORGANISED")` →
  `DEAD_REGIONAL_CRISIS` becomes eligible
- **cross-chapter**: `DIS_ORGANISED` (CH1) unlocking
  `DEAD_REGIONAL_CRISIS` (CH2) specifically
- `mark_known` on an unknown id is a no-op, no raise
- `thread_progress` counts move as facts are marked

**Persistence (profile round-trip)**
- `Apocrysis` game A: mark a fact known via the resolution path →
  `save_profile` → fresh `Apocrysis` game B: `apply_profile` → B's
  `world_investigation.is_known(fid)` is True
- a fact NOT marked stays UNKNOWN across the round-trip
- gear / map / expedition state are NOT carried by the investigation
  round-trip (assert the profile dict has only the status map)

**Resolution hook**
- build a mystery with `target_fact="DIS_ORGANISED"`, drive it to
  `mystery_try_escape` success → `DIS_ORGANISED` is KNOWN and the
  class-var reflects it
- a random (untagged) mystery solved → no fact flips

## Routing

- `world_investigation.py` (new, ~45 lines, some procedural) → Atlas
  first; likely near its line boundary — log the result.
- `worlds/base.py` + `worlds/silence/world.py` edits (small) → Atlas.
- `game.py` edit (mid-size) → Atlas (it did the last `game.py` edit).
- `mystery_mixin.py` (664 lines) + `persistence_mixin.py` (555 lines)
  edits → Atlas once each, expect the large-file wall, hand-write.
- `test_world_investigation.py` → hand-write (procedural).

Log every attempt; append gaps to `atlas-self`. Don't shrink the design.
