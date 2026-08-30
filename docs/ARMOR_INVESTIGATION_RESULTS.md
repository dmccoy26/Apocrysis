# Armor investigation — find / acquire / equip

`tools/armor_investigation.py` · 25 campaigns. See `docs/DESIGN_ESCAPE_MODEL.md` §3.

## A. Availability (analytical)

P(a successful `find_loot` roll resolves to armor), by tier and zone. Armor competes with 5 other base loot types; the rural/wilderness zones (early farmland maps) bias armor to **0.5×**, and `intelligence > 10` rewrites a further `int/100` of rolls to `weapon`.

| tier | rural | suburban | industrial | downtown | wilderness |
|---|---|---|---|---|---|
| 0 | 8.0% | 14.7% | 20.3% | 17.6% | 8.0% |
| 1 | 8.0% | 14.7% | 20.3% | 17.6% | 8.0% |
| 2 | 8.0% | 14.7% | 20.3% | 17.6% | 8.0% |
| 3 | 8.0% | 14.7% | 20.3% | 17.6% | 8.0% |
| 4 | 8.0% | 14.7% | 20.3% | 17.6% | 8.0% |
| 6 | 8.0% | 14.7% | 20.3% | 17.6% | 8.0% |
| 8 | 8.0% | 14.7% | 20.3% | 17.6% | 8.0% |

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
| 0 | 32 | 0.0 | 0.0 | 0.0 | 0.0 | 10 |
| 1 | 31 | 0.0 | 0.0 | 0.0 | 0.0 | 11 |
| 2 | 34 | 0.0 | 0.0 | 0.0 | 0.0 | 12 |
| 3 | 38 | 0.0 | 0.0 | 0.0 | 0.0 | 13 |
| 4 | 42 | 0.0 | 1.0 | 1.0 | 1.0 | 13 |
| 5 | 55 | 0.0 | 1.0 | 1.0 | 1.0 | 18 |
| 6 | 47 | 0.0 | 1.0 | 1.0 | 1.0 | 18 |
| 7 | 83 | 0.0 | 2.0 | 2.0 | 1.0 | 19 |
| 8 | 103 | 0.0 | 2.0 | 0.0 | 2.0 | 19 |
| 9 | 41 | 0.0 | 5.0 | 2.0 | 2.0 | 19 |
| 10 | 44 | 0.0 | 6.0 | 2.0 | 3.0 | 20 |
| 11 | 42 | 0.0 | 3.0 | 0.0 | 3.0 | 20 |
| 12 | 31 | 0.0 | 3.0 | 0.0 | 3.0 | 20 |
| 13 | 39 | 0.0 | 2.0 | 0.0 | 3.0 | 21 |
| 14 | 23 | 0.0 | 2.0 | 0.0 | 3.0 | 21 |
| 15 | 11 | 0.0 | 2.0 | 0.0 | 4.0 | 21 |
| 16 | 1 | 1.0 | 3.0 | 0.0 | 4.0 | 21 |
| 17 | 8 | 0.0 | 3.0 | 0.0 | 4.0 | 21 |

## Diagnosis

```
A (availability): a loot roll at T2 in a rural zone becomes armor ~8.0% of the time — armor is the RAREST of ~6 loot types there (bias 0.5×), and the int>10 rule converts more rolls to weapons.
  B (acquisition):  early tiers find a median of 0.0 total reduction-points of armor per expedition.
  C (equipping):    of 0.0 owned reduction, 0.0 is worn — equip gap 0.0 (negligible — the bot equips what it finds; NOT the bottleneck)

  → PRIMARY BOTTLENECK: ACQUISITION. The pieces barely drop. Even with perfect equipping the early survivor can't assemble a loadout. The lever is find_loot's armor weight / the zone bias / the int>10->weapon override — NOT the ARMOR_TABLE min_expedition bands (T0 armor is already available, it just doesn't appear).
```

## Design constraint (from `DESIGN_ESCAPE_MODEL.md` / the DDR)

Whatever the fix, it must **not** make early armor strong enough to solve the T2 Armored. The target stays: T0–1 little armor / T2 Armored → evade / T3–5 armor makes a **Heavy** survivable / T6+ Armored becomes a costly *possible* fight. Regression anchor: `T2 Armored + best plausible early armor → P(win) ~0%` (check with `tools/difficulty_ramp.py`).

## Candidate levers (measured, not yet chosen)

Acquisition is the bottleneck. The levers, all in `find_loot` /
composition, **none touching `ARMOR_TABLE` numbers or `min_expedition`
bands**:

1. **Raise armor's weight in the loot pool** — especially un-nerf the
   `rural` / `wilderness` `0.5×` bias. Early maps ("farmland and
   fields") are rural, so armor is at its rarest exactly when the
   player has none.
2. **Exempt armor from the `intelligence > 10 → weapon` override**, or
   soften it. It currently converts ~`int/100` of *all* rolls to
   weapons — and weapons are already over-abundant (the player ends
   run 7 with 4 unused ones).
3. **A near-guaranteed early body piece** — the first Padded Vest is
   an ~certain find in expedition 0–1, then normal rates. Gives every
   survivor a floor without changing the ceiling.
4. **Zone mix** — ensure early maps carry some `suburban` /
   `industrial` tiles (armor bias 0.9–1.6) rather than being uniformly
   rural.

Any one of 1–3 likely closes the T2–5 gap; they compound. The
regression anchor holds regardless: even a full early loadout is
reduction ≤ 2–4, which does **not** make the T2 Armored (120 HP, 0.5
damage reduction, 15 attack) winnable — check with
`tools/difficulty_ramp.py` after the change.

## Secondary finding — re-equip after a death

Tiers 11+ show `owned` reduction 2–3 but `equipped` 0. A survivor who
inherits a backpack with armor in it does not reliably end up wearing
it (bot behaviour; a human may also not think to). Small, separate
from the acquisition fix — likely interaction-inference territory
(auto-equip best available armor on spawn, same as the accepted
auto-equip-starting-weapon candidate in
`DESIGN_INTERACTION_INFERENCE.md`).
