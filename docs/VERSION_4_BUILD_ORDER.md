# Version 4 — Build Order

Organizing pass, 2026-08-28 (rev. 2 — separated loop-critical work from
inherited V3 mechanics, added the slice-success gate, the V3-assumption
audit, and the implementation invariants). This is the **program order**
for the escape-world redesign on the `version-4` branch. It does not add
new design — it sequences the 63 pending items in
`projects/apocrysis/version-4/.atlas/todo_list.json` into buildable
stages with their decision gates and dependencies made explicit.

Read alongside `ESCAPE_WORLD_DESIGN_ASSESSMENT.md` (the "what" and
"why"); this file is only the "in what order."

---

## STATUS (2026-08-28) — v4 is playable end to end

The premise change is done: `python3 apocrysis.py` now generates an
investigation mystery every expedition, and you win by working out the
escape route and taking it, not by reaching the Town Center.

| Stage | State |
|---|---|
| 0 — vertical slice | **done**, played, GO given |
| 1 — decision gates | **done** (`PHASE0_KNOWLEDGE_MODEL.md`, `V3_ASSUMPTION_AUDIT.md`; SLICE-SUCCESS satisfied by the playtest) |
| 2A — world geometry | map ceiling ✓, mountain boundary ✓, landmarks ✓; **2A.3 organic settlements, 2A.5 player class, 2A.6 loot bands deferred** |
| 2B — world persistence | **done** (zombie-tile clear, dropped-item persistence, abandonment states) |
| 2C — knowledge model | **done** (`knowledge.py`, journal/remember/inspect/look, save/load); 2C.3 primitive only, 2C.6 = coord labels only |
| 2D — zone ecology | **done** (zone layer, contextual zombies + loot) |
| 3 — investigation harness | **partial** — `tools/mystery_solver.py` covers solvability; the investigation-aware bot policy + budget telemetry not built |
| 4 — escape generator | **done** — `escape.py` (5 mechanisms, Escape Proof, validation), `mystery_mixin.py`, win-condition change, mountain-pass carve. 40/40 seeds valid+reachable |
| 5 — campaign | 5.1 chapters ✓, 5.2 retrospective ✓, 5.4 goal-system removal ✓; **5.3 People layer deferred**, balance sweep deferred |
| 6 — README | **done** — player-facing rewrite |
| H — harness realism | **not done** (H1 bot bugs, H2 reporting, H3 Q-pass) |

**Top open item: combat lethality vs. investigation length.** Survival
was retuned down (`ZOMBIE_MAP_DENSITY` 0.10→0.04, encounter 0.30/0.50→
0.10/0.20) but a mediocre bot (`tools/mystery_solver.py`) still only
solves ~50% solo. A real player does better; this needs human
playtesting to tune, not more blind sweeping.

---

**Before starting any stage, answer this first:** *what assumption from
the design would be most dangerous to discover is wrong?* Build to test
that assumption soonest. The 63-item list can create the illusion that
the architecture is settled — it isn't. Stage 0 exists to let the slice
kill ideas; that is the point of putting it first.

**Execution note (2026-08-28):** the local model driving Atlas
(`qwen3.6-35b-a3b`) failed every non-trivial generation task on this
codebase (0/4 — new-file creation and mid-size function rewrites all
produced unparseable patches). By user direction, Claude now writes
the code Atlas can't, and Atlas is used for verification and small
localized diffs. See todo `ad998cd0` and the memory note. Revisit if a
stronger local coder model becomes available.

## Branch state (corrects the stale handoff note)

- `version-4` **exists**, locally and on `origin`
  (`github.com/dmccoy26/Apocrysis`). HEAD is `5c4912a` — one commit
  ahead of `version-3` (`9c835aa`), containing the design doc, commands
  reference, and README pointer.
- The working tree is at `projects/apocrysis/version-4/` (relative to
  the Atlas repo root). Sibling `version-1/`..`version-3/` directories
  are read-only single-branch clones of the older branches, for
  reference only — no work happens in them.
- All version-4 work commits to `version-4`. The earlier note saying
  "confirm/create it before pushing" is resolved — it's there.

