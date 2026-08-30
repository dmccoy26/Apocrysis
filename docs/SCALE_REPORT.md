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

# Lever matrix (C.3.2a-5 tasks 4–7)

`tools/scale_report.py --levers`, 220 seeds/depth, all 10 mechanisms
rotated. Raw: `tools/lever_matrix.json`. **Measurement-only — every
lever is a class flag on `Apocrysis`, default off; baseline is
byte-identical to `main` (the C.1 golden fixture passes).** No
combinations. No default changed. See
`docs/PHASE_C3_2_5_LEVER_MATRIX.md`.

Each cell: **`ratio p90`** (circuit p90 / 32 — the gate, target < 1) ·
**`over%`** (maps over budget) · **`r→o`** (`require→obstacle` p90,
tiles — the leg the experiment targets) · **`dst/1k`** (distinct
participating settlements / 1000 tiles — must not keep falling).

| variant | d0 | d3 | d4 | d6 | d9 | d12 |
|---|---|---|---|---|---|---|
| **baseline** | 0.69 · 0% · 12 · 5.1 | 1.09 · 14% · 21 · 0.92 | 1.06 · 14% · 24 · 0.92 | 1.31 · 54% · 30 · 0.50 | 1.34 · 69% · 30 · 0.36 | **1.53 · 73% · 31 · 0.30** |
| settlements_scaled | 0.69 · 0% · 12 · 5.1 | 1.00 · 9% · 20 · 1.62 | 1.03 · 12% · 24 · 1.08 | 1.19 · 49% · 29 · 0.70 | 1.28 · 64% · 30 · 0.41 | 1.53 · 76% · 30 · 0.35 |
| **escape_gap_bounded@8** | 0.62 · 0% · 9 · 4.7 | 0.78 · 0% · 9 · 0.75 | 0.84 · 1% · 9 · 0.43 | 0.97 · 5% · 11 · 0.22 | 1.06 · 12% · 12 · 0.14 | **1.16 · 17% · 13 · 0.12** |
| escape_gap_bounded@12 | 0.75 · 1% · 13 · 5.3 | 0.91 · 4% · 12 · 0.77 | 0.94 · 5% · 12 · 0.49 | 1.06 · 14% · 13 · 0.27 | 1.16 · 17% · 13 · 0.14 | 1.22 · 20% · 15 · 0.13 |
| escape_gap_bounded@16 | 0.88 · 0% · 16 · 5.6 | 1.03 · 13% · 16 · 0.89 | 1.03 · 11% · 16 · 0.56 | 1.16 · 20% · 16 · 0.30 | 1.28 · 23% · 17 · 0.19 | 1.34 · 25% · 18 · 0.14 |
| escape_gap_bounded@20 | 0.91 · 0% · 18 · 5.6 | 1.16 · 27% · 20 · 1.04 | 1.19 · 22% · 20 · 0.82 | 1.31 · 29% · 20 · 0.34 | 1.41 · 36% · 21 · 0.23 | 1.47 · 33% · 22 · 0.20 |
| town_distance_capped@12 | 0.69 · 0% · 12 · 5.1 | 1.09 · 14% · 21 · 0.92 | 1.03 · 12% · 24 · 1.04 | 1.28 · 51% · 30 · 0.57 | 1.25 · 62% · 30 · 0.61 | 1.34 · 66% · 31 · 0.68 |
| town_distance_capped@16 | (≈ baseline) | 1.09 · 14% · 21 · 0.92 | 1.06 · 14% · 24 · 0.92 | 1.31 · 52% · 30 · 0.53 | 1.25 · 65% · 30 · 0.53 | 1.34 · 64% · 31 · 0.55 |
| town_distance_capped@20 | (≈ baseline) | 1.09 · 14% · 21 · 0.92 | 1.06 · 14% · 24 · 0.92 | 1.31 · 54% · 30 · 0.50 | 1.28 · 65% · 30 · 0.41 | 1.34 · 70% · 31 · 0.50 |
| sites_across_settlements | 0.66 · 0% · 11 · 5.4 | 1.09 · 12% · 17 · 1.02 | 1.06 · 14% · 17 · 1.15 | 1.34 · 50% · 19 · 0.63 | 1.31 · 67% · 18 · 0.50 | 1.50 · 72% · 21 · 0.34 |

Backtrack p90 (baseline ≈ 0.03–0.07 at every depth): only
`escape_gap_bounded` raises it — **0.09–0.13** at the tighter bounds
(≈ 2–4× baseline). Every other variant stays ≈ 0.03. `infeasible` = 0 %
for **all** variants at all depths.

## Per-lever interpretation

