"""World 2 - "The Wake": the real adversarial integration test.
docs/WORLD_2_THE_WAKE.md §11 step 7.

Testcove proved the engine can *execute* another world. The Wake proves
the engine can *host an authored game*: a full campaign through the real
loop, every WorldFact reachable in DAG order, the hypothesis ladder
breaking on all four rungs, both endings, save/load, and no Silence
content anywhere in reach.
"""
import unittest

from src.game import Apocrysis
from src.worlds import get_world, WORLDS
from src.worlds.the_wake.truth import WORLD_FACTS, MILESTONE_IDS, THREADS
from src.worlds.the_wake.hypotheses import REGIONAL_HYPOTHESES

THE_WAKE = get_world("the_wake")
_BY_ID = {f.id: f for f in WORLD_FACTS}
_SILENCE_IDS = ("DIS_ORGANISED", "DEAD_WERE_LOCALS", "RESP_THE_CHOICE",
                "RESP_THE_ORDER", "BLUE_SIGNS_FACT")


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
    Apocrysis.reset_campaign_state()


def _solve(g):
    """Force this expedition's mystery to done and win it - mechanism
    agnostic (bypasses power/control/checklist gates)."""
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


class TestTheWakeDAG(unittest.TestCase):
    """Same integrity checks World 1's truth gets (test_world_truth)."""

    def test_ids_unique_and_needs_resolve(self):
        ids = [f.id for f in WORLD_FACTS]
        self.assertEqual(len(ids), len(set(ids)))
        for f in WORLD_FACTS:
            for d in f.needs:
                self.assertIn(d, _BY_ID, f"{f.id} needs unknown {d}")
            self.assertNotIn(f.id, f.needs)

    def test_dag_is_acyclic(self):
        WHITE, GREY, BLACK = 0, 1, 2
        colour = {f.id: WHITE for f in WORLD_FACTS}

        def visit(fid, stack):
            colour[fid] = GREY
            for dep in _BY_ID[fid].needs:
                self.assertNotEqual(colour[dep], GREY, f"cycle {stack+[fid,dep]}")
                if colour[dep] == WHITE:
                    visit(dep, stack + [fid])
            colour[fid] = BLACK

        for f in WORLD_FACTS:
            if colour[f.id] == WHITE:
                visit(f.id, [])

    def test_threads_and_chapters_and_leads(self):
        for f in WORLD_FACTS:
            self.assertIn(f.thread, THREADS)
            self.assertIn(f.chapter, (1, 2, 3, 4, 5))
            self.assertTrue(f.lead and len(f.lead.split()) <= 9)
            self.assertNotIn("_", f.lead)
            self.assertNotEqual(f.lead, f.statement)

    def test_milestone_flag_matches_the_id_set(self):
        self.assertEqual({f.id for f in WORLD_FACTS if f.milestone},
                         set(MILESTONE_IDS))

    def test_every_fact_has_a_discovery_route(self):
        for f in WORLD_FACTS:
            self.assertIn(f.id, THE_WAKE.discovery_templates,
                          f"{f.id} has no discovery route - it would stall the campaign")
            for dt in THE_WAKE.discovery_templates[f.id]:
                self.assertIn(dt.mechanism, THE_WAKE.manifest.supported_mechanisms,
                              f"{f.id} routes via unsupported {dt.mechanism}")

    def test_hypothesis_rungs_break_on_milestones(self):
        ms = set(MILESTONE_IDS)
        for h in REGIONAL_HYPOTHESES:
            self.assertIn(h.held_until, ms, f"{h.id} breaks on non-milestone {h.held_until}")