## The two tracks

Version 4 has two mostly-independent bodies of work. Do not interleave
them arbitrarily — they have different risk profiles.

- **Track 1 — Escape-world redesign** (Stages 0–6 below). The premise
  shift. High risk, strictly ordered, gated by the slice playtest.
- **Track 2 — Current-engine cleanup** (Stage H below). Balance-harness
  realism bugs and the exploration/objective investigation pass. Mostly
  independent of Track 1, lower risk, and the harness fixes are a
  prerequisite for *trusting* any Track 1 balance data. Pull the harness
  bug fixes forward; the Q1–Q12 confirmations can happen whenever.

**"Parallel" means Track 2 can run on its own timeline — not that its
work interleaves with Track 1 implementation.** Track 2 never changes
V4 gameplay direction or touches Track 1 gameplay code; its only job is
trustworthy instrumentation before the investigation harness is used as
evidence. Stage 0 remains the *only* design gate.

---

## Stage 0 — Vertical slice (BUILD THIS FIRST)

Supersedes all generator-first sequencing. Hard-coded, no procedural
generation. This is the go/no-go gate for whether the generator
(Stages 2–5) gets built at all.

| Order | ID | Item |
|---|---|---|
| 0.1 | `138c10f6` | Hard-coded 19×19 / 21×21 Dam Service Road map |
| 0.2 | `dd70ae0c` | Dam Service Road Escape Proof as real game state (4 facts / 6 evidence / 2 deductions / 1 hypothesis) |
| 0.3 | `d7a712dc` | Minimal `journal` / `remember` / `inspect`, slice-scoped only |
| 0.4 | `4f8fdc57` | Temporarily loosen survival pressure (slice-mode flag, explicitly throwaway) |
| 0.5 | `ceee7e54` | Knowledge-persists-past-object-destruction example + the gated escape action |
| 0.6 | `9f831f9d` | **Playtest against the three-situation test.** GO/NO-GO GATE. |

Do not start Stage 1 until 0.6 is done and evaluated. Read the 0.6
checklist before running it, not after.

**Formal solvability is necessary but not sufficient.** The Escape Proof
can be structurally perfect and the game can still be no fun. The 0.6
gate tests *player experience*, not merely whether the six evidence
pieces technically connect — evaluate it against the explicit
slice-success criteria in Stage 1 (`SLICE-SUCCESS`), agreed *before*
the playtest so the goalposts don't move afterward.

---

## Stage 1 — Decision gates

Investigation/decision items with no code. Resolve each before the
stages that depend on it — informed by what the slice playtest actually
showed, not ahead of it.

**The filter for every item in this stage:** *is this a true
prerequisite for the generator, or an abstraction we're assuming the
generator will need?* If the slice proved the loop without it, an
assumed abstraction drops to "nice for texture, do when its stage comes
up" — it is not a gate.

### 1.0 — `SLICE-SUCCESS`: what counts as a successful proof of the loop

**Answer this before running the 0.6 playtest.** Not an implementation
task — a measurement gate, kept deliberately lightweight. Fix the
success criteria now so they can't be renegotiated after the fact.
Baseline questions (all must be answerable "yes" from the playtest):

- Can a new player identify something worth investigating with no
  explicit objective given?
- Can they form a plausible hypothesis from player-visible information
  alone?
- Can they take a reasonable action based on that hypothesis?
- Does the world respond meaningfully to that action?
- Can they recognize when a hypothesis was wrong or incomplete?
- Can they recover from that without being handed new information?
- Can they tell important evidence from flavor without a quest marker?
- Does the escape feel earned, rather than like solving a puzzle the
  designer built?
- **Did the player actually enjoy doing this?**

### 1.1 — true prerequisites for the generator

