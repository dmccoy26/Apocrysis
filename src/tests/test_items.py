import asyncio
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from src.constants import TERRAIN_SYMBOLS
from src.game import Apocrysis
from src.items import Backpack, MeleeWeapon, RangedWeapon, Armor
from src.mixins.persistence_mixin import profile_filename_for_name
from src.text_utils import _visible_len, _display_ljust
from src.zombies import (
    FreshZombie, RegularZombie, HeavyZombie,
    SwiftZombie, ToxicZombie, ArmoredZombie,
)



class TestBackpack(unittest.TestCase):
    def setUp(self):
        self.backpack = Backpack()

    def test_add_consumables(self):
        for item in ["food", "water", "medicine", "ammo"]:
            self.backpack.add_item(item)
        self.assertEqual(self.backpack.food, 1)
        self.assertEqual(self.backpack.water, 1)
        self.assertEqual(self.backpack.medicine, 1)
        self.assertEqual(self.backpack.ammo, 1)

    def test_add_weapon(self):
        weapon = MeleeWeapon("Sword", 10, 50)
        self.backpack.add_item(weapon)
        self.assertIn(weapon, self.backpack.weapons)

    def test_add_unrecognized_string_is_ignored(self):
        # ConsumableType lookup (add_item's enum.Enum-based dispatch)
        # should silently ignore anything that isn't a real
        # consumable name, not raise and not increment anything.
        self.backpack.add_item("junk")
        self.assertEqual(self.backpack.food, 0)
        self.assertEqual(len(self.backpack.items), 0)

    def test_add_non_consumable_non_weapon_goes_to_items(self):
        self.backpack.add_item(42)
        self.assertIn(42, self.backpack.items)

    def test_properties_are_read_write(self):
        # food/water/medicine/ammo are properties backed by a
        # Counter - += and -= must keep working, not just direct
        # reads, since the whole rest of the file uses that shape.
        self.backpack.food += 3
        self.assertEqual(self.backpack.food, 3)
        self.backpack.food -= 1
        self.assertEqual(self.backpack.food, 2)


class TestWeapons(unittest.TestCase):
    def test_melee_durability_and_damage(self):
        weapon = MeleeWeapon("Axe", 8, 3)
        self.assertEqual(weapon.use(), 8)
        self.assertEqual(weapon.durability, 2)

        for _ in range(3):
            weapon.use()
        self.assertEqual(weapon.durability, 0)

        with patch("builtins.print"):
            self.assertEqual(weapon.use(), 0)

    def test_ranged_ammo_and_durability_both_gate_use(self):
        weapon = RangedWeapon("Bow", 12, max_ammo=5, durability=2)
        self.assertEqual(weapon.use(), 12)
        self.assertEqual(weapon.ammo, 4)
        self.assertEqual(weapon.durability, 1)

        self.assertEqual(weapon.use(), 12)
        self.assertEqual(weapon.durability, 0)

        # Durability exhausted - further use() must report 0 damage,
        # even though ammo remains.
        with patch("builtins.print"):
            self.assertEqual(weapon.use(), 0)

    def test_ranged_fire_reduces_ammo(self):
        weapon = RangedWeapon("Bow", 12, 5)
        initial_ammo = weapon.ammo
        with patch("builtins.print"):
            weapon.fire()
        self.assertEqual(weapon.ammo, initial_ammo - 1)

    def test_ranged_reload_caps_at_max_ammo(self):
        weapon = RangedWeapon("Bow", 12, max_ammo=5)
        weapon.ammo = 0
        weapon.reload(999)
        self.assertEqual(weapon.ammo, 5)

    def test_melee_str_shows_durability_not_just_damage(self):
        # Real gap found live: a player had no way to compare two
        # melee weapons' durability without reading source.
        weapon = MeleeWeapon("Rusty Dagger", 8, 40)
        text = str(weapon)
        self.assertIn("Damage: 8", text)
        self.assertIn("Durability: 40/40", text)

    def test_ranged_str_shows_durability_alongside_ammo(self):
        weapon = RangedWeapon("Broken Rifle", 10, max_ammo=5, durability=15)
        text = str(weapon)
        self.assertIn("Ammo: 5/5", text)
        self.assertIn("Durability: 15/15", text)


