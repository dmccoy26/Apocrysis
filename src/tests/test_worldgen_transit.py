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
        # Every expedition is either an escape-mystery level OR a
        # scheduled section crossing (WAKE_SPINE §5) with a carved exit -
        # never a degenerate "nothing here" map. The retry loop (enabled
        # for a transit world) backs both. 0 failures across a wide sweep.
        from src.sections import crosses_section
        WAKE = get_world("the_wake")
        misses = []
        for s in range(1, 60):
            for e in range(0, 18):
                g = Apocrysis("T", seed=s, io=_IO(), world="the_wake",
                              expeditions_completed=e)
                if g.mystery is not None:
                    continue
                if crosses_section(e, WAKE) and g.section_exit is not None:
                    continue
                misses.append((s, e))
        self.assertEqual(misses, [])

    def test_wake_settlement_block_is_a_ship_enclave_not_a_valley_town(self):
        # H1 read: the T/H/R/S/B town glyphs were The Silence's valley
        # vocabulary rendered unchanged on a ship deck. The Wake owns
        # its own block letters (Muster/Hab/Run/Store/Bay) - no 'T'.
        WAKE = get_world("the_wake")
        self.assertEqual(WAKE.terrain.settlement_glyphs[0], 'M')
        seen = set()
        for seed in range(1, 20):
            g = Apocrysis("W", seed=seed, io=_IO(), world="the_wake",
                          expeditions_completed=2)
            seen |= {t['content'] for row in g.map for t in row
                     if isinstance(t, dict) and t.get('terrain') == 'town'}
        self.assertTrue(seen)
        self.assertNotIn('T', seen)
        self.assertLessEqual(seen, set('MHRSB'))

    def test_the_silence_settlement_block_is_unchanged(self):
        seen = set()
        for seed in range(1, 20):
            g = Apocrysis("S", seed=seed, io=_IO(), expeditions_completed=3)
            seen |= {t['content'] for row in g.map for t in row
                     if isinstance(t, dict) and t.get('terrain') == 'town'}
        self.assertLessEqual(seen, set('THRSB'))
        self.assertIn('T', seen)

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
