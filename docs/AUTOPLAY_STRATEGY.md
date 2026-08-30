# Autoplay strategy — using bots to game-test Apocrysis

**Status:** proposal. Nothing here is built beyond what already exists
(`tools/balance_autoplay.py`). Do not start the new work until **run 7**
(the human straight-through campaign, `docs/DEV_PLAYTEST.md`) is done —
autoplay is a tool for the *post-playtest* design pass, not a
substitute for it.

---

## The one principle: the I/O seam is the automation interface

Apocrysis already has a clean seam. Every mixin talks to the outside
world through `self.io` — never a bare `print()` / `input()`:

| implementation | file | driver |
|---|---|---|
| `ConsoleIO` | `src/io_console.py` | a human at a plain terminal |
| `TextualIO` | `src/tui.py` | a human in the Textual TUI |
| `TeeIO` | `src/playlog.py` | wraps another IO, writes the transcript |
| `BotIO` | `tools/balance_autoplay.py` | **a bot** |

The interface is tiny: `say(*args)`, `ask(prompt)`, `ask_yes_no(prompt)`,
`ask_combat_letter()`. `say()` receives **exactly the text a player
reads** — the same strings the TUI renders. A bot that decides only
from `say()` output plus the public player state is, for testing
purposes, playing the same game a human plays.

**We do not drive the real TUI over a PTY (pexpect / tmux / expect).**
Reasons:

- Textual repaints the whole screen into an alternate buffer; parsing
  that ANSI stream is fragile and every render tweak breaks it.
- The parser you'd write is the regex layer that's *already* in
  `BotIO` — you'd be maintaining a second, worse copy over a
  timing-dependent transport.
- The things a PTY bot would supposedly catch (attention hierarchy,
  navigation confusion) are **human-cognition failures**. A bot either
  reads the objective's coordinates (navigates perfectly, tells us
  nothing) or reads the rendered text (which is what `BotIO` on the
  seam already does, without the PTY).

Textual's own in-process `Pilot` harness (`App.run_test()`) is the
sanctioned way to exercise the real widget tree — see Level 3 — and it
needs no PTY.

---

## What we have today — Level 1: balance simulation

`tools/balance_autoplay.py` plays full games/campaigns headless through
`BotIO`. It already gives real numbers for:

- win / death / timeout rate, turns, days, final level
- death-cause inference (zombie hit, bleed/poison tick, cold water,
  starvation) from the `say()` stream
- damage dealt/taken per hit by level, crits, fights, zombies defeated
- weapons/armor looted vs the expedition band, crafts, duplicate drops
- food/water/med/ammo **acquired vs consumed**, resource trajectories
- tiles moved, terrain histogram, max distance from spawn, day-phase
  and visibility sampling
- `--expeditions-completed` sweeps (map/loot/zombie difficulty axis)
  independent from `--level` (starting combat stats)

Run it:

```bash
python3 tools/balance_autoplay.py --games 200
python3 tools/balance_autoplay.py --expeditions-completed 6 --games 200
python3 tools/balance_autoplay.py --level 5 --seed 42 --verbose
```

### Where Level 1 deliberately "cheats"

`BotIO._next_mystery_move()` navigates by reading the mystery's
internal structure directly — `m.sites[role]`, `m.obstacle_tile`,
`m.escape_tile`, `m.correct_control`. The code comments already call
this out: *"a comprehension proxy, not a solver of the 'which one'
puzzle — that's the human test's job."*

That is the right call for a **balance** bot: you want it to reliably
reach the escape so you can measure the survival economy along the
way. But it means Level 1 **cannot tell us anything about whether the
game communicates the objective** — the bot is omniscient about
*where*, and only tested on *survival*.

That gap is the whole point of Level 2.

---

## Level 2: the perceived-information bot (the addition worth building)

**Question it answers:** *can a player who only has what the screen
shows actually find and pursue the objective?* — an objective
usability test, not a balance test.

### The rule

A new `--perceived` mode for the autoplay bot. In this mode the bot's
**policy** may read only:

