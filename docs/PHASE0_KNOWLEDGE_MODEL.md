# Phase 0 — the knowledge model the generator must produce (todo 78921694)

2026-08-28. Stage 1 decision gate. Answers "what does the procedural
world need to generate so a player can reason their way to an escape,
rather than discovering unrelated objects that happen to coexist?"

**This is not open design anymore** — the Stage 0 slice built and
proved a concrete instance of it (`src/slice_dam_road.py`'s
`SLICE_FACTS` / `SLICE_EVIDENCE` / `SLICE_DEDUCTIONS` /
`SLICE_HYPOTHESIS`). Phase 0's job is to lift that instance into the
data model the generator targets and Stage 2C implements.

## The four objects

Every expedition's mystery is four linked collections. The generator
builds them **backward from the escape** (see the design doc's "Escape
proof & causal-chain validation"); the player discovers them forward.

### 1. Facts — `Fact`

```
id            "F1"
statement     "The main road out is flooded and impassable."
state         Observed | Known            (never Suspected/Confirmed - those are Hypothesis states)
```

A fact is `Known` as soon as ≥1 piece of its supporting evidence is
discovered. `Observed` is the pre-fact state: the player has seen the
raw thing but no evidence has tied it to a meaning yet (the
discover-before-understand case, design #7).

### 2. Evidence — `Evidence`

```
id            "E2"
location      <location id>               where it physically is
method        observe | search           observe = auto-revealed on arrival; search = deliberate action
text          "Maintenance log: ... gate key is in the control room."
supports      ["F2", "F3", "F4"]          fact ids this evidence establishes
```

**Redundancy is a generation invariant, not a nicety** (design doc,
"Redundancy is a generation requirement"): no `Fact` that a required
deduction depends on may have only one `Evidence` unless that evidence
has multiple independent discovery routes. The slice: every fact has
≥2 evidence routes; a player can miss up to 3 of 7 and still solve it.
The generator validates this by ablation (Stage 3 harness).

**`observe` evidence for load-bearing facts is the safety net** — a
fact whose only evidence is `search` can be permanently missed by a
player who doesn't think to search there. At least one route to each
load-bearing fact must be `observe` (revealed by ordinary movement /
`look`).

### 3. Deductions — `Deduction`

```
id            "D2"
needs         ["F1", "F2", "F3"]          fact ids that must all be Known
text          "There is another road, only blocked by a gate. A gate can be opened."
```

A deduction becomes *available* when all its `needs` facts are Known.
It is never a checkbox the player ticks — `remember` synthesises the
available deductions into prose. Deductions are the "Relationship /
Inference" layer of the design doc's chain
(`evidence → observation → interpretation → fact → relationship →
inference`).

### 4. Hypothesis — `Hypothesis`  (exactly one per expedition)

```
id                "H1"
statement         "The service road past the gate is the way out."
suspected_when    ["D2"]                  deduction ids; all available => state becomes Suspected
confirmed_by      "E6"                    evidence id; found => state becomes Confirmed
```

State machine, **transitions automatic** (design doc: no `confirm`
command):

```
unknown  --(all suspected_when deductions available)-->  suspected
suspected --(confirmed_by evidence discovered)-->         confirmed
```

`confirmed_by` evidence must be `observe` and must be physically
gated behind the escape action's prerequisites (the slice: E6 is only
revealable once you've opened the gate and stepped through). This is
what makes the final action *test the hypothesis* rather than check a
flag.

## Answers to the specific Phase 0 questions

| Question | Answer |
|---|---|
| Discovery vs. clue vs. inferred knowledge? | Discovery = `Evidence` surfaced. Clue = same thing, informal word for it. Inferred = `Deduction` (needs multiple facts) and `Hypothesis`. |
| Can clues contradict? | Not in v4.0. The `supports` model is monotonic. The doc's "contradiction and false leads" stays a later layer; the data shape (evidence→facts, not evidence=facts) leaves room for it. |
| Found in different orders? | Yes, always. A mechanism defines relationships, never a sequence. Validation simulates multiple discovery orders (Stage 3). |
| How does generation guarantee a valid escape chain exists? | The Escape Proof structure is built backward from the escape and validated by ablation before the map ships — the knowledge-chain analogue of `_ensure_reachable()`. This is Stage 4.1, and it must land before the mechanism generator (4.2). |
| Win without every clue? | Yes — redundancy invariant guarantees a solvable subset. Minimum subset = whatever survives ablation as load-bearing. |
| Find a clue before what explains it? | Yes — that's the `Observed` fact state and the discover-before-understand mechanic. |
| How much stated vs. inferred? | Facts are stated once their evidence is found (`journal`). Deductions and the hypothesis are synthesised, never asserted as "OBJECTIVE: open the gate". `remember` says "you are starting to think X", not "do X". |
| Persists between expeditions vs. resets? | The mystery (all four objects) resets each expedition. What persists at profile level: nothing mystery-related in v4.0 — the campaign-narrative layer (Stage 5) is where cross-expedition knowledge would live. |
| Player dies before acting on a discovery? | v4.0: expedition knowledge is in-memory and lost on death, same as map position. Serialising it across save/load within a run is Stage 2C (`e3a1e201`); across death is deferred (design doc "Death and knowledge" is still open). |
| Escape-mechanism TYPE selection / variety? | Shuffle-bag over the mechanism pool, campaign-aware (no repeat until pool exhausted). Tracked in profile state distinct from the per-expedition Escape Proof. Stage 4.2 + Stage 5. |
| Mechanism chosen before terrain, seeding it? | Yes. Generation order changes: mechanism → required geography → terrain → settlements → … → clue placement. Stage 4.2. |
| Seed-choices-then-deterministic generation? | Directionally yes, but v4.0 only commits to it for the escape mechanism (4.2). Generalising it to survivor/ecology/history is Phase C proper. |

## What Stage 2C builds from this

`2C.1` (`f6d126f9`) implements `Fact` / `Evidence` / `Deduction` /
`Hypothesis` as real persisted collections on the game object,
generalising `SliceMixin`'s in-memory versions — same field names,
same four-state model, same automatic transitions. The slice's
`_slice_facts_known()` / `_slice_deductions_available()` /
`_slice_hypothesis_state()` become the engine's, un-prefixed.

`2C.4`/`2C.5` (`look`/`inspect`, `journal`/`remember`) generalise
`SliceMixin`'s command methods.

The generator (Stage 4) is what populates the four collections
per-expedition instead of `slice_dam_road.py` hand-authoring them.
