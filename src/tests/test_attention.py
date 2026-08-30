"""The Apocrysis attention language (docs/ATTENTION_SYSTEM_SPEC.md).

announce_event maps a semantic class (or an old alias) to a glyph +
colour + loudness. Presentation only - no balance.
"""
import re
import unittest

from src.game import Apocrysis
from src.constants import RED, ORANGE, BLUE, MAGENTA, YELLOW, GREEN, CYAN

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


class _CapIO:
    renders_natively = True

    def __init__(self):
        self.lines = []

    def say(self, *a, **k):
        self.lines.append(" ".join(str(x) for x in a))

    def ask(self, prompt=""):
        return ""

    def ask_yes_no(self, prompt):
        return True


def _game():
    g = Apocrysis("Att", seed=1, io=_CapIO())
    g.io.lines.clear()
    return g


class TestAttentionClasses(unittest.TestCase):
    def _emit(self, kind):
        g = _game()
        g.announce_event("a thing", "detail", kind=kind)
        return g.io.lines[-1]

    def test_each_class_has_its_colour_and_glyph(self):
        want = {
            "danger":    (RED, "‼"),
            "warning":   (ORANGE, "⚠"),
            "objective": (BLUE, "◆"),
            "discovery": (YELLOW, "✦"),
            "story":     (MAGENTA, "◈"),
            "success":   (GREEN, "✓"),
            "info":      (CYAN, "•"),
        }
        for cls, (colour, glyph) in want.items():
            out = self._emit(cls)
            self.assertIn(colour, out, f"{cls} missing its colour")
            self.assertIn(glyph, _ANSI.sub("", out), f"{cls} missing its glyph")

    def test_only_danger_and_story_are_banners(self):
        for cls in ("danger", "story"):
            self.assertIn("═", self._emit(cls), f"{cls} should be a banner")
        for cls in ("warning", "objective", "discovery", "success", "info"):
            self.assertNotIn("═", self._emit(cls), f"{cls} should be a line")

    def test_old_aliases_still_resolve_with_their_labels(self):
        cases = {
            "warn": ("⚠", ORANGE),
            "solved": ("MYSTERY SOLVED", GREEN),
            "milestone": ("A PIECE FALLS INTO PLACE", MAGENTA),
            "correction": ("YOU HAD IT WRONG", MAGENTA),
            "lead": ("NEW LEAD", YELLOW),
            "objective": ("OBJECTIVE UPDATED", BLUE),
        }
        for alias, (needle, colour) in cases.items():
            out = self._emit(alias)
            self.assertIn(needle, _ANSI.sub("", out))
            self.assertIn(colour, out)

    def test_reserve_red_ordinary_hunger_is_orange_not_red(self):
        g = _game()
        g.hunger = 25          # tier 1 - "getting hungry"
        g.backpack.food = 5
        g._supply_warnings()
        joined = "\n".join(g.io.lines)
        self.assertIn("getting hungry".upper(), joined.upper())
        hungry_line = next(l for l in g.io.lines if "HUNGRY" in l.upper())
        self.assertIn(ORANGE, hungry_line)
        self.assertNotIn(RED, hungry_line)

    def test_active_starvation_is_danger_red(self):
        g = _game()
        g.hunger = 0           # tier 3 - attrition is live
        g.backpack.food = 5
        g._supply_warnings()
        line = next(l for l in g.io.lines if "HUNGRY" in l.upper())
        self.assertIn(RED, line)


class TestCombatFlare(unittest.TestCase):
    def test_zombie_encounter_emits_a_danger_flare(self):
        from src.zombies import FreshZombie
        g = _game()
        g.encounter_zombie(FreshZombie())
        feed = "\n".join(g.io.lines)
        self.assertIn("ZOMBIE", feed.upper())
        flare = next(l for l in g.io.lines if "ZOMBIE —" in l or "ZOMBIE -" in l)
        self.assertIn(RED, flare)
        self.assertIn("═", flare)


if __name__ == "__main__":
    unittest.main()