class TestTheWakeRuns(unittest.TestCase):

    def setUp(self):
        _reset()

    def tearDown(self):
        _reset()

    def test_registered_and_default_still_silence(self):
        self.assertIn("the_wake", WORLDS)
        self.assertEqual(get_world().id, "silence")
        self.assertEqual(get_world("the_wake").id, "the_wake")

    def test_expedition_0_builds_a_ship_mystery_for_the_first_fact(self):
        g = Apocrysis("Wake", seed=3, io=_IO(), world="the_wake")
        self.assertIs(g.world, THE_WAKE)
        self.assertIsNotNone(g.mystery)
        self.assertEqual(g.mystery.world_fact_id, "WAKE_ALONE")
        self.assertIn(g.mystery.mechanism, THE_WAKE.manifest.supported_mechanisms)
        self.assertIn(g.map_archetype, THE_WAKE.map_archetypes)
        # the mystery prose is ship prose, not valley prose
        blob = (g.mystery.mech_name + " " + " ".join(g.mystery.site_labels.values())).lower()
        self.assertNotIn("valley", blob)
        self.assertNotIn("ranger", blob)

    def test_terrain_reglyph_nothing_reads_the_string(self):
        g = Apocrysis("Wake", seed=1, io=_IO(), world="the_wake")
        rendered = "\n".join(g._render_map_lines())
        # 'o' is The Wake's compartment glyph; 'b' is Silence's building.
        self.assertNotIn("f =", g.world.terrain_legend)   # no 'forest' wording
        self.assertIn("compartment", g.world.terrain_legend)

    def test_full_campaign_completes_no_silence_fact_ever_resolves(self):
        depth, guard = 0, 0
        seen_corrections = []
        while depth < THE_WAKE.manifest.campaign_length and guard < 60:
            guard += 1
            g = Apocrysis("Wake", seed=100 + depth, io=_IO(["1"]),
                          world="the_wake", expeditions_completed=depth)
            if g.mystery is None:
                depth += 1
                continue
            out = _solve(g)
            for _c in ("DIDN'T FAIL", "WASN'T PANIC", "ISN'T A BARRICADE",
                       "ONLY HOLDS WHILE THE SHIP IS DEAD"):
                if _c.lower() in out.lower():
                    seen_corrections.append(_c)
            # no Silence fact id is even in this campaign's investigation
            for sid in _SILENCE_IDS:
                self.assertIsNone(g.world_investigation.fact(sid))
            if getattr(g, "won", False):
                depth = g.expeditions_completed
        self.assertGreaterEqual(depth, THE_WAKE.manifest.campaign_length,
                                f"campaign stalled at depth {depth}")
        # every WorldFact established by the end
        wi_final = dict(Apocrysis._world_investigation)
        unknown = [f.id for f in WORLD_FACTS if wi_final.get(f.id) != "known"]
        self.assertEqual(unknown, [], f"unreached facts: {unknown}")

    def test_hypothesis_ladder_progresses_through_all_four_rungs(self):
        wi = _fresh_wi()
        rungs = []
        # walk the milestones in DAG order, recording the held rung
        for f in WORLD_FACTS:
            h = wi.current_hypothesis()
            if h and (not rungs or rungs[-1] != h.id):
                rungs.append(h.id)
            wi.mark_known(f.id)
        # after the last milestone, no rung is held (the truth)
        self.assertIsNone(wi.current_hypothesis())
        self.assertEqual(rungs, [r.id for r in REGIONAL_HYPOTHESES])

    def test_both_endings_reachable(self):
        for ans, key, needle in (("1", "restart", "You make the pod bay"),
                                 ("2", "shutdown", "you leave the reactor cold")):
            _reset()
            Apocrysis._world_investigation = {
                f.id: "known" for f in WORLD_FACTS
                if f.id not in ("WAKE_THE_CHOICE", "SURVIVORS_ON_A_CLOCK",
                                "WAKE_RESTART_RELEASES", "SHUTDOWN_WAS_THE_CONTAINMENT")
            }
            g = Apocrysis("Wake", seed=7, io=_IO([ans]), world="the_wake",
                          expeditions_completed=THE_WAKE.manifest.campaign_length - 1)
            self.assertTrue(getattr(g.mystery, "is_finale", False))
            self.assertEqual(g.mystery.world_fact_id, "WAKE_THE_CHOICE")
            out = _solve(g)
            self.assertEqual(Apocrysis._campaign_ending, key)
            self.assertIn(needle, out)
            self.assertIn("CAMPAIGN COMPLETE", out)
            # the FIN chain + its final correction land at the finale
            self.assertTrue(g.world_investigation.is_known("WAKE_RESTART_RELEASES"))
            self.assertIn("only holds while the ship is dead", out.lower())
            self.assertNotIn("Protocol Seven", out)
            self.assertNotIn("cordon", out)
        _reset()

    def test_mystery_prose_round_trips_through_save_load(self):
        from src.escape import Mystery
        g = Apocrysis("Wake", seed=5, io=_IO(), world="the_wake")
        d = g.mystery.to_dict()
        m2 = Mystery.from_dict(d)
        self.assertEqual(m2.mech_name, g.mystery.mech_name)
        self.assertEqual(m2.mech_landmark, g.mystery.mech_landmark)
        self.assertEqual(m2.control_correct, g.mystery.control_correct)


def _fresh_wi():
    from src.world_investigation import WorldInvestigation
    return WorldInvestigation(THE_WAKE.world_facts, THE_WAKE.regional_hypotheses)


if __name__ == "__main__":
    unittest.main()
