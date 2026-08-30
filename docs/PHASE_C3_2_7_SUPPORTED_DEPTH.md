# C.3.2a-7 — Supported depth + inheritance-scaled deep expeditions

**Owner decision 2026-08-30**, after three content experiments
(lever matrix / Gate 8 / C.3.2a-6) established that **no generator lever
makes the required circuit fit a fixed survival budget as the map
grows**. The fix is a campaign-structure contract, not a generator
change.

**Chosen format for deep expeditions: explicitly inheritance-scaled.**
Expeditions past the fresh-survivor-viable band stay procedural; the
roguelite inheritance loop *is* the designed answer to their longer
circuits.

---

## 1. The contract

| depth band | contract |
|---|---|
| **0 … N** (N ≈ 6) | **Fresh-survivor-viable.** A brand-new survivor with starter supplies can complete the required circuit. `SCALE_REPORT.md`: baseline `ratio p90` crosses 1.0 at depth ~2–3, and distributed investigation (Gate 8) held it under 1.0 through depth 4; the band is calibrated in §4. |
| **N+1 … 25** | **Inheritance-scaled.** Viable *because the survivor arrives with more than starter supplies* — accumulated rations, gear, Survivor Knowledge, and a supply floor scaled to the depth they take up. NOT expected to be completable from a cold start. |

This answers `ROADMAP_STATUS.md`'s open question — *"is a
25-expedition campaign supposed to have 25 procedurally-equivalent
survival expeditions?"* — **no.** The first ~6 are the "learn the
world" band; the rest are "you are dug in and equipped, the campaign
is a war of attrition you are slowly winning."

## 2. The concrete gap (why this needs any code at all)

`STARTING_RATIONS = {"food": 8, "water": 8, "medicine": 2}` is a flat
class attr in `game.py`, applied to **every fresh construct regardless
of `expeditions_completed`**. Two survivors arrive at deep depth:

- **A returning winner** — carries their real (end-of-expedition,
  depleted) backpack from the profile **+ a flat `{food:10, water:10,
  medicine:5, ammo:20}` prize per win** (`finish_expedition` /
  `_prize_bonus`). Six wins ≈ +60 food banked. Probably already enough;
  measure (§4).
- **A post-death heir** — `persist_new_survivor` calls
  `cls(name, expeditions_completed=depth)` → a **fresh `Backpack()` +
  flat 8/8 rations**. An heir taking up a campaign at depth 10 is
  dropped onto a ~30² map with a ~55-tile p90 required circuit and 8
  food. **Unwinnable by the `SCALE_REPORT` model — this is the hole the
  contract has to close.**

## 3. The minimal change (proposed — needs owner sign-off; balance-adjacent)

> `STARTING_RATIONS` and the win prize scale with `expeditions_completed`,
> calibrated so a survivor *arriving* at depth d starts with a supply
> budget matched to depth d's p90 required circuit.

Sketch: `food = 8 + round(FOOD_PER_DEPTH · max(0, d − N))` (and water
likewise), with `FOOD_PER_DEPTH` derived from `USABLE_BUDGET` growth in
`SCALE_REPORT` — a survivor at depth 12 needs to cover ~56 tiles p90
vs ~32 at depth 4, i.e. ~+24 move-equivalents ≈ +10 food + +10 water at
+5 each. So roughly `FOOD_PER_DEPTH ≈ 1.5`, capped.

Touch points: `game.py` (the `STARTING_RATIONS` application loop, ~line
161) and optionally `world_mixin.finish_expedition` (the prize). Small,
contained, both files already carry depth-scaled logic
(`_zombie_power_curve`, `min_expedition` loot gates).

### Risks / open questions for the owner

1. **Balance-line proximity.** The frozen list is combat / hunger-thirst
   *rates* / encounter / loot / map growth. Depth-scaled *starting
   supplies* is arguably a new campaign-structure mechanic, not a rate
   tweak — but it is close. **Owner confirms this is in bounds before
   it's built.**
2. **The model vs the bot.** `SCALE_REPORT` is a geometry model. The
   actual `balance_autoplay.py --campaign` bot fails deep expeditions
   **100 % on zombie combat, 0 % on starvation**
   (`world_mixin.py` campaign-difficulty diagnosis). So scaling rations
   closes the *modeled* geometry wall and the *fresh-heir* cliff, but
   may not move the bot's win rate — the bot's deep wall is combat
   power, a separate known-unsolved problem. This change makes the
   contract *coherent* (an heir isn't dropped into an arithmetically
   impossible run); it is not claimed to "fix depth 6–12" on the bot.
3. **N's exact value.** §4.

