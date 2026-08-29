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

## The accept/reject gate

C.3 v2 is **within the measured gameplay envelope** and violates none
of the `PHASE_C_FOUNDATION.md` §7 prohibitions. The remaining question
is the one only a human can answer:

> Play ~5 v2 expeditions (`Apocrysis(mapgen="v2")` / a debug flag).
> Does the irregular valley feel more like a real place — a valley you
> navigate — than the old rectangular board? Is the shorter trek an
> improvement or a loss? Do the dead-ends read as texture or as
> annoyance?

- **Accept** → flip `_default_mapgen` to `"v2"`, delete the v1 branch
  (or keep it one more phase as a fallback), freeze, then consider the
  fully-inverted pipeline as C.3.2.
- **Reject** → the default stays `"v1"`; v2 is either deleted or kept
  parked. No architecture was polluted to find out. That is a
  successful negative result.
- **Accept with changes** → tune the target size / dead-end rate /
  the no-mystery floor, re-measure, re-playtest.
