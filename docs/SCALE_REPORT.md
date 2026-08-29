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

## Measured — v1 (refined, C.3.2a-5 task 1–3, 250 seeds/depth)

`required_circuit` = the *true* required path (`spawn →
route/require/require2/power → obstacle → escape`), not the earlier
greedy "touch every site" proxy. `survival_budget` calibrated
(`PHASE_C3_2_5_SPEC.md`): **gross ≈ 50 moves**, **usable investigative
≈ 32** after combat / return-leg / non-beeline margins.

| depth | map | dens (sites/1k) | circ p50 | circ p90 | **ratio p90** (circ / 32) | **% over budget** | backtrack p50/p90 | near\* |
|---|---|---|---|---|---|---|---|---|
| 0 | 15² | 23.5 | 14 | 21 | **0.66** | 0 % | 0.00 / 0.06 | 4 |
| 1 | 18² | 15.6 | 17 | 28 | 0.88 | 6 % | 0.00 / 0.02 | 5 |
| 2 | 21² | 11.1 | 21 | 31 | 0.97 | 7 % | 0.00 / 0.04 | 6 |
| 3 | 24² | 8.2 | 23 | 34 | **1.06** | 13 % | 0.00 / 0.03 | 5 |
| 4 | 27² | 6.4 | 26 | 33 | **1.03** | 10 % | 0.00 / 0.00 | 5 |
| 6 | 33² | 4.3 | 32 | 39 | **1.22** | **49 %** | 0.00 / 0.00 | 5 |
| 9 | 34² | 4.2 | 34 | 41 | 1.28 | **64 %** | 0.00 / 0.03 | 6 |
| 12 | 34² | 4.4 | 35 | 48 | **1.50** | **70 %** | 0.00 / 0.03 | 5 |

\* `near` (spawn → nearest site) is a **diagnostic only** — flat at
4–6, never an evaluation metric.

### Reading

- **The gate fails from depth 3.** `ratio p90` crosses 1.0 at depth 3;
  by depth 6 it's 1.22 with **49 % of maps** over the usable budget,
  depth 12 it's 1.5× and 70 %.
- **The true required circuit (p50 14 → 35) is ~40 % shorter than the
  earlier greedy proxy (20 → 60)** — the old number was inflated by
  `closed` + the town centre. But it *still* outgrows the budget.
- **Backtrack is ≈ 0 at every depth.** The required circuits the
  current generator produces are almost pure forward travel — the
  problem is *distance*, not spaghetti. A lever that cuts distance
  without introducing backtracking is a clean win; one that trades
  distance for re-crossing is not.
- **`infeasible` = 0 %** — every required circuit *is* traversable. This
  is purely a budget problem, not a connectivity one.
- **`dens` collapses 23.5 → 4.2** — the density mismatch is the
  underlying cause; watch it does not keep falling under any lever.

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