class TestNumberedGear(unittest.TestCase):
    def test_slot_numbers_track_contiguous_runs(self):
        from src.items import format_weapon_list
        ws = [MeleeWeapon("Knife", 6, 40), MeleeWeapon("Sword", 15, 40),
              RangedWeapon("Gun", 20, 5), MeleeWeapon("Sword", 15, 40),
              RangedWeapon("Gun", 20, 5), RangedWeapon("Gun", 20, 5)]
        lines = format_weapon_list(ws)
        self.assertTrue(lines[0].startswith("[1] "))
        self.assertTrue(lines[1].startswith("[2] "))
        self.assertTrue(lines[2].startswith("[3] "))    # a Gun, on its own
        self.assertTrue(lines[3].startswith("[4] "))
        self.assertTrue(lines[4].startswith("[5-6] "))   # the last two Guns
        self.assertIn("x2", lines[4])

    def test_gear_arg_resolves_number_or_name(self):
        io_log = []
        fake_io = type("_", (), {
            "say": lambda s, *a: io_log.append(" ".join(map(str, a))),
            "renders_natively": True})()
        with patch("builtins.print"):
            g = Apocrysis("N", map_size=8, seed=1, io=fake_io)
        g.backpack.weapons = [MeleeWeapon("Axe", 8, 40),
                              RangedWeapon("Gun", 20, 5),
                              MeleeWeapon("Machete", 12, 40)]
        self.assertEqual(g._gear_arg("2", "weapon"), "Gun")
        self.assertEqual(g._gear_arg("Machete", "weapon"), "Machete")
        io_log.clear()
        self.assertIsNone(g._gear_arg("9", "weapon"))
        self.assertTrue(any("No weapon [9]" in m for m in io_log))


class TestEmptyRangedWeaponInCombat(unittest.TestCase):
    """Playtest: the game recommended switching to a gun with no ammo,
    and an empty Broken Rifle still 'fired' for a few points of
    strength-bonus damage."""

    def setUp(self):
        with patch("builtins.print"):
            self.game = Apocrysis("GunTest", map_size=8, seed=1)
        self.game.strength = 18

    def test_empty_gun_is_not_recommended_over_a_working_melee(self):
        empty = RangedWeapon("Gun", 20, max_ammo=5)
        empty.ammo = 0
        knife = MeleeWeapon("Kitchen Knife", 6, 40)
        self.game.equipped_weapon = knife
        self.game.backpack.weapons.clear()
        self.game.backpack.weapons.append(empty)
        self.game.backpack.ammo = 0
        said = []
        self.game.io = type("IO", (), {
            "say": lambda s, t: said.append(t),
            "ask_yes_no": lambda s, *a, **k: True,
            "__getattr__": lambda s, n: (lambda *a, **k: None),
        })()
        from src.zombies import RegularZombie
        z = RegularZombie()
        z.health = 1
        self.game.encounter_zombie(z)
        joined = " ".join(said)
        self.assertNotIn("stronger than your Kitchen Knife. Flee and 'eq Gun'", joined)

    def test_firing_an_empty_gun_deals_no_strength_bonus(self):
        empty = RangedWeapon("Broken Rifle", 10, max_ammo=5)
        empty.ammo = 0
        self.game.equipped_weapon = empty
        self.game.backpack.weapons.clear()  # no spare -> no auto-swap
        dealt = []
        self.game.io = type("IO", (), {
            "say": lambda s, t: dealt.append(t),
            "ask_yes_no": lambda s, *a, **k: True,
            "__getattr__": lambda s, n: (lambda *a, **k: None),
        })()
        from src.zombies import RegularZombie
        z = RegularZombie()
        z.health = 100
        hp0 = z.health
        self.game.health = 100
        # one loop iteration's worth: run the fight, it ends when the
        # player or zombie dies - with a 2-dmg club vs 100hp the player
        # will die first, but the zombie should only ever take the
        # bare-hands 2, never str//3 (~6).
        self.game.encounter_zombie(z)
        # every hit the ZOMBIE takes from the empty rifle must be the
        # bare-hands 2 (~<=4 with condition scaling), never str//3 (~6+)
        import re
        for line in dealt:
            mm = re.search(r"[Zz]ombie takes (\d+) damage", str(line))
            if mm:
                self.assertLessEqual(int(mm.group(1)), 4, line)


