# Phase F §F.10 - equipment vocabulary is world-owned.
#
# Engine owns the GRAMMAR (bands, min_expedition, melee/ranged split,
# drop RNG, ingredient costs). A world owns only the names + stat
# values. World 3 must add its loot in worlds/<w>/loot.py and NOWHERE
# in the engine.

import unittest
from unittest.mock import patch

from src import loot
from src.game import Apocrysis
from src.worlds.base import World, WorldLoot
from src.worlds import get_world


class TestLootSeam(unittest.TestCase):

    def test_default_world_tables_are_unchanged(self):
        # The Silence's tables are the historical constants, verbatim.
        from src.constants import LOOT_WEAPON_TABLE, ARMOR_TABLE
        w = get_world("silence")
        self.assertIs(loot.weapon_table(w), LOOT_WEAPON_TABLE)
        self.assertIs(loot.armor_table(w), ARMOR_TABLE)
        self.assertEqual(list(loot.weapon_table(w))[:2],
                         ["Rusty Dagger", "Chipped Sword"])

    def test_a_world_with_no_loot_falls_back_to_the_silence(self):
        bare = World(id="bare", name="Bare", description="",
                     terrain_symbols={}, terrain_legend="", map_archetypes={})
        self.assertEqual(loot.weapon_table(bare), loot.weapon_table(None))
        self.assertEqual(loot.armor_table(bare), loot.armor_table(None))
        self.assertEqual(len(loot.craft_recipes(bare)),
                         len(loot.craft_recipes(None)))

    def test_a_partial_loot_still_falls_back_per_field(self):
        half = World(id="half", name="Half", description="",
                     terrain_symbols={}, terrain_legend="", map_archetypes={},
                     loot=WorldLoot(weapons={"Nail": {"type": "melee", "damage": 3,
                                                      "durability": 5, "min_expedition": 0}}))
        self.assertEqual(list(loot.weapon_table(half)), ["Nail"])
        # armor / crafting / starter not authored -> Silence
        self.assertEqual(loot.armor_table(half), loot.armor_table(None))

    def test_the_wake_has_its_own_vocabulary_at_the_same_stats(self):
        import src.worlds.silence.loot as s
        import src.worlds.the_wake.loot as t

        # not a single valley name survives into The Wake's tables
        self.assertEqual(set(t.WEAPONS) & set(s.WEAPONS), set())
        self.assertEqual(set(t.ARMOR) & set(s.ARMOR),
                         {"Work Gloves", "Steel-Toe Boots"})  # genuinely ship kit too
        _sil_craft = {r["result"]["name"] for r in s.CRAFTING.values() if r.get("result")}
        _wake_craft = {r["result"]["name"] for r in t.CRAFTING.values() if r.get("result")}
        self.assertEqual(_sil_craft & _wake_craft, set())

        # band-for-band stat parity (the balance contract)
        for (sn, sv), (tn, tv) in zip(s.WEAPONS.items(), t.WEAPONS.items()):
            self.assertEqual(sv["type"], tv["type"])
            self.assertEqual(sv["damage"], tv["damage"])
            self.assertEqual(sv["durability"], tv["durability"])
            self.assertEqual(sv.get("max_ammo"), tv.get("max_ammo"))
            self.assertEqual(sv["min_expedition"], tv["min_expedition"])
        for (sn, sv), (tn, tv) in zip(s.ARMOR.items(), t.ARMOR.items()):
            self.assertEqual((sv["slot"], sv["reduction"], sv["durability"],
                              sv["min_expedition"]),
                             (tv["slot"], tv["reduction"], tv["durability"],
                              tv["min_expedition"]))
        self.assertEqual(set(s.CRAFTING), set(t.CRAFTING))   # shared keys

    def test_no_engine_module_names_a_weapon_or_recipe(self):
        # The seam: adding a world must not require editing these.
        import inspect
        import src.mixins.world_mixin as wm
        import src.mixins.combat_mixin as cm
        import src.mixins.actions_mixin as am
        for mod in (wm, cm, am):
            src = inspect.getsource(mod)
            for name in ("Chipped Sword", "Steel Katana", "Leather Bow",
                         "Kevlar Vest", "Riot Armor", "Kitchen Knife"):
                self.assertNotIn(name, src,
                                 f"{mod.__name__} hard-codes {name!r}")


class TestLootReachesTheGame(unittest.TestCase):

    def _forced_weapon_find(self, world_id):
        with patch("builtins.print"):
            g = Apocrysis("L", map_size=12, seed=3, world=world_id,
                          expeditions_completed=8)
        x, y = g.current_position
        g.map[y][x] = {"terrain": "building", "content": "B"}
        got = []
        real_add = g.backpack.add_weapon
        g.backpack.add_weapon = lambda w: (got.append(w.name), real_add(w))[1]

        calls = {"n": 0}

        def choice(seq):
            calls["n"] += 1
            return "weapon" if calls["n"] == 1 else list(seq)[0]

        with patch.object(g.rng, "random", return_value=0.0), \
             patch.object(g.rng, "choice", side_effect=choice), \
             patch.object(g, "_maybe_surface_clue"):
            g.find_loot()
        return got

    def test_wake_loot_drops_are_wake_weapons(self):
        names = self._forced_weapon_find("the_wake")
        wake = set(__import__("src.worlds.the_wake.loot",
                              fromlist=["WEAPONS"]).WEAPONS)
        self.assertTrue(names, "no weapon was dropped")
        self.assertTrue(set(names) <= wake, f"non-Wake weapon dropped: {names}")

    def test_wake_crafting_produces_wake_results(self):
        with patch("builtins.print"):
            g = Apocrysis("C", map_size=12, seed=1, world="the_wake")
        r = g.crafting_recipes
        self.assertEqual(r["steel_sword"]["result_name"], "Plasma Cutter")
        self.assertEqual(r["apex_blade"]["result_name"], "Control Rod")
        made = r["combat_knife"]["result"]()
        self.assertEqual(made.name, "Bench Knife")

    def test_wake_survivor_starts_with_a_ship_tool(self):
        with patch("builtins.print"):
            g = Apocrysis("Start", map_size=12, seed=1, world="the_wake")
        from src.worlds.the_wake.loot import STARTER
        self.assertIn(g.equipped_weapon.name, STARTER["variants"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
