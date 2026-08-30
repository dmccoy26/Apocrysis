# tools/autoplay — the perception-bounded instrument

Built during the run-5/6 playtest analysis. See
`docs/AUTOPLAY_STRATEGY.md` for the why.

## What it is

A bot that plays the **real game** through the `self.io` seam and
decides **only from what a player can see** that turn — HUD numbers,
the fogged map grid, the `say()` stream, the ESCAPE panel. It does not
read `player.map` (unfogged), `mystery.sites`, `mystery.escape_tile`,
the RNG, or zombie internal stats.

Purpose: measure **what the game communicates and whether it is
actionable** — not "can the bot win". Objective facts are recorded as
received/actionable pairs (`direction_text_seen` vs
`direction_operational`, `landmark_named` vs `landmark_visible`).

## Run it

```bash
python3 tools/tui_autoplay.py --policy explorer --chapter 3 --games 50
python3 tools/tui_autoplay.py --policy survival --games 100 --json out/s.jsonl
python3 tools/tui_autoplay.py --policy random --seed 1 --games 1 --verbose
```

`--chapter 1..6` drops in with synthetic state (like `--dev`); omit for
a fresh expedition-1 start. `game N` uses `--seed + N`; a given
`(seed, policy, chapter)` is reproducible.

## Layout

| file | what |
|---|---|
| `perceive.py` | `Perception` (one turn's visible state) + `build_perception()` |
| `metrics.py` | `RunRecord` — the received/actionable comprehension flags + outcome |
| `policies.py` | `random` / `survival` / `explorer` — baseline only |
| `runner.py` | `PerceivedBotIO` + `run_one()` |
| `../tui_autoplay.py` | CLI + summary |

## Instrument phase — what is deliberately NOT here

- **`objective` / `humanlike` policies.** An objective-seeking policy's
  behaviour depends on the spatial language the redesign introduces —
  built after the design pass.
- **The cardinal-vs-landmark A/B.** `--nav-phrasing` is a label field
  only for now; the A/B runs once there is a second phrasing to test.
- **`perceive._reference_frame()` returns `None`** — today the game
  gives no map orientation / compass, so a bearing word is never
  `direction_operational`. That function is the single switch the
  redesign flips.

## Engine touch-point

One additive method: `UIMixin.perceived_map_grid()` in
`src/mixins/ui_mixin.py` — the fogged glyph grid as plain data. It
mirrors `_render_map_lines`'s fog/glyph rules; keep them in sync
(that method stays the source of truth for what the human sees).
`tools/balance_autoplay.py` is untouched and independent.
