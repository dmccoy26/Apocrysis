# §F.11 - the fiction of MOVING through a world is world-owned.
#
# "You push through deep forest" is a claim about the physical world.
# If The Wake can say it, the generator doesn't believe the world it's
# generating. Engine keeps the mechanics (keyed to terrain role); a
# world supplies the sentences.

import inspect
import unittest
from unittest.mock import patch

from src.terrain_prose import tp, GENERIC
from src.game import Apocrysis
from src.worlds import get_world
from src.worlds.base import World

_VALLEY_WORDS = ("forest", "valley", "ridge", "river", "mountain", "wade",
                 "the bank", "current", "swim", "woods", "trail")
_SHIP_WORDS = ("hull", "deck", "compartment", "breach", "vacuum",
               "hatch", "airlock", "corridor")


class TestTerrainProseSeam(unittest.TestCase):

    def test_the_silence_lines_are_unchanged(self):
        w = get_world("silence")
        self.assertEqual(tp(w, "enter", "dense"),
                         "You move through dense forest.")
        self.assertEqual(tp(w, "enter", "slow"),
                         "You wade through water. Movement is difficult.")
        self.assertEqual(tp(w, "barrier", "interior"),
                         "You can't cross the mountain here.")
        self.assertEqual(tp(w, "label", "forest"), "FOREST")
        self.assertEqual(tp(w, "hud_slow", "swamp"), "slow, tiring ground")

    def test_the_wake_makes_ship_claims_not_valley_claims(self):
        w = get_world("the_wake")
        for group, key in (("enter", "dense"), ("enter", "slow"),
                           ("enter", "shelter"), ("reenter", "shelter"),
                           ("hazard", "slow"), ("barrier", "edge_first"),
                           ("barrier", "interior"), ("crossing", "blocked"),
                           ("crossing", "ok"), ("crossing", "fail"),
                           ("spot", "shelter"), ("spot", "settlement")):
            line = tp(w, group, key).lower()
            for bad in _VALLEY_WORDS:
                self.assertNotIn(bad, line, f"{group}/{key}: {line!r}")
        # and it actually reads as a ship
        blob = " ".join(
            tp(w, g, k).lower()
            for g in ("enter", "reenter", "barrier", "spot", "label")
            for k in ("dense", "slow", "shelter", "edge_first", "interior",
                      "settlement", "forest", "mountain"))
        self.assertTrue(any(s in blob for s in _SHIP_WORDS), blob)

    def test_the_generic_fallback_is_world_neutral(self):
        bare = World(id="bare", name="Bare", description="",
                     terrain_symbols={}, terrain_legend="", map_archetypes={})
        for group, sub in GENERIC.items():
            if not isinstance(sub, dict):
                continue
            for key, line in sub.items():
                low = str(line).lower()
                for bad in _VALLEY_WORDS + _SHIP_WORDS:
                    self.assertNotIn(bad, low,
                                     f"GENERIC {group}/{key} claims {bad!r}")
                # tp() returns it when a world authors nothing
                self.assertEqual(tp(bare, group, key), line)

    def test_no_engine_module_hard_codes_the_environment(self):
        import src.mixins.world_mixin as wm
        import src.mixins.mystery_mixin as mm
        import src.mixins.ui_mixin as um
        for mod in (wm, mm, um):
            src = inspect.getsource(mod)
            for phrase in ("dense forest", "wade through water",
                           "the far bank", "cross the mountain here",
                           "cross the river here", "Rooftops in the distance",
                           "off the ridge", "leave the valley"):
                self.assertNotIn(phrase, src,
                                 f"{mod.__name__} hard-codes {phrase!r}")


class TestTerrainProseReachesTheGame(unittest.TestCase):

    def _move_transcript(self, world_id, seed):
        lines = []

        class _IO:
            renders_natively = False
            def say(self, *a, **k): lines.append(" ".join(str(x) for x in a))
            def ask(self, *a, **k): return ""
            def ask_yes_no(self, *a, **k): return False

        with patch("builtins.print"):
            g = Apocrysis("T", map_size=16, seed=seed, world=world_id,
                          expeditions_completed=6, io=_IO())
        import random
        for i in range(150):
            random.seed(seed * 100 + i)
            try:
                g.move_and_search(random.choice("nsew"))
            except Exception:
                pass
        return "\n".join(lines).lower()

    def test_a_wake_move_transcript_has_no_valley_environment(self):
        for seed in (11, 23, 47):
            t = self._move_transcript("the_wake", seed)
            for bad in ("dense forest", "wade through water", "the far bank",
                        "cross the mountain here", "cross the river",
                        "rooftops in the distance", "standing alone in the "
                        "distance", "the current takes you"):
                self.assertNotIn(bad, t, f"seed {seed}: {bad!r} on a spaceship")

    def test_the_silence_help_and_wake_help_use_their_own_leave_verb(self):
        with patch("builtins.print") as p1:
            get_world  # noqa
            Apocrysis("S", map_size=12, seed=1, world="silence").print_help()
        s = "\n".join(str(c.args[0]) for c in p1.call_args_list if c.args)
        self.assertIn("leave the valley", s)
        with patch("builtins.print") as p2:
            Apocrysis("W", map_size=12, seed=1, world="the_wake").print_help()
        w = "\n".join(str(c.args[0]) for c in p2.call_args_list if c.args)
        self.assertIn("get off the ship", w)
        self.assertNotIn("valley", w)


if __name__ == "__main__":
    unittest.main(verbosity=2)
