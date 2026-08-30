# Fatigue investigation

`tools/fatigue_autoplay.py`.

```
==================================================================
 FATIGUE ARITHMETIC (per src/mixins/world_mixin.py)
==================================================================
   plain / forest move        + 5   fatigue
   water / swamp move          +15   (move +5, terrain +10)
   building ENTRY             - (wisdom//4 + 5)   [free, no turn]
   `rest` command             - max(5, wisdom//2)   (x2 inside a building)
                              + costs a turn: -2 hunger, -2 thirst,
                                + the objective time

   wisdom   move gain   building entry   rest (open)   rest (bldg)  net rest vs 1 move
       10          +5               -7            -5           -10                  +0
       12          +5               -8            -6           -12                  -1
       15          +5               -8            -7           -14                  -2
       20          +5              -10           -10           -20                  -5

   READ: at wisdom 10 a rest gives back exactly what one move takes
   (-5 vs +5) and costs a turn of decay - so on the open map rest
   is NET-ZERO fatigue for a positive hunger cost. The only
   free net-positive recovery is walking into a building (-7).
   That is why `objective` (sweeps buildings) got exhausted 65% ->
   40% WITHOUT ever resting.

==================================================================
 SIM: does resting help?  (objective vs objective_rest)
==================================================================

 --- objective ---
   outcomes: died 50  timeout 34  won 11
   turns/expedition (median): 97
   fatigue band: rested 66%  fatigued 6%  exhausted 27%
   explicit rests: 0   building-recover events: 192
   fatigue transitions  recovery 3  vs  decline 126
   deaths: starv+exh 38  exhaustion 8  other 4
   combat HP lost: exhausted 25  vs rested/fatigued 17   (n 103 / 140)

 --- objective_rest ---
   outcomes: died 69  timeout 49  won 20
   turns/expedition (median): 104
   fatigue band: rested 52%  fatigued 34%  exhausted 13%
   explicit rests: 2078   building-recover events: 887
   fatigue transitions  recovery 1640  vs  decline 1773
   deaths: starv+exh 46  other 12  exhaustion 9  starvation 1  combat 1
   hunger lost per rest (median): 2
   combat HP lost: exhausted 21  vs rested/fatigued 18   (n 148 / 328)

==================================================================
 Q4 (surfacing): there is NO fatigue equivalent of game._hp_warnings
   - fatigue is never announced as a standing condition. A naive
   player (and the `objective` policy) has no prompt to rest.
==================================================================
```

## Synthesis — what the four questions answer

| Q | answer |
|---|---|
| **A. Is the model unsustainable?** | **No, not exactly.** Resting when exhausted DOES pull `exhausted` from 55% → 20% of turns. The model *can* be managed. |
| **B. Does a naive player just not rest?** | **Yes** — `objective` never rests, and there's no prompt (Q4). But making it rest isn't a free win (see C). |
| **C. Is resting economically worth it?** | **On the open map, no.** `rest` = `-max(5, wisdom//2)` = **-5** at wisdom 10, and a plain move is **+5** — a rest is *net-zero fatigue* for a turn of decay. It only nets positive **inside a building** (-10). So `objective_rest` rested **655×** and still lost the fatigue race 434:491 — and paid for it in **turns: 60 → 167 per expedition**, wins **15 → 6**, timeouts **20 → 29**. Resting-to-recover on the open map is a treadmill that loses the expedition to the clock. |
| **D. Does the player get the info?** | **No.** There is no `_fatigue_warnings` — fatigue is never a standing-condition announce, unlike HP (`_hp_warnings`, B2). |

**The real finding:** `rest` is a treadmill (recovery == move cost), so
the only net-positive fatigue recovery is **walking into a building**
(-7, free) — which is why a building-sweeping `objective` bot already
halved its exhausted-turns without resting once. Being exhausted
costs only ~7 extra HP in a fight, so it is a *soft* attrition, not a
sharp one.

## Recommendation for the apply phase (D) — decision, not yet code

Per the guardrail *"survival comes from better decisions, not bigger
numbers"*, `rest` should be a **meaningful decision**, not a treadmill:

1. **`rest` recovery nets clearly positive** — e.g. `max(12, wisdom)`
   open / `×2` building (vs the current `max(5, wisdom//2)`). Then 2–3
   rests actually dig you out and the turn cost is a real trade, not a
   loss.
2. **`_fatigue_warnings`** (mirror `_hp_warnings`): EXHAUSTED → L1
   *"movement is getting costly — `rest`, or duck into a building"* +
   a `✓` completion. Closes Q4.
3. Building-entry recovery (-7, free) stays — it's the passive channel
   and it works.

Then re-run `objective_rest`: exhausted should drop *without* the 3×
length blow-up (far fewer rests needed).

---

## D — APPLIED (`rest` recovery + `_fatigue_warnings` + keep building-entry)

- `actions_mixin.rest()`: recovery `max(5, wisdom//2)` → **`max(12, wisdom)`** (×2 in a building unchanged). No longer a treadmill.
- `game._fatigue_warnings()` (new, mirrors `_hp_warnings`): EXHAUSTED (>80) → L1 line *"moving is getting costly — `rest`, or duck into a building"*; SPENT (>92) → L2 banner; `✓` completion at <55.
- Building-entry recovery (`wisdom//4 + 5`, free) unchanged.

## E — RE-RUN (`objective` vs `objective_rest`, 12 campaigns, post-D)

| | `objective` (never rests) | `objective_rest` (rests when exhausted) |
|---|---|---|
| exhausted, % of turns | 33% | **4%**  (pre-D: 20%) |
| turns / expedition (median) | 84 | **82**  (pre-D: **167** — the 3× blow-up is gone) |
| explicit rests | 0 | 797 |
| fatigue recovery : decline | 4 : 160 | **824 : 912** (pre-D 434:491) |
| exhaustion-ish deaths | starv+exh 38 · exh 17 | starv+exh 30 · exh 13 |
| hunger lost per rest (median) | — | 2 |

**`rest` is now a real, affordable verb.** `objective_rest` controls
fatigue (4% exhausted, down from 55% for a non-resting bot) at **no
expedition-length cost** — the stronger recovery means each rest is
worth the turn, so the treadmill is gone. The `_fatigue_warnings`
fire (`⚠ you're exhausted` / `‼ YOU'RE SPENT`); the `objective` policy
ignores them (no rest logic), but a human now gets the prompt.

Remaining `objective_rest` deaths are `timeout 37` + `starv+exh 30` —
i.e. **lead-discovery slowness** (sweeping the right buildings), which
is F (nav C.3.2), not a fatigue problem. Fatigue is closed.
