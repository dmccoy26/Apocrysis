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
from src.game import Apocrysis, depth_supply_bonus, SUPPORTED_DEPTH
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


_LEVER_DEFAULTS = {"_lever_settlements_by_area": False, "_lever_bound_gap": None,
                   "_lever_cap_town_dist": None, "_lever_spread_sites": False,
                   "_lever_scaled_beats": None}


def _forced_game(seed, depth, mech, levers=None):
    A = _gmod.Apocrysis
    A._used_mechanisms = [k for k in MECHANISMS if k != mech]
    A._last_family = None
    A._recent_mechanisms = []
    A._recent_signatures = []
    A._world_investigation = dict(_ALL_FACTS_KNOWN)
    for k, default in _LEVER_DEFAULTS.items():
        setattr(A, k, (levers or {}).get(k, default))
    try:
        return Apocrysis("Scale", seed=seed, io=_Silent(),
                         expeditions_completed=depth)
    finally:
        A._used_mechanisms = []
        A._world_investigation = {}
        A._last_family = None
        A._recent_mechanisms = []
        A._recent_signatures = []
        for k, default in _LEVER_DEFAULTS.items():
            setattr(A, k, default)

# the frozen variant set (docs/PHASE_C3_2_5_LEVER_MATRIX.md)
LEVER_VARIANTS = {
    "baseline": {},
    "settlements_scaled": {"_lever_settlements_by_area": True},
    "escape_gap_bounded@8": {"_lever_bound_gap": 8},
    "escape_gap_bounded@12": {"_lever_bound_gap": 12},
    "escape_gap_bounded@16": {"_lever_bound_gap": 16},
    "escape_gap_bounded@20": {"_lever_bound_gap": 20},
    "town_distance_capped@12": {"_lever_cap_town_dist": 12},
    "town_distance_capped@16": {"_lever_cap_town_dist": 16},
    "town_distance_capped@20": {"_lever_cap_town_dist": 20},
    "sites_across_settlements": {"_lever_spread_sites": True},
}


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


def _walk_required(game):
    """The ordered tile list a survivor must walk to solve THIS mystery:
    spawn -> {route, require, [require2], [power]} nearest-first
          -> obstacle_tile -> escape_tile.
    (`closed` and the town centre are context, not requirements.)
    Returns the tile list, or None when a required node is unreachable /
    there is no mystery."""
    m = getattr(game, "mystery", None)
    if m is None:
        return None
    grid = _terrain_grid(game)
    n = game.map_size
    spawn = tuple(game.current_position)

    required_roles = ["route", "require"]
    if "require2" in m.sites:
        required_roles.append("require2")
    if getattr(m, "power_role", None):
        required_roles.append(m.power_role)
    # C.3.2a-6: scaled intermediate beats are required investigation
    # stops on the corridor (docs/PHASE_C3_2_6_SPEC.md).
    required_roles += list(getattr(m, "required_beats", []))
    targets = [tuple(m.sites[r]) for r in required_roles if r in m.sites]

    tail = []
    ob = getattr(m, "obstacle_tile", None)
    if ob:
        tail.append(tuple(ob))
    esc = getattr(m, "escape_tile", None)
    if esc:
        tail.append(tuple(esc))

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
            return None
        all_tiles += best[0][1:] if all_tiles else best[0]
        cur = best[1]
        remaining.remove(best[1])
    for t in tail:
        p = _seg(grid, n, cur, t)
        if p is None:
            return None
        all_tiles += p[1:] if all_tiles else p
        cur = t
    return all_tiles


def required_circuit(game):
    """Total traversable tiles a survivor must walk, and the backtrack
    proportion. Returns (tiles, backtrack_frac, reachable_ok) or
    (None, None, False)."""
    all_tiles = _walk_required(game)
    if not all_tiles:
        return None, None, False
    total = max(0, len(all_tiles) - 1)
    unique = len(set(all_tiles))
    backtrack = round(1 - unique / len(all_tiles), 3) if all_tiles else 0.0
    return total, backtrack, True


