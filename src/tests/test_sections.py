"""The spatial spine - WAKE_SPINE_INVESTIGATION.md §5.

Sections are The Wake's Bridge -> Main Engineering progression: a
SEPARATE axis from chapters. The Silence has no spine and must be
untouched by any of it.
"""
import unittest

from src.worlds import get_world
from src.sections import (
    section_index_for, section_name_for, section_archetype_for,
    sections_ahead, section_count, has_spine, campaign_objective_line,
    level_type_for, is_section_transit_level, is_encounter_level,
    crosses_section,
)

WAKE = get_world("the_wake")
SILENCE = get_world("silence")


class TestSilenceHasNoSpine(unittest.TestCase):
    def test_all_helpers_return_none_for_silence(self):
        self.assertFalse(has_spine(SILENCE))
        self.assertEqual(section_count(SILENCE), 0)
        for exp in (0, 5, 12, 24):
            self.assertIsNone(section_index_for(exp, SILENCE))
            self.assertIsNone(section_name_for(exp, SILENCE))
            self.assertIsNone(section_archetype_for(exp, SILENCE))
            self.assertIsNone(sections_ahead(exp, SILENCE))

    def test_silence_manifest_untouched(self):
        self.assertEqual(SILENCE.manifest.section_bounds, ())
        self.assertEqual(SILENCE.manifest.campaign_length, 25)


class TestWakeSpine(unittest.TestCase):
    def test_seven_sections_owner_locked_bounds(self):
        self.assertEqual(WAKE.manifest.section_bounds, (0, 3, 7, 11, 15, 19, 22))
        self.assertEqual(section_count(WAKE), 7)
        self.assertEqual(len(WAKE.manifest.section_names), 7)
        self.assertEqual(len(WAKE.manifest.section_archetypes), 7)

    def test_campaign_is_25_levels(self):
        self.assertEqual(WAKE.manifest.campaign_length, 25)

    def test_section_index_is_monotone_over_the_whole_campaign(self):
        prev = -1
        for exp in range(25):
            i = section_index_for(exp, WAKE)
            self.assertGreaterEqual(i, prev)
            prev = i
        self.assertEqual(section_index_for(0, WAKE), 0)
        self.assertEqual(section_index_for(2, WAKE), 0)
        self.assertEqual(section_index_for(3, WAKE), 1)
        self.assertEqual(section_index_for(24, WAKE), 6)

    def test_sections_ahead_counts_down_to_zero(self):
        self.assertEqual(sections_ahead(0, WAKE), 6)
        self.assertEqual(sections_ahead(3, WAKE), 5)
        self.assertEqual(sections_ahead(22, WAKE), 0)
        self.assertEqual(sections_ahead(24, WAKE), 0)

    def test_every_section_archetype_is_a_real_wake_archetype(self):
        for a in WAKE.manifest.section_archetypes:
            self.assertIn(a, WAKE.map_archetypes)

    def test_first_and_last_sections_read_bridge_and_engineering(self):
        self.assertEqual(section_name_for(0, WAKE), "BRIDGE")
        self.assertEqual(section_name_for(24, WAKE), "MAIN ENGINEERING")


class TestCampaignObjectiveLine(unittest.TestCase):
    def _game(self, exp):
        from src.game import Apocrysis
        Apocrysis.reset_campaign_state()
        return Apocrysis("W", seed=exp + 1, io=_IO(), world="the_wake",
                         expeditions_completed=exp)

    def tearDown(self):
        from src.game import Apocrysis
        Apocrysis.reset_campaign_state()

    def test_hidden_until_the_gate_milestone_is_known(self):
        g = self._game(3)
        self.assertIsNone(campaign_objective_line(g))
        g.world_investigation.mark_known("SECTIONS_SEALED")
        self.assertEqual(campaign_objective_line(g),
                         "REACH MAIN ENGINEERING · 5 SECTIONS AHEAD")

    def test_counts_down_and_arrives(self):
        g = self._game(3)
        g.world_investigation.mark_known("SECTIONS_SEALED")
        self.assertIn("5 SECTIONS AHEAD", campaign_objective_line(g))
        g2 = self._game(22)
        g2.world_investigation.mark_known("SECTIONS_SEALED")
        self.assertEqual(campaign_objective_line(g2),
                         "MAIN ENGINEERING - THE REACTOR IS HERE")

    def test_never_shows_a_bearing(self):
        g = self._game(10)
        g.world_investigation.mark_known("SECTIONS_SEALED")
        words = set(campaign_objective_line(g).lower().replace("·", " ").split())
        for bearing in ("north", "south", "east", "west", "northeast",
                        "ne", "nw", "se", "sw", "bearing"):
            self.assertNotIn(bearing, words)

    def test_none_for_the_silence(self):
        from src.game import Apocrysis
        Apocrysis.reset_campaign_state()
        g = Apocrysis("S", seed=1, io=_IO())
        self.assertIsNone(campaign_objective_line(g))
        Apocrysis.reset_campaign_state()


