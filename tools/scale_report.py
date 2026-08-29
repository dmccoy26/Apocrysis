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

from src.game import Apocrysis
from src.worldgen.reachable import reachable_set, shortest_path


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
    return {
        "map": n,
        "playable": len(reach),
        "dens": round(1000 * n_sites / max(1, len(reach)), 2),
        "near": near,                 # diagnostic
        "circuit": circ if ok else None,
        "backtrack": bt if ok else None,
        "ratio": (circ / USABLE_BUDGET) if ok else None,
        "over_budget": (circ is not None and circ > USABLE_BUDGET),
        "infeasible": (m is None) or not ok,
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
    print(f"{'depth':>5} {'map':>7} {'play':>6} {'dens':>5} "
          f"{'circ p50':>8} {'circ p90':>8} "
          f"{'ratio p90':>9} {'>budget':>8} "
          f"{'btrk p50':>8} {'btrk p90':>8} {'infeas':>7} {'near*':>6}")
    for d in depths:
        rows = [measure(Apocrysis("Scale", seed=i, io=_Silent(),
                                  expeditions_completed=d))
                for i in range(args.games)]
        circ = [r["circuit"] for r in rows]
        bt = [r["backtrack"] for r in rows]
        over = 100 * sum(1 for r in rows if r["over_budget"]) / len(rows)
        infeas = 100 * sum(1 for r in rows if r["infeasible"]) / len(rows)
        sz = rows[0]["map"]
        print(f"{d:>5} {f'{sz}x{sz}':>7} "
              f"{round(statistics.mean(r['playable'] for r in rows)):>6} "
              f"{statistics.mean(r['dens'] for r in rows):>5.1f} "
              f"{_p(circ,.5):>8.0f} {_p(circ,.9):>8.0f} "
              f"{_p([r['ratio'] for r in rows],.9):>9.2f} {over:>7.0f}% "
              f"{_p(bt,.5):>8.2f} {_p(bt,.9):>8.2f} {infeas:>6.1f}% "
              f"{_p([r['near'] for r in rows],.5):>6.0f}")

    print()
    print("circ      = REQUIRED circuit: spawn -> route/require/require2/power")
    print("            -> obstacle -> escape (traversable tiles)")
    print(f">budget   = % of maps where the required circuit exceeds the "
          f"usable budget ({USABLE_BUDGET})")
    print("ratio p90 = circ / usable budget at p90  (gate: < 1)")
    print("btrk      = backtrack proportion: 1 - unique tiles / circuit "
          "length  (quality diagnostic, NOT gated yet)")
    print("dens      = meaningful sites per 1000 playable tiles (watch it "
          "does not keep falling under a lever)")
    print("near*     = spawn -> nearest site; DIAGNOSTIC ONLY, never an "
          "evaluation metric")


if __name__ == "__main__":
    main()
