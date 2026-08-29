"""Navigation helpers - turning a route into an honest compass heading.

Pure: plane geometry plus a shortest-path list (a `src.worldgen`
`shortest_path` / `MapGraph` result). No engine imports, no rendering.
See docs/PHASE_C3_2_SPEC.md.

Coordinates are (x, y) with y increasing DOWNWARD, so +y is south -
matching world_mixin's map and the ASCII render. A "bearing" is one of
"", "north", "south", "east", "west", or a hyphenated pair
("north-east") - the same words the two ad-hoc helpers this consolidates
(`mystery_mixin._mystery_heading`, `tui._compass`) already produced.

Ships inert (C.3.2 build-order step 1): nothing calls these yet.
"""

_OPPOSITE = {"north": "south", "south": "north", "east": "west", "west": "east"}


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


def heading_is_honest(path, claimed, window=5):
    """Is `claimed` a fair description of where `path` actually goes
    over its first `window` steps?

    A MONOTONIC-PROGRESS test, not a reachability test. The v2 failure
    (PHASE_C3_SPEC.md) was a destination that WAS reachable but whose
    route detoured hard against the advertised heading for the first
    several tiles - a player following "north-east" hit walls on every
    early decision. So:

        honest  <=>  `claimed` shares at least one compass axis with the
                     route's first-`window`-step direction AND
                     contradicts none of them.

    `path` is a shortest-path list [start, ..., dest].
      - empty `claimed`            -> True (no assertion to be wrong about)
      - degenerate/short path      -> True (nothing to contradict)
      - early route has no clear    -> True (not committed yet is not a lie;
        direction                          only a demonstrated reversal is)

    The dishonest case is a *contradiction*: the claim asserts a compass
    axis the early route demonstrably reverses (claim "north", route
    goes south for the first `window` tiles). Lack of signal is not a
    contradiction.

    To substitute the honest heading when this returns False, a caller
    computes `bearing(path[0], path[min(window, len(path) - 1)])`.
    """
    if not claimed:
        return True
    if not path or len(path) < 2:
        return True
    early_end = path[min(window, len(path) - 1)]
    real = _axes(bearing(path[0], early_end))
    if not real:
        return True  # route hasn't committed to a direction - not a lie
    claimed_axes = _axes(claimed)
    if any(_OPPOSITE[ax] in real for ax in claimed_axes):
        return False  # claim asserts an axis the early route reverses
    return bool(claimed_axes & real)  # ... and shares at least one axis
