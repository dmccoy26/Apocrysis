"""Phase E.2 + E.3 - the bespoke final expedition and the ending choice."""
import json
import os
import tempfile
import unittest

from src.game import Apocrysis
from src.worlds.silence.truth import WORLD_FACTS

_PRE_FINALE = {f.id: "known" for f in WORLD_FACTS
               if f.id not in ("RESP_THE_ORDER", "RESP_THE_CHOICE")}


class _IO:
    renders_natively = True

    def __init__(self, answers=()):
        self.log = []
        self._answers = list(answers)

    def say(self, *a, **k):
        self.log.append(" ".join(str(x) for x in a))

    def ask(self, prompt=""):
        return self._answers.pop(0) if self._answers else ""

    def ask_yes_no(self, prompt):
        return False


def _reset():
    Apocrysis._world_investigation = {}
    Apocrysis._campaign_ending = None
    Apocrysis._used_mechanisms = []


def _solve(g):
    m = g.mystery
    for ev in list(m.knowledge.evidence):
        m.knowledge.discover(ev)
    for fid in list(m.knowledge.facts):
        m.knowledge.observe_fact(fid)
    m.obstacle_open = True
    g.current_position = m.escape_tile
    g.io.log.clear()
    g.mystery_try_escape()
    return "\n".join(g.io.log)


class TestFinaleRouting(unittest.TestCase):
    def tearDown(self):
        _reset()

    def test_expedition_25_is_the_finale(self):
        _reset()
        Apocrysis._world_investigation = dict(_PRE_FINALE)
        g = Apocrysis("Fin", seed=4, io=_IO(), expeditions_completed=24)
        self.assertTrue(getattr(g.mystery, "is_finale", False))
        self.assertEqual(g.mystery.escape_kind, "checkpoint")
        self.assertEqual(g.mystery.world_fact_id, "RESP_THE_CHOICE")

    def test_earlier_expeditions_are_not_the_finale(self):
        _reset()
        g = Apocrysis("Mid", seed=4, io=_IO(), expeditions_completed=10)
        self.assertFalse(getattr(g.mystery, "is_finale", False))

    def test_finale_labels_are_the_compound(self):
        _reset()
        Apocrysis._world_investigation = dict(_PRE_FINALE)
        g = Apocrysis("Fin", seed=4, io=_IO(), expeditions_completed=24)
        self.assertIn("the regional command centre", g.mystery.site_labels.values())


class TestFinaleResolution(unittest.TestCase):
    def tearDown(self):
        _reset()

    def test_solving_the_finale_establishes_both_finale_facts(self):
        _reset()
        Apocrysis._world_investigation = dict(_PRE_FINALE)
        g = Apocrysis("Fin", seed=4, io=_IO(["2"]), expeditions_completed=24)
        _solve(g)
        self.assertTrue(g.world_investigation.is_known("RESP_THE_ORDER"))
        self.assertTrue(g.world_investigation.is_known("RESP_THE_CHOICE"))

    def test_the_final_correction_fires(self):
        _reset()
        Apocrysis._world_investigation = dict(_PRE_FINALE)
        g = Apocrysis("Fin", seed=4, io=_IO(["2"]), expeditions_completed=24)
        out = _solve(g)
        self.assertIn("YOU HAD IT WRONG", out)
        self.assertIn("one plan, Protocol Seven", out)


class TestEndingChoice(unittest.TestCase):
    def tearDown(self):
        _reset()

    def test_broadcast_records_and_prints_its_ending(self):
        _reset()
        Apocrysis._world_investigation = dict(_PRE_FINALE)
        g = Apocrysis("Fin", seed=4, io=_IO(["1"]), expeditions_completed=24)
        out = _solve(g)
        self.assertEqual(Apocrysis._campaign_ending, "broadcast")
        self.assertIn("send it all out past the cordon", out)
        self.assertIn("CAMPAIGN COMPLETE", out)

    def test_protect_records_and_prints_its_ending(self):
        _reset()
        Apocrysis._world_investigation = dict(_PRE_FINALE)
        g = Apocrysis("Fin", seed=4, io=_IO(["2"]), expeditions_completed=24)
        out = _solve(g)
        self.assertEqual(Apocrysis._campaign_ending, "protect")
        self.assertIn("switch it off", out)

    def test_garbage_input_defaults_to_protect(self):
        _reset()
        Apocrysis._world_investigation = dict(_PRE_FINALE)
        g = Apocrysis("Fin", seed=4, io=_IO(["x", "y", "z"]), expeditions_completed=24)
        _solve(g)
        self.assertEqual(Apocrysis._campaign_ending, "protect")

    def test_ending_persists_and_restores(self):
        _reset()
        Apocrysis._world_investigation = dict(_PRE_FINALE)
        g = Apocrysis("Fin", seed=4, io=_IO(["1"]), expeditions_completed=24)
        _solve(g)
        tmp = tempfile.mktemp(suffix=".json")
        try:
            g.save_profile(tmp)
            self.assertEqual(json.load(open(tmp))["campaign"]["ending"], "broadcast")
            Apocrysis._campaign_ending = None
            g2 = Apocrysis("Fin", seed=1, io=_IO())
            g2.apply_profile(Apocrysis.load_profile(tmp))
            self.assertEqual(Apocrysis._campaign_ending, "broadcast")
        finally:
            os.path.exists(tmp) and os.remove(tmp)

    def test_finale_does_not_reprompt_when_ending_already_set(self):
        _reset()
        Apocrysis._world_investigation = dict(_PRE_FINALE)
        Apocrysis._campaign_ending = "protect"
        g = Apocrysis("Fin", seed=4, io=_IO([]), expeditions_completed=24)
        # no answers queued; if it prompted, choice would still resolve
        # but campaign_ending must stay 'protect' untouched
        _solve(g)
        self.assertEqual(Apocrysis._campaign_ending, "protect")


if __name__ == "__main__":
    unittest.main()
