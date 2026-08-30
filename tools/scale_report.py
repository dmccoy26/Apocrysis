"""C.3.2a-5 investigation — is the authored mystery physically feasible
as the map grows with campaign depth?

Pure geometry, no bot. For each expedition depth we measure the
REQUIRED investigative circuit (the travel a survivor must actually do
to solve the mystery and reach the escape) against a fresh survivor's
movement budget - and, as a quality diagnostic, how much of that
circuit is backtracking through already-crossed ground.

    python3 tools/scale_report.py --games 300
    python3 tools/scale_report.py --depths 0,3,6,9,12

See docs/PHASE_C3_2_5_SPEC.md for the metric definitions.
"""
import argparse
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import src.game as _gmod
from src.game import Apocrysis
from src.escape import MECHANISMS
from src.worlds.silence.truth import WORLD_FACTS
from src.worldgen.reachable import reachable_set, shortest_path

# A representative rotation across the role-count range. Fresh
# Apocrysis(seed, expeditions_completed=d) otherwise always targets the
# first un-known WorldFact -> mountain_pass every time (the campaign-
# variety contamination). Force a rotation so the aggregate reflects
# the real mechanism spread, and break out per-mechanism below.
MECH_ROTATION = [
    "mountain_pass",   # spatial: route + require + obstacle + escape
    "rail_tunnel",
    "boat_crossing",
    "evac_corridor",
    "service_route",
    "radio_tower",     # informational: route deferred
    "power_station",   # infrastructural: + power site
    "dam_valves",      # experimental
    "airfield_plane",  # transportation: + require2 (longest)
    "tidal_causeway",  # time-pressure
]
_ALL_FACTS_KNOWN = {f.id: "known" for f in WORLD_FACTS}


def _forced_game(seed, depth, mech):
    _gmod.Apocrysis._used_mechanisms = [k for k in MECHANISMS if k != mech]
    _gmod.Apocrysis._last_family = None
    _gmod.Apocrysis._recent_mechanisms = []
    _gmod.Apocrysis._recent_signatures = []
    _gmod.Apocrysis._world_investigation = dict(_ALL_FACTS_KNOWN)
    try:
        g = Apocrysis("Scale", seed=seed, io=_Silent(),
                      expeditions_completed=depth)
        return g
    finally:
        _gmod.Apocrysis._used_mechanisms = []
        _gmod.Apocrysis._world_investigation = {}
        _gmod.Apocrysis._last_family = None
        _gmod.Apocrysis._recent_mechanisms = []
        _gmod.Apocrysis._recent_signatures = []


# --- the survival budget (docs/PHASE_C3_2_5_SPEC.md, calibrated) -------
#
# Fresh survivor: hunger/thirst start ~90, food/water 8 each, each
# ration/portion +5, decay ~2.5/move over the day-night cycle.
#   90 + 8*5 = 130 hunger-points / 2.5 ≈ 52 moves before attrition.
# Cross-check: the v1 boat_crossing death (fresh-equivalent) starved
# from ~turn 45. So GROSS ≈ 50.
# Margins the raw figure ignores: combat (~2 moves' decay/fight, 3-5
# fights), the return leg from the last site to the obstacle+exit, and
# non-beeline wandering (no marker pre-lead). Net USABLE for the
# investigative circuit ≈ 32.
GROSS_BUDGET = 50
USABLE_BUDGET = 32


class _Silent:
    renders_natively = True

    def say(self, *a, **k):
        pass

    def ask(self, prompt=""):
        return ""

    def ask_yes_no(self, prompt):
        return False


def _terrain_grid(game):
    return [[c if isinstance(c, dict) else {"terrain": "plain"} for c in row]
            for row in game.map]


def _seg(grid, n, a, b):
    return shortest_path(grid, n, tuple(a), tuple(b))