## 4. Verification (before ship)

1. **Pick N.** Re-read `SCALE_REPORT` baseline + Gate 8: `ratio p90`
   by depth is `0.69 / 0.94 / 0.97 / 1.09 / 1.06 / 1.31(d6)`. Under 1.0
   through depth 2 cold; Gate-8 distribution buys through depth 4.
   **Proposed N = 4** for the strict "cold-start-viable" line, or
   **N = 6** if `_lever_scaled_beats` (shallow, free) + a modest prize
   are folded in. Owner picks.
2. **Instrument the heir path.** A `persist_new_survivor` heir at
   depths {4, 8, 12}: does the scaled `STARTING_RATIONS` bring the
   modeled `required_circuit / effective_budget` back under 1? (extend
   `scale_report.py` with a `--heir-budget` mode, or a one-off).
3. **`balance_autoplay.py --campaign`** (seed sweep) before/after —
   confirm no regression in the 0–N band and document the (expected
   small) deep-band movement.
4. Both test suites; v1 byte-identity is unaffected (this is engine
   state, not worldgen).

## 5. What this unblocks

With the contract fixed (even before the code lands), **CH3–FIN
authoring can proceed** — the ending is locked (Truth A,
authored-canonical + one final choice), and the campaign structure is
now known: ~6 expeditions of "learn the world", then an
inheritance-scaled war of attrition to expedition 25 and the finale.
The `_lever_scaled_beats` option (fixes emptiness, free at shallow
depth) is a separate small ship/no-ship call for the 0–N band.

## 6. Atlas

`game.py` is 340 lines — the `STARTING_RATIONS` change is the rare
Atlas-shaped edit (small, precise, a file it has succeeded on before —
the `world` param, log #11). If the owner greenlights the change,
**route it to Atlas** as the first real attempt this session and log
the outcome. `finish_expedition` is in `world_mixin.py` (720 ln) —
hand-write that half.

---

## STATUS — supply-scaling half BUILT + VERIFIED (2026-08-30)

Owner sign-off: (1) depth-scaled starting supplies is **in bounds** —
campaign structure, not a balance-rate tweak. (2) **N = 6**, with
`_lever_scaled_beats` + prize folded in.

### Built (`src/game.py`, hand-written — calibration loop, not routable)

- `depth_supply_bonus(depth)` = `round(1.8 · max(0, depth−1))`, capped
  20. Applied to **food and water** in the `STARTING_RATIONS` loop
  (fixes the `persist_new_survivor` heir) **and** to the
  `_prize_bonus` food/water (the returning winner). `SUPPORTED_DEPTH =
  6` exported.
- Medicine/ammo unchanged. Worldgen untouched — v1 byte-identity holds
  (this is engine state, not map generation).

### Verified

- **`scale_report.py --heir-budget`** (250 seeds/depth, `effective =
  32 + 2·bonus`): `ratio p90 < 1` at **every depth 0–12** (0.68–0.94,
  `>budget` 0–6 %). The scaled floor covers the whole campaign depth
  range — the heir cliff is closed.
- **`balance_autoplay.py --campaign`** (30 runs, seed 7): **28/30
  campaigns completed, before AND after** — zero regression. The bot
  (a returning survivor) was never supply-constrained; its deep wall is
  combat power (§3.2), untouched. The 2 stuck-at-expedition-9 runs are
  the known combat problem, not starvation.
- 280 + 100 tests green.

### NOT built this session — the `_lever_scaled_beats` player feature

The beats construct exists as a **measurement device** (the `--gate6`
harness walks `m.required_beats`). Shipping it as a player-facing
feature needs the §3.1 wiring: a beat must **withhold the next required
site's location**, surface a lead, and mark the map — a
`mystery_mixin` + `tui._objective_steps` + knowledge-model change, not
a flag flip. As a bare flag the beats are invisible to the player (no
objective line, no marker) so they aren't genuinely load-bearing in the
*game* even though the harness treats them as required.

**This does not block anything:** the supply scaling alone achieves the
viability contract through the full depth range. `_lever_scaled_beats`
as a shipped emptiness lever is a separate, self-contained feature —
spec'd in `PHASE_C3_2_6_SPEC.md` §3, deferred.

### What is now unblocked

**CH3–FIN authoring.** Ending locked (Truth A, authored + one final
choice); campaign structure known (0–6 learn-the-world, 7–25
inheritance-scaled attrition, viability contract satisfied by the
model). The DAG can be written toward a known end.

---

*Contract owner-set and the viability half shipped + verified. The
emptiness half (`_lever_scaled_beats` as a player feature) is deferred,
non-blocking.*
