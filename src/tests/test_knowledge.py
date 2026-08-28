"""v4 Phase B - the player knowledge model (src/knowledge.py)."""

import unittest

from src.knowledge import (
    Knowledge, Fact, Evidence, Deduction, Hypothesis,
    KNOWN, OBSERVED,
)


def _mystery():
    """A small mystery with the redundancy the design requires:
    F1 <- E1 or E1b; F2 <- E2 or E3; D1 needs F1,F2; H1 suspected on D1,
    confirmed by E_final."""
    k = Knowledge()
    for fid, s in {"F1": "the road is flooded", "F2": "a bypass exists"}.items():
        k.add_fact(Fact(fid, s))
    k.add_evidence(Evidence("E1", "you see the flood", supports=["F1"], method="observe"))
    k.add_evidence(Evidence("E1b", "the water is rising", supports=["F1"], method="search"))
    k.add_evidence(Evidence("E2", "a note mentions the bypass", supports=["F2"], method="search"))
    k.add_evidence(Evidence("E3", "you see the bypass road", supports=["F2"], method="observe"))
    k.add_evidence(Evidence("E_final", "the bypass leads out", supports=["F2"], method="observe"))
    k.add_deduction(Deduction("D1", "the bypass is the way", needs=["F1", "F2"]))
    k.set_hypothesis(Hypothesis("H1", "take the bypass", suspected_when=["D1"], confirmed_by="E_final"))
    return k


class TestKnowledge(unittest.TestCase):

    def test_fact_becomes_known_on_first_supporting_evidence(self):
        k = _mystery()
        self.assertEqual(k.fact_state("F1"), None)
        k.discover("E1")
        self.assertEqual(k.fact_state("F1"), KNOWN)
        self.assertIn("F1", k.facts_known())

    def test_redundant_evidence_any_one_suffices(self):
        k = _mystery()
        k.discover("E1b")  # the 'search' route, not the 'observe' one
        self.assertEqual(k.fact_state("F1"), KNOWN)

    def test_discover_is_idempotent_and_reports_novelty(self):
        k = _mystery()
        self.assertTrue(k.discover("E2"))
        self.assertFalse(k.discover("E2"))
        self.assertFalse(k.discover("nonexistent"))

    def test_observed_fact_then_evidenced(self):
        k = _mystery()
        k.observe_fact("F1")
        self.assertEqual(k.fact_state("F1"), OBSERVED)
        k.discover("E1")
        self.assertEqual(k.fact_state("F1"), KNOWN)  # promoted, no longer just observed

    def test_deduction_available_only_when_all_needs_known(self):
        k = _mystery()
        k.discover("E1")
        self.assertEqual([d.id for d in k.deductions_available()], [])
        k.discover("E2")
        self.assertEqual([d.id for d in k.deductions_available()], ["D1"])

    def test_hypothesis_state_machine_is_automatic(self):
        k = _mystery()
        self.assertEqual(k.hypothesis_state(), "unknown")
        k.discover("E1")
        k.discover("E2")
        self.assertEqual(k.hypothesis_state(), "suspected")
        k.discover("E_final")
        self.assertEqual(k.hypothesis_state(), "confirmed")

    def test_confirmed_needs_the_specific_evidence_not_just_deductions(self):
        k = _mystery()
        k.discover("E1")
        k.discover("E3")  # F2 known via the other route, D1 available
        self.assertEqual(k.hypothesis_state(), "suspected")
        self.assertNotEqual(k.hypothesis_state(), "confirmed")

    def test_add_clue_is_a_standalone_known_fact(self):
        k = Knowledge()
        fid = k.add_clue("the bridge is out", "a sign reads BRIDGE OUT")
        self.assertEqual(k.fact_state(fid), KNOWN)
        self.assertFalse(k.is_empty())

    def test_progress_snapshot_round_trips(self):
        k = _mystery()
        k.discover("E1")
        k.observe_fact("F2")
        snap = k.progress_snapshot()

        k2 = _mystery()
        k2.restore_progress(snap)
        self.assertEqual(k2.facts_known(), {"F1"})
        self.assertEqual(k2.fact_state("F2"), OBSERVED)

    def test_empty_knowledge(self):
        self.assertTrue(Knowledge().is_empty())

    def test_to_dict_from_dict_full_round_trip(self):
        k = _mystery()
        k.discover("E1")
        k.discover("E2")
        k.observe_fact("F2")  # already known, so this is a no-op - fine
        blob = k.to_dict()

        k2 = Knowledge.from_dict(blob)
        self.assertEqual(set(k2.facts), set(k.facts))
        self.assertEqual(set(k2.evidence), set(k.evidence))
        self.assertEqual(k2.facts_known(), k.facts_known())
        self.assertEqual(k2.hypothesis_state(), k.hypothesis_state())
        self.assertEqual([d.id for d in k2.deductions_available()],
                         [d.id for d in k.deductions_available()])

    def test_from_dict_tolerates_none_and_empty(self):
        self.assertTrue(Knowledge.from_dict(None).is_empty())
        self.assertTrue(Knowledge.from_dict({}).is_empty())


if __name__ == "__main__":
    unittest.main()