def required_circuit(game):
    """Total traversable tiles a survivor must walk to solve THIS
    mystery, and the backtrack proportion of that walk.

    circuit = spawn -> {route, require, [require2], [power]} nearest-first
            -> obstacle_tile -> escape_tile
    (`closed` and the town centre are context, not requirements.)

    Returns (tiles, backtrack_frac, reachable_ok) or (None, None, False)
    when a required node is unreachable / there is no mystery.
    """
    m = getattr(game, "mystery", None)
    if m is None:
        return None, None, False
    grid = _terrain_grid(game)
    n = game.map_size
    spawn = tuple(game.current_position)

    required_roles = ["route", "require"]
    if "require2" in m.sites:
        required_roles.append("require2")
    if getattr(m, "power_role", None):
        required_roles.append(m.power_role)
    targets = [tuple(m.sites[r]) for r in required_roles if r in m.sites]

    tail = []
    ob = getattr(m, "obstacle_tile", None)
    if ob:
        tail.append(tuple(ob))
    esc = getattr(m, "escape_tile", None)
    if esc:
        tail.append(tuple(esc))

    # greedy nearest-first over the required investigation sites, then
    # the fixed obstacle -> escape tail.
    all_tiles = []
    cur = spawn
    remaining = list(targets)
    while remaining:
        best = None
        for t in remaining:
            p = _seg(grid, n, cur, t)
            if p is not None and (best is None or len(p) < len(best[0])):
                best = (p, t)
        if best is None:
            return None, None, False
        all_tiles += best[0][1:] if all_tiles else best[0]
        cur = best[1]
        remaining.remove(best[1])
    for t in tail:
        p = _seg(grid, n, cur, t)
        if p is None:
            return None, None, False
        all_tiles += p[1:] if all_tiles else p
        cur = t

    total = max(0, len(all_tiles) - 1)
    unique = len(set(all_tiles))
    backtrack = round(1 - unique / len(all_tiles), 3) if all_tiles else 0.0
    return total, backtrack, True


# --- decomposition diagnostics (C.3.2a-5, pre-A/B) -------------------

_LEG_ORDER = ["route", "require", "require2", "power", "obstacle", "escape"]


def circuit_legs(game):
    """The required circuit broken into named legs, walked in the
    canonical mystery order (learn the route -> fetch the item(s) ->
    fix the power -> open the obstacle -> leave). Fixed order so legs
    are comparable across seeds. Returns {leg_name: tiles} or {}."""
    m = getattr(game, "mystery", None)
    if m is None:
        return {}
    grid = _terrain_grid(game)
    n = game.map_size

    def node(role):
        if role == "obstacle":
            return getattr(m, "obstacle_tile", None)
        if role == "escape":
            return getattr(m, "escape_tile", None)
        if role == "power":
            pr = getattr(m, "power_role", None)
            return m.sites.get(pr) if pr else None
        return m.sites.get(role)

    seq = [("spawn", tuple(game.current_position))]
    for role in _LEG_ORDER:
        xy = node(role)
        if xy is not None:
            seq.append((role, tuple(xy)))

    legs = {}
    for (an, a), (bn, b) in zip(seq, seq[1:]):
        p = _seg(grid, n, a, b)
        if p is None:
            return {}
        legs[f"{an}->{bn}"] = len(p) - 1
    return legs


def endpoint_dists(game):
    """spawn -> each meaningful endpoint (BFS tiles). Shows which
    endpoint's distance grows with depth."""
    m = getattr(game, "mystery", None)
    grid = _terrain_grid(game)
    n = game.map_size
    spawn = tuple(game.current_position)
    out = {}
    if m is not None:
        for role in ("route", "require", "require2", "power", "obstacle",
                     "escape"):
            xy = (getattr(m, "obstacle_tile", None) if role == "obstacle"
                  else getattr(m, "escape_tile", None) if role == "escape"
                  else m.sites.get(getattr(m, "power_role", None)) if role == "power"
                  else m.sites.get(role))
            if xy is not None:
                p = shortest_path(grid, n, spawn, tuple(xy))
                if p is not None:
                    out[role] = len(p) - 1
    g = getattr(game, "_map_graph", None)
    if g is not None and "town" in g.nodes:
        p = shortest_path(grid, n, spawn, tuple(g.nodes["town"]))
        if p is not None:
            out["town"] = len(p) - 1
    return out


