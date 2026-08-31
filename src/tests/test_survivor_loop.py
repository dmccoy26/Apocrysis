"""Phase B - the roguelite inheritance loop. Campaign persists across
deaths; the survivor does not. See docs/PHASE_B_SPEC.md."""
import json
import os
import tempfile
import unittest

from src.game import Apocrysis
from src.mixins.persistence_mixin import (
    _normalise_profile, _profile_flat, _profile_name,
)


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


class _Base(unittest.TestCase):
    def setUp(self):
        self._saved = (
            dict(Apocrysis._world_investigation),
            list(getattr(Apocrysis, "_survivor_knowledge", [])),
            list(Apocrysis._used_mechanisms),
        )
        Apocrysis._world_investigation = {}
        Apocrysis._survivor_knowledge = []
        Apocrysis._used_mechanisms = []
        Apocrysis._survivors_lost = 0
        Apocrysis.prize_for_next_game = False
        self._tmp = tempfile.mkdtemp()
        self._pf = os.path.join(self._tmp, "p.json")

    def tearDown(self):
        wi, sk, um = self._saved
        Apocrysis._world_investigation = wi
        Apocrysis._survivor_knowledge = sk
        Apocrysis._used_mechanisms = um


class TestProfileSplit(_Base):
    def test_file_has_two_records(self):
        g = Apocrysis("Split", seed=1, io=_IO())
        g.save_profile(self._pf)
        raw = json.load(open(self._pf))
        self.assertEqual(set(raw), {"campaign", "survivor"})
        self.assertIn("world_investigation", raw["campaign"])
        self.assertIn("survivor_knowledge", raw["campaign"])
        self.assertIn("level", raw["survivor"])
        self.assertIn("expeditions_completed", raw["campaign"])
        self.assertNotIn("expeditions_completed", raw["survivor"])

    def test_round_trips_both_records(self):
        g = Apocrysis("Rt", seed=1, io=_IO())
        g.level, g.xp, g.strength = 6, 55, 21
        g.expeditions_completed = 4
        g.world_investigation.mark_known("DIS_FEW_REMAINS")
        Apocrysis._world_investigation = g.world_investigation.snapshot()["status"]
        g.save_profile(self._pf)

        Apocrysis._world_investigation = {}
        prof = Apocrysis.load_profile(self._pf)
        h = Apocrysis("Rt", seed=2, io=_IO())
        h.apply_profile(prof)
        self.assertEqual(h.level, 6)
        self.assertEqual(h.strength, 21)
        self.assertEqual(h.expeditions_completed, 4)
        self.assertTrue(h.world_investigation.is_known("DIS_FEW_REMAINS"))

    def test_legacy_flat_profile_migrates(self):
        legacy = {
            "name": "Old", "level": 3, "xp": 12, "strength": 15,
            "hardcore": True, "expeditions_completed": 5,
            "world_investigation": {"DIS_FEW_REMAINS": "known"},
            "used_mechanisms": ["mountain_pass"],
            "backpack_food": 2, "backpack_water": 2, "backpack_medicine": 0,
            "backpack_ammo": 0, "weapons": [], "armor": [],
            "player_class": "husband", "max_xp": 100,
            "dexterity": 10, "intelligence": 10, "wisdom": 10,
        }
        with open(self._pf, "w") as f:
            json.dump(legacy, f)
        prof = Apocrysis.load_profile(self._pf)
        self.assertEqual(set(prof), {"campaign", "survivor"})
        self.assertEqual(prof["survivor"]["level"], 3)
        self.assertTrue(prof["campaign"]["hardcore"])
        self.assertEqual(prof["campaign"]["expeditions_completed"], 5)
        self.assertEqual(_profile_name(legacy), "Old")

        h = Apocrysis("Old", seed=1, io=_IO())
        h.apply_profile(prof)
        self.assertEqual(h.level, 3)
        self.assertEqual(h.expeditions_completed, 5)
        self.assertTrue(h.world_investigation.is_known("DIS_FEW_REMAINS"))

    def test_flatten_is_lossless(self):
        nested = {"campaign": {"hardcore": True, "expeditions_completed": 9},
                  "survivor": {"name": "N", "level": 2}}
        flat = _profile_flat(nested)
        self.assertEqual(flat, {"hardcore": True, "expeditions_completed": 9,
                                "name": "N", "level": 2})


