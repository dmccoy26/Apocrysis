#!/usr/bin/env python3
"""Navigation / objective investigation.

The resource investigation (RESOURCE_MODEL_RESULTS.md) put the blame
upstream: campaigns run long because the survivor WANDERS, and both
resources deplete on that clock. Before touching hunger/fatigue, this
measures the navigation itself - causally, with the perceived-bot
`objective` policy that acts on perceived text only.

For every turn it records (the ground-truth objective tile is used for
ANALYSIS ONLY - never fed to the policy):

  - is a mystery marker visible on the rendered map?
  - distance to the real objective, and the delta from this move
    (closed / widened / neutral)
  - turn category: pursuing · investigating · exploring · recovering ·
    wandering  (combat is its own event)
  - when it wanders: no marker visible / marker unreachable / other

Reports: turn taxonomy, closed-vs-widened moves while an objective is
knowable, turns-to-objective, revisits-with-an-open-objective,
distance travelled vs spawn->objective, and the cardinal-vs-landmark
A/B (`--nav-phrasing`).

    python3 tools/nav_autoplay.py --campaigns 15
    python3 tools/nav_autoplay.py --campaigns 15 --nav-phrasing cardinal
    python3 tools/nav_autoplay.py --nav-phrasing landmark --md docs/NAV_INVESTIGATION_RESULTS.md
"""
import argparse
import os
import statistics
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.telemetry import Recorder, TelemetryIO, _Stop
from tools.autoplay import policies as _policies
from src.constants import CAMPAIGN_LENGTH
from src.game import Apocrysis
from src import tui as _tui

_DELTA = {"n": (0, -1), "s": (0, 1), "e": (1, 0), "w": (-1, 0)}


def _objective_tile(p):
    """The tile the survivor SHOULD be heading for right now, derived
    from real mystery state. ANALYSIS ONLY."""
    m = getattr(p, "mystery", None)
    if m is None:
        return None
    searched = getattr(p, "_mystery_named", set())
    for role in ("route", "require", "require2"):
        if role in m.sites and role not in searched \
                and role not in getattr(m, "_site_evidence_done", ()):
            # not-yet-visited required site
            if p.current_position != m.sites[role]:
                return m.sites[role]
    if getattr(m, "power_role", None) and not m.power_restored:
        return m.sites.get(m.power_role)
    if not m.obstacle_open and getattr(m, "obstacle_tile", None):
        return m.obstacle_tile
    return m.escape_tile


