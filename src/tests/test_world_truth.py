"""Phase A.1 - integrity of the authored WorldFact DAG. Content tests
only; no runtime behaviour (the DAG isn't wired to anything yet)."""
import dataclasses
import unittest

from src.worlds.silence.truth import (
    WORLD_FACTS, THREADS, MILESTONE_IDS,
)

_BY_ID = {f.id: f for f in WORLD_FACTS}


class TestWorldTruthDAG(unittest.TestCase):
    def test_ids_are_unique(self):
        ids = [f.id for f in WORLD_FACTS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_need_resolves(self):
        for f in WORLD_FACTS:
            for dep in f.needs:
                self.assertIn(dep, _BY_ID, f"{f.id} needs unknown {dep}")

    def test_no_fact_needs_itself(self):
        for f in WORLD_FACTS:
            self.assertNotIn(f.id, f.needs, f"{f.id} depends on itself")

    def test_dag_is_acyclic(self):
        WHITE, GREY, BLACK = 0, 1, 2
        colour = {f.id: WHITE for f in WORLD_FACTS}

        def visit(fid, stack):
            colour[fid] = GREY
            for dep in _BY_ID[fid].needs:
                if colour[dep] == GREY:
                    self.fail(f"cycle: {stack + [fid, dep]}")
                if colour[dep] == WHITE:
                    visit(dep, stack + [fid])
            colour[fid] = BLACK

        for f in WORLD_FACTS:
            if colour[f.id] == WHITE:
                visit(f.id, [])

    def test_threads_in_vocabulary(self):
        for f in WORLD_FACTS:
            self.assertIn(f.thread, THREADS)

    def test_every_fact_has_a_short_player_lead(self):
        # audit 1a: `lead` is the investigation-checklist line item -
        # present, short, lowercase-ish player voice, never the id.
        for f in WORLD_FACTS:
            self.assertTrue(f.lead, f"{f.id} has no lead")
            self.assertLessEqual(len(f.lead.split()), 9, f"{f.id} lead too long")
            self.assertNotIn("_", f.lead, f"{f.id} lead leaks an id")
            self.assertNotEqual(f.lead, f.statement)

    def test_chapters_in_arc_range(self):
        # 5 chapters + a finale (chapter 6) - the full World-1 arc.
        for f in WORLD_FACTS:
            self.assertIn(f.chapter, (1, 2, 3, 4, 5, 6))

    def test_needs_never_point_forward_a_chapter(self):
        # a fact may need earlier-or-same-chapter facts, never a later
        # one - the DAG has to be answerable in chapter order.
        for f in WORLD_FACTS:
            for dep in f.needs:
                self.assertLessEqual(
                    _BY_ID[dep].chapter, f.chapter,
                    f"CH{f.chapter} {f.id} needs later CH{_BY_ID[dep].chapter} {dep}")

    def test_milestone_ids_match_contract(self):
        got = {f.id for f in WORLD_FACTS if f.milestone}
        self.assertEqual(got, set(MILESTONE_IDS))

    def test_ch1_has_no_cross_chapter_needs(self):
        for f in WORLD_FACTS:
            if f.chapter != 1:
                continue
            for dep in f.needs:
                self.assertEqual(
                    _BY_ID[dep].chapter, 1,
                    f"CH1 {f.id} needs CH{_BY_ID[dep].chapter} {dep}",
                )

    def test_worldfact_is_frozen(self):
        with self.assertRaises(dataclasses.FrozenInstanceError):
            WORLD_FACTS[0].id = "x"


if __name__ == "__main__":
    unittest.main(verbosity=2)
