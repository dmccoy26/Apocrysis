# Navigational-signal inventory (pre-C.3.2 investigation)

**Question:** what information does Apocrysis currently give the player
that can legitimately function as a *navigational lead* — something
that turns "wander" into "head that way"?

Motivated by the C.3 v2 feel-test (`PHASE_C3_SPEC.md` § verdict): the
irregular map wasn't unplayable because of its geometry, it was
unplayable because the player had almost no information to navigate it
with. Before writing the C.3.2 spec we need to know whether that's a
**generator** problem or a **surfacing** problem.

## The lens

Each signal is classified on three rising bars:

| bar | meaning |
|---|---|
| **observable** | the player can perceive that it exists |
| **interpretable** | the player can tell *what kind of thing* it is |
| **actionable** | it gives the player a **direction to move now** |

A "lead" (C.3.2 vocabulary) is a signal that reaches **actionable**.
Everything below that is *information* — potentially useful once
connected to other knowledge, but not directional on contact.
`F_OBSTACLE` (a locked gate you found) is information. "The route lies
to the north-east" is a lead.

## Inventory

### Terrain layer

| # | signal | where | reaches | notes |
|---|---|---|---|---|
| 1 | terrain glyphs `f ~ b . ^ = s` | map panel, `_render_map_lines` | **interpretable** | 7 types = movement cost + texture. **No type carries direction.** No roads. Rivers (`=`) are barriers, not corridors. |
| 2 | move feedback ("You move through dense forest") | `move_and_search` | observable | first-visit only; pure texture |
| 3 | map-archetype blurb ("Dense old-growth forest closes in on every side") | once, loop start | observable | scene-setter; *anti*-navigational if anything ("closes in on every side") |
| 4 | the impassable ring (`^`/`=`) as the world edge | map | interpretable | replaced the removed `*` border + coordinate ruler (2026-08-28, "invited edge-following"). On v1 the ring ≈ a rectangle you learn in one lap; on v2 it's the thing the player kept colliding with |

### Structures

| # | signal | where | reaches | notes |
|---|---|---|---|---|
| 5 | "Rooftops in the distance — there's a settlement out there" | `_spot_landmarks` | **observable only** | **no bearing.** Fires only within `visibility_radius` (3 by day, **1 at night**) — so not "in the distance" at all, and you can't triangulate. Doesn't say *which* settlement or whether it's the one you need. |
| 6 | "You spot a building standing alone in the distance" | `_spot_landmarks` | observable only | capped at 3 firings/expedition; no bearing |
| 7 | "You've found a settlement — worth exploring" | on entry | interpretable | you're already on it |
| 8 | district lines ("You're in the commercial district") | on entry | interpretable | intra-settlement only; no navigational value |
| 9 | building interiors (safe zone / abandonment flavour) | on entry / `look` | interpretable | destination texture, not direction |

### Map visibility

| # | signal | where | reaches | notes |
|---|---|---|---|---|
| 10 | fog of war | `_render_map_lines` | — | Manhattan `visibility_radius` 1–3. On 15×15 you see ≤ a 3-tile radius |
| 11 | visited tiles (rendered `.`) | map | observable | a breadcrumb trail — tells you where you've *been*, not where to go |
| 12 | **found survey map** (`map_revealed` / `town_known`) | `find_loot` item | **actionable** | reveals all terrain + the town. When held, navigation transforms. **It's a random loot drop** — the strongest nav signal in the game is not guaranteed to appear. |
| 13 | map orientation | — | — | no compass rose, no "N" label, no scale. Player must infer top = north |

### Mystery / investigation

| # | signal | where | reaches | notes |
|---|---|---|---|---|
| 14 | `!` map marker (mystery site / blocked route) | `_mystery_site_mark` | **actionable** | **only rendered once the relevant `F_*` fact is known.** Pre-fact: nothing on the map. |
| 15 | `+` map marker (route now open) | same | actionable | post-solve |
| 16 | site-arrival prose ("This is the ranger station") | `mystery_arrive` | interpretable | **requires standing exactly on the tile** (`_mystery_role_at` is an equality check) |
| 17 | NEW LEAD banner — `require` / `power` | `_mystery_progress_flare` | **actionable** | carries a **live** `(north-east of you)` heading via `_mystery_heading` |
| 18 | NEW LEAD banner — `route` | same | interpretable→actionable | "It's marked on your map now" — **no heading** on the route lead specifically |
| 19 | static bearing in `E_obstacle_a` ("out toward the north-east edge of the valley") | `build_mystery`, baked at gen | **actionable (but unvalidated)** | computed once from spawn→gap vector. **Never checked against traversability.** This is the exact signal that failed on v2 — the NE edge was a mountain wall. |
| 20 | OBJECTIVES / ESCAPE checklist headings | tui `_objective_steps` → `heading()` | **actionable** | live straight-line `(north-east)` to each *known* site; before F_ROUTE it degrades to "head for the way out" with no place and no direction |
| 21 | investigation facts `F_*` | `journal` / `remember` / `inspect` | information | not directional; the C.3.2 "lead ≠ information" case in point |
| 22 | `_PHASE_B_CLUES` — "Boot prints all lead north", "walking toward the mountains", "muster point" | `_maybe_surface_clue`, 18 % in buildings | **information only — and this is a miss** | genuinely navigational *text*, routed to the journal as inert Known facts. No map marker, no heading, no objective line. Explicitly a "Phase-B stopgap". |

