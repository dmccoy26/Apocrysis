# Apocrysis roadmap — from procedural puzzles to a campaign with a spine

Written 2026-08-29. Supersedes `NIGHT_BUILD_PLAN.md` as the top-level
"where is this going" document. `SCENARIO_SEEDS.md` /
`SCENARIO_EXPANSION.md` become **inputs** to this plan (the discovery
grammar); `SESSION_HANDOFF.md` stays the per-session state.

> **SPOILER WARNING.** Section 2 contains a draft of the world's
> designed truth. It is not locked (see §10). If you want to play blind,
> stop after §1.

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

## 1B. Open horizon — brainstorm, not decided

*This section captures a live brainstorm. Nothing here is committed.
It exists so the decisions we make for §2–§9 don't quietly foreclose a
much larger design space. Read §1B.9 for what it changes about
decisions being made now.*

### 1B.1 The question under the question

We are no longer really arguing about "should Apocrysis have 25 maps."
The real question is **what is an Apocrysis game**:

| | |
|---|---|
| A | one zombie game with an infinite procedural campaign |
| B | one persistent universe with multiple campaigns |
| C | a procedural mystery/adventure **engine** with different authored worlds |
| D | a multiplayer procedural escape-room **platform** |
| E | some combination |

**C + D** is the interesting frame: *Apocrysis is a system for
generating cooperative adventure mysteries.* Under that framing
"zombie apocalypse" is not the product — it is **the first world built
with the engine**. Everything in §2 (The Silence / Cordon / Quiet /
Handoff) becomes *world 1*, not *the campaign*.

### 1B.2 Separate the layers — there are more than three

§1 named three axes. The full set is five:

| layer | question | authored or generated | persistence |
|---|---|---|---|
| **World type** | which story am I playing? | authored (a world pack) | chosen at start |
| **Campaign / World Investigation** | how much of *this world's* truth have I uncovered? | authored DAG, generated discovery | persists across deaths |
| **Chapter** | how deep into the story am I? | authored (chapter gates) | persists across deaths |
| **Expedition difficulty** | how hard is *this* map/mystery? | generated, *derived from chapter* | per expedition |
| **Player level** | how capable is this survivor? | generated | resets on death |

§1's "Map Level" splits: **chapter** (narrative depth, persists) vs
**expedition difficulty** (derived from the chapter, per-run).
Difficulty stops being a number you grind and becomes *a consequence
of where you are in the story*.

### 1B.3 Apocrysis as a story engine

```
╔══════════════════════════════════════════╗
║                 APOCRYSIS                ║
║  CHOOSE YOUR WORLD                        ║
║  > THE SILENCE   a region has gone quiet  ║
║    THE DERELICT  your ship arrived        ║
║                  somewhere no one was     ║
║    THE FORGOTTEN REALM  the kingdom is    ║
║                         dying             ║
║    ???                                    ║
╚══════════════════════════════════════════╝
```

The engine does not care whether the world contains zombies, mutants,
goblins, robots, cultists, or traps. The loop underneath every world
is the same:

> **explore → discover → reason → survive → solve → progress the story**

Three world sketches (all: same loop, same knowledge model, same
generation stack; different pack):

- **THE SILENCE** — zombie survival mystery. *Where did everyone go?*
  (§2, world 1.)
- **THE DERELICT** — sci-fi. You wake on a damaged colony ship;
  everyone is gone; something still answers the comms. The crew didn't
  disappear — they **changed**. "Zombies" become mutated crew;
  "valleys" become decks and sealed compartments.
- **THE FORGOTTEN REALM** — fantasy. Abandoned villages, monsters on
  the roads, failing wards, ancient texts that contradict each other.
  *Why is the kingdom dying?* The heroes didn't defeat the old evil —
  they **joined** it.

### 1B.4 The generation stack

```
WORLD          authored  (a data pack: encounter table, tile vocabulary,
  │                        prose voice, the WorldFact DAG)
  └── CAMPAIGN        authored  (the overarching mystery = the DAG)
       └── CHAPTER    authored  (chapter gates + framing)
            └── MAP           generated  (topology → terrain)
                 └── MYSTERY  generated  (a discovery template, realised)
                      └── EVIDENCE   generated  (clue placement)
                           └── ENCOUNTER  generated  (hazards, NPCs, the Dead)
```

The truth is authored at the top four levels; the *experience of
discovering it* is generated at the bottom four. A "world" is a data
pack over a shared engine — that is what makes world 2 cheap instead
of a rewrite.

### 1B.5 Progression is discovery-based, not map-count

The player advances because *"you discovered something important,"*
not because *"you completed Expedition 14."* The World Investigation
screen (§8) shows % per thread. The player does not necessarily know
how many expeditions remain.

