"""Autoplay instrument for Apocrysis — the perception-bounded harness.

See docs/AUTOPLAY_STRATEGY.md. This package is the *measuring
instrument*, not a redesign of the game:

- `perceive`  — the honest perception boundary. `Perception` is
  everything a player can see this turn (HUD, fogged map grid, the
  say() stream since the last command, the ESCAPE panel), and nothing
  more. A policy decides from a `Perception`, never from engine
  internals.
- `metrics`   — per-run record. Objective facts are recorded as
  received/actionable pairs (`direction_text_seen` vs
  `direction_operational`, `landmark_named` vs `landmark_visible`) so
  a failure separates "not told" from "told unusably".
- `policies`  — baseline policies only: `random`, `survival`,
  `explorer`. The `objective` / `humanlike` policies and the
  cardinal-vs-landmark A/B wait for the spatial-language design pass.
- `runner`    — `PerceivedBotIO` + `run_one()`.

`tools/balance_autoplay.py` (Level 1, the balance lab) is unchanged
and independent of this package.
"""