**`settlements_scaled` (lever 1).** Adds meaningful geography — `dst/1k`
roughly doubles (d3 0.92 → 1.62). But it does **not** shorten the
required trek: `require→obstacle` is unchanged (31 → 30 at d12), and
`ratio p90` barely moves (d12 identical to baseline, d6 1.31 → 1.19).
Backtrack unchanged. *Content density alone does not solve topology.*

**`escape_gap_bounded` (lever 2 — the sweep).** The only lever that
touches the actual mechanism. It **decouples `require→obstacle` from
map size**: at @8 the leg is ≈ 9–13 tiles at *every* depth (baseline
12 → 31). `ratio p90` improves the most at the tightest bound
(d12 1.53 → 1.16 @8). **But it triggers two of the spec's regression
flags:** `dst/1k` at @8/@12/@16 collapses to ≈ 0.12–0.14, *below*
baseline's 0.30 — pulling the gap toward the cluster shrinks the
meaningful footprint (the "nicer shirt" failure) — and backtrack
roughly doubles (0.03 → 0.09–0.13). @20 preserves density (0.20) and
backtrack (0.08) but barely moves the gate (d12 1.47). **And even @8
does not clear the gate** — d9 1.06, d12 1.16.

**`town_distance_capped` (lever 3).** `require→obstacle` **completely
unchanged** (12 → 31 at every cap). `ratio p90` moves by ≤ 0.19 (0 at
most depths). The one real effect is `dst/1k` *rising* (d12 0.30 →
0.50–0.68) — capping the town's drift keeps settlements denser near
spawn. The town is not on the required circuit; the modest d12 movement
is a second-order effect of settlement placement, not the mechanism.

**`sites_across_settlements` (lever 4).** Cleanly redistributes the
target leg — `require→obstacle` p90 31 → 21 — **with backtrack staying
at baseline (0.03)** and `dst/1k` slightly up. But the **headline
`ratio p90` is unchanged** (d12 1.53 → 1.50): the greedy circuit
re-routes — `spawn→require` grows as `require→obstacle` shrinks — so
the total circuit length washes out. It moves *where* the walking is,
not *how much*.

## Hypotheses falsified

1. **Town-distance drift is a driver.** FALSIFIED. `town_distance_capped`
   moves `require→obstacle` by **0** and `ratio p90` by ≤ 0.19 (mostly
   0). The town is not on the required circuit. **Retire lever 3.**
2. **More settlements alone fixes the gate.** FALSIFIED.
   `settlements_scaled` doubles `dst/1k` but leaves `require→obstacle`
   and `ratio p90` essentially unmoved.
3. **`sites_across_settlements` alone fixes the gate.** FALSIFIED for
   the headline gate. It moves the target leg (31 → 21) with no
   regressions, but the circuit re-routes and `ratio p90` doesn't
   move.
4. **A single lever passes the gate.** FALSIFIED. Nothing gets
   `ratio p90 < 1` at depths 9–12. `escape_gap_bounded@8` comes
   closest (d12 1.16) but violates the density and backtrack rules.

## What the matrix does *not* say

- Which lever(s) to implement — owner decision.
- Whether a **combination** works (e.g. `escape_gap_bounded` at a
  looser bound + `sites_across_settlements` to redistribute + a density
  floor from `settlements_scaled`). Not evaluated per the packet.
- What the right bound is — the sweep shows the trade (tighter bound →
  better gate, worse density/backtrack) but does not pick a point.

---

**Stop condition reached (`PHASE_C3_2_5_LEVER_MATRIX.md` §7).** The
matrix, `lever_matrix.json`, the per-lever interpretations and the
falsified list are committed. Next gate: owner reviews and decides
which, if any, lever deserves an implementation spec.

---

# Gate 8 — distributed investigation (the combination experiment)

`tools/scale_report.py --gate8`, **250 seeds/depth**, all 10 mechanisms
rotated. Raw: `tools/gate8_matrix.json`. Spec + acceptance:
`docs/PHASE_C3_2_5_GATE8_SPEC.md`. **Measurement-only — baseline
byte-identical (C.1 golden fixture passes); nothing shipped.**

The hypothesis (owner verdict on the lever matrix): **lever 4
(distributed investigation) + lever 2's mechanism as a *ceiling* on
pathological separation** — the escape gap kept within a bound that
grows with the map's *linear* dimension (`k·√playable`), not its area —
**+ lever 1 as a density-floor guard** (`+setts` rows). Lever 3
retired. The gap bound swept in both forms; **no value picked in
advance**.

