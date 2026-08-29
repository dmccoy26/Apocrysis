# Apocrysis story engine — the far-horizon design space

Written 2026-08-29. Split out of `APOCRYSIS_ROADMAP.md`
once the brainstorm outgrew the plan. **This document is allowed to be
ambitious. The roadmap is not.** Keeping the two apart stops an
interesting future idea from masquerading as a near-term requirement.

`APOCRYSIS_ROADMAP.md` is the buildable plan. This is where the brainstorm
that produced it lives.

> **SPOILER WARNING.** These sections reference the draft world truth
> in `APOCRYSIS_ROADMAP.md` §2 and `WORLD_TRUTH_CANDIDATES.md`. If you
> want to play blind, don't read either.

---

## Framing — hold these distinctions

### Vision vs World 1

- **Vision:** Apocrysis could become a story engine where stories
  *emerge* from decisions, motives, consequences, and traces.
- **World 1 ("The Silence"):** Apocrysis is a *deliberately authored*
  story whose causal history is **frozen**, with procedural machinery
  determining only *how* each player encounters and reconstructs that
  history.

World 1 takes the interesting architecture without becoming a research
project. The runtime narrative simulation is the asymptote (§1F.15),
not the plan.

### The eight primitives are not eight runtime systems

Classify them by *who touches them*, or "story engine" quietly becomes
"simulate everything" — which it does not have to:

| bucket | primitives | form |
|---|---|---|
| **things the engine understands** | WorldFacts · Secrets · evidence provenance · actors / factions · timeline / deadlines · discovery grammar | data schema + a little logic |
| **things the author uses** | the causal model · actor decisions · motives · consequences | an authoring practice — hand-simulated once, then baked static |
| **things the player experiences** | traces · mysteries · discoveries · hypotheses · consequences · their own Story Ledger | the generated, played surface |

For World 1: the middle bucket is a **design document and a bake step**,
not code that runs while you play.

### The design question has changed

Not *"what else can we add to Apocrysis?"* — that question is closed.

> **What is the smallest version of the story engine that makes The
> Silence feel like a story rather than a sequence of procedural
> puzzles?**

That is the Phase A question. The pieces already exist:

```
AUTHORED TRUTH → CAUSAL HISTORY → CONSEQUENCES → TRACES →
PROCEDURAL EXPEDITION → PLAYER INVESTIGATION → UNDERSTANDING
```

What has to be *proven* is that this chain produces the intended
player experience — **one genuinely compelling story reconstructed
through several different expeditions.** Not 25 maps, not 50
mechanisms, not a general engine. If that works, the rest of this
document has something worth building around.

---

*Sections below keep the `§1B`–`§1F` numbering they had in the roadmap,
so every internal cross-reference still resolves. **Bare references to
`§2`–`§11` point to `APOCRYSIS_ROADMAP.md`** (the plan). Read them as
one continuous brainstorm, most-load-bearing first:*

- **§1B** — is Apocrysis a game or an engine? the anthology, the
  meta-mystery, the vocabulary.
- **§1C** — the Story Ledger: the machine for stories that happened to
  *you*.
- **§1D** — the death model: Normal remembers knowledge, Hardcore
  remembers actions. *(Closest to decidable — candidate Phase B spec.)*
- **§1E** — world generated from events (the "Trace" principle):
  traces not clues, causal chains, hidden links.
- **§1F** — the story-engine framing: eight primitives, actors making
  decisions under constraints. The asymptote.

---

## 1B. Open horizon — brainstorm, not decided

*Nothing here is committed. It exists so the decisions made in the
roadmap's §2–§9 don't quietly foreclose a much larger design space.
Read §1B.14 for what it changes about decisions being made now, and
§1B.15 for the questions still open.*

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

## 1C. The Story Ledger — brainstorm, the machine for stories that happened to you

*Also a live brainstorm. This one is a single architectural idea with a
lot of features hanging off it.*

### 1C.0 The thesis

Q10 ("*you won't believe what happened in my game*") does not resolve
to "the story is really good" or "the procgen is really clever." It
resolves to:

> **Apocrysis creates stories that could only have happened to you.**

Two players can share the exact same authored truth and have completely
different stories:

> *"I found the hospital through the kid's drawing. Renner died on the
> bridge. I spent six expeditions sure the blue signs were traps. Then
> Mora found the radio."*
>
> vs. *"I never found the hospital. My first three survivors died
> looking for the dam. Vaughn found the evacuation records by accident
> while hunting for fuel. I blamed the military until the very end."*

