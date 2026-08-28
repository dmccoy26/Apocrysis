# Balance baseline — 2026-08-28 (pre-human-test)

**Do not use this report to justify design changes.** It is the frozen
"before" measurement. The next step is human play of a generated
mystery, not tuning. Re-run the *exact* scenario below as a regression
check after any future change and compare against these numbers.

## Scenario

`tools/balance_autoplay.py`, 2000 games, start level 1,
`expeditions_completed=0`, 15×15 map, 400-turn cap. Run at/around HEAD
`325ed26` (the 8-fix session: playlog crash fixes, map declutter, map
growth 3/exp, identity-prompt fix, terrain archetypes, front-loaded-
mystery evidence redistribution, weapon nudge).

## Headline numbers

| Metric | Value |
|---|---|
| Expedition survival | **1746 / 2000 = 87.3 %** |
| Deaths | 254, **100 % zombie combat** (no timeouts) |
| Turns to win | median 43 · p25 33 · p75 56 · p95 85 |
| Turns to death | median 19 |
| Survival @ level 1 | 81 % |
| Survival @ level 2 | 94 % |
| Median best weapon damage available | **6** (= the starting weapon) |
| Encounters / game | 3.4 · win rate 95 % · dealt:taken 1.40× |
| Near-death (HP ≤ 15) | 190 / 2000 |
| Games reaching night | 99.4 % · flashlight by end | 19.5 % |

## What this run DOES tell us

- **Expedition length is adequate for an investigation loop.** Median
  43-turn wins (vs the old 9–11 concern). A player has room to travel,
  hit several locations, make a wrong turn, recover.
- **Combat is the death gate, not pacing.** Every death is combat, and
  deaths cluster early (median 19 turns) and at level 1. The lever is
  weapon progression — half of expeditions never upgrade past the
  6-damage starting weapon.
- **Food / water / time are not binding.** Net-negative acquisition but
  games end with ~14 food / ~14 water in the pack. Bookkeeping, not
  pressure. Do not tune these off this report.

## What this run CANNOT tell us (bot limitations)

- **Navigation by clue.** `balance_autoplay.py`'s v4 bot
  (`_next_mystery_move`) reads `m.sites[role]`, `m.obstacle_tile`,
  `m.escape_tile` **directly off the Mystery object** and BFS-paths to
  them. It never reads a clue, never discovers evidence to find a
  destination. So exploration %, tiles-visited, and "does the player
  follow a named lead or search every building" are all unmeasurable
  here. The 9.7 %-map-explored figure is an artifact of an omniscient
  bot — treat it as an upper bound on exploration *need*, nothing more.
- **Whether the mystery is comprehensible.** The bot solves the graph;
  it can't tell you if a human understands the world grammar.
- **`Survival rate by expeditions_completed: 0 → 0 %`** is telemetry
  leakage: a win increments the counter to 1 before the row is
  recorded, so the "0" bucket is by definition the games that died.
  Not a signal.

## Next step

Human play **one generated mystery** (not `--slice`) with `--log`.
Record one thing: *when the world hands a named lead ("the keys are at
a ranger station"), do you travel toward it, or revert to searching
every building?* That is the validation the simulator can't provide.

Also worth a human read: the combat death cluster. Was the
armored-zombie type of death **unavoidable**, a **bad decision**, a
**combat-system misunderstanding**, **insufficient early weapon
access**, or **an appropriate survival risk**? Those five lead to five
different fixes — don't buff/nerf anything until it's clear which.

A genuinely-exploring investigation bot (Stage 3, `9b336876`) would
make future sweeps measure navigation. Deferred — not a blocker for
the human playtest.

---

## Regression re-run — HEAD `5179048` (~20 commits later)

Same 2000-game scenario, after: water/swamp caps, front-loaded-mystery
fix, terrain archetypes, `escape`-from-anywhere, hunger/thirst-at-0 HP
drain, drink-from-water, weapon auto-swap, the whole TUI/UX pass,
harness updated to match.

`balance_autoplay` is **non-deterministic** (bot flee rolls etc.).
Three back-to-back 2000-game runs: **85.1% / 86.9% / 85.4% won**
(mean ≈ 85.8%, ±~1pt at n=2000). Baseline was 87.3% (single run).

**Verdict: no meaningful regression.** ~1–1.5pt is within the noise
band; any real component is the intended headwind from the
hunger/thirst HP drain, which the bot mostly absorbs and a human
watching the WARNINGS panel would absorb better. Everything else held:

| | baseline `325ed26` | re-run `5179048` |
|---|---|---|
| won | 87.3% | ~85.8% (mean of 3) |
| deaths | 100% combat | 100% combat |
| turns to win (median) | 43 | 44 |
| survival @ L1 | 81% | 79% |
| ends with food/water | ~14 each | ~14 each |
| water traversal | 8.3% of steps | 7.9% |
| swamp traversal | 6.2% | **2.5%** (cap working) |
| building traversal | 24.2% | **15.3%** (cap working) |
| median best weapon dmg | 6 | 6 (still the open finding) |

The `expeditions_completed 0 → 0%` line is still telemetry leakage,
and the exploration-% numbers are still bot-omniscience artifacts —
both caveats above stand unchanged.