- text it has parsed from `say()` (story stream, encounter cards,
  `NEW LEAD` / `OBJECTIVE` lines, hypothesis banners)
- values a human sees in the HUD: health, hunger, thirst, fatigue,
  food/water/med/ammo counts, current biome label, day/phase,
  the ESCAPE panel checklist and its heading/landmark text
- the **rendered** map view (the same tiles/glyphs the player sees,
  with the same fog — expose this as a plain grid from the render
  layer, not the full `p.map`)

It may **not** read: `m.sites`, `m.obstacle_tile`, `m.escape_tile`,
`m.correct_control`, `p.map` (unfogged), `worldgen` graphs, the RNG,
zombie internal stats, or the analyst line in the playlog header.

Movement is still `n/s/e/w` (or arrows) — and the bot must **derive**
those from whatever spatial language the game gave it, exactly as a
player must. If the game says "south-west" and provides no reference
frame, the bot has the same problem the player does. If the game says
"head toward the water tower" and the tower is a glyph on the rendered
map, the bot can pathfind to that glyph.

### The bot does not "understand directions" — it exposes whether a plan can be built

This is the design stance, and it is what makes Level 2 a real test
rather than a rationalisation:

**The perceived bot is not built to follow instructions. It is built
to expose whether the information the game presents is enough for an
agent with no privileged knowledge to form and maintain an actionable
plan.**

So when the game says *"the evacuation corridor lies south-west,"* the
bot must **not** silently translate that into a coordinate vector
because the harness happens to know where the target is. It records
what it actually received:

```
objective_text_seen   = true
destination_named      = false
spatial_relation       = "south-west"
reference_frame        = none   ← no cardinal UI, so this relation is
                                  semantically valid but operationally
                                  useless
```

That is precisely what the five failed CH3 runs are telling us. Run 6
is the other side: `NEW LEAD → Generator Shed → marked on your map →
checklist → "take it back, west"` gives an agent enough to build and
hold a plan.

### Information *received* vs. information *actionable*

Every objective-related metric is recorded as a pair — was it
presented, and was it usable — so a failure separates cleanly into
"the player wasn't told" vs. "the player was told, but the information
wasn't usable":

| received | actionable | meaning |
|---|---|---|
| `objective_text_seen` | `objective_destination_named` | told there's a goal / told *what/where* it is |
| `direction_text_seen` | `direction_operational` | a spatial relation was stated / the bot could act on it (a reference frame exists) |
| `landmark_named` | `landmark_visible` | a landmark was named in text / that landmark is actually on the rendered map |
| `map_marker_present` | — | the ESCAPE panel / map shows a marker for the destination |

`direction_operational` is the key one for the current problem:
"south-west" with no compass UI is `direction_text_seen: true,
direction_operational: false`. A named landmark that the bot can find
as a glyph is `landmark_named: true, landmark_visible: true`.

### Policies

Keep them small and named, selectable with `--policy`:

| policy | behaviour |
|---|---|
| `random` | legal random walk — the null baseline |
| `survival` | eat/drink/med/fight/loot; no objective-seeking |
| `explorer` | survival + "visit unseen tiles" — models the loot loop |
| `objective` | survival + pursue the objective **using perceived text only** |
| `humanlike` | `objective`, but drops the objective after N turns without progress and reverts to `explorer` for a while — models the run-6 jerrycan decay |

### Metrics Level 2 adds

Per run, machine-readable (JSON lines):

```json
{
  "seed": 12345,
  "chapter": 3,
  "policy": "objective",
  "nav_phrasing": "cardinal",
  "outcome": "died",
  "turns": 91,
  "objective_text_seen": true,
  "objective_destination_named": false,
  "direction_text_seen": true,
  "direction_operational": false,
  "landmark_named": false,
  "landmark_visible": false,
  "map_marker_present": false,
  "objective_reached": false,
  "turns_to_objective": null,
  "turns_pursuing_vs_wandering": [23, 68],
  "hypothesis_formed": false,
  "hypothesis_corrections_seen": 0,
  "facts_found": 2,
  "facts_available": 9,
  "backtrack_ratio": 0.41,
  "revisit_ratio": 0.55
}
```

