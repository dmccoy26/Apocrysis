# Combat Experiment 3 — the difficulty ramp

`tools/difficulty_ramp.py` · 20 campaigns for the power curve · 2500 sims/cell. See `docs/COMBAT_MODEL_EXPERIMENTS.md`.

**Question:** at what expedition depth does the game first present a fight whose consequence exceeds the player's available means — with best realistic gear and no credible avoidance path?

## Realistic best-available gear by tier (median across campaigns)

| tier | level | best weapon dmg | best armor reduction | n |
|---|---|---|---|---|
| 0 | 1 | 6 | 0 | 23 |
| 1 | 2 | 20 | 0 | 25 |
| 2 | 3 | 23 | 0 | 23 |
| 3 | 3 | 23 | 0 | 26 |
| 4 | 4 | 26 | 0 | 51 |
| 5 | 5 | 26 | 1 | 42 |
| 6 | 6 | 26 | 2 | 52 |
| 7 | 6 | 26 | 4 | 66 |
| 8 | 6 | 26 | 6 | 58 |
| 9 | 7 | 26 | 6 | 55 |
| 10 | 7 | 26 | 6 | 33 |
| 11 | 7 | 26 | 6 | 35 |
| 12 | 8 | 26 | 6 | 32 |
| 13 | 8 | 26 | 6 | 28 |
| 14 | 8 | 26 | 6 | 21 |
| 15 | 8 | 26 | 4 | 12 |
| 16 | 9 | 26 | 4 | 12 |
| 17 | 9 | 26 | 6 | 8 |

## Per-tier worst credible encounter

Fight simulated with the tier's realistic gear, mid-expedition condition. `min P(die)` = the best the player can do: fight, or flee (flat 50%) then forced fight on failure.

