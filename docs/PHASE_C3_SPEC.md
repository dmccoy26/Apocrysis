# Phase C.3 — the geography experiment

**A gameplay experiment with an architectural contract**, not a
routine refactor. Builds on `PHASE_C_FOUNDATION.md`.

## The experimental question

> Can irregular geography make exploration feel more like navigating a
> real place, **without materially damaging the established
> survival/combat balance**?

"Gameplay unchanged" does not apply to C.3 the way it applied to
C.1/C.2. C.3 is a controlled change measured against an envelope.

## Reversible by construction

Both generators live behind the one `MapGenerator` API and are
selectable:

```
              Apocrysis(mapgen="v1" | "v2")   (default "v1")
                         │
                  MapGenerator(game, variant)
                    /              \
                v1 pipeline      v2 pipeline
                (frozen,          (irregular
                 byte-identical)   valley mask)
                    \              /
                     MapGraph + build_mystery + zombies  (shared)
```

`tools/geo_compare.py` runs the same seeds through both and compares
distributions. Rejecting C.3 = flip the default back to `"v1"` (one
line) or `git checkout v5-phase-c-foundation`.

## Preserve / intentionally change / measure

| property | C.3 target |
|---|---|
| seed determinism | **preserve** |
| required-node reachability (exit, sites, real town) | **preserve** |
| exit reachability | **preserve** |
| town existence | **preserve** |
| mystery-site reachability | **preserve** |
| terrain vocabulary | **preserve** |
| combat mechanics | **preserve** |
| survival mechanics | **preserve** |
| investigation | **preserve** |
| critical-path concept | **preserve** |
| **rectangular map boundary** | **intentionally change** |
| **terrain shape** | **intentionally change** |
| trek length | **measure, don't assume** |
| buildings encountered | **measure, don't assume** |
| zombie exposure | **measure, don't assume** |
| loot opportunity | **measure, don't assume** |
| hunger/thirst pressure | **measure, don't assume** |
| player perception of exploration | **human test** |

## What v2 does (as implemented)

`MapGenerator._grow_valley_mask()`, only when `variant == "v2"`, after
`g.map` and the boundary ring are built and before spawn:

1. seed 1–3 growth points near the interior centre
2. random-frontier flood outward until the region hits a target size
   (`uniform(0.55, 0.75)` of the interior, with an absolute floor so a
   full mystery always fits)
3. keep only the **largest connected component** of the grown region
4. mountain-fill every other interior cell
5. final pass: keep the largest connected **passable** component (an
   obstacle river from the per-tile overlay could still split it) and
   mountain-fill any leftover islands

Result: one connected irregular valley (~55–65 % of the interior),
mountain everywhere else, boundary ring intact. Spawn, settlements and
the mystery are all embedded on the region afterward, unchanged.

**Not yet in v2** (a later C.3 pass, only if the feel test passes):
the fully inverted pipeline — graph-*first* topology, geography needs
declared by the mechanism, `_carve_escape_pass` against the mask
perimeter, `build_mystery` v2. v2 today is the *minimal* meaningful
change: the board stops being a box.

## Measured result (v1 vs v2, `tools/geo_compare.py`)

### Geometry (1000 games each, exp tiers 0/3/6/9/12)

| metric | v1 mean (p10/p90) | v2 mean (p10/p90) |
|---|---|---|
| playable % | 95.7 (88.5 / 100) | **68.8 (56.6 / 88.2)** ← the change |
| largest region % | 100.0 (100 / 100) | 99.5 (97.4 / 100), min 93.7 |
| dead-end tiles | 2.7 (0 / 9) | 9.2 (1 / 18) |
| spawn→exit | 25.3 (12 / 34) | 20.9 (11 / 31) |
| spawn→site (max) | 24.4 (11 / 33) | 20.3 (10 / 31) |
| critical-path tiles | 38.8 (20 / 58) | 33.2 (16 / 51.5) |
| spawn→town | 23.4 (8 / 36) | 22.8 (9 / 34) |
| maps with no mystery | **0 / 1000** | **0 / 1500** (was 13/1000; fixed by C.3.1) |

### Gameplay (scripted bot, 500 games each, exp tiers 1–5)

| metric | v1 | v2 |
|---|---|---|
| **win rate** | **51 %** | **49 %** (within noise, n=500) |
| turns / expedition | 57.9 | **41.1** (~29 % shorter) |
| zombies defeated | 2.9 | 3.0 |
| fights | 3.4 | 3.5 |
| min health (mean / p10) | 52.7 / 14 | 50.2 / **12** |
| buildings entered | 4.5 | 3.9 |
| settlements discovered | 0.5 | 0.5 |