def meaningful_fraction(game):
    """Gate 8 north-star (docs/PHASE_C3_2_5_GATE8_SPEC.md): of the tiles
    on the required journey, what fraction are spent NEAR a meaningful
    story-bearing location (a mystery role site, the obstacle, the
    escape, or a settlement) versus traversing content-free wilderness.

    A long `require -> obstacle` wilderness leg drags this DOWN; a dense
    investigation cluster or a mid-leg staging settlement pushes it UP.
    Returns a float in [0, 1] or None."""
    tiles = _walk_required(game)
    if not tiles:
        return None
    m = game.mystery
    n = game.map_size
    anchors = {tuple(xy) for xy in m.sites.values()}
    for role in ("obstacle_tile", "escape_tile"):
        xy = getattr(m, role, None)
        if xy:
            anchors.add(tuple(xy))
    for y in range(n):
        for x in range(n):
            c = game.map[y][x]
            if isinstance(c, dict) and c.get("terrain") == "town":
                anchors.add((x, y))
    R = 3
    good = sum(1 for t in tiles
               if any(max(abs(t[0] - a[0]), abs(t[1] - a[1])) <= R
                      for a in anchors))
    return round(good / len(tiles), 3)


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

    # C.3.2a-6: required investigation nodes (route/require/require2/
    # power + scaled beats - NOT closed, obstacle, escape) and the raw
    # relationship to map linear scale.
    _story_roles = {"route", "require", "require2"}
    _story_roles |= set(getattr(m, "required_beats", []) or [])
    if getattr(m, "power_role", None):
        _story_roles.add(m.power_role)
    story_nodes = sum(1 for r in _story_roles if m is not None and r in m.sites)
    nodes_per_sqrt = round(story_nodes / max(1.0, playable ** 0.5), 4)

    # the leg this experiment is trying to move
    rto = None
    if m is not None and "require" in m.sites and getattr(m, "obstacle_tile", None):
        p = shortest_path(grid, n, tuple(m.sites["require"]),
                          tuple(m.obstacle_tile))
        rto = (len(p) - 1) if p is not None else None

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
        "req_to_obstacle": rto,
        "story_nodes": story_nodes,                # C.3.2a-6
        "nodes_per_sqrt": nodes_per_sqrt,          # C.3.2a-6
        "meaningful": meaningful_fraction(game),   # Gate 8 north-star
        "legs": circuit_legs(game),
        "ep": endpoint_dists(game),
    }


def _cell(rows):
    """Summarise one (variant, depth) into the matrix metric dict."""
    circ = [r["circuit"] for r in rows]
    bt = [r["backtrack"] for r in rows]
    rto = [r["req_to_obstacle"] for r in rows]
    sreq = [r["ep"].get("require") for r in rows]
    return {
        "n": len(rows),
        "dens": round(statistics.mean(r["dens"] for r in rows), 2),
        "dst_1k": round(statistics.mean(r["dest_density"] for r in rows), 3),
        "story_nodes_p50": round(_p([r["story_nodes"] for r in rows], .5), 1),
        "nodes_per_sqrt_p50": round(
            statistics.mean(r["nodes_per_sqrt"] for r in rows), 4),
        "meaningful_p50": round(_p([r["meaningful"] for r in rows], .5), 3),
        "circ_p50": round(_p(circ, .5), 1),
        "circ_p90": round(_p(circ, .9), 1),
        "req_obst_p50": round(_p(rto, .5), 1),
        "req_obst_p90": round(_p(rto, .9), 1),
        "spawn_req_p50": round(_p(sreq, .5), 1),
        "spawn_req_p90": round(_p(sreq, .9), 1),
        "ratio_p90": round(_p([r["ratio"] for r in rows], .9), 3),
        "pct_over_budget": round(
            100 * sum(1 for r in rows if r["over_budget"]) / len(rows), 1),
        "backtrack_p50": round(_p(bt, .5), 3),
        "backtrack_p90": round(_p(bt, .9), 3),
        "infeasible_pct": round(
            100 * sum(1 for r in rows if r["infeasible"]) / len(rows), 2),
    }


