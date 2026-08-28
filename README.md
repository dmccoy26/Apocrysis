# Apocrysis

A procedural **investigation game** with a terminal UI. You wake in an
unfamiliar valley after the outbreak. The road you came in on is gone.
Every valley has a way out for someone who understands it — a service
road, a rail tunnel, a foot pass over the ridge, a boat, an old
evacuation corridor. Nothing marks it. You have to work out what this
place *was* and where it has to give.

Survival — hunger, thirst, zombies — is the pressure, not the point.
Playing well means building an accurate picture of a strange place and
using it to make good decisions.

```
survive → notice something → investigate → form a hypothesis →
test it by exploring → find what you need → take the route out
```

## Running it

```bash
pip install -r requirements.txt

python3 apocrysis.py             # play (textual UI)
python3 apocrysis.py --classic   # play (plain terminal, no textual dependency)
python3 apocrysis.py --slice     # the fixed "Dam Service Road" tutorial mystery
python3 apocrysis.py --log       # play, writing a transcript for later analysis
python3 apocrysis.py --test      # built-in smoke test suite
```

Your name and progress carry forward automatically between expeditions
(a profile: name / level / stats / backpack). Named save slots (`save`
/ `sv`) capture an exact in-progress game for a precise resume.

## The loop

- **Move** `n` `s` `e` `w`. The map is lettered down the side and
  numbered across the top — the top-left tile is `a1`, one right is
  `a2`, one down is `b1`.
- **`look`** — take stock of where you're standing. Some things you
  notice just by being there.
- **`search`** — go through a place properly. Records, notes, the
  things that aren't obvious.
- **`journal`** (`j`) — everything you've found, and what it tells
  you. Your memory, not a quest list.
- **`remember`** — think it over. A synthesis of where your
  understanding stands right now.
- **`inspect <thing>`** — what you actually know about one thing:
  *Observed*, *Known*, *Suspected*, or nothing yet.
- **`clear`** / **`open`** — get past the obstacle on the escape
  route, once you have what it takes.
- **`escape`** — leave. Only works once you're sure of the way out
  and the way is open. Standing in the right place isn't enough.

The full command list is in [`commands.md`](commands.md); `help` in
game shows what's available right now.

## What you never see

There are no quest markers, no objective text, no "OBJECTIVE:
open the gate." The generator knows the answer and deliberately
obscures it; you reconstruct it from evidence. `journal` and
`remember` exist so you're never asked to remember an obscure line
from forty screens ago — the challenge is recognising the
*relationship* between things you've found, not that you found them.

The Town Center is the most information-dense place on the map. It is
not the way out.

## The knowledge model

Every expedition is a small mystery: **facts** (what's true about this
place), **evidence** (what you find that establishes them — with more
than one route to anything that matters, so you can miss a clue and
still solve it), **deductions** (what the facts add up to), and one
**hypothesis** (the way out). Your knowledge of the hypothesis moves
`unknown → suspected → confirmed` on its own as you find things —
there's no command to "confirm" anything.

## For developers

- **Design**: [`docs/ESCAPE_WORLD_DESIGN_ASSESSMENT.md`](docs/ESCAPE_WORLD_DESIGN_ASSESSMENT.md)
  — the full architecture. [`docs/VERSION_4_BUILD_ORDER.md`](docs/VERSION_4_BUILD_ORDER.md)
  is the implementation sequence and current status;
  [`docs/PHASE0_KNOWLEDGE_MODEL.md`](docs/PHASE0_KNOWLEDGE_MODEL.md)
  and [`docs/V3_ASSUMPTION_AUDIT.md`](docs/V3_ASSUMPTION_AUDIT.md) are
  the Stage 1 decision records.
- **Layout**: `src/` — `game.py` composes the mixins; `world_mixin`
  generates the map; `escape.py` + `mystery_mixin` are the generated
  mystery; `knowledge.py` + `knowledge_mixin` are the four-state
  player knowledge model; `slice_dam_road.py` + `slice_mixin` are the
  hand-authored tutorial. `src/tests/` is the suite (`python3
  apocrysis.py --test`, or `pytest src/tests/`).
- **Harnesses**: `tools/mystery_solver.py` drives generated maps to a
  win with BFS and reports the solo solve rate;
  `tools/slice_playtest.py` runs the tutorial's three-situation test;
  `tools/balance_autoplay.py` is the survival-balance simulator.
- **Known open item**: combat lethality vs. investigation length is
  still being tuned — see the build order's Stage 4 notes.
- Full v1→v3 development history is in the git log and on the
  `version-1` / `version-2` / `version-3` branches.