### Reading

- **Win rate is identical.** The frozen balance holds.
- **Treks are ~23 % shorter** — the valley is smaller. Could be a
  feature (less tedious walking, fewer "solved it, died on the trek"
  deaths) or a concern (less exploration). This is the biggest change.
- **Combat exposure is unchanged** (zombies / fights equal).
- **v2 is marginally harsher at the p10 min-health tail** (12 vs 14) —
  the narrow irregular corridors give a zombie fewer places to be
  avoided. Small, worth watching.
- **No-mystery maps: eliminated (C.3.1).** Pre-fix, ~1.3 % of v2 maps
  grew a valley too cramped for the three building sites a mystery
  needs and shipped a story-less "reach the town" expedition.
  `generate_map()` now *guarantees* a mystery instead of tuning toward
  one: when `build_mystery` returns None / raises on a v2 map, it
  regenerates the base map and retries (≤12×). Measured 0 / 1500 after.
  v1 is frozen — the loop runs exactly once for v1, RNG consumption and
  byte-identity unchanged. This is the "make it structurally
  impossible, don't tune the statistic" fix the pre-playtest review
  asked for.

## C.3.1 — no-mystery guarantee (DONE, 2026-08-29)

The base map is now regenerated until `build_mystery` succeeds, for
`variant == "v2"` only. Changed: `src/mixins/world_mixin.py`
`generate_map()`. Both suites green (`apocrysis.py --test`; pytest
251 + 100). Geometry/gameplay re-measured — envelope still held, win
rate noise-equal, min-health p10 tail now v1≈v2. The five-expedition
feel-test should be run on this build.

## The accept/reject gate — VERDICT (2026-08-29)

> **C.3 v2 — REJECTED AS CURRENTLY DESIGNED. C.3 architecture kept.
> `_default_mapgen` stays `"v1"`.**

The automated envelope held (win 51 %≈49 %, combat exposure equal, no
contract violated). The human feel-test found the problem the metrics
could not see.

### What the feel-test showed (owner, 1 expedition, `--mapgen v2`, `mountain_pass`)

The full run: `apocrysis_playlog_20260829_152820.txt`.

| phase | turns | what happened |
|---|---|---|
| wander | 1–20 | straight lines through undifferentiated forest, no information |
| obstacle found, unused | 21 | reached the forestry gate with `facts_known: ['F_OBSTACLE']`, hypothesis `unknown` |
| perimeter bounce | 21–62 | ~40 turns colliding with the irregular mountain boundary ("The mountains rise up sheer…" ×3, "You can't cross the mountain here" ×2) with **no new information the whole time** |
| first real lead | 70 | stumbled into the only settlement — **64 % into the expedition** |
| death-march back | 80–107 | starving + parched, −4 HP/turn, 59 → 26 HP |
| escape | 109 | won at **26/105 HP** |

`facts_known` sat at `['F_OBSTACLE']` / hypothesis `unknown` from turn
21 to turn 70.

### Why it failed — the actual finding

**Irregularity alone does not create meaningful exploration.** v2 made
the geometry more interesting *without giving the player more
information with which to navigate it.* The strongest evidence is not
the wall-bounces — it is that the player *found something meaningful at
turn 21* (an obstacle) and the world gave them no chain from
"I found an obstacle" → "there is something beyond it" → "where do I
look next". So: obstacle → wander → mountain → wander → mountain →
wander → settlement. That is spatial punishment for lacking
information, not exploration. The irregular boundary functioned as
**friction, not texture.**

Two things that are NOT the finding:
- *"the valley is too small"* — widening treats the symptom; the
  player wasn't short on square footage, they were short on a reason to
  pick a direction. A wider empty valley is worse.
- *"the player should have used `look`"* — if the intended experience
  needs a special command just to learn there is something nearby,
  that's a UX gap, not a player failure. And they *did* encounter
  `F_OBSTACLE` — the game had the information and failed to make it a
  navigational affordance.

### Update (2026-08-29) — expedition 2 shows this is NOT v2-specific

A second feel-test run — **v1**, `boat_crossing`, 18×18 — died at turn
99 having found **zero mystery evidence** (`facts_known` = 5 ambient
clues, `hypothesis` never left `unknown`). The player left spawn on
turn 1, circled the map perimeter (64 of 324 tiles), and never touched
a mystery site, because the sites cluster near spawn by design. The
ESCAPE panel showed "head for the way out (north)" from turn 1 and an
ambient clue ("boot prints lead north") matched it exactly at turn 94 —
neither was reinforced or marked, and the player acted on neither.

