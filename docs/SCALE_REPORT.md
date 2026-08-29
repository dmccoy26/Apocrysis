# Scale report — does site density hold as the map grows?

The C.3.2a-5 question, made empirical after BlueNoodle's map-4 death.
Tool: `tools/scale_report.py` (pure geometry, 200 seeds/depth).

**"Meaningful site"** = a mystery site (`mystery.sites` — arriving
there surfaces a fact or a lead) or the real town centre. Not "a
building exists somewhere".

## The generator's growth rule (from `constants.py`)

| depth | map | area | settlements | town min-dist |
|---|---|---|---|---|
| 0 | 15² | 225 | 1 | 6 |
| 3 | 24² | 576 | 1 | 12 |
| 4 | 27² | 729 | 2 | 14 |
| 6 | 33² | 1089 | 2 | 18 |
| 7+ | 34² | 1156 | 2–3 | 20–30 |

Area grows **5×** over a campaign. Settlement count grows to 3.
`TOWN_DISTANCE_GROWTH_PER_LEVEL` actively pushes the objective away.
Mystery-site count is fixed at ~5 regardless.

## Measured (200 seeds/depth)

| depth | map | playable | empty% | sites/1k tiles | spawn→nearest site | spawn→farthest (p50) | **solve circuit p50** | **circuit p90** | town (p50) | **circuit > 50 tiles** |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 15² | 170 | 82% | **29.4** | 4 | 11 | 20 | 28 | 8 | **0 %** |
| 1 | 18² | 257 | 84% | 19.5 | 5 | 14 | 26 | 37 | 11 | 0 % |
| 2 | 21² | 362 | 86% | 13.8 | 6 | 18 | 30 | 42 | 14 | 1 % |
| 3 | 24² | 485 | 86% | 10.3 | 5 | 21 | 38 | 51 | 15 | **12 %** |
| 4 | 27² | 626 | 84% | 8.0 | 5 | 24 | 41 | 57 | 19 | **24 %** |
| 6 | 33² | 935 | 85% | 5.3 | 5 | 30 | 52 | 73 | 24 | **54 %** |
| 9 | 34² | 952 | 84% | 5.3 | 6 | 32 | 58 | 80 | 29 | **68 %** |
| 12 | 34² | 909 | 84% | 5.5 | 5 | 33 | 60 | 78 | 32 | **74 %** |

("solve circuit" = greedy path spawn → touch every meaningful site.
"> 50 tiles" ≈ more than a fresh survivor's whole beeline movement
budget before starvation, *before* combat, backtracking, or the trek
to the exit.)

## The finding

**The decision fork resolves to: the map-growth rule is the priority,
not more affordances.**

1. **The *nearest* site stays close (~5 tiles) at every depth.** Sites
   cluster near spawn by design, so "encounter the first meaningful
   thing" is not harder on a big map *if you head the right way*. This
   confirms an affordance (piece 1/2) would help a disoriented player
   *find the start cluster* — but that's not what's killing survivors.

2. **The *solve circuit* explodes: p50 20 → 60 tiles (3×), p90 28 →
   80.** And the fraction of maps where the circuit alone exceeds a
   fresh survivor's entire movement budget goes **0 % → 24 % (depth 4)
   → 54 % (depth 6) → 74 % (depth 12)**. That is not a
   navigation-interface failure. By mid-campaign most maps cannot be
   *completed* by a survivor who isn't carrying inherited supplies —
   independent of how well they navigate.

3. **Site density collapses 5.5×** (29 → 5 per 1000 playable tiles).
   Fixed site count, 5× area. The map gets emptier and emptier; a
   player who misses the spawn cluster early has an ever-larger barren
   space to wander back through.

4. **The roguelite loop masks this.** BlueNoodle survived depths 0–3
   on accumulated gear/supplies; he died at depth 3 (map 4) on the
   hardest mechanism (airfield-plane, 5 sites) after a wrong-way start.
   A *fresh* survivor — or an heir after a death — hits this wall at
   depth 3–4.

## What this means for the roadmap

- **Piece 2 (`look`) is DONE** and validated in real play (BlueNoodle
  used it twice unprompted, map 4). No more `look` machinery.
- **Pieces 1 and 4 are PAUSED** — not abandoned. They answer "I know
  where to go, how do I recover the direction?" That's real but
  secondary now.
- **The priority is C.3.2a-5, reframed:** *how does the generator keep
  an appropriate density of actionable destinations as the geography
  expands?*

### The constraint

`map growth` is on the **FROZEN balance list** (`PHASE_C3_SPEC.md`), so
the lever is **not** "shrink the maps". It's **maintain the circuit
budget as the map grows** — more meaningful destinations distributed
across a bigger map, so the solve circuit stays ≈ constant in tiles
even as area grows.

And the earlier constraint still holds: **do not fix this by clustering
every site near spawn** — that just recreates the "nothing to explore"
problem in a different shape (see the near-column: sites are *already*
clustered near spawn, which is why `near` is flat while `far`/`circuit`
balloon).

### Open design question for the C.3.2a-5 spec

The real target: **the solve circuit (spawn → every meaningful site)
should stay within a fresh survivor's movement budget at every campaign
depth** — via density, not via shrinking the map or collapsing sites
onto spawn.

Candidate levers to weigh in that spec (not decided here):
- scale settlement count / `SETTLEMENTS_PER_EXPEDITIONS` with map area;
- bound the mystery-site placement region so the circuit is
  area-independent;
- cap `TOWN_DISTANCE_GROWTH_PER_LEVEL` (it currently pushes the
  info-hub objective away linearly);
- distribute the mystery's sites across multiple settlements rather
  than one cluster.

---

*Investigation only. Feeds the C.3.2a-5 spec. No generator change made.*
