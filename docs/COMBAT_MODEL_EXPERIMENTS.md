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
