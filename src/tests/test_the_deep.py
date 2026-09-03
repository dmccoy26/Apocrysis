"""World 3 - "The Deep": kill-tests 0 + A-D and the Phase-6 integration.
docs/WORLD_3_THE_DEEP.md.

Kill-test 0 proved the content translates. A-D each proved one small
capability necessary (persistent campaign_state, contested testimony,
authored combat sequencing, a declarative kit gate) and killed the
generic abstraction the spec proposed. Integration assembles the
survivors: the authored carriers realigned, the kill-test-0
scaffolding gone.
"""
import os
import tempfile
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

_LADDER_BREAKS = ("SEAL_FROM_INSIDE", "DELIBERATE_OPERATION",
                  "ORDERS_AFTER_SEAL", "COMMS_CUT_FROM_BELOW",
                  "WORKERS_MAINTAINING_IT")

_CONTESTED = THE_DEEP.contacts["contested_fact"]      # WORKERS_CHOSE_ISOLATION
_RESOLVED_BY = THE_DEEP.contacts["resolved_by"]       # CONTAINMENT_INFRASTRUCTURE


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
        return bool(self._answers.pop(0)) if self._answers else False


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


def _advance(g):
    """Complete this expedition, whatever kind it is - a mystery, a
    combat beat, a contact, a scene beat, or a plain crossing."""
    if g.mystery is not None:
        return _solve(g)
    g.io.log.clear()
    if getattr(g, "_combat_beat", None) is not None:
        # bot: never breaks contact (ask_yes_no -> False), fights both
        g.current_position = tuple(g._encounter_beat)
        g._deep_combat_beat_run()
        g._establish_encounter_fact()
    elif getattr(g, "_encounter_contact", None) is not None:
        g._encounter_beat_seen = True
        g._show_encounter_beat()
        g._establish_encounter_fact()
    elif getattr(g, "_encounter_beat", None) is not None:
        g._encounter_beat_seen = True
        g._show_encounter_beat()
        g._establish_encounter_fact()
    if getattr(g, "_discovery_pickup", None) is not None:
        g._discovery_pickup_taken = True
        g._grant_discovery_pickup(g._discovery_pickup[1])
    # a discovery crossing may also carry a physical reading
    _df = (getattr(g.world.manifest, "discovery_facts", None) or {}).get(
        g.expeditions_completed)
    _wi = g.world_investigation
    if (_df and _wi.fact(_df) is not None and not _wi.is_known(_df)
            and all(_wi.is_known(d) for d in _wi.fact(_df).needs)):
        g._mystery_mark_world_fact(_df)
    g.finish_expedition(reason="went on down")
    return "\n".join(g.io.log)


