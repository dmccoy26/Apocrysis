# Design spec — the escape model (Phase 2)

**Status:** design. Follows `DDR_ARMORED_ZOMBIE.md` (decision A +
`P(escape)` locked). This is the **next artifact — not
`combat_forecast.py`.** Phase 2 decides *what the game does*; Phase 3
(the forecast rewrite) then tells the player the truth about it.

Scope — **exactly three things**:

1. the escape model — the real relationship between encounter/player
   state and the chance of successfully declining a fight
2. spatial affordance — an Armored (or any avoid-tier) encounter must
   actually offer warning + room to run
3. armor progression — moved earlier, as an independent lever

**Out of scope for Phase 2:** an armor-piercing counter weapon
(rejected in the DDR — solves a different problem and would obscure
whether avoidance works); the `combat_forecast` rewrite; the attention
levels; anything about `P(win)` or fight cost (already characterised
in Exp 1–3).

---

## 1. The escape model

### The intrinsic / contextual split

Two separate things, owned by two layers:

| quantity | owner | meaning |
|---|---|---|
| **intrinsic `P(escape)`** | the combat model (→ surfaced by `combat_forecast`) | given that running is *possible*, how likely is the survivor to get clear |
| **escape availability** | the encounter / spatial layer | is running possible *at all* here, and is it constrained |

The forecast shows the player a single actionable number, but it is
`intrinsic × availability`. Open ground → availability ≈ 1, the
displayed number ≈ intrinsic. A confined space → availability is low
or zero, and the card says so explicitly ("nowhere to run").

### Intrinsic `P(escape)` — inputs and monotone shape

Inputs (all already exist on the game state):

| input | direction | rationale |
|---|---|---|
| **zombie speed class** | slow → high, fast → low | a Heavy/Armored lumbers; a Swift runs you down |
| **player Dexterity** | higher → higher | the survivor's own quickness/agility |
| **fatigue** | higher → lower | exhausted survivors don't outrun anything |
| **HP fraction** | lower → lower | wounded survivors are slower and stumble |

Zombie speed classes (from the existing roster):

| class | zombies | intrinsic escape baseline |
|---|---|---|
| **slow** | Heavy, Armored | high — this is what makes "avoid the Armored" a real strategy |
| **normal** | Fresh, Regular, Toxic | moderate |
| **fast** | Swift | low — a Swift is dangerous to *disengage* from, not just to fight |

The exact curve is a Phase-2 modelling task. What is **required** is
the *ordering* and the *monotonicity* — see §4.

### On a failed escape

Currently: a failed flee forces the full fight. Phase-2 sub-decision
(record the choice, don't assume): keep forced-fight, or soften to
"you take one free hit, then it's a fight" / "you break contact but
lose ground / drop loose items". Whatever is chosen, the forecast
card must state it ("if you don't get clear, you're fighting it" is
the current honest line and can stay if forced-fight stays).

The mid-combat desperate flee (`10%` at critical HP) is a separate
mechanic — leave it unless the model naturally subsumes it.

---

## 2. Spatial affordance

Avoidance is only a real verb if the encounter gives the player a
chance to use it. The DDR's "slow Armored is highly escapable" is
meaningless if the Armored appears one tile away in a dead-end
building.

Requirements:

- **Warning before contact for avoid-tier threats.** An Armored (and
  Elite Heavy / Armored generally) should be *spottable* — a line as
  the player approaches its tile, not only the encounter banner once
  they're on it. (`_spot_landmarks` is the existing seam for
  "something in the distance"; this is the threat equivalent.)
- **Terrain gates escape availability:**

  | terrain at the encounter | availability |
  |---|---|
  | open ground / plain / road | full — intrinsic `P(escape)` applies |
  | forest / settlement street | reduced (cover both helps and hinders) |
  | inside a building / confined | low or zero — "nowhere to run" |

- **Placement:** avoid-tier zombies should be biased toward tiles
  where escape is *possible* (open ground, near an exit), not
  dead-ends. A guaranteed-lethal fight the player is walked into blind
  is exactly the failure the DDR forbids. `world_mixin`'s zombie
  placement / `_ZONE_ZOMBIE_BIAS` is the lever.

