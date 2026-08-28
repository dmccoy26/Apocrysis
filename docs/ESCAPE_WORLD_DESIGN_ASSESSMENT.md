# Escape-the-Unknown-World: Engine Assessment

Status: assessment only, per the design discussion's own instruction —
nothing here has been implemented. This evaluates the "escape the
unknown world" design direction (2026-08-27: "you are not looking for
a predefined exit, you are trying to understand the world well enough
to discover how to escape it") against the engine as it exists today,
and specifies the architecture in enough depth to actually build
against. Consolidated 2026-08-27 from several rounds of design
discussion — this version replaces the earlier draft rather than
stacking further "REFINEMENT" notes onto it.

Corresponding implementation todos are filed in this project's own
todo list — `projects/apocrysis/version-4/.atlas/todo_list.json`
(relative to the Atlas repo root), NOT Atlas's own top-level
`.atlas/todo_list.json`,
which is a separate list for Atlas's own self-repair work. Todos are
ordered to match the phases in this document.

## Start here (session status, 2026-08-28)

**Design is done for now. The next action is building, not more
design.** If you're resuming this after clearing context, read this
block and the "Vertical slice prototype" section below — skip the rest
unless you need to look something specific up (use the table of
contents).

- **What's decided:** the full architecture in this document — escape
  mechanisms as per-expedition, campaign-aware, generation-seeding
  choices (Core Design Rule 1); contextual world generation instead of
  independent random layers (Core Design Rule 2); a 5-category loot
  ecology with an 18-location worked catalog; a 4-state knowledge model
  (Observed → Known → Suspected → Confirmed) with automatic, never
  player-issued transitions; a minimal 6-verb command set
  (`look`/`inspect`/`search`/`journal`/`remember`/`map`); a 5-layer
  World Validation model plus a private, generator-internal Escape
  Proof structure validated *backward* from the escape; a physical vs.
  information budget with named `MAX_*` invariants to keep the world
  dense without making the mystery unmanageable; a Persistent World &
  Interaction Model distinguishing what's decided (knowledge persists
  independent of physical evidence; zombies don't respawn in place;
  dropped items persist; save/load must capture real world state) from
  what's deliberately still open (see Open Questions / Questions We
  Aren't Asking — don't resolve these ahead of evidence).
- **What's next, right now:** build the **vertical slice** — a
  hard-coded (non-procedural) Dam Service Road mystery, NOT the
  generator. See "Vertical slice prototype" immediately below for the
  full scope. **Do not start on Phase 0 or the generator work** until
  the slice has been played and evaluated.
- **Where the work is queued:** `projects/apocrysis/version-4/.atlas/todo_list.json`
  — 63 pending items, the first 6 are the vertical slice build (in
  order: hard-coded map → Escape Proof as real state → minimal
  journal/remember/inspect → temporarily loosened survival pressure →
  persistence/backtrack/escape-action → the playtest itself, which is
  the actual go/no-go gate for building the generator at all). The
  playtest todo carries a full behavioral-signal checklist — read it
  before running the playtest, not after.
- **Repo:** this direction lives on the `version-4` branch of
  `github.com/dmccoy26/Apocrysis` (branch HEAD `5c4912a`; forked from
  `version-3` at `9c835aa`). The working tree is checked out at
  `projects/apocrysis/version-4/` (relative to the Atlas repo root);
  sibling `version-1/`..`version-3/` directories hold read-only clones
  of the older branches. All slice and generator work commits to
  `version-4`.
- **The one test that matters most**, if you only remember one thing:
  can a player tell "I haven't solved this yet" apart from "this isn't
  important," using only what the interface gives them? Everything
  else in this document exists to support that one thing.

### Table of contents

- The architectural idea underneath all of this / The governing test
- Vertical slice prototype ← **build this next**
- Target experience
- Classification, point by point / Architectural risk by subsystem
- Recommended build order
- Core design rule 1: the escape mechanism is per-expedition (+ Escape
  Mechanism Model)
- Core design rule 2: random composition, consistent logic (+ place
  hierarchy)
- Loot & discoverable-content ecology (+ 18-location catalog)
- Environmental storytelling & visual world grammar
- Persistent world & interaction model
- Questions we aren't asking
- Knowledge state
- Escape proof & causal-chain validation
- World validation
- Automated expedition simulation & balance
- Failure modes
- Three kinds of state
- Player identity as an interpretation lens
- What the player should NOT see
- Physical & information budget
- Player cognition & information architecture
- Worked example: Railway Escape
- Old engine → new engine
- Open questions
- Follow-up, not part of this assessment

## The architectural idea underneath all of this

Current Apocrysis:

```
Random world -> random objects -> player explores ->
player finds resources -> player reaches a predefined destination
```

Proposed Apocrysis:

```
Seed choices -> world model -> relationships -> evidence ->
player observations -> player interpretation -> player hypothesis ->
player action -> discovery / escape
```

And the core mechanic underneath that:

```
GENERATOR knows the answer
        |
        | deliberately obscures it
        v
PLAYER sees evidence
        |
        | builds understanding
        v
PLAYER reconstructs the answer
```

This is more than a new win condition. Apocrysis moves from a
procedural survival game to a **procedural investigation game that
happens to use survival as its pressure system.** That's why knowledge,
contextual generation, history, clues, relationships, validation, and
escape mechanisms are architectural requirements here, not content
additions layered on top of an unchanged engine.

### The governing test

Added 2026-08-27. What does Apocrysis believe the player is doing when
they're "playing well"? Not killing zombies efficiently, not finding
loot efficiently, not following objectives efficiently — **building an
increasingly accurate mental model of a strange world and using that
model to make good decisions.** Every open question in this document —
persistence, evidence, zombies, world changes, escape — can be
evaluated against one test: **can the player form a mental model of
the world that remains trustworthy as they interact with it?** A
dropped flashlight that can never be found again breaks that trust. A
killed zombie reappearing in the exact same square because the player
came back breaks it too — their actions stopped mattering. A clue's
physical object being destroyed is fine *if* the knowledge gained from
it persists; if it isn't, that's the same trust failure as the
flashlight. This is the frame to run every persistence/world-state
question in this document through — see Persistent World & Interaction
Model below.

## Vertical slice prototype — build this next, not the generator

Added 2026-08-27. Everything else in this document describes the full
procedural system. **Do not build the generator next.** Build one
hard-coded mystery first — the Dam Service Road proof already worked
through in conversation (4 facts, 6 evidence, 1 hypothesis, 1 physical
key item) — as a fixed, non-procedural map, to find out whether the
investigation loop is actually fun before investing in a generator
that reproduces it at scale. This is the reference specimen the
generator eventually has to match, not throwaway code.

**Two attacks on the loop this slice exists to run, in order:**

1. **Decouple investigation from survival first.** Tonight's data
   showed a 9-11 turn median game against a mystery that needs
   15-25+ turns to play out honestly — an architecture conflict, not
   a balance tweak. Build the slice with hunger/thirst/combat pressure
   deliberately loosened (explicitly temporary, not final tuning) so a
   player can reliably spend 30+ turns investigating without dying
   first. Only after the loop itself is proven fun should survival
   pressure be reintroduced and tuned to find where it starts
   interfering.
2. **Test narrative salience vs. mechanical importance directly**,
   not just avoid it. Include a second, deliberately compelling
   irrelevant thread alongside the real mystery (a farmhouse diary
   about a missing daughter, some graffiti) — genuinely interesting,
   mechanically pointless — and measure whether a player can recover
   from chasing it without an explicit hint, not whether they avoid
   chasing it. The fantasy being tested is "I can be curious without
   being punished," not "I always pick the optimal thread."

**The genre-convention finding stands as a decision, not a problem to
fix**: keep the locked-gate/find-a-key mechanism for this first slice.
The real requirement is "never require an action unreasonable given
the player's accumulated knowledge" — a familiar key-and-lock passes
that test cleanly, and using a familiar mechanism here means the
experiment measures the investigation loop, not puzzle novelty.
Stranger mechanisms are a later test, once this one is proven.

**Scope, hard-coded, no procedural generation:** a ~19×19 or 21×21 map;
one location cluster (dam, utility shed, plus the irrelevant-lead
locations); the Dam Service Road Escape Proof exactly as designed
(4 facts / 6 evidence / 2 deductions / 1 hypothesis); the irrelevant
diary/graffiti thread; `journal`, `remember`, and a minimal `inspect`;
hypothesis/confirmation via physical observation, not a status
message; one example of knowledge persisting past its physical
object's destruction; one backtrack (see and don't yet understand the
gate → get the key elsewhere → return); the actual escape action,
gated on the confirmed hypothesis, not tile position; loosened
survival pressure per above.

**Final test to run against the built slice** — the one that actually
matters most: can a player tell the difference between "I haven't
solved this yet" and "this isn't important"? Construct three
situations against the built slice and observe each: (1) a required
piece of evidence the player hasn't found yet, (2) the irrelevant
diary/graffiti thread partially investigated, (3) a required
hypothesis the player has enough discovered evidence to form but
hasn't recognized yet. For each: what the player sees, what `journal`
shows, what `remember` can surface, and what happens if they act on
the wrong reasonable interpretation. Determine whether the player can
recover in every case without the interface ever telling them which
of the three categories they're in. If that holds up in this one
hand-built mystery, the procedural system is worth building. If it
doesn't, that's cheaper to learn now than after building the
generator.

## Target experience

What a successful expedition should feel like, contrasted with what it
feels like today:

**Today:** spawn → find town → find loot → fight zombies → reach exit.

**Target:** survive → notice something unusual → investigate → form a
hypothesis → test the hypothesis through exploration → discover
relationships between places and objects → acquire what's needed →
reach the inferred escape route → escape.

The critical distinction: the player never sees the generator's
dependency graph. The generator knows, e.g., `mountains → mine → mining
settlement → records → blocked tunnel → equipment → tunnel escape`. The
player experiences something more like:

1. Finds an abandoned truck containing mining equipment.
2. Later finds a settlement with several mining-related buildings.
3. Finds a torn sign mentioning a mine.
4. Discovers the mine.
5. Finds the entrance blocked.
6. Finds evidence that equipment was stored elsewhere.
7. Searches another location.
8. Finds the equipment.
9. Realizes the mine tunnel may lead beyond the mountains.
10. Returns to the mine.
11. Clears/accesses the tunnel.
12. Escapes.

**The generator is creating a mystery, not a quest.** That distinction
should stay visible in every subsystem below.

## Classification, point by point