class TestLevelTypeSchedule(unittest.TestCase):
    def tearDown(self):
        from src.game import Apocrysis
        Apocrysis.reset_campaign_state()

    def test_schedule_has_one_entry_per_pre_finale_level(self):
        self.assertEqual(len(WAKE.manifest.level_types), 24)  # 25 - finale

    def test_silence_has_no_schedule_every_level_is_fact(self):
        self.assertEqual(SILENCE.manifest.level_types, ())
        for exp in (0, 5, 12, 24):
            self.assertEqual(level_type_for(exp, SILENCE), "fact")
            self.assertFalse(is_section_transit_level(exp, SILENCE))

    def test_encounter_levels_still_carry_a_fact(self):
        # encounter beats aren't no-mystery crossings (yet) - the DAG
        # needs the slot. Derived from the manifest so a schedule tweak
        # doesn't silently break the invariant.
        for i, t in enumerate(WAKE.manifest.level_types):
            if t == "encounter":
                self.assertEqual(level_type_for(i, WAKE), "encounter")
                self.assertFalse(is_section_transit_level(i, WAKE))

    def test_traversal_quiet_discovery_are_no_mystery_crossings(self):
        crossings = [i for i, t in enumerate(WAKE.manifest.level_types)
                     if t in ("traversal", "discovery", "quiet")]
        self.assertTrue(crossings)
        for exp in crossings:
            self.assertTrue(is_section_transit_level(exp, WAKE),
                            f"exp {exp} should be a section crossing")

    def test_finale_level_is_never_a_crossing(self):
        self.assertFalse(is_section_transit_level(24, WAKE))

    def test_a_scheduled_crossing_builds_no_mystery_and_a_reachable_exit(self):
        from src.game import Apocrysis
        Apocrysis.reset_campaign_state()
        g = Apocrysis("W", seed=11, io=_IO(), world="the_wake",
                      expeditions_completed=6)   # L7 traversal (a crossing)
        self.assertIsNone(g.mystery)
        self.assertIsNotNone(g.section_exit)
        ex, ey = g.section_exit
        self.assertEqual(g.map[ey][ex].get("escape_gap"), True)
        # reachable from spawn over passable terrain
        from src.escape import _reachable_from
        self.assertIn(g.section_exit, _reachable_from(g, g.current_position))

    def test_reaching_the_exit_finishes_the_expedition(self):
        from src.game import Apocrysis
        Apocrysis.reset_campaign_state()
        g = Apocrysis("W", seed=11, io=_IO(), world="the_wake",
                      expeditions_completed=6)
        ex, ey = g.section_exit
        # step in from the wall, then walk back onto the gap
        for (nx, ny, d) in ((ex + 1, ey, "w"), (ex - 1, ey, "e"),
                            (ex, ey + 1, "n"), (ex, ey - 1, "s")):
            if 0 <= nx < g.map_w and 0 <= ny < g.map_h:
                c = g.map[ny][nx]
                if isinstance(c, dict) and c.get("terrain") not in ("mountain", "river"):
                    g.current_position = (nx, ny)
                    g.move_and_search(d)
                    break
        self.assertTrue(getattr(g, "won", False))
        self.assertEqual(g.expeditions_completed, 7)
        Apocrysis.reset_campaign_state()

    def test_section_exit_round_trips_through_save_load(self):
        from src.game import Apocrysis
        Apocrysis.reset_campaign_state()
        import tempfile, os
        g = Apocrysis("W", seed=11, io=_IO(), world="the_wake",
                      expeditions_completed=6)
        sx = g.section_exit
        with tempfile.TemporaryDirectory() as d:
            pf = os.path.join(d, "s.json")
            g.save_game(pf)
            g2 = Apocrysis.load_game(pf)
        self.assertEqual(g2.section_exit, sx)
        self.assertIsNone(g2.mystery)
        Apocrysis.reset_campaign_state()


