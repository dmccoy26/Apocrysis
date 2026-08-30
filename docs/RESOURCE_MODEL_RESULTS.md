# Resource / attrition investigation

`tools/resource_autoplay.py` (over `tools/telemetry.py`). Run after the
combat redesign closed: telemetry showed combat deaths ~0, EXTREME /
SEVERE all evaded — and the survivor now dies slowly of
**starvation / exhaustion** instead. This asks *why*, causally, before
anything is tuned.

Two policies, so "the economy is too tight" separates from "the naive
policy doesn't manage resources":

- **`survival`** — the naive baseline (eats/drinks only at ≤22, never
  rests).
- **`resource`** — a *trying* player (eats/drinks at ≤40, meds at 45%
  HP, rests when exhausted).

10 campaigns each.

## Headline

| | `survival` | `resource` |
|---|---|---|
| expeditions | ~60, **all died** | ~55, **all died** |
| cause: starvation (+exhaustion) | **~87%** | **~91%** |
| cause: combat | **0%** | **0%** |
| STARVING with an empty pack | dominant | dominant |
| STARVING with food in the pack | ~2% of starving turns | ~3% |
| fatigue: recovery vs decay transitions | 9 : 53 → **recovery loses** | 65 : 111 → **recovery loses** |
| explicit rests | 0 | 502 |

**A trying player dies at nearly the same rate as a naive one.** The
policy contribution is real but secondary — the underlying model is
too tight.

## Food — an economy problem

- `STARVING with an empty pack` outweighs `STARVING with food in the
  pack` by ~30:1. So it is overwhelmingly **"food never acquired"**,
  not "food available, eaten too late" and not "bot ignored hunger".
- Finds: ~1 per 12–29 turns, each `+4` (zombie-loot "some food") or a
  small building `+N`. Decay is `-2/turn` (`-3` at night) and each
  `eat` is `+30`. **A moving survivor cannot break even** — median
  food *carried* across all turns is **0** for both policies.
- Buildings are the real food source (per-terrain: forest + building +
  plain finds dominate), and `find_loot` only fires ~24% per building
  tile — so even a survivor who beelines buildings is on a thin
  margin.

## Fatigue — a model problem

- `exhausted` holds **~65%** of all turns, both policies.
- Fatigue gain is a flat **~5 per move**. `rest` recovers
  `max(5, wisdom//2)` — with starting wisdom 10 that is **5**, i.e.
  one rest ≈ undoes one move, and it costs a turn + a round of
  hunger/thirst decay. Building entry recovers `wisdom//4 + 5` ≈ 7.
- The `resource` policy rested **502 times** and still sat exhausted
  66% of the time — **recovery is mathematically incapable of keeping
  up with the gain rate**, and resting to fix fatigue *worsens*
  starvation (it burns the same clock).

## The deeper cause — turn count

Both hunger *and* fatigue are **turn-driven** (decay/turn; fatigue/
move). The survivor dies because the expedition takes too many turns —
and it takes too many turns because it **wanders** (perceived-bot
revisit ratio ~0.88; `moved` is 63% of every hungry *and* every
exhausted turn). Terrain is not the driver: fatigue/turn is a flat 5
across plain/forest/building/swamp.

> **Attrition death is downstream of the navigation problem.** The
> survivor learned not to die in combat; it now dies on the clock,
> and the clock runs long because it can't efficiently reach the
> objective. This is the same finding as runs 1–5 (`DEV_PLAYTEST.md`)
> and the 10k-game baseline (`objective_reached` 0.1%), arriving from
> the survival side.

## What this means for the fixes (not applied — measured)

Three distinct levers, in rough priority:

1. **Navigation / objective pursuit** (the deferred spatial-language
   work — objective lifecycle, investigation-thread panel, the
   perceived-bot `objective` policy). Shortening runs relieves *both*
   resources at once. Do this first; re-measure attrition after.
2. **Fatigue recovery rate.** `rest` at `max(5, wisdom//2)` and
   building recovery at `wisdom//4 + 5` are too weak to be a real
   verb. Candidate: recovery that actually nets positive against ~5/
   move (a bigger rest, or building recovery scaling with turns
   spent), plus surfacing rest as an affordance (the naive policy /
   a naive player never rests — an attention/inference gap).
3. **Early food density.** `find_loot` ~24% per building × armour-and-
   everything-else competing for the roll leaves the early economy on
   a knife edge. Same shape as the armour finding
   (`ARMOR_INVESTIGATION_RESULTS.md`) — acquisition, not the numbers.

**Do not tune any of these yet.** Fix navigation, re-run
`resource_autoplay.py`, and see how much of the attrition was
secondary.

---

## RE-RUN after B1–B4 (objective lifecycle + attention + investigation panel + approach beat)

`--policy objective` — a bot that navigates toward the mystery markers
and sweeps buildings to discover leads (8 campaigns).

| | `survival` (baseline) | `resource` | **`objective`** |
|---|---|---|---|
| outcomes | all died | all died | died 41 · timeout 33 · **won 16** |
| starvation(+exhaustion) deaths | ~87% | ~91% | **53%** (+ 29% exhaustion) |
| hunger turn-share (fed / hungry / **starving**) | 33 / 21 / **47%** | 41 / 16 / **42%** | 64 / 28 / **7%** |
| food carried (median, all turns) | **0** | **0** | **5** |
| turns between food finds (median) | ~12–29 | | **2** |

**Starvation collapsed from 47% of turns to 7%, and the bot started
winning.** The `objective` policy visits buildings systematically to
find leads — and buildings *are* the food source — so navigating
toward the objective incidentally solved the food economy. **The
resource problem was downstream of navigation, exactly as suspected.**

### Verdict per the gate

- **Food: DO NOT TUNE.** It was a navigation artifact. A survivor who
  heads for objectives eats fine.
- **Fatigue: still a real problem.** `exhausted` is 40% of turns (down
  from 65% but not solved), `recovery LOSES to decay` 7:126,
  exhaustion is now **29% of deaths**. The `objective` policy still
  never rests (it's ExplorerPolicy's thresholds), and
  `RESOURCE_MODEL_RESULTS` already showed rest recovers ~5 ≈ one
  move's gain. **This is the one lever that survives the re-run** —
  recovery rate + surfacing rest as an affordance. Measure precisely,
  then tune.
- **Navigation itself:** the `objective` policy still times out 33/90
  and the lifecycle sits URGENT most of the time — the marker pursuit
  works but lead *discovery* (sweeping the right buildings) is slow.
  That's the C.3.2 nav-pieces / a smarter building sweep, not a
  resource fix.
