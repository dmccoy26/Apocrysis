"""Autoplay policies — decide only from a `Perception`.

    random     legal random walk; always fights. The null baseline.
    survival   eat/drink/medicine/fight/loot when the HUD says so;
               no objective-seeking at all.
    explorer   survival, plus: when nothing is urgent, head for the
               nearest unseen edge of the map. Models the run-5/6
               "loot every building" loop.
    resource   a trying survival player (rests, eats early).
    objective  survival, plus: pursue the objective USING PERCEIVED
               TEXT ONLY — head for a mystery marker ('!'/'+') visible
               on the rendered map / named in the ESCAPE panel; when
               none is visible, search where useful, else explore.
               For the spatial-language / navigation investigation
               (docs/DESIGN_SPATIAL_LANGUAGE.md, docs/AUTOPLAY_STRATEGY).

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


class ObjectivePolicy(ExplorerPolicy):
    """Pursues the objective from PERCEIVED information only.

    A player who has learned about a lead sees a '!' (or '+' for an
    opened route) marker on the map, and the ESCAPE panel names a
    place + says "marked on your map" / "close now" / "the marker's in
    sight". This policy acts on exactly that: BFS toward the nearest
    visible marker. When it can't see one, it does NOT get to cheat
    (no `m.sites`) - it searches a mystery-ish tile if the panel hints
    one is near, otherwise it explores. The runner records whether
    each move actually closed distance to the real objective."""
    name = "objective"

    def __init__(self, rng=None):
        super().__init__(rng)
        self._target = None       # committed destination (hysteresis)
        self._seen = set()        # tiles stood on

    # only-when-desperate survival, so pursuit dominates the trace
    def _survival_command(self, per):
        h = per.hud
        if h["health"] <= 0.30 * h["max_health"] and h["medicine"] > 0:
            return "med"
        if h["hunger"] <= 18 and h["food"] > 0:
            return "eat"
        if h["thirst"] <= 18 and h["water"] > 0:
            return "drink"
        return None

    def _structures(self, per):
        """Visible non-ground glyphs a player would read as places worth
        entering (buildings / town features) - where leads are learned."""
        return per.glyph_positions("HRSBT#b") + per.glyph_positions("oc")

    def on_command(self, per):
        here = per.player_xy
        self._seen.add(here)
        cmd = self._survival_command(per)
        if cmd:
            return cmd

        # commit to one destination until reached or it disappears
        # (hysteresis - stops the bounce between equidistant markers)
        if self._target is not None:
            if self._target == here or self._target in self._seen:
                self._target = None
            else:
                step = _bfs_first_step(per, {self._target})
                if step:
                    return step
                self._target = None   # unreachable now, re-pick

        # 1. a *fresh* lead marker on the map -> pick the nearest one
        #    we haven't already stood on
        markers = [m for m in per.glyph_positions("!+") if m not in self._seen]
        if markers:
            px, py = here
            self._target = min(markers, key=lambda m: abs(px-m[0]) + abs(py-m[1]))
            step = _bfs_first_step(per, {self._target})
            if step:
                return step
            return "search"
        # a marker we're standing next to -> search it
        if any(abs(here[0]-mx) + abs(here[1]-my) <= 1
               for mx, my in per.glyph_positions("!+")):
            return "search"

        # 2. no marker -> leads live in structures; go to the nearest
        #    unvisited one and search on arrival
        structs = [s for s in self._structures(per) if s not in self._seen]
        if structs:
            px, py = here
            self._target = min(structs, key=lambda s: abs(px-s[0]) + abs(py-s[1]))
            step = _bfs_first_step(per, {self._target})
            if step:
                return step
            return "search"

        # 3. nothing to aim at -> reveal more map
        step = _bfs_first_step(per, per.unseen_frontier())
        return step or self._random_step(per)


_REGISTRY = {p.name: p for p in (RandomPolicy, SurvivalPolicy, ExplorerPolicy,
                                 ResourcePolicy, ObjectivePolicy)}


def make(name, rng=None):
    try:
        return _REGISTRY[name](rng=rng)
    except KeyError:
        raise SystemExit(
            f"unknown policy {name!r}; instrument-phase policies: "
            + ", ".join(sorted(_REGISTRY)))
