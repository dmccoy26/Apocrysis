# Phase C.3.2 — navigational affordances (design, authored before implementation)

Builds on: `PHASE_C3_SPEC.md` (the v2 feel-test verdict + the three
invariants) and `NAV_SIGNAL_INVENTORY.md` (26 signals classified
`observable → interpretable → actionable`).

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

## The invariants (locked before implementation)

The first three are from `PHASE_C3_SPEC.md`, restated. **Invariant 4 is
new** and is the hard contract for C.3.2.

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

**`bearing()` is a new shared helper** — one implementation, replacing
the two ad-hoc ones (`_mystery_heading`, tui `_compass`). Signature
roughly `bearing(from_xy, to_xy) -> "north-east" | "" ` with the
existing ±1 deadzone. C.3.2 adds a graph-aware variant:
`heading_is_honest(graph, here, node, claimed) -> bool` — true iff the
shortest path's early tiles move in `claimed`'s general direction.

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

## Scope

### C.3.2a — v1 navigation affordances (ships first)

Ordered smallest-first. Each piece stands alone and is testable.

| # | change | where | MapGraph contract | test |
|---|---|---|---|---|
| 1 | **Landmark → bearing.** `_spot_landmarks` says *which way* the rooftops/building are; the sighting is remembered so `look` can re-report it. | `world_mixin._spot_landmarks`, a `_landmarks_seen_dir` store | bearing computed from real tile positions | unit: a sighting NE of the player produces "north-east"; structural: on 200 seeds every settlement sighting has a non-empty bearing or is adjacent |
| 2 | **`look` re-frames** (section above) — reports the nearest earned lead with a graph-honest heading, or says plainly there's none. | `knowledge_mixin.knowledge_look` | `heading_is_honest` before printing a direction | unit: known route NE + clear path → "north-east"; known route NE + wall NE + path actually goes N → "north"; nothing known → the null line |
| 3 | **Validate the spawn→gap bearing.** The baked `E_obstacle_a` / `E_route_reveal` bearing ("toward the north-east edge") is checked against `MapGraph` at generation; if the honest early-path heading differs, the text uses the honest one. | `escape.build_mystery` (the `_bearing` block), `world_mixin.generate_map` after the graph is built | `shortest_path(spawn, exit)` early tiles define the honest heading | structural: on 300 v1 + 300 v2 seeds, the bearing word in `E_obstacle_a` matches the first-5-tiles heading of the spawn→exit path |
| 4 | **Ambient clues → soft hint** *(only if 1–3 don't clear the bar)*. `_PHASE_B_CLUES` entries with a direction ("boot prints lead north") drop a low-confidence directional arc the map/`look` can show — imprecise, not a `!`. | `world_mixin._maybe_surface_clue`, `_render_map_lines` | the arc points along a real reachable sector, else the clue surfaces without a hint | unit: a "north" clue with open north → hint shown; blocked → text only |

**No early-lead *generation* guarantee in C.3.2a.** If 1–4 land and
the early window still starves the player of direction on v1, *then* a
minimal guarantee (an actionable lead reachable within the early
window, validated by Invariant 4) is scoped as C.3.2a-5 — never by
pinning a settlement distance or a story location near spawn.

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

1. `bearing()` + `heading_is_honest()` shared helpers + unit tests
   (small new module, `src/worldgen/` or `src/nav.py`).
2. C.3.2a piece 1 (landmark bearings).
3. C.3.2a piece 2 (`look` reframe).
4. C.3.2a piece 3 (spawn→gap bearing validation) + golden-fixture
   update.
5. Both suites green, commit, tag `v5-phase-c3-2a`.
6. **Owner feel-test on v1** — does navigation feel supported?
7. Piece 4 (ambient clue hints) only if 6 says the early window still
   starves.
8. Variety fix (one of the three options).
9. C.3.2b — owner feel-test on v2. Fill the 2×2. Verdict.

## Acceptance

- **C.3.2a:** all four invariants hold on the structural suite across
  ≥300 v1 seeds; the owner's v1 feel-test reports navigation is
  supported (a known lead always yields an honest heading; `look` is
  useful; no "I have information I can't act on" stretch).
- **C.3.2b:** the 2×2 is filled from real play. A clear verdict on v2
  geometry (accept as default / keep parked / reject outright), with
  the reasoning recorded in `PHASE_C3_SPEC.md`.

---

*Owner review pending. No code until the spec is approved.*
