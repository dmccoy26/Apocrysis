"""Navigation helpers - turning a route into an honest compass heading.

Pure: plane geometry plus a shortest-path list (a `src.worldgen`
`shortest_path` / `MapGraph` result). No engine imports, no rendering.
See docs/PHASE_C3_2_SPEC.md.

Coordinates are (x, y) with y increasing DOWNWARD, so +y is south -
matching world_mixin's map and the ASCII render. A "bearing" is one of
"", "north", "south", "east", "west", or a hyphenated pair
("north-east") - the same words the two ad-hoc helpers this consolidates
(`mystery_mixin._mystery_heading`, `tui._compass`) already produced.

C.3.2: `heading_is_honest` / `honest_bearing` are consumed by
`tui._route_heading` (the ESCAPE-panel route heading, piece 0) and by
`knowledge_mixin.knowledge_look` (recoverable orientation, piece 2).

`honest_bearing` reaches into `src.worldgen.reachable` for a
shortest_path - still no *engine* imports, but no longer standalone.
"""
from src.worldgen.reachable import shortest_path


def bearing(from_xy, to_xy, deadzone=1):
    """Compass word pointing from `from_xy` toward `to_xy`.

    An axis whose separation is within `deadzone` tiles contributes
    nothing, so a nearly-aligned target reads as a single cardinal
    ("north") rather than a noisy diagonal, and a target on top of the
    origin reads as "". This is the +/-1 behaviour of the callers this
    replaces.
    """
    dx = to_xy[0] - from_xy[0]
    dy = to_xy[1] - from_xy[1]
    ns = "north" if dy < -deadzone else "south" if dy > deadzone else ""
    ew = "west" if dx < -deadzone else "east" if dx > deadzone else ""
    return "-".join(p for p in (ns, ew) if p)


def _axes(b):
    return set(b.split("-")) if b else set()


_OPPOSITE = {"north": "south", "south": "north", "east": "west", "west": "east"}


def heading_is_honest(path, claimed, window=8):
    """Would a player following `claimed` from the start of `path` be
    sent *backward* along the real route?

    A CONTRADICTION test, deliberately conservative - it fires only when
    the route's first-`window`-step net direction actually reverses an
    axis `claimed` asserts (the v2 case: panel says "north-east" but the
    route has to run west for a stretch to get around a ridge before it
    can turn). It does NOT fire when the route is merely L-shaped or the
    claim is a diagonal and the early route is one cardinal - walking a
    fine diagonal on open ground makes progress, and a shortest path's
    exact shape is a BFS tie-break artifact, not terrain.

    `path` is a shortest-path list [start, ..., dest].
      - empty `claimed`         -> True (no assertion to be wrong about)
      - degenerate/short path   -> True (nothing to contradict)
      - early route uncommitted -> True (within the deadzone)

    To substitute the honest heading when this returns False, a caller
    computes `bearing(path[0], path[min(window, len(path) - 1)])`.
    """
    if not claimed:
        return True
    if not path or len(path) < 2:
        return True
    early = _axes(bearing(path[0], path[min(window, len(path) - 1)]))
    if not early:
        return True
    return not any(_OPPOSITE[ax] in early for ax in _axes(claimed))


def honest_bearing(here, dest, grid, n, window=8):
    """The graph-honest compass word from `here` toward `dest`.

    The straight-line `bearing` is the claim; the real `shortest_path`
    over `grid` is the authority. If the early route reverses one of the
    claim's axes, return the route's honest early heading instead.

      - `here` on / within the deadzone of `dest` -> "" (no direction)
      - `dest` unreachable                        -> the straight-line
        claim (the caller decides what to do about unreachable)

    `grid` may contain non-dict tiles (a Zombie object) - those are
    treated as passable here: a zombie standing on the direct line is
    not a reason to re-describe where the route goes.
    """
    here, dest = tuple(here), tuple(dest)
    straight = bearing(here, dest)
    if not straight:
        return ""
    terrain = [[c if isinstance(c, dict) else {"terrain": "plain"} for c in row]
               for row in grid]
    path = shortest_path(terrain, n, here, dest)
    if not path or heading_is_honest(path, straight, window):
        return straight
    return bearing(path[0], path[min(window, len(path) - 1)])
