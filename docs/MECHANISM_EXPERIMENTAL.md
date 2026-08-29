# Tier-2 mechanism: experimental (hypothesis → consequence → revise) — todo `e0475adf`

The second high-value family (2026-08-28 synthesis). Player question:
**"what if my interpretation is wrong?"** — the evidence is truthful
but under-determines; the *obvious* reading is wrong; you act, observe
a consequence, and revise your model.

With `power_station` this gives the three-mystery phase gate
(`69d78812`) two of its three families.

## The scenario: `dam_valves`

| axis | value |
|---|---|
| family | `experimental` |
| discovery | `observe_anomaly` (the low road is under water) |
| reasoning | `revise` |
| resolution | `operate` (pull the right control) |
| confirmation | `environmental` (the reservoir drops, the road lifts clear) |

Prose chain:

1. `closed` — the main road out is gone: a slide.
2. `route` — there's a **lower valley road** that runs under the dam.
   It's under water right now, but it's still there.
3. `obstacle` — the water. The reservoir level is held by the dam and
   set from the **control room**.
4. `require` (**the control room**) — a bank of controls: the **main
   sluice**, the **east intake**, the **west intake**. No item to
   fetch — you have to work out which one drops the *valley*
   reservoir.
5. The player's first reasonable reading: "the main sluice, obviously."
   Pulling it: *"Water roars downstream — but the level behind the dam
   doesn't move. The main sluice feeds the river, not the valley
   side."* Truthful. Reframes the model.
6. One intake is wrong: *"The level drops a hand's width, then holds.
   This gate only takes part of it."* The other is right: *"Behind the
   dam the reservoir starts falling. Downstream, the low road lifts
   clear of the water."*
7. `escape` — the low road, now dry.

The **obvious control is never the correct one** — `build_mystery`
picks `correct_control` from the intakes only. The wrong pulls are
*observations*, not "wrong, try again."

## Minimal new machinery

### `Mystery` (src/escape.py)
```python
self.controls = []            # experimental family: the candidate controls, or []
self.correct_control = None   # the one that opens the obstacle
self.controls_tried = []      # names pulled so far (for save/load + "already tried")
```
+ round-trip all three in `to_dict` / `from_dict`.

### `MECHANISMS['dam_valves']`
Same shape as the others, plus:
- `"controls"`: `["the main sluice", "the east intake", "the west intake"]`
- `"obvious_control"`: `"the main sluice"` (excluded from `correct_control`)
- `"control_wrong_obvious"`, `"control_wrong_other"`, `"control_correct"`:
  the three consequence strings (with a `{control}` slot where useful)
- `"item"`: still present but unused (`""` or a placeholder) — the
  family has no fetch item; keep the key so nothing else breaks.
  Better: give it `"item": None` and guard the F_REQUIRE prose /
  E_require_b construction on `spec["item"]` being truthy.

### `build_mystery` (src/escape.py)
After the base role assignment, if `spec.get('controls')`:
- `m.controls = list(spec['controls'])`
- `m.correct_control = rng.choice([c for c in m.controls
   if c != spec['obvious_control']])`
- the `require` role IS the control room (already placed); relabel via
  `spec['roles']['require']`
- F_REQUIRE prose becomes "The reservoir is set from {control room} —
  a bank of controls." E_require_b ("you find the item here") is
  skipped (no item); E_require_a stays.
- no new fact needed — the "which control" question lives in the
  action, not the knowledge graph. (If a fact helps the objective
  panel, add `F_CONTROL` "one of the dam controls drops the valley
  reservoir" with 2 evidence, but v1 can skip it.)

### command: `pull <control>` / `try <control>`
- dispatch_map: `'pull'`, `'try'` → `mystery_pull_control` (parse the arg)
- `mystery_pull_control(name)` (mystery_mixin):
  - not at the control-room site → "There's nothing here to pull."
  - name not matching a control (fuzzy contains) → list the controls
  - already in `controls_tried` and not correct → "You've already
    tried that one. It didn't do it."
  - `name == obvious` and wrong → say `control_wrong_obvious`
  - other wrong intake → say `control_wrong_other`
  - correct → `m.obstacle_open = True`, clear the obstacle tile,
    `★ OBJECTIVE UPDATED` "the way is open" with `control_correct`
  - append to `controls_tried`

### `_mystery_obstacle_ready` (mystery_mixin)
```python
if m.controls:     return m.obstacle_open   # opens from the control room only
if m.power_role:   return m.power_restored
return self._mystery_has_item()
```
`mystery_bump_obstacle`: if `m.controls and not m.obstacle_open`, say
"The water's too deep to wade. This clears from the control room, not
here."

### tui / ui
- `_objective_steps`: experimental branch — "found the flooded low
  road / found the dam controls / ▸ work out which control clears it /
  opened the way / escape". Never name the controls or the answer.
- `_action_bar`: at the control-room site with the obstacle not open:
  `pull <control>` and list the untried control names.
- `_mystery_site_mark`: the `require` (control-room) site marks once
  F_REQUIRE known (unchanged).

## Validation

`Mystery.validate()`: if `controls` is set, require `correct_control
in controls` and `correct_control != spec obvious` (checked at build).
Everything else unchanged.

## Scope guard

No new item type. No knowledge-graph fact strictly required (the
experiment is an action loop, not a derivation). No region mutation
beyond flipping `obstacle_open` + the one tile. One list, one answer,
one command.