**The v2 rejection was never really about v2.** v1 has the identical
failure mode; the rectangular map's self-correcting bounds merely hid
it more often. This does not change the verdict (v2 stays rejected as
designed, C.3.2 stays the path) — it sharpens why C.3.2a on v1 is a
real fix, not a warm-up. See `PHASE_C3_2_SPEC.md` § "The problem is not
v2-specific".

### A clean negative result (not a failed experiment)

Keep the four claims separate:

| claim | verdict |
|---|---|
| **C.3 architecture** — `worldgen/` + `MapGraph` + reversible variants behind one API | **good.** Worth building. A negative geography result cost one `_default_mapgen` line, not a phase. |
| **C.3 v2 geography** — the grown irregular valley as it stands | **rejected.** |
| **C.3 hypothesis** — "irregular geography by itself makes exploration feel more place-like" | **disproved by the playtest.** |
| **What it revealed** — geometry needs navigational *affordances*, not merely irregular boundaries | **the actual finding, and the basis for C.3.2.** |

The irregular geometry is **perceptually real** — the player noticed it
immediately and named it. That's the good half. The failure is that
the rest of the world doesn't give that geometry meaning.

### Actions

1. `_default_mapgen` stays `"v1"` (production default). v2 kept as a
   **rejected experiment / reference implementation** (not deleted) —
   the boundary-growth code is C.3.2's substrate.
2. **Do not** revert the C.3 architecture or the tag
   `v5-phase-c-foundation`.
3. **Do not tune the current irregular mask.** The run exposed two
   separable effects — (a) concavity → repeated boundary collisions,
   (b) the world doesn't communicate enough to exploit the geometry.
   Widening the valley or trimming dead ends would make the bad
   behaviour less painful without answering whether irregular geography
   is useful at all. That's a worse result than a clean rejection.
4. The "fully-inverted pipeline" idea (old C.3.2) is **superseded** —
   no point inverting a pipeline whose geography doesn't yet earn
   navigation.
5. **Next step is NOT the C.3.2 spec.** First do the small design
   investigation below (`## Pre-C.3.2 investigation`). Then author the
   C.3.2 spec against its findings → owner review → implement.
6. **Also blocking C.3.2:** fix mechanism variety (see
   `## Contamination: mechanism variety`). Three `mountain_pass` runs
   in a row contaminated the geography read.

## Pre-C.3.2 investigation — the navigational-signal inventory (DONE)

**`docs/NAV_SIGNAL_INVENTORY.md`** — 26 signals inventoried and
classified `observable → interpretable → actionable`. Owner review
pending.

Headline findings:

- **Terrain is inert for navigation.** 7 types, none directional. No
  roads. The only linear features are barriers.
- **The map has no orientation aids** (no coords / compass / scale —
  removed 2026-08-28) **and no markers until a fact is already known.**
- **The strongest actionable signal — the found survey map — is a
  random loot drop.**
- **Every mystery lead is gated behind already knowing the fact**, and
  you learn the fact by physically stepping on the site tile. No
  see-it-at-a-distance beat (except the rare BLUE_SIGNS lore).
- **The one heading the generator hands out** (spawn→gap bearing,
  "toward the north-east edge") **is never validated against
  traversability** — Invariant 2 failing by construction, predating v2.
- **Navigational flavour text exists and is thrown away** (boot-prints-
  lead-north etc. land in the journal as inert trivia).

**Conclusion: the generator is not the primary problem.** The game
already computes live bearings, has a marker system, and generates
directional clue text — it just gates all of it behind knowing the
fact, never validates a heading, and leaves ambient nav text inert.
So C.3.2 is **mostly a surfacing + validation experiment with a small
generator guarantee**, not a generation rewrite (see the doc's
"What this means for C.3.2" for the ordered candidate pieces).

## C.3.2 — navigational affordances

> **Spec authored: `PHASE_C3_2_SPEC.md`** (2026-08-29, owner review
> pending). C.3.2a = v1 affordances (4 ordered pieces + a graph-honest
> `bearing()` helper); C.3.2b = replay the feel-test on v2. The result
> is a 2×2 (v1/v2 × old-nav/affordances), and the comparison that
> matters is **v1-affordances vs v2-affordances**. **Invariant 4** was
> added: navigation signals must correspond to actual `MapGraph`
> topology — prose and generation don't independently agree, the claim
> is validated against the realised graph. The three invariants below
> are restated verbatim in that spec.