Each cell: `ratio p90` (circuit p90 / 32 — the gate, < 1) · `mean p50`
(`meaningful_fraction` — share of the required journey spent within 3
tiles of a story site / settlement, vs dead wilderness) · `r→o`
(`require→obstacle` p90) · **`s→req`** (`spawn→require` p90 — the leg
lever 4 shifts the walking *onto*) · `dst/1k` · `btrk` (backtrack p90).

| variant | d0 | d3 | d4 | d6 | d9 | d12 |
|---|---|---|---|---|---|---|
| **baseline** | 0.69·0.94·12·9·5.0·.07 | 1.09·0.67·21·17·0.91·.04 | 1.06·0.66·24·17·0.88·.03 | 1.31·0.55·30·23·0.50·.03 | 1.34·0.55·30·26·0.34·.03 | **1.53·0.54·31·30·0.29·.05** |
| **distributed@√0.6** | 0.59·1.00·8·11·4.6·.10 | 0.91·0.78·12·17·0.78·.06 | 0.97·0.74·14·18·0.58·.04 | 1.22·0.68·17·25·0.29·.04 | 1.31·0.69·18·27·0.21·.06 | **1.34·0.68·18·29·0.17·.10** |
| distributed@√0.8 | 0.66·1.00·10·11·4.8·.07 | 1.09·0.72·16·20·0.93·.04 | 1.16·0.68·18·21·0.96·.03 | 1.41·0.63·21·28·0.46·.03 | 1.53·0.60·23·29·0.33·.06 | 1.50·0.62·23·30·0.20·.06 |
| distributed@√1.0 | 0.75·0.91·13·11·5.5·.05 | 1.25·0.65·21·21·1.21·.03 | 1.28·0.64·22·24·1.16·.03 | 1.59·0.59·27·31·0.64·.02 | 1.56·0.56·27·31·0.49·.03 | 1.75·0.58·27·32·0.34·.03 |
| **distributed@cap16** | 0.84·0.81·16·11·5.7·.04 | 1.03·0.73·15·18·0.95·.05 | 1.00·0.72·15·18·0.68·.04 | 1.12·0.73·16·24·0.33·.05 | 1.25·0.71·16·27·0.21·.09 | **1.31·0.74·17·29·0.15·.09** |
| distributed@cap20 | 0.91·0.80·17·12·5.8·.04 | 1.16·0.67·18·21·1.17·.03 | 1.16·0.68·18·21·0.96·.03 | 1.25·0.65·19·25·0.40·.04 | 1.34·0.64·20·28·0.25·.07 | 1.44·0.64·20·30·0.19·.07 |
| distributed@cap24 | 0.91·0.80·17·12·5.8·.04 | 1.31·0.62·23·21·1.32·.03 | 1.25·0.65·21·23·1.14·.03 | 1.38·0.59·22·26·0.50·.03 | 1.56·0.59·22·28·0.31·.04 | 1.50·0.60·23·31·0.24·.04 |
| distributed+setts@√0.8 | 0.66·1.00·10·11·4.8·.07 | 1.00·0.79·15·20·1.50·.03 | 1.12·0.69·17·21·1.20·.03 | 1.34·0.69·21·28·0.71·.03 | 1.47·0.61·23·29·0.39·.06 | 1.47·0.64·23·29·0.22·.07 |
| distributed+setts@√1.0 | 0.75·0.91·13·11·5.5·.05 | 1.12·0.73·18·21·2.04·.03 | 1.28·0.67·21·24·1.41·.03 | 1.44·0.68·19·31·0.92·.02 | 1.56·0.58·23·31·0.62·.03 | 1.72·0.61·27·32·0.44·.04 |

## Verdict — §5 acceptance: **NONE PASS. Hypothesis FALSIFIED (§6, path 1).**

`tools/scale_report.py --gate8` scores every variant against
`GATE8_SPEC.md` §5 mechanically. **Passing variant(s): NONE.** No swept
bound — relational or flat, with or without the density floor — gets
`ratio p90 < 1` at the supported depths (0–12, *not* redefined after
the fact).

### The wash-out is confirmed, and it is the whole story

Read `r→o` against `s→req`:

- baseline d12: `require→obstacle` 31, `spawn→require` 30.
- `distributed@√0.6` d12: `require→obstacle` drops to **18** — the gap
  ceiling is doing exactly what it should — but `spawn→require` stays
  at **29**, and `ratio p90` only falls 1.53 → 1.34, *still far over 1*.
- `distributed@√1.0` d6: `spawn→require` **rises** to 31 (baseline 23).

Lever 4's `_staging` places `require` toward the route→exit midpoint.
That midpoint is *farther from spawn*. So the combination moves the
walking off `require→obstacle` and onto `spawn→require` — **net zero on
the circuit**, precisely the lever-matrix finding, now reproduced with
the ceiling added. The ceiling shortens one leg; the greedy circuit
lengthens another.

