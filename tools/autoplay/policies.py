"""Baseline autoplay policies — decide only from a `Perception`.

Instrument-phase set only:

    random    legal random walk; always fights. The null baseline.
    survival  eat/drink/medicine/fight/loot when the HUD says so;
              no objective-seeking at all.
    explorer  survival, plus: when nothing is urgent, head for the
              nearest unseen edge of the map. Models the run-5/6
              "loot every building" loop.

The `objective` and `humanlike` policies are deliberately NOT here —
an objective-seeking policy's behaviour depends on what spatial
language the redesign introduces, so it is built after the design
pass (docs/AUTOPLAY_STRATEGY.md, "Sequencing").

A policy never sees `player`. It sees `Perception` and returns a
command string / a combat letter / a yes-no.
"""
from __future__ import annotations

import random
from collections import deque

_DELTA = {"n": (0, -1), "s": (0, 1), "e": (1, 0), "w": (-1, 0)}
_BLOCKED = {"^", "="}


def _bfs_first_step(per, targets):
    """First move (n/s/e/w) along a shortest path over the PERCEIVED
    grid from the player to the closest tile in `targets`. Unseen (' ')
    tiles are treated as walkable — a player would try them. None if
    unreachable through what's visible."""
    if not targets:
        return None
    targets = set(targets)
    start = per.player_xy
    if start in targets:
        return None
    seen = {start}
    q = deque([(start, None)])
    while q:
        (x, y), first = q.popleft()
        for d, (dx, dy) in _DELTA.items():
            nx, ny = x + dx, y + dy
            if not (0 <= nx < per.size and 0 <= ny < per.size):
                continue
            if (nx, ny) in seen:
                continue
            if per.grid[ny][nx] in _BLOCKED:
                continue
            step = first or d
            if (nx, ny) in targets:
                return step
            seen.add((nx, ny))
            q.append(((nx, ny), step))
    return None


class Policy:
    name = "base"

    def __init__(self, rng=None):
        self.rng = rng or random.Random()

    # --- combat -------------------------------------------------------
    def on_yes_no(self, per) -> bool:
        return True   # old fight/flee path: fight, for hit sampling

    def on_combat_letter(self, per) -> str:
        enc = per.encounter or {}
        threat = (enc.get("threat") or "").upper()
        fight = enc.get("fight_pct")
        if threat in ("EXTREME", "SEVERE"):
            return "e"
        if fight is not None and fight < 35:
            return "e"
        return "f"

    # --- turn command ----------------------------------------------
    def _survival_command(self, per):
        h = per.hud
        if h["health"] <= 0.35 * h["max_health"] and h["medicine"] > 0:
            return "med"
        if h["hunger"] <= 22 and h["food"] > 0:
            return "eat"
        if h["thirst"] <= 22 and h["water"] > 0:
            return "drink"
        return None

    def on_command(self, per):
        raise NotImplementedError

    def _random_step(self, per):
        legal = per.legal_moves()
        return self.rng.choice(legal) if legal else "n"


class RandomPolicy(Policy):
    name = "random"

    def on_command(self, per):
        return self._random_step(per)

    def on_combat_letter(self, per):
        return "f"


class SurvivalPolicy(Policy):
    name = "survival"

    def on_command(self, per):
        cmd = self._survival_command(per)
        if cmd:
            return cmd
        # loot where you stand now and then, otherwise drift
        if self.rng.random() < 0.30:
            return "search"
        return self._random_step(per)


class ExplorerPolicy(Policy):
    name = "explorer"

    def on_command(self, per):
        cmd = self._survival_command(per)
        if cmd:
            return cmd
        if self.rng.random() < 0.25:
            return "search"
        step = _bfs_first_step(per, per.unseen_frontier())
        if step:
            return step
        return self._random_step(per)


class ResourcePolicy(ExplorerPolicy):
    """A survival-*minded* player: eats/drinks earlier, meds sooner, and
    actually rests when exhausted. For the resource-attrition
    investigation - isolates "the economy is too tight" from "the naive
    policy just doesn't manage resources" (docs/RESOURCE_MODEL_RESULTS)."""
    name = "resource"

    def _survival_command(self, per):
        h = per.hud
        if h["health"] <= 0.45 * h["max_health"] and h["medicine"] > 0:
            return "med"
        if h["fatigue"] > 85:
            return "rest"
        if h["hunger"] <= 40 and h["food"] > 0:
            return "eat"
        if h["thirst"] <= 40 and h["water"] > 0:
            return "drink"
        return None


_REGISTRY = {p.name: p for p in (RandomPolicy, SurvivalPolicy, ExplorerPolicy,
                                 ResourcePolicy)}


def make(name, rng=None):
    try:
        return _REGISTRY[name](rng=rng)
    except KeyError:
        raise SystemExit(
            f"unknown policy {name!r}; instrument-phase policies: "
            + ", ".join(sorted(_REGISTRY)))
