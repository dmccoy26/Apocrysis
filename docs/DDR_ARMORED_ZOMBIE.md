# Design Decision Record — the Armored Zombie at expedition tier 2

**Status: DECIDED (2026-08-30). → `A` + `P(escape)` locked as a
first-class forecast signal.** Next artifact is
`DESIGN_ESCAPE_MODEL.md` (Phase 2), **not** `combat_forecast.py` yet.

## Decision

> **A — The tier-2 Armored Zombie stays, as an intentional *avoidance*
> threat. Avoidance becomes a legitimate, reliable gameplay response.**
>
> **YES — `P(escape)` becomes a first-class, calibrated forecast
> consequence signal, regardless of anything else.**

**Design intent, recorded:** the T2 Armored is an *"engage or evade"*
enemy, not a *"don't fight this"* enemy. An appropriately-equipped T2
survivor is **not expected to defeat it reliably**; they are expected
to *recognise* the threat, *assess* their state, and have a *credible
opportunity to disengage*. Later progression turns the same creature
from "avoid" into "possibly fight." This gives Apocrysis a new
progression axis:

```
recognise → avoid → prepare → eventually overcome
```

rather than `encounter → calculate DPS → fight`. The interesting
decision is **fight / flee / accept the risk** — Apocrysis must not
become a game where the answer to a scary zombie is always "run."

**The Armored's ~0% win property is NOT to be softened** to make the
numbers prettier. If it is the early "you are not ready for this"
creature, being unbeatable at T2 is correct. **The failure is the
50/50 escape**, not the 0% fight.

## Locked consequences

1. `P(escape)` becomes a first-class combat-forecast signal.
2. Escape probability is **derived from encounter + player state**
   (zombie speed class, player Dexterity, fatigue, HP fraction, and
   whether the encounter offers room to run) — never a constant,
   never derived from `threat_tier`.
3. The Armored's low fight probability is not softened to flatter the
   forecast.
4. Escape must be **reliable enough for an unprepared survivor** that
   "don't fight" is a real strategy, not a coin flip.
5. Earlier armor progression is a **Phase-2 balance lever** — its
   purpose is a *gradually improving fight option*, NOT "armor so you
   can finally survive the Armored."
6. Attention communicates the distinction between **dangerous to
   fight** and **difficult to escape**. `L3 CRITICAL` shifts meaning:
   from "this will kill you" to *"your intended response has become
   critical"* — an Armored with `0% fight / 92% escape` in the open is
   `L2`; the same Armored while wounded/exhausted in a confined space
   (`0% fight / 18% escape`) is `L3`.
7. The forecast rewrite happens **after** the Phase-2 model/balance
   decisions — the frozen sequencing holds.

**Not chosen:** B (armor-piercing counter — solves a different, more
conventional problem and would obscure whether avoidance works); C
(move Armored later — relocates the wall, adds no verb); D (hybrid) —
D may still *emerge* as a Phase-2 balancing refinement inside A if
simulations show a milder early plated enemy makes the ramp cleaner,
but it is not the primary decision and does not defer this one.

---

## The decision (context, as posed)

> **Was: is the Armored Zombie at expedition tier 2 an intended
> avoidance threat, or a premature hard wall?**

The experiments (`COMBAT_MODEL_EXPERIMENTS.md`,
`COMBAT_EXP{1,2,3}_RESULTS.md`) finished discovering the problem. This
record is where the design decided what game Apocrysis wants to be.

## The evidence

Combat has **three isolated layers**, and the experiments nailed each:

```
                 COMBAT MODEL
        ┌─────────────┼─────────────┐
     outcome         cost         escape
     P(win)        HP-loss       viability
        └─────────────┼─────────────┘
               COMBAT FORECAST  →  ATTENTION
```

1. **Exp 1** — a fight's *cost* is unrelated to its *outcome*. The
   `LOW` bucket spans 2–98% p90 HP loss.
2. **Exp 2** — `threat_tier` is a pure `P(win)` function → a category
   error; 646/1728 cells break their label's promise. A two-axis
   `f(P(win), cost)` fixes the *communication* with no balance change.
