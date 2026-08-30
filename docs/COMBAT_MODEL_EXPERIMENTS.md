# Combat model — experiments

**Status:** experiment design. Deliberately **outside** the three
interface specs (`DESIGN_PASS.md`). These questions want **simulation**
(`tools/balance_autoplay.py` + instrumentation), not more blind
playtesting. No changes until the simulations run.

Two layers, kept separate:

```
COMBAT MODEL           what is actually happening in a fight?      ← exp 1
        ↓
COMBAT COMMUNICATION   does the forecast match the outcome?       ← exp 2
        ↓
DIFFICULTY RAMP        when does an unwinnable fight first appear? ← exp 3
```

## The failing cases to reproduce (from run 7)

| # | situation | forecast said | what happened |
|---|---|---|---|
| A | exp 1 t5: Regular Zombie, Screwdriver (6), L1, 100 HP | `LOW · Fight ~100% · overkill` | 100 → **14 HP**, burned all 3 medicine |
| B | exp 3 t9: Heavy Zombie, Chipped Sword (12), L3, no armor | `EXTREME · Fight ~11% · poorly suited` | dead in 5 rounds (20 dmg/hit) |

Case A is the poison: the forecast was **not wrong about winning** —
he won. It was wrong about **cost**. `threat_tier` and
`weapon_verdict` are pure functions of `P(win)`
(`src/combat_forecast.py`), and `P(win) ≈ 1` for a fight that nearly
killed him. Case B is arguably working-as-intended communication of a
model / ramp problem.

## Current model (as built) — the three things under test

From `src/combat_forecast.py`:

- `fight_pct` — Monte-Carlo of the real round loop. **Accurate about
  P(win).** Not the problem.
- `threat_tier(win_pct)` — buckets P(win): ≥85 LOW, ≥60 MODERATE,
  ≥35 HIGH, ≥15 SEVERE, else EXTREME. **Ignores cost entirely.**
- `weapon_verdict(win_pct)` — ≥85 "overkill", ≥60 "well suited",
  ≥35 "adequate but it'll cost you", else "poorly suited". **Also
  pure P(win).**
- `escape_pct` — `round(100 * _FLEE_CHANCE)` with `_FLEE_CHANCE = 0.50`,
  a **flat constant**. A Swift Zombie and a Heavy Zombie show the same
  escape %. Ignores zombie speed class, player dexterity, fatigue, HP.

> **Instrumentation note:** `combat_forecast._RNG` is a private
> `random.Random()` seeded from system entropy at import (it must not
> perturb the global stream the real fight uses). For experiment 2 to
> be reproducible, seed `_RNG` per trial. This is also the small
> non-determinism `tools/autoplay` papers over.

---

## Experiment 1 — cost of a fight, not just the outcome

**Question:** why does a "trivial" LOW encounter remove 86 HP?

**Simulate:** for each `(weapon, zombie_type, player_level, armor)`
cell across the realistic range, run N fights and record — **given a
win** — the distribution of HP lost: mean, p50, p90, worst case; plus
rounds-to-kill (TTK) and the zombie's damage-per-round output.

**Expected finding (hypothesis):** the Screwdriver (6 dmg) has a TTK
against a Regular Zombie (~30–40 HP + `damage_reduction`) of ~5–7
rounds; the zombie outputs ~10/round + a 15% bleed / 10% stun roll;
so expected loss ≈ 55–70 and p90 ≈ 90 **while `P(win)` stays ≈ 1.**

**Calibrated means:** a defined relationship between the weapon tier a
player *has* at an expedition depth and the p90 HP cost of the fights
that depth throws at them. "The intended early game" is a design
choice — but it should be a *chosen* number, not an emergent 86.

**Levers if it's wrong:** starting weapon damage/durability; early
zombie HP / `damage_reduction`; bleed/stun roll rates; the
`C.3.2a-7` supply/HP scaling. **Balance-frozen — this experiment only
produces the numbers and a recommendation.**

### RESULTS — run 2026-08-30 (`tools/combat_cost.py`, full table in `COMBAT_EXP1_RESULTS.md`)

The hypothesis is confirmed and then some.

| cell | forecast card | actual, given a win |
|---|---|---|
| **Starter (6) vs Regular, L1, fresh, no armor** (run-7 case A) | `LOW · overkill · ~100%` | mean 44 · **p90 66 (66%)** · worst 98 (98%) · 5 rounds |
| same, **worn** (mid-expedition) | `LOW · overkill · ~98%` | mean 64 · **p90 80 (80%)** · worst 100% |
| Rusty Dagger (8) vs Regular, L2 | `LOW · overkill` | p90 56 (53%) |
| Chipped Sword (12) vs Regular, L2 | `LOW · overkill` | p90 44 (42%) |
| **Iron Axe (16) vs Heavy, L4, kevlar, fresh** | `LOW · overkill · ~91%` | mean 66 · **p90 90 (78%)** · worst 101% |
| Chipped Sword (12) vs Heavy, L3, no armor (case B) | `EXTREME · ~4%` | (card honest — model/ramp problem) |

