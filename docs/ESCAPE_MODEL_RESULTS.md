# Escape model — Phase-2 harness results

`tools/escape_model.py`. See `docs/DESIGN_ESCAPE_MODEL.md`.

## The model (one source of truth)

```
resolved = clamp(intrinsic × terrain_availability, 0.02, 0.97)
intrinsic = speed_base + dex_mod + fatigue_mod + hp_mod   (clamped 0.05–0.97)

speed_base    slow 0.88   normal 0.55   fast 0.24
dex_mod       (dex-10) × 0.012, capped ±0.12
fatigue_mod   0 / -0.08 (>50) / -0.15 (>80)
hp_mod        0 / -0.08 (<0.5) / -0.15 (<0.25)
terrain       open 1.0   reduced 0.6   confined 0.22
```

The flee roll is `random() < resolved`; `combat_forecast.escape_pct` is `round(100 * resolved)` on the same inputs. Never two formulas.

## R1–R6

| fixture | intrinsic | avail | resolved | pass | requirement |
|---|---|---|---|---|---|
| R1  Armored·healthy·rested·open | 0.90 | 1.00 | 0.90 | ✅ | resolved ≥ 0.75 (reliably high) |
| R2  Armored·wounded+fatigued·open | 0.74 | 1.00 | 0.74 | ✅ | materially below R1, still > 0.5 (best option) |
| R2x Armored·extreme(20%HP,90fat)·open | 0.60 | 1.00 | 0.60 | ✅ | below R2 (state keeps mattering) |
| R3  Swift·healthy·rested·open | 0.26 | 1.00 | 0.26 | ✅ | materially below the Armored (fast = hard to disengage) |
| R4  Armored·confined | 0.90 | 0.22 | 0.20 | ✅ | constrained — availability < 1, resolved low |
| R5  Dexterity 4 vs 20 (Regular·open) | — | — | lo 0.48 / hi 0.67 | ✅ | escape ↑ with Dex |
| R6  "don't fight" is a strategy not a coin flip | 0.90 | 1.00 | 0.90 | ✅ | R1 resolved materially above 0.50 (ideally 0.75–0.90) |

## §4a Monotonicity matrix

| variable (low → baseline → high) | values | pass |
|---|---|---|
| zombie speed  Swift → Regular → Armored | 0.26 → 0.57 → 0.90 | ✅ |
| Dexterity      4 → 12 → 20 | 0.48 → 0.57 → 0.67 | ✅ |
| fatigue        90 → 30 → 0   (rested = higher escape) | 0.42 → 0.57 → 0.57 | ✅ |
| HP fraction    0.2 → 0.6 → 1.0 | 0.42 → 0.57 → 0.57 | ✅ |
| terrain avail  confined → reduced → open | 0.13 → 0.34 → 0.57 | ✅ |

## §4b Bounded influence

`escape(slow, worst survivor state, open)` = **0.50**  >  `escape(fast, best survivor state, open)` = **0.36**  → ✅ zombie speed stays the dominant factor

## §5 Trust

Worst |empirical − predicted| flee rate over 9 (speed × terrain) cells, 200k trials each: **0.0025** ✅ — the roll and the forecast read the same number.

## Gate

Items 1–6: **PASS**. Item 7 (armor progression moved earlier, Armored still ~0% fight at T2) is a separate `tools/difficulty_ramp.py` check — pending the `ARMOR_TABLE` band change.

## What moves to `combat_mixin` when the gate is green

- `escape_probability(player, zombie, terrain)` — exactly this function, as the single source of truth
- zombie `speed_class` on the roster (`src/zombies.py`)
- the flee roll becomes `random() < escape_probability(...).resolved`
- `combat_forecast.escape_pct` becomes `round(100 * ...resolved)`
