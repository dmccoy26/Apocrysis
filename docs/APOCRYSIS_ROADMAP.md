# Apocrysis roadmap — from procedural puzzles to a campaign with a spine

Written 2026-08-29. Supersedes `NIGHT_BUILD_PLAN.md` as the top-level
"where is this going" document. `SCENARIO_SEEDS.md` /
`SCENARIO_EXPANSION.md` become **inputs** to this plan (the discovery
grammar); `SESSION_HANDOFF.md` stays the per-session state.

> **SPOILER WARNING.** §2 contains a draft of the world's designed
> truth (not locked — see §10). the brainstorm behind it lives in
> `APOCRYSIS_STORY_ENGINE.md`. If you want to play blind, stop after §1.

---

## 0. Why this document

Apocrysis today is a good **mystery engine** with no **reason to care
about the next map**. It has three progression axes that all answer
small questions:

| axis | question it answers | status |
|---|---|---|
| player level | how capable am I? | live |
| expedition number | what's the next map? | live (framing only, `campaign.py`) |
| mystery | can I escape *this* valley? | live (10 mechanisms) |

It is missing the axis that would make the others mean something:

| **world investigation** | **what happened to the world?** | **this roadmap** |

The fix is not more mechanics. It is a **spine**: one enormous
authored question that every procedural expedition answers a piece of.

---

## 1. The reframe

**Apocrysis is a procedural survival-mystery roguelite about exploring
a region that has gone silent. Every expedition is a self-contained
escape mystery; solving it also recovers one piece of the larger
question — what happened to everyone.**

Three axes, restated:

| axis | question | persistence |
|---|---|---|
| **Player Level** | how capable is this survivor? | resets on death |
| **Map Level** (chapter/depth) | how far into the region have I reached? | resets on death |
| **World Investigation** | how much of the truth have I uncovered? | **persists across deaths** |

**Win condition:** recover enough evidence to determine what happened
to the region's people, identify the source of the last surviving
transmission, reach it, and resolve the truth of the Apocrysis.

**Death is not failure of the campaign.** "That survivor didn't make
it." The World Investigation persists; a new survivor picks up where
the region's knowledge stands. This is the roguelite loop, and it is
what makes permadeath tolerable — you always kept *something*.

The critical design line:

> **The truth is authored. The discovery is procedural.** The
> procedural engine decides *how* a player learns a fact, never *what*
> the fact is.

---

## 1B. Vision — see `APOCRYSIS_STORY_ENGINE.md`

The far end of Apocrysis: a story engine where stories *emerge* from
decisions, motives, consequences, and traces. That whole design space —
the game-vs-engine question, the anthology and the meta-mystery, the
Story Ledger, the death model, the "Trace" causal-model principle, the
eight story-engine primitives — lives in `APOCRYSIS_STORY_ENGINE.md`,
kept separate on purpose so an ambitious future idea can't masquerade
as a near-term requirement.

**This document is the buildable plan.** Two distinctions from the
brainstorm bear on it directly:

- **Vision vs World 1.** World 1 ("The Silence") is a *deliberately
  authored* story whose causal history is **frozen**; procedural
  machinery determines only *how* each player reconstructs it. The
  runtime narrative simulation is the asymptote, not the plan. The
  causal model for World 1 is hand-authored and static — full stop.
- **The Phase A question** is not "what else can we add" — it is:
  *what is the smallest version of the story engine that makes The
  Silence feel like a story rather than a sequence of procedural
  puzzles?* One compelling story, reconstructed through several
  expeditions. Prove that; the rest of the architecture then has
  something worth building around.

The brainstorm flagged a handful of things as **cheap to reserve room
for now** — `WorldSecret` (a `WorldFact` with a `reinterprets` field),
evidence provenance + epistemic status, `faction` tags, treating
`deadline` as the seed of a story clock — and one as **close to
decidable**: `STORY_ENGINE §1D`, the death model (Normal remembers
knowledge, Hardcore remembers actions), a candidate Phase B spec.
Those are folded into §3, §9 and §10 below.

---

## 2. The world spine — world 1: "The Silence" (draft — see §10 and `APOCRYSIS_STORY_ENGINE.md` before building)

### 2.1 The premise: The Silence

One morning a survivor wakes. No people. Zombies. Infrastructure half
up — cars, homes, radio towers, a hospital, evacuation centres,
military checkpoints. Almost nobody left. The survivor does not know
why. **Neither does the game tell them.**

