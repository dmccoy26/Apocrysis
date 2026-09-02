"""World 3 - "The Deep": kill-test 0 - the world shell.
docs/WORLD_3_THE_DEEP.md §5B.12.

Proves: the DAG walks, the campaign completes on the bot, the
hypothesis ladder breaks through all five rungs, both endings are
reachable, and no Silence content is anywhere in reach. The four new
capabilities (campaign_state, WorldContact, the L7 combat experiment,
the kit seam) are kill-tests A-D and are NOT exercised here.
"""
import unittest

from src.game import Apocrysis
from src.worlds import get_world, WORLDS
from src.worlds.the_deep.truth import WORLD_FACTS, MILESTONE_IDS, THREADS
from src.worlds.the_deep.hypotheses import REGIONAL_HYPOTHESES

THE_DEEP = get_world("the_deep")
_BY_ID = {f.id: f for f in WORLD_FACTS}
_SILENCE_IDS = ("DIS_ORGANISED", "DEAD_WERE_LOCALS", "RESP_THE_CHOICE",
                "RESP_THE_ORDER", "BLUE_SIGNS_FACT")
_WAKE_IDS = ("WAKE_ALONE", "SECTIONS_SEALED", "WAKE_THE_CHOICE")

# §5B.5 - the five facts the belief ladder breaks on. Rungs 1, 2, 4
# break on NON-milestone facts, deliberately (§3.9a).
_LADDER_BREAKS = ("SEAL_FROM_INSIDE", "DELIBERATE_OPERATION",
                  "ORDERS_AFTER_SEAL", "COMMS_CUT_FROM_BELOW",
                  "WORKERS_MAINTAINING_IT")


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


class TestTheDeepDAG(unittest.TestCase):

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
            self.assertIn(f.id, THE_DEEP.discovery_templates,
                          f"{f.id} has no discovery route - it would stall")
            for dt in THE_DEEP.discovery_templates[f.id]:
                self.assertIn(dt.mechanism, THE_DEEP.manifest.supported_mechanisms,
                              f"{f.id} routes via unsupported {dt.mechanism}")

    def test_ladder_breaks_on_the_five_spec_facts(self):
        # §5B.5 / §3.9a: the belief ladder is NOT the milestone set.
        self.assertEqual(tuple(h.held_until for h in REGIONAL_HYPOTHESES),
                         _LADDER_BREAKS)
        non_milestone = [h.held_until for h in REGIONAL_HYPOTHESES
                         if h.held_until not in MILESTONE_IDS]
        self.assertEqual(sorted(non_milestone),
                         ["DELIBERATE_OPERATION", "ORDERS_AFTER_SEAL",
                          "WORKERS_MAINTAINING_IT"])