| ID | Decision | Blocks |
|---|---|---|
| `78921694` | Phase 0: what must the world generate so a player can *reason* to an escape? (this is the spec for `4.1`/`4.2`) | Stage 4 |
| `182bdc49` | The minimum information interface (what `look`/`inspect`/`journal`/`remember`/`map` must minimally provide) | `9c2db876`, `a6de97c0`, `1f2c7826` |
| `d3179782` | World-validation + information-budget invariants (`MAX_MEANINGFUL_LOCATIONS`, `MAX_EVIDENCE`, …) | `c1730862`, Stage 4 validation |
| — | **V3-assumption audit** (new): enumerate every V3 mechanic that assumes a known objective, Town Center = goal, combat-primary, exploration = finding settlements, loot-as-reward, progression-as-reason-to-continue, global map knowledge, or the goal/task system as player intent. Classify each: KEEP / MODIFY / DELETE / TEMPORARILY DISABLE. V4 is a premise change, not V3 + an investigation system — this may matter more than another 20 implementation todos. | Stages 2C, 4, 5.3 |

### 1.2 — assumed abstractions (revisit after the slice; gate only if their stage survives)

| ID | Decision | Note |
|---|---|---|
| `457c93a6` | Zone/district layer — semantic zone tag on top of terrain clustering | Only a gate for `2D` and the contextual-ecology work. If the slice proves the loop without a zone abstraction, don't commit to the architecture pre-emptively. |
| — | Design forks still open in the doc: physical/knowledge persistence detail, zombie-ecology open questions, people historical-vs-simulated, time-as-world-state, world-age/decay, escape-as-failable-arc. Resolve the ones a stage actually touches, when it touches them — not all up front. |

---

## Stage 2 — Phase A + B: player information architecture, then world texture

Split by what the investigation loop actually needs. **2C is the loop**
— build it first and prove it standalone against whatever flavor
facts/locations already exist. **2A / 2B / 2D are world texture** —
legitimate systems, but they don't prove
`World → Observation → Interpretation → Hypothesis → Action → Result`.
Several are V3 mechanics being carried forward because they already
exist; sequence them flexibly after 2C and after the 1.1 V3-assumption
audit has classified them.

### 2C — Player information architecture — LOOP-CRITICAL, do first (Phase B), after `182bdc49`

Status 2026-08-28: **2C.1 / 2C.4 / 2C.5 done** (commit — `src/knowledge.py`,
`src/mixins/knowledge_mixin.py`, slice migrated onto the shared model,
10 tests). 2C.2 partial (snapshot API exists, not yet wired to
save/load). 2C.3 / 2C.6 open.

| Order | ID | Item | Status |
|---|---|---|---|
| 2C.1 | `f6d126f9` | Knowledge/discovery core data model — `clue` outcome + persisted fact collection + Observed/Known/Suspected/Confirmed | **done** — `src/knowledge.py`, four-object model, `find_loot()` clue hook |
| 2C.2 | `e3a1e201` | Persist the new discovery state in BOTH serialization paths (`save_profile`/`apply_profile` + JSON). Trace **each** state through death → serialize → restore. | partial — `Knowledge.progress_snapshot()/restore_progress()` built + tested; not yet called from persistence_mixin |
| 2C.3 | `478c2cf9` | Discover-before-understand mechanic (significance deferred until later evidence) | open — `observe_fact()` primitive exists, no generator use yet |
| 2C.4 | `9c2db876` | `look` and `inspect` commands | **done** — `KnowledgeMixin` |
| 2C.5 | `a6de97c0` | `journal` and `remember` commands | **done** — `KnowledgeMixin`, raw-evidence vs. synthesis kept distinct |
| 2C.6 | `1f2c7826` | Map as a knowledge surface — progressive annotation over `print_map()` (pairs with `8f9ec034` / Q3). Grid coordinate labels (a1/b2 style) already landed here. | open |

### 2A — World geometry — world texture, not loop-critical (Phase A)

