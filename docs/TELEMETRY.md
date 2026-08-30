# Telemetry — the black-box event recorder

`tools/telemetry.py`. Not an outcome counter — an **event stream**.
Every campaign emits a `campaign → run → turn → event → payload` trace
you can replay to reconstruct *why* a run behaved as it did.

```bash
python3 tools/telemetry.py --campaigns 20 --policy survival
python3 tools/telemetry.py --campaigns 50 --jsonl out/trace.jsonl
```

## Four levels

| level | events | payload highlights |
|---|---|---|
| **turn / environment** | `turn` | terrain, day/phase, pos, action, HP/hunger/thirst/fatigue (+ bands), weapon/armor, food/water/med/ammo, distance from spawn, tiles visited |
| **survival state** | `state_transition` | `axis` (hp/hunger/fatigue), `frm`→`to` band, the turn it flipped, HP at the time |
| **combat** | `combat` | terrain, zombie, threat tier, **fight% / escape% captured at the decision, before the outcome**, weapon, armor, decision, forced-fight, per-round damage (`round_detail`), totals, outcome, HP before/after |
| **decision** | `combat_decision` | the forecast the bot saw vs the action it took vs what a threat-aware policy *should* do (`mismatch`) |

Plus `expedition_start/end`, `campaign_end`.

## Constraint

The recorder **observes**; it never feeds the bot information it
wouldn't have. Forecast fields are the numbers on the encounter card
at the instant of the decision — recorded before the fight resolves.
So every combat answers: *what did the agent know, what did it decide,
what actually happened.*

## What the human report derives — "where did the turns go?"

- **WHERE THE TURNS WENT** — every turn bucketed: moving-to-a-new-tile
  / revisiting / searching / recovering / in-combat / other, + how many
  moves were on slow terrain.
- **TIME / TERRAIN** — per terrain: turns · **in-game minutes spent** ·
  **minutes per move** (the movement-cost signal — water/swamp run
  ~1.5× a plain move) · moves / searches / combat / rest / revisit
  turns *in that terrain*. This is what separates "60 turns in forest
  because the route crossed it" from "60 turns bouncing between 8
  forest tiles".
- **MOVEMENT** — moves, % onto a revisited tile, searches, rests,
  median max-distance-from-spawn, and the travel:reach ratio
  (moves / distance actually covered).
- **SURVIVAL STATE** — band turn-share + the transition histogram.
- **RESOURCES** — food/water found (**by source**: building /
  zombie-loot / ground) · consumed · turns-at-zero-in-pack · fatigue
  recovery events (rests + building).
- **COMBAT** — composition · outcomes · total damage dealt/received ·
  **per zombie type** (fights, dmg dealt/taken, avg rounds) · **per
  weapon** (wins, avg HP lost, avg rounds, total dealt).
- **DECISION vs FORECAST** — fought-% by threat tier, policy mismatch,
  deaths after fighting an EXTREME/SEVERE.

Per-turn events also carry `time_min`, `dt_min` (this move's cost),
and `revisit` (times this tile has been stood on) for offline slicing.

## First finding (survival policy, small n)

Expeditions end in death, but **combat outcomes are ~all wins and
`deaths after fighting an EXTREME/SEVERE = 0`** while `starving` and
`exhausted` each hold ~50% of turns. The bots die of **attrition, not
combat** — the escape model + graded attention are doing their job;
resource pressure is the killer. That is the kind of causal split the
old `final_hp = 12` counter could never show.