class TestDeathTransition(_Base):
    def _campaign_with_progress(self):
        """A game whose campaign has real state - depth 8, a milestone
        known, some variety history."""
        Apocrysis._world_investigation = {
            "DIS_FEW_REMAINS": "known", "DIS_MOVED_TOGETHER": "known",
            "DIS_ROUTES_PREPARED": "known", "DIS_ORGANISED": "known",
        }
        Apocrysis._used_mechanisms = ["mountain_pass", "evac_corridor"]
        Apocrysis._survivor_knowledge = ["BLUE_SIGNS"]
        g = Apocrysis("Founder", seed=1, io=_IO())
        g.expeditions_completed = 8
        g.level, g.xp = 6, 90
        return g

    def test_heir_resets_survivor_keeps_campaign(self):
        dying = self._campaign_with_progress()
        Apocrysis._survivors_lost = 1
        heir = Apocrysis.persist_new_survivor(
            self._pf, "Ada", hardcore=False, depth=dying.expeditions_completed)

        # survivor reset - a fresh life (xp 0, full health, new name),
        # but 1d gives the CAMPAIGN a survivability floor: the heir has a
        # modest level floor and real gear, still well short of a
        # survivor who actually reached depth 8.
        self.assertEqual(heir.name, "Ada")
        self.assertEqual(heir.xp, 0)
        self.assertGreater(heir.level, 1)                        # floor
        self.assertLess(heir.level, 8)                           # not a depth-8 character
        self.assertEqual(heir.health, heir.max_health)
        self.assertGreater(getattr(heir.equipped_weapon, "damage", 0), 6)  # not the screwdriver
        # campaign kept
        self.assertEqual(heir.expeditions_completed, 8)          # depth, not survivor
        self.assertTrue(heir.world_investigation.is_known("DIS_ORGANISED"))
        self.assertEqual(len(heir.world_investigation.milestones_known()), 1)

    def test_campaign_record_is_byte_identical_across_the_death(self):
        dying = self._campaign_with_progress()
        dying.save_profile(self._pf)
        before = json.load(open(self._pf))["campaign"]

        Apocrysis.persist_new_survivor(
            self._pf, "Cole", hardcore=False, depth=dying.expeditions_completed)
        after = json.load(open(self._pf))["campaign"]

        # depth and the rest are untouched by the death (invariant 1)
        self.assertEqual(before["world_investigation"], after["world_investigation"])
        self.assertEqual(before["used_mechanisms"], after["used_mechanisms"])
        self.assertEqual(before["expeditions_completed"], after["expeditions_completed"])
        self.assertEqual(before["survivor_knowledge"], after["survivor_knowledge"])

    def test_depth_is_not_survivor_progress(self):
        self._campaign_with_progress()
        heir = Apocrysis.persist_new_survivor(self._pf, "Iris", hardcore=False, depth=8)
        # reload as the real lifecycle would
        prof = Apocrysis.load_profile(self._pf)
        flat = _profile_flat(prof)
        self.assertEqual(flat["expeditions_completed"], 8)   # campaign
        self.assertLess(flat["level"], 8)                    # survivor level != depth

    def test_survivor_name_cycles_then_numbers(self):
        from src.cli import _next_survivor_name, _SURVIVOR_POOL
        self.assertEqual(_next_survivor_name(1), _SURVIVOR_POOL[0])
        self.assertEqual(_next_survivor_name(len(_SURVIVOR_POOL)), _SURVIVOR_POOL[-1])
        wrapped = _next_survivor_name(len(_SURVIVOR_POOL) + 1)
        self.assertTrue(wrapped.startswith(_SURVIVOR_POOL[0]) and "(2)" in wrapped)


