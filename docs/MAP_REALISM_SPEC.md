# Map realism — aspect ratio, terrain mass, river crossings (spec)

Owner-raised 2026-08-30 from the `--dev` playtests. Three separate
problems, three different sizes and risk levels.

> **Freeze note.** `map growth` and `map generation` are on the frozen
> balance list (`PHASE_C_FOUNDATION.md`), and **C.3 v2 — a prior
> map-generation rework — was REJECTED after the owner's feel-test**
> (`PHASE_C3_SPEC.md`: "irregularity alone ≠ meaningful navigation").
> A second map-gen change gets the same rigour: spec → flag-gated,
> reversible build → feel-test → owner verdict. Nothing here ships on
> `main`'s default generator without that.

---

## Problem 1 — the map renders portrait, not landscape

The tile array is **square** (`map_size × map_size`). A terminal
character cell is roughly **2:1** (twice as tall as wide), so a 34×34
grid of glyphs renders as a tall portrait rectangle and wastes the
terminal's horizontal space.

### Fix A (cheap, no generator change) — render each tile 2 chars wide

`ui_mixin._render_map_lines` (and the `tui.py` map panel) emit each
tile as **two characters** (`"Z "` / a glyph + a space, or a
double-width glyph). A 34×34 grid then renders ~68×34 on screen —
square-to-landscape, using the horizontal space.

- Zero change to generation, `MapGraph`, `reachable`, `escape.py`, the
  golden fixture, `scale_report.py`, or any coordinate.
- Reversible (a render constant).
- Tests that index rendered lines by column need the ×2 (a handful in
  `test_ui.py` / `test_worlds.py` — small).
- **This is the recommended fix for the aspect-ratio complaint.**

### Fix B (large) — a true `width × height` landscape grid

`map_size` becomes `map_w × map_h` with `map_w ≈ 1.6 × map_h`.
`map_size` is a single scalar used ~30× in `generator.py` alone (both
`range(map_size)` axes, the `map_size - 1` boundary index), plus
`graph.py`, `reachable.py`, `escape._carve_escape_pass` (iterates the
4-sided ring), `world_mixin.generate_map`, the growth formula, the
golden fixture, `scale_report.py`'s whole circuit model, the `--dev`
depth math, and dozens of tests.

**This is a multi-day cross-cutting refactor** and it re-opens every
number in the C.3.2a line (the survival-budget model, the lever
matrix, C.3.2a-7's `depth_supply_bonus` calibration — all assume `n²`).
Only worth it if Fix A's rendered landscape still feels wrong in the
feel-test. **Not recommended first.**

---

## Problem 2 — rivers and mountains are 1-tile features

Today: the boundary ring is 1-tile-thick `mountain`; interior
`mountain`/`river` obstacles are single tiles
(`generator.py` `_terrain_for_chunk` → `rng.choice(['mountain',
'river'])`). A mountain occupies the same footprint as a house; a river
is a puddle, not a barrier.

### 2a. Mountains as mass

- The boundary becomes a **band** (2–4 tiles thick, thicker at the
  corners) instead of a 1-tile ring. `force_boundary_ring` →
  `force_boundary_band(thickness)`.
- Interior mountains generate as **blobs** (a seed tile + grow 4–10
  connected tiles), not singletons. Reuse the seed-and-grow code from
  the parked C.3 v2 `_grow_valley_mask` — it already does connected
  region growth.
- Mountains still can't sit on the required circuit
  (`MapGraph` connectivity guarantee is unchanged — an unreachable
  required node still raises).

### 2b. Rivers as a connected boundary

- One river **path** per map: a connected `river` line from one map
  edge to another (or to the mountain band), 1–2 tiles wide, meandering
  (a drunkard's walk between two edge points).
- It genuinely **partitions** the interior — the required circuit may
  have to cross it (that's the point of Problem 3).
- `MapGraph` still must find every required node reachable; the river
  crossing (Problem 3) is what keeps it reachable.

### Risk

This is exactly where C.3 v2 died: *"irregularity alone ≠ meaningful
navigation."* A connected river is only good if crossing it is a
**legible decision** (a visible bridge, a signposted ford) — not
another wall the player bounces off. Problem 3 is not optional here;
2b + 3 ship together or not at all.

---

## Problem 3 — crossing a river

Today `river` is in `IMPASSABLE_TERRAIN` — a hard "you can't cross the
river here", same as a mountain. (`water` is separate — passable, slow,
wadeable with waders.)

### 3a. Bridges

- The river generator places **1–2 `bridge` tiles** on the river path
  (passable, rendered distinctly, ideally near where the required
  circuit wants to cross).
- A found map / the objective panel can mark the nearest bridge — a
  real navigational affordance (feeds C.3.2's lead-vs-texture work).

### 3b. Swim attempt (a real choice with a real cost)

At a `river` tile, `move_and_search` offers: *try to swim across?*

- Success chance derived (not raw): base ~55 %, +dexterity, −fatigue,
  −current health penalty, − if carrying a lot; **waders** raise it a
  lot (they already exist for water/swamp).
- **On success:** cross, but lose time + a chunk of fatigue, and a
  chance to lose a non-equipped item downstream.
- **On failure:** swept back to the near bank, HP + fatigue hit, a
  chance to drop an item. Not death directly — attrition.
- Reuse the encounter-card pattern (`COMBAT_INFO_SPEC.md`): show the
  swim %, the cost, and the consequence **before** the player commits.

### Risk

3b is a **new failure mode** (drowning-adjacent attrition) — that is a
balance change. It needs the same before/after `balance_autoplay.py`
check the combat card got, and the bot needs a swim/bridge heuristic
(prefer the bridge; only swim when the detour is large).

---

## Recommended sequencing

1. **Now (if the portrait look is hurting the playtest):** Fix A — the
   2-char render. Cheap, isolated, reversible, not frozen-adjacent.
2. **After the current blind playtest completes:** fold Problems 2 + 3
   into the post-playtest map/navigation design pass. The playtest is
   already surfacing navigation and pacing findings; a river/mountain
   rework should be designed against **all** of them together, per the
   owner's own "playtest → then design the visual/spatial language"
   principle — not piecemeal mid-playtest.
3. When built: `Apocrysis(mapgen="v1" | "landscape")`, default `"v1"`,
   byte-identical with the flag off (the C.3 pattern). Feel-test at
   depth 4 and depth 10. Owner verdict before the default flips.

## Open owner decisions

- **Un-freeze map generation for this?** (It is on the frozen list.)
- **Now, or after the playtest?**
- **Fix A alone might be enough for "landscape"** — do you want the
  cheap render change first and then judge whether B/2/3 are still
  wanted?

---

## STATUS (2026-08-30)

Owner decision: **Fix A now; Problems 1b / 2 / 3 deferred to the
post-playtest design pass.**

- **Fix A SHIPPED** (`ui_mixin._render_map_lines`: `line += char + " "`).
  Each tile renders as glyph + space; a 34×34 array now fills 68×34 on
  screen — landscape. Zero generation change, no coordinate touched,
  fully reversible. `test_ui.py`'s `_tile_char` helper updated for the
  ×2 column. 308+100 green.
- **1b (true `w×h` grid) / 2 (terrain mass) / 3 (bridges + swim)** —
  NOT started. Revisit as one design pass after the blind playtest,
  flag-gated + feel-tested like C.3. Map generation stays frozen until
  then.

---

*Fix A shipped (render width, low-risk). The rest is deferred - map
generation is frozen and a prior rework was rejected; the terrain /
river work waits for the post-playtest design pass.*