The headline numbers: **`objective_reached` rate** and
**`turns_to_objective`**, by policy and by phrasing.

### The A/B protocol — what makes the spatial-language work measurable

Once the attention/spatial-language redesign exists behind a flag,
this is the objective test of it:

```bash
python3 tools/tui_autoplay.py --policy objective \
    --nav-phrasing cardinal  --chapter 3 --games 500 --json out/cardinal.jsonl

python3 tools/tui_autoplay.py --policy objective \
    --nav-phrasing landmark  --chapter 3 --games 500 --json out/landmark.jsonl
```

If "landmark + marked on map" phrasing does not move
`objective_reached` and `turns_to_objective` for the `objective`
policy, the redesign didn't work — regardless of how good it looks.
Run the same A/B with `--policy humanlike` to check whether the
attention **lifecycle** (`NEW → ACTIVE → REMINDER → URGENT`) actually
pulls a wandering bot back.

### Build shape

```
tools/
    balance_autoplay.py   # unchanged - the Level 1 balance lab
    autoplay/
        __init__.py
        botio.py          # BotIO, lifted out of balance_autoplay, + PerceivedBotIO
        perceive.py       # the "what the screen shows" view: parsed say() log,
                          #   HUD snapshot, fogged render grid, ESCAPE panel
        policies.py       # random / survival / explorer / objective / humanlike
        metrics.py        # Level 1 Metrics + the Level 2 comprehension counters
    tui_autoplay.py       # CLI: --policy --perceived --nav-phrasing --chapter
                          #   --games --seed --json
```

`balance_autoplay.py` keeps working as-is (import `BotIO` from the new
module, or leave a shim). No engine changes except **exposing the
fogged render grid and the ESCAPE-panel text as plain data** — which
is useful for the TUI itself anyway.

---

## Level 3: visual snapshots — later, once

For reviewing whether the *visual* language reads (colour, glyph,
hierarchy), not for the balance loop.

Use Textual's in-process harness:

```python
async with ApocrysisApp(...).run_test() as pilot:
    await pilot.press("e", "e", "e")
    pilot.app.save_screenshot("out/spawn.svg")
```

Drive a scripted or `objective`-policy run and `save_screenshot()` at
named moments: spawn, objective discovered, zombie encounter, low
water, critical HP, new clue, town arrival, hypothesis correction,
death, finale. ~50–200 runs, eyeball the SVGs. Do this when the
visual-language spec is being reviewed, not continuously.

---

## What autoplay cannot tell us — keep the human runs

- whether the story makes you **want** to know what happens next
- whether a discovery **feels** meaningful or the finale **feels**
  earned
- whether a location reads as a place or a container for rolls
- whether the writing lands

`docs/DEV_PLAYTEST.md` runs, `tools/playtest_three.py` blind
comprehension runs, and `docs/PLAYER_UNDERSTANDING.md` stay the
authority on those. Autoplay tells us **what the game communicates and
what decisions that produces**; humans tell us **how it feels**. The
balance bot can prove food is sufficient; only the perceived bot can
show the player never finds it; only a human can say the chapter was
boring.

---

## Sequencing

1. **Run 7** — human straight-through campaign. Nothing below starts
   before this is logged.
2. Design the attention / spatial language from runs 1–7 (see
   `docs/DEV_PLAYTEST.md` conclusion + `docs/ATTENTION_SYSTEM_SPEC.md`).
3. Build **Level 2** (`--perceived` bot + `objective`/`humanlike`
   policies + comprehension metrics). ~1–2 days on existing code.
4. Run the **A/B** (cardinal vs landmark; static vs lifecycle) to
   validate the redesign with numbers.
5. Extend **Level 1** telemetry as balance questions come up from the
   full-campaign evidence.
6. **Level 3** screenshots only when the visual spec is under review.