def run_lever_matrix(games, depths):
    import json
    out = {"budget_usable": USABLE_BUDGET, "games_per_cell": games,
           "variants": {}}
    for vname, levers in LEVER_VARIANTS.items():
        out["variants"][vname] = {}
        for d in depths:
            rows = [measure(_forced_game(
                        i, d, MECH_ROTATION[i % len(MECH_ROTATION)], levers))
                    for i in range(games)]
            out["variants"][vname][str(d)] = _cell(rows)
        base = out["variants"]["baseline"]
        v = out["variants"][vname]
        d_ref = str(max(depths))
        print(f"{vname:>26}  d{d_ref}: ratio p90 "
              f"{v[d_ref]['ratio_p90']:.2f} "
              f"(base {base[d_ref]['ratio_p90']:.2f})  "
              f"req->obst p90 {v[d_ref]['req_obst_p90']:.0f} "
              f"(base {base[d_ref]['req_obst_p90']:.0f})  "
              f"btrk p90 {v[d_ref]['backtrack_p90']:.2f}  "
              f"infeas {v[d_ref]['infeasible_pct']:.1f}%  "
              f"dst/1k {v[d_ref]['dst_1k']:.2f}")

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "lever_matrix.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nwrote {os.path.join(here, 'lever_matrix.json')}")
    return out


# --- Gate 8: the "distributed investigation" experiment ---------------
#   docs/PHASE_C3_2_5_GATE8_SPEC.md. Two variants (baseline + distributed
#   = lever 4 spread + lever 2's relational gap ceiling), the gap bound
#   swept in both forms. `+setts` layers the lever-1 density floor.
GATE8_VARIANTS = {
    "baseline": {},
    "distributed@sqrt0.6": {"_lever_spread_sites": True,
                            "_lever_bound_gap": ("sqrt", 0.6)},
    "distributed@sqrt0.8": {"_lever_spread_sites": True,
                            "_lever_bound_gap": ("sqrt", 0.8)},
    "distributed@sqrt1.0": {"_lever_spread_sites": True,
                            "_lever_bound_gap": ("sqrt", 1.0)},
    "distributed@cap16": {"_lever_spread_sites": True,
                          "_lever_bound_gap": ("cap", 16)},
    "distributed@cap20": {"_lever_spread_sites": True,
                          "_lever_bound_gap": ("cap", 20)},
    "distributed@cap24": {"_lever_spread_sites": True,
                          "_lever_bound_gap": ("cap", 24)},
    "distributed+setts@sqrt0.8": {"_lever_spread_sites": True,
                                  "_lever_bound_gap": ("sqrt", 0.8),
                                  "_lever_settlements_by_area": True},
    "distributed+setts@sqrt1.0": {"_lever_spread_sites": True,
                                  "_lever_bound_gap": ("sqrt", 1.0),
                                  "_lever_settlements_by_area": True},
}

_SUPPORTED_DEPTHS = 12   # the gate applies to depths 0..12 (spec §5.1)


def _gate8_verdict(cells, base):
    """Score one variant's per-depth cells against GATE8_SPEC §5.
    `cells` / `base` are {depth_str: metric_dict}. Returns (pass_bool,
    list_of_reason_strings)."""
    reasons = []
    depths = sorted((int(d) for d in cells), key=int)
    supported = [d for d in depths if d <= _SUPPORTED_DEPTHS]
    deep = [d for d in supported if d >= 9]

    # 1. gate: ratio p90 < 1 at every supported depth
    bad = [d for d in supported if cells[str(d)]["ratio_p90"] >= 1.0]
    if bad:
        reasons.append("FAIL gate: ratio p90 >= 1 at depths "
                       + ",".join(map(str, bad)))
    # 2. meaningful geography: deep meaningful_p50 within 0.15 of base d0
    m0 = base["0"]["meaningful_p50"]
    mbad = [d for d in deep
            if cells[str(d)]["meaningful_p50"] < m0 - 0.15]
    if mbad:
        reasons.append(f"FAIL meaningful: p50 at {mbad} below base-d0 "
                       f"{m0:.2f} - 0.15")
    # 3. density held: dens AND dst_1k >= same-depth baseline at deep
    dbad = [d for d in deep
            if cells[str(d)]["dens"] < base[str(d)]["dens"] - 1e-9
            or cells[str(d)]["dst_1k"] < base[str(d)]["dst_1k"] - 1e-9]
    if dbad:
        reasons.append(f"FAIL density: dens/dst_1k below baseline at {dbad}")
    # 4. backtrack held: p90 <= 1.5x same-depth baseline
    bbad = [d for d in supported
            if cells[str(d)]["backtrack_p90"]
            > 1.5 * max(base[str(d)]["backtrack_p90"], 0.02) + 1e-9]
    if bbad:
        reasons.append(f"FAIL backtrack: p90 > 1.5x baseline at {bbad}")
    # 5. infeasible = 0
    ibad = [d for d in supported if cells[str(d)]["infeasible_pct"] > 0]
    if ibad:
        reasons.append(f"FAIL infeasible: > 0% at {ibad}")

    return (not reasons), (reasons or ["PASS all of GATE8_SPEC §5"])


