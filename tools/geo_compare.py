"""Phase C.3 - the v1-vs-v2 map-generator comparison harness.

Runs the same seeds through both generators and compares the
DISTRIBUTIONS of geometry and gameplay metrics (not just averages - a
generator can hold the mean and still spit out miserable outliers).

    python3 tools/geo_compare.py --games 300
    python3 tools/geo_compare.py --games 2000 --variants v1,v2

Geometry is read straight off the generated map + its MapGraph (no bot
needed). Gameplay reuses tools/balance_autoplay.py's scripted bot so
the numbers line up with the frozen-balance harness.
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


def _passable(grid, n, x, y):
    # a zombie occupies a walkable tile - you deal with it and move on,
    # so it is NOT a wall. Only mountain/river block.
    if not (0 <= x < n and 0 <= y < n):
        return False
    c = grid[y][x]
    if not isinstance(c, dict):
        return True  # Zombie object -> walkable underneath
    return c.get("terrain") not in ("mountain", "river")


def _neighbours(grid, n, x, y):
    for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        if _passable(grid, n, x + dx, y + dy):
            yield (x + dx, y + dy)


def geometry(game):
    """Pure map/graph metrics for one generated expedition."""
    # a zombie sits on a walkable tile - substitute a plain dict so the
    # reachable.py helpers (strict dict check) see the tile, not a wall.
    grid = [[c if isinstance(c, dict) else {"terrain": "plain"} for c in row]
            for row in game.map]
    n = game.map_size
    spawn = game.current_position
    g = getattr(game, "_map_graph", None)
    m = game.mystery

    interior = [(x, y) for y in range(1, n - 1) for x in range(1, n - 1)]
    passable = [xy for xy in interior if _passable(grid, n, *xy)]
    comp = reachable_set(grid, n, spawn)
    comp_interior = [xy for xy in comp if xy in set(interior)]

    deg = {xy: sum(1 for _ in _neighbours(grid, n, *xy)) for xy in passable}
    dead_ends = sum(1 for d in deg.values() if d == 1)
    branches = sum(1 for d in deg.values() if d >= 3)

    out = {
        "map_size": n,
        "playable_pct": round(100 * len(passable) / max(1, len(interior)), 1),
        "largest_region_pct": round(100 * len(comp_interior) / max(1, len(passable)), 1),
        "dead_ends": dead_ends,
        "branches": branches,
        "branch_ratio": round(branches / max(1, len(passable)), 3),
    }

    if m is not None:
        ex = m.escape_tile
        p = shortest_path(grid, n, spawn, ex)
        out["spawn_to_exit"] = (len(p) - 1) if p else None
        out["manhattan_spawn_exit"] = abs(spawn[0] - ex[0]) + abs(spawn[1] - ex[1])
        site_d = []
        for role, xy in m.sites.items():
            pp = shortest_path(grid, n, spawn, xy)
            if pp:
                site_d.append(len(pp) - 1)
        out["spawn_to_site_mean"] = round(statistics.mean(site_d), 1) if site_d else None
        out["spawn_to_site_max"] = max(site_d) if site_d else None
        if g is not None:
            cp = g.critical_path_tiles("spawn",
                                       *[k for k in g.nodes if k.startswith("site_") or k == "exit"])
            out["critical_path_tiles"] = len(cp)

    # distance to the real town centre
    tc = None
    for y, row in enumerate(game.map):
        for x, c in enumerate(row):
            if isinstance(c, dict) and c.get("content") == "T":
                tc = (x, y)
    if tc:
        p = shortest_path(grid, n, spawn, tc)
        out["spawn_to_town"] = (len(p) - 1) if p else None
    return out


def run_geometry(variant, games, exp_tiers):
    rows = []
    for i in range(games):
        exp = exp_tiers[i % len(exp_tiers)]
        game = Apocrysis("Geo", seed=i, io=_Silent(),
                         expeditions_completed=exp, mapgen=variant)
        rows.append(geometry(game))
    return rows


def run_gameplay(variant, games, exp_tiers, max_turns):
    from tools import balance_autoplay as ba

    rows = []
    for i in range(games):
        exp = exp_tiers[i % len(exp_tiers)]
        # play_one_game builds its own Apocrysis - set the variant via
        # the class default it will pick up.
        Apocrysis._default_mapgen = variant
        try:
            m = ba.play_one_game(level=max(1, exp), expeditions_completed=exp,
                                 seed=i, max_turns=max_turns)
        finally:
            Apocrysis._default_mapgen = "v1"
        rows.append({
            "outcome": m.outcome,
            "turns": m.turns,
            "zombies_defeated": m.zombies_defeated,
            "fights": m.fights,
            "min_health": m.min_health,
            "buildings_entered": getattr(m, "buildings_entered", None),
            "settlements_discovered": getattr(m, "settlements_discovered", None),
        })
    return rows


def _dist(values):
    vs = sorted(v for v in values if isinstance(v, (int, float)))
    if not vs:
        return "  (no data)"
    q = statistics.quantiles(vs, n=10) if len(vs) >= 10 else [vs[0]] * 9
    return (f"n={len(vs):4d}  mean={statistics.mean(vs):7.1f}  "
            f"p10={q[0]:6.1f}  p50={statistics.median(vs):6.1f}  "
            f"p90={q[8]:6.1f}  min={vs[0]:6.1f}  max={vs[-1]:6.1f}")


def compare(a_rows, b_rows, keys, label_a, label_b):
    for k in keys:
        av = [r.get(k) for r in a_rows]
        bv = [r.get(k) for r in b_rows]
        print(f"\n  {k}")
        print(f"    {label_a}: {_dist(av)}")
        print(f"    {label_b}: {_dist(bv)}")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--games", type=int, default=300,
                    help="seeds sampled per variant/tier (default: 300)")
    ap.add_argument("--variants", default="v1,v2",
                    help="comma-separated mapgen variants to compare")
    ap.add_argument("--max-turns", type=int, default=600)
    ap.add_argument("--gameplay", action="store_true",
                    help="also run the bot (slow) - geometry only by default")
    ap.add_argument("--exp-tiers", default="0,3,6,9,12",
                    help="comma-separated expedition depths to sample")
    args = ap.parse_args()

    variants = args.variants.split(",")
    tiers = [int(x) for x in args.exp_tiers.split(",")]

    geo = {}
    for v in variants:
        print(f"[geometry] {v} x {args.games} ...", flush=True)
        geo[v] = run_geometry(v, args.games, tiers)

    geo_keys = ["playable_pct", "largest_region_pct", "dead_ends", "branches",
                "branch_ratio", "spawn_to_exit", "manhattan_spawn_exit",
                "spawn_to_site_mean", "spawn_to_site_max", "critical_path_tiles",
                "spawn_to_town"]
    if len(variants) == 2:
        print("\n" + "=" * 70 + "\nGEOMETRY\n" + "=" * 70)
        compare(geo[variants[0]], geo[variants[1]], geo_keys, *variants)
    else:
        print("\nGEOMETRY -", variants[0])
        for k in geo_keys:
            print(f"  {k:24s} {_dist([r.get(k) for r in geo[variants[0]]])}")

    if args.gameplay:
        play = {}
        for v in variants:
            print(f"\n[gameplay] {v} x {args.games} (bot) ...", flush=True)
            play[v] = run_gameplay(v, args.games, tiers, args.max_turns)
        pkeys = ["turns", "zombies_defeated", "fights", "min_health",
                 "buildings_entered", "settlements_discovered"]
        if len(variants) == 2:
            print("\n" + "=" * 70 + "\nGAMEPLAY\n" + "=" * 70)
            compare(play[variants[0]], play[variants[1]], pkeys, *variants)
            for v in variants:
                won = sum(1 for r in play[v] if r["outcome"] == "won")
                print(f"\n  {v}: win {won}/{len(play[v])} "
                      f"({100 * won / len(play[v]):.0f}%)")
        else:
            for k in pkeys:
                print(f"  {k:24s} {_dist([r.get(k) for r in play[variants[0]]])}")


if __name__ == "__main__":
    main()
