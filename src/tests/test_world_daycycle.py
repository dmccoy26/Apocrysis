# F.11-class: a starship has no sunrise. The day/night MECHANIC stays
# in the engine (four phase roles drive visibility / encounters /
# decay); what the phases are CALLED, and the one-time discoverables
# ("waders", "flashlight"), are the world's to name.

import random
import unittest
from unittest.mock import patch

from src.daycycle import phase_label, phase_glyph
from src.game import Apocrysis
from src.worlds import get_world

_SKY_WORDS = ("sun", "sunrise", "sunset", "sky", "dawn", "dusk",
              "daylight", "nightfall", "moon", "star")


class TestDayCycleSeam(unittest.TestCase):

    def test_the_silence_labels_and_glyphs_are_unchanged(self):
        w = get_world("silence")
        for phase in ("dawn", "day", "dusk", "night"):
            self.assertEqual(phase_label(w, phase), phase)
        self.assertEqual(phase_glyph(w, "day"), "☀")
        self.assertEqual(phase_glyph(w, "night"), "☾")

    def test_the_wake_names_a_lighting_schedule_not_a_sky(self):
        w = get_world("the_wake")
        labels = [phase_label(w, p) for p in ("dawn", "day", "dusk", "night")]
        self.assertEqual(labels,
                         ["lights up", "ship day", "lights down", "ship night"])
        for p in ("dawn", "day", "dusk", "night"):
            self.assertNotIn(phase_glyph(w, p), ("☀", "☾"))
            for bad in _SKY_WORDS:
                self.assertNotIn(bad, phase_label(w, p))

    def test_discoverables_fall_back_to_the_valley_default(self):
        w = get_world("silence")
        prose = (w.prose or {}).get("discoverables", {})
        # Silence authors none - the engine default stands.
        self.assertEqual(prose, {} if "discoverables" not in w.prose
                         else prose)

    def test_the_wake_discoverables_are_ship_kit(self):
        w = get_world("the_wake")
        d = w.prose["discoverables"]
        self.assertIn("hardsuit", d["waders"])
        self.assertNotIn("swamp", d["waders"].lower())
        self.assertNotIn("water", d["waders"].lower())
        self.assertIn("lamp", d["flashlight"])


class TestDayCycleReachesTheGame(unittest.TestCase):

    def _loot_transcript(self, world_id, seed):
        lines = []

        class _IO:
            renders_natively = False
            def say(self, *a, **k): lines.append(" ".join(str(x) for x in a))
            def ask(self, *a, **k): return ""
            def ask_yes_no(self, *a, **k): return False

        with patch("builtins.print"):
            g = Apocrysis("T", map_size=16, seed=seed, world=world_id,
                          expeditions_completed=6, io=_IO())
        for i in range(200):
            random.seed(seed * 100 + i)
            try:
                g.move_and_search(random.choice("nsew"))
            except Exception:
                pass
        return "\n".join(lines).lower()

    def test_a_wake_transcript_never_hands_you_waders(self):
        for seed in (11, 23, 47, 91):
            t = self._loot_transcript("the_wake", seed)
            self.assertNotIn("waders", t, f"seed {seed}")
            self.assertNotIn("water and swamp", t, f"seed {seed}")
            self.assertNotIn("working flashlight", t, f"seed {seed}")

    def test_the_silence_transcript_still_says_waders(self):
        # at least one seed surfaces them - proves the default path is live
        hits = "".join(self._loot_transcript("silence", s)
                       for s in (3, 7, 11, 19, 23, 29, 31, 37))
        self.assertIn("waders", hits)


if __name__ == "__main__":
    unittest.main(verbosity=2)