The forecast (Phase 3) reads the resolved availability and shows the
player the real number. The player must be able to **trust** it — see
§5.

---

## 3. Armor progression (independent lever)

**Purpose:** give the player a *gradually improving fight option* so
the winnable-but-expensive fights (Heavy) stop being near-death
through the whole mid-game. **Not:** "armor so you can finally survive
the Armored" — that would collapse the avoid→prepare→overcome arc back
into a stat check.

Current curve (`COMBAT_EXP3_RESULTS.md`): median armor reduction is
**0 through tier 4**, 6 (of 13 max) only by tier 8.

Target shape:

```
T0–1   ~0        "I can fight most things."
T2     Armored appears; armor still minimal   "I cannot fight that yet." → evade
T3–5   armor + weapons develop   "I might be able to take a Heavy without dying."
T6+    a real loadout   "An Armored is a serious, costly fight — but a fight."
```

Levers: `ARMOR_TABLE` `min_expedition` bands; loot-band gating in
`world_mixin`; drop rates. The change is to the *availability curve*,
not the per-piece numbers (those were tuned to sum to 13 deliberately).

---

## 4. Testable requirements (the fixtures Phase 2 must satisfy)

**Percentages come from the model design, not invented here. The
*ordering* and *behavioural distinctions* are the requirements.** A
Phase-2 harness (extend `tools/difficulty_ramp.py` / a new
`tools/escape_model.py`) must show:

| # | scenario | requirement |
|---|---|---|
| R1 | T2 Armored · healthy · rested · open ground | `P(win) ≈ 0%` · `P(escape)` **reliably high** (an unprepared survivor's default read is "I can get away") |
| R2 | T2 Armored · wounded &/or fatigued · open ground | `P(win) ≈ 0%` · `P(escape)` **materially lower than R1** (still the best option, but now a real risk) |
| R3 | Swift · same survivor as R1 | `P(escape)` **materially lower than the Armored's** (fast zombie = hard to disengage) |
| R4 | Armored · confined terrain (inside a building) | escape **constrained or unavailable**; the card says so |
| R5 | any zombie · Dexterity high vs low, all else equal | `P(escape)` **monotonically higher** for higher Dex |
| R6 | T2 Armored · R1 conditions | `P(escape)` is **high enough that "don't fight" is a strategy, not a coin flip** — i.e. materially above 50%, ideally ~75–90% for the healthy/rested/open case (final number from the model) |

R6 is the load-bearing one: it is the DDR's constraint 4 made
testable. If the model can't hit it without also making Swift trivial
to escape (R3), the model is wrong.

---

## 5. The trust constraint

> The displayed `P(escape)` must correspond to the actual escape
> mechanic closely enough that the player can rely on it.

Otherwise Phase 3 just replaces one misleading forecast (`Fight 0% /
Escape 50%`) with another. Concretely: the number on the card is
computed from the *same* inputs and the *same* function the flee roll
in `combat_mixin` uses — not a parallel estimate that can drift.
(This is the pattern `fight_pct` already follows — it Monte-Carlos the
real round loop. The escape number should be a direct read of the
real escape probability, which is even simpler.)

---

## What Phase 2 hands to Phase 3

- an `escape_probability(player, zombie, terrain)` function in the
  combat model (or `combat_mixin`) that the flee roll uses directly
- zombie speed classes on the roster
- the resolved armor-progression bands
- the fixtures in §4, passing, as regression anchors

Phase 3 (`combat_forecast.py`) then:

- `escape_pct` → a real read of `escape_probability(...)`
- `threat_tier` / `weapon_verdict` → two-axis (`P(win)` × cost), per
  `COMBAT_EXP2_RESULTS.md`
- validate against the Exp 1/2 fixtures + the §4 fixtures

Phase 4 (attention) then consumes a forecast that tells the truth on
all three axes — `P(win)`, cost, `P(escape)` — and `L3` can mean
*"your intended response has become critical"* (Armored + wounded +
confined) rather than only *"this will kill you."*