### 2.2 The principle of wrong assumptions

The campaign is built so the player's early conclusions are *earned
and wrong*, disproved in stages:

1. *Everyone was killed by the infected.* → evidence of organised
   evacuation disproves it.
2. *Everyone evacuated.* → evidence that the corridors closed while
   people were still inside disproves it.
3. *The military got them out.* → partly true; the same body then
   sealed the region.
4. *The evacuation was a rescue.* → the seal was scheduled from the
   start. The rescue and the abandonment were one operation.

The apocalypse was **not one event**. It happened in stages, and the
worst stage was the response.

### 2.3 The three mysteries that are one story

| thread | surface question | resolves to |
|---|---|---|
| **The Disappearance** | where did the people go? | most were moved out through a few corridors; the rest were sealed in deliberately |
| **The Dead** | what are the infected? | the region's own people — those who didn't get out, plus the original contained cases; behaviour differs by disease *stage*, not by kind |
| **The Response** | what did the surviving organisations do? | a regional emergency command ran a real evacuation, then sealed the cordon on a timetable to contain the spread — "Phase Two" is the seal |

The player discovers, late, that A + B + C are the same operation seen
from three angles.

### 2.4 The hidden timeline (reconstructed from evidence, never shown)

```
DAY -40   contained incident at a regional research/containment station
DAY -14   containment fails in transit; first cases reach the hospital
DAY -10   hospitals report neurological symptoms; spread outpaces models
DAY -7    emergency services overwhelmed
DAY -5    regional command activates "Protocol Seven" — staged evacuation
DAY -3    consolidation points; blue-sign corridors; convoys begin
DAY -2    communications cut — deliberately, to hold the cordon and the story
DAY -1    last convoys leave; corridors close with people still inside
DAY  0    regional command goes dark. THE SILENCE.
DAY +1    the survivor wakes
```

The `Evidence → Deduction → Hypothesis` model in `src/knowledge.py`
finally has a job: reconstructing this timeline is the campaign.

### 2.5 The twist that keeps it from being "everyone died"

This was a **regional** event. The wider world is intact — it
contained the outbreak by sealing the region off and letting it go
quiet. The cordon still has ears. That matters for the ending.

### 2.6 The endgame

The last surviving transmission is an automated loop from (or near)
the regional emergency command centre. The final expedition reaches
it. What's there — pick one in §10, or make it a player choice:

- **Empty.** The loop is automated. The logs hold the seal order and
  the signature. The player can broadcast the truth outward — the
  cordon is listening — or not.
- **Staffed.** A handful of command personnel, alive since Day 0,
  sealed in with everyone else. They have a way out they never used,
  because using it confirms to the outside that people survived —
  which may trigger a sterilisation of the region.
- **A settlement.** One consolidation point was never evacuated *out*
  — the "evacuation" past it was a lie to keep people walking toward a
  place that could be held. They're still there, walled up, surviving.

Leaning: the command centre holds the **truth**, and the transmission
also points to a **surviving settlement** — the campaign's final act
is reaching the first living humans and deciding what to do with what
you now know.

### 2.7 Milestone discoveries

Not every expedition is "another document." ~7–9 expeditions produce a
**milestone** that reorders the player's understanding:

```
M1  the evacuation was organised, not a rout
M2  it wasn't nationwide — this was a regional event
M3  someone cut communications on purpose
M4  the infected existed before the evacuation
M5  the corridors closed on a schedule, not because they were overrun
M6  the same command that ran the evacuation ordered the seal
M7  the destination past the last checkpoint doesn't exist on any map
M8  someone is still transmitting
M9  there are living people
```

Milestones are authored `WorldFact` nodes flagged `milestone: true`;
the generator guarantees the player meets them in dependency order
across the campaign (§3, §4).

---

## 2B. Architectural principle — the seven layers (2026-08-29)

Locked after a full code-level read (`docs/STRUCTURE_ASSESSMENT.md`).
The engine should keep these **conceptually separate**, even while most
of them are static for World 1:

```
TRUTH        what is actually true about the world?          ← authored
   │
HISTORY      what happened before the player arrived?         ← authored causal model
   │
STATE        what is true about the world right now?          ← mostly generated / static
   │
EXPERIENCE   what physical situation does the player meet?    ← procedural
   │
EVIDENCE     what traces of history/state can be observed?    ← procedural
   │
KNOWLEDGE    what does the player conclude?                   ← player-driven
   │
ACTION       what does the player do?                         ← player-driven
   │
STORY LEDGER what happened during THIS playthrough?           ← recorded
```

