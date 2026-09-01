"""H1 - the tactical helmet (WAKE_DEVICE_PASS.md).

Before the helmet The Wake plays contact-only (like Hardcore): bearing +
distance + physical landmarks, no advance `!`. After: learned leads mark
`!` again, and detected-but-unidentified sites show `?`. The Silence
never gates anything on the device.
"""
import unittest

from src.game import Apocrysis
from src.worlds import get_world

WAKE = get_world("the_wake")
SILENCE = get_world("silence")


class _IO:
    renders_natively = True

    def __init__(self):
        self.log = []

    def say(self, *a, **k):
        self.log.append(" ".join(str(x) for x in a))

    def ask(self, prompt=""):
        return ""

    def ask_yes_no(self, prompt):
        return False


def _wake(exp, seed=5, scanner=False):
    Apocrysis.reset_campaign_state()
    g = Apocrysis("D", seed=seed, io=_IO(), world="the_wake",
                  expeditions_completed=exp)
    if scanner:
        g.has_scanner = True
    return g


class TestTheGate(unittest.TestCase):
    def tearDown(self):
        Apocrysis.reset_campaign_state()

    def test_wake_gates_markers_silence_does_not(self):
        self.assertTrue(WAKE.manifest.markers_need_device)
        self.assertFalse(SILENCE.manifest.markers_need_device)

    def test_pre_helmet_a_wake_fact_level_is_contact_only(self):
        g = _wake(8)                     # L9, a mystery/fact level
        self.assertIsNotNone(g.mystery)
        self.assertTrue(g._markers_gated())
        # no advance marker for any site
        for xy in g.mystery.sites.values():
            if xy:
                self.assertNotIn("!", g._mystery_site_mark(*xy) or "")

    def test_helmet_lifts_the_gate(self):
        g = _wake(8, scanner=True)
        self.assertFalse(g._markers_gated())

    def test_silence_is_never_gated(self):
        Apocrysis.reset_campaign_state()
        g = Apocrysis("S", seed=3, io=_IO())
        self.assertFalse(g._world_gates_markers())
        self.assertFalse(g._markers_gated())
        Apocrysis.reset_campaign_state()


class TestRecovery(unittest.TestCase):
    def tearDown(self):
        Apocrysis.reset_campaign_state()

    def _l5(self):
        # find the first discovery level
        exp = next(i for i, t in enumerate(WAKE.manifest.level_types)
                   if t == "discovery")
        return _wake(exp, seed=5)

    def test_l5_discovery_crossing_places_the_helmet(self):
        g = self._l5()
        self.assertIsNone(g.mystery)
        self.assertIsNotNone(g.section_exit)
        self.assertIsNotNone(g._discovery_pickup)
        self.assertEqual(g._discovery_pickup[1], "scanner")
        from src.worldgen.reachable import shortest_path
        path = shortest_path(g.map, g.map_size, g.current_position, g.section_exit)
        self.assertIn(g._discovery_pickup[0], path)

    def test_cannot_leave_the_section_without_the_helmet(self):
        g = self._l5()
        g.current_position = g.section_exit
        g.io.log.clear()
        g.move_and_search("z")
        self.assertFalse(getattr(g, "won", False))
        self.assertIn("back for first", " ".join(g.io.log).lower())

    def test_pickup_then_completion_grants_the_helmet_and_the_online_beat(self):
        g = self._l5()
        self.assertFalse(g.has_scanner)
        # step onto the pickup: taken, but not granted yet
        g.current_position = g._discovery_pickup[0]
        g.io.log.clear()
        g.move_and_search("z")
        self.assertTrue(g._discovery_pickup_taken)
        self.assertFalse(g.has_scanner, "helmet lands on completion, not touch")
        self.assertIn("take it", " ".join(g.io.log).lower())
        # complete the crossing: helmet + TACTICAL SYSTEM ONLINE
        g.current_position = g.section_exit
        g.io.log.clear()
        g.move_and_search("z")
        self.assertTrue(g.has_scanner)
        self.assertTrue(getattr(g, "won", False))
        self.assertIn("TACTICAL SYSTEM ONLINE", " ".join(g.io.log))

    def test_later_discovery_crossings_are_plain_once_the_helmet_is_held(self):
        # L21 (exp 20) is also a discovery - but with the helmet already
        # held it carries no pickup, it's a plain crossing.
        exps = [i for i, t in enumerate(WAKE.manifest.level_types)
                if t == "discovery"]
        self.assertGreaterEqual(len(exps), 2)
        g = _wake(exps[1], seed=9, scanner=True)
        self.assertIsNone(g._discovery_pickup)
        self.assertIsNotNone(g.section_exit)

    def test_has_scanner_round_trips_through_save_load(self):
        import tempfile, os
        g = _wake(8, scanner=True)
        with tempfile.TemporaryDirectory() as d:
            pf = os.path.join(d, "s.json")
            g.save_game(pf)
            g2 = Apocrysis.load_game(pf)
        self.assertTrue(g2.has_scanner)


class TestDetection(unittest.TestCase):
    def tearDown(self):
        Apocrysis.reset_campaign_state()

    def test_scanner_observes_an_in_sight_unknown_site_as_question_mark(self):
        g = _wake(8, seed=5, scanner=True)
        m = g.mystery
        # pick a site whose fact isn't known and move next to it
        role, xy = next((r, p) for r, p in m.sites.items()
                        if p and r in ("route", "require", "power"))
        fid = g._SITE_ROLE_FACT[role]
        # ensure not already known
        if fid in m.knowledge.facts_known():
            self.skipTest("fact already known for this seed")
        g.current_position = (xy[0], xy[1])
        g._scanner_detect()
        self.assertEqual(m.knowledge.fact_state(fid), "Observed")
        self.assertIn("?", g._mystery_site_mark(*xy) or "")

    def test_no_detection_without_the_helmet(self):
        g = _wake(8, seed=5, scanner=False)
        m = g.mystery
        role, xy = next((r, p) for r, p in m.sites.items()
                        if p and r in ("route", "require", "power"))
        g.current_position = (xy[0], xy[1])
        g._scanner_detect()
        fid = g._SITE_ROLE_FACT[role]
        self.assertNotEqual(m.knowledge.fact_state(fid), "Observed")


if __name__ == "__main__":
    unittest.main()
