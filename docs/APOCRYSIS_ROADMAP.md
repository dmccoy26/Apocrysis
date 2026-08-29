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
much larger design space. Read §1B.14 for what it changes about
decisions being made now, and §1B.15 for the questions still open.*

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

§1 named three axes. Broken out fully there are five layers, and four
of them are *numbers the player can watch*:

| layer | question | authored/generated | persistence |
|---|---|---|---|
| **World type** | which story am I playing? | authored (a world pack) | chosen at start |
| **Investigation** — how much do I understand? | per-thread % (`Disappearance 72% · Infected 41% · Response 18%`) | authored DAG, generated discovery | persists across deaths |
| **World depth** — how far into the mystery have I penetrated? | a single number, gates chapter framing + difficulty | authored gates | persists across deaths |
| **Expedition** — what am I doing right now? | run number within the current push | generated | per expedition |
| **Survivor level** — how capable am I? | strength / gear / skills | generated | resets on death |

A player could be *Survivor 23 · Expedition 14 · Depth 4 ·
Investigation 61%* — and those four numbers tell four different
stories. "Chapter" is the *narrative face* of World depth (Depth 4 →
"Chapter 4: The Response"); they may be one axis viewed two ways, or
two axes if optional side-investigations can raise Investigation
without raising Depth. Open (§1B.15 Q8).

The important shift: **expedition difficulty stops being a number you
grind and becomes a consequence of World depth** — of where you are in
the story.

### 1B.3 Apocrysis as a story engine

```
╔══════════════════════════════════════════╗
║                 APOCRYSIS                ║
║  CHOOSE YOUR WORLD                        ║
║  > THE SILENCE   ☑ truth uncovered  23/25 ║
║    THE DERELICT  □ unexplored             ║
║    THE FORGOTTEN REALM  □ unexplored      ║
║    ???           □ unknown                ║
╚══════════════════════════════════════════╝
```

The engine does not care whether the world contains zombies, mutants,
goblins, robots, cultists, or traps. The loop underneath every world
is the same:

> **explore → discover → reason → survive → solve → progress the story**

Same loop, same knowledge model, same generation stack; the *world
pack* changes everything the player sees:

| | THE SILENCE (world 1) | THE DERELICT | THE FORGOTTEN REALM |
|---|---|---|---|
| genre | post-apoc survival mystery | sci-fi horror / exploration | fantasy mystery / adventure |
| player fantasy | "figure out what happened" | "something happened to this ship" | "something is wrong with this kingdom" |
| the Dead | the infected | mutated crew | monsters / the cursed |
| threats | infection · starvation · dark · terrain | hull breach · O₂ · radiation · auto-defences | curses · traps · wards · weather |
| the mystery | where did everyone go? | why did the crew change? | why is the kingdom dying? |
| map vocabulary | valley · town · dam · ridge · marina | Command · Engineering · Cryo · Cargo · Research | forest · village · crypt · castle · swamp · temple |
| the twist shape | the rescue *was* the abandonment | the crew didn't vanish, they changed | the heroes didn't win — they joined it |

### 1B.4 The generation stack

```
WORLD          authored  (a data pack: encounter table, tile vocabulary,
  │                        prose voice, survival-pressure module, the WorldFact DAG)
  └── CAMPAIGN        authored  (the overarching mystery = the DAG)
       └── CHAPTER    authored  (depth gates + framing)
            └── MAP           generated  (topology → terrain)
                 └── MYSTERY  generated  (a discovery template, realised)
                      └── EVIDENCE   generated  (clue placement)
                           └── ENCOUNTER  generated  (hazards, NPCs, the Dead)
```

The truth is authored at the top; the *experience of discovering it*
is generated at the bottom. A "world" is a data pack over a shared
engine — that is what makes world 2 cheap instead of a rewrite.
**Caveat (from §1B.14):** the survival layer is deeply tuned (the
frozen balance) and hard to genericise, so a world pack realistically
ships its own survival-pressure module too — a bigger pack interface
than "just text and tiles."

### 1B.5 Progression is discovery-based, and the world remembers

The player advances because *"you discovered something important,"*
not because *"you completed Expedition 14."* The World Investigation
screen (§8) shows % per thread. The player does not necessarily know
how many expeditions remain.

