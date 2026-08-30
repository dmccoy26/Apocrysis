"""Phase E.1 - the competing regional hypothesis ladder.

The survivor's working theory is DERIVED from milestone-known state;
each rung breaks on one specific milestone; the correction beat fires
once per rung, in order, campaign-wide.
"""
import unittest

from src.world_investigation import WorldInvestigation
from src.worlds.silence.truth import WORLD_FACTS
from src.worlds.silence.hypotheses import REGIONAL_HYPOTHESES


def _wi():
    return WorldInvestigation(WORLD_FACTS, REGIONAL_HYPOTHESES)


class TestLadderData(unittest.TestCase):
    def test_every_rung_breaks_on_a_real_milestone(self):
        ids = {f.id for f in WORLD_FACTS if f.milestone}
        for h in REGIONAL_HYPOTHESES:
            self.assertIn(h.held_until, ids, f"{h.id} breaks on non-milestone {h.held_until}")

    def test_rungs_break_in_dag_order(self):
        # each rung's disproving milestone must come no earlier in the
        # authored order than the previous rung's - the ladder can't
        # collapse out of sequence.
        order = [f.id for f in WORLD_FACTS]
        pos = [order.index(h.held_until) for h in REGIONAL_HYPOTHESES]
        self.assertEqual(pos, sorted(pos))

    def test_frozen(self):
        import dataclasses
        with self.assertRaises(dataclasses.FrozenInstanceError):
            REGIONAL_HYPOTHESES[0].id = "x"


class TestCurrentHypothesis(unittest.TestCase):
    def test_starts_on_the_first_rung(self):
        self.assertEqual(_wi().current_hypothesis().id, "RH_KILLED")

    def test_each_milestone_advances_exactly_one_rung(self):
        wi = _wi()
        wi.mark_known("DIS_ORGANISED")            # breaks rung 1
        self.assertEqual(wi.current_hypothesis().id, "RH_EVACUATED")
        wi.mark_known("RESP_SEAL_SCHEDULED")      # breaks rung 2
        self.assertEqual(wi.current_hypothesis().id, "RH_RESCUE_RAN_OUT")
        wi.mark_known("RESP_ONE_COMMAND")         # breaks rung 3
        self.assertEqual(wi.current_hypothesis().id, "RH_BETRAYED_AT_END")
        wi.mark_known("RESP_THE_ORDER")           # breaks rung 4 - the truth
        self.assertIsNone(wi.current_hypothesis())

    def test_unrelated_milestone_does_not_advance(self):
        wi = _wi()
        wi.mark_known("DEAD_REGIONAL_CRISIS")     # a milestone, but no rung's held_until
        self.assertEqual(wi.current_hypothesis().id, "RH_KILLED")

    def test_broken_by_maps_fact_to_its_rung(self):
        wi = _wi()
        self.assertEqual(wi.hypothesis_broken_by("RESP_ONE_COMMAND").id, "RH_RESCUE_RAN_OUT")
        self.assertIsNone(wi.hypothesis_broken_by("DIS_FEW_REMAINS"))

    def test_survives_snapshot_restore(self):
        wi = _wi()
        wi.mark_known("DIS_ORGANISED")
        wi.mark_known("RESP_SEAL_SCHEDULED")
        snap = wi.snapshot()
        fresh = _wi()
        fresh.restore(snap)
        self.assertEqual(fresh.current_hypothesis().id, "RH_RESCUE_RAN_OUT")


class TestCorrectionBeat(unittest.TestCase):
    def test_solving_a_rung_breaker_fires_one_correction_banner(self):
        from src.game import Apocrysis

        class _IO:
            renders_natively = True
            def __init__(self): self.log = []
            def say(self, *a, **k): self.log.append(" ".join(str(x) for x in a))
            def ask(self, p=""): return ""
            def ask_yes_no(self, p): return False

        Apocrysis._world_investigation = {}
        # target DIS_ORGANISED (rung 1's breaker) and solve it
        g = Apocrysis("Ladder", seed=7, io=_IO())
        # walk the DAG to DIS_ORGANISED
        for fid in ("DIS_FEW_REMAINS", "DIS_MOVED_TOGETHER", "DIS_ROUTES_PREPARED"):
            g.world_investigation.mark_known(fid)
        Apocrysis._world_investigation = g.world_investigation.snapshot()["status"]
        g = Apocrysis("Ladder", seed=7, io=_IO())
        self.assertEqual(g.mystery.world_fact_id, "DIS_ORGANISED")
        m = g.mystery
        for ev in list(m.knowledge.evidence):
            m.knowledge.discover(ev)
        for fid in list(m.knowledge.facts):
            m.knowledge.observe_fact(fid)
        m.obstacle_open = True
        g.current_position = m.escape_tile
        g.io.log.clear()
        g.mystery_try_escape()
        banner = "\n".join(g.io.log)
        self.assertIn("YOU HAD IT WRONG", banner)
        self.assertEqual(banner.count("YOU HAD IT WRONG"), 1)
        Apocrysis._world_investigation = {}


if __name__ == "__main__":
    unittest.main()