Death → **the world remembers**. Survivor #1 learns "the evacuation
was organised" and dies at chapter 4. Survivor #2 starts at chapter 4
with that knowledge (but #1's gear is gone), reads things #1 couldn't,
gets further, dies. Survivor #3 inherits both discoveries. "Damn, I
died, start over" becomes "okay — we know why they closed the routes
now; what's next."

### 1B.6 Multiple endings

```
              FINAL TRUTH
                   │
        ┌──────────┼──────────┐
      EXPOSE    PROTECT     LEAVE
        │          │          │
     ENDING A   ENDING B   ENDING C
```

Accumulated discoveries gate which choices are *available*. Some
endings require **optional** investigations — the player finishes the
main story and realises "I never found out what happened at that
hospital," which is an invitation to replay. Per-world.

### 1B.7 Multiplayer — a separate axis

A procedural cooperative escape room, 2–4 players. The key is
**information asymmetry**: players hold *different* evidence and must
talk to combine it.

> Player A finds an evacuation map: *blue route → north.*
> Player B finds a maintenance log: *blue routes abandoned after the
> second convoy.*
> Now they are **discussing the puzzle**, not each independently
> clicking things.

The knowledge model already has the shape for this: `Evidence →
Deduction → Hypothesis`. Multiplayer distributes the `Evidence` nodes
across players; the `Deduction` only lands when they pool what they
have. Treat it as its own track — **not core now** — but note the
architectural constraint in §1B.9.

### 1B.8 Vocabulary

Settle on: **World · Campaign · Chapter · Expedition**, with **player
level** orthogonal to all of them. Stop saying "map level" — a level-23
character can be on *Chapter 3, Expedition 11* of *The Silence*, or
*Chapter 7, Expedition 3* of *The Derelict*.

### 1B.9 What this changes about decisions being made now

- **The A/B/C truth candidates (`WORLD_TRUTH_CANDIDATES.md`) are
  candidates for *world 1 ("The Silence")*, not "the Apocrysis
  truth."** Choosing one does not lock the engine to zombies.
- **Resolve the game-vs-engine question (A–E) before Phase A step 1.**
  It decides whether `world_truth.py` is a single file or
  `worlds/silence/` is a module implementing a `World` interface
  (encounter table, tile vocabulary, prose voice, `WorldFact` DAG,
  win/ending logic).
- **Recommended regardless of the answer:** build Phase A behind a thin
  `World` seam even if there is only one world for a long time. The
  cost is a handful of indirections; the payoff is that world 2 is a
  data pack, not a fork. This is the cheapest insurance against
  regretting a hardcoded "zombie" assumption later.
- **If multiplayer is ever wanted:** the `Evidence / Deduction /
  Hypothesis` refactor in Phase E must be **single-observer-agnostic
  from the start** — no assumption that one player has seen everything,
  and the solvability solver (§7) must reason about "is this solvable
  by the *group's* pooled evidence," not one observer's.

### 1B.10 The honest status

This is bigger than a night's work and it is not decided. The near-term
plan (§9 Phase A) still holds — *prove the discovery loop is
compelling on world 1 before building the platform under it*. But
build it with §1B.9 in mind, so "world 1" and "the engine" are
separable from the first commit.

---

## 2. The world spine — world 1: "The Silence" (draft — see §10 and §1B before building)

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

## 3. Architecture: fixed truth + procedural discovery

### 3.1 World truth = a DAG of `WorldFact`s

A new authored data structure (location depends on the §1B.9 seam
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
        -> required geography (the template declares it)
        -> connectivity graph  (nodes: spawn, exit, sites; edges: distance, chokepoint, encounter-risk)
        -> critical-path budget check  (does the story fit the chapter's travel budget?)
        -> terrain realisation  (realise the graph as an irregular valley on a 34x34 array)
        -> mystery embedding  (build_mystery places evidence onto the realised graph)
```

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

0. **The `World` seam (§1B.9).** Before any content: a thin interface
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
| **game vs engine (§1B.1, A–E)** | **Phase A step 1** | decides whether `world_truth.py` is a file or `worlds/silence/` is a `World` module. Recommendation: build behind a thin `World` seam regardless (§1B.9) |
| the exact truth for world 1 (`WORLD_TRUTH_CANDIDATES.md` A/B/C) | Phase A | scope locked (~25 / 5 chapters + finale); candidate not yet picked |
| the exact truth (§2) — ratify or rewrite | Phase A | the DAG can't be authored until the ending is chosen |
| the ending shape (§2.6) — empty / staffed / settlement / choice | Phase A (structure), Phase E (content) | leaning: truth at command centre + settlement as the final act |
| chapter count and maps-per-chapter | Phase A | draft: 5 chapters + finale, ~4–5 maps each, ~25 total |
| what carries forward on death, exactly | Phase B | draft: World Investigation + Survivor Knowledge + story fragments; **not** level/gear/chapter-map |
| does a wrong hypothesis commitment cost a whole expedition, or just a correction beat? | Phase E | affects how punishing the mid-game feels |
| is the wider world's cordon a background fact or does the player get to act on it (broadcast outward)? | Phase E | changes whether the ending is discovery or decision |
| Survivor Knowledge effects — how many, how strong (must not become power creep) | Phase B | hard cap; each must be *legibility*, not *strength* |

---

## 11. Relationship to existing docs

- `WORLD_TRUTH_CANDIDATES.md` — the three candidate truths for world 1
  ("The Silence"); §1B reframes these as *world 1*, not *the* truth.
  Spoiler-gated. The §10 decision picks one.
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
