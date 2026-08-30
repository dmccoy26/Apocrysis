# C.3.2a-5 — the lever A/B matrix (implementation packet)

Owner-frozen. This is an **experiment**, not a solution. Execute it,
document the matrix, and **stop at the review gate**.

> **Before Task 1:** if the existing implementation differs materially
> from the lever descriptions below, **do not reinterpret the design —
> stop and report the discrepancy for owner review.** This matters most
> for `escape_gap_bounded` and `sites_across_settlements`: they are
> structural enough that a locally "reasonable" reinterpretation would
> change what is being measured.

> **After the matrix:** do **not** write the implementation spec.
> The sequence is: matrix → human interpretation → chosen hypothesis →
> a new reviewed spec → implementation. The job is measurement only.

## 0. Implementation boundary (read first)

> You are implementing an experiment, not solving C.3.2a-5.
> - Do **not** choose the winning lever.
> - Do **not** combine levers.
> - Do **not** change the default generator.
> - Do **not** alter combat, hunger, thirst, loot, survivor progression,
>   `WorldFact`s, or investigation mechanics.
> - Do **not** "improve" a lever while implementing it.
> - If a lever needs a design choice not specified here, **stop and
>   report it** rather than silently choosing one.
> - Every variant is **independently switchable** and **leaves the
>   baseline byte-identical when disabled** (the C.1 golden fixture must
>   still pass with all flags off).

## 1. Context / finding

- C.3.2a-5 is a **distance-at-scale** problem, not "maps too empty" or
  "player can't navigate".
- Investigation sites (`route`, `require`) stay ~5–15 tiles from spawn
  at every campaign depth.
- **`require → obstacle` is the leg that grows** — p50 7 → 22 tiles
  across depths 0 → 12.
- `spawn → escape` grows p50 12 → 32. The escape gap is carved at *"the
  far corner"* (`escape.py` `_carve_escape_pass`).
- **Backtracking is currently ≈ 0** on every generated required circuit.
- `infeasible` (unreachable required node) is **0 %**.
- **v1 is and stays the production / default generator.** No gameplay
  balance changes.

Full data: `SCALE_REPORT.md`. Metric definitions + the frozen
four-lever set: `PHASE_C3_2_5_SPEC.md`.

## 2. Experimental contract

- Four independent generator variants, each a single class-level flag
  on `Apocrysis`, default off.
- **Baseline + exactly one lever at a time.** No combinations.
- **Same seeds, same depths, all 10 mechanisms rotated** for every
  variant — reuse `tools/scale_report.py`'s harness.
- Variants are **measurement-only**. Nothing ships. No default changes.
- No commit alters shipped generation behaviour: with every flag off,
  generation is byte-identical to `main`.

## 3. The five variants

| id | flag | what it does |
|---|---|---|
| `baseline` | (all off) | today's generator, unchanged |
| `settlements_scaled` | `_lever_settlements_by_area` | settlement **count** scales with map *area* (vs the 15² base), bypassing `MAX_SETTLEMENTS`; `SETTLEMENTS_PER_EXPEDITIONS` unchanged |
| `escape_gap_bounded` | `_lever_bound_gap = <int\|None>` | **primary.** The carved escape gap must sit within a **bounded traversable distance of the required-investigation endpoint** (the `require` site once known, else the nearest-3-building centroid), *independent of map dimensions*. **The bound is a sweep parameter** — run the variant at several bound values (e.g. 8, 12, 16, 20) and report each; do **not** pick one. |
| `town_distance_capped` | `_lever_cap_town_dist = <int\|None>` | `TOWN_DISTANCE_GROWTH_PER_LEVEL`'s effect on the settlement `min_distance` is capped at a fixed ceiling (sweep: 12, 16, 20). Falsification control — the town is not on the required circuit, so this is expected to move the gate little. |
| `sites_across_settlements` | `_lever_spread_sites` | at least one required site (`require` or `require2`) is placed in a **different settlement** from `route`, creating a staging point between the investigation and the escape — **without forcing a retrace** (measure backtrack). |

### Guardrail for `escape_gap_bounded`

Do **not** define it as "the obstacle must be within N tiles of
spawn" — that just swaps one hard-coded distance for another. Define it
**relationally**: bounded traversable distance between the escape gap
and the required-investigation endpoint, independent of `map_size`. Let
the sweep tell us which bound produces `ratio p90 < 1`.

## 4. Metrics (per variant, per depth, 10 mechanisms rotated)

