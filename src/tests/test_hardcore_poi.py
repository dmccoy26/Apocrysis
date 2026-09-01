# Hardcore: a POI marker (`!`) is EARNED BY CONTACT, not handed over by
# advance knowledge. The generator/mystery is untouched - a site is
# exactly as real, discoverable and interactable as in Normal; only its
# map glyph waits until the player has physically stood on the tile.
# The way-out marker (+/! on escape_tile / obstacle_tile) is NOT gated -
# Hardcore still shows the objective, just not the search targets.

import unittest
from unittest.mock import patch

from src.game import Apocrysis


class _IO:
    renders_natively = True
    def __init__(self): self.lines = []
    def say(self, *a, **k): self.lines.append(" ".join(str(x) for x in a))
    def ask(self, *a, **k): return ""
    def ask_yes_no(self, *a, **k): return False


def _mk(hardcore, seed=7, exp=4):
    io = _IO()
    with patch("builtins.print"):
        g = Apocrysis("T", seed=seed, io=io, hardcore=hardcore,
                      expeditions_completed=exp)
    return g, io


def _first_known_site(g):
    """A non-'closed' site the fact-known path would normally mark -
    i.e. one whose owning fact has real evidence we can `discover()`."""
    m = g.mystery
    fact_for_role = {'route': 'F_ROUTE', 'require': 'F_REQUIRE', 'power': 'F_POWER'}
    for role, xy in m.sites.items():
        fact = fact_for_role.get(role)
        if fact is None or xy is None:
            continue
        if any(fact in ev.supports for ev in m.knowledge.evidence.values()):
            return role, xy, fact
    return None, None, None


def _learn_fact(g, fact):
    """Discover one piece of evidence supporting `fact`, the real way -
    facts_known() is derived, not a set you can mutate directly."""
    for eid, ev in g.mystery.knowledge.evidence.items():
        if fact in ev.supports:
            g.mystery.knowledge.discover(eid)
            return
    raise AssertionError(f"no evidence supports {fact}")


class TestHardcorePOIRendering(unittest.TestCase):

    def test_normal_mode_marks_a_site_from_fact_knowledge_alone(self):
        g, _ = _mk(hardcore=False)
        role, xy, fact = _first_known_site(g)
        if role is None:
            self.skipTest("no fact-gated site on this fixture")
        _learn_fact(g, fact)
        mark = g._mystery_site_mark(*xy)
        self.assertIsNotNone(mark, "Normal mode should mark on fact-knowledge alone")

    def test_hardcore_does_not_mark_from_fact_knowledge_alone(self):
        g, _ = _mk(hardcore=True)
        role, xy, fact = _first_known_site(g)
        if role is None:
            self.skipTest("no fact-gated site on this fixture")
        _learn_fact(g, fact)
        mark = g._mystery_site_mark(*xy)
        self.assertIsNone(mark, "Hardcore must not reveal a POI from advance knowledge")

    def test_hardcore_marks_the_site_once_you_stand_on_it(self):
        g, io = _mk(hardcore=True)
        role, xy, fact = _first_known_site(g)
        if role is None:
            self.skipTest("no fact-gated site on this fixture")
        self.assertIsNone(g._mystery_site_mark(*xy))
        g.current_position = xy
        g.mystery_arrive(*xy)                 # physically entering the tile
        self.assertIn(role, getattr(g, "_mystery_named", set()))
        self.assertIsNotNone(g._mystery_site_mark(*xy),
                             "contact must earn the marker")

    def test_hardcore_site_is_still_real_discoverable_and_interactable(self):
        """The generator/mystery is untouched by hardcore - only the
        glyph is gated. Arriving still reveals evidence exactly as
        Normal would."""
        g, io = _mk(hardcore=True)
        role, xy, fact = _first_known_site(g)
        if role is None:
            self.skipTest("no fact-gated site on this fixture")
        before = set(g.mystery.knowledge.facts_known())
        g.current_position = xy
        g.mystery_arrive(*xy)
        after = set(g.mystery.knowledge.facts_known())
        self.assertTrue(len(after) >= len(before),
                        "visiting a hardcore site must still be able to reveal evidence")
        self.assertTrue(any("This is " in ln for ln in io.lines),
                        "the site still names itself on arrival, same as Normal")

    def test_hardcore_never_hides_the_way_out_marker(self):
        g, _ = _mk(hardcore=True)
        m = g.mystery
        if m.escape_tile is None:
            self.skipTest("no escape tile on this fixture")
        m.saw_obstacle = True
        m.obstacle_open = True
        mark = g._mystery_site_mark(*m.obstacle_tile)
        self.assertIsNotNone(mark, "the way-out objective must stay visible in Hardcore")

    def test_hardcore_perceived_grid_hides_poi_too(self):
        """The bot-perception boundary shares the same rendering seam."""
        g, _ = _mk(hardcore=True)
        role, xy, fact = _first_known_site(g)
        if role is None:
            self.skipTest("no fact-gated site on this fixture")
        _learn_fact(g, fact)
        grid = g.perceived_map_grid()["grid"]
        self.assertNotEqual(grid[xy[1]][xy[0]], '!')


if __name__ == "__main__":
    unittest.main(verbosity=2)
