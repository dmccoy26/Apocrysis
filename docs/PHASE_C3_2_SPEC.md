# Phase C.3.2 — navigational affordances (design, authored before implementation)

Builds on: `PHASE_C3_SPEC.md` (the v2 feel-test verdict + the three
invariants) and `NAV_SIGNAL_INVENTORY.md` (26 signals classified
`observable → interpretable → actionable`).

## The problem is not v2-specific (2026-08-29, expedition 2)

A second feel-test run — **v1**, `boat_crossing`, 18×18 — died at turn
99 with **zero mystery evidence found**. `facts_known` was five ambient
`_PHASE_B_CLUES` and nothing else; `hypothesis` never left `unknown`.
The player left spawn on turn 1, looped the entire map perimeter (64 of
324 tiles, all edge), never touched a single mystery site, and starved.

This matters for C.3.2's framing:

- **v1 has the identical failure mode.** The mystery sites cluster near
  spawn by design (`escape.py`: "the gap is deliberately the far
  corner"); leave spawn and circle, and you can miss the entire
  mystery. Expedition 1 only passed because that map's RNG put the
  settlement on the wander line. v2 didn't create this — it removed the
  rectangle's forgiveness (self-correcting bounds).
- **The turn-1 directional lead already exists and is not enough.** The
  ESCAPE panel showed "► head for the way out (north)" from turn 1
  (`_objective_steps` → `heading('route')`, unconditional straight-line
  to the route site). At turn 94 an ambient clue fired: "Boot prints
  all lead the same way — out the back, north." **Two independent
  "north" signals, never connected, never reinforced, never on the
  map** — and the player, circling the south/east edge, acted on
  neither.

So C.3.2's job is not to *invent* an early lead — it's to make the one
that exists **land**: validate it (Invariant 4) and **reinforce** it
(`look`, ambient clues, a soft map hint). And the 2×2's top-left cell
("v1, old navigation") is **not a passing baseline** — C.3.2a is a real
fix on v1, not a warm-up for v2.

## What this has become (2026-08-29, BlueNoodle's two runs)

The geography experiment has turned into a **player-information
experiment.** The finding is stronger than "make prettier irregular
maps":

> The map doesn't need to tell the player *more*. The game needs to make
> the information it already has **persist, reinforce itself, and stay
> actionable.**

BlueNoodle (the "moves and fights, never interrogates" archetype) won
two v1 expeditions and **never typed `look` once**. Behavioural
evidence: this player *will* act on information already in front of him
— he follows the ESCAPE-panel heading, he uses the survey map the
moment it drops — but he will not stop to interrogate the world.

### Channel ranking (revised)

| # | channel | why |
|---|---|---|
| 1 | **persistent passive objective signal** — the ESCAPE-panel heading, kept honest (piece 0) and always present | highest value; it's what BlueNoodle actually navigates by, and it costs the player nothing |
| 2 | **passive environmental reinforcement** — landmark bearings (piece 1), ambient-clue directional hints (piece 4) | arrives *while playing*, no command; closest to the existing loop |
| 3 | **map affordances** — the survey map | useful, but it must stay a **discovery**, never a crutch. Do not buff it (guardrail). |
| 4 | **`look`** (piece 2) | an excellent *recovery* tool for a player who deliberately seeks orientation. **Proven to work technically; not proven players will use it.** Do NOT let the core loop depend on it. |

### What is NOT concluded

**Not** "`look` doesn't work because BlueNoodle didn't use it" — that's
a selection effect; he was never lost. The controlled test still
matters: *deliberately* get a player into a state where the existing
heading isn't salient, then see whether `look` rescues them. But it's
now **secondary validation**, not the primary product question.

### The piece 4 trap

Do **not** turn every ambient clue into a compass arrow. Preserve the
texture-vs-navigation distinction. The test for a clue-hint is: *does
it reinforce an already-established lead?* — not *can we extract a
direction from this prose?*

## The reframe

C.3.2 is **not primarily a map-generation feature.** The inventory
showed the generator already produces workable geography; what's
missing is the information layer that lets a player navigate it. So:

> **C.3.2 gives the existing geography a chance to work by making the
> information the player already possesses *actionable*, and by making
> the game's navigational claims *true* against the generated
> topology.**

Two halves, and the split matters:

- **Surfacing** — turn existing signals (landmarks, `look`, ambient
  clues) into directional hints. Mostly engine/prose, no generation
  change.
- **Validation** — every navigational claim the game makes is checked
  against `MapGraph`. This is where the generator keeps a real
  responsibility.

## The question C.3.2 answers

> Does irregular geography (the parked v2 mask) become playable once
> the information layer supports navigation — or does irregularity
> itself introduce unacceptable friction regardless?

Answered by a 2×2, not a single comparison:

| | old navigation | + C.3.2 affordances |
|---|---|---|
| **v1 geometry** | baseline (shipped) | **C.3.2a — the first test** |
| **v2 geometry** | rejected (`PHASE_C3_SPEC.md`) | **C.3.2b — the real experiment** |

- v2-with-affordances feels good → *irregular geography works, but only
  when the information layer supports it.*
- v2-with-affordances still feels bad → *irregular geography itself is
  the friction.*

Both are valuable results. The comparison that matters is
**v1-affordances vs v2-affordances**, not v2 against the original v1.

## The invariants (locked — spec FROZEN 2026-08-29)

Invariants 1–3 are from `PHASE_C3_SPEC.md`, restated. **Invariant 4**
(topology authority) and **Invariant 5** (persistence) are new and are
the hard contracts for C.3.2.

> **Invariant 1 — Lead before obstacle.** Every expedition exposes at
> least one meaningful navigational lead within the early exploration
> window, and a blocking / obstructive site must not become the
> player's first meaningful information without an existing lead that
> gives it context.
>
> **Invariant 2 — Leads must survive geography.** If a player-facing
> lead establishes a destination and a directional heading, the
> generated geography must provide a traversable route consistent with
> that heading.
>
> **Invariant 3 — Navigation must stay actionable.** Between receiving
> a lead and reaching its destination, the geography may require
> route-finding, but must not repeatedly invalidate the lead's implied
> direction through arbitrary boundary collisions.
>
> **Invariant 4 — Navigation signals must correspond to actual
> topology.** `MapGraph` is the single authority for whether a
> navigational claim is true. Prose and generation do not
> independently agree — the claim is validated against the realised
> graph.
>
> **Invariant 5 — Navigation Persistence.** A meaningful navigational
> lead must remain *recoverable* after the player ignores it. The game
> must not require "I obeyed the turn-1 instruction perfectly." A
> player who wanders, forgets, or takes a wrong turn must be able to
> reconnect with the objective through a channel they'll actually
> hit — `look`, an ambient clue, a landmark, the map.

### The persistence loop (Invariant 5)

Expedition 2 proved the game *has* a turn-1 lead ("head north") and no
way to get back to it. The missing loop:

```
Turn 1   ESCAPE panel: head north
              │
         player wanders / investigates something else / takes a wrong turn
              │
         look          → "The way out lies to the north."
              │
         ambient clue  → "Boot prints lead north."   (reinforces, same axis)
              │
         landmark / map → the northward route becomes legible
              │
         player reconnects with the objective
```

None of the reinforcement channels invent new information — they
re-surface the lead the player already earned, in a place they're
looking.

### Invariant 4, concretely

```
WORLD CONTENT / MECHANISM
      │  "the way out is toward the north-east edge"
      ▼
NAVIGATION SIGNAL  (evidence text, landmark bearing, look output, clue hint)
      │  validate before it reaches the player
      ▼
MapGraph
      ├── destination reachable from where the claim is made?   reachable(a, b)
      ├── is the stated heading the honest one?                 bearing(here → node) vs claimed
      └── does a route actually run that way?                   shortest_path(here, node)
                                                                first N tiles trend toward the heading
```

If a check fails the signal is **corrected, not suppressed**: re-word
the heading to the honest one, or (generation only) regenerate. A claim
is never shipped that the graph says is false.

#### `heading_is_honest` is a *monotonic-progress* test, not a reachability test

The v2 failure was not "the destination is unreachable" — it was
reachable. The failure was that a player following the displayed
heading hit walls on their first several decisions:

```
claimed: north-east
  NE → wall
  N  → wall
  NE → wall
  E  → wall        ← route actually detours west around a ridge first
```

So the test is: **would a player following the claimed heading be sent
*backward* along the real route?** `MapGraph` supplies the real route
(`shortest_path`); the helper checks whether the route's early net
direction *reverses* an axis the claim asserts.

**Two shared helpers (as built — the spec's earlier sketch was
refined during implementation; see "As built" below):**

- `bearing(from_xy, to_xy, deadzone=1) -> "north-east" | "" ` — pure
  geometry, ±1 deadzone, y-down = south. Consolidates the two ad-hoc
  impls (`_mystery_heading`, tui `_compass`) *as their call sites are
  migrated* — piece 0 migrates tui's.
- `heading_is_honest(path, claimed, window=8) -> bool` — `path` is a
  `shortest_path` result. **Contradiction test, not a match test:**
  `True` unless the route's first-`window`-step net direction contains
  the *opposite* of an axis `claimed` asserts. Empty `claimed` / short
  path / uncommitted early route → `True`.

  *Why a contradiction test and not "claimed axes ⊆ route axes":* a
  shortest path's exact shape is a BFS tie-break artifact. On open
  ground the path from A to B is often L-shaped ("all north, then all
  east"), so a subset test would "correct" a perfectly fine "north-east"
  claim to "north" ~50% of the time. Only a genuine *reversal* (the
  route has to run west to get around a ridge before it can head NE)
  means the player following the claim hits walls. Measured: the
  contradiction rule fires on **0 % of v1 and ~0.1 % of v2** route-site
  headings from sampled positions — see "As built".

Callers substitute the honest heading with
`bearing(path[0], path[min(window, len(path)-1)])`.

## `look` — the reframe

Current: `"Open forest. Nothing here that matters."` — anti-navigation.

C.3.2: `look` answers one question — *given what this survivor
currently knows, is there something worth orienting toward from here?*

```
You look across the trees.
Somewhere to the north-east, the route you learned about continues.
```

or, when nothing is known:

```
You look across the trees.
Nothing here gives you a direction to follow.
```

It is **not** a GPS. It reports only leads the player has *already
earned* (a known mystery site, a spotted-and-remembered landmark, an
ambient clue's soft hint), with a graph-honest bearing (Invariant 4).
It never invents a clue on a tile that has none.

`look` is the primary **persistence** channel (Invariant 5) — the one
place a wandering player can always ask "which way was I meant to go?"
and get the answer back. It is likely the single most important
player-facing change in C.3.2a. Landmark bearings (piece 1) and the
ambient-clue hints (piece 4) are *reinforcement* around it, not
navigation mechanisms in their own right.

## A conceptual distinction to keep (do NOT build the abstraction yet)

C.3.2 is, underneath, the discovery that Apocrysis needs a first-class
**lead / surfacing layer** distinct from its fact layer:

```
FACT         "I found a locked gate."          (Phase A: WorldFact / F_*)
LEAD         "The route is north."             (C.3.2: currently only the ESCAPE panel)
CONNECTION   "The locked gate is on the route." (Phase A: deductions)
OBJECTIVE    "Reach and open that gate."        (the ESCAPE checklist)
```

Phase A handles facts and connections well. C.3.2 is exposing that
**leads** are under-served: one channel, no persistence, no validation.

**Do not create a `NavigationLead` object in C.3.2.** The approach —
shared helpers + existing signals + `MapGraph` validation — is
deliberately un-abstracted. Let the experiment prove whether a formal
lead type is actually necessary before building one.

## Scope

### C.3.2a — v1 navigation affordances (ships first)

Ordered smallest-first. Each piece stands alone and is testable.
**The through-line: the ESCAPE panel already carries a turn-1 route
heading (`_objective_steps` → `heading('route')`). C.3.2a validates it
and reinforces it in the places the player is actually looking — it
does not add a competing new lead.**

| # | change | where | MapGraph contract | test |
|---|---|---|---|---|
| 0 | **Validate the ESCAPE-panel route heading.** `heading('route')` is an unconditional straight-line bearing to the route site — on v2's expedition it pointed "north-east" into a wall. Run it through `heading_is_honest`; show the honest heading, or drop the parenthetical if there is no honest one. | `tui._objective_steps` `heading()` / `_compass` → the shared helper | `heading_is_honest(graph, player, route_site, claimed)` | unit: straight-line NE but path goes N → panel says "(north)"; no coherent heading → no parenthetical |
| 1 | **Landmark → bearing** *(reinforcement, not the primary mechanism)*. `_spot_landmarks` says *which way* the rooftops/building are; the sighting is remembered so `look` can re-report it. | `world_mixin._spot_landmarks`, a `_landmarks_seen_dir` store | bearing computed from real tile positions | unit: a sighting NE of the player produces "north-east"; structural: on 200 seeds every settlement sighting has a non-empty bearing or is adjacent |
| 2 | **`look` → recoverable orientation** *(the key player-facing change; the primary Invariant-5 channel)*. Reports the nearest earned lead (incl. the ESCAPE-panel route heading) with a graph-honest heading, or says plainly there's none. The panel heading and `look` must agree. | `knowledge_mixin.knowledge_look` | `heading_is_honest` before printing a direction | unit: known route NE + clear path → "north-east"; known route NE + wall NE + path actually goes N → "north"; nothing known → the null line |
| 3 | **Validate the spawn→gap bearing in evidence.** The baked `E_obstacle_a` / `E_route_reveal` bearing ("toward the north-east edge") is checked against `MapGraph` at generation; if the honest early-path heading differs, the text uses the honest one. | `escape.build_mystery` (the `_bearing` block), `world_mixin.generate_map` after the graph is built | `shortest_path(spawn, exit)` early tiles define the honest heading | structural: on 300 v1 + 300 v2 seeds, the bearing word in `E_obstacle_a` matches the first-5-tiles heading of the spawn→exit path |
| 4 | **Ambient clues → soft hint** *(only if 0–3 don't clear the bar)*. `_PHASE_B_CLUES` entries with a direction ("boot prints lead north") drop a low-confidence directional arc `look`/the map can show — imprecise, not a `!`. In expedition 2 "boot prints lead north" *matched* the panel heading and was never connected; this piece connects them. | `world_mixin._maybe_surface_clue`, `_render_map_lines` | the arc points along a real reachable sector, else the clue surfaces without a hint | unit: a "north" clue with open north → hint shown; blocked → text only |

**C.3.2a-5 — early-window signal recoverability (separate generator
concern, decided by the v1 feel-test).** The requirement, phrased so it
does *not* prescribe where sites go:

> The player must be able to **encounter or recover** an actionable
> navigational signal during the early exploration window **without
> already having solved the mystery**.

Expedition 2 (v1) failed this: zero mystery evidence in 99 turns
because every site clusters near spawn and the player circled the
perimeter. If pieces 0–4 land and the early window still starves the
player on v1, the fix is one of — a minimal early-reachable-lead
guarantee (validated by Invariants 4/5), *or* stop the generator
clustering every site in one blob near spawn. Kept a separate concern
so the surfacing experiment (0–4) is tested first, uncontaminated.
Never by pinning a
fixed settlement distance or a story location near spawn.

### C.3.2b — replay the experiment on v2

No new code beyond flipping `mapgen="v2"`. Re-run the feel-test
protocol from `PHASE_C3_SPEC.md` (≥5 expeditions, varied mechanisms —
see the variety fix below), record the same phase table, fill in the
2×2.

## Blocking C.3.2b — mechanism variety

`DIS_FEW_REMAINS` → only `mountain_pass`, so every fresh campaign's
expedition 1 is identical (`PHASE_C3_SPEC.md` § contamination). Before
C.3.2b, do **one** of:

- play a single campaign forward (mechanisms vary run to run — cheapest,
  no code), or
- add a debug `--force-mechanism` to `apocrysis.py` (the balance
  harness already has the plumbing), or
- give `DIS_FEW_REMAINS` a second, non-spatial `DiscoveryTemplate`.

Decide when C.3.2b starts; it is not part of C.3.2a.

## Guardrails

- **Do not buff the survey map.** The strongest existing signal
  (`map_revealed`) stays a loot drop. C.3.2's job is to make *earned*
  information actionable, not to add a second navigation system.
- **Do not pin geometry.** No guaranteed settlement distance, no story
  location near spawn. Affordance, not layout.
- **Do not call the generator "solved."** The inventory shows it isn't
  the *primary* problem — it does not show it has no responsibility.
  Invariant 4 is a permanent contract: *if the game makes a
  navigational claim, the generated world must make that claim true.*
- **Balance stays FROZEN** (combat / hunger-thirst / encounter / loot /
  map growth). C.3.2 touches prose, one generator text substitution,
  and a bearing helper — nothing on the balance line.
- **v1 generation stays byte-identical** where C.3.2a doesn't
  deliberately change it. Piece 3 changes one evidence string's *wording*
  under a condition; the golden-fixture test updates to assert the new
  rule, not the old byte-match, for that one field.
- **No assist mode. Do not un-mixin the `Apocrysis` class.**
- Route only self-contained ≤~60-line new files to Atlas; hand-write
  the rest (`ATLAS_CAPABILITY_LOG.md`).

## What C.3.2 is NOT

- not a generation rewrite;
- not the inverted pipeline (that idea is superseded — `PHASE_C3_SPEC.md`);
- not a minimap / waypoint / quest-arrow system;
- not a change to what the player can *see* (fog of war, visibility
  radius) — only to what the game *tells* them about what they've
  learned;
- not a re-open of the C.3 architecture (`v5-phase-c-foundation` stays
  frozen).

## Build order

> **THIS STEP (spec frozen 2026-08-29):** build **only** step 1 —
> `bearing()` + `heading_is_honest()` + their unit tests, in
> `src/nav.py`. **No generator changes. No new navigation abstraction.
> No map hints. No call-site migration yet.** The helpers are inert
> until a later piece wires them in. This keeps the next experiment
> controlled: first make the navigation claim *truthful*, then (piece
> 0–2) make it *recoverable*, then see if that's enough before touching
> generation.

1. ~~`bearing()` + `heading_is_honest()` in `src/nav.py` + tests.~~ ✅ `2c1cc4d`
2. ~~C.3.2a piece 0 (graph-honest ESCAPE-panel route heading).~~ ✅ `3fe0485`
3. ~~C.3.2a piece 2 (`look` recovers the route direction).~~ ✅ `5cd5da6` — **DONE, validated in real play**
4. ~~Scale investigation~~ ✅ `SCALE_REPORT.md` (`tools/scale_report.py`)
   — the solve circuit outgrows the survival budget by mid-campaign.
5. **→ Author the C.3.2a-5 spec** against `SCALE_REPORT.md`: keep an
   appropriate density of actionable destinations as the map grows
   (not by shrinking maps, not by clustering on spawn). Owner review.
6. Implement C.3.2a-5. Re-run `scale_report.py`. Owner feel-test.
7. C.3.2a piece 1 (landmark bearings) — PARKED, only if the player
   still can't *recover direction* after C.3.2a-5.
8. C.3.2a piece 4 (clue reinforcement) — PARKED, after piece 1.
9. C.3.2a piece 3 (evidence spawn→gap bearing validation) +
   golden-fixture update. Tag `v5-phase-c3-2a`.
10. Variety fix (one of the three options).
11. C.3.2b — owner feel-test on v2. Fill the 2×2. Verdict.

## As built — steps 1–3 (2026-08-29)

### Sequence (owner, after two of BlueNoodle's runs)

Two re-weights: piece 0's finding (claim is truthful, player can't act
on it), then BlueNoodle (the target player won't type `look` — passive
channels rank above it). Current order:

```
piece 0 (guardrail) ✅ → piece 2 (look, one recovery mechanism) ✅
  → step A: controlled look test → step B: play v1 normally
  → piece 1 (passive landmark bearings) IF normal play still fails
  → piece 4 (clue reinforcement, established-lead only) if still needed
  → C.3.2a-5 (site distribution) last → revisit v2
```

**Executable success criterion (Invariant 5):** *a player who ignores a
navigation lead must be able to recover it without discovering anything
new.*

### Step 1 — `src/nav.py`

`bearing`, `heading_is_honest`, and (added for piece 2) `honest_bearing`
— commits `2c1cc4d` / `2d30950`, 16 tests. `heading_is_honest` refined
during piece 0 from the spec's "shares an axis" to a pure
**contradiction test** (`window=8`) — subset tests punish BFS L-shapes
(reason in the helper section above). `honest_bearing(here, dest, grid,
n)` is the shared graph-honest-heading core: straight-line claim vs the
real `shortest_path`, substitute on a genuine reversal. `nav.py` now
imports `src.worldgen.reachable` (pure, not engine).

### Step 2 — piece 0, commits `3fe0485` / `2d30950`
- `tui._route_heading(here, dest, grid, n)` — new module-level, pure,
  unit-tested (`test_route_heading.py`, 5 tests). `_objective_steps`'s
  `heading()` delegates to it; the old nested `_compass` is gone.
- Straight-line `bearing` is the claim; a terrain-only `shortest_path`
  is the authority. Honest or unreachable → the straight-line claim,
  unchanged (byte-identical panel output for ~all cases). Contradiction
  → the route's honest early heading (`bearing(path[0], path[8])`), or
  nothing if it commits to no direction.
- Applies to **every** `heading()` call (route / require / power), not
  just route — same claim shape, same fix. Not special-cased.
- **Atlas: attempted, REJECTED-UNPARSEABLE** (3 attempts, no parseable
  patch) — `tui.py` at ~980 lines is past Atlas's whole-file load
  ceiling even for a ~15-line edit. Hand-written. `atlas-self` todo
  `9ecc7f2b`. Log entry #49.

### Measured finding (the "few v1/v2 runs" gate before piece 3)

Across ~1840 sampled (position, route-site) pairs per generator: the
correction fires on **0 % of v1** and **~0.1 % of v2** route headings.

**Interpretation:** the ESCAPE-panel route heading was almost never an
actual *lie*. The v2 feel-test friction ("NE → wall, N → wall …") was
the irregular boundary making *greedy movement* annoying while the
heading stayed directionally sound — an Invariant-3 (texture) problem,
not an Invariant-2/4 (falsehood) problem, and on v1 not a problem at
all. Piece 0 is therefore a correct, cheap **guard** that closes the
Invariant-4 hole for the rare pathological case, but it is **not** the
fix for what the two expeditions showed. The weight is on **piece 2
(`look` / persistence)** and **C.3.2a-5 (site clustering / early-lead
recoverability)**.

### Step 3 — piece 2 (`look` recovers the route direction), commit `5cd5da6`

`knowledge_look` ends with `_look_recall_bearing()`:

> `You get your bearings. The way out lies to the north-west.`

- non-informational: from turn 1 (matches the panel's unconditional
  route step); informational: silent until `F_ROUTE`; names the
  mechanism once `F_ROUTE` is known; silent on/adjacent to the site.
- The recall bearing is `nav.honest_bearing` from the player's
  *current* position — so a player who wandered to the far corner
  types `look` and gets a fresh, correct heading, no discovery needed.
  Verified live: spawn panel "(east)" → wander to the SE corner →
  `look` → "(north-west)".
- **Atlas: SHIPPED+FIXUP** (`atlas request --file
  src/mixins/knowledge_mixin.py`, workflow `6ec6269a`, VERIFIED
  pytest ×3). First real Apocrysis win since Phase A — small file
  (191 ln) + method body supplied verbatim + one call site. Fixup:
  method placement. Log entry #50.
- `test_look_recall.py` — Invariant 5 executable: wander to the
  farthest reachable tile, assert `look` gives a direction matching
  `honest_bearing` with `facts_known` unchanged. 277 + 100 green.
- **BlueNoodle v1 runs 1–3 (23, 48, 102 turns) — clean wins, no
  regression, `look` typed zero times.** He navigated by the
  ESCAPE-panel heading + the survey map. This is why `look` sits at #4.
- **BlueNoodle run 4 — `look` VALIDATED, then a map-scale death.**
  Airfield-plane, 24×24 (the map grows with expedition depth). The son
  — the "never interrogates" archetype — **typed `look` twice
  unprompted** (turns 48, 50): *"You get your bearings. The way out
  lies to the east"*, and moved on it. So the "players won't use it"
  worry is at least partly wrong.
  **He died anyway** at turn 220 / day 12: settlement not found until
  ~turn 130, food gone at turn 46, ~170 turns of starvation grind, then
  an Elite Armored Zombie (25 dmg/hit) at HP 40. **Not a heading
  failure — he knew "east".** The killer is **map scale**: the
  wander-to-first-settlement cost scales with map *area*, and an
  expedition-4 24×24 board breaks even an over-equipped survivor. This
  is the strongest signal yet for **C.3.2a-5** (early-lead
  reachability), and it raises a question outside C.3.2's frozen
  balance: whether `map_size` should keep growing unbounded with depth.

## The gate — revised after BlueNoodle (2026-08-29)

### Where it stands (2026-08-29, after BlueNoodle runs 1–4 + the scale report)

- **Piece 0** — shipped, guardrail, near-no-op (measured).
- **Piece 2 (`look`) — DONE.** Validated in real play: BlueNoodle (the
  "never interrogates" archetype) used it twice unprompted on map 4
  and acted on it. **No more `look` machinery.**
- **Pieces 1 and 4 — PAUSED.** Not abandoned. They answer "I know
  where to go, how do I recover the direction?" — real, but no longer
  the priority.
- **`SCALE_REPORT.md` (200 seeds/depth, not one playthrough) is the
  finding:** the *nearest* meaningful site stays ~5 tiles from spawn at
  every depth, but the *solve circuit* (spawn → touch every site)
  balloons p50 20 → 60 tiles, and the fraction of maps whose circuit
  alone exceeds a fresh survivor's whole movement budget goes
  0 % → 24 % (depth 4) → 74 % (depth 12). Site density collapses 5.5×.
  **By mid-campaign most maps can't be *completed* by a survivor
  without inherited supplies, independent of navigation.** The
  roguelite loop masked this until BlueNoodle died at depth 3.

### The priority: C.3.2a-5, reframed

> **How does the generator keep an appropriate density of actionable
> destinations as the geography expands** — so the solve circuit stays
> within a fresh survivor's movement budget at every campaign depth?

Constraints for that spec:
- `map growth` is **FROZEN** → the lever is *maintain density*, not
  *shrink maps*.
- **Do not cluster every site near spawn** — that recreates the
  "nothing to explore" problem (and `near` is already flat; it's `far`
  / `circuit` that balloon).
- Candidate levers (undecided): scale settlement count with area; bound
  the site-placement region; cap `TOWN_DISTANCE_GROWTH_PER_LEVEL`;
  spread a mystery's sites across multiple settlements.

Author the C.3.2a-5 spec against `SCALE_REPORT.md` → owner review →
implement. Pieces 1 / 4 stay parked until that lands and is re-tested.

## Acceptance

- **C.3.2a:** all five invariants hold on the structural suite across
  ≥300 v1 seeds; the owner's v1 feel-test reports navigation is
  supported (a known lead always yields an honest heading; `look`
  always answers "which way was I meant to go?"; no "I have information
  I can't act on" stretch; a player who ignores the turn-1 heading can
  still recover it).
- **C.3.2b:** the 2×2 is filled from real play. A clear verdict on v2
  geometry (accept as default / keep parked / reject outright), with
  the reasoning recorded in `PHASE_C3_SPEC.md`.

---

*Spec FROZEN 2026-08-29 (owner-approved, with Invariant 5 added).
Implementation begins at build-order step 1 only: `src/nav.py` with
`bearing()` + `heading_is_honest()` + unit tests. Everything past step 1
is gated on the v1 feel-test.*
