# C.3.2a-5 — Gate 8 hypothesis + experiment spec

**Owner verdict recorded 2026-08-29.** This is the artifact the frozen
sequence calls for *after* the lever matrix and *before* any generator
change:

```
matrix  →  owner interpretation  →  chosen hypothesis (THIS DOC)
        →  a reviewed experiment  →  owner review  →  implementation spec
        →  implementation  →  fresh-survivor validation
```

**This doc does NOT authorise a generator change.** It defines the
hypothesis, says exactly what "lever 4 + bounded separation" means,
what gets measured, and what would falsify it. Implementation is a
later, separately-reviewed spec.

---

## 1. The owner's reading of the matrix

The matrix did what it was designed to do: it did not hand us a winning
lever, it handed us **the shape of the design problem**. The clean
decomposition from `SCALE_REPORT.md § Lever matrix`:

| lever | what it actually told us | disposition |
|---|---|---|
| **1 — settlements ∝ area** | adds destinations, does not shorten the required circuit (`require→obstacle` 31→30 at d12; `ratio p90` unmoved) | **not a primary fix.** Density ≠ topology. May return later *if settlements become gameplay infrastructure in their own right* — not as a circuit fix. |
| **2 — bounded escape gap** | the only lever that touches the mechanism — decouples `require→obstacle` from map size — but tight bounds distort geography: `dst/1k` collapses below baseline ("nicer shirt"), backtrack ~2–4×, and even @8 misses the gate at d9–12 | **useful mechanism, wrong as a blunt target distance.** Keep the mechanism, change what it constrains (see §3). |
| **3 — town-distance cap** | `require→obstacle` moves **0**; `ratio p90` ≤ 0.19. The town is not on the required circuit | **RETIRED.** Falsified. Remove the flag path in a later cleanup; do not carry it into the Gate 8 experiment. |
| **4 — sites across settlements** | cleanly moves the target leg (`require→obstacle` 31→21) with **no backtrack penalty and no density penalty**, but the greedy circuit re-routes (`spawn→require` grows as `require→obstacle` shrinks) so the headline ratio washes out | **best structural ingredient.** It changes the *relationship* between story nodes and geography, which is what we actually want. |

### The deeper finding

The problem is **not** "not enough settlements", "the town gets too
far", or even "the escape is too far". It is:

> **The procedural world expands faster than the required story can
> meaningfully occupy it.**

At depth 0 the required story occupies a reasonable fraction of the
physical journey. At depth 12 the world is ~5× larger but the required
story has not gained proportionally more geographic *structure* — so
the player spends an increasing share of the survival budget traversing
space that is doing nothing for the investigation.

That is why lever 1 is revealing (more settlements ≠ more meaningful
geography) and why lever 4 is promising (it changes the story-node ↔
geography relationship).

---

## 2. The chosen hypothesis — "distributed investigation"

> **As the world grows, distribute the *required* story nodes across
> meaningful geography (lever 4 as the foundation), while preventing the
> investigation→escape separation from scaling without bound (lever 2's
> mechanism, applied as a bound on *pathological* separation — not as a
> target distance). Preserve large maps. Require the resulting topology
> to remain forward-progressing and low-backtrack.**

Three ingredients, in priority order:

### 2a. Primary — distributed investigation (lever 4 foundation)

> **At least one required investigation step occurs at a distinct
> settlement / staging location, so the investigation itself creates a
> geographically meaningful progression rather than staying clustered
> around spawn.**

This is a game-design improvement, not statistical manipulation: the
mystery *should* walk you somewhere. Lever 4's `_staging` placement is
the seed of this, but the matrix showed the greedy circuit re-routes
around it. The Gate 8 experiment must measure **what the re-route
actually does to the three-number matrix** when lever 4 is combined
with 2b — not lever 4 alone (already falsified for the headline gate).

### 2b. Secondary guardrail — bounded relational separation (lever 2 mechanism)

> **The escape gap must not become arbitrarily remote from the
> investigation endpoint *simply because the map became larger*.**

This is deliberately **not** "the escape must be 12 tiles away". The
distinction is the whole point of the experiment:

| blunt target (rejected) | relational bound (chosen) |
|---|---|
| `require→obstacle` ≈ N tiles, always | `require→obstacle` grows *sub-linearly* in `map_size` — the leg is allowed to grow, just not proportionally |
| designs the map with a ruler | preserves scaling; only clips the pathological tail |
| crashes density + backtrack at tight N | expected to leave density/backtrack near baseline at a loose bound |

Concretely, the experiment sweeps the *form* of the bound, not just its
value:

- **`ratio` form** — `require→obstacle ≤ k · sqrt(playable_tiles)` for
  `k` in a small sweep. Ties the leg to the *linear* dimension of the
  map, not its area, so a 34² map gets a longer leg than a 15² but not
  5× longer.
- **`cap` form** — `require→obstacle ≤ C` for `C` in `{16, 20, 24}` —
  the loose end of the matrix's sweep, retained only as a comparison
  baseline (the matrix already showed tight caps fail).
- The bound is applied the same way lever 2 already applies it (choose
  the reachable gap whose distance-to-investigation-centroid best fits
  the bound), so the code delta from the existing flag is small.

**Do not pick the form or the constant in this doc.** The experiment
reports each; the owner picks in the implementation-spec review.

### 2c. Density floor (lever 1, demoted to a guard — not a fix)

> **`dens` and `dst/1k` must not fall below baseline at the chosen
> combination.**

Lever 1 is *not* implemented as a circuit fix. It is available only as
a **floor**: if 2a+2b drive the circuit down but leave `dst/1k` below
baseline, a minimal `settlements_scaled` is layered in purely to hold
the density line, and the experiment reports whether that is needed.

---

## 3. The stronger north star — "meaningful geography"

The current spec measures `dens = sites / playable-tiles`. That is too
passive. The Gate 8 experiment adds a metric that captures what we are
actually trying to preserve:

> **`meaningful_fraction` — of the tiles on the player's required
> journey, what fraction are spent moving *between* meaningful
> story-bearing locations (route / require / require2 / power /
> obstacle / escape), versus traversing wilderness that carries no
> required beat?**

Operationally, on the required circuit
`spawn → {route, require, [require2], [power]} → obstacle → escape`:

```
meaningful_fraction =
    (sum of leg lengths where BOTH endpoints are story sites)
  / (total required-circuit length)
```

- baseline at depth 0: expected high (the story fills the journey).
- baseline at depth 12: expected low (long wilderness legs, esp.
  `require→obstacle` and `spawn→escape`).
- **the hypothesis passes only if `meaningful_fraction` at deep
  campaign depths moves materially back toward the depth-0 value** —
  i.e. the larger world *gained* proportional story structure, it did
  not just get a shorter mystery.

This is the metric that distinguishes a real fix from the
spawn-cluster-in-a-nicer-shirt failure the original spec warns about.
`dens` / `dst/1k` stay in the report as supporting diagnostics.

---

## 4. What the Gate 8 experiment measures

Reuse `tools/scale_report.py --levers` harness. **Two variants only:**

| id | flags | notes |
|---|---|---|
| `baseline` | all off | unchanged, byte-identical to `main` |
| `distributed` | `_lever_spread_sites = True` **and** `_lever_bound_gap` set to each swept form/value | lever 4 + the relational bound, together |

Optionally a third: `distributed + settlements_scaled` — run **only** if
`distributed` holds the gate but drops `dst/1k` below baseline (§2c).

Sweep of the bound (§2b): the `ratio` form at `k ∈ {0.6, 0.8, 1.0}` and
the `cap` form at `C ∈ {16, 20, 24}`. `_lever_cap_town_dist` is **not**
in this experiment — lever 3 is retired.

Depths: `0, 1, 2, 3, 4, 6, 9, 12`. **≥ 250 seeds/depth**, all 10
mechanisms rotated (same harness as the matrix).

Per (variant, depth) cell, report:

- **required circuit p50 / p90** (tiles)
- **`ratio p90`** = circuit p90 / `USABLE_BUDGET` (32) — the gate
- **% over budget**
- **`require → obstacle` p50 / p90** — the leg
- **`spawn → require` p50 / p90** — to see the re-route lever 4 caused
- **`meaningful_fraction` p50** — the new north-star metric (§3)
- **backtrack proportion p50 / p90** — quality gate
- **`dens`, `dst/1k`** — density diagnostics
- **`infeasible` %** — must stay 0

Output, same as the matrix:
1. `tools/gate8_matrix.json` — machine-readable.
2. `SCALE_REPORT.md § Gate 8 — distributed investigation` — the table +
   a 2–4 sentence read per swept cell.
3. An explicit **pass / fail against §5** with the reasoning.

---

## 5. Acceptance — what "the hypothesis is confirmed" means

The `distributed` variant, at some single swept bound value, must
achieve **all** of:

1. **Gate:** `ratio p90 < 1` at every **supported** depth. "Supported"
   is still a decision — if the owner rules depths 9–12 are balanced
   around inherited supplies, the gate applies to 0–N and the doc says
   so. Default assumption for this experiment: supported = 0–12.