def run_gate8(games, depths):
    import json
    out = {"budget_usable": USABLE_BUDGET, "games_per_cell": games,
           "supported_depths": _SUPPORTED_DEPTHS, "variants": {},
           "verdict": {}}
    for vname, levers in GATE8_VARIANTS.items():
        out["variants"][vname] = {}
        for d in depths:
            rows = [measure(_forced_game(
                        i, d, MECH_ROTATION[i % len(MECH_ROTATION)], levers))
                    for i in range(games)]
            out["variants"][vname][str(d)] = _cell(rows)
    base = out["variants"]["baseline"]
    d_ref = str(max(depths))

    print(f"{'variant':>26}  {'d'+d_ref+' ratio':>10} {'mean_p50':>9} "
          f"{'r->o p90':>9} {'s->req p90':>10} {'btrk p90':>9} "
          f"{'dst/1k':>7} {'infeas':>7}")
    for vname in GATE8_VARIANTS:
        c = out["variants"][vname][d_ref]
        print(f"{vname:>26}  {c['ratio_p90']:>10.2f} "
              f"{c['meaningful_p50']:>9.2f} {c['req_obst_p90']:>9.0f} "
              f"{c['spawn_req_p90']:>10.0f} "
              f"{c['backtrack_p90']:>9.2f} {c['dst_1k']:>7.2f} "
              f"{c['infeasible_pct']:>6.1f}%")
        if vname != "baseline":
            ok, reasons = _gate8_verdict(out["variants"][vname], base)
            out["verdict"][vname] = {"pass": ok, "reasons": reasons}
            for r in reasons:
                print(f"{'':>28}  - {r}")

    passing = [v for v, r in out["verdict"].items() if r["pass"]]
    print("\n=== GATE 8 §5 verdict ===")
    print("PASSING variant(s): " + (", ".join(passing) if passing else "NONE"))
    if not passing:
        print("-> hypothesis FALSIFIED for these bounds (GATE8_SPEC §6). "
              "No swept bound satisfies §5 simultaneously.")

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "gate8_matrix.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nwrote {os.path.join(here, 'gate8_matrix.json')}")
    return out


# --- C.3.2a-6: Scaled Investigation Structure ------------------------
#   docs/PHASE_C3_2_6_SPEC.md. Does the required story acquiring MORE
#   intermediate structure as the world grows restore viability? Sweep
#   the scaling form; fixed@N are controls (§7.7).
GATE6_VARIANTS = {
    "baseline": {},
    "fixed@1": {"_lever_scaled_beats": ("fixed", 1)},
    "fixed@2": {"_lever_scaled_beats": ("fixed", 2)},
    "log@1.5": {"_lever_scaled_beats": ("log", 1.5)},
    "log@2": {"_lever_scaled_beats": ("log", 2)},
    "sqrt@1": {"_lever_scaled_beats": ("sqrt", 1)},
    "sqrt@1.5": {"_lever_scaled_beats": ("sqrt", 1.5)},
    "linear@1": {"_lever_scaled_beats": ("linear", 1)},
    "linear@1.5": {"_lever_scaled_beats": ("linear", 1.5)},
}


