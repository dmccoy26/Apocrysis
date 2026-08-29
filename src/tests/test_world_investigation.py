"""Phase A.3 - World Investigation state, the DAG scheduler, and the
profile round-trip. No UI, no gameplay beyond the resolution hook."""
import os
import tempfile
import unittest

from src.game import Apocrysis
from src.world_investigation import WorldInvestigation, KNOWN, UNKNOWN
from src.worlds.silence.truth import WORLD_FACTS
from src.escape import build_mystery


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


def _fresh_investigation():
    return WorldInvestigation(WORLD_FACTS)


class TestDagScheduler(unittest.TestCase):
    def test_fresh_target_is_a_root_fact(self):
        wi = _fresh_investigation()
        # DIS_FEW_REMAINS is the first authored fact and has no needs
        self.assertEqual(wi.next_target(), "DIS_FEW_REMAINS")

    def test_a_needs_b_ordering(self):
        wi = _fresh_investigation()
        # DEAD_REGIONAL_CRISIS needs DIS_ORGANISED. Neither known yet.
        self.assertEqual(wi.status("DEAD_REGIONAL_CRISIS"), UNKNOWN)
        self.assertEqual(wi.status("DIS_ORGANISED"), UNKNOWN)
        self.assertNotEqual(wi.next_target(), "DEAD_REGIONAL_CRISIS")
        self.assertNotIn("DEAD_REGIONAL_CRISIS", [f.id for f in wi.eligible()])

        # unlock the whole CH1 chain up to DIS_ORGANISED
        for fid in ("DIS_FEW_REMAINS", "DIS_MOVED_TOGETHER",
                    "DIS_ROUTES_PREPARED", "DIS_ORGANISED"):
            wi.mark_known(fid)

        # now the cross-chapter dependency is satisfied
        self.assertIn("DEAD_REGIONAL_CRISIS", [f.id for f in wi.eligible()])

    def test_cross_chapter_unlock_is_specifically_dis_organised(self):
        wi = _fresh_investigation()
        wi.mark_known("DEAD_WERE_LOCALS")
        wi.mark_known("DEAD_STAGES_DIFFER")
        wi.mark_known("DEAD_CONTAINED_FIRST")
        # DEAD_REGIONAL_CRISIS still blocked - it needs a CH1 fact
        self.assertNotIn("DEAD_REGIONAL_CRISIS", [f.id for f in wi.eligible()])
        wi.mark_known("DIS_ORGANISED")
        self.assertIn("DEAD_REGIONAL_CRISIS", [f.id for f in wi.eligible()])

    def test_mark_unknown_id_is_a_noop(self):
        wi = _fresh_investigation()
        wi.mark_known("NOT_A_FACT")  # must not raise
        self.assertEqual(wi.status("NOT_A_FACT"), UNKNOWN)

    def test_thread_progress_moves(self):
        wi = _fresh_investigation()
        d0 = wi.thread_progress()["disappearance"]
        wi.mark_known("DIS_FEW_REMAINS")
        d1 = wi.thread_progress()["disappearance"]
        self.assertEqual(d1[0], d0[0] + 1)
        self.assertEqual(d1[1], d0[1])  # total unchanged

    def test_milestones_known(self):
        wi = _fresh_investigation()
        self.assertEqual(wi.milestones_known(), [])
        wi.mark_known("DIS_ORGANISED")
        self.assertEqual(wi.milestones_known(), ["DIS_ORGANISED"])


class _ProfileTest(unittest.TestCase):
    def setUp(self):
        self._orig = dict(Apocrysis._world_investigation)
        Apocrysis._world_investigation = {}
        self._tmp = tempfile.mkdtemp()
        self._pf = os.path.join(self._tmp, "p.json")

    def tearDown(self):
        Apocrysis._world_investigation = self._orig


class TestProfileRoundTrip(_ProfileTest):
    def test_known_fact_survives_profile_round_trip(self):
        a = Apocrysis("Rt", seed=1, io=_IO())
        a.world_investigation.mark_known("DIS_ORGANISED")
        Apocrysis._world_investigation = a.world_investigation.snapshot()["status"]
        a.save_profile(self._pf)

        Apocrysis._world_investigation = {}  # wipe the class-var
        prof = Apocrysis.load_profile(self._pf)
        b = Apocrysis("Rt", seed=2, io=_IO())
        b.apply_profile(prof)
        self.assertTrue(b.world_investigation.is_known("DIS_ORGANISED"))
        self.assertFalse(b.world_investigation.is_known("DIS_FEW_REMAINS"))

    def test_profile_carries_only_the_status_map(self):
        a = Apocrysis("Rt", seed=1, io=_IO())
        a.world_investigation.mark_known("DIS_FEW_REMAINS")
        Apocrysis._world_investigation = a.world_investigation.snapshot()["status"]
        a.save_profile(self._pf)
        prof = Apocrysis.load_profile(self._pf)
        self.assertEqual(prof["world_investigation"], {"DIS_FEW_REMAINS": KNOWN})


class TestResolutionHook(_ProfileTest):
    def test_solving_a_tagged_mystery_marks_the_fact_known(self):
        g = Apocrysis("Hook", seed=3, io=_IO())
        m = build_mystery(g, target_fact="DIS_ORGANISED")
        g.mystery = m
        g.knowledge = m.knowledge

        # drive it to a solved state
        for eid in list(m.knowledge.evidence):
            m.knowledge.discover(eid)
        m.obstacle_open = True
        g.current_position = m.escape_tile
        g.mystery_try_escape()

        self.assertTrue(m.escaped)
        self.assertTrue(g.world_investigation.is_known("DIS_ORGANISED"))
        self.assertEqual(
            Apocrysis._world_investigation.get("DIS_ORGANISED"), KNOWN)

    def test_solving_an_untagged_mystery_flips_nothing(self):
        g = Apocrysis("Hook2", seed=4, io=_IO())
        m = g.mystery  # the random one from generate_map, world_fact_id is None
        self.assertIsNone(m.world_fact_id)
        for eid in list(m.knowledge.evidence):
            m.knowledge.discover(eid)
        m.obstacle_open = True
        g.current_position = m.escape_tile
        g.mystery_try_escape()
        self.assertEqual(Apocrysis._world_investigation, {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