def _run_campaign(seed_base=100, answers=("1",)):
    """Walk a whole Deep campaign on the bot. Returns (depth, log)."""
    _reset()
    depth, guard, log = 0, 0, []
    while depth < THE_DEEP.manifest.campaign_length and guard < 80:
        guard += 1
        g = Apocrysis("Deep", seed=seed_base + depth, io=_IO(list(answers)),
                      world="the_deep", expeditions_completed=depth)
        # the first Changed - auto-establishes CHANGED_ARE_CREW
        g._deep_auto_fact("first_hostile")
        out = _advance(g)
        log.append(out)
        if getattr(g, "won", False):
            depth = g.expeditions_completed
    return depth, "\n".join(log)


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
            self.assertTrue(f.lead and len(f.lead.split()) <= 9, f.id)
            self.assertNotIn("_", f.lead)
            self.assertNotEqual(f.lead, f.statement)

    def test_milestone_flag_matches_the_id_set(self):
        self.assertEqual({f.id for f in WORLD_FACTS if f.milestone},
                         set(MILESTONE_IDS))

    def test_the_carrier_map_covers_every_fact_exactly_once(self):
        mf = THE_DEEP.manifest
        mystery = set(THE_DEEP.discovery_templates) - {"THE_CHOICE"}
        beat = set(mf.beat_carried_facts)
        finale = set(THE_DEEP.finale.also_establishes) | {"THE_CHOICE"}
        covered = mystery | beat | finale
        self.assertEqual(covered, {f.id for f in WORLD_FACTS},
                         f"uncovered: {{f.id for f in WORLD_FACTS}} - covered")
        # a mystery fact is never also beat-carried
        self.assertEqual(mystery & beat, set())

    def test_mystery_facts_route_via_supported_mechanisms(self):
        for fid, dts in THE_DEEP.discovery_templates.items():
            for dt in dts:
                self.assertIn(dt.mechanism, THE_DEEP.manifest.supported_mechanisms)

    def test_ladder_breaks_on_the_five_facts(self):
        self.assertEqual(tuple(h.held_until for h in REGIONAL_HYPOTHESES),
                         _LADDER_BREAKS)
        non_milestone = sorted(h.held_until for h in REGIONAL_HYPOTHESES
                               if h.held_until not in MILESTONE_IDS)
        self.assertEqual(non_milestone,
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

    def test_expedition_0_builds_a_mine_mystery_for_the_first_fact(self):
        g = Apocrysis("Deep", seed=3, io=_IO(), world="the_deep")
        self.assertIs(g.world, THE_DEEP)
        self.assertEqual(g.mystery.world_fact_id, "DESCENT_BLOCKED")
        self.assertIn(g.mystery.mechanism, THE_DEEP.manifest.supported_mechanisms)
        blob = (g.mystery.mech_name + " "
                + " ".join(g.mystery.site_labels.values())).lower()
        for leak in ("valley", "ranger", "reservoir", "ship", "deck", "cryo"):
            self.assertNotIn(leak, blob)

    def test_terrain_reglyph_and_settlement_block(self):
        g = Apocrysis("Deep", seed=1, io=_IO(), world="the_deep")
        self.assertNotIn("f =", g.world.terrain_legend)
        self.assertIn("drift", g.world.terrain_legend)
        seen = set()
        for seed in range(1, 12):
            g2 = Apocrysis("Deep", seed=seed, io=_IO(), world="the_deep",
                           expeditions_completed=2)
            seen |= {t['content'] for row in g2.map for t in row
                     if isinstance(t, dict) and t.get('terrain') == 'town'}
        self.assertTrue(seen and 'T' not in seen)
        self.assertLessEqual(seen, set('CMQSD'))

    def test_full_campaign_completes_and_every_fact_lands(self):
        depth, _ = _run_campaign()
        self.assertGreaterEqual(depth, THE_DEEP.manifest.campaign_length,
                                f"campaign stalled at depth {depth}")
        wi = dict(Apocrysis._world_investigation)
        unknown = [f.id for f in WORLD_FACTS if wi.get(f.id) != "known"]
        self.assertEqual(unknown, [], f"unreached facts: {unknown}")
        # no cross-world fact ever exists in the Deep's investigation
        for sid in _SILENCE_IDS + _WAKE_IDS:
            self.assertNotIn(sid, wi)

    def test_the_hypothesis_ladder_fires_every_correction_in_a_real_run(self):
        _reset()
        _, log = _run_campaign()
        for rung in REGIONAL_HYPOTHESES:
            self.assertIn(rung.corrected_to.split(".")[0][:30], log,
                          f"correction for {rung.id} never fired")

    def test_the_finale_choice_arrives_already_understanding_the_cost(self):
        # by the time the finale prompt shows, the player knows the
        # restoration consequence, the survivors' clock, and the stances.
        depth, log = _run_campaign()
        self.assertGreaterEqual(depth, 25)
        wi = dict(Apocrysis._world_investigation)
        for fid in ("RESTART_REOPENS_THE_ROUTE", "SURVIVORS_ON_A_CLOCK",
                    "THE_STANCES", "ORE_IS_SOURCE"):
            self.assertEqual(wi.get(fid), "known", fid)

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
        for ans, key, needle in ((1, "bring_up", "the seam goes up"),
                                 (2, "seal_it", "stays below for good")):
            _reset()
            Apocrysis._world_investigation = {
                f.id: "known" for f in WORLD_FACTS if f.id not in tail
            }
            g = Apocrysis("Deep", seed=7, io=_IO([str(ans)]), world="the_deep",
                          expeditions_completed=THE_DEEP.manifest.campaign_length - 1)
            self.assertTrue(getattr(g.mystery, "is_finale", False))
            self.assertEqual(g.mystery.world_fact_id, "THE_CHOICE")
            out = _solve(g)
            self.assertEqual(Apocrysis._campaign_ending, key)
            self.assertIn(needle, out)
            self.assertIn("CAMPAIGN COMPLETE", out)
            self.assertNotIn("Protocol Seven", out)
            self.assertNotIn("reactor", out.lower())
        _reset()


class TestKillTestA(unittest.TestCase):
    """Persistent facility restoration (§5B.8)."""

    def setUp(self):
        _reset()

    def tearDown(self):
        _reset()

    def test_no_facility_systems_is_a_total_noop(self):
        for wid in ("silence", "the_wake"):
            self.assertIsNone(get_world(wid).facility_systems)
        g = Apocrysis("W", seed=1, io=_IO(), world="the_wake")
        g._deep_restore("ANYTHING")
        self.assertEqual(Apocrysis._campaign_state.get("restored", []), [])

    def test_restoration_accumulates_and_fills_the_extraction_line(self):
        depth, log = _run_campaign()
        self.assertGreaterEqual(depth, 25)
        cs = Apocrysis._campaign_state
        path = set(THE_DEEP.facility_systems["extraction_path"])
        self.assertTrue(path.issubset(set(cs["restored"])),
                        f"line not whole: {cs['restored']}")
        self.assertIn("THE EXTRACTION LINE IS WHOLE", log)
        levels = [e[1] for e in cs["restoration_log"]]
        self.assertEqual(levels, sorted(levels))
        self.assertEqual(Apocrysis._world_investigation.get(
            "RESTART_REOPENS_THE_ROUTE"), "known")

    def test_restart_fires_at_L23_when_its_knowledge_precondition_is_met(self):
        fac = THE_DEEP.facility_systems
        path = list(fac["extraction_path"])
        Apocrysis._world_investigation = {
            f.id: "known" for f in WORLD_FACTS
            if f.id not in ("RESTART_REOPENS_THE_ROUTE", "THE_CHOICE")
        }
        Apocrysis._campaign_state = {"restored": path[:-1],
                                     "restoration_log": [[s, 3] for s in path[:-1]]}
        g = Apocrysis("Deep", seed=7, io=_IO(), world="the_deep",
                      expeditions_completed=22)
        g.world_investigation.restore({"status": dict(Apocrysis._world_investigation)})
        g._deep_restore("discovery:2")
        self.assertIn(path[-1], Apocrysis._campaign_state["restored"])
        self.assertTrue(g.world_investigation.is_known("RESTART_REOPENS_THE_ROUTE"))

    def test_campaign_state_round_trips_through_save_load_and_death(self):
        Apocrysis._campaign_state = {
            "restored": ["power", "lift_deep"],
            "restoration_log": [["power", 4], ["lift_deep", 10]],
            "stances": [], "testimony": {},
        }
        g = Apocrysis("Deep", seed=1, io=_IO(), world="the_deep",
                      expeditions_completed=11)
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        try:
            g.save_profile(path)
            _reset()
            self.assertEqual(Apocrysis._campaign_state.get("restored", []), [])
            g2 = Apocrysis("Deep", seed=1, io=_IO(), world="the_deep")
            g2.apply_profile(Apocrysis.load_profile(path))
            self.assertEqual(set(Apocrysis._campaign_state["restored"]),
                             {"power", "lift_deep"})
        finally:
            os.unlink(path)


class TestKillTestB(unittest.TestCase):
    """Person as evidence source (§5B.7)."""

    def setUp(self):
        _reset()

    def tearDown(self):
        _reset()

    def _contact(self, lvl_idx, seed=5):
        g = Apocrysis("Deep", seed=seed, io=_IO(), world="the_deep",
                      expeditions_completed=lvl_idx)
        g.world_investigation.restore(
            {"status": dict(Apocrysis._world_investigation)})
        self.assertIsNotNone(getattr(g, "_encounter_contact", None),
                             f"no contact at level index {lvl_idx}")
        g._encounter_beat_seen = True
        return g

    def test_no_contacts_is_a_noop(self):
        for wid in ("silence", "the_wake"):
            self.assertIsNone(get_world(wid).contacts)
        g = Apocrysis("W", seed=1, io=_IO(), world="the_wake")
        self.assertIsNone(getattr(g, "_encounter_contact", None))

    def test_del_then_marek_contradict_and_the_fact_stays_suspected(self):
        g = self._contact(14)                          # DEL (L15)
        g._establish_contact_testimony()
        self.assertEqual(Apocrysis._world_investigation.get(_CONTESTED), "suspected")
        keep_wi = dict(Apocrysis._world_investigation)
        g2 = self._contact(19)                         # MAREK (L20)
        Apocrysis._world_investigation = keep_wi
        g2.world_investigation.restore({"status": keep_wi})
        g2._establish_contact_testimony()
        self.assertEqual(Apocrysis._world_investigation.get(_CONTESTED), "suspected")
        tst = Apocrysis._campaign_state["testimony"][_CONTESTED]
        self.assertEqual([t[0] for t in tst], ["DEL", "MAREK"])
        self.assertEqual([t[1] for t in tst], ["leave", "hold"])
        self.assertNotEqual(tst[0][2], tst[1][2])
        # MAREK also confirms his own fact directly (KNOWN, not testimony)
        self.assertEqual(Apocrysis._world_investigation.get(
            "WORKERS_MAINTAINING_IT"), "known")

    def test_physical_evidence_adjudicates_the_contested_fact(self):
        g = self._contact(14)
        g._establish_contact_testimony()
        self.assertEqual(g.world_investigation.status(_CONTESTED), "suspected")
        g._mystery_mark_world_fact(_RESOLVED_BY)       # the L19 physical reading
        self.assertEqual(Apocrysis._world_investigation.get(_CONTESTED), "known")

    def test_marek_line_varies_on_whether_del_was_heard(self):
        g = self._contact(14)
        g._establish_contact_testimony()               # stance "leave"
        g2 = self._contact(19)
        lines, _ = g2._encounter_beat_prose()
        self.assertTrue(any("Del" in ln for ln in lines))
        _reset()
        g3 = self._contact(19)
        self.assertFalse(any("Del's been talking" in ln
                             for ln in g3._encounter_beat_prose()[0]))

    def test_the_stances_lands_at_the_three_way_scene_not_before(self):
        g = self._contact(14)
        g._establish_contact_testimony()
        self.assertNotEqual(Apocrysis._world_investigation.get("THE_STANCES"), "known")
        g2 = self._contact(19)
        g2._establish_contact_testimony()
        self.assertNotEqual(Apocrysis._world_investigation.get("THE_STANCES"), "known")
        g3 = self._contact(23)                          # L24 - the three of them
        g3._establish_contact_testimony()
        self.assertEqual(Apocrysis._world_investigation.get("THE_STANCES"), "known")

    def test_orla_establishes_her_facts_directly(self):
        g = self._contact(21)                           # L22 - ORLA
        g._establish_contact_testimony()
        for fid in ("ORE_IS_SOURCE", "SURVIVORS_ON_A_CLOCK"):
            self.assertEqual(Apocrysis._world_investigation.get(fid), "known", fid)


class _ScriptIO:
    renders_natively = True

    def __init__(self, answers=()):
        self.log = []
        self._a = list(answers)

    def say(self, *a, **k):
        self.log.append(" ".join(str(x) for x in a))

    def ask(self, prompt=""):
        return ""

    def ask_yes_no(self, prompt):
        return self._a.pop(0) if self._a else True


class TestKillTestC(unittest.TestCase):
    """The L7 stationed-pair combat beat (§5B.3)."""

    def setUp(self):
        _reset()

    def tearDown(self):
        _reset()

    def _at_beat(self, answers, seed=5):
        g = Apocrysis("Deep", seed=seed, io=_ScriptIO(answers),
                      world="the_deep", expeditions_completed=6)
        self.assertIsNotNone(getattr(g, "_combat_beat", None))
        g.world_investigation.restore(
            {"status": dict(Apocrysis._world_investigation)})
        return g

    def test_no_combat_beat_is_a_noop(self):
        for wid in ("silence", "the_wake"):
            self.assertIsNone(get_world(wid).combat_beat)

    def test_the_pair_is_authored_not_rolled(self):
        from src.zombies import speed_class_of
        g = self._at_beat([])
        for z in (g._combat_z1, g._combat_flank_zombie):
            self.assertEqual(z.flags, ())
            self.assertNotIn("Elite", z.name)
            self.assertEqual(speed_class_of(z), "normal")
            self.assertLessEqual(z.health, 30)

    def test_commit_then_break_is_a_legitimate_success(self):
        g = self._at_beat([True, True])
        g.current_position = tuple(g._encounter_beat)
        g._deep_combat_beat_run()
        self.assertGreater(g.health, 0)
        self.assertTrue(g._encounter_beat_seen)
        self.assertGreater(g._combat_flank_zombie.health, 0)

    def test_breaking_leaves_the_flank_hostile_untouched(self):
        # breaking contact: you didn't fight the second one.
        g_break = self._at_beat([True, True])
        g_break.current_position = tuple(g_break._encounter_beat)
        z2_hp0 = g_break._combat_flank_zombie.health
        g_break._deep_combat_beat_run()
        self.assertEqual(g_break._combat_flank_zombie.health, z2_hp0)
        # pushing: you did fight it (it takes damage / dies).
        _reset()
        g_push = self._at_beat([True, False] + [True] * 20)
        g_push.current_position = tuple(g_push._encounter_beat)
        z2b0 = g_push._combat_flank_zombie.health
        g_push._deep_combat_beat_run()
        self.assertLess(g_push._combat_flank_zombie.health, z2b0)

    def test_dying_to_the_first_does_not_burn_the_fact(self):
        g = self._at_beat([True] * 20)
        g.current_position = tuple(g._encounter_beat)
        g.health = 8
        g._combat_z1.health = 200
        g._combat_z1.attack = 30
        g._deep_combat_beat_run()
        self.assertLessEqual(g.health, 0)
        self.assertFalse(g._encounter_beat_seen)

    def test_the_fact_lands_on_crossing_completion(self):
        Apocrysis._world_investigation = {"DESCENT_BLOCKED": "known"}
        g = self._at_beat([True, True])
        g.current_position = tuple(g._encounter_beat)
        g._deep_combat_beat_run()
        self.assertFalse(g.world_investigation.is_known(g._combat_beat["fact"]))
        g._establish_encounter_fact()
        self.assertTrue(g.world_investigation.is_known(g._combat_beat["fact"]))
        # fighting the pair also established "these are crew"
        self.assertTrue(g.world_investigation.is_known("CHANGED_ARE_CREW"))


class TestKillTestD(unittest.TestCase):
    """D1 kit seam (§3.1) + D2 vertical fiction (§5B.11)."""

    def setUp(self):
        _reset()

    def tearDown(self):
        _reset()

    def _walk_to(self, g, target):
        from src.worldgen.reachable import shortest_path
        for (nx, ny) in shortest_path(g.map, g.map_size,
                                      g.current_position, target)[1:]:
            cx, cy = g.current_position
            d = {(1, 0): "e", (-1, 0): "w", (0, 1): "s", (0, -1): "n"}.get(
                (nx - cx, ny - cy))
            if d is None or g.health <= 0:
                break
            g.move_and_search(d)

    def test_no_section_kit_is_a_noop(self):
        for wid in ("silence", "the_wake"):
            m = get_world(wid).manifest
            self.assertIsNone(getattr(m, "section_kit", None))
            self.assertIsNone(getattr(m, "discovery_grants", None))

    def test_the_requirement_is_always_meetable(self):
        sk = THE_DEEP.manifest.section_kit
        dg = THE_DEEP.manifest.discovery_grants
        for lvl, (flag, _label) in sk.items():
            granted = [g_lvl for g_lvl, (g_flag, _k) in dg.items() if g_flag == flag]
            self.assertTrue(granted)
            self.assertLess(min(granted), lvl)

    def _step_onto_exit(self, g):
        """Place the survivor one tile from the section exit and step on
        - isolates the crossing-completion gate from the Band-V combat
        the full walk would trigger."""
        ex, ey = g.section_exit
        for (ax, ay), d in (((ex - 1, ey), "e"), ((ex + 1, ey), "w"),
                            ((ex, ey - 1), "s"), ((ex, ey + 1), "n")):
            cell = g.map[ay][ax] if 0 <= ay < g.map_h and 0 <= ax < g.map_w else None
            if isinstance(cell, dict) and cell.get("terrain") not in ("mountain", "river"):
                g.current_position = (ax, ay)
                g.tile_event_cooldowns[(ax, ay)] = g.day + 5   # no fight this step
                g.health = g.max_health
                g.move_and_search(d)
                return
        self.fail("no passable tile beside the exit")

    def test_the_bore_crossing_is_gated_on_breathing_gear(self):
        lvl = min(THE_DEEP.manifest.section_kit)
        g = Apocrysis("D", seed=5, io=_IO(["1"]), world="the_deep",
                      expeditions_completed=lvl)
        self.assertIsNone(g.mystery)
        self._step_onto_exit(g)
        self.assertFalse(getattr(g, "won", False))
        self.assertTrue(any("breathing gear" in ln or "can't take it without" in ln
                            for ln in g.io.log))
        _reset()
        g2 = Apocrysis("D", seed=5, io=_IO(["1"]), world="the_deep",
                       expeditions_completed=lvl)
        g2.has_waders = True
        self._step_onto_exit(g2)
        self.assertTrue(getattr(g2, "won", False))

    def test_the_kit_is_guaranteed_on_the_earlier_discovery_crossing(self):
        g_lvl = min(THE_DEEP.manifest.discovery_grants)
        g = Apocrysis("D", seed=3, io=_IO(["1"]), world="the_deep",
                      expeditions_completed=g_lvl)
        self.assertEqual(g._section_level_type, "discovery")
        self.assertEqual(g._discovery_pickup[1], "waders")
        self.assertFalse(getattr(g, "has_waders", False))
        g._grant_discovery_pickup(g._discovery_pickup[1])
        self.assertTrue(getattr(g, "has_waders", False))

    def test_the_deep_crossings_suppress_the_compass(self):
        g = Apocrysis("D", seed=5, io=_IO(), world="the_deep",
                      expeditions_completed=11)
        self.assertEqual(g._crossing_bearing(g.section_exit), "")
        self.assertEqual(g._crossing_exit_noun(), "the way down")

    def test_other_worlds_keep_the_compass(self):
        g = Apocrysis("W", seed=5, io=_IO(), world="the_wake",
                      expeditions_completed=6)
        self.assertEqual(g._crossing_exit_noun(), "the way through")

    def test_no_deep_crossing_objective_names_a_direction(self):
        g = Apocrysis("D", seed=7, io=_IO(), world="the_deep",
                      expeditions_completed=11)
        _scene, _obj = g._section_brief()
        line = f"{_obj} It's marked{g._crossing_bearing(g.section_exit)}."
        for d in (" east", " west", " north", " south"):
            self.assertNotIn(d, line.lower())


def _fresh_wi():
    from src.world_investigation import WorldInvestigation
    return WorldInvestigation(THE_DEEP.world_facts, THE_DEEP.regional_hypotheses)


if __name__ == "__main__":
    unittest.main()