class TestSurvivorLoreData(unittest.TestCase):
    def test_shipped_lore_is_well_formed(self):
        from src.worlds.silence import SILENCE
        from src.worlds.silence.lore import SURVIVOR_LORE_BY_ID
        ids = [lo.id for lo in SILENCE.survivor_lore]
        self.assertEqual(sorted(ids),
                         ["BLUE_SIGNS", "COMMAND_FREQUENCY", "RESERVOIR_CONTROLS"])
        self.assertLessEqual(len(SILENCE.survivor_lore), 5)   # hard cap
        for lo in SILENCE.survivor_lore:
            self.assertTrue(lo.blurb and lo.effect and lo.learned_when)
            self.assertIs(SURVIVOR_LORE_BY_ID[lo.id], lo)

    def test_effect_is_never_interpreted_by_the_engine(self):
        # invariant 3: `effect` is player-facing / doc text. The engine
        # may DISPLAY it (announce_event / io.say) but must never branch
        # or compare on it. Grep for the interpretation shapes.
        import pathlib
        import re
        root = pathlib.Path(__file__).resolve().parents[1]
        bad = re.compile(
            r"\.effect\s*(==|!=|\bin\b|\band\b|\bor\b)"
            r"|if\s+[\w.]*\.effect"
            r"|\.effect\.(startswith|endswith|split|lower|upper)"
        )
        for path in list((root / "mixins").glob("*.py")) + [
            root / "game.py", root / "escape.py",
            root / "world_investigation.py", root / "survivor_knowledge.py",
        ]:
            hits = bad.findall(path.read_text())
            self.assertEqual(hits, [], f"{path.name} interprets a lore .effect: {hits}")


class TestSurvivorKnowledgePersistence(_Base):
    def test_learned_lore_survives_a_death(self):
        Apocrysis._survivor_knowledge = []
        g = Apocrysis("Founder", seed=1, io=_IO())
        self.assertTrue(g.survivor_knowledge.learn("BLUE_SIGNS"))
        Apocrysis._survivor_knowledge = g.survivor_knowledge.snapshot()
        g.expeditions_completed = 3

        Apocrysis._survivors_lost = 1
        heir = Apocrysis.persist_new_survivor(self._pf, "Ada", hardcore=False, depth=3)
        self.assertTrue(heir.survivor_knowledge.has("BLUE_SIGNS"))

        # and through a full profile round-trip
        prof = Apocrysis.load_profile(self._pf)
        self.assertIn("BLUE_SIGNS", _profile_flat(prof)["survivor_knowledge"])

    def test_learn_is_idempotent(self):
        k = Apocrysis("K", seed=1, io=_IO()).survivor_knowledge
        self.assertTrue(k.learn("BLUE_SIGNS"))
        self.assertFalse(k.learn("BLUE_SIGNS"))


def _solve(game, mech):
    """Force `game` onto a fresh `mech` mystery and solve it."""
    from src.escape import MECHANISMS, build_mystery
    Apocrysis._used_mechanisms = [k for k in MECHANISMS if k != mech]
    Apocrysis._last_family = None
    Apocrysis._recent_mechanisms = []
    Apocrysis._recent_signatures = []
    Apocrysis._world_investigation = {f.id: "known"
                                      for f in __import__(
                                          "src.worlds.silence.truth",
                                          fromlist=["WORLD_FACTS"]).WORLD_FACTS}
    m = build_mystery(game)
    assert m.mechanism == mech, (m.mechanism, mech)
    game.mystery = m
    game.knowledge = m.knowledge
    for eid in list(m.knowledge.evidence):
        m.knowledge.discover(eid)
    m.obstacle_open = True
    game.current_position = m.escape_tile
    game.io.log.clear()
    game.mystery_try_escape()
    return m