| # | Idea | Classification | Why |
|---|---|---|---|
| 1 | Core premise (survive→explore→discover→learn→prepare→travel→escape) | Needs modification | No code by itself — becomes real via #2/#5/#6/#7 below. |
| 2 | No known exit point | **Architectural risk (bounded)** | Touches one centralized check (`move_and_search()`'s `content == 'T'` branch) plus `self.won`/`settlement_explored`/`town_known`'s current meanings and the campaign-completion flow. Real but localized — one function owns the win check today. |
| 3 | Mountains as natural border | Split by phase — see below | Phase 1 small, Phase 3 real risk. |
| 4 | Irregular region, incremental | Same as #3 | |
| 5 | Town Center role change (win point → info-rich location) | Needs modification | Directly coupled to #2 — same code, same change. |
| 6 | Clues as real exploration layer | **Missing** | No fact/clue system exists. Needs new persisted state + a new `find_loot()` outcome category. |
| 7 | Discover before understand | **Missing** | Needs a multi-stage state model — see Knowledge State below. |
| 8 | Maps as knowledge, not loot | Already supports (partially) | `town_known`/the existing `"map"` loot type is real precedent — a found map already reveals geography without revealing everything else. |
| 9 | Settlements as organic populated regions | Needs modification | `_generate_settlement()`'s diamond boundary + district tags is a real head start, but placement is still a fixed `town_size × town_size` box independent of surrounding terrain. |
| 10 | Terrain landscape coherence | **Already supports** | Chunk-neighbor clustering + swamp terrain already landed. Verify only. |
| 11 | Restrict open-terrain loot | **Already supports** | `find_loot()` is already gated to building terrain and settlement content only. Confirmed, no change needed. |
| 12 | Loot progression bands | Needs modification | `LOOT_WEAPON_TABLE`/`ARMOR_TABLE` already band by `min_expedition` — a tuning/restructuring question, not a new system. |
| 13 | Day/night reinforcing exploration | **Already supports** | dawn/day/dusk/night phases, visibility radius, flashlight, and `TERRAIN_MOVE_MINUTES` (now including swamp) are all live. Verify pacing only. |
| 14 | Buildings as strategic locations | Needs modification | Safe-zone/rest bonus and building-gated loot already exist. Missing: clue-location tie-in and landmark-visible-from-distance. |
| 15 | Exploration = knowledge + resources | Missing | Same underlying gap as #6/#7 — the philosophy statement for it. |
| 16 | Campaign as narrative chapters | Needs modification | `expeditions_completed` already drives map/loot/zombie difficulty tier-by-tier — no narrative *text* framing exists per tier yet. |
| 17 | Campaign victory real payoff | Needs modification | A distinct ending message already landed — real but shallow. A real revelation needs the knowledge layer to have content to reveal. |
| 18 | Core philosophy | N/A | Informs #2/#5/#6/#7/#15, no separate implementation. |
| 19 | Discovery over direction (no quest markers) | N/A | A constraint on how #6/#7 get built — see "What the player should NOT see" below. |
| 20 | This assessment | — | — |

## Architectural risk by subsystem

- **Map representation:** low risk through mountain-boundary Phase 1-2
  (grid stays rectangular); real risk only at Phase 3 (per-expedition
  irregular playable shape).
- **Procedural generation (`generate_map()`):** moderate. Everything
  proposed is an *addition* to a function that already layers several
  independent randomness passes — not a rewrite, but the generation
  *order* likely needs to change (see Generation Order below).
- **Settlement generation:** moderate. The diamond-boundary technique
  is reusable, but truly organic settlements likely need a different
  algorithm — seed-and-grow or a random walk — not just parameter
  tuning.
- **Movement (`move_and_search()`):** low. It already centralizes
  terrain effects, encounter rolls, and loot; a knowledge-discovery
  branch and a changed win-check are additions, not a restructure.
- **Persistence:** moderate, mechanical, but with a real precedent for
  getting it wrong — see "Three kinds of state" below.
- **Fog of war:** low. Already does the hard part and is directly
  reusable.
- **TUI:** low-to-moderate. A knowledge-interaction panel is new UI
  real estate but purely additive.
- **Campaign progression:** low for chapter framing (already
  data-driven by `expeditions_completed`); moderate once win semantics
  diverge from "reach the Town Center" uniformly.

## Recommended build order

**Revised 2026-08-27** to insert player information architecture
*before* world-logic/mystery generation — the complexity that phase
produces needs somewhere for the player to hold it, or it's being
built with nowhere to land. This supersedes the build order in earlier
drafts of this document; the phase letters below are the current
ones — todo items filed earlier still carry their original `[Phase X]`
label text and may not match this lettering exactly. Ordering in
`version-4/.atlas/todo_list.json` is what's authoritative, not the label text on
any individual item.

**Phase A — world geometry, no premise change, ships independently:**
bounded map dimensions (see Physical & Information Budget below),
mountain-boundary Phase 1, terrain coherence (done), organic-settlement
tuning, zone/district layer, buildings as loot/landmark locations. Open-
terrain loot restriction and day/night pacing are already done — verify
only.

**Phase B — player information architecture, still no premise change:**
`look`/`inspect`, the Observed/Known/Suspected/Confirmed discovery-state
model, `journal` and its sub-views, `remember`, map annotation layers,
and persistence for all of it. Built and testable standalone, against
whatever flavor facts/locations already exist from Phase A, before the
deeper mystery-generation machinery in Phase C gives the player
something real to use these tools on.

**Phase B½ — automated investigation harness, depends on B's minimum
interface being answered (not necessarily fully built):** extend
`tools/balance_autoplay.py` with an investigation-aware bot policy that
uses the real command interface and only player-available information
(see Automated Expedition Simulation & Balance above), and the
mystery-specific telemetry it needs. Deliberately starts *alongside*
Phase C, not after — the whole point is testing Phase C's generator
while it's being built, not once it's finished.

**Phase C — world logic, depends on A and B existing:**
the region → zone → settlement → district → location hierarchy,
contextual loot, contextual zombie ecology, history generation,
infrastructure relationships, and the escape-mechanism template system
(data model, not yet wired to the win condition). **The Escape Proof
data structure and backward causal-chain validation (see that section
above) must exist before the first escape mechanism is implemented,
not added afterward** — build the mechanism generator first and
there's no rigorous way to tell later whether its mysteries actually
work. Test continuously against Phase B½'s harness as this lands, not
just at the end.

**Phase D — escape system, depends on C:**
Town Center role change, the escape-discovery win condition, mountain-
boundary Phase 3 (the pass/tunnel becomes the actual escape route) —
these three are really one coordinated change, since the new win
condition needs Phase C's clue chain to point at Phase D's actual exit.

**Phase E — campaign narrative, depends on D:**
campaign-as-chapters framing, campaign-aware escape-mechanism variety
(the shuffle-bag), and a real campaign-victory payoff.

**Not phase-gated, can slot in anytime after Phase A:**
mountain-boundary Phase 2 (organic boundary shape).

---

## Core design rule 1: the escape mechanism is per-expedition

The escape route is not a permanent property of Apocrysis — it's a
property of the individual expedition. Each new map asks "how does
*this* place allow someone to escape?", and the answer changes map to
map.

**The rule, verbatim:** every expedition has one primary escape
mechanism. Escape mechanisms are campaign-aware and should not repeat
during the early campaign until the available mechanism pool has been
exhausted (a shuffle-bag, not `random.choice()`). The selected
mechanism influences the geography, locations, clues, and requirements
generated for *that* expedition — it is not decorated onto an
otherwise independently-generated map afterward.

**Candidate mechanism pool (10, illustrative — not a final list):**
mountain pass, mining tunnel, abandoned highway, railway tunnel,
dam/service route, evacuation route, collapsed road requiring
clearing, hidden boat crossing, military access road, underground
infrastructure.

**Named-stage template schema:** each mechanism's generation chain
follows the same named stages, in order —

```
Geography -> Infrastructure -> Civilization -> Locations ->
History -> Clues -> Obstacle -> Requirement -> Escape
```

This is a real candidate for the mechanism template's actual data
shape, not just flavor text — the player only ever experiences it in
fragments and in whatever order they explore.

### Escape Mechanism Model (data shape)

| Field | Purpose |
|---|---|
| `id` | Stable mechanism identifier |
| `name` | Internal/display name |
| `geography_requirements` | Terrain/world conditions required |
| `infrastructure_type` | Road, rail, mine, dam, etc. |
| `civilization_types` | Settlements that plausibly emerge around it |
| `location_types` | Locations required/eligible |
| `history_seed` | Historical event/theme |
| `clue_types` | Evidence that can reveal the history |
| `obstacle_type` | Why the route isn't immediately usable |
| `requirement_types` | What must be discovered/acquired |
| `escape_location_type` | Final location |
| `minimum_map_space` | Space required to make the chain work |
| `generation_priority` | When it must be generated |
| `uniqueness_rules` | What can't coexist with it |
| `clue_distribution_rules` | How evidence is distributed |
| `completion_condition` | Exact condition for escape |

**Important constraint:** a mechanism defines *relationships and
constraints*, not a linear quest sequence. It is not `do A, then B,
then C, then D` — that would silently turn the game into a hidden
quest system with extra steps. It's a set of things that must exist
and how they relate; the player's discovery *order* is theirs, not the
generator's.

**Worked chain examples:**

```
Mining tunnel:  mountains -> mine -> mining camp/settlement ->
                mine records -> blocked tunnel -> required
                equipment -> escape

Abandoned highway: town -> road network -> checkpoint ->
                    collapsed bridge -> alternate road ->
                    mountain pass -> escape

Boat route:     large water body -> marina -> boat -> fuel ->
                navigation clue -> escape

Railway tunnel: rail-compatible terrain -> the railway itself ->
                a town/industrial area grows around it -> rail
                yard/station/maintenance buildings -> something
                happened to the railway -> signs/records/equipment/
                graffiti/abandoned vehicles -> tunnel blocked ->
                find another way in/equipment/restore access ->
                the tunnel itself
```

Picking the mechanism has to happen *early* in `generate_map()` —
before terrain/settlement placement, not after — since it determines
what the map should even contain. This is the single biggest
architectural implication in the whole design: procedural generation
moves from "generate objects that happen to coexist" to "generate a
world in which objects form a deliberate relationship chain."

**Player-facing effect (must be preserved):** the player should never
perceive this as templated ("Expedition 4, therefore mine"). They
should arrive at the inference themselves — "I keep finding mining
equipment, maybe there's something in those mountains" on one
expedition, "every road leads toward the old evacuation corridor" on
another.

---

## Core design rule 2: random composition, consistent logic

**The rule, verbatim:** Apocrysis should generate worlds that are
random in composition but consistent in logic. The player should be
able to learn the rules of the world without being able to predict the
specific world they will encounter.

Moving through forest → rural road → industrial area → suburb → city
should feel different not because terrain tiles changed, but because
*what exists there* changes — who lived there, what they left behind,
what danger accumulated there.

### Place hierarchy

```
World -> Region -> Zone -> Settlement -> District -> Location -> Contents
```

**Extended 2026-08-27** with a layer this version was missing —
people. Not necessarily NPCs walking around; evidence that specific
humans existed at a location and had relationships with other
locations/objects/each other. See "People, organizations, and
relationship evidence" under Environmental Storytelling below for the
full treatment:

```
... -> Location -> People/Organizations -> Objects/Infrastructure -> Evidence
```

Worked examples:

```
Rural region -> rolling woodland -> rural zone -> small settlement
    -> residential district -> farmhouse
    -> kitchen supplies, canned food, basic tools
    -> rural zombie population

Coastal region -> wetlands + large water -> industrial zone
    -> port district -> marina
    -> fuel, rope, boat parts
    -> drowned/swollen/Toxic-type zombies

Mountain region -> mountains + forest -> mining zone
    -> mining settlement -> industrial district -> mine
    -> tools, protective gear, blasting-equivalent resources
    -> workers/miners/Armored-type zombies
```

Each level narrows what the level below it can plausibly contain — the
player should never find a marina's contents inside a mountain mine.
`District` is the same concept `_generate_settlement()` already tags
(downtown/commercial/residential); the hierarchy adds `Region` above
`Zone` and formalizes `Location` (a single building or landmark) below
`District` as the level contextual loot/zombie tables actually key off.

### Generator dependency graph

```
EXPEDITION SEED
      |
      +-- Survivor
      |
      +-- Region Type
      |       |
      |       +-- Terrain
      |       +-- Climate
      |       +-- Resources
      |
      +-- Civilization
      |       |
      |       +-- Settlement Types
      |       +-- Districts
      |       +-- Locations
      |
      +-- Zombie Ecology
      |
      +-- Loot Ecology
      |
      +-- History
      |
      +-- Escape Mechanism
              |
              +-- Required Geography
              +-- Infrastructure
              +-- Locations
              +-- History
              +-- Clues
              +-- Obstacle
              +-- Requirement
              +-- Escape
```

**Generation flows downward. Player discovery flows upward.** That's
close to the fundamental architecture of this version of Apocrysis.

### Proposed generation order

1. Expedition seed
2. Survivor identity
3. Region/civilization selection
4. Escape mechanism selection
5. Required geography
6. Terrain generation
7. Infrastructure generation
8. Settlement placement
9. District generation
10. Location generation
11. Historical event generation
12. Zombie ecology
13. Loot ecology
14. Escape obstacle
15. Escape requirement
16. Clue placement
17. Fog-of-war initialization
18. Validation (see below)
19. Player spawn
20. Final reachability validation

**The generator must validate not merely that the player can
physically reach the escape location, but that the generated world
contains sufficient evidence for a player to reasonably discover the
escape mechanism.** That's a different, harder guarantee than the
current `_ensure_reachable()` provides.

### Concrete new pieces this implies

- A **zone/district layer** on top of terrain — terrain answers "what
  do I walk on," zone answers "what kind of place is this."
- **Zombie composition keyed to zone**, not just to
  `expeditions_completed` the way `_select_zombie_for_encounter()`
  works today.
- **Contextual, per-location-type loot tables** (garage, pharmacy,
  police station...) instead of one shared pool with rarity as the
  only axis.
- **Randomized player identity at spawn**, drawn from the existing
  `PLAYER_CLASSES` pool (`src/player.py` already has 22 archetypes)
  instead of always starting as the fixed `husband`/Kitchen Knife
  baseline. **Note:** this reverses an earlier explicit decision in
  this same design conversation ("strip out all player-class/
  progression material," keep husband/Kitchen Knife fixed) — recorded
  here so the reversal is visible, not silently overwritten.

---

## Loot & discoverable-content ecology

Added 2026-08-27, sharpening the "contextual, per-location-type loot
tables" bullet above into a real model. The current engine's loot is
a global resource table: `find building → roll generic loot → receive
weapon/armor/resource`, with `LOOT_WEAPON_TABLE`/`ARMOR_TABLE` banded
by `min_expedition` (see the earlier answer in this conversation for
the exact current tables). The proposed model is: `understand where
you are → infer what would plausibly exist there → search that
location → find resources and evidence`. This makes `LOOT_WEAPON_TABLE`/
`ARMOR_TABLE` genuinely obsolete, not merely bigger.

### Five loot categories, not one pool

1. **Survival resources** — food, water, medicine, ammo (the existing
   consumable types, now sourced contextually rather than uniformly).
2. **Equipment** — weapons and armor (the existing item types, now
   location-appropriate rather than expedition-tier-gated).
3. **Tools** — things useful for overcoming *physical* obstacles (a
   repair kit, mining equipment, boat fuel) — distinct from equipment,
   ties directly into the Escape Mechanism Model's `requirement_types`
   field.
4. **Evidence** — clues, records, signs, maps, objects that feed the
   knowledge system (see Knowledge State below).
5. **Infrastructure/context objects** — things that tell the player
   what this place *was*, independent of whether they're mechanically
   useful (a rail timetable board, a collapsed loading dock).

Giving every location type a reason to stock some subset of these five
is what turns "generic building" into "recognizably a pharmacy vs. a
police station vs. a farmhouse."

### Separate "loot" from "discoverable content"

This distinction matters architecturally, not just for flavor.
Searching one location (a mine, worked example) can produce things at
genuinely different tiers:

```
Location
├── physical_loot
│   ├── survival    (canned food, water, medical supplies)
│   ├── equipment   (mining helmet, work gloves)
│   └── tools       (pickaxe, protective gear)
│
├── environmental_evidence      (things simply OBSERVED, no search needed)
│   ├── observations  (mine entrance, abandoned carts)
│   └── landmarks     (railway connection, blocked tunnel)
│
└── searchable_evidence         (requires deliberate `search`/`inspect`)
    ├── records     (mine map, production ledger, maintenance log)
    ├── signs
    ├── objects
    └── relationships  ("ore shipments were sent north" — not tied
                         to any single object, emerges from combining
                         multiple pieces)
```

`environmental_evidence`/`searchable_evidence` are **not loot** in the
RPG sense — they're information produced by investigating a location,
and should route through the knowledge-state system (Observed → Known
→ Suspected → Confirmed), not the backpack. Collapsing evidence into
"just another loot roll with a low drop rate" is exactly the failure
mode this whole design direction is trying to avoid — it turns "find
loot → collect clue items → assemble quest" back into a checklist.

This gives two independent-but-interacting systems:

```
WORLD LOGIC
    |
LOCATION
    +-- contextual physical loot
    |
    +-- contextual evidence
              |
              v
        player knowledge
```

Evidence generation references the mechanism/history graph (Core
Design Rule 1); physical loot references the location's role in the
place hierarchy (Core Design Rule 2). They can layer at the same
location without being the same table.

### Illustrative location loot ecology (partial — not final)

| Location | Survival | Equipment | Tools | Evidence |
|---|---|---|---|---|
| Farmhouse | food, water, medicine | basic melee | tools | family records, road map |
| Garage | water, food | wrench/tool weapon | repair tools, fuel | vehicle records, route notes |
| Pharmacy | medicine | — | medical supplies | prescriptions, evacuation notices |
| Police station | medicine, ammo | firearms, armor | keys, breaching tools | incident reports, evacuation records |
| Railway station | food, water | light weapons | rail tools | timetables, station records |
| Mine | water, food | heavy melee, protective gear | mining equipment | mine maps, work logs |
| Maintenance shed | — | tools | specialized equipment | maintenance records |
| Marina | water, food | ranged weapons | fuel, rope, boat parts | navigation charts |
| Dam | water | industrial equipment | service equipment | engineering records |
| Military checkpoint | food, water | firearms, armor | access equipment | orders, evacuation maps |

The 10-location table above is illustrative shorthand; the full
catalog below (18 locations) is the actual content-authoring pass —
concrete item lists, rarity bands within each category, and which
escape mechanism(s) each location's evidence primarily supports.
Content only, no code — authored against the five-category model and
the `physical_loot`/`environmental_evidence`/`searchable_evidence`
split above. Treat every item name as illustrative, not final;
Common/Uncommon/Rare bands are relative *within* a location, not a
global rarity scale shared across locations (a "Rare" garage find and
a "Rare" hospital find aren't meant to be equally powerful — see the
Physical & Information Budget section's caution against letting any
one axis balloon).

### Loot ecology catalog (18 locations)

**Farmhouse** *(rural zone)*
Survival: Common — canned food, well water. Uncommon — preserved
meat, first-aid kit.
Equipment: Common — pitchfork, hunting knife. Uncommon — shotgun
(low ammo).
Tools: Common — hand tools, rope. Uncommon — chainsaw (fuel-gated).
Evidence: environmental — a burned field, an abandoned tractor;
searchable — family photos, a hand-drawn local road map, a diary
entry. Mechanism relevance: general/history-only (rarely load-bearing
for an escape chain, mostly atmosphere and early-game "where am I").

**Garage** *(suburban/rural)*
Survival: Common — bottled water. Uncommon — energy bars.
Equipment: Common — wrench (melee), tire iron. Uncommon — nail gun
(ranged-ish, low damage).
Tools: Common — repair kit components, spare fuel. Uncommon — a full
vehicle battery, jumper cables.
Evidence: environmental — a half-repaired vehicle, oil stains leading
outward; searchable — a vehicle registration, a route map with a
hand-marked detour. Mechanism relevance: **abandoned highway**.

**Pharmacy** *(suburban/downtown)*
Survival: Common — bandages, basic medicine. Uncommon — antibiotics.
Rare — a full trauma kit.
Equipment: none (this location's identity is medicine, not weapons —
deliberately absent, not just low-probability).
Tools: Uncommon — a pharmacist's toolkit (useful for the `repair_kit`-
style requirement chain).
Evidence: environmental — a shattered display case, empty shelves;
searchable — a prescription log, an evacuation notice taped to the
counter. Mechanism relevance: **evacuation route** (prescription logs
plausibly reference relocated patients/staff).

**Police station** *(suburban/downtown)*
Survival: Common — rations from a break room. Uncommon — medicine
from a first-aid locker.
Equipment: Common — a sidearm, a stab vest. Rare — a shotgun, riot
armor.
Tools: Common — handcuff keys, a crowbar. Uncommon — breaching tools.
Evidence: environmental — barricaded windows, a burned patrol car;
searchable — incident reports, an evacuation-corridor map, dispatch
logs. Mechanism relevance: **evacuation route**, **military access
road** (police/military coordination records).

**Railway station** *(industrial zone)*
Survival: Common — vending-machine food/water.
Equipment: Common — a length of pipe, a signal flare gun.
Tools: Uncommon — rail maintenance tools, a set of heavy bolt
cutters.
Evidence: environmental — rusted tracks, a boarded ticket window;
searchable — a timetable board, a maintenance log, a torn evacuation
notice. Mechanism relevance: **railway tunnel** (primary).

**Mine** *(mountain zone)*
Survival: Common — canteens left by workers.
Equipment: Uncommon — a pickaxe (heavy melee). Rare — a miner's
sidearm.
Tools: Common — mining helmet, protective gear. Rare — blasting-
equivalent clearing equipment (a `requirement_type` payload, not
flavor).
Evidence: environmental — the mine entrance itself, abandoned ore
carts; searchable — a mine map, a production ledger, a maintenance
log referencing a "northern access." Mechanism relevance: **mining
tunnel** (primary).

**Maintenance shed** *(any zone, usually paired with infrastructure)*
Survival: rare/none (not this location's role).
Equipment: none.
Tools: Common — general repair tools. Uncommon — mechanism-specific
requirement items (context-dependent — this is the location TYPE
`requirement_types` in the Escape Mechanism Model most often resolves
through).
Evidence: searchable — maintenance records, a supply requisition
form. Mechanism relevance: generic — appears adjacent to whichever
mechanism is active (railway maintenance shed, dam maintenance shed,
etc.), not a fixed pairing.

**Marina** *(coastal zone)*
Survival: Common — bottled water, canned goods from a dockside store.
Equipment: Uncommon — a flare gun, a boat hook (melee).
Tools: Common — rope, fuel canisters. Rare — a functioning boat
engine part.
Evidence: environmental — beached/sunken boats, a collapsed dock;
searchable — navigation charts, a harbor log, a fuel requisition
form. Mechanism relevance: **hidden boat crossing** (primary).

**Dam** *(mountain/rural)*
Survival: Common — a stocked break room.
Equipment: none/rare (not an equipment-rich location by design).
Tools: Uncommon — service equipment, a valve wrench. Rare — pump
equipment (requirement-tier).
Evidence: environmental — the dam structure itself, a flooded access
road; searchable — engineering records, a maintenance-access
schematic. Mechanism relevance: **dam/service route** (primary).

**Military checkpoint** *(any zone)*
Survival: Common — MREs, water rations.
Equipment: Uncommon — a rifle, body armor. Rare — a full tactical
loadout.
Tools: Common — access keycards/passes.
Evidence: environmental — sandbag barricades, a burned-out vehicle;
searchable — deployment orders, an evacuation-corridor map with
military annotations. Mechanism relevance: **military access road**
(primary), **evacuation route**.

**Grocery store** *(suburban)*
Survival: Common — abundant food/water (this location's identity).
Equipment: rare (a box cutter, at most).
Tools: none.
Evidence: environmental — looted/untouched shelves (a meaningful
signal either way — looted implies others survived long enough to
scavenge); searchable — a community corkboard with notices.
Mechanism relevance: general/history-only.

**Hospital** *(downtown/hospital zone)*
Survival: Uncommon — medicine (higher tier than a pharmacy). Rare —
specialized medical equipment.
Equipment: rare (improvised only — this is a dangerous, not
weapon-rich, location).
Tools: Uncommon — surgical/technical tools.
Evidence: environmental — overturned gurneys, a triage sign; searchable
— patient records, an evacuation-priority list, a director's log
describing when/why the facility was abandoned. Mechanism relevance:
**evacuation route**, general history (hospitals are often where the
"what happened here" thread starts). Notably dangerous — see the
zone-aware zombie ecology todo, Toxic/medical-flavored variants
cluster here.

**School** *(suburban)*
Survival: Common — a stocked cafeteria pantry.
Equipment: rare.
Tools: rare.
Evidence: environmental — a classroom mid-lesson, a gymnasium set up
as a shelter; searchable — an evacuation roster, a PA announcement
transcript pinned to a board. Mechanism relevance: **evacuation
route** (schools plausibly served as staging points).

**Gas station** *(rural/highway)*
Survival: Common — convenience-store food/water.
Equipment: Uncommon — a tire iron.
Tools: Common — fuel. Uncommon — a road atlas (a real navigational
tool, not just flavor).
Evidence: environmental — abandoned vehicles at the pumps; searchable
— a receipt log with a timestamp cluster (evidence of a mass
departure), a hand-marked road map. Mechanism relevance: **abandoned
highway** (primary).

**Ranger station** *(rural/forest, mountain-adjacent)*
Survival: Common — rations, a water filtration kit.
Equipment: Uncommon — a hunting rifle.
Tools: Common — a compass, rope, climbing gear (requirement-tier for
mountain-pass mechanisms).
Evidence: environmental — a fire watchtower, marked trailheads;
searchable — a regional trail map, a logbook noting an "old pass, not
maintained." Mechanism relevance: **mountain pass** (primary).

**Warehouse** *(industrial zone)*
Survival: Uncommon — bulk stored goods.
Equipment: Uncommon — a forklift's improvised parts (melee), a
nail gun.
Tools: Common — heavy tools, pallet equipment.
Evidence: environmental — collapsed shelving, a loading dock;
searchable — shipping manifests (useful for tracing what left the
region and when). Mechanism relevance: **underground infrastructure**,
general logistics evidence for other mechanisms.

**Quarry** *(mountain zone)*
Survival: rare.
Equipment: Uncommon — heavy tools as improvised melee.
Tools: Uncommon — clearing/blasting-equivalent equipment (a second
possible source for this requirement type, alongside the mine).
Evidence: environmental — a collapsed access road, heavy machinery
left mid-operation; searchable — a site survey, a closure notice.
Mechanism relevance: **collapsed road requiring clearing** (primary).

**Radio/relay station** *(any zone, usually elevated terrain)*
Survival: rare.
Equipment: rare.
Tools: Uncommon — communications equipment (occasionally a
requirement for a mechanism needing coordination/signal evidence).
Evidence: environmental — a fallen antenna tower; searchable — a
radio log, a final transmission transcript. Mechanism relevance:
general/history hub — often the single richest environmental-history
source regardless of which mechanism is active, since a relay station
plausibly logged evacuation-era radio traffic for the whole region.

### Notes on using this catalog

- Not every mechanism needs its own dedicated location type — several
  locations above (maintenance shed, radio/relay station, warehouse)
  are deliberately generic/reusable across mechanisms, since the
  Escape Mechanism Model's `location_types` field should be able to
  pull from a shared pool, not require one bespoke location per
  mechanism.
- Rarity bands are illustrative starting points for the Phase C
  loot-band todo (`2977a8a1`) to tune against real generation, not
  locked probabilities.
- This catalog should grow, not stay fixed at 18 — the "Notes on using
  this catalog" bullet above about shared/generic locations is what
  makes adding a 19th, 20th, etc. location type cheap once the
  five-category shape exists in code.

### Loot selector: replace expedition-gating with contextual composition

Stop using `expeditions_completed` as the *primary* loot selector.
The current model:

```
min_expedition -> what can spawn
```

becomes:

```
location type + zone/ecology + civilization + expedition
progression + mechanism/history -> contextual loot/evidence
```

Expedition progression still influences *quality and availability*
within what a location plausibly has — a level-9 pharmacy can have
rarer medical supplies or more dangerous surroundings than a level-1
one — but a pharmacy should never suddenly produce a katana because
the expedition counter crossed a threshold. A mine has mine things
because it's a mine, not because expedition 6 unlocked the Iron Axe.

### Zombie drops need the same treatment

`combat_mixin.py`'s `handle_loot()` currently gives every zombie type
the same two-item pool (`MeleeWeapon("Sword", 15, 25)` or
`RangedWeapon("Gun", 20, 5)`, hardcoded, un-banded, ignoring even the
`min_expedition` gating the exploration tables have) — this is exactly
the disconnected procedural randomness the new design is eliminating
elsewhere. A miner-flavored zombie could plausibly carry a pickaxe or
protective gear; a police-flavored zombie could carry police
equipment; a military-flavored zombie could carry military equipment.
Treat loot-table redesign and zombie-ecology redesign (already queued
as a separate todo) as parallel halves of the same contextualization
work, not sequential ones — a zombie's loot table should derive from
the same location/zone context that determines which zombie type can
appear there in the first place.

---

## Environmental storytelling & visual world grammar

Added 2026-08-27. Investigation only — defines what information *can*
be communicated through terrain, ASCII glyphs, color, location states,
objects, human traces, and environmental history, without adding
another information-management system on top of the ones already
specified. Not an implementation spec yet.

**The governing principle:** don't make the world more detailed by
putting more stuff into it — make it more detailed by making the stuff
that already exists tell a coherent story. For a text interface this
is a real strength, not a limitation: ASCII plus color can communicate
relationships, history, danger, and significance without needing large
amounts of prose.

**The trick that keeps this compatible with the Physical & Information
Budget:** distinguish detail the player *sees* from detail the player
*needs to understand*. The first can be large — trees, roads, fences,
wrecks, signs, machinery, debris, vehicles, tracks, barricades,
graffiti, vegetation. The second stays exactly as bounded as already
specified (8-30 locations, 8-40 evidence, 5-10 facts, 2-4 questions, 1
escape hypothesis). The world can be visually dense while the mystery
stays small — that's the actual design win here, not "more content."

### Terrain has identity

Beyond the existing terrain symbols (`TERRAIN_SYMBOLS`, constants.py),
terrain should read as visually distinct ecological regions rather
than a symbol soup — forest as dense visual texture, mountains as
visually imposing, swamp as murky/irregular, developed land showing
roads/foundations/cleared ground, abandoned infrastructure visually
distinct from natural terrain. This is a rendering-layer investigation
on top of the terrain-clustering work already landed (chunk-neighbor
biasing), not a new generation system.

### Civilization leaves fingerprints

A settlement's *shape* should reflect its history, not read as a
uniform block of building glyphs. A mining settlement's layout
(clustered near a rail line feeding the mine) should look visually
different from a military settlement's (checkpoints, barriers,
barracks, vehicle staging) or a rural settlement's (fields, barns,
fences, wells, dirt roads) — the player should be able to infer what
kind of place they're in from the *shape* on the map before anything
explicit tells them. This extends the organic-settlement todo already
queued (seed-and-grow footprints) — the shape isn't just organic, it's
organic *in a way specific to that settlement's type*.

### Locations have visual states that accumulate meaning

A location's rendering (and description) should change as the player
learns more about it — not by revealing new tiles, but by the *same*
location acquiring meaning. E.g. a gas station renders plainly until
the player notices abandoned vehicles at the pumps; inspecting reveals
"several vehicles were abandoned facing east, doors open"; a later,
unrelated discovery (a receipt log showing a spike in fuel purchases
in one three-hour window) retroactively makes that same gas station
more significant. World detail should accumulate *semantically* — the
map isn't getting prettier, the player's interpretation of it is
changing. This is a direct extension of "the map as a knowledge
surface" (Player Cognition & Information Architecture) — same
mechanism, framed here as a content/storytelling technique rather than
a UI feature.

### Color should have a grammar, not be decorative

Color communicates *information state*, tied directly to the
Observed/Known/Suspected/Confirmed model: neutral (ordinary terrain),
subdued highlight (observed, uninterpreted), stronger highlight (a
known relationship), a distinct treatment for suspected vs. confirmed,
a warning treatment for dangerous locations, ordinary fog for
unexplored, and a temporary emphasis for something just discovered
this session. The same map structure should be able to communicate
more as the player's knowledge changes, without the UI ever needing to
announce "ESCAPE MECHANISM DISCOVERED!" — the world becomes gradually
more legible instead. Investigate against Textual's actual theming
capability (see `src/tui.py`'s existing `$accent`/health-color
pattern in `_render_map_lines()` for the precedent this would extend)
before locking in a palette.

### Layered map views

The existing `map`/`map terrain`/`map locations`/`map knowledge`
sub-view idea (Player Cognition & Information Architecture) can be
made concrete as genuinely different renderings of the same
underlying map data, not just different data included/excluded:
a terrain view (plain ecology), a location view (adds
buildings/landmarks), an infrastructure view (adds connections —
roads, rail, power lines as drawn links between locations), and a
knowledge view (infrastructure view, but connections/locations render
according to the color grammar above — a `?` where a relationship is
suspected but not confirmed). These are visualization modes over one
data model, not four separate map representations to generate and
keep in sync.

### Variable "abandoned" states

A location's abandonment should have a *cause*, and each cause should
imply different placed content — not a single generic `abandoned:
true` flag. Candidate states: normal abandonment, hurried evacuation
(desks overturned, doors open, personal items left mid-use), barricaded
(boarded/sandbagged, implies defenders who didn't survive or didn't
stay), burned, looted (implies other survivors passed through),
partially occupied (someone was here more recently than the rest of
the region), recently disturbed (implies current activity — a hook for
danger, not just history), flooded, collapsed, deliberately sealed
(implies someone made a choice, not just decay), maintained until
recently (implies the collapse was gradual, not sudden). Same location
*type* can read as an entirely different story depending on which
state generation assigns it — a cheap way to multiply perceived detail
without multiplying the number of location types.

### Zombies as environmental storytelling, not just a combat table

Extends the zone-aware zombie ecology work already queued: don't just
place a zombie type keyed to zone (`mountain → miner-flavored`) —
place it somewhere that implies *why* it's there. A miner-flavored
zombie standing in a mine's worker area or barracks; a police-flavored
zombie at a checkpoint or a station's holding area; a hospital's
Toxic/medical-flavored zombie specifically in an emergency entrance,
ambulance bay, or a labeled "contaminated wing." The placement is
environmental history, the type is ecology — both should derive from
the same location context, reinforcing rather than duplicating the
already-queued zombie-ecology work.

### People, organizations, and relationship evidence

The biggest genuinely new concept in this section. The place hierarchy
(`World → Region → Zone → Settlement → District → Location`) is
missing a layer: **people** — not necessarily NPCs, but evidence that
specific individuals existed and had relationships crossing multiple
locations. A farmhouse might contain evidence "the owner worked at the
northern mine"; the garage, "his truck was serviced here"; the mine,
his employee record; the school, his child's evacuation roster. Four
otherwise-unrelated locations become one human story once connected —
and critically, **the generator knows the relationship before the
player does**, the same asymmetry already established for the escape
mechanism itself (Core Design Rule 1).

Candidate relationship graph, crossing location boundaries the way the
Escape Mechanism Model's stages already do:

```
PERSON
  |-- worked at    -> MINE
  |-- lived at     -> FARMHOUSE
  |-- owned        -> TRUCK
  \-- evacuated via -> RAILWAY

MINE
  |-- supplied      -> TOWN
  |-- connected to  -> RAILWAY
  \-- maintained by -> PERSON
```

This is compatible with the existing architecture without requiring a
new generation pass from scratch — it's the same relationship-chain
idea the Escape Mechanism Model already uses, generalized from "one
chain per escape mechanism" to "any number of person/place/object
relationships," some of which may be escape-relevant and some purely
atmospheric (most should be the latter, per the information budget —
not every generated relationship needs to matter for the escape).

### Summary: the two tiers of detail

```
Detail the player SEES        (can be large)
  trees, roads, fences, wrecks, signs, buildings, machinery,
  debris, vehicles, tracks, barricades, graffiti, vegetation

Detail the player NEEDS TO UNDERSTAND    (stays exactly as bounded
                                           as already specified)
  8-30 meaningful locations
  8-40 evidence pieces
  5-10 established facts
  2-4 active questions
  1 escape hypothesis
```

The world can be dense while the mystery stays small. That's the
actual mechanism by which Apocrysis avoids both directions of failure
this whole document has been guarding against — Zelda-scale sprawl on
one side, a database-management UI on the other.

---

## Persistent world & interaction model

Added 2026-08-27. The biggest missing category from earlier drafts:
the document was strong on *what exists, why it exists, how the player
understands it, how they escape* — and silent on *what happens after
the player touches the world, whether that persists, what the player
can rely on when they return.* Run every answer below through The
Governing Test above.

### Physical persistence vs. knowledge persistence — the core split

**Decided.** These are two different state systems, and conflating
them is a real design trap:

```
WORLD               (what still physically exists)
  |
PLAYER DISCOVERS IT
  |
KNOWLEDGE            (what the player has learned)
```

A mine map can later burn. The knowledge gained from reading it must
not. Concretely, evidence needs three states, not two:

- **Unseen** — physical evidence exists, player hasn't found it.
- **Discovered** — player found it; knowledge is recorded permanently
  (feeds the Observed/Known/Suspected/Confirmed model — Knowledge
  State below is downstream of this, not a replacement for it).
- **Consumed/removed** — the physical object is gone (destroyed,
  looted by the world, whatever), but discovered knowledge remains.

**The rule, verbatim:** once the player has legitimately discovered
evidence, that evidence remains available to the player even if the
physical object is later destroyed, moved, or inaccessible. The world
remembers physical things; the player remembers discoveries.

**Revisiting evidence — decided, keep both forms distinct.** The
journal should be able to show two different things about one piece
of evidence: the raw evidence itself (what was actually found — "Evac
notice: workers directed through the northern tunnel") and the current
interpretation of it (what it currently means — "Known: workers used
the northern tunnel during evacuation"). Keep them visually distinct;
this becomes important if interpretation can ever change (see
"Contradiction and false leads" below). Re-finding the exact physical
object a second time (`search farmhouse` again) should generally not
re-surface it — the journal is the durable record, not the world.

### Zombies: ecological, not static or naively respawning

**Decided, with an important constraint.** Preferred model: zombies
are generated from environmental/ecological conditions, a spawned
zombie is a real world entity, killing it removes that entity, and new
zombies can emerge/migrate according to explicit world rules — but **a
killed zombie must not respawn in the same square merely because the
player returned.** Otherwise player action doesn't change the world,
which directly fails The Governing Test. Consequence worth protecting
deliberately: the player can make the world safer through their own
actions, and should be able to trust that.

**Open (design questions, not yet decided — do not implement any of
these without a decision):** persistent per-zombie identity; whether
zombies can move between tiles or follow the player; migration between
locations or ecological zones; whether killing zombies measurably
reduces local danger; noise-triggered spawns; whether a cleared
location can be repopulated later; whether night changes zombie
movement/spawn behavior (beyond the existing encounter-chance bump);
finite vs. effectively-unbounded population per expedition; whether
the world simulates zombies outside the player's current visibility;
whether time advances while the player is elsewhere; whether an
abandoned location can become *more* dangerous with time, not just
static.

### World objects: dropped items, containers, and environmental change

**Decided:** dropped items are persistent by default — a shotgun
dropped at one tile and found 30 turns later should still be there
unless the world has a specific reason for it not to be. This is the
same trust principle as evidence persistence. Item states: `INVENTORY`
(player-owned), `WORLD OBJECT` (persistent physical object at a
location), `CONSUMED`/`DESTROYED` (removed from the world), `MOVED`
(exists, but elsewhere — e.g. salvaged/relocated by another entity).

**Open (design questions):** can containers hold items, and can items
move between containers; can zombies move or drop items; can the
player deliberately stash supplies for later; can environmental
objects be destroyed (doors, barricades, vehicles, fuel, boats); do
player-caused changes (a cleared obstacle, a broken barricade, an
opened door) persist permanently once made; can the player leave their
own markers/signs for their future self.

### Player-caused world changes need a stated philosophy, not a feature list

**Open, but the framing is decided:** the design needs an explicit
answer to *which parts of the world are immutable scenery and which
are manipulable state* — not a feature checklist (open doors, clear
rubble, repair infrastructure, move vehicles, drain water, restore
power, activate machinery, destroy bridges, start fires, restore radio
stations, use generators). Don't build all of these; decide the
philosophy first, since it determines which ones are even candidates.
This is directly downstream of the Escape Mechanism Model's
`requirement_types` and `obstacle_type` fields — "clear the tunnel
obstruction" is already an implied instance of "player permanently
changes world state," so the philosophy question is really "how far
beyond the escape-critical cases does this go."

### Time as world state, not just visibility

**Open.** Day/night currently mostly means "affects visibility" (plus
the existing hunger/thirst decay and encounter-chance bump). Whether
time is a deeper world-state axis — zombie movement/density,
environmental hazards, resource availability, world deterioration,
whether the world changes while the player isn't actively exploring a
given tile — is a real fork with two very different resulting games,
both valid, not yet chosen. Needs a decision, not a default.

### Are people historical or simulated?

**Open, real fork.** The People/Organizations layer (Environmental
Storytelling above) can mean two different things: **historical
entities** reconstructed only through evidence you find (a name, a
job, a possession — inferred backward from artifacts), or **simulated
entities** whose actual sequence of events (lived here → worked there
→ owned this → evacuated via that) is generated *first*, with evidence
derived *from* that generated history rather than authored
independently per location. The second is richer and doesn't require
any actual NPCs walking around to get the benefit — the world would be
generating the remnants of an actual story, not clues about one. Worth
resolving before the People/Organizations todo is implemented, since
it changes what that generation pass actually needs to produce.

### What "history" actually generates

**Open, but the shape is proposed:** `historical event generation`
(already named as a Phase C requirement) should probably unify as:

```
WORLD HISTORY -> major events -> local consequences ->
people affected -> infrastructure changes -> abandonment
state -> physical evidence
```

E.g. an evacuation event cascades into: railway used heavily → station
partially abandoned → vehicles left behind → records left behind →
some people escaped, some didn't. This is what would make Variable
Abandonment States (Environmental Storytelling above) *generated*
consequences of history rather than independently rolled flavor.

### World age and decay

**Open.** If the outbreak happened years ago, why is there still
usable food, an unrusted vehicle, working paper records, a flashlight
with charge? Realism isn't the goal, but *consistent* decay rules are
— a world-age/decay model (recently abandoned / weeks / months / years
/ long-term decay) that environmental evidence and item availability
derive from, especially now that Variable Abandonment States exist and
need to interact with it coherently.

### Contradiction and false leads

**Open, and probably the most consequential open question in this
section for how satisfying the mystery actually feels.** The
Observed → Known → Suspected → Confirmed model (Knowledge State below)
implicitly only moves forward. Real investigation needs to at least
leave room for `Known → Contradicted → Reinterpreted` later, even if
v1 doesn't build it — the data model shouldn't make it structurally
impossible. Sharper questions: can evidence support more than one
interpretation; can the player form an incorrect hypothesis and be
wrong (not just under-informed); how does the game let them discover
they were wrong; can a false hypothesis meaningfully cost time; how
many plausible-but-wrong escape hypotheses should exist alongside the
one real one. The distinction that matters: "the game gave me no idea
what to do" (bad ambiguity) vs. "I thought the dam was the answer, I
was wrong, the evidence actually points toward the railway" (good
ambiguity) — those feel completely different to a player even though
both are "the player was wrong for a while."

### Escape as its own multi-step arc, and whether it can fail

**Open, but leaning toward a specific shape:** `escape_success = True`
the instant a hypothesis is confirmed is too thin. Stronger arc:
`discover → confirm → prepare → travel → execute`, where the player
can act whenever they choose once escape is *possible*, not the moment
it's merely understood — "I know how" and "I'm doing it" are different
moments and should probably stay different. Whether an escape attempt
can fail is a related open question: arriving at the mountain pass
without the required equipment saying "you can't escape yet" is
low-risk and probably fine; whether a genuinely bad/premature attempt
can cost resources, injure the player, or — most interestingly — itself
generate new evidence ("that route is impassable after all, but you
notice something else while trying") is a real design opportunity, not
yet decided.

### Death and knowledge

**Open, with real tension.** Does dying mid-expedition mean the whole
expedition (world + knowledge) is lost, or does discovered knowledge
survive death the way profile-level stats already do? The second is
appealing (failed expeditions still teach the player something) but
risks letting the player brute-force a mystery through repeated deaths
instead of investigation — worth resolving deliberately, not by
default inheriting whatever `save_profile()`/`apply_profile()` already
happens to carry forward.

### Save/load must restore exact world state, not just the seed

**Decided.** Once any of the above persistence is real (dropped items,
killed zombies, cleared obstacles, discovered evidence, knowledge
states), a save has to capture actual world state, not just the
generation seed plus current position — replaying the same seed
without the accumulated state would make the persisted world
non-deterministic relative to what the player actually experienced. A
save should reasonably need: world seed, world generation state,
current turn/time, player position, inventory, dropped/world objects,
dead vs. living zombies, opened/cleared/broken environmental state,
discovered locations, discovered evidence and its state (unseen/
discovered/consumed), knowledge states, active hypotheses, map
annotations, escape progress, and campaign state. This is a real
expansion of the existing persistence work (`save_game()`/`load_game()`
and `save_profile()`/`apply_profile()`, `persistence_mixin.py`), not a
new system from scratch.

### Can the player "break" the mystery?

**Open, leaning toward a specific answer.** If a player physically
stumbles onto the escape tunnel before finding any clues, can they
just use it? Leaning toward: **the player can physically encounter the
answer early, but can't necessarily recognize or effectively use it
until they've learned enough** — preserves discovery-over-direction
(What The Player Should NOT See, above) without hard-blocking physical
access, which would feel like an invisible wall.

### Distinguishing "important" from "interesting"

**Open, and needed before the loot ecology catalog's evidence
entries get generated at scale.** Not every discoverable thing is
escape-relevant — a farmhouse diary about someone's daughter, a burned
school, unexplained graffiti, a wrecked ambulance. Without a
classification, the 8-40 evidence budget quietly becomes "8-40
things," some load-bearing and some not, indistinguishable to the
generator. Candidate classification: `load-bearing` (supports escape
inference directly), `corroborating` (reinforces an escape inference
without being required), `contextual` (explains the world, no escape
relevance), `atmospheric` (adds story, requires no interpretation),
`misdirecting` (appears meaningful, isn't). This is what keeps the
two-tier detail philosophy (Environmental Storytelling above) honest
at generation time, not just as a design intention.

### What inference is the player actually allowed to make?

**Open, and probably the hardest single question in this whole
document.** "The railway runs north" plus "mountains are north"
reasonably supports "the railway might lead into the mountains" — but
does it support "therefore the railway is the escape route"? Too
literal a model (clue → exact predefined fact, nothing inferred) makes
the mystery mechanical; too loose a model (player notices two vaguely
related things, the game decides they "figured it out") makes it
arbitrary. This is precisely what the Escape Proof (above) needs to
define concretely, not just qualitatively — each `deduction` in the
proof needs a stated sufficiency condition (which specific evidence
combination legitimately supports it), not just a list of contributing
evidence.

### Replayability at the mystery level

**Open.** Beyond mechanism repetition (the shuffle-bag, already
decided) — can the same mechanism type produce substantially different
underlying histories; can the same location type play different roles
across expeditions; can the same evidence type mean different things
in different expeditions; does the campaign gradually teach players
the world's "grammar" (railways are *often* important infrastructure,
so investigate one — a learned heuristic, not "railway always means
escape," which would make the mystery predictable rather than
learnable).

## Questions we aren't asking

Added 2026-08-27. A deliberate checkpoint, not yet answered — recorded
so these don't get silently decided by whatever the first
implementation happens to do.

**World:** What is this world's age? What physically decays, what
stays functional? What causes a location to become more dangerous
over time — or safer? What traces do human actions leave; what traces
do zombie actions leave?

**Player:** Which actions permanently change the world, which are
reversible? What can the player safely assume will persist? What
happens when something is lost? Can the player leave their own
landmarks, or deliberately leave information for a future self? How
much can a player exploit knowledge carried over from a previous
expedition?

**Investigation:** Can evidence be wrong, incomplete, or contradictory?
Can a hypothesis be abandoned, or grow stronger/weaker over time? Can
the player discover the answer by accident? Can they solve the mystery
without visiting every required location, or without finding the
"intended" clue for a given deduction?

**Escape:** What exactly constitutes "knowing enough"? What
constitutes "being ready"? Can the player attempt escape prematurely,
and what happens if they do? Can there be multiple apparent exits —
one real, several false leads? Is the final escape itself its own
small investigation? Does the player know a given attempt is their
last one?

**World building:** Who built these places, and why here? Who used
them, and what relationships connected them? What happened to those
people? Why was the place abandoned, and what evidence would that
event physically leave? Which evidence survives, which decays, which
is misleading without the right context?

**Game design:** What makes investigation satisfying rather than
tedious? How much uncertainty feels exciting vs. frustrating? How
often should an "aha" moment land? How long can the player go without
meaningful information before it feels like wandering? How much
backtracking reads as detective work vs. busywork? How much irrelevant
evidence is healthy, and how much can the player ignore and still
succeed? What does mastery look like after ten expeditions?

## Knowledge state

**Revised 2026-08-27** to a simpler four-state model — supersedes an
earlier six-stage draft (`Unknown → Observed → Recognized → Connected →
Understood → Actionable`), which is folded in here rather than dropped:
`Recognized`+`Connected` collapse into `Known`, `Understood` becomes
`Suspected`, `Actionable` becomes `Confirmed`. The six-stage version is
finer-grained and could still inform sub-states inside `Known` later;
the four-state version is what should actually get built first — it's
the smallest model that supports the discover-before-understand
mechanic (#7) and gives the journal something legible to render.

| Stage | Meaning | Example |
|---|---|---|
| Observed | Directly encountered, no meaning attached yet | "There is a railway." |
| Known | A fact established through evidence | "The railway connected Milltown to the mountain settlement." |
| Suspected | A player hypothesis supported by incomplete evidence | "The railway may be an escape route." |
| Confirmed | A conclusion established by sufficient evidence | "The railway tunnel leads out of the region." |

This is a **player knowledge model**, not just a generation mechanic —
it's the actual state each fact/location carries in `known_facts` (or
whatever the eventual data structure is named), and it's what the
`journal`/`remember` commands (see Player Cognition & Information
Architecture below) render.

**State transitions must be automatic, not player-issued.** There is
no `confirm railway` command. The player never manually promotes a
fact from `Suspected` to `Confirmed` — the world causes the transition
when the player encounters evidence that warrants it (finding the
tunnel's far end, say), and the interface reflects a state that
already changed, rather than the player operating the state machine
directly. The player thinks the conclusion; the system records it
because the evidence now supports it. (This mostly resolves the open
question "are facts automatically recorded, or must the player
explicitly `inspect`?" — inspecting/searching/observing is what
surfaces evidence to the player and may be required for *that*, but
the resulting state transition itself is never a separate player
action.)

### Facts vs. clues

A clue isn't necessarily a fact. E.g. "Mine trucks found near northern
settlement" is *evidence*; the resulting fact might be "there is
probably a mine somewhere north," and later "the mine connects to the
mountain interior," and eventually "the mine tunnel is an escape
route." The full chain:

```
World evidence -> Observation -> Candidate interpretation ->
Fact -> Relationship -> Inference
```

This distinction opens the door to false or incomplete interpretations
later (a more interesting game), but v1 does not need that complexity
— the assessment should just acknowledge the distinction exists so
`known_facts`' data shape doesn't get built too flat to ever support it.

---

## Escape proof & causal-chain validation

Added 2026-08-27. The single most important addition to the validation
architecture — sharpens "the generator knows the answer and deliberately
obscures it" (stated as far back as the opening of this document) into
something actually testable. **Recommended as a Phase C requirement
before the first escape mechanism is implemented** — build the
mechanism generator first and you'll discover only afterward that
there's no rigorous way to tell whether its mysteries actually work.

**The distinction this section exists to make:** "the escape exists
and is physically reachable" is not the same claim as "a player using
only what the game exposes can discover that it exists, understand the
evidence, and successfully act on that understanding." Every
expedition needs three separate guarantees, not one:

1. **Physical solvability** — there is a path to the escape.
2. **Logical solvability** — the generated evidence actually supports
   the intended conclusion.
3. **Player solvability** — a player using only what the game exposes
   can reconstruct that conclusion.

### The Escape Proof

A private, generator-internal structure — never shown to the player,
not a quest, not the schema's `location_types`/`clue_types` fields
themselves but the actual instantiated proof that a *specific*
generated expedition's evidence set supports its *specific* escape
hypothesis. Worked example:

```
ESCAPE PROOF
------------
Escape mechanism: Railway Tunnel

Required world facts:
    F1  Railway exists
    F2  Railway connects settlement to mountains
    F3  Northern tunnel exists
    F4  Tunnel is blocked
    F5  Clearing equipment exists
    F6  Tunnel leads beyond playable region

Evidence:
    E1  railway cutting            -> F1
    E2  station sign                -> F1
    E3  evacuation record           -> F2
    E4  mine/rail maintenance record -> F3
    E5  blocked tunnel observed     -> F4
    E6  maintenance shed equipment  -> F5
    E7  tunnel exit observation     -> F6

Required deductions:
    D1  railway is connected to mountain region
    D2  northern tunnel is significant
    D3  tunnel may provide passage through mountains
    D4  tunnel can be made usable

Escape hypothesis:
    H1  railway tunnel is an escape route

Confirmation: F6

Independent evidence paths:
    Path A: station -> evacuation record -> northern tunnel
    Path B: railway -> mountain settlement -> tunnel
    Path C: maintenance records -> blocked tunnel -> equipment
```

The player only ever sees the leaves (railway, station, evacuation
notice, mountains, blocked tunnel, maintenance shed, equipment) —
never this structure. The validator's job is to ask: "if I hide the
answer and expose only these pieces of evidence, does a legitimate
player have enough information to reconstruct it?"

### Validate backward from the escape, not forward from generation

The weak version of validation asks "did we generate enough clues"
(`evidence_count >= 8`). That's insufficient — you can have 40
beautifully written clues that collectively tell the player nothing
useful. The strong version traces backward:

```
ESCAPE
  |
Tunnel must be accessible
  |
Obstacle must be cleared
  |
Clearing equipment must exist
  |
Equipment location must be discoverable
  |
Player needs a reason to search that location
  |
Evidence must establish that relationship
  |
Evidence itself must be discoverable
```

If any link in that chain breaks, it's a generation failure — caught
before the expedition is ever handed to a player, not discovered by a
frustrated one.

### Two kinds of evidence support

- **Direct support** — one piece of evidence directly establishes a
  fact (the evacuation notice states the tunnel/railway relationship
  outright).
- **Corroborating support** — separate, independent pieces of evidence
  each point toward the same conclusion without any single one being
  required (railway tracks trend toward mountains; the mining
  settlement sits on the railway; a maintenance record mentions
  "northern access"; the tunnel itself is found blocked; the
  geography alone makes a tunnel a plausible route). The player
  shouldn't need every piece — that's what makes it feel like
  investigation rather than a scavenger hunt.

### Redundancy is a generation requirement, not a nice-to-have

The player must be able to miss clues. Formally: **no required
deduction may depend on exactly one discoverable evidence item unless
that evidence has multiple independently accessible discovery
routes.** A deduction fed by 3 evidence items (E1/E2/E3 all
independently supporting F1) tolerates losing any one of them; a
deduction fed by exactly one item (E1 → F1 → H1) is a single point of
failure the validator must catch. New validator outputs:
`critical_evidence`, `redundant_evidence`, `single_point_failures`.

### Test by ablation and by discovery order

Two empirical testing techniques for the Phase B½ harness (see
Automated Expedition Simulation & Balance below), not just static
graph analysis:

**Knowledge ablation** — after generation, don't run the investigation
bot once. Run it repeatedly with evidence deliberately removed (miss
E3; miss E5; miss two redundant clues; miss a critical one) and record
which removals still succeed vs. fail. That empirically produces the
clue *dependency graph* — which pieces are actually load-bearing —
rather than asserting redundancy exists from static analysis alone.

**Discovery-order independence** — since the whole design deliberately
allows arbitrary discovery order, validation must not assume the
"intended" order either. Generate the dependency graph first, then
simulate multiple legitimate discovery orders against it (railway →
station → record → tunnel; or tunnel → railway → farmhouse → station →
record; or mountains → tunnel → maintenance shed → railway → station)
and confirm the same underlying world stays solvable regardless of
which order a player happens to explore in. This is what actually
prevents "find A before B before C" from becoming a hidden quest
sequence disguised as an open world.

### False-escape validation

The opposite failure: the player forms a plausible-sounding but wrong
hypothesis (railway + mountains + tunnel → "this must be the way out")
while an unrelated dam elsewhere also has mountains + a service road.
If the player can physically reach the dam and the game lets them
"win" there, the design has produced an escape unsupported by any
mystery. The engine must distinguish three different claims:

```
CAN PHYSICALLY REACH  !=  IS THE GENERATED ESCAPE  !=  IS A VALID ESCAPE ATTEMPT
```

Final escape condition, roughly:
`physical_access AND escape_location AND obstacle_resolved AND
escape_mechanism_confirmed` (exact requirements vary by mechanism).
This prevents "I randomly walked into this tunnel and won" — unless
accidental discovery is a deliberate design choice for a specific
mechanism, which should be an explicit decision, not an accident of
implementation.

### The final action should test the hypothesis, not just check a flag

The player should not reach the tunnel tile and auto-win because the
generator internally knows `tunnel == escape`. The moment of escape
should read as the world confirming the player's own hypothesis, not
the game acknowledging a checklist:

```
PLAYER HYPOTHESIS  ("I think this tunnel gets me out")
        |
PLAYER TAKES ACTION
        |
GAME TESTS THE WORLD  (does the tunnel actually connect
        |               beyond the boundary?)
        v
     ESCAPE
```

The game should never say "congratulations, you collected the correct
clues" — it should say "you figured it out, and you were right." This
is a real implementation constraint on Phase D's win-condition change,
not just a validation nicety — the win check needs to *test* the
hypothesis at the moment of action, not merely confirm the player
stood on a marked tile.

## World validation

**Expanded 2026-08-27** from four categories to five — Inference
Validity is split out from Discovery Validity rather than buried
inside it, because they're different bugs: a *discovery* failure is
"the clue never spawned"; an *inference* failure is "the clues
spawned, but they don't logically connect" (this is what the Escape
Proof above exists to catch); an *action* failure is "the player
figured it out, but the game gave no legitimate way to act on the
conclusion." Conflating these into one category makes them hard to
tell apart when something breaks.

**1. Physical validity** — can the world physically exist and be
traversed?
- Playable region is connected.
- Required locations are reachable.
- Escape location is reachable once the obstacle is resolved.
- Required resources can exist (enough map space, etc.).

**2. Semantic validity** — do geography, civilization, locations,
infrastructure, loot, zombies, and history make sense together?
- Escape mechanism has all required stages present.
- Civilization makes sense for the geography.
- Locations make sense for the civilization.
- Loot makes sense for the locations.
- Zombie ecology makes sense for the locations/zones.

**3. Discovery validity** — can the player encounter enough evidence
to form the intended understanding?
- Sufficient clues exist.
- Clues are distributed across multiple locations (not clustered onto
  one tile).
- Clues don't reveal the answer immediately.
- First useful discovery occurs early enough to hook the player;
  critical discoveries aren't clustered together; the expedition
  doesn't require excessive backtracking (pacing concerns, folded in
  here rather than kept as a separate category).

**4. Inference validity** (new) — does the evidence actually support
the intended escape hypothesis, with redundancy, and without requiring
hidden generator knowledge? This is what the Escape Proof and backward
validation above exist to guarantee — no single mandatory clue makes
the expedition impossible if missed; the player can theoretically
infer the escape mechanism from what's actually placed, corroborated
by more than one independent path.

**5. Action validity** (new) — once the player forms the correct
hypothesis, can they discover/acquire what's needed and successfully
execute the escape? The final requirement isn't impossible to obtain;
the escape action actually tests the hypothesis (see "the final action
should test the hypothesis" above) rather than checking a flag; no
false-escape opportunity exists elsewhere on the map.

This deserves its own implementation phase — procedural mystery
generation can produce a world that's technically valid (everything is
reachable) but practically unsolvable (nothing points anywhere), or
solvable-in-principle but accidentally escapable somewhere the mystery
never intended.

## Automated expedition simulation & balance

Added 2026-08-27. Once the game becomes an investigation game, "did
the bot win?" stops being enough — the existing `tools/
balance_autoplay.py` harness needs to measure whether the generated
*mystery* is solvable and whether the player-information system (Phase
B) is actually doing its job, not just survival/combat balance. This
extends the existing harness rather than building a second one — the
telemetry, seeding, and campaign-simulation machinery already there is
the foundation.

**Two governing rules, verbatim:**

1. Every procedural system that materially affects playability must be
   testable through large-scale deterministic simulation without the
   TUI.
2. The simulation player may access only information available to a
   real player. Generator state, hidden mechanism structure, and
   undiscovered relationships are test-only observability for
   *measuring* the run afterward — never bot inputs during it.

Rule 2 is the important one to hold the line on. A generated world
could validate as physically/semantically/discovery-valid and still
only "work" because the test bot secretly knows the answer — this is
the exact same failure already caught and flagged as a pre-existing
bug in the *current* engine (`7dc71b94` in this project's todo list —
`_find_town_center()` scans `player.map` directly instead of respecting
fog-of-war, so the existing bot has known the Town Center's location
since turn one in every run). That bug is a preview of what happens at
much larger scale here if the investigation bot is ever given a
shortcut into generator state.

**Two bot policies needed, not one "perfect AI":**

- **Naive/random explorer** — tests baseline physical playability: is
  the world physically playable, can a non-strategic player stumble
  into important things, are resources catastrophically scarce, are
  important locations pathologically hidden. Closer to today's `BotIO`
  policy.
- **Investigation-aware bot** — uses the actual Phase B command
  interface (`look`/`inspect`/`search`/`journal`/`remember`/`map`) the
  way a real player would, reasons only over what it has actually
  discovered, and is the one that answers whether the mystery is
  *solvable*, not just reachable.

**New telemetry categories** (beyond the existing turns/combat/loot/
exploration metrics, which still matter): `escape_mechanism`,
`escape_location`, `mechanism_discovered`, `mechanism_discovery_turn`,
`first_meaningful_discovery_turn`; `evidence_generated`/`_discovered`/
`_relevant`/`_irrelevant`; `facts_generated`/`_discovered`/
`_established`; `hypotheses_generated`, `correct_hypotheses`,
`turn_correct_hypothesis_formed`; `required_deductions`/
`deductions_completed`; `required_locations`/`locations_discovered`;
`required_requirements`/`_discovered`/`_acquired`; `backtracking_distance`,
`wandering_distance`; `escape_attempts`, `escape_success`; and,
machine-testable rather than prose, `physical_validity`,
`semantic_validity`, `discovery_validity`, `pacing_validity` (see World
Validation above — these become boolean/scored fields per run, not
just design-doc categories).

**Additional telemetry from Escape Proof & causal-chain validation**
(added 2026-08-27, see that section above for the full reasoning):
`escape_proof_valid`; `required_deductions`, `deductions_supported`,
`deductions_missing`; `independent_evidence_paths`;
`critical_evidence_count`, `single_point_failures`;
`hypothesis_supported`, `hypothesis_confirmable`, `hypothesis_confirmed`;
`false_hypotheses`, `false_escape_attempts`; `required_evidence_discovered`,
`required_evidence_missed`; `escape_action_available`,
`escape_action_success`; and `inference_validity`, `action_validity`
(the two new World Validation categories, alongside the original four).

**Ablation and order-independence testing**, not just single-run
telemetry: run the investigation bot repeatedly per generated
expedition with evidence deliberately withheld (see "test by ablation
and by discovery order" in Escape Proof & causal-chain validation
above) to empirically derive the dependency graph, and repeatedly with
discovery order randomized to confirm order-independence. This
produces `single_point_failures`/`critical_evidence_count` from actual
bot runs, not just static graph analysis.

**Solvability is the headline metric**, distinct from win rate: given
only player-available information, can the escape mechanism actually
be inferred? Across a large batch, the report should look like a
funnel, not a single percentage — now with inference/action validity
broken out rather than folded into one "discovery-valid" bucket:

```
Generated                          10,000

Physical validity                   99.8%
Semantic validity                   99.4%
Discovery validity                  93.1%
Inference validity                  91.7%
Action validity                     98.9%

Correct hypothesis formed           86.4%
Correct hypothesis confirmed        81.2%
Escape successfully executed        79.8%

Average independent evidence paths    2.7
Single-point clue failures            1.1%
False escape opportunities            3.4%
```

**Per-expedition report against the information-budget invariants**
(see Physical & Information Budget's `MAX_*` constants) — a real
generation failure, not a player failure, when a run violates its own
budget:

```
EXPEDITION 8F31A2
Map:                         27 x 27
Meaningful locations:        19 / 30
Evidence:                    24 / 40
Established facts:            8 / 10
Active questions:             3 / 6
Required deductions:          4 / 5   <- e.g. if this were 7/5, that's
                                         a generation bug, not something
                                         the player should be expected
                                         to overcome
Escape mechanism:             Railway Tunnel
Independent evidence paths:   3 (minimum required: 2)
First useful discovery:       turn 11
Hypothesis formed:            turn 37
Requirement discovered:       turn 44
Escape reached:               turn 61
RESULT: ESCAPED
```

**Statistical balance experiments**, once mechanisms/bots exist —
sweep seed × mechanism type × map size × expedition tier × bot
strategy to ask things like: does one mechanism type fail more often
than another? Does more map size actually improve the mystery, or just
add noise? Is the first meaningful clue found early enough? How much
backtracking occurs? Are some mechanisms effectively unsolvable without
lucky exploration? This is "generate → simulate → measure → change →
simulate again," not balance-by-vibes — the same discipline the
existing harness already applies to combat, extended to the mystery
layer.

**Build-order implication:** the harness doesn't wait for the whole
mystery system to exist — see the revised build order below (new Phase
B½). As soon as Phase B's minimum information interface exists, an
investigation-aware bot can exercise it, so Phase C's generator can be
tested *while it's being built*, not only after.

## Failure modes

**Generation failures**
- Escape mechanism requires mountains but the generated region lacks
  sufficient mountain area.
- A required location cannot be placed.
- The settlement chain doesn't fit available geography.
- Clue locations collapse onto one another.
- The requirement item/knowledge cannot be generated.

**Discovery failures**
- Player can reach the escape route without understanding it.
- Player can discover every clue but still can't infer the route.
- A critical clue is inaccessible.
- Clues are too obvious (breaks the mystery) or too ambiguous (breaks
  solvability).

**Gameplay failures**
- Player exhausts resources before discovering useful information.
- Exploration degenerates into random wandering.
- Player can't tell whether something they found is meaningful.
- Player repeatedly encounters irrelevant evidence.
- One mechanism type becomes dramatically easier than another.

**Persistence failures**
- Discovered knowledge isn't carried correctly within a save.
- Expedition-local knowledge leaks into the next expedition.
- Campaign-level mechanism history isn't persisted (the shuffle bag
  forgets what's been used).
- Shuffle-bag state resets unexpectedly.

That last one points at a distinction worth making explicit — see
below.

## Three kinds of state

To keep the new knowledge system from becoming one giant ambiguous
profile dictionary:

**Expedition state** (exists only for the current map): discovered
locations, observed clues, understood facts, escape-mechanism
knowledge, map discoveries, obstacle state, current escape readiness.

**Campaign state** (persists across expeditions, via
`save_profile()`/`apply_profile()`): expeditions completed, mechanisms
already experienced (the shuffle-bag's memory), campaign chapter,
survivor progression, possibly accumulated narrative knowledge.

**Profile state** (persists independently): character identity, stats,
gear.

World knowledge and campaign knowledge are different things and should
not share one data structure just because both happen to be "things
the player knows."

## Player identity as an interpretation lens

The earlier reversal (randomizing survivor identity) raises a sharper
question than "should the player be randomly selected from 22
classes": **does player identity become part of world generation
itself?**

A `Hunter` might make hunting cabins more legible, recognize hunting
equipment immediately, read more into animal tracks, get richer
observations in rural locations. A `Police Officer` might recognize
police infrastructure, evacuation signage, road checkpoints, emergency
facilities, radio equipment on sight.

```
world evidence + player background -> interpretation
```

Not required for v1, but recorded here as a real second-order
consequence of randomizing survivor identity that the eventual design
should decide on deliberately rather than back into.

## What the player should NOT see

Given the deliberate move away from conventional RPG quest design, the
player should never receive: quest markers, "Escape route discovered!"
notifications, objective arrows, explicit clue chains, mechanism
names, stage numbers, "you need X to continue" (unless they've
actually learned that fact through play), or a quest log that turns
mystery into checklist.

Instead, the player receives: observations, environmental
descriptions, discovered records, object relationships, partial
information, journal entries, map annotations, contextual
descriptions.

## Physical & information budget

Added 2026-08-27. The single biggest gap the earlier drafts had: they
described *how* the world generates without bounding *how much* of it
a player can actually hold in their head through a text interface.
More world is not more discovery — past a point it's forensic
archaeology. The design target is a compact, information-dense world
a player can build a real mental model of within one expedition
(roughly the 45-60 minute range already implicit in this project's
existing pacing).

**Governing principle:** the world should be large enough to contain a
mystery, but small enough for the player to understand it. Map
dimensions are bounded by player comprehension, not renderer
capability — the TUI can technically scroll a 50×50 map (see the
earlier map-size answer in this conversation), but "can Textual
display it" is the wrong question. The right one: can a reasonably
attentive player explore this world, retain what they discover through
the game's knowledge system, form a plausible hypothesis, test it,
acquire what they need, and escape within the intended playtime?

**Physical budget — map size ceiling (investigate, not final):** replace
indefinite growth (`MAP_GROWTH_PER_LEVEL` currently scales the map
without bound up to `MAX_MAP_SIZE = 50`, constants.py) with a hard
gameplay ceiling in roughly the 25×25-33×33 range, not 50×50. Later
expeditions should grow *logically* more complex (more relationships,
richer history, harder-to-infer chains), not simply *physically*
larger. Concretely: don't just resize `MAX_MAP_SIZE` down without also
revisiting `MAP_GROWTH_PER_LEVEL`'s curve, since the two constants
jointly determine what expedition 5 vs. expedition 9 actually looks
like — this needs its own pass against the map-size and
zombie-difficulty telemetry the balance harness already tracks, not a
guess.

**Rule: map size must not determine information volume.** Added
2026-08-27 to resolve an apparent tension in the numbers below (they
describe different *layers*, not one flat count — see the hierarchy
immediately after). An expedition can have a physically larger
wilderness without that creating more things the player has to
remember. Concretely, resist the RPG instinct — the current
`BASE_MAP_SIZE=15/MAP_GROWTH_PER_LEVEL=2/MAX_MAP_SIZE=50` progression
is "you got stronger → the world got bigger"; the target is "you
progressed → the world became more conceptually difficult." Expedition
1 might be `15×15, ~10 locations, ~10 evidence pieces, a simple
relationship chain`. Expedition 9 should NOT be `50×50, 80 locations,
150 clues` — that isn't a harder mystery, it's more paperwork.

### Information hierarchy

Added 2026-08-27. The numbers in this section describe different
layers of one funnel, not competing totals — stated explicitly so a
future implementer doesn't read "20-40 evidence pieces" as "40 things
the player needs to understand" (they emphatically should not need to):

```
TILES
  |    (a 25x25 map has 625 of these; almost all pure atmosphere)
  v
LOCATIONS                    (the "meaningful" count below)
  |
  v
OBSERVATIONS / EVIDENCE      (the "evidence" count below)
  |
  v
FACTS                        (the "established facts" count below)
  |
  v
RELATIONSHIPS                (connections between facts)
  |
  v
HYPOTHESES                   (candidate escape-mechanism theories)
  |
  v
CONFIRMED KNOWLEDGE          (1 escape mechanism, actually acted on)
```

Each layer is meant to be smaller than the one above it — that's what
makes the funnel work. If a future pass finds `RELATIONSHIPS >
FACTS`, something's wrong with the generator, not the budget numbers.

**Physical budget — per-expedition (investigate target ranges, not
locked numbers):** roughly 1 primary escape mechanism and its escape
chain, 1-3 settlements, a handful of zones/districts, on the order of
8-15 to 15-30 *meaningful* locations (not tiles — see Tile ≠ location
below), leaving the rest of the map as atmospheric terrain that
doesn't require investigation.

**Information budget — per-expedition (investigate target ranges):**
roughly 8-15 to 20-40 discoverable evidence pieces, 5-10 established
facts, 2-4 unresolved questions, a small number (3-6) of major
obstacles/requirements, and — critically — a small number of *required*
deductions to actually identify the escape mechanism (3-5 major
discoveries feeding 2-4 meaningful connections feeding 1 hypothesis,
roughly). The escape chain should read as a puzzle, not a scavenger
hunt requiring the player to assemble 17 clues correctly.

**Tile ≠ location:** a 25×25 map is 625 tiles; only a fraction of them
(the 8-30 figure above) should ever be "meaningful" — worth a journal
entry. Walking across five plain forest tiles in a row shouldn't
produce five journal entries; `forest → old road → cabin` should
produce one, at the cabin. This is what keeps a small-in-tile-count
map from feeling small, and a large one from becoming unmanageable.

**Candidate generator invariants** (named constants, not just prose
ranges — added 2026-08-27): `MAX_MEANINGFUL_LOCATIONS`,
`MAX_EVIDENCE`, `MAX_ESTABLISHED_FACTS`, `MAX_ACTIVE_QUESTIONS`,
`MAX_REQUIRED_DEDUCTIONS`. World Validation (above) should be able to
report against these directly, e.g.:

```
World validation
  17 meaningful locations   (<= MAX_MEANINGFUL_LOCATIONS)
  23 evidence pieces        (<= MAX_EVIDENCE)
  7 established facts       (<= MAX_ESTABLISHED_FACTS)
  3 unresolved questions    (<= MAX_ACTIVE_QUESTIONS)
  4 major deductions        (<= MAX_REQUIRED_DEDUCTIONS)
  3 independent evidence paths to the escape hypothesis
  escape mechanism is inferable from placed evidence
```

That's validating the *playability of the mystery*, not merely the
correctness of the generated map — a materially stronger guarantee
than today's single `_ensure_reachable()` check.

**This budget is a generation-time validation target, not just a
narrative constraint** — see World Validation above (discovery
validity, pacing validity) and Failure Modes (gameplay failures like
"exploration becomes random wandering," "player repeatedly encounters
irrelevant evidence") — both sections already describe exactly the
failure mode an unbounded information budget produces. This section
gives those failure modes their actual numeric target to validate
against.

## Player cognition & information architecture

Added 2026-08-27. New architectural concern, moderate/high importance
— arguably the biggest missing piece from earlier drafts. World
generation substantially increases how much a player *could* discover;
rendering capacity was never the real constraint (see Physical &
Information Budget above) — what a player can meaningfully explore,
remember, and reason about through a command-line interface is.

**Core principle:** the player must never be required to remember
information the interface can reasonably preserve. If the game expects
a player to recall an obscure sentence from 40 screens ago without any
way to look it back up, that's not difficulty, it's bad information
architecture. The challenge should be recognizing the *relationship*
between things already discovered, not remembering that they exist at
all. This is why the knowledge interface below is a game mechanic, not
a UI nicety layered on afterward.

**Three separate layers**, not one:

```
PHYSICAL WORLD  (there's a tunnel at coordinates 21,14)
      |
WHAT THE PLAYER HAS SEEN  ("old railway tunnel, entrance blocked")
      |
WHAT THE PLAYER UNDERSTANDS  ("the railway once connected this
      |                        settlement to the mountains")
      v
Observed -> Known -> Suspected -> Confirmed   (see Knowledge State above)
```

**Must NOT become a conventional quest tracker.** No `QUEST: ESCAPE
THROUGH THE MOUNTAIN TUNNEL`, no `OBJECTIVE: FIND MINING EQUIPMENT
[2/1]`, no checklist. The interface should preserve *uncertainty* and
unanswered questions, not convert the mystery into a to-do list — a
theory display should read "the military may have used the dam
service road" with supporting/missing evidence listed, never "THE DAM
SERVICE ROAD IS YOUR ESCAPE ROUTE."

### Candidate commands — narrowed toward a minimal verb set

**Resolved 2026-08-27**, replacing the earlier "two proposals,
unresolved" framing: the risk with the expansive shape isn't that any
one command is wrong, it's that `journal`/`clues`/`facts`/`connections`/
`notes`/`map knowledge`/`nearby`/`where`/`why` collectively amount to
building a knowledge-management application the player has to learn —
easily more complicated than the mystery it's meant to support. The
recommended default is now a small set of core verbs, with richer
views living *underneath* them rather than each becoming its own
top-level command:

```
l / look        - describe the current location and surroundings
i / inspect     - ask the game what you currently understand about
                  a specific thing (see below - this absorbs `why`)
s / search      - deliberately investigate the current location
j / journal     - structured record: locations / evidence / facts /
                  questions / theories, as sub-views
r / remember    - a short synthesized narrative of current
                  understanding, NOT a journal dump (see example below)
m / map         - terrain / locations / knowledge, as sub-views
```

`why <thing>` does not become its own command — it's folded into
`inspect <thing>`, which reports what's Observed/Known/Suspected/
still-Unknown about that subject without ever supplying the answer:

```
> inspect railway

RAILWAY

Observed:
  An abandoned railway runs north toward the mountains.

Known:
  It once connected Milltown with the northern settlement.

Suspected:
  The railway may provide access through the mountains.

Unknown:
  Whether the northern tunnel remains passable.
```

That gives `inspect` a clear identity: it isn't just examining an
object, it's asking the game what you currently understand about that
subject — very on-theme for an investigation game, and one command
instead of two.

`remember` should read as prose, not a table — a short paragraph or
two synthesizing current understanding plus an "unresolved" list, e.g.:

```
WHAT YOU REMEMBER

You have discovered an abandoned railway running north toward
the mountains. A damaged evacuation notice suggests workers used
the northern tunnel during the collapse. You suspect the railway
may provide a route through the mountains.

UNRESOLVED
  - Why was the railway abandoned?
  - What blocked the northern tunnel?
  - Is there another entrance?
```

**Player loop this is meant to support** — keep this as the design
target when building Phase B, not the command list itself:

```
LOOK -> notice something -> INSPECT / SEARCH -> information is
preserved automatically -> player starts recognizing relationships
-> REMEMBER / JOURNAL when the player wants to check their own
understanding -> player acts on that understanding
```

**When implementing, distinguish** commands the *engine* needs (the
mechanism by which a fact transitions Observed → Known) from commands
that are pure UX (`journal`/`remember` are presentation over state
that could otherwise print automatically). `inspect`/`search` are
plausibly essential; `journal`/`remember` are plausibly
presentation-only layered on the same underlying state.

**Do not implement these commands yet.** The actual next Phase B task
is narrower than "build the six commands" — see "The minimum
information interface" below.

### The minimum information interface

Added 2026-08-27. Before `journal`, `inspect`, `remember`, etc. become
individual implementation todos, answer this question directly:

**What is the minimum information interface that lets a player
successfully investigate a procedurally generated world without
turning Apocrysis into a quest tracker or a database UI?**

This is a real design/investigation task, not a rhetorical framing —
it should produce a concrete answer (which of the six verbs above are
actually load-bearing vs. nice-to-have, what the smallest useful
`journal`/`remember` output actually looks like against *real*
generated content, not the hand-written examples in this document)
before any of the four Phase B command todos get implemented. Sequence
it first among the Phase B todos in the project's todo list.

### The map as a knowledge surface, not just a terrain viewer

The existing `m`/`map` command should eventually support layered views
(`map terrain`, `map locations`, `map knowledge`) and progressive
annotation — a mountain range renders as plain `^^^` until discovered,
`^^^ [OLD RAILWAY]` once observed, `^^^ [RAILWAY → MOUNTAIN TUNNEL]`
once understood. The map becomes a representation of knowledge, not
only geography, once this lands — but it's an extension of the
existing fog-of-war/`town_known` mechanism, not a new one.

### Deprecate the existing goal/task system

`go`/`goals`/`complete`/`ts`/`ct` (see `commands.md`) are close to
philosophically opposed to "you are trying to understand the world
well enough to discover how to escape it." A task saying "kill 5
zombies → reward" isn't inherently bad, but "reach Town Center →
reward" actively fights the new design once the win condition changes
(Phase D). Investigate replacing the whole system with the
knowledge-interaction commands above once Phase D lands — implicit
objectives should emerge from accumulated knowledge, not be assigned
by a goal list. Don't keep the old system just because it's already
implemented; the assessment's job is to say when something should be
retired, not only when something should be added.

## Worked example: Railway Escape

Demonstrates most of the architecture above in one place.

**Generator knows** (never shown to the player): region = mountain;
civilization = industrial mining; escape = railway tunnel. Required:
mountains, railway, rail station, industrial settlement, maintenance
location, blocked tunnel, equipment, historical evacuation, clues.

**Player experiences, in the order they happen to explore:**

- *Early expedition:* "You find an abandoned railway cutting through
  the trees." (Observed — doesn't know it's important yet.)
- *Later:* a weathered sign reads "…STATION — 3 MILES." (Recognized —
  now knows there's infrastructure.)
- *Settlement:* several buildings appear railway-associated.
  (Connected — a relationship starts forming.)
- *Station:* an old evacuation notice mentions workers moved through
  the northern tunnel. (History enters the picture.)
- *Mountain:* the tunnel is found, but the entrance is blocked.
  (Understood — now has a hypothesis.)
- *Maintenance shed:* heavy tools suitable for clearing the
  obstruction. (Actionable — the requirement is apparent.)
- *Tunnel:* the obstruction is cleared.
- *Escape:* the tunnel leads out of the playable region.

## Old engine → new engine

| Current engine | Proposed engine |
|---|---|
| Town Center = implicit goal | Escape route = emergent goal |
| Terrain generated independently | Terrain supports a region concept |
| Settlements placed independently | Settlements emerge from geography |
| Buildings mostly generic | Buildings derive from settlement/district |
| Loot generic | Loot derives from location |
| Zombies expedition-scaled | Zombies derive from ecology/location |
| Map reveals geography | Map represents knowledge |
| Loot gives resources | Evidence gives knowledge |
| Goal tells player what to do | World gives player reasons to infer what to do |
| Win condition is known | Win condition is discovered |
| Generator creates objects | Generator creates relationships |
| Player follows objective | Player constructs objective |

## Open questions

These should stay open questions during design, not turn into
implementation decisions prematurely.

**Knowledge:** Are facts automatically recorded, or must the player
explicitly `inspect`? Can the player misunderstand evidence? Can clues
become obsolete? Can clues be redundant (multiple paths to the same
fact)? Can an expedition be completed without understanding every clue?

**Escape:** Does every mechanism require an obstacle? Does every
mechanism require a physical item, or can the requirement be knowledge
alone? Can the mechanism be discovered before its associated
infrastructure? Can the player accidentally escape without
understanding the complete chain?

**Generation:** How many settlements does a mechanism require? How
large must the playable region be? How many independent clues should
exist, and what's the minimum needed to establish an inference? How
much randomness is allowed once a dependency has been established?

**Interface:** narrowed 2026-08-27 toward a minimal 6-verb set (see
"Candidate commands" under Player Cognition & Information
Architecture) — no longer a fully open two-way split, but "what's the
minimum interface that actually works" (see "The minimum information
interface" in that same section) is still a real open question to
answer with actual generated content before implementing.

**Campaign:** Does the player eventually recognize recurring mechanism
families? Does the campaign teach the player how Apocrysis works over
time? Does mechanism repetition become possible once the shuffle bag
is exhausted? Does history persist between expeditions, or reset each
map?

## Follow-up, not part of this assessment

The README currently mixes player-facing description with
implementation history (`award_xp()`, exact XP values, zombie
subclass names). Once this direction lands, the README should become
primarily player-facing — what Apocrysis is, the core loop, how to
play — with implementation detail moved to a separate
`docs/ARCHITECTURE.md`. Not done as part of this assessment since it's
a real file change with its own review, not a design decision; filed
as its own todo for later.