**Findings:**

1. **`LOW / overkill` is systematically wrong across the entire early
   game.** `threat_tier` and `weapon_verdict` are pure `P(win)`
   functions, so *any* fight you eventually win reads "overkill" —
   even a 5–7 round grind that takes 40–80% of your HP. Run 7's
   86-HP loss was p90, not a fluke.
2. **The worn-condition penalty compounds hard.** The same L1-vs-Regular
   fight goes from p90 66% to p90 80% just from `hunger/thirst 40,
   fatigue 60`. `_cond_penalty` is doing a lot of silent work.
3. **The starkest cell is Iron Axe vs Heavy at L4 with armor:** win
   91%, card says `LOW / overkill`, and it costs a p90 of **78% of
   max HP**. "Overkill" for a fight that routinely half-kills you.
4. **Case B is a real model/ramp wall, not a comms bug.** Chipped
   Sword (best fresh-exp-3 gear) vs Heavy = 4% win; +light armor +
   fresh = 38%. Confirms experiment 3's candidate cliff from the
   experiment-1 angle.

**Conclusion — two independent fixes:**

- **Communication (no balance change, do this before wiring the
  forecast into attention):** `threat_tier` and `weapon_verdict` must
  read the cost distribution, not just `P(win)`.
  `threat_tier = f(P(win), p90_HP_loss_fraction, worst_case)`;
  "overkill" requires a near-certain *and* cheap win. Every row where
  a LOW/MODERATE tier sits next to a p90 loss > ~40% max-HP is a cell
  where the attention spec (which derives level from the forecast)
  would under-level the event.
- **Model / ramp (balance-frozen — needs the design decision):** the
  6-dmg starter turns every early Regular into a 44–64 HP average
  fight; Heavy/Armored are unwinnable with depth-appropriate gear at
  exp 3–4. → experiments 2 and 3.

---

## Experiment 2 — does the forecast match the outcome?

**Question:** do `LOW / MODERATE / HIGH / SEVERE / EXTREME`, the fight
%, the escape %, and the weapon verdict correspond to what actually
happens?

**Simulate:** for a large sample of real encounters, tag each with its
displayed forecast, then play it out and record the outcome (won/died,
HP lost, had-to-fight-after-failed-escape). Cross-tabulate.

**Pass criteria:**

| the forecast says | the outcome should be |
|---|---|
| LOW | walked away at > ~75% HP, essentially every time |
| MODERATE | won, cost real HP, rarely dangerous |
| HIGH | won most of the time, sometimes ugly, a genuine decision |
| SEVERE / EXTREME | often died; escape is the correct read |
| "overkill" | you barely felt it |
| "adequate, but it'll cost you" | you felt it, you were fine |
| "poorly suited" | you should not be doing this |
| escape ~X% | flee actually succeeds ~X% of the time **for this zombie** |

**Redesign the derivations (proposal, to validate):**

- `threat_tier = f(P(win), expected_HP_loss_fraction, worst_case_HP)`
  — a 100%-win fight that routinely drops you below 20% HP is **not**
  LOW.
- `weapon_verdict = f(P(win), median_HP_loss)` — "overkill" requires
  *both* a near-certain win *and* a cheap one.
- `escape_pct = f(zombie_speed_class, player_dex, fatigue, hp_frac)`
  — retire the constant. A Heavy (slow) should be more escapable than
  a Swift; a fatigued/wounded player less so. This is also the
  deferred *escape-informed-by-threat* finding — the current "Fight
  ~0% / Escape ~50%" pairing is the incoherence runs 4–7 kept hitting.

### RESULTS — run 2026-08-30 (`tools/forecast_calibration.py`, full report in `COMBAT_EXP2_RESULTS.md`)

1728 cells (weapon × zombie × level × armor × condition × elite),
3000 sims each. Grouped by the label the card would show:

**Current forecast — `threat_tier(P(win))` only:**

| tier | n | P(win) range | p90 HP-loss median | p90 HP-loss range |
|---|---|---|---|---|
| LOW | 1151 | 85–100% | **27%** | **2–98%** |
| MODERATE | 39 | 60–84% | 94% | 72–99% |
| HIGH | 37 | 35–59% | 94% | 87–99% |
| SEVERE | 28 | 15–34% | 96% | 85–99% |
| EXTREME | 473 | 0–14% | 94% | 62–100% |