**Irregular geography is only useful if the world provides enough
information for the player to navigate it.**

The v1/v2 evidence (table below) gives three distinct, testable,
story-agnostic constraints. A "lead" here is anything that turns
"wander" into "head that way" — a settlement direction, a road that
visibly continues, a distant landmark, a sign, a radio transmission, a
terrain transition, a discovered site, an investigation deduction. The
list stays open; the story layer decides what any given lead *means*.

> **Invariant 1 — Lead before obstacle.** Every expedition must expose
> at least one meaningful navigational lead within the early
> exploration window, and a blocking / obstructive site must not become
> the player's first meaningful information without an existing lead
> that gives it context.
>
> **Invariant 2 — Leads must survive geography.** If a player-facing
> lead establishes a destination and a directional heading, the
> generated geography must provide a traversable route consistent with
> that heading. A valid destination elsewhere on the map is
> insufficient if following the communicated direction immediately
> runs into an impassable boundary.
>
> **Invariant 3 — Navigation must stay actionable.** Between receiving
> a lead and reaching its destination the geography may require
> exploration or route-finding, but must not repeatedly invalidate the
> lead's implied direction through arbitrary boundary collisions.

**A lead is not the same thing as information.** `F_OBSTACLE` is
information — a locked gate the player found. "The evacuation route
lies to the north-east" is a lead — it gives an actionable direction
immediately. Information becomes useful only once connected to other
knowledge; a lead is directional on contact. This distinction matters
for the investigation system's future design too, not just the map.

**Prohibited solutions.** Do not guarantee a particular settlement
distance from spawn. Do not embed a specific story location near spawn.
The requirement is *navigational affordance*, not a prescribed layout —
solving it by pinning geometry just optimises the generator around
today's implementation.

### Empirical motivation — v1 vs v2, same terrain, same player behaviour

Two expeditions, both `mountain_pass`, both ~15×15 mostly-forest,
player used no investigation commands in either, both wandered ~20
turns before the first discovery:

| | **v1** (`apocrysis_playlog_20260829_154304.txt`) | **v2** (`apocrysis_playlog_20260829_152820.txt`) |
|---|---|---|
| first discovery | settlement at turn 22 — **all three route facts at once** (`F_OBSTACLE`, `F_REQUIRE`, `F_ROUTE`), a heading, and a plan | **obstacle** at turn 21 — `F_OBSTACLE` only, no context |
| next ~50 turns | key at t24, straight walk to the gate t26–37 | ~40 turns bouncing off the irregular boundary, still `F_OBSTACLE` only |
| first real lead | turn 22 (58 % — but the run was short *because* it went well) | turn 70 (64 %) |
| total turns / tiles | 38 / 24 | 109 / 76 |
| end HP | 23/105 | 26/105 |
| "north-east edge" heading | actionable — walk north-east on the rectangle | invalidated — north-east was a mountain wall |

Same noticeboard text, same player, same terrain palette. v1 produced
an actionable route at the first discovery; v2 produced an isolated
obstacle followed by boundary friction. That is the whole finding, and
it is unusually clean.

*(v1 is the bar, and it's not a high one: that run finished at 23 HP
with fatigue pinned at 100 the whole back half and a −50 HP zombie hit
at the gate. "Functional, not comfortable.")*

## Contamination: mechanism variety (fix before C.3.2)

`DIS_FEW_REMAINS` (the first CH1 WorldFact, and the one every fresh
campaign targets on expedition 1) has exactly one DiscoveryTemplate
route: `mountain_pass` (`worlds/silence/discovery.py`). So **every
brand-new campaign's first expedition is `mountain_pass`,
deterministically.** The three repeats in the feel-test came from the
survivor-name bug (fixed, `d6e03de`) preventing the campaign from
saving — each launch restarted at expedition 1.

With saving fixed, the Balthus campaign now progresses
(`DIS_FEW_REMAINS: known` already), so expedition 2 targets
`DIS_MOVED_TOGETHER` → `rail_tunnel` / `boat_crossing`, etc. But for
deliberately feel-testing geography *across* mechanisms, either:
- play the existing campaign forward (mechanisms vary run to run), or
- add a debug way to force the mechanism (the balance harness already
  has `--force-mechanism`; nothing player-facing yet), or
- give `DIS_FEW_REMAINS` a 2nd non-spatial route so even expedition 1
  varies.

Pick one when C.3.2's spec is written. The geography experiment should
run across `mountain_pass / radio_tower / evac_corridor / service_route
/ dam_valves`-shaped runs, not five near-identical ones.