**This is not the architecture of the eventual story engine. It is the
architecture of World 1's transition into that engine.** The current
code intertwines these layers because Apocrysis grew organically; that
is acceptable as long as the new seams don't deepen the tangle. The
future engine makes more of the *middle* (STATE / EXPERIENCE / EVIDENCE)
dynamic — World 1 gets to keep them baked.

The mixin `Apocrysis` class is ugly but does **not** currently violate
this boundary in a way that blocks the roadmap, so it stays. The danger
would be a new giant abstraction to "fix" it. Make the new boundaries
**data-oriented** instead:

```
World                          Engine                   Campaign
 ├── Truth                      ├── knowledge             ├── investigation
 ├── Causal history             ├── mystery generation    ├── survivors
 ├── Discovery grammar          ├── world generation      ├── ledger
 ├── geography vocabulary       ├── persistence           └── current world state
 └── world-specific rules       ├── survival
                                └── presentation
```

The single most consequential architectural change is making **"The
Silence" a thing passed *into* the engine** rather than something the
engine implicitly assumes (the `worlds/` seam, Phase A.0). Everything
after that can grow organically. The codebase does not need to become a
beautiful generalised engine now — it needs to become *capable of
becoming one* without making World 1 impossible to ship.

### Phasing this maps to

| layer work | phase |
|---|---|
| `worlds/` seam (`docs/PHASE_A0_SEAM.md`) · `WorldFact` beside the knowledge model · `DiscoveryTemplate` · competing hypotheses · World Investigation persistence · `MechanismFamily` **only as far as `DiscoveryTemplate` needs** | **Phase A** |
| `src/worldgen/` · topology/graph generation replacing rectangular-map assumptions · causal-model → consequence → trace pipeline · the real mystery solver · **consider** a SQLite-backed `WorldStore` (see `PHASE_A_DECISIONS.md` — only once World 1's persistent shape is known) | **Phase C** |
| `WorldState` transitions · reactive actors · faction behaviour · player-caused mysteries · simulation-driven branching · **ChromaDB** as a semantic index over the authoritative store (never as source of truth) | **Later** (post-Phase E) |

### Pre-Phase-A cleanup (obsolete weight, not a refactor)

"Don't refactor prematurely" and "remove dead weight" are not in
tension. Before Phase A.0, establish a clean baseline:

1. verify slice mode has no remaining callers
2. delete the slice implementation + its `slice_mode` guards
3. split `test_apocrysis.py` (1990 lines) with **no behaviour change**
4. run the full suite (`--test` + pytest)
5. commit that as the clean baseline
6. then begin Phase A.0

---

## 3. Architecture: fixed truth + procedural discovery

### 3.1 World truth = a DAG of `WorldFact`s

> **Story-engine §1E revises this.** The brainstorm argues the DAG should be authored
> *against a causal model* (events → consequences → traces), and the
> generator should derive the expedition puzzle from a consequence with
> a hidden causal link. Treat what follows as the minimum shape; STORY_ENGINE §1E is
> the richer target.

A new authored data structure (location depends on the STORY_ENGINE §1B.14 seam
decision — `src/world_truth.py` or `worlds/silence/truth.py`):

```python
WorldFact(
    id="RESPONSE_SEAL_SCHEDULED",
    thread="response",                 # disappearance | dead | response
    chapter=4,
    milestone=True,
    statement="The corridor closure was on a timetable from the start.",
    needs=["RESPONSE_CORDON_EXISTED", "DISAPPEARANCE_LEFT_BEHIND"],
    discovery_templates=[               # >=2 procedural ways to learn it
        DiscoveryTemplate(family="corroborative", roles=..., evidence=...),
        DiscoveryTemplate(family="informational", roles=..., evidence=...),
        DiscoveryTemplate(family="sequential",    roles=..., evidence=...),
    ],
)
```

- The **DAG** is fixed. The **discovery templates** are the procedural
  surface: each is a recipe for embedding that fact into a generated
  map as an escape mystery of a given family.
- `needs` enforces revelation order: `RESPONSE_SEAL_SCHEDULED` can't be
  offered until its prerequisites are `KNOWN`.
- One expedition targets **one** un-known `WorldFact` whose `needs` are
  all met, picks one of its `discovery_templates` (weighted by variety
  rules A/B/C, extended to template signatures), and hands that to
  `build_mystery`.

### 3.2 The knowledge model, promoted to world scope

`src/knowledge.py`'s `Fact / Evidence / Deduction / Hypothesis` already
does exactly this at expedition scope. Two changes:

- **`Deduction` earns its keep.** Today it's near-vestigial (every
  chain is linear). World facts frequently need *corroboration* — two
  independent records that agree — so `Deduction(needs=[A,B])` becomes
  load-bearing. This is the `two_maps_agree` seed, generalised.