def dest_settlement_count(game):
    """How many DISTINCT settlement clusters a required-circuit site
    falls in - the "meaningful destinations that can participate in the
    required circuit". Currently ~1 (sites cluster in one settlement);
    lever 4 would raise it."""
    m = getattr(game, "mystery", None)
    if m is None:
        return 0
    n = game.map_size
    town = {(x, y) for y in range(n) for x in range(n)
            if isinstance(game.map[y][x], dict)
            and game.map[y][x].get("terrain") == "town"}
    if not town:
        return 0
    # connected components of town tiles
    comps = []
    seen = set()
    for t in town:
        if t in seen:
            continue
        stack, comp = [t], set()
        while stack:
            c = stack.pop()
            if c in comp:
                continue
            comp.add(c)
            seen.add(c)
            cx, cy = c
            for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                nb = (cx + dx, cy + dy)
                if nb in town and nb not in comp:
                    stack.append(nb)
        comps.append(comp)
    req = {tuple(m.sites[r]) for r in ("closed", "route", "require", "require2")
           if r in m.sites}
    return sum(1 for comp in comps if comp & req)


def measure(game):
    grid = _terrain_grid(game)
    n = game.map_size
    spawn = tuple(game.current_position)
    m = getattr(game, "mystery", None)
    reach = reachable_set(grid, n, spawn)

    # diagnostic only (NOT an evaluation metric - see the spec)
    near = None
    if m is not None:
        ds = [len(p) - 1 for xy in m.sites.values()
              if (p := shortest_path(grid, n, spawn, tuple(xy))) is not None]
        near = min(ds) if ds else None

    n_sites = len(m.sites) if m is not None else 0
    circ, bt, ok = required_circuit(game)
    playable = len(reach)
    dsc = dest_settlement_count(game)
    return {
        "map": n,
        "playable": playable,
        "dens": round(1000 * n_sites / max(1, playable), 2),
        "dest_setts": dsc,
        # distinct participating settlements per 1000 playable tiles
        "dest_density": round(1000 * dsc / max(1, playable), 3),
        "near": near,                 # diagnostic
        "circuit": circ if ok else None,
        "backtrack": bt if ok else None,
        "ratio": (circ / USABLE_BUDGET) if ok else None,
        "over_budget": (circ is not None and circ > USABLE_BUDGET),
        "infeasible": (m is None) or not ok,
        "legs": circuit_legs(game),
        "ep": endpoint_dists(game),
    }


