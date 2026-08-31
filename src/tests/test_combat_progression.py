"""1d combat/progression pass (docs/COMBAT_PROGRESSION_PASS.md):
- the campaign inherits a survivability FLOOR when a survivor dies
- a failed escape costs one hit, not the whole run (fast infected excepted)
- looted weapons carry real names
"""
import os
import tempfile
import unittest

import src.escape_model as escape_model
from src.game import Apocrysis
from src.zombies import ArmoredZombie, HeavyZombie, SwiftZombie, FreshZombie


class _IO:
    renders_natively = True

    def __init__(self):
        self.log = []

    def say(self, *a, **k):
        self.log.append(" ".join(str(x) for x in a))

    def ask(self, prompt=""):
        return "q"

    def ask_yes_no(self, prompt):
        return False           # choose to escape

    def ask_combat_letter(self):
        return "e"


class TestHeirAdvantage(unittest.TestCase):
    def setUp(self):
        self._orig = os.getcwd()
        os.chdir(tempfile.mkdtemp())
        Apocrysis._world_investigation = {}
        Apocrysis._survivors_lost = 1

    def tearDown(self):
        os.chdir(self._orig)

    def _heir(self, depth):
        return Apocrysis.persist_new_survivor("h.json", "Ada",
                                              hardcore=False, depth=depth)

    def test_deep_heir_is_not_a_level_1_screwdriver(self):
        h = self._heir(5)
        self.assertGreater(h.level, 1)
        self.assertLess(h.level, 5)                       # still short of a depth-5 survivor
        self.assertGreater(h.equipped_weapon.damage, 6)   # not the class default
        self.assertIsNotNone(h.equipped_armor.get("body"))
        self.assertEqual(h.xp, 0)                         # a fresh life

    def test_advantage_scales_with_depth_but_stays_behind(self):
        d3, d10 = self._heir(3), self._heir(10)
        self.assertLessEqual(d3.equipped_weapon.damage, d10.equipped_weapon.damage)
        self.assertLess(d10.level, 10)
        # never the very best weapon in the game before it's earned
        self.assertLess(self._heir(6).equipped_weapon.damage, 20)

    def test_shallow_heir_gets_only_a_small_floor(self):
        h = self._heir(1)
        self.assertLessEqual(h.level, 2)

    def test_heir_never_downgrades_an_inherited_weapon(self):
        # (persist_new_survivor builds a fresh survivor, so the default
        #  is the class weapon - the floor only ever raises it)
        h = self._heir(4)
        self.assertGreaterEqual(h.equipped_weapon.damage, 6)


class TestFailedEscape(unittest.TestCase):
    def setUp(self):
        self._orig = escape_model.escape_chance_for
        escape_model.escape_chance_for = lambda *a, **k: 0.0   # always fail

    def tearDown(self):
        escape_model.escape_chance_for = self._orig

    def _g(self):
        g = Apocrysis("Esc", seed=3, io=_IO())
        g.current_position = (5, 5)
        return g

    def test_failed_escape_from_a_slow_infected_costs_one_hit_not_the_run(self):
        g = self._g()
        z = ArmoredZombie()
        g._attach_infected(z, ("t", 1))
        hp0 = g.health
        g.encounter_zombie(z)
        # one grab, then out of reach - not four rounds of an Armored
        self.assertGreater(g.health, hp0 - z.attack)      # < one full hit
        self.assertGreater(g.health, 0)
        self.assertTrue(any("break away" in l.lower() for l in g.io.log))

    def test_failed_escape_from_a_fast_infected_still_means_a_fight(self):
        g = self._g()
        z = SwiftZombie()
        g._attach_infected(z, ("t", 1))
        g.encounter_zombie(z)
        self.assertTrue(any("runs you down" in l.lower() for l in g.io.log))
        self.assertTrue(any("preparing for battle" in l.lower() for l in g.io.log))

    def test_a_slow_failed_escape_sets_the_tile_cooldown(self):
        g = self._g()
        z = HeavyZombie()
        g._attach_infected(z, ("t", 1))
        g.encounter_zombie(z)
        self.assertIn((5, 5), g.tile_event_cooldowns)


class TestLootedWeaponNames(unittest.TestCase):
    def test_combat_loot_weapons_have_real_names(self):
        from src.constants import LOOT_WEAPON_TABLE
        g = Apocrysis("Loot", seed=1, io=_IO())
        g.expeditions_completed = 6
        names = set()
        for _ in range(60):
            before = len(g.backpack.weapons)
            g.handle_loot(["weapon"], None)
            if len(g.backpack.weapons) > before:
                names.add(g.backpack.weapons[-1].name)
        self.assertTrue(names)
        self.assertTrue(names <= set(LOOT_WEAPON_TABLE))   # all real
        self.assertNotIn("Gun", names)                     # not the bare category


if __name__ == "__main__":
    unittest.main()
