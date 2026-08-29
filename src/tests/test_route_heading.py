"""C.3.2 piece 0: the ESCAPE-panel route heading is graph-honest.

`tui._route_heading` must not advertise a compass direction the actual
route immediately contradicts - the exact v2 feel-test failure ("head
north-east" into a ridge that forces you west first).
"""
import unittest

from src.tui import _route_heading


def _grid(n, mountains=()):
    mset = set(mountains)
    return [[{"terrain": "mountain" if (x, y) in mset else "plain"}
             for x in range(n)] for y in range(n)]


class TestRouteHeading(unittest.TestCase):
    def test_v2_detour_is_not_advertised_as_the_straight_line(self):
        # dest is straight-line north-east, but a tall wall just east of
        # the player forces the real route SOUTH-east first (down and
        # around the wall). The northward half of the claim was the lie.
        n = 12
        wall = [(7, y) for y in range(0, 9)]
        g = _grid(n, wall)
        here, dest = (6, 5), (10, 1)          # bearing(here, dest) == "north-east"
        out = _route_heading(here, dest, g, n)
        self.assertNotIn("north", out)         # the reversed axis is gone
        self.assertEqual(out, " (south-east)")  # the honest early heading

    def test_honest_straight_line_is_kept(self):
        n = 12
        g = _grid(n)
        out = _route_heading((5, 9), (5, 1), g, n)   # due north, open ground
        self.assertEqual(out, " (north)")

    def test_unreachable_route_falls_back_to_straight_line(self):
        # full wall between player and dest -> no path -> the UI still
        # gets a direction to show, unchanged from before C.3.2.
        n = 12
        wall = [(5, y) for y in range(n)]
        g = _grid(n, wall)
        out = _route_heading((1, 1), (10, 10), g, n)
        self.assertEqual(out, " (south-east)")

    def test_on_top_reads_near_here(self):
        n = 8
        g = _grid(n)
        self.assertEqual(_route_heading((4, 4), (5, 4), g, n), " (near here)")
        self.assertEqual(_route_heading((4, 4), None, g, n), "")

    def test_zombie_on_the_line_does_not_change_the_heading(self):
        # a non-dict tile (a Zombie object stand-in) on the direct path
        # is treated as passable for the topology check.
        n = 10
        g = _grid(n)
        g[4][5] = "ZOMBIE"            # right between (5,8) and (5,1)
        self.assertEqual(_route_heading((5, 8), (5, 1), g, n), " (north)")


if __name__ == "__main__":
    unittest.main()