- **Hypotheses can compete.** `Knowledge` holds a *set* of world
  hypotheses with support/confidence; "confirmed" becomes "the player
  committed, and was right — or wrong." A wrong commitment costs an
  expedition's worth of investigation and sends the player down a
  correction arc. That is a far better failure mode than starving on
  the walk out, and it ties the knowledge model to the campaign stakes.

### 3.3 Persistent state

Three new persisted structures (same class-var + profile pattern as
`_used_mechanisms` / `_recent_signatures`, see commit `73ff535` and
`748c40a`):

| structure | holds | affects |
|---|---|---|
| **World Investigation** | which `WorldFact`s are `KNOWN` / `SUSPECTED`, per-thread % | which fact the next expedition targets; the endgame gate |
| **Survivor Knowledge** | things *players* have learned that carry: "infected avoid certain sounds", "Protocol Seven marked routes with blue signs", "frequencies changed after Day 3" | small, non-power-creep expedition effects (a blue sign on the map is legible; a known frequency skips a step) |
| **Story fragments** | flavour lore collected but not load-bearing (§6 optional evidence) | the World Investigation screen; nothing mechanical |

All three **survive death**. Player level, gear, and the current
chapter's map do not.

### 3.4 The roguelite loop

```
        WORLD INVESTIGATION  (persists)
                  |
   new survivor, level 1, chapter = furthest reached
                  |
        expedition: escape mystery that also
        targets one un-known WorldFact
                  |
        solve it -> fact KNOWN, investigation advances
        die      -> "that survivor didn't make it"; investigation stands
                  |
        endgame unlocks when the three threads pass their
        chapter thresholds and M8 (still transmitting) is KNOWN
```

---

## 4. The three axes in detail

### Player Level — unchanged
Strength / weapons / survival capability. Resets on death. The frozen
balance stays frozen; this axis is not where the campaign lives.

### Map Level — chapters (new)
Replaces `campaign.py`'s pure-framing chapter lines with real
structure. ~20–26 expeditions, grouped:

```
CH1  THE SILENCE      maps 1–5    why did everyone disappear?
CH2  THE INFECTED     maps 6–9    where did the infected come from?
CH3  THE EVACUATION   maps 10–14  where were the survivors taken?
CH4  THE RESPONSE     maps 15–19  who ordered the seal, and why?
CH5  THE LAST SIGNAL  maps 20–24  is anyone still alive?
FIN  THE TRUTH        map 25/26   reach the source
```

Chapter gates depth: CH1 is rural valleys; by CH4 you're reaching
regional command infrastructure. Map *size* stops being `15 + 3×n` and
becomes a function of the chapter's target playable-tile budget and
the targeted fact's critical-path length (§5, map-v2).

### World Investigation — the spine (new)
Per-thread completion, driven by `WorldFact`s reaching `KNOWN`. The
endgame unlocks on thresholds, not on a raw expedition count. Surfaced
by the World Investigation screen (§8).

---

## 5. Map generation v2 — the inverted pipeline

The current pipeline:

```
rectangular grid -> paint terrain -> place mystery sites -> carve exit gap
```

The target pipeline:

```
targeted WorldFact + chosen discovery template
        -> [STORY_ENGINE §1E: causal model -> a consequence with a hidden link -> the expedition puzzle]
        -> required geography (the template / consequence declares it)
        -> connectivity graph  (nodes: spawn, exit, sites; edges: distance, chokepoint, encounter-risk)
        -> critical-path budget check  (does the story fit the chapter's travel budget?)
        -> terrain realisation  (realise the graph as an irregular valley on a 34x34 array)
        -> mystery embedding  (place traces + the puzzle onto the realised graph)
```

