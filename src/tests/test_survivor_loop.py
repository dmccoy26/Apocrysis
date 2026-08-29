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


if __name__ == "__main__":
    unittest.main(verbosity=2)
