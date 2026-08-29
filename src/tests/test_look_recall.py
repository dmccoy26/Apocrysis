"""C.3.2 piece 2 — `look` re-surfaces the route direction so a player
who wandered away from the objective can recover it WITHOUT discovering
anything new. This is Invariant 5 (Navigation Persistence) in
executable form.
"""
import re
import unittest

from src.game import Apocrysis
from src.nav import honest_bearing
from src.worldgen.reachable import reachable_set

_DIRS = ("north", "south", "east", "west", "north-east", "north-west",
         "south-east", "south-west")


class _IO:
    renders_natively = True

    def __init__(self):
        self.log = []

    def say(self, *a, **k):
        self.log.append(" ".join(str(x) for x in a))

    def ask(self, prompt=""):
        return ""

    def ask_yes_no(self, prompt):
        return False


def _far_reachable(g):
    grid = [[c if isinstance(c, dict) else {"terrain": "plain"} for c in row]
            for row in g.map]
    reach = reachable_set(grid, g.map_size, g.current_position)
    sx, sy = g.current_position
    return max(reach, key=lambda p: abs(p[0] - sx) + abs(p[1] - sy))


class TestLookRecall(unittest.TestCase):
    def test_wander_then_look_recovers_the_direction_with_no_discovery(self):
        checked = 0
        for seed in range(40):
            g = Apocrysis("Look", seed=seed, io=_IO(), expeditions_completed=2)
            m = getattr(g, "mystery", None)
            if not m or not m.sites.get("route"):
                continue
            from src.escape import MECHANISMS
            if MECHANISMS.get(m.mechanism, {}).get("reveals_route"):
                continue  # informational: covered separately
            checked += 1

            facts_before = set(m.knowledge.facts_known())
            # wander: teleport to the farthest reachable tile, discover nothing
            g.current_position = tuple(_far_reachable(g))
            self.assertEqual(set(m.knowledge.facts_known()), facts_before)

            g.io = _IO()
            g.knowledge_look()
            out = "\n".join(g.io.log)

            # nothing was discovered by looking
            self.assertEqual(set(m.knowledge.facts_known()), facts_before)

            # a recoverable, actionable direction was given
            self.assertIn("You get your bearings", out)
            mobj = re.search(r"lies to the ([a-z-]+)\.", out)
            self.assertIsNotNone(mobj, out)
            self.assertIn(mobj.group(1), _DIRS)

            # and it agrees with the graph-honest bearing from here
            expected = honest_bearing(g.current_position, tuple(m.sites["route"]),
                                      g.map, g.map_size)
            self.assertEqual(mobj.group(1), expected)

        self.assertGreater(checked, 5)

    def test_informational_family_stays_silent_until_the_route_is_known(self):
        from src.escape import MECHANISMS
        info_mech = next(k for k, v in MECHANISMS.items() if v.get("reveals_route"))
        for seed in range(40):
            g = Apocrysis("Info", seed=seed, io=_IO(), expeditions_completed=2)
            m = getattr(g, "mystery", None)
            if not m or not m.sites.get("route"):
                continue
            m.mechanism = info_mech  # force the informational family
            self.assertNotIn("F_ROUTE", m.knowledge.facts_known())
            g.current_position = tuple(_far_reachable(g))
            g.io = _IO()
            g.knowledge_look()
            # reveals_route + F_ROUTE unknown -> the route has no place the
            # player could head for yet; look must not point at one.
            self.assertNotIn("You get your bearings", "\n".join(g.io.log))
            return

    def test_standing_on_the_route_site_does_not_double_up(self):
        for seed in range(40):
            g = Apocrysis("OnSite", seed=seed, io=_IO(), expeditions_completed=2)
            m = getattr(g, "mystery", None)
            if not m or not m.sites.get("route"):
                continue
            g.current_position = tuple(m.sites["route"])
            g.io = _IO()
            g.knowledge_look()
            # on the site, look does the arrival pass, not the recall line
            self.assertNotIn("You get your bearings", "\n".join(g.io.log))
            return


if __name__ == "__main__":
    unittest.main()
