# Tier-2 mechanism: infrastructural (dependency chains) — todo `c67cbd25`

The first genuinely-different family after `spatial`. Player question:
**"what dependency makes this work?"** — you can't just carry the key
to the door; the door is powered by something *elsewhere*, and you
have to trace that.

Priority #1 of the Tier-2 set (2026-08-28 synthesis) — with `spatial`
it gives the two families the three-mystery phase gate (`69d78812`)
needs.

## The scenario: `power_station`

| axis | value |
|---|---|
| family | `infrastructural` |
| discovery | `observe_anomaly` (the gate is dead) |
| reasoning | `infer` (trace the dependency) |
| resolution | `repair` (restore power) |
| confirmation | `environmental` (the gate lights up) |

Prose chain the player reconstructs:

1. `closed` — the roads out are all blocked.
2. `route` — there's a road **tunnel** through the ridge; it's the way.
3. `obstacle` — the tunnel gate is **electrically operated, and dead.**
   *This is the anomaly.* You can't pick it, can't force it.
4. `power` (**new role**) — the gate's power comes from the old
   **hydro station** downriver.
5. At the hydro station: the **generator is dry** — no fuel.
6. `require` — fuel drums are stored at the **maintenance yard**.
7. Bring fuel → the hydro station (NOT the gate) → generator runs →
   the gate has power → walk through.

The reasoning difference from `spatial`: the item is applied at a
**different place than the obstacle**, and the obstacle opens on a
**state flag** (`power_restored`), not on the player carrying an item
to it. A player who tries "walk the fuel to the gate" learns the gate
isn't where fuel goes.

## Minimal new machinery

Reuse everything possible. Deltas only:

### `Mystery` (src/escape.py)
```python
self.power_role = None       # role name of the "apply the fix here" site, or None
self.power_restored = False  # infrastructural: the dependency is satisfied
```
+ round-trip both in `to_dict` / `from_dict`.

### `MECHANISMS['power_station']` entry
Same shape as the others, plus:
- a 5th `roles` key: `"power": "the hydro station"`
- classification keys (table above)
- `"power_item"` reuses `"item"` (a jerrycan of fuel) — no new item type

### `build_mystery` (src/escape.py)
After the existing 4-role assignment, if `'power' in spec['roles']`:
- pick a 5th distinct building site → `m.sites['power']`, label it,
  `m.power_role = 'power'`
- F_REQUIRE's prose changes to point at the generator, not the gate
- add evidence: `E_power_a` at `obstacle` ("the gate is electric and
  dead - it's fed from the hydro station"), `E_power_b` at `power`
  ("the generator's dry"). Both support a new `F_POWER` fact OR fold
  into F_OBSTACLE/F_REQUIRE — decide during impl; F_POWER is cleaner.
- reachability: `m.sites['power']` joins the protected/`_ensure_reachable`
  set.

### `mystery_mixin`
- `mystery_arrive`: `if role == m.power_role and self._mystery_has_item()
  and not m.power_restored:` → consume the item, `m.power_restored = True`,
  `announce_event("power restored at " + label, ..., kind="objective")`.
- obstacle open condition: today `mystery_clear_obstacle` and the
  `world_mixin` auto-clear (line ~813) gate on `self._mystery_has_item()`.
  For an infrastructural mystery gate on `m.power_restored` instead.
  Helper: `m.obstacle_ready()` → `power_restored if power_role else
  has_item`.

### tui / ui
- `_objective_steps`: insert "restored power at {power label}" between
  "got the {item}" and "opened the way".
- `_mystery_site_mark`: mark `m.sites['power']` once `F_POWER` known.
- `_action_bar`: "restore power (at the generator)" when at the power
  site with the item.

## Validation

`Mystery.validate()`: if `power_role` is set, require `power_role in
sites` and `F_POWER` (if used) has ≥2 evidence. `_ensure_reachable`
must cover the power site (add it alongside the others).

## What this does NOT need

No new item types. No multi-item chain yet (that's `helicopter` /
`17f2a0ca`). No region mutation (that's `dam_spillway` / the
environmental todo). One extra role, one flag. Keep it that small.
