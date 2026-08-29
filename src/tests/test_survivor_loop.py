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

        # survivor reset
        self.assertEqual(heir.name, "Ada")
        self.assertEqual(heir.level, 1)
        self.assertEqual(heir.xp, 0)
        self.assertEqual(heir.health, heir.max_health)
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
        self.assertEqual(flat["level"], 1)                   # survivor

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

    def test_effect_is_never_read_by_the_engine(self):
        # invariant 3: grep the engine for `.effect` on a lore object.
        # A weak proxy, but it catches an accidental `lore.effect ==`.
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[1]
        for path in list((root / "mixins").glob("*.py")) + [
            root / "game.py", root / "escape.py",
            root / "world_investigation.py", root / "survivor_knowledge.py",
        ]:
            text = path.read_text()
            self.assertNotIn(".effect", text,
                             f"{path.name} reads a lore .effect - it's doc text only")


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