class TestBlueSigns(_Base):
    def test_solving_evac_corridor_teaches_blue_signs_once(self):
        Apocrysis._survivor_knowledge = []
        g = Apocrysis("BS", seed=2, io=_IO())
        _solve(g, "evac_corridor")
        self.assertTrue(g.survivor_knowledge.has("BLUE_SIGNS"))
        self.assertIn("SURVIVORS NOW KNOW", "\n".join(g.io.log))
        self.assertEqual("\n".join(g.io.log).count("SURVIVORS NOW KNOW"), 1)

        # a second evac_corridor solve does not re-announce
        g2 = Apocrysis("BS2", seed=3, io=_IO())
        Apocrysis._survivor_knowledge = g.survivor_knowledge.snapshot()
        g2.survivor_knowledge.restore(Apocrysis._survivor_knowledge)
        _solve(g2, "evac_corridor")
        self.assertNotIn("SURVIVORS NOW KNOW", "\n".join(g2.io.log))

    def test_blue_signs_marks_the_route_site_from_turn_one(self):
        from src.escape import MECHANISMS, build_mystery
        from src.worlds.silence.truth import WORLD_FACTS

        def _fresh_evac(sk):
            Apocrysis._used_mechanisms = [k for k in MECHANISMS if k != "evac_corridor"]
            Apocrysis._last_family = None
            Apocrysis._recent_mechanisms = []
            Apocrysis._recent_signatures = []
            Apocrysis._world_investigation = {f.id: "known" for f in WORLD_FACTS}
            Apocrysis._survivor_knowledge = list(sk)
            g = Apocrysis("Route", seed=5, io=_IO())
            self.assertEqual(g.mystery.mechanism, "evac_corridor")
            return g

        without = _fresh_evac([])
        rx, ry = without.mystery.sites["route"]
        self.assertIsNone(without._mystery_site_mark(rx, ry))   # fog of war

        withl = _fresh_evac(["BLUE_SIGNS"])
        rx, ry = withl.mystery.sites["route"]
        self.assertIsNotNone(withl._mystery_site_mark(rx, ry))  # visible


class TestCommandFrequency(_Base):
    def _evac_then_radio(self):
        Apocrysis._survivor_knowledge = []
        g = Apocrysis("CF", seed=2, io=_IO())
        _solve(g, "radio_tower")
        return g

    def test_solving_radio_tower_teaches_command_frequency(self):
        g = self._evac_then_radio()
        self.assertTrue(g.survivor_knowledge.has("COMMAND_FREQUENCY"))
        self.assertIn("SURVIVORS NOW KNOW", "\n".join(g.io.log))

    def test_command_frequency_drops_one_radio_tower_search_step(self):
        from src.escape import MECHANISMS, build_mystery
        from src.worlds.silence.truth import WORLD_FACTS

        def _radio(sk):
            Apocrysis._used_mechanisms = [k for k in MECHANISMS if k != "radio_tower"]
            Apocrysis._last_family = None
            Apocrysis._recent_mechanisms = []
            Apocrysis._recent_signatures = []
            Apocrysis._world_investigation = {f.id: "known" for f in WORLD_FACTS}
            Apocrysis._survivor_knowledge = list(sk)
            g = Apocrysis("R", seed=6, io=_IO())
            self.assertEqual(g.mystery.mechanism, "radio_tower")
            return g.mystery.knowledge

        def _searchables(k):
            return sorted(e.id for e in k.evidence.values() if e.method == "search")

        without = _searchables(_radio([]))
        withl = _searchables(_radio(["COMMAND_FREQUENCY"]))
        self.assertIn("E_route_a", without)
        self.assertNotIn("E_route_a", withl)
        # exactly one fewer, and it's E_route_a - nothing else moved
        self.assertEqual(set(without) - set(withl), {"E_route_a"})
        self.assertEqual(set(withl) - set(without), set())