**The category error, made visible:** the `LOW` bucket contains fights
that cost anywhere from 2% to 98% of max HP. The label reports P(win)
and says *nothing* about cost. `MODERATE` ("well suited") sits at a
p90 loss of 94%. **646 / 1728 cells break their label's promise.**

**Proposed forecast — two axes: `P(win)` × cost-of-winning (p90):**

| tier | n | P(win) range | p90 HP-loss median | p90 HP-loss range |
|---|---|---|---|---|
| LOW | 446 | 100% | 12% | **2–19%** |
| MODERATE | 404 | 100% | 31% | **20–45%** |
| HIGH | 377 | 35–100% | 69% | 45–99% |
| SEVERE | 28 | 15–34% | 96% | 85–99% |
| EXTREME | 473 | 0–14% | 94% | 62–100% |

The `LOW` and `MODERATE` buckets are now tight and honest — LOW means
"trivial", MODERATE means "you'll win, but it'll cost you". Run-7
case A (Starter vs Regular L1, p90 66%) moves `LOW → HIGH` ("likely
win — and likely near death"). The two-axis model fixes it with **no
balance change** — same simulation, richer label.

*Open refinement:* the proposed `HIGH` spans P(win) 35–100% (it merges
"coin-flip win" and "likely win but near-death"). The tier *word* is
the same; the verdict string differentiates them (`"a real gamble"` vs
`"you'll likely win — and likely be near death"`). Splitting the tier
is possible but the merge matches the design table's intent
("genuine decision" / "dangerous despite likely win" are both "stop").

**`escape_pct`:** flat 50% for every zombie
(`round(100 * _FLEE_CHANCE)`, `_FLEE_CHANCE = 0.50`). There is no
per-zombie value, so "escape ~X% → flee succeeds ~X% for this zombie"
cannot be evaluated — X does not vary. Making it real is a **model**
change (below / experiment 3), not calibration.

**Verdict:** rewrite `threat_tier` / `weapon_verdict` to the two-axis
form **before** `DESIGN_ATTENTION_LANGUAGE.md`'s level derivation
consumes the forecast — otherwise the L0–L3 machinery is built on a
forecast that still calls a 91%-win / 78%-cost fight `LOW`.

---

## Experiment 3 — the difficulty ramp

**Question:** when should a fight the player cannot reasonably win
first appear, and what gear / knowledge should they have when it does?

**Simulate:** run full campaigns (`balance_autoplay --games N`) and
for each expedition tier record: the strongest zombie that spawns, the
realistic player loadout at that tier (weapon damage, armor, level,
HP), and the resulting `fight_pct` with best-available gear.

**Pass criteria:**

- No expedition tier throws an **EXTREME with best-available gear**
  before the player has had a fair chance to acquire counters (a real
  weapon, some armor).
- `DIFFICULTY_RAMP_LENGTH = 10`: the curve over expeditions 0–10
  should be legible — each tier's worst case is a step, not a cliff.
- Run 7 data point: a Heavy Zombie that is EXTREME-for-best-gear on
  **expedition 3** (Chipped Sword 12, no armor, L3) is the candidate
  cliff. Confirm or deny.

**Levers if it's wrong:** zombie composition by
`expeditions_completed`; elite spawn rate at low tiers; the loot band
(when does the first real weapon / first armor become reachable);
where Heavy/Armored types are gated in.

---

## Adjacent finding (not one of the three, record it)

Run 7: the player kept a **Screwdriver equipped for two whole
expeditions** while carrying a Chipped Sword, a Sword, and a Rusty
Dagger. The encounter card's `[w]` window is the only place the game
nudges a loadout — and only mid-fight, under pressure. The pack list
(`ui_mixin`) shows damage numbers but doesn't say "you're holding the
worst one." This is partly interaction-inference territory
(auto-equip the strongest *at expedition start* is already accepted in
`DESIGN_INTERACTION_INFERENCE.md`) and partly a spatial/attention
nudge. Not a combat-model bug, but it compounds experiment 1: the
model is being measured against a player who is under-equipping
himself by inattention.

## What these experiments are NOT

- Not a redesign of the round loop — that's accurate; leave it.
- Not the *presentation* of the forecast — the attention spec decides
  how loud `EXTREME` is. This decides whether `EXTREME` is the right
  label.
- Not blind-playtest work — these are deterministic-simulation
  questions with numeric pass criteria.