3. **Exp 3** — the first real cliff is **tier 2, the Armored Zombie**:
   - 0% win with best realistic gear (`damage_reduction = 0.5` negates
     the player's only developing axis, weapon damage)
   - armor reduction medians **0 through tier 4**
   - **no avoidance path**: `min P(die)` is a flat **50%** (fight =
     certain death; the alternative is the coin-flip flee that forces
     the fight on failure)
   - the composition ramp introduces Armored exactly at its ~4% weight
     crossing — the timing is systemic, not incidental

**This is not a communication problem.** It is a **missing gameplay
response**: the world contains an encounter for which the player has
no reliable successful action.

## The hidden fourth axis this exposes

The player's real decision has four inputs, not three:

```
         ENCOUNTER FORECAST
   Can I win?  ──────────  P(win)
   What will it cost?  ──  HP-loss distribution
   Can I avoid it?  ─────  P(escape)        ← currently a flat 50% constant
```

`Fight ~0% · Escape ~50%` is not a decision model — it's two numbers
that don't relate. Whichever way the decision below goes, **escape
probability must become a first-class consequence signal** (see the
second locked question).

## The options

| # | decision | what it commits to | cost / risk |
|---|---|---|---|
| **A** | **Keep Armored at T2 + make it avoidable** | Avoidance becomes a legitimate combat verb. `escape_pct = f(zombie_speed_class, player_dex, fatigue, hp)` — a slow Armored is *highly* escapable. The encounter needs spatial affordance: warning + open ground to run. Forecast says "Do not fight this. You can probably get away." Combat hierarchy gains a real avoid tier: `LOW→fight · MODERATE→fight, watch cost · HIGH→decide · SEVERE→probably avoid · EXTREME→avoid`. | The most design work. Avoidance has to *actually work* — a 65%+ escape against a slow enemy, not a coin flip — or it's just gambling with extra steps. Needs the encounter/movement layer, not just the forecast. |
| **B** | **Keep Armored at T2 + introduce a credible counter before T2** | A weapon type, consumable, or mechanic that beats `damage_reduction` (armour-piercing, a heavy blunt weapon, a molotov) is reachable by tier 1–2. Armored stays a hard fight but a *soluble* one. | Adds a new item/mechanic and its own acquisition/loot problem. Doesn't fix the flat-escape incoherence on its own (still want the escape-signal fix). The counter has to be findable, not just craftable at a level players don't reach. |
| **C** | **Move Armored (and its 0.5 reduction) later** | Gate `ArmoredZombie` in the composition table to a tier where armor development + weapon damage give a fair fight (exp 3 suggests ~tier 8–9, where it eases to proposed-HIGH). Optionally also make armor develop earlier so the gate can be sooner. | Simplest. But leaves tiers 4–8 (the "wall") still hard from Heavy/Elite unless those move too. Doesn't add a new strategic dimension — Apocrysis stays fight-or-die. |
| **D** | **Hybrid: a weak early Armored → the full hard-counter later** | A tier-2 "Scavenger in plates" with `damage_reduction ≈ 0.2` and less HP — a *costly* fight (proposed MODERATE/HIGH), not a wall. The `0.5` / 120-HP Armored is gated to a later tier as the intended hard counter. | Two enemy definitions to author and balance. But it lets the ramp keep a plated enemy early for texture without the cliff, and preserves the hard-counter role for when the player can meet it. |

## Recommendation (the one the decision followed)

**A + the escape-signal fix**, with **C's armor-development change as
support.**

Rationale: Exp 3 shows the player spends most of the campaign with one
enemy class *outside their combat system*. The cleanest fix that also
makes Apocrysis more interesting is to make "avoid" a real verb — it
gives the threat hierarchy somewhere to point above HIGH, it resolves
the `Fight 0% / Escape 50%` incoherence that recurred in runs 4–7, and
it fits the game's identity (you survive by understanding a place, not
by out-DPSing it). Pair it with making armor actually develop by
tier 3–4 so the *winnable-but-expensive* fights (Heavy) don't stay
near-death the whole mid-game.

Against pure C: moving Armored later without adding avoidance leaves
the game fight-or-die and just relocates the wall.

## Second locked question

> **Does the forecast expose escape probability as a first-class
> consequence signal?**

**Proposed: YES, regardless of A/B/C/D.** Runs 4–7 repeatedly hit the
`Fight ~0% / Escape ~50%` incoherence; the perceived-bot and the
experiments confirm "fight vs flee" is part of the player's actual
decision. A constant is not a forecast. `escape_pct` becomes
`f(zombie_speed_class, player_dex, fatigue, hp_frac)` and the card
shows it as a real number the player can act on.

(Whether the *underlying* flee roll in `combat_mixin` also changes is
part of the Phase-2 model decision — but the forecast must at minimum
stop reporting a constant as if it were a prediction.)

## The phased plan (freeze this)

```
Phase 1 — DESIGN decision   this record: what does Armored@T2 mean?      (no code)
Phase 2 — MODEL decision    if A: the escape model + spatial affordance
                            if B: the counter item
                            if C/D: the composition/armor gates
                            + the escape_pct signal (all paths)          (balance changes live here)
Phase 3 — FORECAST rewrite  combat_forecast.py: two-axis threat_tier /
                            weapon_verdict + escape_pct as f(...).
                            Validate against COMBAT_EXP1/2 fixtures.     (first src/ change)
Phase 4 — ATTENTION         DESIGN_ATTENTION_LANGUAGE.md: L0–L3 consumes
                            the now-trustworthy forecast.
```

The forecast's job is **to tell the truth about whatever game Phase 1
and 2 choose** — it does not make a 0%-win / 50%-escape fight *feel*
reasonable. Attention then makes that truth perceptually
proportionate.

## Also recorded — the non-monotonic curve

Tiers 4–8 are the hardest, not tiers 9–12. This is a **structural
progression problem**, not "late game is hard": the composition system
introduces a threat class whose counter-progression (armor) lags it by
~6 expeditions. Whatever is decided for Armored, the armor-development
curve is a Phase-2 lever in its own right.