class TestReservoirControls(_Base):
    def _dam(self, sk):
        from src.escape import MECHANISMS
        from src.worlds.silence.truth import WORLD_FACTS
        Apocrysis._used_mechanisms = [k for k in MECHANISMS if k != "dam_valves"]
        Apocrysis._last_family = None
        Apocrysis._recent_mechanisms = []
        Apocrysis._recent_signatures = []
        Apocrysis._world_investigation = {f.id: "known" for f in WORLD_FACTS}
        Apocrysis._survivor_knowledge = list(sk)
        g = Apocrysis("D", seed=8, io=_IO())
        self.assertEqual(g.mystery.mechanism, "dam_valves")
        return g

    def test_solving_dam_valves_teaches_reservoir_controls(self):
        Apocrysis._survivor_knowledge = []
        g = Apocrysis("RC", seed=2, io=_IO())
        _solve(g, "dam_valves")
        self.assertTrue(g.survivor_knowledge.has("RESERVOIR_CONTROLS"))

    def test_reservoir_controls_names_the_right_control_but_changes_nothing_mechanical(self):
        without = self._dam([])
        withl = self._dam(["RESERVOIR_CONTROLS"])

        # same number of controls, same correct control, same open path
        self.assertEqual(len(withl.mystery.controls), len(without.mystery.controls))
        self.assertEqual(withl.mystery.controls, without.mystery.controls)

        # the control-room evidence now names the correct control
        e = withl.mystery.knowledge.evidence["E_require_b"]
        self.assertIn(withl.mystery.correct_control, e.text)
        self.assertNotIn("but which", e.text)
        # without the lore it does not
        e0 = without.mystery.knowledge.evidence["E_require_b"]
        self.assertIn("but which", e0.text)

        # the searchable evidence set is unchanged (no step removed)
        def _searchables(k):
            return sorted(x.id for x in k.evidence.values() if x.method == "search")
        self.assertEqual(_searchables(withl.mystery.knowledge),
                         _searchables(without.mystery.knowledge))


class TestSurfacing(_Base):
    def test_wi_screen_footer_lists_learned_lore_blurbs(self):
        Apocrysis._survivor_knowledge = []
        g = Apocrysis("Surf", seed=2, io=_IO())
        _solve(g, "evac_corridor")
        g.io.log.clear()
        g.world_investigation_screen()
        out = "\n".join(g.io.log)
        self.assertIn("WHAT SURVIVORS HAVE LEARNED", out)
        self.assertIn("blue signs", out)          # BLUE_SIGNS blurb
        # never the internal id
        self.assertNotIn("BLUE_SIGNS", out)

    def test_retrospective_notes_a_lore_learned_this_run(self):
        Apocrysis._survivor_knowledge = []
        g = Apocrysis("Retro", seed=2, io=_IO())
        _solve(g, "evac_corridor")
        g.io.log.clear()
        g._render_end_screen()
        out = "\n".join(g.io.log)
        self.assertIn("survivors after you will carry this", out)

    def test_tui_strip_shows_a_lore_count(self):
        from src.tui import _investigation_strip
        Apocrysis._survivor_knowledge = []
        g = Apocrysis("Strip", seed=2, io=_IO())
        self.assertNotIn("●", "\n".join(_investigation_strip(g)))
        g.survivor_knowledge.learn("BLUE_SIGNS")
        self.assertIn("● 1", "\n".join(_investigation_strip(g)))


class TestLegibilityNotPower(_Base):
    """Invariant 4 - a learned lesson changes what's surfaced, nothing
    mechanical. Two otherwise-identical games, one with the lore."""

    def _pair(self, lore_id, mech):
        from src.escape import MECHANISMS

        def _mk(sk):
            Apocrysis._used_mechanisms = [k for k in MECHANISMS if k != mech]
            Apocrysis._last_family = None
            Apocrysis._recent_mechanisms = []
            Apocrysis._recent_signatures = []
            Apocrysis._world_investigation = {}
            Apocrysis._survivor_knowledge = list(sk)
            return Apocrysis("Pair", seed=9, io=_IO())

        return _mk([]), _mk([lore_id])

    def _assert_mechanically_identical(self, a, b):
        for attr in ("strength", "dexterity", "intelligence", "wisdom",
                     "max_health", "health", "level", "xp"):
            self.assertEqual(getattr(a, attr), getattr(b, attr), attr)
        self.assertEqual(a.backpack.food, b.backpack.food)
        self.assertEqual(a.backpack.water, b.backpack.water)
        wa = a.equipped_weapon
        wb = b.equipped_weapon
        self.assertEqual(type(wa), type(wb))
        self.assertEqual(getattr(wa, "damage", None), getattr(wb, "damage", None))
        # same zombie roll over a fixed RNG
        import random
        a.rng = random.Random(123)
        b.rng = random.Random(123)
        za = [type(a._select_zombie_for_encounter()).__name__ for _ in range(20)]
        b.rng = random.Random(123)
        zb = [type(b._select_zombie_for_encounter()).__name__ for _ in range(20)]
        self.assertEqual(za, zb)

    def test_blue_signs_is_legibility_not_power(self):
        a, b = self._pair("BLUE_SIGNS", "evac_corridor")
        self._assert_mechanically_identical(a, b)

    def test_command_frequency_is_legibility_not_power(self):
        a, b = self._pair("COMMAND_FREQUENCY", "radio_tower")
        self._assert_mechanically_identical(a, b)

    def test_reservoir_controls_is_legibility_not_power(self):
        a, b = self._pair("RESERVOIR_CONTROLS", "dam_valves")
        self._assert_mechanically_identical(a, b)


