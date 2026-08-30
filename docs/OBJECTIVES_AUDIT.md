# Audit 1c — the legacy Goals / Tasks systems

*2026-08-30. Trace of `src/objectives.py` + `src/mixins/objectives_mixin.py`
against the live World-1 experience. Decision: **remove both.***

## The question

Does anything in the actual World-1 player experience depend on Goals
or Tasks?

**No.** Neither system is seeded, driven, or read by anything the
player interacts with. The game has fully converged on one objective
architecture:

```
WorldFact investigation
        │
   ┌────┴────┐
 Threads   Leads
   │          │
Expedition objective (the mystery)
   │
objective_tick lifecycle  (none→active→distracted→reminder→urgent→complete)
```

Goals and Tasks are competing "what am I supposed to do?" models from
v3, left as no-ops by the v4 investigation rewrite and never removed.

## What the trace found

### Goals

| stage | finding |
|---|---|
| creation / seeding | `game.py:209` → `self.goals = []`. **Never auto-seeded.** The v4 comment at `game.py:203` says the hard-coded goal list is "gone". The only creator is the `go` console command (player types a goal by hand). |
| reads | `_check_and_complete_goals(action)` is called from combat (`kill` ×2), actions (`eat`/`drink`/`medicine`/`craft` ×5), world (`reach_town` ×1), and every turn via `_auto_check_goals()`. Every one of these **iterates an empty list** — pure no-ops. |
| writes / completion | `complete_goal(i)` applies an xp/health/fatigue/food/water/medicine reward. Reachable only via `_check_and_complete_goals` (empty list) or the `complete` console command (needs a hand-entered goal first). |
| persistence | `persistence_mixin` writes `goals` + `last_action`; loads them back if the key is present (replace-not-append, a bug that was fixed once). |
| UI consumers | `go` / `goals` / `complete` console commands — **hidden from `help` and from `_available_commands`** (`test_ui.py` asserts help never mentions them). Classic-mode HUD "Active Tasks" block renders nothing on an empty list. The TUI does not reference goals at all. |

**Net:** dead unless a player manually types `go`. Nothing in the
authored World-1 arc touches it.

### Tasks

| stage | finding |
|---|---|
| generation | `_generate_dynamic_tasks()` — **zero callers.** grep of the whole tree finds no invocation. The "10 %/turn roll in `run_game_loop`" described in a stale `balance_autoplay.py` comment **no longer exists** (`ui_mixin.py:524` comment: "the dynamic task generator is gone entirely"). |
| completion | `complete_task(i)` applies the same reward switch as goals. **No auto-check anywhere** — only the `ct [idx]` console command calls it, and only on an always-empty list. |
| persistence | same as goals — `tasks` key written/read if present. |
| UI consumers | `ts` / `ct` console commands (empty list); classic HUD block (renders nothing). |

**Net:** 100 % dead code. `self.tasks` is `[]` for the entire lifetime
of every session.

### The source of the confusion

`tools/balance_autoplay.py:785` carries a comment claiming "game.py
seeds 6 fixed Goals every game" and "run_game_loop() rolls a 10 %
chance per turn to add a dynamic Task". **Both statements are false as
of v4.** The earlier top-level audit inherited them from this comment.

## "Save-file compatibility"

The saves are local single-player JSON on the developer's machine, with
no format-version field — every field is a best-effort `dict.get()`.
There is no external user base and no requirement to preserve pre-v4
saves. Obsolete `goals` / `tasks` / `last_action` keys in an old save
are **discarded at the load boundary** (we simply stop reading them);
this is an architectural cleanup, not a gameplay change. A save written
by v5 onward just won't contain the keys.

## The removal

Delete:

- `src/objectives.py`, `src/mixins/objectives_mixin.py`
- `ObjectivesMixin` from `Apocrysis`'s bases; the `Goal` import
- `self.goals`, `self.tasks`, `self.last_action` in `game.py`
- all 8 `_check_and_complete_goals(...)` calls (combat ×2, actions ×5,
  world ×1) and the per-turn `_auto_check_goals()` + `last_action`
  assignment + `_map_command_to_action()` in `ui_mixin`
- the `go` / `goals` / `complete` / `ts` / `ct` command entries and the
  classic-HUD "Active Tasks" block
- `goals` / `tasks` / `last_action` from `persistence_mixin` (write and
  read)
- the `ap_tasks` "Task System Integration" block in `cli.py`'s test
  path; the dead goal loop in `test_combat.py`
- the goals/tasks telemetry in `tools/balance_autoplay.py` + the stale
  comment

End state: one objective architecture, no dead competitors.
