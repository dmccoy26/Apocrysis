# Pacing: mystery-to-exit continuity (schema invariant 3d)

**The critical path of an escape story must create geographic progress
toward the escape, and resolution must not require an unrelated
post-solution trek.**

## Why

5 playtests (2026-08-28), every death: solve the mystery in the
near-spawn cluster, then die on a long solo march to the far-corner
escape gap — combat + resource attrition on turns that add nothing to
the investigation. The bot's ~86% survival can't see this (straight
lines, no wasted turns, optimal weapon). Maps grow +3/expedition, so
the tax scales exactly as the campaign tightens.

This is **pacing**, not combat balance. Combat/resource numbers stay
frozen while fixing it.

## Lever A — DONE (`c816232`)

Informational (`reveals_route`): `H_escape.confirmed_by =
E_route_reveal`. The radio response confirms the hypothesis the moment
it fires, `obstacle_open` flips, and `mystery_try_escape` already lets
a confirmed + open mystery be left from anywhere ("You follow the
directions off the ridge and keep going"). The walk is narrated, not
played. `E_confirm` at the gap still exists as optional flavour.

## Lever B — DONE (`build_mystery` + `_carve_escape_pass`)

Shipped. `_carve_escape_pass` picks the ~65th-percentile gap by spawn
distance (not the max). `build_mystery` scores sites by `_detour(p) =
(spawn→p + p→exit) − spawn→exit` and assigns: `closed` near spawn,
`route` = lowest-detour in the 25–85% band of the spawn→exit run,
`require`/`power` = lowest-detour capped at `map_size*0.5`. Falls back
to the old logic on an empty filtered pool.

**Measured (24² maps):** last-action-site→exit ~20→~15 avg, worst
39→23. spawn→exit 30→20. **Bot (3 seeds): survival ~85.2% (baseline
~85.8%), 100% combat deaths, median expedition 43→27 turns.**

### Original plan (kept for reference)


Give the **critical-path** sites geographic momentum toward the exit.
Side roles (`require`, `power`) may still be detours, but bounded ones.

### B1. `_carve_escape_pass` — stop always picking the farthest gap

Today: `max(reachable_gaps, key=distance-from-spawn)` — "escape should
feel like a journey." Change to a gap at a **moderate** distance (e.g.
the ~65th-percentile reachable gap by spawn distance, or clamp the max
to `spawn_dist <= map_size * 0.8`). Keeps a sense of journey without a
half-map hike on a 34².

### B2. `build_mystery` — lay the critical path along spawn→exit

After `m.escape_tile` is known, score every reachable building site by
its **detour cost**:

```python
def detour(p):
    return (dist(spawn, p) + dist(p, exit)) - dist(spawn, exit)
```

Sites on the direct line score ~0; sites off to the side score high.

- `closed` — keep near-spawn (it's where you came in). `sites` is
  already nearest-spawn-first; `near[0]`.
- `route` — lowest-detour site whose `dist(spawn, p)` is in the middle
  band (roughly 30–70% of `dist(spawn, exit)`). This is the site that
  turns "wander to find the mystery" into "head toward the way out."
- `require`, `power` — lowest-detour sites overall, but allow a real
  detour (cap `detour(p) <= map_size * 0.4`) so they still feel like a
  side-trip, not a straight shot.
- `obstacle` — unchanged (it IS `inner_tile` at the gap).

### Graceful degradation

On a small / sparse map the banded/low-detour pool can come up empty.
Fall back to the current logic (`near[1]` for route, shuffled remainder
for require) whenever a filtered pool has < 1 candidate. Never fail
generation over placement aesthetics.

### Per-family expression (design intent, not all code)

| family | resolution lands you… |
|---|---|
| spatial | at the pass you cleared — it **is** the exit |
| infrastructural | at the gate you powered — it **is** the exit |
| experimental | on the road the dam just uncovered |
| informational | wherever you are (lever A) |
| sequential | on the trail network you assembled |
| transportation | at the vehicle you repaired — leave from there |
| environmental | on the road the drain/clear exposed |

`obstacle == exit` already holds for spatial/infrastructural. The
others need `m.escape_kind ∈ {gap, vehicle, revealed}` (schema §4) —
later; B1+B2 is the immediate win for all of them.

## Validation for B

- All 7→8 mechanisms still `validate()` across ≥8 seeds.
- `_ensure_reachable` still carves every moved site reachable.
- Bot run (unforced, ≥300 games, ≥3 seeds): survival within noise of
  the ~85.8% baseline; **median turns-to-win should DROP** (less dead
  walking) — that's the signal B worked.
- A human playtest: does "solve then trek" still happen?