2. **Meaningful geography:** `meaningful_fraction` p50 at depths 9–12
   rises to within ~0.15 of the depth-0 baseline value (i.e. the deep
   world regained story structure, it didn't just shrink the mystery).
3. **Density held:** `dens` and `dst/1k` at depths 9–12 are **≥
   baseline** (with or without the §2c floor — the report says which).
4. **Backtrack held:** backtrack p90 stays ≤ ~1.5× baseline
   (baseline ≈ 0.03–0.07). Any approach to lever-2's tight-bound
   backtrack blow-up (0.09–0.13) is a fail for that cell.
5. **`infeasible` = 0 %** at every depth.
6. **v1 byte-identity** holds with all flags off (C.1 golden fixture).

## 6. What would falsify the hypothesis

- **No swept bound satisfies §5 simultaneously** — e.g. every cell that
  passes the gate fails `meaningful_fraction` or density. → distributed
  investigation is not sufficient; the problem is more structural
  (candidate next hypotheses: a mid-journey *required* beat generated
  proportional to map size; or accept that deep campaigns are
  inherited-supply-balanced and formally bound "supported" to 0–N).
- **Lever 4 + bound passes the gate only by the circuit re-routing
  through a shorter `spawn→require`** while `meaningful_fraction` does
  not move — that is the wash-out the matrix already saw, now hidden
  behind a passing ratio. Explicitly checked via the `spawn→require`
  column.
- **The `ratio` (sub-linear) form behaves no differently from the
  `cap` form** — would mean "relational" bought us nothing over a flat
  cap, and we are back to designing with a ruler.

## 7. Hard constraints (unchanged from the matrix packet)

- Nothing here touches combat / hunger / thirst / loot / survivor power
  / **map growth**. The world-generation / content network carries the
  burden.
- Lever flags default **off**; baseline stays byte-identical. No lever
  becomes a default in this experiment. Nothing ships.
- Lever 3 (`_lever_cap_town_dist`) is retired — not exercised here; a
  later cleanup removes its wiring in `generator.py`.
- Measurement only. The stop condition is `gate8_matrix.json` + the
  `SCALE_REPORT.md` block + the pass/fail analysis committed. Then the
  owner reviews and, only if §5 is met, an **implementation spec** is
  written.

## 8. Note on tooling (Atlas)

This experiment is code in `tools/scale_report.py` (harness extension:
the new `meaningful_fraction` metric, the combined-flag sweep) and a
2-line class-attr change pattern already present in `src/game.py`. Per
`docs/ATLAS_CAPABILITY_LOG.md`, `scale_report.py` is a procedural
metrics harness well past Atlas's reliable ceiling on this repo, and
`escape.py` (where lever 2's `_carve_escape_pass` and lever 4's
`_staging` live, ~940 lines) is far past the large-file edit wall.
**The Gate 8 harness work is hand-written.** A capability todo for the
underlying gap ("Atlas cannot extend a procedural metrics/analysis
harness or edit the 900-line generator module") is filed in
`atlas-self`.

---

---

## STATUS — experiment RAN, hypothesis FALSIFIED (2026-08-30)

`tools/scale_report.py --gate8`, 250 seeds/depth, 10 mechanisms, depths
0–12. Raw: `tools/gate8_matrix.json`. Full table + interpretation:
`SCALE_REPORT.md § Gate 8`.

**§5 verdict: no variant passes.** No swept gap bound — `√0.6 / √0.8 /
√1.0` relational or `cap 16 / 20 / 24`, with or without the `+setts`
density floor — gets `ratio p90 < 1` at depths 6–12. The loosest that
helps (`√0.6`, `cap16`) still sits at 1.31–1.34 at depth 12 and pays in
density (`dst/1k` 0.29 → 0.15–0.17) and backtrack.

**§6 falsification, path 1.** The `spawn→require` column confirms the
wash-out: the ceiling cuts `require→obstacle` (31 → 18) but lever 4's
staging placement lengthens `spawn→require` to compensate (stays ~29) —
net zero on the circuit. Distributing a *fixed* amount of story
structure inside a 5×-larger world runs out around depth 4–6.

**What did land:** the ending decision (Truth A, authored-canonical +
one final choice — `PHASE_A_DECISIONS.md`). And distributed
investigation cleanly clears the gate through **depth 4** — a real but
partial result.

**Next (owner gate):** pick the next hypothesis from `SCALE_REPORT.md §
Gate 8` "Where the evidence now points" — (1) story-structure count
that scales with `map_size`, (2) formally bound supported depth to
0–N ≈ 6, or (3) a combination. Then a new controlled experiment. **Not
a patched Gate 8.**

---

*Hypothesis + experiment spec. Nothing ships. Baseline byte-identical.
Implementation is a later, separately-reviewed spec — and only if §5 is
met.*