### Other

| # | signal | where | reaches | notes |
|---|---|---|---|---|
| 23 | `look` on open ground | `knowledge_look` | — | "Open forest. Nothing here that matters." **Actively tells the player there is nothing to navigate by.** Doesn't re-report distant landmarks, doesn't give a bearing. |
| 24 | radio response (`radio_tower` / informational family) | `E_route_reveal` | **actionable** | names a route + folds in the `{bearing}`; same spawn-relative, unvalidated bearing as #19 |
| 25 | `SurvivorLore` BLUE_SIGNS | `_mystery_site_mark` override | actionable | marks the `evac_corridor` route from turn 1 — the *one* case where a lead precedes exploration. Legibility, not power. |
| 26 | compass bearing helpers | `_mystery_heading`, tui `_compass` | — | **two** independent implementations, both straight-line player→site with a ±1 deadzone. **Neither checks whether the heading is traversable.** |

## Findings

**1. Terrain is inert for navigation.** Seven terrain types, zero of
them directional. No roads, no ridgelines-as-guides, no "the valley
floor slopes toward the river". The only linear features (`=` rivers,
`^` mountain) are barriers. A player standing in forest has *nothing*
in the terrain telling them which way anything is.

**2. The map is a weak navigational surface by design.** Fogged to
r≤3, no coordinates, no compass, no scale, and — critically — **no
markers at all until you already know a fact**. The 2026-08-28 removal
of the border + ruler was correct for its goal (stop edge-following)
but it left the map with no orientation aids of any kind. On a bounded
rectangle that's survivable; the space self-corrects a wanderer. On an
irregular valley it isn't.

**3. The strongest actionable signal is a random drop.** The found
survey map (#12) is the single thing that reliably turns wandering into
routing — and whether the player gets it is a loot roll.

**4. The mystery system's leads are actionable but arrive too late and
too locally.** `!` markers and live headings (#14, #17, #20) are good
signals — but every one of them is gated behind *already knowing the
fact*, and you learn the fact only by **physically stepping on the site
tile** (#16). There is no "you see a structure that might be a ranger
station, half a mile north" beat. The BLUE_SIGNS lore (#25) is the only
lead-before-exploration case in the whole game, and it's a rare
unlockable.

**5. The one heading the generator does hand out is never validated.**
The spawn→gap bearing (#19, #24) is computed once and baked into
evidence text. Nothing checks that "north-east" is actually walkable
from spawn. This is C.3.2 Invariant 2 failing *by construction*, and it
predates v2 — v2 just made it bite.

**6. Navigational flavour exists and is thrown away.** #22's boot-print
and muster-point clues are exactly the kind of soft directional signal
C.3.2 wants — and they land in the journal as inert trivia.

## What this means for C.3.2

**The generator is not the primary problem.** The game already
computes live bearings (twice), already has a map-marker system,
already generates directional clue text. The gaps are:

- **(surfacing)** nothing directional reaches the player *before* they
  know a fact — landmarks have no bearing, `look` is dead, the
  nav-flavoured clues are inert;
- **(validation)** a communicated heading is never checked against the
  geography it's supposed to cross;
- **(guarantee)** nothing ensures an actionable lead exists early, or
  before the first obstacle.

So C.3.2 is likely **mostly a surfacing + validation experiment with a
small generator guarantee**, not a generation rewrite. Candidate
pieces, smallest first:

1. give `_spot_landmarks` (#5/#6) a bearing, and let `look` (#23)
   re-report the nearest known-but-unvisited landmark with a heading —
   pure surfacing, no generation change;
2. validate the spawn→gap bearing (#19/#24) against `MapGraph` at
   generation; if "north-east" is blocked, either re-word it to a
   traversable heading or regenerate — directly answers Invariant 2;
3. wire the navigational clues (#22) to a soft, imprecise map hint (a
   direction arc, not a `!`) — Invariant 1's "a lead before the
   obstacle";
4. only then consider a generator guarantee that an actionable lead is
   reachable within the early window (Invariants 1–3), and **not** by
   pinning a settlement distance.

Recommendation: the C.3.2 spec should be scoped around **1–3 as the
experiment**, with the irregular v2 mask kept parked and re-tested
*after* the surfacing changes land on v1 — so we learn whether
irregular geography is playable *with* affordances, without
re-confounding it against a generation change.

---

*Owner review pending. Feeds the C.3.2 spec.*