def _gate6_verdict(cells, base):
    """Score one form against GATE6_SPEC §7. Returns (pass_bool, reasons)."""
    reasons = []
    depths = sorted((int(d) for d in cells), key=int)
    supported = [d for d in depths if d <= _SUPPORTED_DEPTHS]
    deep = [d for d in supported if d >= 9]

    bad = [d for d in supported if cells[str(d)]["ratio_p90"] >= 1.0]
    if bad:
        reasons.append("FAIL gate: ratio p90 >= 1 at depths "
                       + ",".join(map(str, bad)))
    m0 = base["0"]["meaningful_p50"]
    mbad = [d for d in deep if cells[str(d)]["meaningful_p50"] < m0 - 0.15]
    if mbad:
        reasons.append(f"FAIL meaningful: p50 at {mbad} below base-d0 "
                       f"{m0:.2f} - 0.15")
    dbad = [d for d in deep
            if cells[str(d)]["dens"] < base[str(d)]["dens"] - 1e-9
            or cells[str(d)]["dst_1k"] < base[str(d)]["dst_1k"] - 1e-9]
    if dbad:
        reasons.append(f"FAIL density: dens/dst_1k below baseline at {dbad}")
    bbad = [d for d in supported
            if cells[str(d)]["backtrack_p90"]
            > 1.5 * max(base[str(d)]["backtrack_p90"], 0.02) + 1e-9]
    if bbad:
        reasons.append(f"FAIL backtrack: p90 > 1.5x baseline at {bbad}")
    ibad = [d for d in supported if cells[str(d)]["infeasible_pct"] > 0]
    if ibad:
        reasons.append(f"FAIL infeasible: > 0% at {ibad}")
    return (not reasons), (reasons or ["PASS all of GATE6_SPEC §7.1-7.6"])


def run_heir_budget(games, depths):
    """C.3.2a-7: does the inheritance-scaled starting supply
    (game.depth_supply_bonus) bring a fresh survivor ARRIVING at each
    depth back under budget? effective_usable = USABLE_BUDGET + 2 move-
    equivalents per bonus ration (a +5 ration ~ 2 moves at 2.5/move
    decay), counted once - food and water deplete in parallel so the
    binding constraint moves in lockstep."""
    print(f"{'depth':>5} {'map':>7} {'circ p50':>9} {'circ p90':>9} "
          f"{'bonus':>6} {'eff.budget':>10} {'ratio p90':>10} "
          f"{'>budget':>8}  supported<=" + str(SUPPORTED_DEPTH))
    results = {}
    for d in depths:
        rows = [measure(_forced_game(i, d, MECH_ROTATION[i % len(MECH_ROTATION)]))
                for i in range(games)]
        circ = [r["circuit"] for r in rows if r["circuit"] is not None]
        bonus = depth_supply_bonus(d)
        eff = USABLE_BUDGET + 2 * bonus
        p90 = _p(circ, .9)
        ratio = p90 / eff
        over = 100 * sum(1 for c in circ if c > eff) / max(1, len(circ))
        sz = rows[0]["map"]
        results[d] = ratio < 1.0
        print(f"{d:>5} {f'{sz}x{sz}':>7} {_p(circ,.5):>9.0f} {p90:>9.0f} "
              f"{bonus:>6} {eff:>10} {ratio:>10.2f} {over:>7.0f}%"
              f"{'  OK' if ratio < 1.0 else '  OVER'}")
    ok_through = 0
    for d in sorted(results):
        if results[d]:
            ok_through = d
        else:
            break
    print(f"\ninheritance-scaled supply keeps ratio p90 < 1 through "
          f"depth {ok_through}  (contract target: {SUPPORTED_DEPTH})")


