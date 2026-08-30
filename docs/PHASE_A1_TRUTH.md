# Phase A.1 — the `WorldFact` DAG (`worlds/silence/truth.py`)

Authored before implementation. Atlas types the file; it does not
design the truth. Builds on `PHASE_A_DECISIONS.md` (truth A "The
Cordon") and `PHASE_A0_SEAM.md`.

## Scope — astonishingly small

**One new file** `src/worlds/silence/truth.py`:

```python
@dataclass(frozen=True)
class WorldFact:
    id: str
    thread: str          # "disappearance" | "dead" | "response"
    chapter: int
    milestone: bool
    statement: str
    needs: list[str] = field(default_factory=list)

WORLD_FACTS = [ ... ]     # CH1 + CH2 only
```

**`WorldFact` does NOT inherit from `knowledge.Fact`.** Different job:
`Fact` = *what the player has learned*; `WorldFact` = *what is actually
true in this world*. They meet later, through `DiscoveryTemplate`
(A.2), never by inheritance.

**Nothing else.** No graph class, no traversal, no solver, no inference
engine, no runtime state, no investigation manager, no persistence, no
UI, no causal model, no evidence/mechanism references. The DAG is
**content**, not yet a runtime system.

## The authored DAG — CH1 + CH2

```
CH1 — THE SILENCE  (thread: disappearance)      "why is everyone gone?"

  DIS_FEW_REMAINS
        │
  DIS_MOVED_TOGETHER
        │
  DIS_ROUTES_PREPARED
        │
  DIS_ORGANISED  ★M1

CH2 — THE INFECTED  (thread: dead)              "what are the infected,
                                                 and where did they start?"
  DEAD_WERE_LOCALS
      │        │
  DEAD_STAGES  DEAD_CONTAINED_FIRST
  _DIFFER          │
      │            │
  (DIS_ORGANISED ──┤              ← cross-chapter need, CH1 → CH2 (allowed)
      │            │
  DEAD_REGIONAL    DEAD_INFECTION_PREDATES_EVAC  ★M4
  _CRISIS  ★M2
```

| id | thread | ch | milestone | needs | statement |
|---|---|---|---|---|---|
| `DIS_FEW_REMAINS` | disappearance | 1 | – | – | Far fewer remains than a die-off would leave. Most people left; they didn't fall. |
| `DIS_MOVED_TOGETHER` | disappearance | 1 | – | `DIS_FEW_REMAINS` | The people who left moved along a handful of specific routes, the same direction, over a few days. |
| `DIS_ROUTES_PREPARED` | disappearance | 1 | – | `DIS_MOVED_TOGETHER` | Those routes were prepared before the exodus — signed corridors, marshalling yards, supply caches. |
| `DIS_ORGANISED` | disappearance | 1 | **M1** | `DIS_ROUTES_PREPARED` | The exodus was an organised evacuation, directed by some authority — not a panicked flight. |
| `DEAD_WERE_LOCALS` | dead | 2 | – | – | The infected wear the valley's own clothes and carry its own papers. They are the people who lived here. |
| `DEAD_STAGES_DIFFER` | dead | 2 | – | `DEAD_WERE_LOCALS` | The infected differ by how far the disease has run, not by kind — some lucid and failing slowly, others long past that. |
| `DEAD_CONTAINED_FIRST` | dead | 2 | – | `DEAD_WERE_LOCALS` | There was a contained outbreak before the exodus — a quarantine/research site with early cases already inside it. |
| `DEAD_REGIONAL_CRISIS` | dead | 2 | **M2** | `DIS_ORGANISED` | The crisis was handled as regional: notices and broadcasts describe a cordon around the valley, reception centres *outside* it. The wider world did not end. |
| `DEAD_INFECTION_PREDATES_EVAC` | dead | 2 | **M4** | `DEAD_CONTAINED_FIRST`, `DIS_ORGANISED` | The infection was known and present before the evacuation began. The evacuation was a response to it — not the other way round. |

9 facts, 3 milestones (`DIS_ORGANISED` = M1, `DEAD_REGIONAL_CRISIS` =
M2, `DEAD_INFECTION_PREDATES_EVAC` = M4).

### Invariants the shape must hold

- **CH1 facts have no cross-chapter needs.** (CH2 facts may need CH1
  facts — that's the chapter boundary working, not breaking it.)
- The `needs` graph is a DAG (acyclic; no self-loops).
- Every `needs` id resolves to a real `WorldFact`.
- `thread` ∈ {`disappearance`, `dead`, `response`}. (No CH1/CH2 fact
  uses `response` — it's reserved for CH4.)
- `chapter` ∈ {1, 2} for this file.
- Milestone ids are exactly `{DIS_ORGANISED, DEAD_REGIONAL_CRISIS,
  DEAD_INFECTION_PREDATES_EVAC}`.
- The player never sees `thread` / `id` — only `statement`
  (`PLAYER_UNDERSTANDING.md` no-vocab-leak rule).

## `src/tests/test_world_truth.py`

1. every id in every `needs` list resolves to a `WORLD_FACTS` id
2. the `needs` graph is acyclic
3. **no fact lists its own id in `needs`** (clearer failure than the
   cycle check alone)
4. every `thread` is in the closed vocabulary
5. every `chapter` is 1 or 2
6. milestone fact ids == the authored contract set (exact)
7. no CH1 fact has a `needs` entry pointing at a CH2 fact

## Not in A.1 (guardrails for Atlas — same spirit as A.0)

No `DiscoveryTemplate`, no `target_fact` in `build_mystery`, no World
Investigation state/screen, no `campaign.py` changes, no engine wiring
at all. `truth.py` is imported by **nothing** yet except its test.
That's A.2+.

## Routing

`truth.py` is a **self-contained new file** (only `from dataclasses
import …`) — the shape Atlas succeeded on for `base.py`. Route it to
Atlas. `test_world_truth.py` is import-then-use — route it too. If
either hits the known boundary (`dbc93715` multi-file / import-construct,
`f7ee975b` large literal), log it, file/append the `atlas-self` todo,
hand-write it. Do **not** shrink the DAG to make Atlas succeed.

---

## CH3–FIN authored (2026-08-30) — the full arc

`truth.py` extended from 9 facts (CH1+CH2) to **23** — the whole "The
Cordon" arc (`WORLD_TRUTH_CANDIDATES.md` candidate A). 14 new facts on
the **`response`** thread:

| chapter | facts | milestone |
|---|---|---|
| CH3 THE EVACUATION | `RESP_CORRIDORS_LED_OUT` → `RESP_NOT_ALL_REACHED` → `RESP_COMMS_CUT_DELIBERATE` → `RESP_CORDON_HELD_OUTSIDE` | **M3** (comms cut on purpose) |
| CH4 THE RESPONSE | `RESP_PROTOCOL_SEVEN` → `RESP_SEAL_SCHEDULED` → `RESP_ONE_COMMAND` → `RESP_CONTAINMENT_WORKED` | **M5** (seal scheduled), **M6** (one command) |
| CH5 THE LAST SIGNAL | `RESP_STILL_MONITORED` → `RESP_A_POST_TRANSMITS` · `RESP_CONSOLIDATION_HELD` → `RESP_PEOPLE_ALIVE` | **M8** (a post transmits), **M9** (people alive) |
| FIN THE TRUTH | `RESP_THE_ORDER` → `RESP_THE_CHOICE` | — |

**8 milestones** total (M1/M2/M4 from CH1-2 + the 5 above; M7 unused,
matching the candidate). The DAG walks cleanly end-to-end via
`next_target()` — 23 facts in chapter order, every fact carries a
`DiscoveryTemplate` (`discovery.py`), every CH3-FIN fact × 4 seeds
builds a valid targeted mystery.

`needs` edges never point forward a chapter (`test_world_truth.py`
`test_needs_never_point_forward_a_chapter`). `test_chapters_are_1_or_2`
→ `test_chapters_in_arc_range` (1..6).

**`RESP_THE_CHOICE`** states the ending fork (broadcast the truth past
the cordon vs leave the settlement its silence) as a *fact the player
establishes* — the ending *system* that acts on it (the choice UI, the
two authored outcomes) is Phase E, not this pass.

## Also this pass (campaign structure)

- `CAMPAIGN_LENGTH` 10 → **25**; new `DIFFICULTY_RAMP_LENGTH = 10`
  decouples the zombie difficulty curve from arc length (the frozen
  curve is unchanged for exp 0–10 and holds at max after).
- `campaign.py`: 6 chapter-intro lines + `_CHAPTER_BOUNDS` +
  `chapter_for_expedition(n)` + `CHAPTER_TITLES`; `chapter_intro` keyed
  to the chapter the depth falls in, pulled forward when the
  investigation runs ahead (replaying early maps after deaths).
- Bot: **7/8 full 25-expedition campaigns completed** (1 stuck at the
  known expedition-9 combat wall).

## Not in this pass — the three endgame *systems* (Phase E)

Competing hypotheses (`knowledge.py` `self.hypothesis` → a set + a
correction beat), the bespoke final expedition, and the ending choice
(broadcast vs protect) acting on `RESP_THE_CHOICE`. Each is an engine
change, separately specced.
