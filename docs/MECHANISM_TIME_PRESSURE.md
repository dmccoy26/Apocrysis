# Tier-2 mechanism: time-pressure (finish before the world changes) — todo `5761c63f`

The sixth genuinely-different grammar. Player question:
**"what must I finish before the clock runs out — and what can I skip?"**

Every other family rewards *thoroughness* — read every clue, corroborate,
be sure. Time-pressure rewards **triage**: you have a window, the
critical path fits inside it, the optional evidence does not. Learning
to leave the side-trip alone *is* the skill.

## The scenario: `tidal_causeway`

| axis | value |
|---|---|
| family | `time_pressure` |
| discovery | `find_document` (a posted tide table) |
| reasoning | `triage` (new — added to `REASONING_PATTERNS`) |
| resolution | `follow` (walk the causeway; nothing to fix or fetch) |
| confirmation | `traversal` |

Prose chain:

1. `closed` — every road inland is checkpointed or slid.
2. `route` (**the shore station**) — a stone causeway runs out to a
   headland; a footbridge carries on from there, off the map, inland.
   The causeway floods at high water. A tide table is posted here.
3. `obstacle` (**the causeway**) — walkable *now*, at low tide. When
   the tide turns it goes under, chest-deep and rising.
4. `require` (**the tide board**) — the same schedule, read properly:
   the window is real but short, and there's a second low tide after
   dark if you miss this one.
5. Get across before the water. If you don't, wait out the flood
   (~24 turns) and go on the next low tide — you've lost time and
   daylight, not the run. **Soft failure.**

There is **no item and no fix**. The causeway is open when you get
there; the deadline is the whole puzzle.

## What's new vs every other family

`Mystery.deadline` (turns remaining until the tide turns) and
`Mystery.tide_recovery` (turns until it drops again after a flood).
`None` / `0` for the other 9 mechanisms — nothing else changes.

- **Diegetic start.** `deadline` is `None` until `F_ROUTE` lands —
  the clock starts when the *player* learns the causeway exists and
  reads the tide, not at spawn. Reaching the shore station starts it.
- **Per-turn tick.** `world_mixin.move_and_search`, right after
  `_apply_decay()`, calls `_mystery_tide_tick()`. Decrement `deadline`;
  escalating tide banners at 10 / 5 / 2 turns left (tide language, never
  "deadline: 0").
- **Soft failure at 0.** The causeway floods: `obstacle_open` flips
  `False`, a `⚠ THE TIDE HAS TURNED` banner fires, `tide_recovery` is
  set to `flood_recovery` turns. While flooded, walking onto the
  causeway tile just says "wait for the water to drop." When
  `tide_recovery` reaches 0 the causeway reopens (`★ THE TIDE IS OUT
  AGAIN`), `deadline` resets to a fresh window.
- **Crossing is permanent.** Once the player has stood on the escape
  tile with the causeway open, `m.crossed` is set — the tide can't
  trap you on the far side, and `escape` works from anywhere (pacing
  invariant 3d: no post-solution trek, and no cruel re-block).
- **Visible timer.** An objective-panel line ("the tide turns in ~6
  turns" / "the water's over the causeway — next low tide in ~15") and
  a HUD `WARNINGS` line when it's close.

## `build_mystery` changes

Guarded on `spec.get('deadline_turns')`:

- `m.obstacle_open = True` at build (the tide is out when the mystery
  starts; there is nothing to unlock).
- `m.deadline = None`, `m.tide_recovery = 0` — the mixin arms the
  clock when `F_ROUTE` becomes known.
- The `route` site is placed nearest the carved gap (same as
  transportation — the causeway runs to the valley's edge).
- `require` (the tide board) is a *short* side-trip: reading it is the
  optional-evidence-you-can-skip that the triage lesson is about. It
  still carries a second `F_REQUIRE` route so the fact stays redundant.
- `item` is `None`; `E_require_b` uses the tide-board text
  (`spec['require_ev']`), not "you find the None here".
- `_req_line` (the `F_REQUIRE` fact) comes from `spec['require_fact']`
  ("The tide runs on a schedule you can read and plan around.").

## Mixin changes (`mystery_mixin.py`)

- `_mystery_obstacle_ready()` — time-pressure branch: `m.obstacle_open`
  (the tide state is the gate; `m.crossed` overrides).
- `_mystery_arm_deadline()` — called from `mystery_arrive` /
  `_mystery_progress_flare` when `F_ROUTE` is newly known and
  `spec.get('deadline_turns')`: `m.deadline = spec['deadline_turns']`,
  banner `★ NEW LEAD — the tide is going out` with the window.
- `_mystery_tide_tick()` — the per-turn state machine above.
- `mystery_bump_obstacle()` — time-pressure branch: if flooded, "the
  water's over the causeway — {n} turns to the next low tide"; if open,
  fall through (you can walk on).
- `mystery_arrive()` escape branch — set `m.crossed = True` when the
  player reaches the escape tile with the causeway open.
- `mystery_try_escape()` — allow when `m.crossed` even if a later
  flood closed `obstacle_open`.

## TUI (`tui.py`)

- `_objective_steps` time-pressure branch: the route/obstacle steps,
  then a live `▸ cross now — the tide turns in ~{n}` hot line (or
  `☐ wait for the tide — ~{n} to the next low water` when flooded),
  then `escaped by the causeway`.
- `_status_block` WARNINGS: `the tide turns in ~{n}` when
  `0 < deadline <= 8`, `causeway flooded — ~{n} to low tide` when
  flooded.

## `balance_autoplay.py`

The bot already beelines the escape tile once the route sites are
searched, so it triages by accident (it never takes optional
detours). Two tweaks:

- `_next_mystery_move`: for a `deadline`-carrying mystery, skip the
  `require` (tide-board) search — go straight route → escape. This is
  exactly the triage a focused player does.
- If the causeway floods mid-approach (`not m.obstacle_open` and no
  item family), keep pathing to the escape tile and let the bump/wait
  play out; the tick reopens it.

Expect forced `tidal_causeway` bot survival **below** the ~85.8%
baseline — the family is *meant* to be lost by dawdling, and the bot
dawdles when a flood adds ~24 idle turns of attrition. Report it,
don't tune it. The held line is the **unforced aggregate** staying in
noise (time-pressure is 1-in-10 of expeditions).

## Balance guardrail

`deadline_turns` and `flood_recovery` are **not** balance numbers in
the frozen sense (combat / hunger / thirst / encounter / loot / map
growth). They're the mechanism's own difficulty dial and may be tuned
off a real player's first reach. Start: `deadline_turns = 22`,
`flood_recovery = 24`. The critical path (spawn → shore → causeway →
gap) on a median map is ~15–20 steps, so a focused player clears it
in one window and a wanderer eats a flood.

## Scope guard

One new mechanism, one new reasoning-vocabulary word (`triage`), two
new `Mystery` fields, one per-turn hook. No region mutation, no
`escape_kind`, no movement cap, no change to decay rates. The tide is
a property of one mystery, not a world system.
