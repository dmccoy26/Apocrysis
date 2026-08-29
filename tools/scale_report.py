"""C.3.2a-5 investigation — does the generator keep an appropriate
density of *actionable* destinations as the map grows with campaign
depth?

Pure geometry, no bot. For each expedition depth: how big is the map,
how many meaningful sites are on it, and how far is the nearest one
from spawn — the thing BlueNoodle's map-4 death was about.

    python3 tools/scale_report.py --games 200
    python3 tools/scale_report.py --games 400 --depths 0,3,6,9,12

"Meaningful site" = a mystery site (`mystery.sites` — arriving there
surfaces a fact/lead) or the real town centre. NOT "a building exists
somewhere".
"""
import argparse
import os
import statistics
import sys
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.game import Apocrysis
from src.worldgen.reachable import reachable_set, shortest_path


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


def _bfs_dist(grid, n, start, goal):
    p = shortest_path(grid, n, tuple(start), tuple(goal))
    return None if p is None else len(p) - 1


def measure(game):
    grid = _terrain_grid(game)
    n = game.map_size
    spawn = tuple(game.current_position)
    m = getattr(game, "mystery", None)

    reach = reachable_set(grid, n, spawn)
    playable = len(reach)

    sites = []
    if m is not None:
        sites += [tuple(xy) for xy in m.sites.values()]
    tc = getattr(game, "_map_graph", None)
    town = None
    if tc is not None and "town" in tc.nodes:
        town = tuple(tc.nodes["town"])
        sites.append(town)
    sites = [s for s in sites if s in reach]

    dists = sorted(d for s in sites
                   if (d := _bfs_dist(grid, n, spawn, s)) is not None)
    nearest = dists[0] if dists else None
    farthest = dists[-1] if dists else None
    town_d = _bfs_dist(grid, n, spawn, town) if town else None

    # the solve circuit: spawn -> nearest site -> next-nearest -> ... ->
    # farthest, greedily. A rough "how far do you walk to touch
    # everything that matters" independent of which order the mystery
    # actually needs.
    circuit = None
    if len(sites) >= 2:
        remaining = list(sites)
        cur = spawn
        total = 0
        ok = True
        while remaining:
            hop = min(
                ((_bfs_dist(grid, n, cur, s), s) for s in remaining),
                key=lambda t: (t[0] is None, t[0]),
            )
            if hop[0] is None:
                ok = False
                break
            total += hop[0]
            cur = hop[1]
            remaining.remove(hop[1])
        circuit = total if ok else None

    # empty traversable ground: reachable tiles that are not a
    # building / town / meaningful site
    site_set = set(sites)
    empty = sum(
        1 for (x, y) in reach
        if (x, y) not in site_set
        and grid[y][x].get("terrain") not in ("building", "town")
    )

    return {
        "map": n,
        "playable": playable,
        "n_sites": len(sites),
        "site_density_per_1k": round(1000 * len(sites) / max(1, playable), 2),
        "nearest_site": nearest,
        "farthest_site": farthest,
        "circuit": circuit,
        "town_dist": town_d,
        "empty_tiles": empty,
        "empty_frac": round(empty / max(1, playable), 2),
        "no_mystery": m is None,
    }


def _col(rows, key):
    return [r[key] for r in rows if r.get(key) is not None]


def _pct(vals, thresh):
    return round(100 * sum(1 for v in vals if v > thresh) / max(1, len(vals)), 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=200)
    ap.add_argument("--depths", default="0,1,2,3,4,6,9,12")
    args = ap.parse_args()
    depths = [int(x) for x in args.depths.split(",")]

    # a fresh survivor's rough movement budget before starvation bites,
    # from the play logs: ~2 hunger/turn, ~8 starting food at ~15 each,
    # start hunger ~88 -> ~50 turns of moving, and a real player does
    # not beeline (no marker pre-lead) so halve it for "likely to reach".
    BUDGET_BEELINE = 50
    BUDGET_REAL = 25

    hdr = (f"{'depth':>5} {'map':>7} {'play':>6} {'empty':>6} {'dens':>5} "
           f"{'near':>5} {'far p50':>7} {'far p90':>7} "
           f"{'circ p50':>8} {'circ p90':>8} {'circ max':>8} "
           f"{'town p50':>8} {'circ>b/l':>8} {'circ>real':>9}")
    print(hdr)
    for d in depths:
        rows = []
        for i in range(args.games):
            g = Apocrysis("Scale", seed=i, io=_Silent(), expeditions_completed=d)
            rows.append(measure(g))
        near = _col(rows, "nearest_site")
        far = _col(rows, "farthest_site")
        circ = _col(rows, "circuit")
        town = _col(rows, "town_dist")
        dens = _col(rows, "site_density_per_1k")
        sz = rows[0]["map"]

        def q(v, p):
            return sorted(v)[min(len(v) - 1, int(len(v) * p))]

        print(f"{d:>5} {f'{sz}x{sz}':>7} "
              f"{round(statistics.mean(_col(rows,'playable'))):>6} "
              f"{round(100*statistics.mean(_col(rows,'empty_frac'))):>5}% "
              f"{round(statistics.mean(dens),1):>5} "
              f"{statistics.median(near):>5.0f} "
              f"{statistics.median(far):>7.0f} {q(far,0.9):>7.0f} "
              f"{statistics.median(circ):>8.0f} {q(circ,0.9):>8.0f} {max(circ):>8.0f} "
              f"{statistics.median(town):>8.0f} "
              f"{_pct(circ, BUDGET_BEELINE):>7.0f}% {_pct(circ, BUDGET_REAL):>8.0f}%")

    print()
    print("near      = spawn -> NEAREST meaningful site (BFS tiles), median")
    print("far       = spawn -> FARTHEST meaningful site")
    print("circ      = greedy circuit spawn -> touch every meaningful site")
    print(f"circ>b/l  = % of maps where the circuit > {BUDGET_BEELINE} tiles "
          "(a fresh survivor's beeline movement budget)")
    print(f"circ>real = % where the circuit > {BUDGET_REAL} tiles "
          "(effective budget once you factor in not knowing where to go)")
    print("dens      = meaningful sites per 1000 playable tiles")


if __name__ == "__main__":
    main()