def run_gate6(games, depths):
    import json
    out = {"budget_usable": USABLE_BUDGET, "games_per_cell": games,
           "supported_depths": _SUPPORTED_DEPTHS, "variants": {},
           "verdict": {}}
    for vname, levers in GATE6_VARIANTS.items():
        out["variants"][vname] = {}
        for d in depths:
            rows = [measure(_forced_game(
                        i, d, MECH_ROTATION[i % len(MECH_ROTATION)], levers))
                    for i in range(games)]
            out["variants"][vname][str(d)] = _cell(rows)
    base = out["variants"]["baseline"]
    d_ref = str(max(depths))

    print(f"{'variant':>14}  {'d'+d_ref+' ratio':>10} {'mean_p50':>9} "
          f"{'nodes p50':>10} {'n/sqrt':>7} {'r->o p90':>9} "
          f"{'btrk p90':>9} {'dst/1k':>7} {'infeas':>7}")
    for vname in GATE6_VARIANTS:
        c = out["variants"][vname][d_ref]
        print(f"{vname:>14}  {c['ratio_p90']:>10.2f} {c['meaningful_p50']:>9.2f} "
              f"{c['story_nodes_p50']:>10.1f} {c['nodes_per_sqrt_p50']:>7.3f} "
              f"{c['req_obst_p90']:>9.0f} {c['backtrack_p90']:>9.2f} "
              f"{c['dst_1k']:>7.2f} {c['infeasible_pct']:>6.1f}%")
        if vname != "baseline":
            ok, reasons = _gate6_verdict(out["variants"][vname], base)
            out["verdict"][vname] = {"pass": ok, "reasons": reasons}
            for r in reasons:
                print(f"{'':>16}- {r}")

    scaled_pass = [v for v in out["verdict"]
                   if out["verdict"][v]["pass"] and not v.startswith("fixed")]
    fixed_pass = [v for v in out["verdict"]
                  if out["verdict"][v]["pass"] and v.startswith("fixed")]
    print("\n=== GATE 6 §7 verdict ===")
    print("scaled form(s) passing: " + (", ".join(scaled_pass) or "NONE"))
    print("fixed control(s) passing: " + (", ".join(fixed_pass) or "NONE"))
    if scaled_pass and not fixed_pass:
        print("-> §7 MET: scaling restores viability; a constant +N does not "
              "(the rule is +f(map), not +N).")
    elif scaled_pass and fixed_pass:
        print("-> §7.7: scaled forms pass BUT so does a fixed control - "
              "'scaling' is not what did the work. Rule is likely '+N beats'.")
    elif fixed_pass and not scaled_pass:
        print("-> only a fixed +N passes. Simpler rule; report it (§8).")
    else:
        print("-> §8 FALSIFIED: structural growth alone does not clear the "
              "supported depths. -> next: formally bound supported depth 0-N.")

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "gate6_matrix.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nwrote {os.path.join(here, 'gate6_matrix.json')}")
    return out


def _p(v, q):
    v = sorted(x for x in v if x is not None)
    return v[min(len(v) - 1, int(len(v) * q))] if v else float("nan")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--games", type=int, default=300,
                    help="seeds sampled per depth (default: 300)")
    ap.add_argument("--depths", default="0,1,2,3,4,6,9,12",
                    help="comma-separated expedition depths to measure")
    ap.add_argument("--levers", action="store_true",
                    help="run the C.3.2a-5 lever A/B matrix instead of the "
                         "single-variant scale report")
    ap.add_argument("--gate8", action="store_true",
                    help="run the Gate 8 distributed-investigation experiment "
                         "(docs/PHASE_C3_2_5_GATE8_SPEC.md)")
    ap.add_argument("--gate6", action="store_true",
                    help="run the C.3.2a-6 scaled-investigation-structure "
                         "experiment (docs/PHASE_C3_2_6_SPEC.md)")
    ap.add_argument("--heir-budget", action="store_true",
                    help="C.3.2a-7: check the inheritance-scaled supply floor "
                         "against the required circuit by depth")
    args = ap.parse_args()
    depths = [int(x) for x in args.depths.split(",")]

    print(f"budget: gross {GROSS_BUDGET} moves, usable (investigative) "
          f"{USABLE_BUDGET}  [docs/PHASE_C3_2_5_SPEC.md]")
    print()

    if args.heir_budget:
        run_heir_budget(args.games, depths)
        return

    if args.gate6:
        run_gate6(args.games, depths)
        return

    if args.gate8:
        run_gate8(args.games, depths)
        return

    if args.levers:
        run_lever_matrix(args.games, depths)
        return

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