def _p(v, q):
    v = sorted(x for x in v if x is not None)
    return v[min(len(v) - 1, int(len(v) * q))] if v else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=300)
    ap.add_argument("--depths", default="0,1,2,3,4,6,9,12")
    args = ap.parse_args()
    depths = [int(x) for x in args.depths.split(",")]

    print(f"budget: gross {GROSS_BUDGET} moves, usable (investigative) "
          f"{USABLE_BUDGET}  [docs/PHASE_C3_2_5_SPEC.md]")
    print()

    per_depth = {}
    per_depth_mech = {}   # (depth, mech) -> rows
    for d in depths:
        rows = []
        for i in range(args.games):
            mech = MECH_ROTATION[i % len(MECH_ROTATION)]
            r = measure(_forced_game(i, d, mech))
            r["mech"] = mech
            rows.append(r)
            per_depth_mech.setdefault((d, mech), []).append(r)
        per_depth[d] = rows

    # --- headline matrix ---
    print("=== headline matrix ===")
    print(f"{'depth':>5} {'map':>7} {'play':>6} {'dens':>5} {'dst/1k':>6} "
          f"{'circ p50':>8} {'circ p90':>8} "
          f"{'ratio p90':>9} {'>budget':>8} "
          f"{'btrk p50':>8} {'btrk p90':>8} {'infeas':>7} {'near*':>6}")
    for d in depths:
        rows = per_depth[d]
        circ = [r["circuit"] for r in rows]
        bt = [r["backtrack"] for r in rows]
        over = 100 * sum(1 for r in rows if r["over_budget"]) / len(rows)
        infeas = 100 * sum(1 for r in rows if r["infeasible"]) / len(rows)
        sz = rows[0]["map"]
        print(f"{d:>5} {f'{sz}x{sz}':>7} "
              f"{round(statistics.mean(r['playable'] for r in rows)):>6} "
              f"{statistics.mean(r['dens'] for r in rows):>5.1f} "
              f"{statistics.mean(r['dest_density'] for r in rows):>6.3f} "
              f"{_p(circ,.5):>8.0f} {_p(circ,.9):>8.0f} "
              f"{_p([r['ratio'] for r in rows],.9):>9.2f} {over:>7.0f}% "
              f"{_p(bt,.5):>8.2f} {_p(bt,.9):>8.2f} {infeas:>6.1f}% "
              f"{_p([r['near'] for r in rows],.5):>6.0f}")

    # --- leg-by-leg decomposition (canonical order) ---
    leg_names = []
    for d in depths:
        for r in per_depth[d]:
            for k in r["legs"]:
                if k not in leg_names:
                    leg_names.append(k)
    print()
    print("=== required circuit, leg by leg (canonical order)  p50 / p90 ===")
    print(f"{'depth':>5} " + " ".join(f"{ln:>16}" for ln in leg_names))
    for d in depths:
        rows = per_depth[d]
        cells = []
        for ln in leg_names:
            vals = [r["legs"].get(ln) for r in rows if ln in r["legs"]]
            cells.append(f"{_p(vals,.5):>7.0f}/{_p(vals,.9):<8.0f}"
                         if vals else f"{'-':>16}")
        print(f"{d:>5} " + " ".join(cells))

    # --- spawn -> each endpoint (which endpoint grows) ---
    ep_names = ["route", "require", "require2", "power", "obstacle",
               "escape", "town"]
    print()
    print("=== spawn -> endpoint distance  p50 / p90  (which endpoint grows) ===")
    print(f"{'depth':>5} " + " ".join(f"{e:>13}" for e in ep_names))
    for d in depths:
        rows = per_depth[d]
        cells = []
        for e in ep_names:
            vals = [r["ep"].get(e) for r in rows if e in r["ep"]]
            cells.append(f"{_p(vals,.5):>5.0f}/{_p(vals,.9):<7.0f}"
                         if vals else f"{'-':>13}")
        print(f"{d:>5} " + " ".join(cells))

    # --- per-mechanism circuit p50/p90 at a few depths ---
    show_depths = [d for d in (0, 3, 6, 12) if d in depths] or depths[:1]
    print()
    print("=== required circuit by mechanism   circ p50 / p90 ===")
    print(f"{'mechanism':>16} " + " ".join(f"{'d'+str(d):>13}" for d in show_depths))
    for mech in MECH_ROTATION:
        cells = []
        for d in show_depths:
            rs = per_depth_mech.get((d, mech), [])
            cv = [r["circuit"] for r in rs]
            cells.append(f"{_p(cv,.5):>5.0f}/{_p(cv,.9):<7.0f}" if cv
                         else f"{'-':>13}")
        print(f"{mech:>16} " + " ".join(cells))

    print()
    print("circ      = REQUIRED circuit: spawn -> route/require/require2/power")
    print("            -> obstacle -> escape (greedy nearest-first, tiles)")
    print("            aggregate rows rotate through all 10 mechanisms")
    print("legs      = same required set, walked in canonical mystery order")
    print("            (fixed order so legs compare across seeds)")
    print(f">budget   = % of maps where the required circuit exceeds {USABLE_BUDGET}")
    print("ratio p90 = circ / usable budget at p90  (gate: < 1)")
    print("btrk      = backtrack: 1 - unique tiles / circuit length "
          "(quality; regression if it rises under a lever)")
    print("dens      = mystery sites / 1000 playable tiles")
    print("dst/1k    = DISTINCT settlements a required site falls in, "
          "per 1000 playable tiles")
    print("near*     = spawn -> nearest site; DIAGNOSTIC ONLY")


if __name__ == "__main__":
    main()
