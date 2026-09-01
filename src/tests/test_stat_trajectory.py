# The v1-4 "player class" abstraction was removed in v5 (worlds do not
# select classes; the player is given a survivor). The stat progression
# it happened to implement - flat per-level growth + a tier bonus at
# levels 5/10/15/20 - is preserved EXACTLY, as plain data in
# src/player.py.
#
# This pins the full level 1-20 trajectory. The golden below was
# captured from the class-based implementation immediately before it
# was deleted; the assertion proves the refactor changed nothing about
# any level, not just the four obvious thresholds.

import unittest
from unittest.mock import patch

from src.game import Apocrysis


class _IO:
    renders_natively = True
    def say(self, *a, **k): pass
    def ask(self, *a, **k): return ""
    def ask_yes_no(self, *a, **k): return False


# (level, health, max_health, strength, dexterity, intelligence, wisdom)
_GOLDEN = [
    (1, 100, 100, 12, 10, 10, 10),
    (2, 100, 105, 13, 11, 11, 11),
    (3, 100, 110, 14, 12, 12, 12),
    (4, 100, 115, 15, 13, 13, 13),
    (5, 100, 120, 16, 17, 18, 15),
    (6, 100, 125, 17, 18, 19, 16),
    (7, 100, 130, 18, 19, 20, 17),
    (8, 100, 135, 19, 20, 21, 18),
    (9, 100, 140, 20, 21, 22, 19),
    (10, 100, 145, 21, 22, 23, 22),
    (11, 100, 150, 22, 23, 24, 23),
    (12, 100, 155, 23, 24, 25, 24),
    (13, 100, 160, 24, 25, 26, 25),
    (14, 100, 165, 25, 26, 27, 26),
    (15, 100, 180, 30, 28, 28, 27),
    (16, 100, 185, 31, 29, 29, 28),
    (17, 100, 190, 32, 30, 30, 29),
    (18, 100, 195, 33, 31, 31, 30),
    (19, 100, 200, 34, 32, 32, 31),
    (20, 100, 215, 37, 38, 37, 34),
]


class TestStatTrajectory(unittest.TestCase):

    def _trajectory(self):
        with patch("builtins.print"):
            g = Apocrysis("T", seed=1, io=_IO())
        rows = [(g.level, g.health, g.max_health, g.strength,
                 g.dexterity, g.intelligence, g.wisdom)]
        with patch("builtins.print"):
            for _ in range(19):
                g.level_up()
                rows.append((g.level, g.health, g.max_health, g.strength,
                             g.dexterity, g.intelligence, g.wisdom))
        return rows

    def test_level_1_to_20_matches_the_pre_removal_golden(self):
        self.assertEqual(self._trajectory(), _GOLDEN)

    def test_no_player_class_attribute_or_saved_field(self):
        import json, os, tempfile
        with patch("builtins.print"):
            g = Apocrysis("T", seed=1, io=_IO())
        self.assertFalse(hasattr(g, "player_class"))
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        try:
            g.save_profile(path)
            raw = json.load(open(path))
            self.assertNotIn("player_class", raw.get("survivor", {}))
            self.assertNotIn("player_class", raw.get("campaign", {}))
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