Reuse `scale_report.py`. For every (variant, depth) cell report:

- `dens` — mystery sites / 1000 playable tiles
- `dst/1k` — distinct settlements a required site falls in, per 1000
  playable tiles
- **required circuit p50 / p90** (tiles)
- **`require → obstacle` p50 / p90** — the leg this experiment is
  actually trying to move
- **survival-budget ratio p90** = circuit p90 / `USABLE_BUDGET` (32)
- **% over budget**
- **backtrack proportion** p50 / p90
- **`infeasible` %**

Depths: `0, 1, 2, 3, 4, 6, 9, 12`. 250 seeds/depth minimum.

## 5. Experimental acceptance rules

- **The budget ratio (`ratio p90`) is the viability gate.** Target:
  `< 1` at the supported depths.
- **Density (`dens`, `dst/1k`) is a diagnostic.** A lever that drives
  the ratio under 1 while `dens` keeps falling has **not** passed — it
  shrank the mystery instead of filling the world.
- **Backtracking is a quality diagnostic.** Any rise from ≈ 0 is a
  meaningful regression even if the headline ratio improves. Flag it.
- **`infeasible` > 0 % is a regression.** Report and do not proceed
  with that lever/bound.
- **No combination** of levers is evaluated. Owner review only.

## 6. Required output

1. **Machine-readable raw results** — `tools/lever_matrix.json`
   (per variant → per depth → the metric dict).
2. **Human-readable comparison table** — appended to
   `SCALE_REPORT.md` under `## Lever matrix`, one block per variant,
   the same column layout as the existing v1 table, plus the
   `require → obstacle` column.
3. **Per-lever interpretation** — 2–4 sentences each: did the gate
   move, did density hold, did backtracking rise, at what bound.
4. **Explicit list of hypotheses falsified** — e.g. "lever 3
   (town-distance cap) moves `ratio p90` by ≤ 0.05 at every depth →
   the town-drift hypothesis is retired."
5. **No recommendation** on which lever(s) to implement or combine.

## 7. Stop condition

Claude stops after `lever_matrix.json` + the `SCALE_REPORT.md`
comparison block + the per-lever interpretations + the falsified list
are committed. No further C.3.2a-5 work.

## 8. Next human gate

Owner reviews the matrix and decides which, if any, lever deserves
implementation. Only then is an implementation spec written.

---

## STATUS — tasks 1–7 DONE (2026-08-29, commit `265dd80`)

The flags are built (`src/game.py` class attrs, default off; wired into
`generator.py` levers 1/3 and `escape.py` levers 2/4). The matrix ran
(220 seeds/depth, 10 mechanisms). Results:
`tools/lever_matrix.json` + `SCALE_REPORT.md` § "Lever matrix".

**Headline:** no single lever passes the gate.
- lever 3 (town-distance cap) **FALSIFIED** — retire it.
- lever 1 (settlements ∝ area) — density up, trek unmoved.
- lever 2 (escape-gap bound) — the only lever touching the mechanism;
  decouples `require→obstacle` from map size, but tight bounds crash
  `dst/1k` below baseline + double backtrack, and even @8 misses the
  gate at d9–12.
- lever 4 (sites across settlements) — clean redistribution of the leg
  (31→21) with no penalties, but the circuit re-routes so the headline
  ratio is unchanged.

**We are at gate 8: owner review.** Do NOT proceed to an implementation
spec until the owner picks a hypothesis (likely a combination — a
looser gap bound + lever 4 + a density floor — but that is the owner's
call).

## 9. Task sequence

1. Add the four flags to `Apocrysis` (class attrs, default off). Wire
   each into the generator / `escape.py` behind an `if getattr(self,
   flag, ...)` guard. **Verify the C.1 golden fixture still passes with
   all flags off.**
2. Unit-test each flag in isolation: enabled changes what it should,
   disabled leaves the relevant output identical to baseline.
3. Extend `scale_report.py` (or a sibling `lever_matrix.py`) to sweep
   `{baseline, settlements_scaled, escape_gap_bounded×{8,12,16,20},
   town_distance_capped×{12,16,20}, sites_across_settlements}` and emit
   `lever_matrix.json` + the tables.
4. Run it. Commit the JSON + the `SCALE_REPORT.md` block + the
   interpretations + the falsified list.
5. Stop. Ping the owner.

---

*Experiment packet. Nothing ships. Baseline stays byte-identical.*