class TestPhaseBExitCondition(_Base):
    """A survivor dies. The next one starts weak, with a new name - but
    knows what the last one figured out, carries a concrete survival
    lesson, and is dropped at the depth the campaign reached."""

    def test_the_whole_loop(self):
        from src.worlds.silence.truth import WORLD_FACTS

        # a founder who has got somewhere: depth 6, half the CH1 chain
        # understood, and who solved an evac_corridor (BLUE_SIGNS).
        Apocrysis._survivor_knowledge = []
        Apocrysis._world_investigation = {}
        founder = Apocrysis("Founder", seed=2, io=_IO())
        founder.level, founder.xp = 5, 80
        founder.expeditions_completed = 6
        founder.world_investigation.mark_known("DIS_FEW_REMAINS")
        founder.world_investigation.mark_known("DIS_MOVED_TOGETHER")
        Apocrysis._world_investigation = founder.world_investigation.snapshot()["status"]
        _solve(founder, "evac_corridor")   # teaches BLUE_SIGNS
        # _solve marks every fact known - roll the campaign back to the
        # founder's real progress + keep the lore it just taught
        Apocrysis._world_investigation = {
            "DIS_FEW_REMAINS": "known", "DIS_MOVED_TOGETHER": "known"}
        self.assertTrue(founder.survivor_knowledge.has("BLUE_SIGNS"))
        Apocrysis._survivor_knowledge = founder.survivor_knowledge.snapshot()

        # --- the founder dies at depth 6 ---
        from src.cli import _next_survivor_name
        Apocrysis._survivors_lost = 1
        heir = Apocrysis.persist_new_survivor(
            self._pf, _next_survivor_name(1), hardcore=False, depth=6)

        # a fresh life (xp 0, new name) with the campaign's survivability
        # floor - weaker than a depth-6 survivor, stronger than L1
        self.assertEqual(heir.xp, 0)
        self.assertNotEqual(heir.name, "Founder")
        self.assertGreater(heir.level, 1)
        self.assertLess(heir.level, 6)
        self.assertEqual(heir.health, heir.max_health)
        # knows the campaign
        self.assertTrue(heir.world_investigation.is_known("DIS_FEW_REMAINS"))
        self.assertTrue(heir.world_investigation.is_known("DIS_MOVED_TOGETHER"))
        # carries the lesson
        self.assertTrue(heir.survivor_knowledge.has("BLUE_SIGNS"))
        # dropped at the campaign's depth
        self.assertEqual(heir.expeditions_completed, 6)
        # and the campaign record on disk is intact
        flat = _profile_flat(Apocrysis.load_profile(self._pf))
        self.assertEqual(flat["expeditions_completed"], 6)
        self.assertIn("BLUE_SIGNS", flat["survivor_knowledge"])
        self.assertEqual(flat["world_investigation"],
                         {"DIS_FEW_REMAINS": "known", "DIS_MOVED_TOGETHER": "known"})
        self.assertEqual(flat["survivors_lost"], 1)

        # heir's next expedition picks up the investigation where it stands
        self.assertEqual(heir.world_investigation.next_target(), "DIS_ROUTES_PREPARED")
        self.assertEqual(heir.mystery.world_fact_id, "DIS_ROUTES_PREPARED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