The authored truth provides **meaning**; the survival layer provides
**chaos**; the knowledge system provides **interpretation**. **The
collisions between those three are the product.**

### 1C.1 The architecture — one new layer

```
                   AUTHORED TRUTH  (§2)
                          │
                   WORLDFACT DAG  (§3.1)
                          │
             ┌────────────┴────────────┐
        DISCOVERY ENGINE          SURVIVAL ENGINE
         (§3, §5, §6)              (frozen balance)
             └────────────┬────────────┘
                     PLAYER ACTIONS
                          │
             ┌────────────┴────────────┐
         WORLD STATE              KNOWLEDGE STATE
             └────────────┬────────────┘
                          │
                  ►  STORY LEDGER  ◄     ← the new layer
                          │
             ┌────────────┴────────────┐
        CAMPAIGN HISTORY          RETELL MOMENTS
```

The **Story Ledger** (internal name: *Narrative Telemetry* — not
analytics; the game's own model of *"what happened in this player's
story"*) sits **downstream** of the engine in §3–§9. Most of what
follows requires **no change to the core mystery engine** — the Ledger
observes and records. The exceptions (1C.5–1C.7) feed back upward and
belong with Phases C/D.

### 1C.2 What the Ledger records

Per survivor: born / died / cause; significant events ("found a child's
drawing beneath the pharmacy", "followed blue markers north", "became
convinced the military caused the disappearance", "found evidence
contradicting the theory", "died 63 tiles from the exit"); what they
carried at the end; their last discovery; their successor. Per
campaign: the **discovery path** (`pharmacy → drawing → hospital →
ambulance log → blue corridor → depot → command`), the theory history,
the wrong-belief record.

### 1C.3 Emergent-moment detection — "something strange happened"

A post-run pass over **emergent state**, not authored content. Flags:
`<10% HP while solving a critical clue` · `reached a site turns before
an environmental change` · `held two contradictory clues at once` ·
`changed hypothesis immediately after new evidence` · `carried a
critical item an absurd distance` · `final survivor inherited from
three dead ones` · `escaped by an unintended-but-valid route` · `spent
six expeditions on a disproved theory`. Surfaced as an **APOCRYSIS
EVENT** — *"THE HOSPITAL RUN. You had 7 HP. Night had fallen. The
eastern road was flooded. You found the frequency in the last building
you searched. You made it out with 2 HP."* Content generated from
gameplay.

Plus a rare **"impossible coincidence"** seed class — statistically
improbable procedural collisions (you find the item you abandoned ten
expeditions ago; a dead survivor's route becomes the optimal route for
the next). Players will swear the game did it on purpose. That is the
goal.

### 1C.4 The cast — your deaths are the protagonists

Survivors accumulate identity through **play, not character creation**:
*Renner — "the one who found the hospital." Vaughn — "the one who
proved Renner wrong." Mora — "the one who reached the radio tower."*
The campaign develops a cast without a single authored character.

Dead survivors leave **geography**. You find a body under a collapsed
awning; a name is scratched into the radio casing — *Renner* — and the
game does **not** say "you found Renner." "A familiar name" lands
harder than a label. The world accumulates **memorials**: eleven
survivors die at one bridge and it becomes *the Renner Bridge*; names
carved in concrete that the player slowly realises are *their people*.

### 1C.5 The world scarred by your attempts *(feeds the engine — Phase C/D)*

Previous survivors' actions persist **narratively**, never as power
creep: a gate Renner opened, a vehicle Mora moved, a building Ellis
drained, a danger someone marked, a cache someone's been using ("*Thank
you.*" — no explanation). This is **asynchronous multiplayer without
multiplayer**; if a shared world ever exists (§1B.10), the same hook
points at *other people's* Renners.

### 1C.6 Knowledge has a survival cost *(feeds the engine — this is "the two games finally talk")*

Some evidence is not a card in a pocket:

- use frequency 91.7 → something answers → **you've announced your
  location**
- fuel the generator for evidence → it **attracts the infected**
- open the military archive → **triggers a security system**
- the flood-control schedule isn't lore, it's a **forecast** — the
  reservoir opens in 30 turns

Investigation *increases* danger; evidence *predicts* the map changing.
This is the concrete answer to the "two games don't talk" problem from
the earliest brainstorm.

### 1C.7 The generator responds to what you know *(feeds the engine)*

Procedural **narrative continuity**, not just variety. The generator
reads `PLAYER_KNOWS: blue markers = evacuation route` and generates a
**legitimate** contradiction involving blue markers — teaching "*I was
treating a clue as a rule.*" Latent affordances (the flare that matters
once you learn command recognises flare signals — reverse Chekhov).
Early over-discovery: find a Chapter-4 clue in Chapter 1 → **lock the
interpretation, not the discovery** ("someone ordered this" — but not
yet *who*). Dramatic irony: the player knows the dam will open; the
survivor doesn't.

### 1C.8 Being wrong is content

A **theory board** the player pins their *own* interpretations to ("*I
think command knew the infection was airborne*"), tracked as a player
hypothesis. Later: **YOUR THEORY WAS WRONG** — archived, dated,
attributed to the survivor who held it. *"Vaughn believed Protocol
Seven was a rescue. Disproved on Expedition 18."*

The ending becomes **epistemological**, not just moral: you broadcast
what you *believe* (*"14 confirmed facts, 3 disputed claims, 2 theories
later proven false — the world will hear what you believe happened, not
necessarily what happened"*). And you can finish at **Truth 88% / your
conclusion 100%** — an investigation, not a puzzle with one gated
answer.

### 1C.9 Never say "procedural"

The magic is ambiguity. *"Something strange happened,"* never
*"procedurally generated event."* The player should not be able to tell
whether a moment was authored or invented. That uncertainty **is**
part of Apocrysis's identity.

### 1C.10 The genre is itself a mystery *(pushes §1B.8 / §1B.12 harder)*

*"WORLD UNKNOWN. Wake up."* You assume fantasy — ruins, a village,
inscriptions — then find *"PROPERTY OF ███ RESEARCH, UNIT 04."* The
rules of the world slowly go **ambiguous**; the player asks *what kind
of world am I actually in?* World 2 makes World 1 **retroactively
stranger** — Protocol Seven turns up centuries earlier — and the player
carries an **unresolved contradiction between worlds**. That's what
people obsess over.

### 1C.11 The social layer, still no multiplayer *(extends §1B.10)*

**"Compare your investigation."** Same truth, different routes: you
reached it via `hospital → pharmacy → ambulance` (17/25 WorldFacts),
they via `drawing → school → teacher's journal` (19/25); 11 shared, 8
different, 6 different routes to the same fact. Procgen has produced an
inherently social question: **"how did you figure it out?"**

The endgame terminal reconstructs *your* run against the authored
timeline — Day 1 Renner wakes, Day 4 Renner dies, Day 4 Vaughn
inherits, … Day 17 you reach Command — and then a branch appears:
**there was another survivor.** A parallel thread you may never have
met, who may have scarred the world you walked through.

### 1C.12 The generated postmortem — "YOUR APOCRYSIS"

Not statistics. A **story**: *25 expeditions, 31 survivors, 8 died
pursuing the hospital, your first theory was wrong, your second mostly
right, you never found the northern checkpoint. Renner reached the
hospital. Vaughn found the transmission. Mora proved it wasn't a
rescue. You chose to broadcast.* Plus **YOUR MOST UNLIKELY MOMENT**,
**YOUR BIGGEST MISTAKE**, **YOUR DISCOVERY PATH**. Eventually a
~60-second generated presentation — *"The Story of Dan's 31
Survivors."* And *then*: **start another world.** The anthology
(§1B.9) becomes *collecting stories you lived through*, not collecting
games.

### 1C.13 Hardcore — one deteriorating timeline

An endgame mode where the world remembers **everything** — every
corpse, opened door, abandoned vehicle, consumed cache, activated
generator, death, hypothesis, environmental change — across the whole
campaign. Not replaying maps: living in one decaying timeline through
multiple bodies.

### 1C.14 Where this sits in the plan

- **Recording half** — starts as soon as Phase A has state worth
  recording. Cheap: it observes.
- **Feedback halves** (1C.5–1C.7) — real engine changes; land with
  Phase C/D.
- **Downstream features** (cast, memorials, postmortem, comparison,
  theory board) — any time after the Ledger exists; pure downstream.
- **None of it is a rewrite of the mystery engine.** It's a new layer
  under the one being built in §3–§9.

---

## 1D. The death model — brainstorm, but close to decidable

*The least speculative part of this whole conversation. It largely
answers §10's "what carries forward on death, exactly" and should
probably be promoted to a Phase B design spec.*

### 1D.1 The rule that gives the two modes a real difference

> **Normal: the world remembers your knowledge.**
> **Hardcore: the world remembers your actions.**

Not "Normal = easier, Hardcore = harder." A philosophical difference:
*Normal is a continuing investigation through successive survivors;
Hardcore is a single deteriorating world experienced through multiple
lives.*

### 1D.2 Three tiers of persistence

| tier | what | Normal | Hardcore |
|---|---|---|---|
| **Knowledge** | WorldFacts, deductions, hypotheses, discovered frequencies, known routes, investigation % | **always persists** | always persists |
| **Narrative** | survivor bodies, journals, markings, caches, memorials, opened shortcuts, established outposts, world changes (a drained building, a moved truck, an opened floodgate) | **selected** traces persist (the Ledger picks a handful — never all, that's clutter) | **all** of it persists |
| **Mechanical** | XP, level, weapons, armor, inventory, consumables, buffs | never | never |

Hardcore is *Narrative-tier promoted to Knowledge-tier* — everything
that happened stays.

### 1D.3 Neither mode restarts the campaign

**This is the load-bearing insight.** On death you lose your *position
in the timeline*, not the investigation. A player can spend 20 hours
solving the mystery and lose a survivor without losing progress. In
Normal the physical region can regenerate around the persistent
knowledge; in Hardcore it doesn't. Either way: **new survivor, from an
established outpost, at the current World depth** — not Expedition 1,
not the death tile.

### 1D.4 The Survivor Network — where you respawn

Not the death tile (death becomes meaningless — brute-force by throwing
bodies at a hazard). Not Expedition 1. Instead: **established
outposts**, which the player *discovers and deliberately establishes*
(costs resources) from candidate buildings — ranger stations, fire
stations, churches, shelters, maintenance buildings.

Exploration gains a second purpose: not just "where's the evidence?"
but "where can I make my next life safer?" — a genuine interaction
between the two games.

**Difficulty-curve risk (my note):** a deep outpost network + cheap
frontier survivors trivialises late-campaign survival. Needs a counter
— outposts degrade, get overrun, or the frontier outpaces them, or
establishing cost escalates. Otherwise the roguelite tension
evaporates once the network is built.

### 1D.5 The Survivor Network is also evidence

You establish four outposts for survival. Later you discover all four
sit along the old evacuation corridor. A survival decision
retroactively becomes evidence — exactly the §1C-class collision the
game wants.

### 1D.6 Death generates a question, not just a record

The Ledger infers **Last Known Intent**, not just cause of death:

> *RENNER — believed the hospital held evacuation records; attempted to
> reach the north wing; discovered emergency frequency 91.7; died 300m
> short. Unresolved: who was transmitting?*

The next survivor now has a *personal* reason to continue — "Renner
died trying to get there, I need to finish this" — not "the game says
my next objective is Hospital."

### 1D.7 The Expedition Board — one screen, not three

Between expeditions: unresolved investigation threads **+** dead
survivors' open questions (the "unfinished business" system — inherited
as *open questions, not mandatory quests*). The player **chooses** what
to pursue — maybe they ignore Renner entirely; maybe Renner was wrong;
maybe the hospital is a death trap. **Player-authored investigative
priorities**, and the point where investigation and survival openly
compete.

This screen is the same object as the World Investigation screen (§8)
and the theory board (§1C.8) — build one between-expeditions view, not
three overlapping ones.

### 1D.8 The death screen matters as much as any screen in the game

Not `YOU DIED / CAUSE: INFECTED / TURNS: 47`. Instead:

```
                    RENNER
                 DID NOT RETURN

     8 expeditions survived
     3 discoveries recovered
     1 theory abandoned
     2 outposts established

     Last known location:  north of the hospital
     Last known objective: determine who operated
                           emergency frequency 91.7

     The investigation continues.
                  [ CONTINUE ]

                    VAUGHN
           Someone has to finish this.
```

### 1D.9 Don't turn it into an XP spreadsheet

*"Renner is gone. But the things Renner learned aren't. The
investigation continues."* is enough. The player should understand the
rules but the experience should feel like **continuity**, not
`+7% Investigation · +1 Memorial`.

### 1D.10 The payoff

Late in the campaign the player reaches the final area and sees **17
names** — their own survivors. They realise: they were never playing
one hero. They were playing an investigation conducted by *a
succession of people who kept trying*, and the cast was generated by
their own failures. No author writes Renner — the player creates
Renner by playing desperately, cleverly, recklessly, or just getting
unlucky.

### 1D.11 Smaller mechanics on the pile

- **Survivor rumours** — after enough deaths the campaign generates
  folk knowledge ("three people have vanished near the dam"). Some
  true, some misleading. The player develops folk knowledge about
  their *own* world.
- **Memorial geography** — enough deaths at one place and it acquires a
  name: *Renner's Crossing*. "The road ahead has been marked with
  names." The player realises: *I named this place.*
- **Survivor-to-survivor notes** (rare) — *"IF YOU FIND THIS — DON'T GO
  THROUGH THE EAST TUNNEL."* But Mora may have been wrong, or the
  danger changed. Your own history becomes evidence that needs
  interpretation.

### 1D.12 Where it fits

Normal-tier persistence + the Survivor Network → **Phase B** (it *is*
the roguelite loop). Hardcore's full-timeline persistence → after
Phase D (needs the world-state persistence layer and a decay model,
per §1C.13). The death screen and Last Known Intent → Phase B, they're
Ledger read-outs.

---

## 1E. World generated from events — brainstorm, the "Trace" principle

*Adapted from the Trace game's design as source material. Not a
mechanic, not a mode — a principle that changes §3 and §5.*

### 1E.1 The principle

> **The world is generated from things that happened, and the
> expedition puzzle is a problem caused by one of those things
> happening.**

The level story and the world story stop being two layers beside each
other. They become **the same story at two scales**: *how do I deal
with what happened here?* / *why did it happen?* Death adds a third:
*what did all my survivors do trying to find out?*

### 1E.2 The generation order gains a layer

```
WORLD TRUTH                (authored — §2)
     ↓
CAUSAL MODEL               (authored — events, actors, cause→effect edges)
     ↓
EVENTS + ACTORS
     ↓
CONSEQUENCES               (how an event manifests: a flood, a barricade, a burnt-out convoy)
     ↓
TRACES                     (generated — what a consequence leaves on a map)
     ↓
EXPEDITION PUZZLE          (generated — one consequence, framed as the player's problem)
     ↓
PLAYER INTERPRETATION → THEORY → WORLD INVESTIGATION
```

The authored `WorldFact` DAG (§3.1) still defines what is *true*; it is
now authored **against the causal model**, and the player never sees
either — they see the traces the truth left behind.

### 1E.3 Traces, not clues

A **clue** is placed for the player. A **trace** exists because
something happened. Subtle, enormous difference. If the truth says
*"Emergency Command redirected Convoy 7 north,"* the generator doesn't
place "Convoy 7 went north" — it creates consequences: abandoned
vehicles and a turned sign at the highway; inspection records and fuel
logs at the checkpoint; discarded equipment and damaged vehicles along
the northern route. The player reconstructs *something moved through
here → it was Convoy 7 → it was redirected → someone ordered it.*

### 1E.4 Every trace has provenance

Hidden metadata: created **when / where / by whom / why**, and *could
the author have known what they claim?* This is what makes
contradictions meaningful — and (my note) it is the **safety mechanism
for 1E.5**: a lie is only fair if it's detectable, and it's detectable
when two provenanced records disagree.

### 1E.5 Evidence needn't tell the truth

The world truth is true. Individual traces can be incomplete, outdated,
written before or after an event, based on bad information, or
accurate-but-misleading-in-context. The player concludes *"everyone
evacuated,"* then finds a hospital census: *143 patients remained.*
They don't feel cheated — they think *"I had incomplete evidence."*

**Solvability guardrail (my note):** every `WorldFact` needs at least
one *reliable* path, or its unreliable evidence must be detectable via
provenance contradiction. Otherwise a generated mystery can be
genuinely unsolvable and §7's solver has to know it. Unreliable
evidence is not free.

### 1E.6 Causal chains, walked backward

```
Protocol Seven → evacuation → consolidation → hospital transfers →
power redirected → generator overload → cold storage fails →
medication spoils
```

The player finds the **spoiled medication** first and walks back up the
chain. Detective work, not a scavenger hunt.

### 1E.7 Multiple causal *surfaces* per fact

Not just multiple clue locations. *"The evacuation was deliberately
terminated"* is provable from: a closure order · a bridge dropped
**after** the last convoy passed · a gate programmed to close at a set
time · a guard's journal · a recorded command · two records with
matching timestamps · evidence people were still trying to cross after
closure. Each is a different `DiscoveryTemplate`.

### 1E.8 The generator hides links — gaps

A perfect chain is boring. `EVENT → TRACE → TRACE → ??? → TRACE →
FACT`. The missing edge **is** the mystery; the expedition puzzle is
one way to recover a missing link. This is the cleanest new generator
primitive in the whole brainstorm: **build a causal chain, remove one
or more edges, the puzzle recovers one.** Prototype this first.

### 1E.9 The expedition puzzle is generated *from* a consequence

```
FACT       the corridor was intentionally flooded
EVENT      the reservoir gate opened
CONSEQ     the road flooded
PUZZLE     the player can't cross
INVESTIG.  why was the gate opened?
SOLUTION   reach the control station
DISCOVERY  the gate activation was scheduled before the evacuation
FACT ↑     the closure was planned
```

The puzzle exists *because of* the world story. That is the whole
point.

### 1E.10 Retroactive meaning → revisit

Discover a blue sign in Expedition 3 (unremarkable). Learn in
Expedition 7 that blue signs mark evacuation routes. Expedition 3
acquires meaning. Learn the hospital had an emergency generator; later
learn generators kept the evac comms alive; the hospital is worth
**revisiting**.

```
DISCOVER → LEARN → REINTERPRET → REVISIT → DISCOVER SOMETHING NEW
```

Knowledge increases the value of *old* discoveries — the world feels
deeper than its physical size, which matters enormously for procgen.

**Reconciliation with §1D (my note):** this loop needs the region to
be **stable for the length of a campaign** — it only regenerates when
you start a new campaign / new world. Otherwise "revisit the hospital
knowing what I know now" hits a different hospital. Pin this.

### 1E.11 Knowledge unlocks actions, not just text

Learn *"Emergency Command recognises signal flares."* The flare stops
being a light source and becomes a **communications device the player
can choose to use** — and using it might attract the infected, reveal
their position, trigger a response, open a route, or produce a new
transmission.

```
KNOWLEDGE → NEW AFFORDANCE → PLAYER CHOICE → CONSEQUENCE → NEW EVIDENCE
```

This is where investigation and survival become **one system** (same
target as §1C.6).

### 1E.12 The full architecture

```
              AUTHORED WORLD TRUTH
                      │
                 CAUSAL MODEL
              ┌───────┴───────┐
           EVENTS           ACTORS
              └───────┬───────┘
                 CONSEQUENCES
                      │
                    TRACES
                      │
             PROCEDURAL EXPEDITION
              ┌───────┴───────┐
          SURVIVAL         DISCOVERY
              │                │
              │          INTERPRETATION → THEORY
              └───────┬────────┘
                    ACTION
                 ┌────┴────┐
              SURVIVE     DIE
                 │         │
                 │   NEW SURVIVOR
                 └────┬────┘
                 MORE TRACES
                      │
                 DEEPER TRUTH
```

### 1E.13 What this changes about §3 and §5

- **§3.1** gains a layer *beneath* the `WorldFact` DAG: a **causal
  model** (events / actors / cause→effect edges) the DAG is authored
  against, and from which the generator derives consequences → traces →
  the expedition puzzle. `DiscoveryTemplate` becomes *"a way of
  recovering a hidden link in a causal chain."*
- **§5's** inverted pipeline (`story → geography → graph → terrain →
  mystery`) becomes `story → causal model → consequences → (traces +
  the puzzle) → geography → graph → terrain`.
- **Authoring cost goes up a lot (my note).** A 28-node fact DAG is a
  data file; a causal model that generates traces is a *content
  pipeline* — events, edges, and consequence templates ("how does 'gate
  opened' manifest as traces on a generated map?"). This is the
  difference between a 3-month and a 12-month project. Mitigation:
  author the causal model **shallow** for world 1 (one or two
  consequence-hops per fact), deepen later.

---

## 1F. The story-engine framing — brainstorm, the asymptote

*The most ambitious framing in this document. Read §1F.15 first — it is
the vision the architecture should not foreclose, not the thing to
build in Phase A.*

### 1F.0 The gap and the thesis

The roadmap has a **discovery grammar** (spatial / infrastructural /
experimental / …) — *how* the player learns things. It is missing a
**story grammar** — *what kinds of stories can happen*. And the deeper
reframe:

> **The engine shouldn't generate stories from clues. It should
> generate stories from people making decisions under constraints.**
> Traces, mysteries, maps, evidence, consequences — even many of the
> "quests" — are shadows cast by those decisions.

### 1F.1 Eight engine primitives

| primitive | answers | status |
|---|---|---|
| **Story Grammar** | what kinds of stories can exist? | absent |
| **Actors** | who makes things happen? | history-only in §1E |
| **Goals / Motives** | why do they act? | absent |
| **Secrets** | what isn't immediately knowable? | absent (`WorldFact` only) |
| **Timeline** | when do things happen? | partial (`deadline`, `tidal_causeway`) |
| **World State** | what is true *right now*? | absent (`WorldFact` = what is true, not when) |
| **Consequences** | what changes because things happened? | §1E traces, one direction only |
| **Story Ledger** | what happened specifically in *your* game? | §1C |

Existing systems become **components** of this engine, not the whole:
`WorldFact DAG → truth · Causal Model → history · Discovery Templates →
investigation · Map Generator → physical realisation · Knowledge
System → player understanding · Survival System → pressure · Story
Ledger → personal history · Survivor Network → persistent
consequences`.

### 1F.2 Story Grammar

A pool of story *structures*: disappearance · betrayal · rescue ·
conspiracy · accident · containment failure · cover-up · pilgrimage ·
sabotage · forbidden experiment · faction conflict ·
race-against-a-deadline · someone hiding something · someone revealing
something · two groups with incompatible goals. A generated mystery =
**story structure × causal events × actors × locations × evidence ×
discovery method × player choices**.

### 1F.3 Actors as causal agents

An actor has: goal · fear · knowledge · secret · allegiance ·
relationships · resources · available actions · **false beliefs** ·
things they hide · things they misunderstand · the consequences of
their succeeding or failing. The player **never meets Mara** — they
encounter the consequences of Mara's actions. Dramatic causality, not
just historical.

### 1F.4 Motives — the causal model gains a head

```
GOAL        Command wants to contain the outbreak
   ↓
DECISION    seal the evacuation corridor
   ↓
ACTION      close Gate 7
   ↓
CONSEQUENCE 143 civilians remain inside
   ↓
TRACES      gate log · abandoned vehicles · hospital census · radio traffic
```

The player reconstructs not just *what* happened but *why someone did
it*.

### 1F.5 Relationships

`Mara trusts Daniel · Daniel suspects Command · Command controls Mara ·
Mara protects her brother`. Relationships become mysteries: *"why did
the hospital director falsify the evacuation list?"* — answered not by
a document but by assembling *her brother was on the list · his name
was removed · she had system access · she was in contact with Command ·
a survivor says she was trying to save him*. The player interprets
human behaviour.

### 1F.6 `WorldSecret` — a sibling to `WorldFact`

**Fact:** "Command ordered the corridor sealed." **Secret:** "The
commander knew his own family was still inside when he gave the order."
The secret is **not required** to solve the main mystery — discovering
it *reinterprets* the fact. `fact → context → reinterpretation`. Feeds
retroactive meaning (§1E.10). **Cheap (my note):** it's `WorldFact`
with a `reinterprets: <fact_id>` field and no gate on the main
hypothesis — worth reserving room for in Phase A's schema.

### 1F.7 Factions

Not NPC simulation — the *concept*. Emergency Command · hospital staff
· local government · survivors · researchers · military · a religious
group · refugees. Each has goals · resources · territory ·
relationships · knowledge · enemies · policies. Stories emerge from
**conflicting objectives**: *"Command wanted containment"* vs *"hospital
staff wanted evacuation"* vs *"the survivors wanted out."* The causal
model gets competing objectives, not one chain. **Cheap as a tag (my
note):** a `faction` field on facts/actors makes competing objectives
legible even in a hand-baked model.

### 1F.8 Narrative time — the story clock

Bigger than time-of-day. Events carry: absolute time · duration ·
deadlines · prerequisites · triggers · consequences.

```
T+20 floodgate opens · T+30 road impassable · T+40 settlement abandoned
· T+50 infected arrive · T+60 the transmission begins
```

The player reconstructs the timeline. Once they know enough: *"the
flood isn't random — we have 12 turns."* Knowledge changes how the
player experiences time. **This generalises the shipped `deadline`
machinery (`tidal_causeway`) — extend it, don't build a parallel
system.**

### 1F.9 `WorldState` — what is true *right now*

A first-class engine concept, distinct from `WorldFact`. Fact = what is
true (history). State = what is true at this moment. The world holds:
geography · infrastructure · characters · factions · resources ·
events · relationships · secrets · facts · **state** · timeline.

### 1F.10 Story-state transitions — the world reacts to the player

The biggest missing loop:

```
player opens the dam → water falls → new road exposed →
survivors reach the settlement → infected migrate toward it →
the settlement changes its defences → new evidence appears
```

`player knowledge → action → world change → new story state → new
evidence`. This is what turns a mystery *generator* into a living
narrative *system*.

### 1F.11 Branching via simulation, not authored branches

Not `choice A → story A`. Instead: `player action → world state changes
→ causal model reacts → new consequences → new traces → player
discovers them`. The story branches because the **simulation**
branches — compatible with procgen, and two players get genuinely
different stories with no second authored narrative.

### 1F.12 The player can cause mysteries

The endpoint of the Ledger idea:

```
player opens a sealed bunker → the survivors inside leave →
their absence changes another settlement →
a later survivor finds that settlement abandoned → "what happened here?"
```

The player becomes part of the causal model. Gives §1C.5–§1C.7 a much
bigger purpose.

### 1F.13 The full architecture (the asymptote)

```
                STORY AUTHORING
                      │
                 WORLD PREMISE
                      │
             CHARACTERS / FACTIONS
                      │
           GOALS / MOTIVES / SECRETS
                      │
                 CAUSAL MODEL
                      │
                   TIMELINE
                      │
                  WORLD STATE
             ┌────────┴────────┐
        CONSEQUENCES       ACTORS ACT
             │                 │
          TRACES          WORLD CHANGES
             └────────┬────────┘
                 PROCEDURAL WORLD
                      │
              PLAYER EXPERIENCES  ←──┐
                      │              │  KNOWLEDGE ENGINE
                 PLAYER ACTION       │  traces/evidence ↑
              ┌───────┴───────┐      │  hypotheses ↓ decisions ↓
          SURVIVES          DIES     │
              └───────┬───────┘ ─────┘
                 STORY LEDGER
                      │
               WORLD REMEMBERS
                      │
                NEW STORY STATE
                      │  (repeat)
```

### 1F.14 The answer to "how do we add more stories"

Not 100 more hand-authored mystery scenarios. **New authored
worlds/campaigns expressed through a common story grammar**, with the
engine generating the circumstances in which those stories are
discovered. This is where Apocrysis stops being "a procedural zombie
mystery" and becomes a procedural story/game engine that *happens to
have* The Silence as its first story.

### 1F.15 Reality check — this is the asymptote, not the plan

- **Scope.** A runtime actor model with goals, beliefs, relationships,
  and a reactive causal simulation is a **2+ year, research-grade**
  system. Very few games have shipped it (Dwarf Fortress, Versu,
  RimWorld's storyteller as a thin version). Most attempts didn't
  ship. The current game is ~12,600 lines and *works*; the jump from
  Phase A ("`WorldFact` DAG + discovery templates", months) to §1F
  ("reactive actor simulation", years) is enormous.
- **It degrades gracefully — and world 1 should take the degraded
  path.** Author the actors and their decisions *once, at authoring
  time*, as a design document; **bake** the resulting causal model
  into a static structure; do **not** simulate at runtime. You get
  ~80% of the "stories from decisions" feel with none of the
  simulation risk. The actor model becomes an authoring *mindset and
  tool*, not a runtime system.
- **What to actually reserve room for in Phase A** (all cheap):
  - `WorldSecret` = `WorldFact + reinterprets` field (§1F.6).
  - Evidence provenance + epistemic status in the `Evidence` schema
    (§1E.4 / §1F.11) — the honest-lies mechanism.
  - `faction` as a tag on facts and actors (§1F.7).
  - Treat `deadline` as the seed of the story clock, not a one-off
    (§1F.8).
- **The line to hold.** §1F is the vision; Phases A–E build *toward* it
  without committing to the runtime simulation. The test for every
  Phase A/B decision: *does this foreclose a reactive actor model
  later?* If no — proceed with the baked version.