class TestTheDeepRuns(unittest.TestCase):

    def setUp(self):
        _reset()

    def tearDown(self):
        _reset()

    def test_registered_and_default_still_silence(self):
        self.assertIn("the_deep", WORLDS)
        self.assertEqual(get_world().id, "silence")
        self.assertEqual(get_world("the_deep").id, "the_deep")

    def test_expedition_0_builds_a_mine_mystery_for_the_first_fact(self):
        g = Apocrysis("Deep", seed=3, io=_IO(), world="the_deep")
        self.assertIs(g.world, THE_DEEP)
        self.assertIsNotNone(g.mystery)
        self.assertEqual(g.mystery.world_fact_id, "DESCENT_BLOCKED")
        self.assertIn(g.mystery.mechanism, THE_DEEP.manifest.supported_mechanisms)
        self.assertIn(g.map_archetype, THE_DEEP.map_archetypes)
        blob = (g.mystery.mech_name + " "
                + " ".join(g.mystery.site_labels.values())).lower()
        for leak in ("valley", "ranger", "reservoir", "ship", "deck", "cryo"):
            self.assertNotIn(leak, blob)

    def test_terrain_reglyph_nothing_reads_the_string(self):
        g = Apocrysis("Deep", seed=1, io=_IO(), world="the_deep")
        self.assertNotIn("f =", g.world.terrain_legend)   # no 'forest' wording
        self.assertIn("drift", g.world.terrain_legend)
        self.assertIn("C/M/Q/S/D", g.world.terrain_legend)

    def test_settlement_block_is_a_mine_circuit_not_a_town(self):
        seen = set()
        for seed in range(1, 16):
            g = Apocrysis("Deep", seed=seed, io=_IO(), world="the_deep",
                          expeditions_completed=2)
            seen |= {t['content'] for row in g.map for t in row
                     if isinstance(t, dict) and t.get('terrain') == 'town'}
        self.assertTrue(seen)
        self.assertNotIn('T', seen)
        self.assertLessEqual(seen, set('CMQSD'))

    def test_full_campaign_completes_no_silence_fact_ever_resolves(self):
        depth, guard = 0, 0
        while depth < THE_DEEP.manifest.campaign_length and guard < 80:
            guard += 1
            g = Apocrysis("Deep", seed=100 + depth, io=_IO(["1"]),
                          world="the_deep", expeditions_completed=depth)
            if g.mystery is None:
                if getattr(g, "_encounter_beat", None) is not None:
                    g._encounter_beat_seen = True
                    g._show_encounter_beat()
                    g._establish_encounter_fact()
                g.finish_expedition(reason="went on down")
                depth = g.expeditions_completed
                continue
            _solve(g)
            for sid in _SILENCE_IDS + _WAKE_IDS:
                self.assertIsNone(g.world_investigation.fact(sid))
            if getattr(g, "won", False):
                depth = g.expeditions_completed
        self.assertGreaterEqual(depth, THE_DEEP.manifest.campaign_length,
                                f"campaign stalled at depth {depth}")
        wi_final = dict(Apocrysis._world_investigation)
        unknown = [f.id for f in WORLD_FACTS if wi_final.get(f.id) != "known"]
        self.assertEqual(unknown, [], f"unreached facts: {unknown}")

    def test_hypothesis_ladder_progresses_through_all_five_rungs(self):
        wi = _fresh_wi()
        rungs = []
        for f in WORLD_FACTS:
            h = wi.current_hypothesis()
            if h and (not rungs or rungs[-1] != h.id):
                rungs.append(h.id)
            wi.mark_known(f.id)
        self.assertIsNone(wi.current_hypothesis())
        self.assertEqual(rungs, [r.id for r in REGIONAL_HYPOTHESES])

    def test_both_endings_reachable(self):
        tail = set(THE_DEEP.finale.also_establishes) | {"THE_CHOICE"}
        for ans, key, needle in (("1", "bring_up", "the seam goes up"),
                                 ("2", "seal_it", "stays below for good")):
            _reset()
            Apocrysis._world_investigation = {
                f.id: "known" for f in WORLD_FACTS if f.id not in tail
            }
            g = Apocrysis("Deep", seed=7, io=_IO([ans]), world="the_deep",
                          expeditions_completed=THE_DEEP.manifest.campaign_length - 1)
            self.assertTrue(getattr(g.mystery, "is_finale", False))
            self.assertEqual(g.mystery.world_fact_id, "THE_CHOICE")
            out = _solve(g)
            self.assertEqual(Apocrysis._campaign_ending, key)
            self.assertIn(needle, out)
            self.assertIn("CAMPAIGN COMPLETE", out)
            self.assertTrue(g.world_investigation.is_known("RESTART_REOPENS_THE_ROUTE"))
            self.assertNotIn("Protocol Seven", out)
            self.assertNotIn("reactor", out.lower())
        _reset()

    def test_mystery_prose_round_trips_through_save_load(self):
        from src.escape import Mystery
        g = Apocrysis("Deep", seed=5, io=_IO(), world="the_deep")
        d = g.mystery.to_dict()
        m2 = Mystery.from_dict(d)
        self.assertEqual(m2.mech_name, g.mystery.mech_name)
        self.assertEqual(m2.mech_landmark, g.mystery.mech_landmark)


def _fresh_wi():
    from src.world_investigation import WorldInvestigation
    return WorldInvestigation(THE_DEEP.world_facts, THE_DEEP.regional_hypotheses)


if __name__ == "__main__":
    unittest.main()
