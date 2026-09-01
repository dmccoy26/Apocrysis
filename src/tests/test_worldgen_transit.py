# §F.12 - a "transit" world (WorldManifest.map_transit) plays as a
# traverse: you wake against one side wall and the way out is carved in
# the opposite wall, roughly level. The Silence does not opt in and its
# generator RNG / golden fixture are untouched (that's the golden test).

import unittest

from src.game import Apocrysis
from src.worlds import get_world


class _IO:
    renders_natively = True
    def say(self, *a, **k): pass
    def ask(self, *a, **k): return ""
    def ask_yes_no(self, *a, **k): return False


class TestTransitLayout(unittest.TestCase):

    def test_the_wake_opts_in_the_silence_does_not(self):
        self.assertTrue(get_world("the_wake").manifest.map_transit)
        self.assertFalse(get_world("silence").manifest.map_transit)

    def test_wake_spawn_and_exit_are_on_opposite_walls_roughly_level(self):
        seen_west = seen_east = False
        for seed in range(1, 40):
            for exp in (0, 6, 12, 17):
                g = Apocrysis("T", seed=seed, io=_IO(), world="the_wake",
                              expeditions_completed=exp)
                if g.mystery is None:            # degenerate map (retry gave up)
                    continue
                sx, sy = g.current_position
                ex, ey = g.mystery.escape_tile
                w, h = g.map_w, g.map_h

                # spawn hard against a side wall
                self.assertIn(sx, (1, w - 2), f"seed {seed}/{exp} spawn x={sx}")
                # exit in the opposite wall
                if sx == 1:
                    seen_west = True
                    self.assertEqual(ex, w - 1, f"seed {seed}/{exp}")
                else:
                    seen_east = True
                    self.assertEqual(ex, 0, f"seed {seed}/{exp}")
                # and close to level - a traverse, not a diagonal
                self.assertLessEqual(abs(ey - sy), h // 4 + 1,
                                     f"seed {seed}/{exp}: dy {abs(ey - sy)}")
        self.assertTrue(seen_west and seen_east, "both start walls should occur")

    def test_wake_never_ships_a_story_less_expedition(self):
        # the degenerate-map retry loop is enabled for a transit world
        # (it is not for a plain v1 world) - 0 failures across a wide sweep.
        misses = [(s, e) for s in range(1, 60) for e in range(0, 18)
                  if Apocrysis("T", seed=s, io=_IO(), world="the_wake",
                               expeditions_completed=e).mystery is None]
        self.assertEqual(misses, [])

    def test_the_silence_spawn_is_not_forced_to_an_edge(self):
        interior = 0
        for seed in range(1, 25):
            g = Apocrysis("S", seed=seed, io=_IO(), expeditions_completed=3)
            sx, sy = g.current_position
            if sx not in (1, g.map_w - 2) and sy not in (1, g.map_h - 2):
                interior += 1
        self.assertGreater(interior, 15)   # overwhelmingly interior, as before


if __name__ == "__main__":
    unittest.main(verbosity=2)
