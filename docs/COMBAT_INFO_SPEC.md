# Combat information layer (spec)

Owner-proposed 2026-08-30 from playtest run 3 (`--dev --chapter 3`,
died turn 99 to an Elite Heavy Zombie, level 10, Steel Katana). The
game presented *"Encountered an Elite Heavy Zombie! Do you want to
fight?"* — and the player had **no way to see** the enemy's HP/damage,
the fight odds, the escape odds, or which of the 7 weapons in the pack
would change the matchup. The decision as presented is *"gamble your
run on odds you can't see."*

## The boundary — this is a PLAYER-INFORMATION layer, not a rebalance

> **No combat or escape MATH changes.** The forecast reads the same
> numbers the fight loop already uses (`zombie.health`, `zombie.attack`,
> `player.strength/dexterity/health`, weapon damage, armor reduction,
> `_condition_penalty`, crit/dodge/stun/bleed rates) and converts them
> to player-facing estimates. The fight itself, the 50 % flee roll, XP,
> loot — all unchanged.

Deferred (owner flagged, explicitly NOT in this change): a
dangerous-enemy reward bonus (fighting an Armored / Heavy / Elite pays
more than a Fresh). That IS a balance change — its own experiment,
after this info layer is playtested.

## What replaces "Do you want to fight?"

An encounter card, shown once when the encounter fires:

```
  ─── ELITE HEAVY ZOMBIE ───────────────────────────
  A massive infected under layers of improvised plate.
  It hits like a truck and barely staggers.

  Threat:  EXTREME

  With your Steel Katana (20 dmg):
    Fight    ~15%      Escape   ~50%
    If the escape fails, you're fighting it anyway.

  Weapon:  poorly suited to this target.
  In your pack:  Gun (32 dmg) would help.

  [f] fight    [e] try to escape    [w] change weapon
  ─────────────────────────────────────────────────
```

- **Name + one-line description** — authored per zombie subclass +
  an "Elite" prefix line. Flavour the survivor could plausibly infer
  (bulk, speed, armour), never raw stats.
- **Threat** — a tier (`LOW / MODERATE / HIGH / SEVERE / EXTREME`)
  derived from `fight%` (see §Forecast). Not a stat readout.
- **Fight %** — estimated chance the player wins the fight, at the
  currently equipped weapon.
- **Escape %** — estimated chance the flee roll succeeds (currently a
  flat 50 %; the forecast reports what the code actually does, so if
  the flee roll ever becomes dexterity-scaled the card follows).
- **"If the escape fails…"** — the consequence line. Escape 50 % on a
  fight you'd lose is very different from escape 50 % on a fight you'd
  win; spell it out.
- **Weapon verdict** — `poorly suited / adequate / well suited /
  overkill`, from the equipped weapon's fight %.
- **Pack suggestion** — if a weapon in the backpack gives a materially
  better fight % (≥ +15 points), name the best one. This is the first
  time the loot the player has been hoarding becomes actionable.
- **[w]** — opens the existing equip flow, then **re-shows the card**
  with the new weapon's numbers. No turn passes; you're still deciding.

## Forecast (§Forecast)

`src/combat_forecast.py` — pure, imports nothing from the mixins.

- `fight_forecast(player, zombie) -> {win_pct, threat, weapon_verdict}`
- `escape_forecast(player, zombie) -> {escape_pct, fail_consequence}`
- `better_weapon(player, zombie) -> (Weapon, win_pct) | None`

**Method: Monte Carlo over a faithful copy of the round loop.** Run
~300 silent simulated fights (the real per-round formulas: `damage =
round((wdmg + str//3) * condition_penalty)`, `crit = min(.25,
dex/200)` ×2, dodge `min(.5, dex/150)`, bleed 15 %/3t, stun 10 %/1t,
armor `.absorb` per piece), count wins. Reuses the exact numbers, not
a re-derived approximation — the owner's "the existing combat simulator
estimates fight outcome". The loop is ~40 lines; keeping it in
`combat_forecast.py` (not calling the real `combat_mixin` method)
avoids any risk of the forecast mutating real player state or printing.

A drift guard: one test asserts the forecast's simulated win-rate for a
few fixed matchups is within ~10 points of the *actual* `combat_mixin`
fight loop run headless the same number of times.

`condition_penalty`, crit/dodge/status constants are read from the same
places `combat_mixin` reads them (extract the magic numbers to
`constants.py` if that's cleaner, without changing their values).

## Threat tiers (from equipped-weapon fight %)

| fight % | threat |
|---|---|
| ≥ 85 | LOW |
| 60–84 | MODERATE |
| 35–59 | HIGH |
| 15–34 | SEVERE |
| < 15 | EXTREME |

## Wiring

- `combat_mixin` encounter entry: replace the `ask_yes_no("Do you want
  to fight?")` block with a `_encounter_card(zombie)` call that renders
  the card and returns `"fight" | "escape"`. The `[w]` branch loops.
- `io` seam: the card is `io.say` lines + an `io.ask` for the letter
  (classic) / the TUI renders it in the log and takes the key. Reuse
  the numbered-equip pattern for `[w]`.
- The existing weak-weapon nudge (`_weak_weapon_nudged`) is now
  redundant with the weapon verdict — remove it.
- Bot (`balance_autoplay.py`): the bot answers the card the same way it
  answered the yes/no (its existing fight/flee heuristic maps to
  `f`/`e`); no bot rewrite, and the forecast is not consulted by the
  bot (keeps the balance numbers comparable pre/post).

## Acceptance

- No change to any combat/escape/XP/loot number. The balance bot's
  survival % and death-cause breakdown are within noise of pre-change
  (run `balance_autoplay.py --games 2000` before/after).
- The card shows for every encounter; `[w]` re-rolls the numbers
  without passing a turn.
- Forecast within ~10 points of the real fight loop on the drift-guard
  matchups.
- Both suites green.

## What this does NOT do

- No reward change (deferred).
- No new zombie types or stats.
- No auto-equip (the player still chooses; the card just makes the
  choice legible).
- No change to encounter rate or the 50 % flee roll.

---

*Player-information layer. The combat math is frozen and untouched;
this exposes what it already computes.*