class TestArmor(unittest.TestCase):
    """
    Equipment-slot investigation, multi-piece follow-up: four
    independently-equippable slots (equipped_armor is now a dict of
    ARMOR_SLOTS, not a single object/None).
    """

    def setUp(self):
        with patch("builtins.print"):
            self.game = Apocrysis("ArmorTest", map_size=8, seed=1)

    def tearDown(self):
        # Only test_apply_profile_restores_equipped_armor_across_
        # expeditions below actually writes a profile file, but
        # cleaning up here regardless keeps this self-contained rather
        # than relying on the test remembering to do it inline.
        f = profile_filename_for_name("ArmorProfileTest")
        if os.path.exists(f):
            os.remove(f)

    def test_armor_absorbs_damage_and_degrades_durability(self):
        self.game.equipped_armor["body"] = Armor("Padded Vest", 3, 2, "body")
        self.game.health = 100

        with patch("builtins.print"):
            self.game.take_damage(10)

        self.assertEqual(self.game.health, 93)  # 10 - 3 reduction
        self.assertEqual(self.game.equipped_armor["body"].durability, 1)

    def test_multiple_equipped_pieces_stack_reduction_and_all_degrade(self):
        self.game.equipped_armor["head"] = Armor("Bandana", 1, 5, "head")
        self.game.equipped_armor["body"] = Armor("Padded Vest", 3, 5, "body")
        self.game.health = 100

        with patch("builtins.print"):
            self.game.take_damage(10)

        self.assertEqual(self.game.health, 94)  # 10 - 1 - 3
        self.assertEqual(self.game.equipped_armor["head"].durability, 4)
        self.assertEqual(self.game.equipped_armor["body"].durability, 4)

    def test_broken_armor_absorbs_nothing(self):
        self.game.equipped_armor["body"] = Armor("Padded Vest", 3, 0, "body")
        self.game.health = 100

        with patch("builtins.print"):
            self.game.take_damage(10)

        self.assertEqual(self.game.health, 90)  # full damage, armor broken

    def test_no_armor_equipped_takes_full_damage(self):
        self.game.health = 100

        with patch("builtins.print"):
            self.game.take_damage(10)

        self.assertEqual(self.game.health, 90)

    def test_equip_armor_swaps_only_the_matching_slot(self):
        a1 = Armor("Padded Vest", 2, 30, "body")  # body
        a2 = Armor("Kevlar Vest", 4, 70, "body")   # also body - should swap a1 out
        a3 = Armor("Bandana", 1, 20, "head")       # different slot - unaffected
        self.game.equipped_armor["body"] = a1
        self.game.equipped_armor["head"] = a3
        self.game.backpack.armor.append(a2)

        with patch("builtins.print"):
            self.game.equip_armor("kevlar vest")

        self.assertEqual(self.game.equipped_armor["body"].name, "Kevlar Vest")
        self.assertIs(self.game.equipped_armor["head"], a3)  # untouched
        self.assertIn(a1, self.game.backpack.armor)
        self.assertNotIn(a2, self.game.backpack.armor)

    def test_drop_armor_removes_equipped_or_backpack_piece(self):
        a1 = Armor("Padded Vest", 2, 30, "body")
        self.game.equipped_armor["body"] = a1

        with patch("builtins.print"):
            self.game.drop_armor("padded vest")

        self.assertIsNone(self.game.equipped_armor["body"])

    def test_find_loot_respects_armor_carry_cap(self):
        x, y = self.game.current_position
        self.game.map[y][x]["terrain"] = "building"
        for _ in range(self.game.backpack.MAX_ARMOR):
            self.game.backpack.armor.append(Armor("Filler", 1, 1, "body"))

        with patch.object(self.game.rng, "random", return_value=0.0), \
             patch.object(self.game.rng, "choice", side_effect=["armor", "Padded Vest"]), \
             patch("builtins.print"):
            self.game.find_loot()

        self.assertEqual(len(self.game.backpack.armor), self.game.backpack.MAX_ARMOR)

    def test_armor_drops_respect_min_expedition_banding(self):
        # Riot Armor has min_expedition=6 - shouldn't be an eligible
        # option at all at expeditions_completed=0.
        with patch("builtins.print"):
            game = Apocrysis("ArmorBandTest", map_size=8, seed=1, expeditions_completed=0)
        x, y = game.current_position
        game.map[y][x]["terrain"] = "building"

        def _choice(options):
            if "armor" in options:
                return "armor"
            self.assertNotIn("Riot Armor", options)
            self.assertNotIn("Kevlar Vest", options)
            return options[0]

        with patch.object(game.rng, "random", return_value=0.0), \
             patch.object(game.rng, "choice", side_effect=_choice), \
             patch("builtins.print"):
            game.find_loot()

        self.assertEqual(len(game.backpack.armor), 1)

    def test_apply_profile_restores_equipped_armor_across_expeditions(self):
        with patch("builtins.print"):
            source = Apocrysis("ArmorProfileTest", map_size=8, seed=1)
        source.equipped_armor["body"] = Armor("Kevlar Vest", 4, 70, "body")
        source.equipped_armor["head"] = Armor("Bandana", 1, 20, "head")
        filename = profile_filename_for_name(source.name)
        source.save_profile(filename)
        profile = Apocrysis.load_profile(filename)

        with patch("builtins.print"):
            fresh = Apocrysis("ArmorProfileTest", map_size=8, seed=2)
        fresh.apply_profile(profile)

        self.assertEqual(fresh.equipped_armor["body"].name, "Kevlar Vest")
        self.assertEqual(fresh.equipped_armor["body"].damage_reduction, 4)
        self.assertEqual(fresh.equipped_armor["head"].name, "Bandana")
        self.assertIsNone(fresh.equipped_armor["hands"])
        self.assertIsNone(fresh.equipped_armor["feet"])