Death → **the world remembers**. Survivor #1 learns "the evacuation
was organised" and dies at Depth 4. Survivor #2 starts at Depth 4 with
that knowledge (but #1's gear is gone), reads things #1 couldn't, gets
to Depth 7, dies. Survivor #3 inherits both discoveries. "Damn, I
died, start over" becomes "okay — we know why they closed the routes
now; what's next." Whether a dead survivor leaves *more* than
knowledge — a journal, an unlocked door, a body with their last
evidence on it — is the async-multiplayer hook in §1B.10.

### 1B.6 The win condition is a decision, not a map count

25 expeditions is a **pacing mechanism, not the win**. The real win
condition:

> **Understand the truth well enough to make the final decision.**

The final expedition isn't "the hardest map." It's the point where the
game asks you to *act on everything you've learned*:

```
             YOU KNOW
       WHAT / WHO / WHY
                │
          FINAL EXPEDITION
                │
        ┌───────┼───────┐
      EXPOSE  PROTECT  LEAVE
```

That's a genuine ending, not a victory screen. It also means the game
*can't* be won by grinding — you can only end it by understanding it.

### 1B.7 Multiple endings

Accumulated discoveries gate which choices at §1B.6 are *available*.
Some endings require **optional** investigations — the player finishes
the main story and realises "I never found out what happened at that
hospital," which is an invitation to replay. Per-world.

### 1B.8 One story, or many? The meta-mystery

The worlds needn't be unrelated genres. Possibilities, escalating in
ambition:

- **Independent.** Three self-contained stories, no connection. Safest.
- **Thematic echo.** Same *shape* of twist (a betrayal disguised as a
  rescue) across genres; no diegetic link.
- **Connected — the meta-mystery.** World 1's outbreak "wasn't
  natural." World 2's ship carried samples "from the same research
  programme." World 3 looks like pure fantasy — until the player finds
  a piece of technology, or an inscription that names something from
  the other worlds. The player realises: *these aren't three games,
  they're three pieces of one mystery.* The `WorldFact` DAGs share
  nodes; solving world 1 partially reveals a fact that only completes
  in world 3.

```
                 APOCRYSIS
        ┌────────────┼────────────┐
     WORLD 1      WORLD 2       WORLD 3
   THE SILENCE  THE DERELICT  THE FORGOTTEN REALM
        │            │             │
     campaign     campaign      campaign
        └────────────┼─────────────┘
                     │
               SHARED TRUTH  (the meta-mystery)
```

**Payoff:** retention transcends any single world — "what kind of
world is next, and how does it connect?" **Risk:** reads as a gimmick
if the connection isn't load-bearing (the player must *need* a
cross-world fact, not just spot an easter egg).

### 1B.9 What the player owns — the anthology

Go one level up from "a campaign" and the player owns **a collection
of solved worlds**. The main menu becomes an adventure anthology, each
world showing discovered / expeditions / truth state. The retention
question changes from *"how do I make someone play Expedition 17?"* to
*"what makes someone want to uncover another world?"*

Still open (§1B.15 Q6): what is *permanently* the player's — truth?
Survivor knowledge? Named characters who survived? Artifacts? The set
of completed worlds and their endings?

### 1B.10 Multiplayer — two very different shapes

Not one idea. Two, and neither is "the current game with more players":

**Synchronous cooperative** — 2–4 people, a real procedural escape
room. Information asymmetry is the point: players hold *different*
evidence and must talk to combine it.

> A: "blue route went north." B: "but Route 7 was closed after convoy
> two." C: "the hospital is north." D: "and I have the hospital
> frequency." — the conversation *is* the deduction engine.

This fights single-player Apocrysis's design (the four panels remember
*for* you; `think` synthesises your next step) — cooperative play needs
players to hold things in their heads. It would be a distinct
information architecture: **Apocrysis: Solo** and **Apocrysis:
Cooperative** over shared world/mystery machinery. And the networking
(server authority, state sync, turn arbitration, reconnection) makes
it closer to a separate product than a phase.

**Asynchronous shared world** — fits the roguelite better. One
persistent world; player A explores, dies, their discoveries *and
traces* remain; player B enters later and finds "someone has been
here" — a journal, a door already solved, the previous survivor's body
with their last evidence. Cooperative investigation with no
synchronous session and far less networking.

