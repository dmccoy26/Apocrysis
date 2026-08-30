# Armor investigation — find / acquire / equip

`tools/armor_investigation.py` · 25 campaigns. See `docs/DESIGN_ESCAPE_MODEL.md` §3.

## A. Availability (analytical)

P(a successful `find_loot` roll resolves to armor), by tier and zone. Armor competes with 5 other base loot types; the rural/wilderness zones (early farmland maps) bias armor to **0.5×**, and `intelligence > 10` rewrites a further `int/100` of rolls to `weapon`.

| tier | rural | suburban | industrial | downtown | wilderness |
|---|---|---|---|---|---|
| 0 | 15.4% | 16.0% | 22.2% | 16.7% | 15.4% |
| 1 | 15.4% | 16.0% | 22.2% | 16.7% | 15.4% |
| 2 | 15.4% | 16.0% | 22.2% | 16.7% | 15.4% |
| 3 | 15.4% | 16.0% | 22.2% | 16.7% | 15.4% |
| 4 | 15.4% | 16.0% | 22.2% | 16.7% | 15.4% |
| 6 | 15.4% | 16.0% | 22.2% | 16.7% | 15.4% |
| 8 | 15.4% | 16.0% | 22.2% | 16.7% | 15.4% |

**Reduction given a drop** (uniform over eligible `ARMOR_TABLE`):

| tier | eligible pieces | mean reduction | P(reduction = 1) | P(reduction ≥ 3) | best |
|---|---|---|---|---|---|
| 0 | 4 | 1.25 | 75% | 0% | 2 |
| 1 | 4 | 1.25 | 75% | 0% | 2 |
| 2 | 4 | 1.25 | 75% | 0% | 2 |
| 3 | 7 | 1.86 | 43% | 14% | 4 |
| 4 | 8 | 2.00 | 38% | 25% | 4 |
| 6 | 9 | 2.44 | 33% | 33% | 6 |
| 8 | 9 | 2.44 | 33% | 33% | 6 |

## B + C. Acquisition + equipping (simulated)

| tier | n | reduction found / exp (med) | owned (med) | equipped (med) | slots (med) | int (med) |
|---|---|---|---|---|---|---|
| 0 | 30 | 0.0 | 0.0 | 0.0 | 0.0 | 10 |
| 1 | 31 | 0.0 | 0.0 | 0.0 | 0.0 | 11 |
| 2 | 33 | 0.0 | 0.0 | 0.0 | 0.0 | 12 |
| 3 | 33 | 0.0 | 0.0 | 0.0 | 0.0 | 13 |
| 4 | 42 | 0.0 | 0.0 | 0.0 | 1.0 | 13 |
| 5 | 57 | 0.0 | 1.0 | 1.0 | 1.0 | 18 |
| 6 | 60 | 0.0 | 2.0 | 2.0 | 2.0 | 18 |
| 7 | 82 | 0.0 | 4.0 | 2.0 | 2.0 | 19 |
| 8 | 79 | 0.0 | 5.0 | 2.0 | 2.0 | 19 |
| 9 | 79 | 0.0 | 6.0 | 2.0 | 3.0 | 19 |
| 10 | 40 | 0.0 | 6.0 | 4.0 | 3.0 | 20 |
| 11 | 44 | 0.0 | 5.0 | 2.0 | 3.0 | 20 |
| 12 | 38 | 0.0 | 5.0 | 0.0 | 3.0 | 20 |
| 13 | 35 | 0.0 | 8.0 | 0.0 | 3.0 | 21 |
| 14 | 25 | 0.0 | 8.0 | 0.0 | 4.0 | 21 |
| 15 | 6 | 0.0 | 8.0 | 0.0 | 4.0 | 21 |
| 16 | 15 | 0.0 | 7.0 | 0.0 | 2.0 | 21 |
| 17 | 2 | 0.0 | 8.0 | 0.0 | 4.0 | 22 |
| 18 | 2 | 0.0 | 8.0 | 0.0 | 4.0 | 22 |
| 19 | 4 | 0.0 | 8.0 | 0.0 | 4.0 | 22 |
| 20 | 8 | 0.0 | 8.0 | 0.0 | 4.0 | 22 |

## Diagnosis

```
A (availability): post-change, a rural loot roll becomes armor ~15% of the time — at parity with the other zones (the 0.5× penalty and the int>10→weapon override are removed).
  B/C (accumulation): OWNED reduction reaches ~0 by T3–5 and ~3 by T6–7 (cumulative via inheritance). EQUIPPED tracks it (~0 / ~2).
  Late equip gap (T9–14): owned − equipped ≈ 5.0 — inherited armor not re-equipped after a death (interaction-inference: auto-equip best armor on spawn; separate).

  → Acquisition was the bottleneck; the rural un-nerf + removing the int→weapon override lifts the accumulation curve without touching ARMOR_TABLE. The regression anchor (difficulty_ramp.py) is the acceptance test: Heavy at T2–5 should be winnable-or-evadable while the T2 Armored stays P(win) ~0%.
```

## Design constraint (from `DESIGN_ESCAPE_MODEL.md` / the DDR)

Whatever the fix, it must **not** make early armor strong enough to solve the T2 Armored. The target stays: T0–1 little armor / T2 Armored → evade / T3–5 armor makes a **Heavy** survivable / T6+ Armored becomes a costly *possible* fight. Regression anchor: `T2 Armored + best plausible early armor → P(win) ~0%` (check with `tools/difficulty_ramp.py`).
