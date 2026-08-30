"""The landscape map generator (docs/MAP_REALISM_SPEC.md 1b/2/3).

Flag-gated: `Apocrysis(mapgen="landscape")`. v1 stays square and
byte-identical (that's `test_worldgen_structure`); this covers the new
variant only.
"""
import unittest

from src.game import Apocrysis
from src.constants import MAP_ASPECT


class _IO:
    renders_natively = True

    def say(self, *a, **k):
        pass

    def ask(self, prompt=""):
        return ""

    def ask_yes_no(self, prompt):
        return False


def _lg(seed=1, depth=9):
    return Apocrysis("Lg", seed=seed, io=_IO(), expeditions_completed=depth,
                     mapgen="landscape")


class TestLandscapeShape(unittest.TestCase):
    def test_grid_is_wider_than_tall(self):
        g = _lg()
        self.assertEqual(g.map_h, g.map_size)
        self.assertEqual(g.map_w, round(g.map_size * MAP_ASPECT))
        self.assertGreater(g.map_w, g.map_h)
        self.assertEqual(len(g.map), g.map_h)
        self.assertEqual(len(g.map[0]), g.map_w)

    def test_v1_stays_square(self):
        g = Apocrysis("Sq", seed=1, io=_IO(), expeditions_completed=9)
        self.assertEqual(g.map_w, g.map_h)
        self.assertEqual(g.map_w, g.map_size)

    def test_seed_deterministic(self):
        def terr(g):
            return [[c.get("terrain") if isinstance(c, dict) else "Z"
                     for c in row] for row in g.map]
        self.assertEqual(terr(_lg(seed=7)), terr(_lg(seed=7)))


class TestLandscapeTerrain(unittest.TestCase):
    def test_mountains_are_mass_not_scatter(self):
        g = _lg()
        mtn = sum(1 for row in g.map for c in row
                  if isinstance(c, dict) and c.get("terrain") == "mountain")
        # the band alone is ~2*(w+h)*2; blobs add more. A 1-tile ring
        # would be ~2*(w+h) only.
        self.assertGreater(mtn, 2 * (g.map_w + g.map_h))

    def test_a_connected_river_with_bridges(self):
        for seed in range(6):
            g = _lg(seed=seed)
            river = [(x, y) for y, row in enumerate(g.map)
                     for x, c in enumerate(row)
                     if isinstance(c, dict) and c.get("terrain") == "river"]
            bridge = [(x, y) for y, row in enumerate(g.map)
                      for x, c in enumerate(row)
                      if isinstance(c, dict) and c.get("terrain") == "bridge"]
            self.assertGreaterEqual(len(river), 10, f"seed {seed}: thin river")
            self.assertGreaterEqual(len(bridge), 1, f"seed {seed}: no bridge")

    def test_mystery_still_builds_and_is_reachable(self):
        for seed in range(6):
            g = _lg(seed=seed)
            self.assertIsNotNone(g.mystery, f"seed {seed}: no mystery")
            # every required node reachable (MapGraph guarantee)
            self.assertEqual(g._map_graph.unreachable_from("spawn"), [])


class TestSwim(unittest.TestCase):
    def test_swim_offered_only_on_landscape(self):
        g = _lg()
        self.assertNotEqual(g._try_swim_river.__self__._mapgen, "v1")
        # a v1 river tile just blocks
        v1 = Apocrysis("Sq", seed=1, io=_IO(), expeditions_completed=9)
        self.assertFalse(v1._try_swim_river(1, 1))

    def test_declining_the_swim_keeps_you_put(self):
        g = _lg()
        river = next(((x, y) for y, row in enumerate(g.map)
                      for x, c in enumerate(row)
                      if isinstance(c, dict) and c.get("terrain") == "river"), None)
        self.assertIsNotNone(river)
        before = g.current_position
        g.io.ask_yes_no = lambda p: False
        self.assertFalse(g._try_swim_river(*river))
        self.assertEqual(g.current_position, before)

    def test_odds_go_up_with_waders(self):
        g = _lg()
        base = g._swim_odds()
        g.has_waders = True
        self.assertGreater(g._swim_odds(), base)


if __name__ == "__main__":
    unittest.main()