Architectural constraint either way (see §1B.14): the Phase E
knowledge-model refactor must be **single-observer-agnostic**.

### 1B.11 Community world packs (far future, conceptual only)

Once World / Campaign / Chapter / Expedition / Mystery / Evidence is a
real framework, a world pack is *content* — "The Lost Station", "The
Kingdom Beneath", "The Last Mars Colony" — and the engine generates
the expeditions. Not user-generated content any time soon, but it
means the game's longevity need not depend on forever hand-writing new
zombie maps. Flag only; nothing here plans for it.

### 1B.12 The name

If Apocrysis becomes the framework, then Apocrysis isn't "the zombie
game" — it's the universe. *The Silence* is a story inside Apocrysis;
*The Derelict* is another. And a future **World 4 — ???** where the
player doesn't know the genre they're entering gives a retention hook
one layer above "what happens next": **mystery about the mystery** —
*what kind of world is this?*

### 1B.13 Vocabulary

Settle on: **World · Campaign · Chapter · Expedition**, with **Survivor
level** and **World depth / Investigation %** as separate readouts.
Stop saying "map level." The code still says `expeditions_completed` /
`CAMPAIGN_LENGTH` / `map_size` — rename early, while the surface is
small (this is the one job `atlas rename` is actually good at).

### 1B.14 What this changes about decisions being made now

- **The A/B/C truth candidates (`WORLD_TRUTH_CANDIDATES.md`) are
  candidates for *world 1 ("The Silence")*, not "the Apocrysis
  truth."** Choosing one does not lock the engine to zombies.
- **Resolve the framing question (§1B.1 A–E, and §1B.8
  independent/echo/connected) before Phase A step 1.** It decides
  whether the DAG is one file or `worlds/silence/` is a `World` module,
  and whether `WorldFact` needs a cross-world scope from day one.
- **Recommended regardless:** build Phase A behind a thin `World` seam
  even with only one world for a long time — this is *interface
  discipline* ("don't hardcode 'zombie' into `build_mystery`"), not a
  plugin system. Cost: a handful of indirections. Payoff: world 2 is a
  data pack, not a fork; and the survival-pressure module is named as
  part of the pack, not assumed.
- **If multiplayer is ever wanted:** the `Evidence / Deduction /
  Hypothesis` refactor in Phase E must be **single-observer-agnostic
  from the start** — no assumption one player has seen everything; the
  solvability solver (§7) reasons about the *group's* pooled evidence.
- **Do the vocabulary rename now** (§1B.13), independent of everything
  else — it only gets more expensive.

### 1B.15 Open brainstorm questions — keep the space wide

Not to be resolved yet:

1. Is Apocrysis ultimately one story, or a collection of stories?
2. Can different worlds share a meta-story (§1B.8)?
3. Is a world something you finish once, or replay with different
   truths / endings?
4. Should players know the world premise before starting, or discover
   what kind of game they've entered (§1B.12)?
5. Can one engine support horror, sci-fi, fantasy, mystery, and
   survival without making them all feel mechanically identical?
6. What does a player collect permanently — truth, knowledge,
   characters, artifacts, completed worlds (§1B.9)?
7. Can *death itself* contribute to the story, not just preserve
   investigation (§1B.5, §1B.10)?
8. Could different survivors have genuinely different experiences of
   the same world — is World depth one axis or two (§1B.2)?
9. What makes someone come back after actually finishing The Silence?
10. **North star:** what makes someone tell a friend *"you have to play
    this — you won't believe what happened in my game"*?

Q10 is the retention question that matters most. Procedural generation
is impressive; the stories players *retell* are what make a game
stick.

### 1B.16 The honest status

This is bigger than a night's work and it is not decided. The near-term
plan (§9 Phase A) still holds — *prove the discovery loop is
compelling on world 1 before building the platform under it*. But build
it with §1B.14 in mind, so "world 1" and "the engine" are separable
from the first commit.

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

A new authored data structure (location depends on the §1B.14 seam
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

0. **The `World` seam (§1B.14).** Before any content: a thin interface
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
| **game vs engine (§1B.1, A–E)** | **Phase A step 1** | decides whether `world_truth.py` is a file or `worlds/silence/` is a `World` module. Recommendation: build behind a thin `World` seam regardless (§1B.14) |
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