| tier | zombie | spawn ~ | win% | p90 loss | current tier | proposed tier | P(die\|fight) | min P(die) |
|---|---|---|---|---|---|---|---|---|
| 0 | Regular | 26.0% | 98 | 80% | LOW | HIGH | 2% | 1% |
| 0 | Swift | 10.0% | 100 | 62% | LOW | HIGH | 0% | 0% |
| 0 | Fresh | 62.0% | 100 | 25% | LOW | MODERATE | 0% | 0% |
| 1 | Fresh | 56.8% | 100 | 7% | LOW | LOW | 0% | 0% |
| 1 | Regular | 24.9% | 100 | 29% | LOW | MODERATE | 0% | 0% |
| 1 | Swift | 10.5% | 100 | 16% | LOW | LOW | 0% | 0% |
| 2 | Armored | 4.0% | 0 | — | EXTREME | EXTREME | 100% | 50% |
| 2 | Heavy | 5.0% | 90 | 91% | LOW | HIGH | 10% | 5% |
| 2 | Fresh | 51.6% | 100 | 6% | LOW | LOW | 0% | 0% |
| 3 | Armored | 6.0% | 0 | — | EXTREME | EXTREME | 100% | 50% |
| 3 | Elite Armored | 0.5% | 0 | — | EXTREME | EXTREME | 100% | 50% |
| 3 | Elite Heavy | 0.7% | 0 | 87% | EXTREME | EXTREME | 100% | 50% |
| 4 | Elite Armored | 1.0% | 0 | — | EXTREME | EXTREME | 100% | 50% |
| 4 | Armored | 8.0% | 2 | 97% | EXTREME | EXTREME | 98% | 49% |
| 4 | Elite Heavy | 1.2% | 3 | 83% | EXTREME | EXTREME | 97% | 48% |
| 5 | Elite Armored | 1.5% | 0 | — | EXTREME | EXTREME | 100% | 50% |
| 5 | Armored | 10.0% | 5 | 99% | EXTREME | EXTREME | 95% | 48% |
| 5 | Elite Heavy | 1.9% | 11 | 99% | EXTREME | EXTREME | 89% | 44% |
| 6 | Elite Armored | 2.2% | 0 | — | EXTREME | EXTREME | 100% | 50% |
| 6 | Armored | 12.0% | 11 | 98% | EXTREME | EXTREME | 89% | 45% |
| 6 | Elite Heavy | 2.7% | 16 | 98% | SEVERE | SEVERE | 84% | 42% |
| 7 | Elite Armored | 2.9% | 0 | — | EXTREME | EXTREME | 100% | 50% |
| 7 | Armored | 14.0% | 13 | 94% | EXTREME | EXTREME | 87% | 44% |
| 7 | Elite Heavy | 3.7% | 16 | 93% | SEVERE | SEVERE | 84% | 42% |
| 8 | Elite Armored | 3.8% | 0 | — | EXTREME | EXTREME | 100% | 50% |
| 8 | Elite Heavy | 4.8% | 18 | 86% | SEVERE | SEVERE | 82% | 41% |
| 8 | Armored | 16.0% | 27 | 96% | SEVERE | SEVERE | 73% | 36% |
| 9 | Elite Armored | 4.9% | 0 | — | EXTREME | EXTREME | 100% | 50% |
| 9 | Elite Heavy | 6.1% | 36 | 82% | HIGH | HIGH | 64% | 32% |
| 9 | Armored | 18.0% | 39 | 99% | HIGH | HIGH | 61% | 30% |
| 10 | Elite Armored | 6.0% | 0 | — | EXTREME | EXTREME | 100% | 50% |
| 10 | Elite Heavy | 7.5% | 36 | 82% | HIGH | HIGH | 64% | 32% |
| 10 | Armored | 20.0% | 39 | 99% | HIGH | HIGH | 61% | 30% |
| 11 | Elite Armored | 6.0% | 0 | — | EXTREME | EXTREME | 100% | 50% |
| 11 | Elite Heavy | 7.5% | 36 | 82% | HIGH | HIGH | 64% | 32% |
| 11 | Armored | 20.0% | 39 | 99% | HIGH | HIGH | 61% | 30% |
| 12 | Elite Armored | 6.0% | 0 | — | EXTREME | EXTREME | 100% | 50% |
| 12 | Armored | 20.0% | 42 | 96% | HIGH | HIGH | 58% | 29% |
| 12 | Elite Heavy | 7.5% | 47 | 96% | HIGH | HIGH | 53% | 26% |
| 13 | Elite Armored | 6.0% | 0 | — | EXTREME | EXTREME | 100% | 50% |
| 13 | Armored | 20.0% | 42 | 96% | HIGH | HIGH | 58% | 29% |
| 13 | Elite Heavy | 7.5% | 47 | 96% | HIGH | HIGH | 53% | 26% |
| 14 | Elite Armored | 6.0% | 0 | — | EXTREME | EXTREME | 100% | 50% |
| 14 | Armored | 20.0% | 42 | 96% | HIGH | HIGH | 58% | 29% |
| 14 | Elite Heavy | 7.5% | 47 | 96% | HIGH | HIGH | 53% | 26% |
| 15 | Elite Armored | 6.0% | 0 | — | EXTREME | EXTREME | 100% | 50% |
| 15 | Armored | 20.0% | 31 | 97% | SEVERE | SEVERE | 69% | 34% |
| 15 | Elite Heavy | 7.5% | 35 | 83% | HIGH | HIGH | 65% | 32% |
| 16 | Elite Armored | 6.0% | 0 | — | EXTREME | EXTREME | 100% | 50% |
| 16 | Armored | 20.0% | 40 | 96% | HIGH | HIGH | 60% | 30% |
| 16 | Elite Heavy | 7.5% | 41 | 81% | HIGH | HIGH | 59% | 30% |
| 17 | Elite Armored | 6.0% | 0 | 98% | EXTREME | EXTREME | 100% | 50% |
| 17 | Elite Heavy | 7.5% | 54 | 94% | HIGH | HIGH | 46% | 23% |
| 17 | Armored | 20.0% | 58 | 96% | HIGH | HIGH | 42% | 21% |

## The first cliff

**Expedition tier 2.** A **Armored** (~4% of encounters at this tier) is proposed-**EXTREME** with the best gear a real campaign has by then (level 3, weapon 23 dmg, armor 0).

- Fighting: **100% death**.
- Best case (flee at flat 50%, else forced fight): **50% death**.
- **No credible avoidance path** — escape is a coin flip and failing it forces the fight. This is run 7's exp-3 Heavy, confirmed as the structural cliff, not bad luck.

## The design question

Is expedition 2 *supposed* to contain a "don't fight this" enemy?

- **YES** → the player needs a real escape / avoidance path: `escape_pct` must become a function of zombie speed / player dex (a slow Heavy should be very escapable), and/or the encounter should arrive with enough warning and open ground to run. A guaranteed-lethal forced fight is not a decision.

- **NO** → gate Heavy/Armored to a later tier, lift the loot band so armor actually develops (it currently medians 0 at the cliff), or soften the composition ramp before this tier.

## Note on the power curve

Armor reduction stays near 0 for most of the campaign (confirmed here and in `balance_autoplay`'s own comments). The player's only real combat-power axis is weapon damage, which plateaus ~20–26 around tier 3. So "best-available gear" past ~tier 3 barely improves — the ramp climbs, the counter-play doesn't.