The `[STORY_ENGINE §1E: ...]` step is the brainstorm target; without it the
pipeline still works with `DiscoveryTemplate` as a flat "family +
roles + evidence" recipe.

### Key points

- **Topology is the unit of work; shape and size fall out of it.** You
  generate a connectivity graph first, then realise it as terrain. The
  crescent / basin / peninsula / two-lobed shapes are *consequences* of
  the graph, not inputs.
- **Irregular playable masks, rectangular storage.** Keep the 34×34
  array. Flood-fill a valley region; mountain-fill the rest. The engine
  is already reachability-based (`_reachable_from`, `_ensure_reachable`,
  `_building_sites` all walk passable terrain, not array bounds), so an
  irregular mask is *already representable* — ~250–750 playable cells in
  a 1156-cell array.
- **Critical-path budget is a graph property**, known before a tile
  exists. A simple spatial mystery needs `spawn→clue→key→gate`; a combo
  needs `spawn→evidence→infrastructure→vehicle→exit`. The chapter sets
  the budget; the graph generator fits the story inside it. This is
  also the permanent fix for "solved it, died on the trek."
- **Story-aware terrain.** `river_leads_out` declares "needs: a river
  reaching the perimeter." `lift_bridge` declares "needs: a gorge."
  `tidal_causeway` declares "needs: a coastal boundary." `power_station`
  declares "needs: infrastructure adjacent to a plausible power
  source." The generator satisfies the constraint; it doesn't discover
  water conveniently nearby afterward.

### What this breaks (it's a branch, not a patch)

- `_carve_escape_pass` hard-codes the array edge as the boundary
  (`for i in range(1, n-1)` over four sides). With an irregular mask the
  boundary is the *mask perimeter* — full rewrite.
- The pacing heuristics in `build_mystery` (`_detour`, `_from_spawn`,
  the spawn→exit band logic) assume a compact rectangular field —
  replaced by graph-native path budgeting.
