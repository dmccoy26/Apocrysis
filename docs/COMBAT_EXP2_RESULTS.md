# Combat Experiment 2 — forecast calibration

`tools/forecast_calibration.py` · 1728 cells · 3000 sims/cell. See `docs/COMBAT_MODEL_EXPERIMENTS.md`.

**The question:** does the card describe the actual distribution of outcomes well enough for the player to make the intended decision? The confusion matrices group every simulated cell by its forecast label and show the spread of what actually wears that label.

## Current forecast — `threat_tier(P(win))` only

| tier | n | P(win) range | P(win) median | p90 loss median | p90 loss range |
|---|---|---|---|---|---|
| LOW | 1150 | 85–100% | 100% | 27% | 2–96% |
| MODERATE | 42 | 60–84% | 73% | 94% | 72–99% |
| HIGH | 35 | 35–58% | 43% | 94% | 87–99% |
| SEVERE | 28 | 16–34% | 26% | 96% | 85–99% |
| EXTREME | 473 | 0–13% | 0% | 94% | 68–100% |

**647 of 1728 cells break their label's promise.** The failure mode is uniform: a tier is assigned purely on P(win), so a reliably-won fight is `LOW` no matter what it costs.

Worst offenders (LOW / "overkill" over a huge cost):

| cell | card | win% | p50 loss | p90 loss |
|---|---|---|---|---|
| Iron Axe (16) vs Heavy L2 none/fresh | MODERATE / "well suited to this target" | 60 | 82% | 99% |
| Starter (6) vs Elite Regular L6 light/worn | MODERATE / "well suited to this target" | 68 | 83% | 98% |
| Chipped Sword (12) vs Heavy L6 light/fresh | MODERATE / "well suited to this target" | 76 | 78% | 98% |
| Iron Axe (16) vs Heavy L6 light/worn | MODERATE / "well suited to this target" | 76 | 78% | 98% |
| Starter (6) vs Elite Regular L3 light/fresh | MODERATE / "well suited to this target" | 61 | 85% | 98% |
| Iron Axe (16) vs Heavy L2 light/fresh | MODERATE / "well suited to this target" | 71 | 92% | 98% |
| Chipped Sword (12) vs Heavy L4 kevlar/fresh | MODERATE / "well suited to this target" | 61 | 66% | 97% |
| Starter (6) vs Heavy L10 light/fresh | MODERATE / "well suited to this target" | 62 | 81% | 97% |
| Starter (6) vs Elite Regular L4 none/fresh | MODERATE / "well suited to this target" | 71 | 70% | 97% |
| Rusty Dagger (8) vs Elite Regular L4 none/worn | MODERATE / "well suited to this target" | 65 | 83% | 97% |
| Rusty Dagger (8) vs Elite Regular L3 light/fresh | LOW / "overkill for this target" | 88 | 79% | 96% |
| Iron Axe (16) vs Heavy L3 none/fresh | MODERATE / "well suited to this target" | 73 | 80% | 96% |

## Proposed forecast — two axes

`tier = f(P(win), cost-of-winning)` where cost is the p90 HP-loss fraction. A likely win that is expensive is no longer `LOW` — it becomes `MODERATE` ("you'll win, but it'll cost you") or `HIGH` ("likely win — and likely near death").

| tier | n | P(win) range | P(win) median | p90 loss median | p90 loss range |
|---|---|---|---|---|---|
| LOW | 445 | 100–100% | 100% | 12% | 2–19% |
| MODERATE | 404 | 100–100% | 100% | 31% | 20–45% |
| HIGH | 378 | 35–100% | 100% | 70% | 45–99% |
| SEVERE | 28 | 16–34% | 26% | 96% | 85–99% |
| EXTREME | 473 | 0–13% | 0% | 94% | 68–100% |

The proposed tiers are tighter: within each label the P(win) *and* the p90-loss ranges are narrower and match the promise. This is the change to make in `combat_forecast` **before** the attention hierarchy consumes the forecast.

## Escape %

`combat_forecast.escape_pct` returns a flat `50%` for every zombie — `round(100 * _FLEE_CHANCE)`, `_FLEE_CHANCE = 0.50`. There is no per-zombie escape estimate to calibrate; the pass criterion "escape ~X% → flee succeeds ~X% for this zombie" cannot be evaluated because X does not vary. Making `escape_pct` a real function of `(zombie_speed_class, player_dex, fatigue, hp_frac)` is a **model** change (experiment 3 / the deferred escape-informed-by-threat work), not a calibration fix.

## Verdict

- The current forecast has a **category error**: it reports P(win) as if it were fight severity.
- The proposed two-axis derivation fixes it with no balance change — same simulation, richer label.
- `escape_pct` is not a forecast and needs the model, not calibration.
- Do the `threat_tier` / `weapon_verdict` rewrite before wiring `combat_forecast` into `DESIGN_ATTENTION_LANGUAGE.md`'s level derivation.
