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

## Measured — v1 (C.3.2a-5, refined + decomposed, 250 seeds/depth)

`required_circuit` = the *true* required path (`spawn →
route/require/require2/power → obstacle → escape`). `survival_budget`
calibrated (`PHASE_C3_2_5_SPEC.md`): **gross ≈ 50 moves**, **usable
investigative ≈ 32**. Seeds rotate through **all 10 mechanisms**
(fresh `Apocrysis` otherwise always targets the first WorldFact →
mountain_pass only).

### Headline matrix

| depth | map | dens | dst/1k | circ p50 | circ p90 | **ratio p90** | **% over budget** | backtrack | near\* |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 15² | 25.3 | 5.04 | 15 | 22 | **0.69** | 0 % | ≈0 | 4 |
| 1 | 18² | 16.7 | 2.65 | 18 | 30 | 0.94 | 6 % | ≈0 | 5 |
| 2 | 21² | 11.9 | 1.59 | 21 | 31 | 0.97 | 8 % | ≈0 | 6 |
| 3 | 24² | 8.9 | 0.91 | 23 | 35 | **1.09** | 14 % | ≈0 | 5 |
| 4 | 27² | 6.9 | 0.88 | 27 | 34 | **1.06** | 14 % | ≈0 | 5 |
| 6 | 33² | 4.6 | 0.50 | 33 | 42 | **1.31** | **52 %** | ≈0 | 5 |
| 9 | 34² | 4.5 | 0.34 | 35 | 43 | 1.34 | **68 %** | ≈0 | 6 |
| 12 | 34² | 4.7 | 0.30 | 36 | 49 | **1.53** | **74 %** | ≈0 | 5 |

\* `near` is a **diagnostic only** — flat at 4–6, never an evaluation
metric. `dst/1k` = distinct settlements a required site falls in, per
1000 playable tiles.

### Per mechanism (circ p50 / p90) — it's *systemic*, not one bad family

| mechanism | d0 | d3 | d6 | d12 |
|---|---|---|---|---|
| mountain_pass | 14/21 | 23/28 | 33/41 | 36/41 |
| rail_tunnel | 14/20 | 24/35 | 34/40 | 35/57 |
| boat_crossing | 14/23 | 22/39 | 35/43 | 36/57 |
| evac_corridor | 15/22 | 23/33 | 36/47 | 38/56 |
| radio_tower | 17/31 | 24/37 | 35/49 | 36/61 |
| power_station | 15/24 | 25/28 | 32/44 | 37/40 |
| dam_valves | 15/22 | 23/40 | 31/34 | 36/57 |
| **airfield_plane** | 15/24 | 27/39 | **34/65** | 38/51 |
| tidal_causeway | 14/21 | 23/37 | 29/44 | 37/47 |

All 10 cluster tightly. `airfield_plane` at d6 has the worst p90 (65) —
the extra `require2` fetch on a big map, exactly BlueNoodle's death.

### spawn → endpoint distance (p50 / p90) — **which endpoint grows**

| depth | route | require | require2 | power | **obstacle** | **escape** | town |
|---|---|---|---|---|---|---|---|
| 0 | 6/10 | 6/9 | 7/8 | 6/12 | 11/12 | 12/13 | 8/12 |
| 3 | 11/18 | 9/17 | 10/19 | 11/16 | **20/22** | **21/23** | 15/21 |
| 6 | 16/26 | 9/22 | 12/23 | 9/25 | **30/33** | **31/34** | 24/34 |
| 12 | 15/31 | 10/30 | 20/30 | 7/31 | **30/34** | **32/35** | 33/39 |

### Leg-by-leg (canonical order, p50 / p90)

| depth | spawn→route | route→require | **require→obstacle** | obstacle→escape |
|---|---|---|---|---|
| 0 | 6/10 | 2/5 | **7/12** | 1/1 |
| 3 | 11/18 | 2/12 | **14/21** | 1/1 |
| 6 | 16/26 | 3/23 | **23/30** | 1/1 |
| 12 | 15/31 | 4/27 | **22/31** | 1/1 |

## The finding — the escape gap is the scaling driver

The `route` / `require` sites stay near spawn as designed
(`spawn→require` p50 6 → 10). **`obstacle` and `escape` are what grow**
— `spawn→escape` p50 **12 → 32** (2.7×). The escape gap is deliberately
carved at *"the far corner"* (`escape.py` `_carve_escape_pass`), so as
the map grows the exit moves proportionally further from the
spawn-clustered investigation.

The leg breakdown localises it: **`require→obstacle`** (get the item,
then walk to the gate) is the leg that scales — **p50 7 → 22 tiles**.
`route→require` also balloons at p90 (12 → 27): the `require` side-trip
can land far on a big map.

**The primary lever the decomposition points at is not quite on the
original list**: *bound how far the escape gap — and therefore the
`require→obstacle` leg — is placed from the investigation cluster* (a
refinement of lever 2). Capping `TOWN_DISTANCE_GROWTH` (lever 3) touches
settlement placement, which drifts `route`/`require` out a little, but
the town itself isn't on the required circuit.

- **Backtrack ≈ 0 at every depth** → the problem is **distance**, not
  spaghetti. Any lever that shortens `require→obstacle` / `spawn→escape`
  without introducing re-crossing is a clean win; one that trades
  distance for re-crossing is a regression even if the ratio improves.
- **`infeasible` = 0 %** → purely a budget problem, not connectivity.
- **`dens` 25 → 4.7, `dst/1k` 5.0 → 0.30** → the mystery lives in **one**
  settlement at every depth; the density of that one place per unit
  geography craters.

### Old table (superseded — greedy all-sites circuit, `> 50` threshold)

<details><summary>200 seeds/depth, first pass</summary>

| depth | map | playable | dens | near | far p50 | circ p50 | circ p90 | circ > 50 |
|---|---|---|---|---|---|---|---|---|
| 0 | 15² | 170 | 29.4 | 4 | 11 | 20 | 28 | 0 % |
| 3 | 24² | 485 | 10.3 | 5 | 21 | 38 | 51 | 12 % |
| 6 | 33² | 935 | 5.3 | 5 | 30 | 52 | 73 | 54 % |
| 12 | 34² | 909 | 5.5 | 5 | 33 | 60 | 78 | 74 % |

</details>

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
