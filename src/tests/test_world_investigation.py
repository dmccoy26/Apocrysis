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

    def _solve_targeted(self, seed, fid):
        g = Apocrysis("MB", seed=seed, io=_IO())
        m = build_mystery(g, target_fact=fid)
        g.mystery = m
        g.knowledge = m.knowledge
        for eid in list(m.knowledge.evidence):
            m.knowledge.discover(eid)
        m.obstacle_open = True
        g.current_position = m.escape_tile
        g.io.log.clear()
        g.mystery_try_escape()
        return g

    def test_milestone_fact_fires_the_milestone_banner_once(self):
        g = self._solve_targeted(11, "DIS_ORGANISED")   # DIS_ORGANISED is M1
        out = "\n".join(g.io.log)
        self.assertEqual(out.count("A PIECE FALLS INTO PLACE"), 1)

    def test_non_milestone_fact_fires_no_milestone_banner(self):
        g = self._solve_targeted(12, "DIS_FEW_REMAINS")  # not a milestone
        out = "\n".join(g.io.log)
        self.assertNotIn("A PIECE FALLS INTO PLACE", out)
        self.assertTrue(g.world_investigation.is_known("DIS_FEW_REMAINS"))

    def test_milestone_banner_does_not_refire_when_already_known(self):
        Apocrysis._world_investigation = {"DIS_ORGANISED": KNOWN}
        g = self._solve_targeted(13, "DIS_ORGANISED")
        out = "\n".join(g.io.log)
        self.assertNotIn("A PIECE FALLS INTO PLACE", out)

    def test_solving_an_untagged_mystery_flips_nothing(self):
        # every fact already known -> next_target() is None -> generate_map
        # produces an ordinary (untagged) mystery
        Apocrysis._world_investigation = {f.id: KNOWN for f in WORLD_FACTS}
        g = Apocrysis("Hook2", seed=4, io=_IO())
        Apocrysis._world_investigation = {}  # clear so the assertion below is meaningful
        g.world_investigation.restore({"status": {}})
        m = g.mystery
        self.assertIsNone(m.world_fact_id)
        for eid in list(m.knowledge.evidence):
            m.knowledge.discover(eid)
        m.obstacle_open = True
        g.current_position = m.escape_tile
        g.mystery_try_escape()
        self.assertEqual(Apocrysis._world_investigation, {})


class TestInvestigationScreen(_ProfileTest):
    def test_screen_shows_thread_titles_and_known_statements(self):
        g = Apocrysis("Scr", seed=1, io=_IO())
        g.world_investigation.mark_known("DIS_FEW_REMAINS")
        g.io.log.clear()
        g.world_investigation_screen()
        out = "\n".join(g.io.log)
        self.assertIn("THE SILENCE", out)          # thread title, not "disappearance"
        self.assertIn("THE INFECTED", out)
        self.assertIn("Most people left", out)     # the known fact's statement
        self.assertIn("1/4", out)                  # disappearance progress

    def test_screen_never_leaks_schema_vocabulary(self):
        g = Apocrysis("Scr2", seed=1, io=_IO())
        for f in WORLD_FACTS:
            g.world_investigation.mark_known(f.id)
        g.io.log.clear()
        g.world_investigation_screen()
        out = "\n".join(g.io.log).lower()
        for banned in ("disappearance", "thread", "chapter=", "world_fact",
                       "milestone=", "f_closed"):
            self.assertNotIn(banned, out)

    def test_screen_hides_unknown_fact_statements(self):
        g = Apocrysis("Scr3", seed=1, io=_IO())  # nothing known
        g.io.log.clear()
        g.world_investigation_screen()
        out = "\n".join(g.io.log)
        self.assertNotIn("Most people left", out)   # unknown -> not spoiled
        self.assertIn("more to piece together", out)


class TestInvestigationDrivenTargeting(_ProfileTest):
    def test_expeditions_target_facts_in_dag_order_with_no_repeat_family(self):
        from src.escape import MECHANISMS

        Apocrysis._world_investigation = {}
        targets, families = [], []
        for i in range(6):
            g = Apocrysis("Camp", seed=100 + i, io=_IO())
            m = g.mystery
            self.assertIsNotNone(m.world_fact_id, "expedition should be targeted")
            targets.append(m.world_fact_id)
            fam = MECHANISMS[m.mechanism]["family"]
            families.append(fam)
            # simulate solving it
            g.world_investigation.mark_known(m.world_fact_id)
            Apocrysis._world_investigation = g.world_investigation.snapshot()["status"]
            Apocrysis._last_family = fam

        self.assertEqual(targets[:4], [
            "DIS_FEW_REMAINS", "DIS_MOVED_TOGETHER",
            "DIS_ROUTES_PREPARED", "DIS_ORGANISED",
        ])
        for a, b in zip(families, families[1:]):
            self.assertNotEqual(a, b, f"back-to-back story family: {families}")

    def test_targeting_stops_when_the_dag_is_exhausted(self):
        Apocrysis._world_investigation = {f.id: KNOWN for f in WORLD_FACTS}
        g = Apocrysis("Done", seed=7, io=_IO())
        self.assertIsNone(g.mystery.world_fact_id)


if __name__ == "__main__":
    unittest.main(verbosity=2)