### `meaningful_fraction` rose — but by shrinking the footprint, not filling the world

The distributed variants *do* lift `mean p50` at deep depths (d12:
0.54 → 0.68 at √0.6, 0.74 at cap16) — but never to the §5 bar (0.79 =
d0 − 0.15), and they do it while `dst/1k` **falls below baseline**
(0.29 → 0.15–0.20). That is the "nicer shirt": a larger *fraction* of a
*smaller* required journey sits near content, while the rest of the
34² world gets emptier. The `+setts` density floor holds `dst/1k` at or
above baseline for the √1.0 cases (d12 0.44) but √1.0 is the worst gate
result (1.72) — density and gate move in opposite directions.

### What did move: the front of the campaign

`√0.6` and `cap16` clear the gate cleanly through **depth 4**
(0.91–1.03) and are borderline at depth 6 (1.12–1.22). Distributed
investigation makes expeditions ~0–5 more viable. It does **nothing
structural for 6–12** — every variant is ≥ 1.25 by depth 9.

### Falsified

> **Distributing the existing required nodes across geography — even
> with a relational ceiling on the escape gap and a settlement density
> floor — does not keep the required circuit within the survival budget
> as the world scales.** The node *count* and node *spacing* are not
> the free variables that fix depths 6–12. Rearranging a fixed amount
> of story structure inside a 5×-larger world reaches its limit around
> depth 4–6.

### Where the evidence now points (next hypothesis — not built)

The amount of **story-bearing geography itself must scale with world
size**, not just its arrangement. Candidate next experiments, in the
same discipline (measure → falsify → controlled experiment → implement
only on evidence):

1. **A mid-journey *required* beat whose count scales with `map_size`**
   — e.g. one additional required site per ~N tiles of linear growth,
   so the required circuit gains genuine intermediate structure instead
   of one longer wilderness leg. This is the "world does more work"
   reading of lever 4, done properly.
2. **Formally bound "supported depth" to 0–N** (the data suggests N ≈
   5–6) and make expeditions past N explicitly inherited-supply-balanced
   *by design* — a campaign-structure decision, made *after* seeing this
   result, not a redefinition to rescue a failing experiment.
3. Some combination: scale story structure through ~depth 6, accept
   inheritance-balanced past it.

---

# Scaled investigation structure (C.3.2a-6)

`tools/scale_report.py --gate6`, **250 seeds/depth**, all 10 mechanisms
rotated. Raw: `tools/gate6_matrix.json`. Spec:
`docs/PHASE_C3_2_6_SPEC.md`. **Measurement-only — baseline
byte-identical (C.1 golden fixture passes); nothing shipped.**

The hypothesis (post-Gate-8): *what if the story itself grows with the
world?* A `_lever_scaled_beats` flag (default off) inserts `k = f(map)`
genuine intermediate required beats — each an on-spine stop
(`spawn→route→obstacle`) that withholds the next required site's
location, ≥3 tiles from every other site, near-zero detour. Scaling
form swept: `fixed@1/2` (controls) · `log` · `sqrt` · `linear`.

Each cell: `ratio p90` (gate, < 1) · `mean p50` (`meaningful_fraction`)
· `nodes` (required story nodes p50) · `n/√` (nodes / √playable —
reported raw, not targeted) · `r→o` (`require→obstacle` p90) · `btrk`.

| variant | d0 | d3 | d4 | d6 | d9 | d12 |
|---|---|---|---|---|---|---|
| **baseline** | 0.69·0.94·2·31·.07 | 1.09·0.67·2·21·.04 | 1.06·0.66·2·24·.03 | 1.31·0.55·2·30·.03 | 1.34·0.55·2·30·.03 | **1.53·0.54·2·31·.05** |
| fixed@1 | 0.78·0.95·3·31·.10 | 1.19·0.74·3·21·.06 | 1.16·0.74·3·24·.04 | 1.44·0.65·3·30·.04 | 1.50·0.65·3·30·.04 | 1.69·0.63·3·31·.07 |
| fixed@2 | —·—·4·— | 1.28·0.75·4·— | 1.25·0.75·4·— | 1.53·0.70·4·— | 1.56·0.70·4·— | 1.72·0.69·4·31·.08 |
| **sqrt@1** | 0.69·0.94·2·31·.07 | 1.22·0.78·4·21·.08 | 1.19·0.78·4·24·.06 | 1.50·0.75·5·30·.07 | 1.59·0.74·5·30·.09 | **1.75·0.74·5·31·.08** |
| sqrt@1.5 | 0.69·0.94·2·— | 1.22·0.78·4·— | 1.25·0.80·5·— | 1.62·0.76·6·— | 1.66·0.76·6·— | 1.81·0.76·6·31·.10 |
| linear@1 | 0.69·0.94·2·— | 1.22·0.78·4·— | 1.19·0.78·4·— | 1.50·0.75·5·— | 1.59·0.74·5·— | 1.75·0.74·5·31·.08 |
| linear@1.5 | 0.69·0.94·2·— | 1.22·0.78·4·— | 1.25·0.80·5·— | 1.62·0.76·6·— | 1.66·0.76·6·— | 1.81·0.76·6·31·.10 |