class TestEncounterBeats(unittest.TestCase):
    def tearDown(self):
        from src.game import Apocrysis
        Apocrysis.reset_campaign_state()

    def _enc_exp(self):
        return next(i for i, t in enumerate(WAKE.manifest.level_types)
                    if t == "encounter")

    def test_encounter_is_a_crossing_that_carries_a_fact(self):
        exp = self._enc_exp()
        self.assertTrue(is_encounter_level(exp, WAKE))
        self.assertFalse(is_section_transit_level(exp, WAKE))   # not a plain one
        self.assertTrue(crosses_section(exp, WAKE))
        self.assertFalse(is_encounter_level(exp, SILENCE))

    def test_encounter_level_builds_no_mystery_but_a_beat_on_the_path(self):
        from src.game import Apocrysis
        from src.worldgen.reachable import shortest_path
        exp = self._enc_exp()
        Apocrysis.reset_campaign_state()
        g = Apocrysis("W", seed=exp + 3, io=_IO(), world="the_wake",
                      expeditions_completed=exp)
        self.assertIsNone(g.mystery)
        self.assertIsNotNone(g.section_exit)
        self.assertIsNotNone(g._encounter_beat)
        self.assertIsNotNone(g._encounter_fact)
        path = shortest_path(g.map, g.map_size, g.current_position, g.section_exit)
        self.assertIn(g._encounter_beat, path,
                      "the beat must sit on the spawn->exit walk")

    def test_cannot_leave_the_section_without_passing_the_beat(self):
        from src.game import Apocrysis
        exp = self._enc_exp()
        Apocrysis.reset_campaign_state()
        g = Apocrysis("W", seed=exp + 3, io=_IO(), world="the_wake",
                      expeditions_completed=exp)
        # teleport straight to the exit without touching the beat
        g.current_position = g.section_exit
        g.io.log.clear()
        g.move_and_search("z")   # any no-op move re-runs the arrival check
        self.assertFalse(getattr(g, "won", False))
        blob = " ".join(g.io.log).lower()
        self.assertIn("haven't reached", blob)

    def test_the_fact_lands_on_completion_not_on_beat_touch(self):
        # a bot that sees the beat then dies must NOT burn the milestone
        from src.game import Apocrysis
        exp = self._enc_exp()
        Apocrysis.reset_campaign_state()
        g = Apocrysis("W", seed=exp + 3, io=_IO(), world="the_wake",
                      expeditions_completed=exp)
        fid = g._encounter_fact
        g.current_position = g._encounter_beat
        g.move_and_search("z")
        self.assertTrue(g._encounter_beat_seen)
        self.assertFalse(g.world_investigation.is_known(fid),
                         "fact must not be established just by reaching the beat")
        g._establish_encounter_fact()
        self.assertTrue(g.world_investigation.is_known(fid))
        Apocrysis.reset_campaign_state()


class TestChaptersRespacedToSectionStarts(unittest.TestCase):
    def test_chapter_bounds_align_with_section_boundaries(self):
        # each chapter intro should fire on entering a section (§5.4)
        secs = set(WAKE.manifest.section_bounds)
        for b in WAKE.manifest.chapter_bounds:
            self.assertIn(b, secs, f"chapter boundary {b} is mid-section")

    def test_still_five_chapters(self):
        self.assertEqual(len(WAKE.manifest.chapter_bounds), 5)
        self.assertEqual(len(WAKE.manifest.chapter_titles), 5)


class TestGeneratorHonoursTheSectionArchetype(unittest.TestCase):
    def test_wake_map_archetype_is_section_driven_not_random(self):
        from src.game import Apocrysis
        # section 6 (exp 22-24) = "engineering"; section 0 = "habitation"
        for exp, want in ((0, "habitation"), (22, "engineering"),
                          (19, "open_decks")):
            Apocrysis.reset_campaign_state()
            g = Apocrysis("W", seed=exp + 1, io=_IO(), world="the_wake",
                          expeditions_completed=exp)
            self.assertEqual(g.map_archetype, want)
        Apocrysis.reset_campaign_state()

    def test_silence_archetype_still_comes_from_the_rng_roll(self):
        # byte-identity guard: the roll is consumed and NOT overridden
        from src.game import Apocrysis
        Apocrysis.reset_campaign_state()
        g1 = Apocrysis("S", seed=42, io=_IO())
        Apocrysis.reset_campaign_state()
        g2 = Apocrysis("S", seed=42, io=_IO())
        self.assertEqual(g1.map_archetype, g2.map_archetype)
        self.assertIn(g1.map_archetype, SILENCE.map_archetypes)
        Apocrysis.reset_campaign_state()


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


if __name__ == "__main__":
    unittest.main()