| Order | ID | Item | File |
|---|---|---|---|
| 2A.1 | `aa461cec` | Bound map size to a gameplay ceiling (~25–33, revisit `MAP_GROWTH_PER_LEVEL` too) | `src/constants.py` |
| 2A.2 | `6c9f672a` | Mountain-boundary Phase 1: force outer ring to `mountain` | `src/mixins/world_mixin.py` |
| 2A.3 | `98ab82c7` | Organic settlements: seed-and-grow footprint instead of fixed box | `src/mixins/world_mixin.py` |
| 2A.4 | `7ecd39cc` | Buildings as landmarks: one-time message when a building enters visibility | `src/mixins/world_mixin.py` |
| 2A.5 | `b31aac00` | Randomize player classification at spawn (inherited V3 mechanic — confirm the 1.1 audit says KEEP before doing it) | `src/mixins/actions_mixin.py` |
| 2A.6 | `2977a8a1` | Loot progression bands — restructure `min_expedition` banding (inherited V3 mechanic; do only if the audit keeps expedition-tiered loot) | `src/constants.py` |

### 2B — Current-engine persistence findings — world texture (Phase A/C-adjacent, concrete bugs)

| Order | ID | Item |
|---|---|---|
| 2B.1 | `93edaf83` | Defeated zombies are never cleared from the map — fix |
| 2B.2 | `6c9a4ca6` | Dropped items are deleted, not placed in the world — fix |
| 2B.3 | `7db3c4b5` | Variable location abandonment states (generated *cause*, not a bool flag) |

### 2D — Zone-dependent ecology — world texture (Phase B/C-adjacent), gated on `457c93a6` surviving Stage 1.2

| Order | ID | Item |
|---|---|---|
| 2D.1 | `1255e24e` | Zone-aware zombie ecology — `_select_zombie_for_encounter()` keyed to zone |
| 2D.2 | `a9c8c83e` | Contextual per-location-type loot tables — `find_loot()` keyed to building type |

---

## Stage 3 — Phase B½: automated investigation harness

Starts **alongside** Stage 4, not after. Depends on 2C's command
interface existing (at least a first version) and on `d3179782`'s
invariants.

| Order | ID | Item |
|---|---|---|
| 3.1 | `9b336876` | Investigation-aware bot policy using the real command interface + player-available info only |
| 3.2 | `7f6d4331` | Mystery/solvability telemetry in the Metrics struct |
| 3.3 | `c1730862` | Per-expedition information-budget reporting against the `MAX_*` invariants |

Prerequisite: the harness realism bugs in Stage H (`7dc71b94`,
`75016734`, `f81aa556`) should be fixed before 3.1 — a bot that cheats
by reading `player.map` directly can't honestly test solvability.

---

## Stage 4 — Phase C: world logic and the escape-mechanism generator

Depends on Stages 2 and 3. Test continuously against Stage 3's harness.