(`log@1.5/2` ≈ `fixed@2` — `log2(34/15) ≈ 1.2`, so `k` saturates at
3–4 by depth 3. `infeasible = 0 %` for every variant at every depth.
`dst/1k` unchanged from baseline — beats land in the existing
settlement, so they don't move settlement density.)

## Verdict — §7: **NONE PASS. §8 falsified, path 1.**

`--gate6` scores every form against `GATE6_SPEC` §7 mechanically. **No
scaled form passes. No fixed control passes.** And the reason is
structural, not a tuning miss:

### The two problems are orthogonal — and beats pull them opposite ways

| | baseline d0 → d12 | `sqrt@1` d0 → d12 |
|---|---|---|
| `meaningful_fraction` | **0.94 → 0.54** (collapses) | **0.94 → 0.74** (nearly held) |
| `ratio p90` | 1.53 (over budget) | **1.75** (*further* over) |
| required circuit p90 | 49 tiles | 56 tiles |

**Scaled beats do exactly what the hypothesis wanted for the *emptiness*
problem** — `meaningful_fraction` stops collapsing; `sqrt@1` holds it at
~0.74–0.78 at every depth instead of sliding to 0.54. `nodes / √playable`
stays flat at ~0.16, so the scaling function tracks map size as designed.

**But every required beat is more required walking, and the survival
budget counts tiles, not meaning.** `require→obstacle` is untouched (the
beats sit on the `spawn→route` spine, correctly), yet the total circuit
grows ~2–4 tiles per beat, `ratio p90` rises uniformly from depth 1 up,
and backtrack ticks to 0.08–0.10 (k on-spine stops can't stay perfectly
collinear). **The scaling *form* is irrelevant** — `fixed`, `log`,
`sqrt`, `linear` all fail the same way, because the *sign* is wrong:
adding required structure can only lengthen the required circuit, never
shorten it.

### Falsified — and now three experiments converge

> **The required circuit cannot be made to fit a fixed survival budget
> as the map grows.** Rearranging fixed nodes buys viability to depth
> ~4–6 (Gate 8). Adding scaled nodes fixes emptiness but *worsens*
> viability (this experiment). Shrinking the map and clustering on
> spawn are both forbidden. There is no content-side lever left.

**C.3.2a-5 / Gate 8 / C.3.2a-6 have jointly established that the
survival envelope itself is the wall at deep campaign depth.** The
remaining move is a **campaign-design decision**, made on this evidence:

> **Formally bound "supported depth" to 0–N.** The baseline `ratio p90`
> crosses 1.0 at depth ~2–3 and 1.3 by depth 6; distributed
> investigation (Gate 8) held it under 1.0 through depth 4. **N ≈ 5–6.**
> Expeditions past N are a deliberately different format —
> inherited-supply-balanced, authored escalation, or a distinct
> late-game mode — *not* procedurally-equivalent survival runs. This is
> `ROADMAP_STATUS.md`'s "is a 25-expedition campaign supposed to have
> 25 procedurally-equivalent survival expeditions?" answered: **no.**

### Keep as an option, decoupled: `_lever_scaled_beats` for emptiness

The flag genuinely fixes `meaningful_fraction`. At **shallow depth**,
where the circuit already fits the budget (`ratio p90 < 1` through
depth ~2 baseline, further with Gate-8 distribution), adding 1–2 beats
costs nothing in viability and makes the map feel occupied rather than
a large empty grid with a mystery in one corner. It is a **content /
texture lever for the 0–N range**, not a viability fix — the two
questions are now known to be separate. Whether to ship it there is its
own small decision, not part of the C.3.2a-5 viability line.

---

*Investigation only. No generator change shipped; all lever flags
default off; baseline byte-identical. Gate 8 and C.3.2a-6 are both
clean negative results on the content side — the valuable artifact is
the convergent falsification: the fix for deep-campaign viability is a
campaign-structure decision, not a generator lever.*