class TestLootWeapons(unittest.TestCase):
    """
    Real bug found live: find_loot() (world_mixin.py) used to build
    every looted weapon as MeleeWeapon(name, 10, 100) regardless of
    which name got picked - a "Rusty Dagger" and a "Steel Katana"
    were mechanically identical, and name-implied ranged weapons
    ("Broken Rifle", "Leather Bow") were built as MeleeWeapon and
    could never use ammo/reload.
    """

    @staticmethod
    def _stand_on_building(game):
        # find_loot() only rolls on building/town tiles (loot economy
        # overhaul) - these tests exercise find_loot() directly and
        # need a tile that passes that gate, regardless of where
        # generate_map()'s random spawn actually landed.
        x, y = game.current_position
        game.map[y][x]["terrain"] = "building"

    def test_loot_table_has_real_stat_variety(self):
        from src.constants import LOOT_WEAPON_TABLE
        damages = {spec["damage"] for spec in LOOT_WEAPON_TABLE.values()}
        durabilities = {spec["durability"] for spec in LOOT_WEAPON_TABLE.values()}
        self.assertGreater(len(damages), 1, "every loot weapon has the same damage")
        self.assertGreater(len(durabilities), 1, "every loot weapon has the same durability")

    def test_find_loot_does_nothing_on_open_terrain(self):
        # The actual bug this overhaul fixes: walking across plains/
        # forest used to roll loot on almost every move regardless of
        # terrain (243 ammo / 13 guns by level 6-7 in real testing).
        with patch("builtins.print"):
            game = Apocrysis("LootGateTest", map_size=8, seed=1)
        x, y = game.current_position
        game.map[y][x]["terrain"] = "plain"

        with patch.object(game.rng, "random", return_value=0.0), \
             patch.object(game.rng, "choice", side_effect=["weapon", "Broken Rifle"]), \
             patch("builtins.print"):
            game.find_loot()

        self.assertEqual(len(game.backpack.weapons), 0)

    def test_ranged_named_loot_produces_a_real_ranged_weapon(self):
        with patch("builtins.print"):
            game = Apocrysis("LootTest", map_size=8, seed=1)
        self._stand_on_building(game)

        # Force: loot occurs, loot_type is "weapon", name is "Broken
        # Rifle" - the specific case the original bug got wrong.
        # find_loot() draws from game.rng (a per-instance
        # random.Random), not the global random module, so that's
        # what needs patching to force a deterministic outcome here.
        with patch.object(game.rng, "random", return_value=0.0), \
             patch.object(game.rng, "choice", side_effect=["weapon", "Broken Rifle"]), \
             patch("builtins.print"):
            game.find_loot()

        self.assertEqual(len(game.backpack.weapons), 1)
        looted = game.backpack.weapons[0]
        self.assertIsInstance(looted, RangedWeapon)
        self.assertEqual(looted.name, "Broken Rifle")
        self.assertTrue(hasattr(looted, "ammo"))

    def test_finding_a_map_reveals_the_town_and_drops_out_of_future_loot_pools(self):
        with patch("builtins.print"):
            game = Apocrysis("LootTest", map_size=8, seed=1)
        self._stand_on_building(game)
        self.assertFalse(game.town_known)

        with patch.object(game.rng, "random", return_value=0.0), \
             patch.object(game.rng, "choice", return_value="map"), \
             patch("builtins.print"):
            game.find_loot()

        self.assertTrue(game.town_known)

        # Once already known, "map" must drop out of the loot pool -
        # nothing left to reveal, so re-rolling it would be wasted.
        def _choice_excludes_map(options):
            self.assertNotIn("map", options)
            return options[0]

        with patch.object(game.rng, "random", return_value=0.0), \
             patch.object(game.rng, "choice", side_effect=_choice_excludes_map), \
             patch("builtins.print"):
            game.find_loot()

    def test_find_loot_respects_weapon_carry_cap(self):
        # Real bug found live: find_loot() used to append straight to
        # backpack.weapons, bypassing Backpack.add_weapon()'s
        # MAX_WEAPONS cap entirely (unlike craft(), which already
        # respects it) - a player could accumulate unlimited weapons
        # just by walking around.
        with patch("builtins.print"):
            game = Apocrysis("LootCapTest", map_size=8, seed=1)
        self._stand_on_building(game)
        for _ in range(game.backpack.MAX_WEAPONS):
            game.backpack.weapons.append(MeleeWeapon("Filler", 1, 1))

        with patch.object(game.rng, "random", return_value=0.0), \
             patch.object(game.rng, "choice", side_effect=["weapon", "Broken Rifle"]), \
             patch("builtins.print"):
            game.find_loot()

        self.assertEqual(len(game.backpack.weapons), game.backpack.MAX_WEAPONS)

    def test_weapon_drops_respect_min_expedition_banding(self):
        # Steel Katana has min_expedition=6 - shouldn't be an eligible
        # option at all at expeditions_completed=0, only after enough
        # expeditions. Asserts on the actual OPTIONS list rng.choice()
        # is called with (not just its return value), so a broken
        # filter that still hands Steel Katana to choice() as an
        # option would fail this even if choice() happened not to
        # pick it.
        with patch("builtins.print"):
            game = Apocrysis("LootBandTest", map_size=8, seed=1, expeditions_completed=0)
        self._stand_on_building(game)

        def _choice(options):
            if "weapon" in options:
                return "weapon"
            self.assertNotIn("Steel Katana", options)
            self.assertNotIn("Iron Axe", options)
            self.assertNotIn("Leather Bow", options)
            return options[0]

        with patch.object(game.rng, "random", return_value=0.0), \
             patch.object(game.rng, "choice", side_effect=_choice), \
             patch("builtins.print"):
            game.find_loot()

        self.assertEqual(len(game.backpack.weapons), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