**Mystery-representation contract — settle this before 4.1/4.2, it is
the architectural heart of V4.** The authoritative flow (from
`ESCAPE_WORLD_DESIGN_ASSESSMENT.md` → "Escape proof & causal-chain
validation" and the generator dependency graph):

```
mechanism selected  →  seeds required geography  →  world generated
    →  Escape Proof assembled from the evidence that was actually placed
    →  validated BACKWARD from the escape by ablation + discovery-order runs
```

The Escape Proof is authoritative for *validation*, not a script the
world is reconstructed from. `4.1` (proof structure + validator) lands
before `4.2` (mechanism seed) so the validator exists before there is
anything to validate. If this flow isn't crystal-clear to whoever
starts 4.1, stop and make it clear first.

| Order | ID | Item | Note |
|---|---|---|---|
| 4.1 | `10855536` | Escape Proof data structure + backward causal-chain validation (ablation, discovery-order independence, false-escape, `critical_evidence`/`redundant_evidence`/`single_point_failures`) | **MUST land before 4.2** |
| 4.2 | `53ec9e53` | Escape mechanism as a generation seed (selection before terrain/settlement) | depends on `78921694` + 4.1 |
| 4.3 | `403bf871` `ddd8ce16` `0b052554` `4b0fafcc` | **Generator → win, as ONE end-to-end escape path** — not three sequential abstractions. Town Center: win-trigger → info-rich location; the escape-discovery win condition (which `known_facts` set = "knows how to escape"); mountain-boundary Phase 3 (a pass/tunnel through the ring = the actual route); and the decoy-vs-objective settlement fix (Q6 — `self.settlement_explored` is a single global bool). Build and test as one vertical slice from a generated mystery to a validated escape. | depends on 4.2; Phase B landed |
| 4.4 | `d3179782` | World validation + failure-mode handling (implementation, once the 1.1 invariants are set) | investigate as generation-order changes land |

People / organizations / relationship evidence (`44c1449a`) **moves to
Stage 5** — the slice explicitly cut it, and if the generator produces
satisfying mysteries from places + objects + environmental evidence +
documents alone, People is an expansion mechanism, not a prerequisite.
Only pull it back into Stage 4 if Stage 4 testing shows mysteries feel
hollow without a human layer.

---

## Stage 5 — Phase D/E: campaign narrative

Depends on Stage 4.

| Order | ID | Item |
|---|---|---|
| 5.1 | `44c1449a` | People / organizations / relationship evidence layer (moved from Stage 4 — expansion, not prerequisite; resolve the historical-vs-simulated fork first). Gate: name a concrete capability this unlocks that places + objects + environmental evidence + documents cannot demonstrate. If the answer is "nothing essential," it stays here. |
| 5.2 | `55df661d` | Campaign-as-chapters — narrative framing text per expedition tier |
| 5.3 | `20c9c192` | Real campaign-victory payoff (needs the knowledge layer to have content to reveal) |
| 5.4 | `87dc4cf0` | Deprecate/replace the goal/task system (`go`/`goals`/`complete`/`ts`/`ct`) with the knowledge interaction model (execution of the 1.1 audit's verdict on the goal/task system) |
| 5.5 | `a59a2da5` | Balance-sweep extension for full escape-world campaigns (lower priority) |

**Not phase-gated — slot in any time after 2A.2:**

| ID | Item |
|---|---|
| `ef3e9bf6` | Mountain-boundary Phase 2 — organic/irregular ring instead of uniform 1-tile width |

---

## Stage 6 — Follow-up

| ID | Item |
|---|---|
| `cc49e8e8` | Rewrite `README.md` as a player-facing document once the direction has landed |

---

## Stage H — Track 2: current-engine cleanup (mostly parallel to Track 1)

### H1 — Balance-harness realism bugs (pull forward — Stage 3 depends on these)

| Order | ID | Item |
|---|---|---|
| H1.1 | `7dc71b94` | Bug A (dominant): `_find_town_center()` scans `player.map` directly, no fog-of-war — bot knows the goal instantly |
| H1.2 | `75016734` | Bug B: `_bfs_path()` routes using full-map terrain knowledge |
| H1.3 | `f81aa556` | Bug C: `_step_is_legal()` / `_random_legal_step()` read `player.map` directly for terrain legality |
| H1.4 | `cee4cb36` | Investigation D: combat policy always fights, never flees |

### H2 — Balance-harness protocol & reporting

| ID | Item |
|---|---|
| `2fbb435a` | H: establish two labeled balance-test protocols (combat stress test vs. full campaign) |
| `5de4d6fd` | E: per-expedition-tier survival breakdown in the non-campaign report |
| `d04cd313` | F: per-run player-progression snapshot |
| `3fcea5fe` | G: exploration-specific metrics (buildings entered/searched, settlements found, tiles seen) |

### H3 — Exploration/objective investigation pass (Q1–Q12)

`4b0fafcc` (Q6 — decoy vs. objective settlement, `self.settlement_explored`
is a single global bool) is flagged **THE CORE FIX** and overlaps
directly with Stage 4.4 (Town Center role change) — do it as part of
Stage 4, not here.

`8f9ec034` (Q3 — what a found map reveals now that there are multiple
settlements) is a real change and pairs with 2C.6.

The rest (`121c7b10` Q1, `fb492c15` Q2, `54340f22` Q4, `3b6975b0` Q5,
`20d5281b` Q7, `803192db` Q8, `063f5c8c` Q9, `322ce1e4` Q10,
`8ade9640` Q11, `972de29e` Q12) are mostly "proposed answer is already
true in the current code — confirm and document." Low effort, do in one
sitting whenever; they inform Stage 1's Phase 0 investigation.

`ec98648a` — tune endgame difficulty ramp (expeditions 7–9; only 27%
of campaigns complete all 10). Independent balance tuning; do after H1
(so the harness data is trustworthy).

---

## Invariants that must survive into implementation

These are design decisions that tend to get lost between doc and code.
Each should become an actual test or validator output, not a
behavioural expectation.

1. **Load-bearing evidence cannot be RNG-missed.** Every fact a required
   deduction depends on must either be auto-revealed by ordinary player
   behaviour (enter the tile / `look`) or have multiple independently
   accessible discovery routes. "The object exists on a tile" is not the
   same guarantee as "the player learns the relevant information on
   reaching it." Validator must emit `single_point_failures`; the B½
   harness proves it by knowledge-ablation runs. (`10855536`, `9b336876`)
2. **`remember` is not an oracle.** It may only re-surface information
   the player has already been exposed to. Make "produces no
   previously-unseen information" an explicit test invariant on the
   command. (`a6de97c0`)
3. **Knowledge persistence through death is fully specified.** Trace
   each of Observed / Known / Suspected / Confirmed — plus raw
   observations, interpretations, hypotheses, journal entries, map
   annotations — through death → serialize → restore. The profile
   system and the investigation system must agree on what survives.
   (`e3a1e201`)
4. **World state dies; player knowledge survives.** Once evidence is
   legitimately discovered it stays available even if the physical
   object is later destroyed, moved, or inaccessible. (`ceee7e54`,
   `e3a1e201`)
5. **The final escape action tests the hypothesis, not a flag.** No
   auto-win on reaching a tile;
   `physical_access AND escape_location AND obstacle_resolved AND
   escape_mechanism_confirmed`. `CAN PHYSICALLY REACH` ≠ `IS THE
   GENERATED ESCAPE` ≠ `IS A VALID ESCAPE ATTEMPT`. (`ddd8ce16`,
   `0b052554`)
6. **Discovery order is free.** A mechanism defines relationships and
   constraints, never a sequence; validation simulates multiple
   legitimate discovery orders and confirms the world stays solvable
   regardless. (`53ec9e53`, `9b336876`)
7. **Convenience is a generation failure.** The generator must not
   colocate a deduction's required evidence so tightly that it becomes a
   de facto quest marker. (`d3179782`)

## One-screen summary

```
Stage 0  Vertical slice ............... 138c10f6 dd70ae0c d7a712dc 4f8fdc57 ceee7e54 9f831f9d
         └─ 9f831f9d is the GO/NO-GO gate; agree SLICE-SUCCESS (1.0) before running it
Stage 1  Decision gates .............. 1.0 SLICE-SUCCESS criteria (pre-playtest)
                                       1.1 prereqs: 78921694 182bdc49 d3179782 + V3-assumption audit
                                       1.2 assumed: 457c93a6 (+ open design forks)
Stage 2  Loop first, then texture ... 2C (LOOP): f6d126f9 e3a1e201 478c2cf9 9c2db876 a6de97c0 1f2c7826
                                       2A (texture): aa461cec 6c9f672a 98ab82c7 7ecd39cc b31aac00 2977a8a1
                                       2B (texture): 93edaf83 6c9a4ca6 7db3c4b5
                                       2D (texture, gated on 457c93a6): 1255e24e a9c8c83e
Stage 3  Phase B½ harness ............ 9b336876 7f6d4331 c1730862   (needs H1 first)
Stage 4  Phase C generator .......... 10855536 → 53ec9e53 → [403bf871 ddd8ce16 0b052554 4b0fafcc as ONE path] → d3179782
Stage 5  Phase D/E campaign ......... 44c1449a(People, moved here) 55df661d 20c9c192 87dc4cf0 a59a2da5   (ef3e9bf6 anytime)
Stage 6  Follow-up .................. cc49e8e8

Track 2 (parallel):
Stage H1 harness bugs .............. 7dc71b94 75016734 f81aa556 cee4cb36   (pull forward)
Stage H2 harness reporting ......... 2fbb435a 5de4d6fd d04cd313 3fcea5fe
Stage H3 Q-pass ................... 8f9ec034 + (Q1,Q2,Q4,Q5,Q7-Q12 confirmations) + ec98648a
```
