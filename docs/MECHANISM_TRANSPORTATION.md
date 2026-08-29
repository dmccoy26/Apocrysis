# Tier-2 mechanism: transportation (the way out is a machine) — todo `17f2a0ca`

The fifth genuinely-different grammar. Player question:
**"the way out isn't a place — it's a machine, and it needs more than
one thing before it'll run."**

Every other family so far has a single requirement (spatial: one key;
infrastructural: one fuel applied down a *chain*; experimental: no item,
a control; informational: one fuel for the transmitter). Transportation
is the first with **two parallel requirements** — a checklist, not a
chain. You can fetch them in any order; the machine teaches you the
missing half.

## The scenario: `airfield_plane`

| axis | value |
|---|---|
| family | `transportation` |
| discovery | `find_object` (a plane tied down on a strip) |
| reasoning | `sequence` (assemble what it needs — order-free) |
| resolution | `repair` (fit the parts) |
| confirmation | `traversal` (the engine catches, you lift off) |

Prose chain:

1. `closed` — every road out ends at a checkpoint or a slide.
2. `route` (**the airstrip**) — a crop-duster, tied down on the grass.
   Small, but it flies. Sits right where the valley opens up.
3. `obstacle` — it won't start: the propeller's off the shaft and the
   tanks read empty.
4. `require` (**the hangar**) — the propeller, racked on the wall.
5. `require2` (**the field store**) — a drum of avgas and a hand pump.
6. Bring both to the plane, either order. Fit the prop, fill the
   tanks → the engine turns over and catches → you taxi out and lift
   off. `escape` from the strip.

The two items are **independent**. Getting the fuel first doesn't
depend on having the prop, and vice-versa. That's what makes it a
different problem from `power_station`'s gate ← hydro ← generator ←
fuel chain, where the order is forced.

## What's new vs the single-item families

`requirement_item` (one string) stays for the other 7 mechanisms.
Transportation adds:

- `Mystery.requirement_items: list[str]` — every item the machine
  needs. Defaults to `[requirement_item]` for a single-item mechanism,
  so nothing else changes. Transportation sets it to two.
- A second requirement site, role `require2`, with its own item, label
  and evidence (`E_require2_a` observe + `E_require2_b` "you find the
  {item2} here" search). Supports `F_REQUIRE` — the fact is "the way
  needs things", plural.
- `_mystery_has_all_items()` / `_mystery_missing_items()` on the mixin.
- `_mystery_obstacle_ready()` transportation branch: `all items held`.
- `mystery_bump_obstacle` transportation branch: name the missing
  item(s) if you're short; "the engine catches" (open) when you have
  them all and walk up to the plane.
- Objective panel: a transportation branch listing each item with its
  own ✓ / ▸ and a compass heading to its site.
- `to_dict` / `from_dict` round-trip `requirement_items`.

**Not in v1:** `escape_kind = 'vehicle'` (leave from wherever the
machine is, no mountain gap). The plane is placed adjacent to the
carved gap and you cover the last tile — mechanically the exit is
still a gap tile. The "leave from the machine's location" variant is a
later change; it isn't what makes transportation a distinct *question*.

## `build_mystery` changes

Guarded on `spec.get('item2')`:

- `m.requirement_items = [spec['item']] + ([spec['item2']] if spec.get('item2') else [])`
  (always at least the one item; `requirement_item` still = `spec['item']`).
- After the normal `require` placement, place a `require2` site from
  the low-detour pool (a side-trip, like `require`), label it from
  `spec['roles']['require2']`, index its evidence.
- The `route` site is placed adjacent to `m.escape_tile` when
  `spec.get('item2')` — the plane sits at the valley's edge, so
  "head for the airstrip" and "head for the way out" are the same
  vector (pacing invariant 3d).
- `E_require2_a` / `E_require2_b` added to the evidence list, both
  supporting `F_REQUIRE`.

## Validation

`validate()`: if `requirement_items` has >1 entry, every entry must be
non-empty and `require2` must be in `m.sites`. `F_REQUIRE` still needs
≥2 evidence routes (it has E_require_a/b + E_require2_a/b + E_route_b).

## Scope guard

Two items, not N. One extra site. No `escape_kind`. No region
mutation. The obstacle is a bool flip when the checklist is complete,
same as every other family — the checklist just has two boxes.
