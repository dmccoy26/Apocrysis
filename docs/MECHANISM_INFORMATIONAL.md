# Tier-3 mechanism: informational (the response reveals the route) — todo `ea1d52be`

The third genuinely-different grammar. Player question:
**"the way out isn't a place I can find — it's a thing I have to make
happen."** Every other family, the route exists on the map from the
moment you learn about it (you just can't *use* it yet). Here the
route is **not known and not visible** until you restore a system and
something outside answers.

## The scenario: `radio_tower`

| axis | value |
|---|---|
| family | `informational` |
| discovery | `receive_information` (a broadcast log) |
| reasoning | `infer` (contact is possible → contact gets us out) |
| resolution | `repair` (fuel the generator, transmitter comes up) |
| confirmation | `external_response` (a voice answers and reads you a road) |

Prose chain:

1. `closed` — every road out ends the same way: a checkpoint, a
   dropped bridge. Nothing is driving out.
2. `route` (**the broadcast log**) — *not a route.* "The valley's
   emergency channel is still monitored from the regional station.
   The last entry: *if the tower comes back up, we can talk someone
   out.*" → you learn **contact with outside is possible**, not where
   to go.
3. `obstacle` (**the broadcast tower**) — the transmitter on the ridge
   is dark. The panel's dead. No power. → the way out won't come clear
   until this is transmitting.
4. `power` (**the generator shed**) — the transmitter runs off a
   generator below the tower. Its tank is dry.
5. `require` (**the ranger depot**) — a fuel cache. The jerrycan.
6. Fuel the generator → the transmitter comes up → **a voice answers.
   They read you an emergency access road on the {bearing} ridge — a
   track the maps don't show. It's on your map now.** → `F_ROUTE` is
   revealed *here, for the first time*; the escape tile is marked.
7. `escape` — the access road, out over the ridge.

## What's genuinely new vs `power_station`

`power_station` already is "bring fuel → apply at a remote site →
`power_restored` → obstacle opens." `radio_tower` **reuses all of
that machinery unchanged** — `power_role`, `power_restored`,
`power_fact`, the `power` site, `power_restored_desc`,
`mystery_apply_fix`, the jerrycan, `_mystery_obstacle_ready`
(`return m.power_restored`).

The twist is one flag, `spec['reveals_route'] = True`:

| aspect | `power_station` | `radio_tower` |
|---|---|---|
| `F_ROUTE` known | early, at the route site | **only after `power_restored`** |
| the route site tells you | where the tunnel is | that the channel is monitored — a *system*, not a place |
| `power_restored` effect | the gate opens | **a response arrives → `F_ROUTE` revealed + escape tile marked + `obstacle_open`** |
| escape tile shown on map | once `F_OBSTACLE` known / map found | **only once `F_ROUTE` known** (`escape_kind` = revealed) |
| the "obstacle" | a physical dead gate you bump | not-knowing; there is no gate |

## Minimal new machinery

### `MECHANISMS['radio_tower']` (src/escape.py)

Same shape as `power_station` (it sets `power_role`, `power_fact`,
`power_obstacle_ev`, `power_site_ev`, `generator_ev`,
`power_restored_desc`), plus:

- `"reveals_route": True`
- `"f_obstacle"`: override for the generic F_OBSTACLE string —
  *"The way out won't come clear until the transmitter is back up."*
- `"route_reveal_ev"`: the response text —
  *"The channel crackles. A voice, then directions: an emergency
  access road on the {bearing} ridge, a track that isn't on any map.
  It's marked for you now."* (`{bearing}` filled from the real gap
  direction, same as `E_obstacle_a` already does.)

### `build_mystery` (src/escape.py)

Guarded on `spec.get('reveals_route')`:

- The generic `F` dict takes `spec.get('f_obstacle', <default>)`.
- **Withhold `F_ROUTE` from the early evidence.** For a reveals_route
  mystery: `E_route_a` supports nothing (or is skipped); `E_route_b`
  drops `F_ROUTE` (keeps `F_REQUIRE`); `E_obstacle_a` drops `F_ROUTE`
  (keeps `F_OBSTACLE`). `F_ROUTE` is then supported only by
  `E_route_reveal` (below) and `E_confirm` — both land after restore.
  ≥2-routes invariant holds.
- Add `E_route_reveal` (`supports=['F_ROUTE']`, no location — it is
  *not* placed on a site; `mystery_mixin` discovers it on restore).

### `mystery_mixin.py`

In the two places `m.power_restored` is set to `True` —
`mystery_arrive`'s power block and `mystery_apply_fix` — after the
existing `announce_event('the generator is running', …)`:

```python
if getattr(m, 'reveals_route', False) or MECHANISMS[m.mechanism].get('reveals_route'):
    self._mystery_reveal('E_route_reveal')   # F_ROUTE lands, banner fires
    m.obstacle_open = True                    # no physical obstacle
```

`_mystery_progress_flare`'s `F_ROUTE` branch needs an informational
case: there's no `m.site_labels['route']` route to point at, so
instead — *"the way out — an emergency road on the ridge — is on your
map now."*

`mystery_bump_obstacle`: for a reveals_route mystery with
`not power_restored`, "There's nothing to force here. Nothing gets you
out until the transmitter is back up."

### `ui_mixin.py`

- `_mystery_site_mark`: the escape tile shows once
  `(m.family == 'informational' and 'F_ROUTE' in known)` — the
  existing `F_OBSTACLE`/`map_revealed` gate stays for the others.
- `_objective_steps`: an informational branch — "found the broadcast
  log / found the dead transmitter / learned you need fuel — at the
  depot / got the fuel / restored the transmitter / ▸ follow the
  directions out / escaped". Never say "the answer is a radio."
- `_action_bar`: at the generator site pre-restore, surface
  `use fuel`.

### `choose_mechanism`

No change — the shuffle-bag + no-back-to-back-family already read
`MECHANISMS[m]['family']`, and `informational` is just a new value.

## Validation

`Mystery.validate()` unchanged. Extra build-time assert: if
`reveals_route`, `F_ROUTE` must have ≥2 supporting evidence and none
of them at an early site (closed/route/obstacle).

## Scope guard

No `requirement_items` chain (one jerrycan, like `power_station`). No
region mutation (`obstacle_open` is a bool flip, the escape tile
already exists — it's just unmarked). No new `escape_kind` field yet —
"revealed" is expressed as "the marker gates on F_ROUTE." One flag,
one withheld fact, one late evidence.