def _manh(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class NavIO(TelemetryIO):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self._prev_obj_dist = None
        self._visited = Counter()
        self._objective_known_turn = None
        self._reached_turn = None
        self._spawn_obj = None

    def ask(self, prompt=""):
        cmd = super().ask(prompt)
        if prompt.strip().startswith("Press Enter"):
            return cmd
        p = self.player
        per = self._perceive()
        obj = _objective_tile(p)
        pos = p.current_position
        self._visited[pos] += 1

        marker_visible = bool(per.glyph_positions("!+"))
        dist = _manh(pos, obj) if obj else None
        delta = None
        if dist is not None and self._prev_obj_dist is not None:
            delta = dist - self._prev_obj_dist   # <0 closed, >0 widened
        # "knows an objective" = a lead marker is / has been visible on
        # the map. The panel text alone isn't enough (it says "head for
        # the way out" from turn 1).
        if marker_visible:
            self._ever_saw_marker = True
        knows = getattr(self, "_ever_saw_marker", False)
        if knows and self._objective_known_turn is None:
            self._objective_known_turn = self._turn
        if obj and pos == obj and self._reached_turn is None:
            self._reached_turn = self._turn

        # categorise the turn
        if cmd in ("eat", "drink", "med", "rest"):
            cat = "recovering"
        elif cmd == "search":
            cat = "investigating" if marker_visible else "exploring"
        elif cmd in _DELTA:
            if not knows:
                cat = "exploring"
            elif delta is not None and delta < 0:
                cat = "pursuing"
            elif delta is not None and delta > 0:
                cat = "wandering"
            else:
                cat = "pursuing" if marker_visible else "exploring"
        else:
            cat = "other"

        why_wander = None
        if cat == "wandering":
            why_wander = ("no marker visible" if not marker_visible
                          else "marker visible but moved away")

        self.rec.emit(self._turn, "nav", category=cat, action=cmd,
                      knows_objective=knows, marker_visible=marker_visible,
                      obj_dist=dist, obj_delta=delta, why_wander=why_wander,
                      pos=list(pos), revisit=self._visited[pos])
        self._prev_obj_dist = dist
        if self._spawn_obj is None and obj is not None:
            self._spawn_obj = _manh(pos, obj)
        return cmd


def run_campaign_nav(rec, policy_name, seed, phrasing, max_turns=600, max_attempts=6):
    import random
    _tui._SPATIAL_MODE = phrasing
    Apocrysis._used_mechanisms = []
    profile, level, exp = None, 1, 0
    attempts = defaultdict(int)
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        pf = os.path.join(tmp, "p.json")
        while exp < CAMPAIGN_LENGTH:
            attempts[exp] += 1
            if attempts[exp] > max_attempts:
                rec.emit(0, "campaign_end", reason="stuck", stuck_at=exp)
                return
            rec.run += 1
            pol = _policies.make(policy_name, rng=random.Random(seed + rec.run))
            io = NavIO(pol, rec, max_turns=max_turns)
            p = Apocrysis("Nav", level=level, expeditions_completed=exp,
                          seed=seed + rec.run * 7, io=io)
            if profile is not None:
                p.apply_profile(profile)
            io.player = p
            try:
                p.run_game_loop()
            except _Stop:
                pass
            io._flush_combat()
            outcome = ("won" if getattr(p, "won", False)
                       else "died" if p.health <= 0 else "timeout")
            rec.emit(io._turn, "nav_expedition_end", exp=exp, outcome=outcome,
                     turns=io._turn,
                     objective_known_turn=io._objective_known_turn,
                     reached_turn=io._reached_turn,
                     spawn_to_obj=io._spawn_obj,
                     unique_tiles=len(io._visited),
                     total_moves=sum(io._visited.values()))
            level = p.level
            p.save_profile(pf)
            profile = Apocrysis.load_profile(pf)
            if getattr(p, "won", False):
                exp = p.expeditions_completed
    rec.emit(0, "campaign_end", reason="complete")


def report(events, phrasing):
    nav = [e for e in events if e["event"] == "nav"]
    ends = [e for e in events if e["event"] == "nav_expedition_end"]
    L = ["=" * 66, f" NAVIGATION / OBJECTIVE  -  phrasing: {phrasing}", "=" * 66]
    L.append(f" expeditions: {len(ends)}   nav turns: {len(nav)}")
    oc = Counter(e["outcome"] for e in ends)
    L.append(" outcomes: " + "  ".join(f"{k} {v}" for k, v in oc.most_common()))

    cats = Counter(e["category"] for e in nav)
    tot = sum(cats.values()) or 1
    L.append("\n TURN TAXONOMY")
    for c in ("pursuing", "investigating", "exploring", "recovering",
              "wandering", "other"):
        L.append(f"   {c:<14} {cats.get(c, 0):>5}  ({100*cats.get(c, 0)//tot}%)")

    moves = [e for e in nav if e["obj_delta"] is not None and e["knows_objective"]]
    closed = sum(1 for e in moves if e["obj_delta"] < 0)
    widened = sum(1 for e in moves if e["obj_delta"] > 0)
    neutral = len(moves) - closed - widened
    L.append("\n MOVES WHILE AN OBJECTIVE IS KNOWABLE")
    L.append(f"   closed distance:  {closed}  ({100*closed//max(1,len(moves))}%)")
    L.append(f"   widened distance: {widened}  ({100*widened//max(1,len(moves))}%)")
    L.append(f"   neutral:          {neutral}")

    ww = Counter(e["why_wander"] for e in nav if e["why_wander"])
    L.append("\n WHY IT WANDERS: " + ", ".join(f"{k} ×{v}" for k, v in ww.most_common()))

    revis = [e for e in nav if e["knows_objective"] and e["revisit"] > 1]
    L.append(f"\n revisits of a tile WHILE an objective is knowable: {len(revis)} "
             f"({100*len(revis)//max(1,len(nav))}% of nav turns)")

    known_t = [e["objective_known_turn"] for e in ends if e["objective_known_turn"]]
    reached = [e for e in ends if e["reached_turn"]]
    L.append(f"\n objective became knowable by turn (median): "
             f"{statistics.median(known_t):.0f}" if known_t else
             "\n objective never became knowable in any expedition")
    if reached:
        tto = [e["reached_turn"] for e in reached]
        L.append(f" objective tile physically reached: {len(reached)}/{len(ends)} "
                 f"expeditions, at turn (median) {statistics.median(tto):.0f}")
        eff = [e["total_moves"] / max(1, e["spawn_to_obj"]) for e in reached
               if e["spawn_to_obj"]]
        if eff:
            L.append(f" path efficiency (moves taken / spawn→objective distance, "
                     f"median): {statistics.median(eff):.1f}×")
    else:
        L.append(f" objective tile physically reached: 0/{len(ends)}")
    uniq = [e["unique_tiles"] / max(1, e["total_moves"]) for e in ends if e["total_moves"]]
    L.append(f" unique-tile ratio (1 = never revisits): median "
             f"{statistics.median(uniq):.2f}" if uniq else "")
    L.append("=" * 66)
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--campaigns", type=int, default=12)
    ap.add_argument("--policy", default="objective",
                    choices=["objective", "explorer", "resource"])
    ap.add_argument("--nav-phrasing", default="landmark",
                    choices=["landmark", "cardinal"])
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--jsonl", default=None)
    ap.add_argument("--md", default=None)
    args = ap.parse_args()

    rec = Recorder(args.jsonl)
    try:
        for c in range(args.campaigns):
            rec.campaign = c + 1
            run_campaign_nav(rec, args.policy, args.seed + c * 1000,
                             args.nav_phrasing)
            print(f"  campaign {c+1}/{args.campaigns} ({len(rec.events)} events)")
    finally:
        rec.close()
        _tui._SPATIAL_MODE = "landmark"

    rpt = report(rec.events, args.nav_phrasing)
    print("\n" + rpt)
    if args.md:
        with open(args.md, "w") as f:
            f.write(f"# Navigation / objective investigation\n\n"
                    f"`tools/nav_autoplay.py` - policy `{args.policy}`, "
                    f"{args.campaigns} campaigns.\n\n```\n" + rpt + "\n```\n")
        print(f"\n wrote {args.md}")


if __name__ == "__main__":
    main()
