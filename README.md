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

python3 apocrysis.py                  # play (textual UI)
python3 apocrysis.py --classic        # play (plain terminal, no textual dependency)
python3 apocrysis.py --no-log         # play without writing a session transcript (logging is on by default)
python3 apocrysis.py --test           # built-in smoke test suite
python3 apocrysis.py --dev --chapter 3   # drop in at the start of a chapter, synthetic state (story inspection)
python3 apocrysis.py --mapgen landscape  # experimental wide-valley map generator (default: v1)
```

Interactive play writes a plain-text transcript automatically — one
file per session, each expedition appended. Toggle it in game with
`log`, or suppress it with `--no-log`.

Everything Apocrysis writes at run time lives under one directory,
`.apocrysis/` (git-ignored), never scattered into the project root:

```
.apocrysis/
├── player/            per-campaign profiles (identity, progression, investigation)
├── saves/             full-state session saves (named slots)
└── logs/
    ├── sessions/      play-session transcripts
    └── telemetry/     bot-run / analysis output (opt-in)
```

Set `APOCRYSIS_HOME` to relocate the whole tree (the test suite points
it at a per-test temp dir). See [`src/runtime_paths.py`](src/runtime_paths.py).

`--mapgen` selects the map generator: `v1` (default, shipped), `v2`
(an irregular-valley experiment, **rejected** — kept for comparison),
or `landscape` (a wide valley with a mountain band and a connected
river; needs a feel-test before it becomes default). See
[`docs/MAP_REALISM_SPEC.md`](docs/MAP_REALISM_SPEC.md).

`--dev` puts a fresh, depth-appropriate survivor at the start of a
chosen chapter (`--chapter 1`–`6`, or `--finale`) in a coherent
world-investigation state — for inspecting one story section, not a
substitute for a full campaign. Sandboxed; see
[`docs/DEV_PLAYTEST.md`](docs/DEV_PLAYTEST.md).

Your name and progress carry forward automatically between expeditions
(a profile: name / level / stats / backpack). Named save slots (`save`
/ `sv`) capture an exact in-progress game for a precise resume.

## The loop

- **Move** `n` `s` `e` `w` (or the arrow keys). The map is a plain
  grid of terrain glyphs — no border, no coordinate ruler (both were
  removed on player feedback; they just invited edge-following). A
  lead you've learned about shows as a `!` marker on the map.
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
- **`escape`** — leave from a distance, once you're sure of the way
  out and the way is open. You don't need this if you just walk to
  the way out itself: **reaching the cleared, confirmed escape tile
  ends the expedition automatically.**

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

- **Start here**: [`docs/SESSION_HANDOFF.md`](docs/SESSION_HANDOFF.md)
  and [`docs/ROADMAP_STATUS.md`](docs/ROADMAP_STATUS.md) — the current
  state, the doc map, and the reading order. Phases A
  (world-investigation spine), B (roguelite inheritance), the Phase C
  geography foundation, the C.3.2a depth-scaling line, and Phase E
  (the full World-1 arc — 25 expeditions, "The Cordon") are complete
  and frozen. Active work is a **blind playtest** of the whole arc
  ([`docs/DEV_PLAYTEST.md`](docs/DEV_PLAYTEST.md)), then a
  spatial-language / attention design pass driven by what it finds.
  Balance and map-growth are frozen for the playtest.
- **Design**: [`docs/ESCAPE_WORLD_DESIGN_ASSESSMENT.md`](docs/ESCAPE_WORLD_DESIGN_ASSESSMENT.md)
  — the original architecture. [`docs/PHASE0_KNOWLEDGE_MODEL.md`](docs/PHASE0_KNOWLEDGE_MODEL.md)
  and [`docs/V3_ASSUMPTION_AUDIT.md`](docs/V3_ASSUMPTION_AUDIT.md) are
  the Stage 1 decision records; `docs/PHASE_*_COMPLETE.md` are the
  frozen as-built specs for each later phase.
- **Layout**: `src/` — `game.py` composes the mixins; `world_mixin`
  orchestrates map generation while `src/worldgen/` (`MapGenerator` +
  `MapGraph`) owns the pipeline and the connectivity guarantee;
  `src/worlds/` is the pluggable world seam (truth DAG, discovery
  bindings, lore); `escape.py` + `mystery_mixin` are the generated
  mystery; `knowledge.py` + `knowledge_mixin` are the four-state
  player knowledge model. Run **both** suites: `python3 apocrysis.py
  --test` (hand-rolled asserts) and `pytest -q` (the `unittest`
  classes) — they catch different bugs.
- **Harnesses**: `tools/mystery_solver.py` drives generated maps to a
  win with BFS and reports the solo solve rate;
  `tools/playtest_three.py` runs a blind three-mystery comprehension
  test; `tools/balance_autoplay.py` is the survival-balance simulator
  (Level 1); `tools/tui_autoplay.py` + `tools/autoplay/` is the
  perception-bounded instrument (Level 2) — a bot that decides only
  from what a player can see, measuring what the game *communicates*
  and whether it is actionable. See
  [`docs/AUTOPLAY_STRATEGY.md`](docs/AUTOPLAY_STRATEGY.md).
- **Known open items** (deferred until after the playtest): combat
  escape-probability vs. threat-tier coherence; building-loot value;
  the `landscape` mapgen feel-test; the spatial-language redesign.
- Full v1→v4 development history is in the git log and on the
  `version-1` … `version-4` branches.