- Most of `test_escape.py` ("every seed produces a valid reachable
  mystery") — rewritten against the graph model.
- `build_mystery` becomes a from-scratch v2 with a compatibility bridge
  so the current 10 mechanisms keep working during the transition.

### Acceptance test for map-v2

> The **same generated valley** can host **at least two different
> mysteries** and feels like a different expedition each time.

That is the thing that proves map and mystery are generated *together*
rather than one decorating the other. Automatable.

---

## 6. The scenario matrix becomes a discovery grammar

> **Story-engine §1F reframes this.** The discovery grammar is *one of eight engine
> primitives* (STORY_ENGINE §1F.1), not the organising one — it answers "how does
> the player learn", while Story Grammar / Actors / Motives answer
> "what happened and why". This section stays valid; it's just no
> longer the top of the stack.

Each family stops being "a random puzzle" and becomes **a way of
discovering history**:

| family | discovery question in campaign context |
|---|---|
| spatial | where did the evacuation road actually go? |
| infrastructural | why was the emergency power still running here? |
| experimental | which containment valve was activated? |
| informational | who sent this transmission, and when? |
| corroborative | do these two records together prove the seal was scheduled? |
| sequential | where did the evacuation network lead? |
| environmental | why did the flood expose this facility? |
| transportation | can I get this vehicle running to reach the next site? |
| time-pressure | can I reach the evacuation point before the cordon sweep? |

`SCENARIO_SEEDS.md`'s seeds get re-tagged with **which `WorldFact`(s)
each can plausibly carry**. Build priority in `SCENARIO_EXPANSION.md`
is re-ranked by *coverage of the world DAG*, not just
new-question-per-machinery.

**Optional evidence** (`Evidence(supports=[])`, already handled by the
knowledge model) becomes the mechanism for **world history without
mechanical necessity**: 2–4 non-load-bearing fragments per map,
drawn as a *consistent subset* from a per-region "valley file", collected
into the World Investigation screen. This is the highest
identity-per-effort lever and it works on the current engine today.

---

## 7. Solvability verification — a build-time track

Every item in this roadmap makes mysteries harder to *prove solvable*:
competing hypotheses, optional evidence, corroboration gates, region
mutation, world-fact dependency ordering. A hand-written `validate()`
can't keep up, and the balance bot reads `m.correct_control` /
`m.sites` directly — it's a comprehension proxy, not a solver.

`tools/mystery_solver.py` (172 lines today) grows into a real solver
that, given **only** the evidence and the realised world, proves the
targeted `WorldFact`'s hypothesis is reachable — run as a build-time
gate beside `Mystery.validate()` and `_assert_directional_truth`.
Without it, map-v2 + uncertainty is untestable generation. Start early.

---

## 8. The World Investigation screen

A new top-level view (`w` from the `>` prompt, and shown between
expeditions):

```
╔═══════════════════════════════════════════════╗
║              THE APOCRYSIS                     ║
╠═══════════════════════════════════════════════╣
║  THE SILENCE            ████████████░░░░  58%  ║
║  What happened to the people?                  ║
║    ✓ the evacuation was organised              ║
║    ✓ multiple corridors existed                ║
║    ? where did they lead                       ║
║    ? why did communications stop               ║
║    ? who ordered it                            ║
║                                               ║
║  THE INFECTED           █████░░░░░░░░░░░  24%  ║
║    ? where did the infection begin             ║
║    ? why do early and late infected differ     ║
║                                               ║
║  THE RESPONSE           ██░░░░░░░░░░░░░░  11%  ║
║                                               ║
║  Survivor knowledge (carries forward):         ║
║    · infected are drawn to sustained noise      ║
║    · Protocol Seven routes are blue-signed      ║
╚═══════════════════════════════════════════════╝
```

This replaces `EXPEDITION 7 / LEVEL 23 / NEXT EXPEDITION` as the thing
the player looks at between runs. The retention question shifts from
"what's the next map?" to "what am I going to find out next?"

---

## 9. Build sequence

Value ships in every phase. The two expensive tracks (map-v2, the
authored world DAG at full size) run **behind** cheaper wins, not in
front of them.

### Phase A — the spine, on the current engine
*No map-v2. Prove the loop is compelling before rebuilding generation.*

0. **The `World` seam (STORY_ENGINE §1B.14).** Before any content: a thin interface
   so "world 1" and "the engine" are separable — `worlds/silence/`
   holds the encounter table, tile vocabulary, prose voice, `WorldFact`
   DAG, and ending logic; the engine takes a `World`. Costs a handful
   of indirections now, saves a fork later. Do this even if there is
   only ever one world.
1. `worlds/silence/truth.py` — the `WorldFact` DAG, **CH1 + CH2 only**
   (~10 facts, ~3 milestones). Enough truth to build toward.
2. `DiscoveryTemplate` — bind a `WorldFact` to an existing MECHANISMS
   family + role labels + evidence text. `build_mystery` gains a
   `target_fact` path that overrides the random mechanism pick.
3. World Investigation persistent state + profile round-trip.
4. The World Investigation screen (§8).
5. `campaign.py` chapter intros keyed to World Investigation progress,
   not raw `expeditions_completed`.
6. Milestone discovery banner — the "wait, they didn't all die" beat.

**Ships:** a 8–10 expedition mini-campaign with a real question and a
persistent answer, on today's maps.

### Phase B — the roguelite loop
1. Death → "that survivor didn't make it"; World Investigation +
   Survivor Knowledge persist; new survivor at level 1, current chapter.
2. Survivor Knowledge: 3–5 entries, each with one small legible
   expedition effect (blue signs, known frequency, sound behaviour).
3. Optional evidence + per-region valley file (§6) — world history that
   isn't mechanically required.

**Ships:** dying stops feeling like a rollback.

### Phase C — map-v2 (parallel branch, starts during Phase A)
1. Connectivity-graph generator + critical-path budgeting.
2. Irregular playable mask; `_carve_escape_pass` rewrite for
   mask-perimeter exits.
3. Terrain realisation from the graph.
4. `build_mystery` v2 with a compat bridge for the 10 existing
   mechanisms.
5. Story-declared geography requirements on discovery templates.
6. `mystery_solver.py` → real solvability gate (§7), landed with C4.

**Ships:** the "I played three times and I don't know how it keeps
coming up with these situations" bar.

### Phase D — world conditions + mutation
1. Unified `world_conditions` (time-of-day + weather + tide as one
   system mechanisms read as puzzle inputs) — merges the `#12/#13`
   ideas into one system, not three.
2. Region mutation — solving an environmental mystery flips a tile-set
   impassable→passable. The "★ THE WATER IS RECEDING" beat.
3. `escape_kind` — leave from the vehicle / the far side of the bridge,
   not always a mountain gap.

### Phase E — the endgame
1. CH3–FIN of the `WorldFact` DAG (~15 more facts).
2. Competing world hypotheses + the wrong-commitment correction arc
   (§3.2).
3. The final expedition: less procedurally random, realised from the
   player's *own* discovered information; the designed truth revealed;
   the ending choice (§2.6).

### Dependency graph

```
Phase A ──> Phase B ──────────────> Phase E
   │                                  ▲
   └──> Phase C ──> Phase D ──────────┘
        (parallel branch)     (needs C's build_mystery v2)
```

NPCs / a living world are **not** on this graph. A moving NPC means
evidence gains a when/where-available dimension — the world has to
tick — which is an architecture change to the knowledge model. Park it
after Phase E.

---

## 10. Open decisions — lock before the phase that needs them

| decision | needed by | notes |
|---|---|---|
| **game vs engine (STORY_ENGINE §1B.1, A–E)** | **Phase A step 1** | decides whether `world_truth.py` is a file or `worlds/silence/` is a `World` module. Recommendation: build behind a thin `World` seam regardless (STORY_ENGINE §1B.14) |
| the exact truth for world 1 (`WORLD_TRUTH_CANDIDATES.md` A/B/C) | Phase A | scope locked (~25 / 5 chapters + finale); candidate not yet picked |
| the exact truth (§2) — ratify or rewrite | Phase A | the DAG can't be authored until the ending is chosen |
| the ending shape (§2.6) — empty / staffed / settlement / choice | Phase A (structure), Phase E (content) | leaning: truth at command centre + settlement as the final act |
| chapter count and maps-per-chapter | Phase A | draft: 5 chapters + finale, ~4–5 maps each, ~25 total |
| what carries forward on death, exactly | Phase B | **STORY_ENGINE §1D has a strong candidate answer** — three persistence tiers (Knowledge always / Narrative selected / Mechanical never) + Survivor-Network respawn. Promote STORY_ENGINE §1D to a Phase B spec; ratify or amend |
| the region's stability window (STORY_ENGINE §1E.10) | Phase A/B | draft: the region is stable for a whole campaign, regenerates only on a new campaign — needed so retroactive-meaning / revisit works |
| does the causal model (STORY_ENGINE §1E) land in world 1, or is world 1 fact-DAG-only? | Phase A step 1 | shallow causal model (1–2 hops) vs deferring it entirely; big scope lever |
| does a wrong hypothesis commitment cost a whole expedition, or just a correction beat? | Phase E | affects how punishing the mid-game feels |
| is the wider world's cordon a background fact or does the player get to act on it (broadcast outward)? | Phase E | changes whether the ending is discovery or decision |
| Survivor Knowledge effects — how many, how strong (must not become power creep) | Phase B | hard cap; each must be *legibility*, not *strength* |

---

## 11. Relationship to existing docs

- `APOCRYSIS_STORY_ENGINE.md` — the far-horizon design space (the
  brainstorm, §1B–§1F). Deliberately kept separate so it can be
  ambitious without leaking near-term requirements into this plan.
  Bare `§2`–`§11` refs in that doc point back here.
- `WORLD_TRUTH_CANDIDATES.md` — the three candidate truths for world 1
  ("The Silence"); the story-engine doc reframes these as *world 1*,
  not *the* truth. Spoiler-gated. The §10 decision picks one.
- `NIGHT_BUILD_PLAN.md` — done, superseded by this. Its Phase-5
  variety rules are live and feed §3.1.
- `SCENARIO_SEEDS.md` — becomes the discovery-grammar catalogue; seeds
  get a "carries WorldFact(s)" tag (§6).
- `SCENARIO_EXPANSION.md` — its 5 levels of randomness and variety
  rules stay; build priority re-ranks by world-DAG coverage.
- `ESCAPE_STORY_SCHEMA.md` / `PLAYER_UNDERSTANDING.md` — unchanged; the
  UX rules and the no-vocab-leak invariant apply to `WorldFact` prose
  too (the player never sees `thread: response`).
- `BALANCE_BASELINE_2026-08-28.md` — the frozen numbers stay frozen
  through every phase here. This roadmap adds *reasons to play*, not
  survival tuning.
- `SESSION_HANDOFF.md` — per-session state; each phase updates it.

---

## The bar

Not "Apocrysis has 50 scenarios." The bar is: **a player finishes
Apocrysis, and along the way stops thinking "what's the next map?" and
starts thinking "I need to know what happened."**
