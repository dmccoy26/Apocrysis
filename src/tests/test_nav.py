"""C.3.2 build-order step 1: the navigation helpers (src/nav.py).

bearing() - plane compass word with a deadzone.
heading_is_honest() - monotonic-progress test: is a claimed heading a
fair description of where a route actually goes early on?
"""
import unittest

from src.nav import bearing, heading_is_honest


def _line(*pts):
    """A path from explicit (x, y) waypoints - dense-stepped so
    len(path) reflects real tile count."""
    out = [tuple(pts[0])]
    for nxt in pts[1:]:
        x, y = out[-1]
        tx, ty = nxt
        while (x, y) != (tx, ty):
            if x != tx:
                x += 1 if tx > x else -1
            elif y != ty:
                y += 1 if ty > y else -1
            out.append((x, y))
    return out


class TestBearing(unittest.TestCase):
    def test_cardinals_y_down_is_south(self):
        self.assertEqual(bearing((5, 5), (5, 0)), "north")
        self.assertEqual(bearing((5, 5), (5, 10)), "south")
        self.assertEqual(bearing((5, 5), (10, 5)), "east")
        self.assertEqual(bearing((5, 5), (0, 5)), "west")

    def test_diagonal(self):
        self.assertEqual(bearing((5, 5), (10, 0)), "north-east")
        self.assertEqual(bearing((5, 5), (0, 10)), "south-west")

    def test_deadzone_collapses_near_alignment(self):
        # within +/-1 on an axis -> that axis drops out
        self.assertEqual(bearing((5, 5), (6, 0)), "north")
        self.assertEqual(bearing((5, 5), (5, 3)), "north")   # dy = -2, just past
        self.assertEqual(bearing((5, 5), (5, 6)), "")        # dy = +1, inside
        self.assertEqual(bearing((5, 5), (5, 5)), "")        # on top

    def test_negative_coordinates_are_fine(self):
        self.assertEqual(bearing((0, 0), (-4, 1)), "west")        # dy inside deadzone
        self.assertEqual(bearing((0, 0), (-4, 4)), "south-west")  # dy = 4, past it


class TestHeadingIsHonest(unittest.TestCase):
    def test_empty_claim_is_always_honest(self):
        self.assertTrue(heading_is_honest(_line((0, 0), (0, 9)), ""))

    def test_short_or_degenerate_path_is_honest(self):
        self.assertTrue(heading_is_honest([], "north"))
        self.assertTrue(heading_is_honest([(3, 3)], "north"))
        self.assertTrue(heading_is_honest([(3, 3), (3, 2)], "north"))

    def test_straight_route_matches_claim(self):
        north = _line((5, 9), (5, 0))
        self.assertTrue(heading_is_honest(north, "north"))
        self.assertFalse(heading_is_honest(north, "south"))

    def test_claim_close_enough_when_route_shares_an_axis(self):
        # route goes due north; "north-east" shares 'north', contradicts
        # nothing -> a fair description
        north = _line((5, 9), (5, 0))
        self.assertTrue(heading_is_honest(north, "north-east"))

    def test_v2_failure_detour_against_the_claim(self):
        # claimed north-east, but the route detours WEST for the first
        # several tiles before it can turn - the exact v2 case
        detour = _line((10, 9), (2, 9), (2, 1))
        self.assertFalse(heading_is_honest(detour, "north-east"))
        # the honest heading a caller would substitute:
        end = detour[min(5, len(detour) - 1)]
        self.assertEqual(bearing(detour[0], end), "west")

    def test_claim_reversed_on_one_axis_is_dishonest(self):
        south_first = _line((5, 2), (5, 12))
        self.assertFalse(heading_is_honest(south_first, "north"))

    def test_window_bounds_the_judgement_to_the_early_route(self):
        # first 5 steps go east, then it turns hard north for a long way.
        # claim "east" is honest (early), claim "north" is not (yet).
        dogleg = _line((0, 5), (5, 5), (5, 0))
        self.assertTrue(heading_is_honest(dogleg, "east", window=5))
        self.assertFalse(heading_is_honest(dogleg, "north", window=5))
        # widen the window past the turn and "north" becomes fair too
        self.assertTrue(heading_is_honest(dogleg, "north", window=20))


if __name__ == "__main__":
    unittest.main()
