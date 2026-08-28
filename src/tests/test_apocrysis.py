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
from src.player import PlayerClass
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


class TestZombies(unittest.TestCase):
    def test_take_damage(self):
        zombie = FreshZombie()
        initial_health = zombie.health
        zombie.take_damage(10)
        self.assertEqual(zombie.health, initial_health - 10)

    def test_loot_tables_are_distinct_per_subclass(self):
        # loot_table is a class attribute, not rebuilt per __init__ -
        # each subclass must still see its OWN list, not share one.
        self.assertEqual(FreshZombie.loot_table, ["food", "water", "medicine"])
        self.assertEqual(
            RegularZombie.loot_table,
            ["food", "water", "medicine", "weapon"],
        )
        self.assertEqual(
            HeavyZombie.loot_table,
            ["food", "water", "medicine", "weapon", "ammo"],
        )


class TestPlayerClass(unittest.TestCase):
    def test_update_status_clamps_to_0_100(self):
        pc = PlayerClass(50, 50, 50, 0, 10, 10, 10, 10, None)
        pc.update_status(health_delta=-1000, hunger_delta=1000, thirst_delta=5)
        self.assertEqual(pc.health, 0)
        self.assertEqual(pc.hunger, 100)
        self.assertEqual(pc.thirst, 55)


class TestApocrysisCore(unittest.TestCase):
    def setUp(self):
        with patch("builtins.print"):
            self.game = Apocrysis("TestPlayer", map_size=10, seed=1)

    def test_eat_restores_health_and_hunger(self):
        self.game.backpack.food = 1
        self.game.health = 50
        with patch("builtins.print"):
            self.game.eat()
        self.assertLessEqual(self.game.hunger, 100)
        self.assertLessEqual(self.game.health, 100)
        self.assertEqual(self.game.backpack.food, 0)

    def test_eat_does_nothing_without_food(self):
        self.game.backpack.food = 0
        health_before = self.game.health
        with patch("builtins.print"):
            self.game.eat()
        self.assertEqual(self.game.health, health_before)

    def test_drink_restores_thirst(self):
        self.game.backpack.water = 1
        with patch("builtins.print"):
            self.game.drink()
        self.assertLessEqual(self.game.thirst, 100)
        self.assertEqual(self.game.backpack.water, 0)

    def test_use_medicine_restores_to_max(self):
        self.game.backpack.medicine = 1
        self.game.health = 80
        with patch("builtins.print"):
            self.game.use_medicine()
        self.assertEqual(self.game.health, 100)

    def test_equip_weapon_swaps_and_returns_previous(self):
        w1 = MeleeWeapon("Knife", 5, 100)
        w2 = MeleeWeapon("Sword", 10, 100)
        self.game.equipped_weapon = w1
        self.game.backpack.weapons.append(w2)

        with patch("builtins.print"):
            self.game.equip_weapon("sword")

        self.assertEqual(self.game.equipped_weapon.name, "Sword")
        self.assertIn(w1, self.game.backpack.weapons)
        self.assertNotIn(w2, self.game.backpack.weapons)

    def test_equip_unknown_weapon_leaves_state_unchanged(self):
        current = self.game.equipped_weapon
        with patch("builtins.print"):
            self.game.equip_weapon("does not exist")
        self.assertIs(self.game.equipped_weapon, current)

    # place_zombies()/generate_map() (called from Apocrysis.__init__)
    # randomly seed zombies onto some of the map's tiles with no fixed
    # seed, so move_and_search can land on an occupied tile and
    # trigger a real encounter_zombie() -> input() prompt. Mocking
    # builtins.input (not just builtins.print, like every other test
    # here) is what makes this deterministic instead of blocking on
    # real stdin on an unlucky random draw. "n" (flee) resolves either
    # way (the 50% flee-success roll doesn't call input() again), and
    # the position assertions only depend on where move_and_search()
    # puts the player, not on the fight outcome. v3: the fight prompt
    # is y/n now (combat_mixin.py's encounter_zombie()) - anything
    # else re-prompts, so a stale "flee" mock would hang this test.
    @patch("builtins.input", return_value="n")
    @patch("builtins.print")
    def test_move_and_search_bounds(self, mock_print, mock_input):
        # v3: spawn is random (world_mixin.py's generate_map()), not
        # always the map center - assert the relative effect of a
        # move (or a same-position no-op if blocked/at an edge, both
        # real possible outcomes now that impassable terrain exists),
        # not a specific absolute starting coordinate.
        before = self.game.current_position
        self.game.move_and_search("n")
        after = self.game.current_position
        self.assertIn(after, (before, (before[0], before[1] - 1)))

        # At the map's eastern edge (x=9 on a 10-wide map) - "e" must
        # refuse to move past the boundary, position unchanged.
        self.game.current_position = (9, 5)
        self.game.move_and_search("e")
        self.assertEqual(self.game.current_position, (9, 5))

    def test_rest_recovers_fatigue(self):
        self.game.fatigue = 50
        with patch("builtins.print"):
            self.game.rest()
        self.assertLess(self.game.fatigue, 50)

    def test_rest_when_already_rested_is_a_no_op(self):
        self.game.fatigue = 0
        with patch("builtins.print"):
            self.game.rest()
        self.assertEqual(self.game.fatigue, 0)

    def test_single_level_up_below_threshold_does_not_change_class(self):
        self.game.level = 2  # below the first real threshold (5)
        starting_class = self.game.player_class
        with patch("builtins.print"):
            self.game.level_up()
        self.assertEqual(self.game.level, 3)
        self.assertEqual(self.game.player_class, starting_class)

    def test_level_up_crossing_a_tier_threshold_blends_stats(self):
        self.game.level = 4  # level_up() -> 5, TIER_LEVEL_THRESHOLDS[1]
        starting_class = self.game.player_class
        with patch("builtins.print"):
            self.game.level_up()
        self.assertEqual(self.game.level, 5)
        self.assertNotEqual(self.game.player_class, starting_class)

    def test_multi_level_xp_jump_crosses_every_threshold_in_between(self):
        # award_xp()'s while loop calls level_up() once per level -
        # a big XP gain crossing multiple tier thresholds (5, 10)
        # must apply BOTH tier blends, not just the final one.
        self.game.level = 4
        self.game.xp = 0
        self.game.max_xp = 100
        with patch("builtins.print"):
            self.game.award_xp(100000)  # max_xp grows 1.5x/level - well past level 10
        self.assertGreaterEqual(self.game.level, 10)

        # Whichever thresholds were actually crossed, player_class
        # must reflect the HIGHEST one reached (proves every
        # intermediate crossing ran in order, not just the final one
        # landing by coincidence - e.g. if only the level-10 blend had
        # run and level 15/20 were silently skipped, this would still
        # show a stale tier here).
        from src.player import TIER_LEVEL_THRESHOLDS, tier_representative
        expected_tier = max(
            i for i, t in enumerate(TIER_LEVEL_THRESHOLDS) if t <= self.game.level
        )
        self.assertEqual(self.game.player_class, tier_representative(expected_tier))


class TestTimeAndDecay(unittest.TestCase):
    def setUp(self):
        with patch("builtins.print"):
            self.game = Apocrysis("TestPlayer", map_size=10, seed=1)

    def test_update_time_advances_and_wraps(self):
        # v3: _update_time()'s default 15 minutes is scaled up by
        # DAY_COMPRESSION_SCALE (constants.py, 1440/MINUTES_PER_DAY)
        # before being added, so a normal trek crosses a meaningful
        # portion of the day/night cycle - 15 * 6.0 = 90 here.
        from src.constants import DAY_COMPRESSION_SCALE
        scaled = int(15 * DAY_COMPRESSION_SCALE)

        self.game.time_of_day = 1430
        self.game._update_time()
        self.assertEqual(self.game.time_of_day, (1430 + scaled) % 1440)  # wraps past midnight

    def test_night_reduces_visibility(self):
        self.game.time_of_day = 21 * 60  # 21:00 - within the night window
        self.game._update_time()
        self.assertTrue(self.game.is_night)
        self.assertLess(self.game.visibility_radius, 3)

    def test_day_has_full_visibility(self):
        self.game.time_of_day = 12 * 60  # noon
        self.game._update_time()
        self.assertFalse(self.game.is_night)
        self.assertEqual(self.game.visibility_radius, 3)

    def test_decay_reduces_hunger_and_thirst(self):
        self.game.hunger = 50
        self.game.thirst = 50
        self.game._apply_decay()
        self.assertLess(self.game.hunger, 50)
        self.assertLess(self.game.thirst, 50)

    def test_decay_never_goes_below_zero(self):
        self.game.hunger = 1
        self.game.thirst = 0
        self.game._apply_decay()
        self.assertGreaterEqual(self.game.hunger, 0)
        self.assertGreaterEqual(self.game.thirst, 0)

    def test_a_normal_trek_crosses_a_day_night_transition(self):
        # v3 SPRINT step 5's actual goal, verified directly rather
        # than just checking the arithmetic: before this sprint, a
        # ~10-move trek (150 real minutes at a flat 15 min/move) on a
        # 1440-minute day barely dented the clock. A normal trek must
        # now cross at least one is_night flip.
        self.game.time_of_day = 8 * 60  # 08:00, daytime
        self.game.is_night = False
        started_night = self.game.is_night

        flipped = False
        for _ in range(12):  # a normal-length trek's worth of moves
            self.game._update_time(15)  # plain-terrain move cost
            if self.game.is_night != started_night:
                flipped = True
                break

        self.assertTrue(
            flipped,
            "a 12-move trek never crossed a day/night transition",
        )

    def test_dawn_and_dusk_are_intermediate_phases(self):
        # Day/night granularity investigation: visibility now steps
        # gradually (night=1, dawn/dusk=2, day=3) instead of jumping
        # straight between 1 and 3.
        self.game.time_of_day = 7 * 60  # 07:00 - dawn window (06:00-08:00)
        self.game._update_time(0)
        self.assertEqual(self.game.day_phase, "dawn")
        self.assertEqual(self.game.visibility_radius, 2)
        self.assertFalse(self.game.is_night)

        self.game.time_of_day = 19 * 60  # 19:00 - dusk window (18:00-20:00)
        self.game._update_time(0)
        self.assertEqual(self.game.day_phase, "dusk")
        self.assertEqual(self.game.visibility_radius, 2)
        self.assertFalse(self.game.is_night)

    def test_flashlight_boosts_visibility_at_night_not_during_day(self):
        self.game.has_flashlight = True

        self.game.time_of_day = 22 * 60  # night
        self.game._update_time(0)
        self.assertEqual(self.game.day_phase, "night")
        self.assertEqual(self.game.visibility_radius, 2)  # 1 base + 1 flashlight

        self.game.time_of_day = 12 * 60  # noon - already full visibility
        self.game._update_time(0)
        self.assertEqual(self.game.day_phase, "day")
        self.assertEqual(self.game.visibility_radius, 3)  # capped, no change

    def test_find_loot_flashlight_is_one_time_and_takes_effect_immediately(self):
        x, y = self.game.current_position
        self.game.map[y][x]["terrain"] = "building"
        self.game.time_of_day = 22 * 60  # night, so the effect is visible right away
        self.game._update_time(0)
        self.assertFalse(self.game.has_flashlight)
        self.assertEqual(self.game.visibility_radius, 1)

        with patch.object(self.game.rng, "random", return_value=0.0), \
             patch.object(self.game.rng, "choice", return_value="flashlight"), \
             patch("builtins.print"):
            self.game.find_loot()

        self.assertTrue(self.game.has_flashlight)
        self.assertEqual(self.game.visibility_radius, 2)

        # Once owned, "flashlight" must drop out of the loot pool -
        # nothing left to find, so re-rolling it would be wasted.
        def _choice_excludes_flashlight(options):
            self.assertNotIn("flashlight", options)
            return options[0]

        with patch.object(self.game.rng, "random", return_value=0.0), \
             patch.object(self.game.rng, "choice", side_effect=_choice_excludes_flashlight), \
             patch("builtins.print"):
            self.game.find_loot()


class TestCrafting(unittest.TestCase):
    def setUp(self):
        with patch("builtins.print"):
            self.game = Apocrysis("TestPlayer", map_size=10, seed=1)

    def test_craft_success_consumes_ingredients_and_adds_weapon(self):
        self.game.backpack.food = 5
        self.game.backpack.weapons.append(MeleeWeapon("Scrap", 1, 1))
        weapons_before = len(self.game.backpack.weapons)

        with patch("builtins.print"):
            self.game.craft("steel_sword")

        self.assertEqual(self.game.backpack.food, 3)  # steel_sword costs 2 food
        # one weapon consumed as an ingredient, one crafted result added
        self.assertEqual(len(self.game.backpack.weapons), weapons_before)
        # endswith, not ==: a "Fine"/"Masterwork" quality roll (see
        # TestCraftingQuality below) prefixes the name.
        self.assertTrue(
            any(w.name.endswith("Steel Sword") for w in self.game.backpack.weapons)
        )

    def test_craft_insufficient_ingredients_is_refused(self):
        self.game.backpack.food = 0
        self.game.backpack.weapons.append(MeleeWeapon("Scrap", 1, 1))
        weapons_before = list(self.game.backpack.weapons)

        with patch("builtins.print"):
            self.game.craft("steel_sword")

        self.assertEqual(self.game.backpack.weapons, weapons_before)

    def test_craft_without_weapon_ingredient_is_refused(self):
        self.game.backpack.food = 5
        self.game.backpack.weapons = []

        with patch("builtins.print"):
            self.game.craft("steel_sword")

        self.assertEqual(len(self.game.backpack.weapons), 0)

    def test_craft_unknown_recipe_does_not_crash(self):
        with patch("builtins.print"):
            self.game.craft("not_a_real_recipe")  # must not raise

    def test_craft_list_does_not_crash(self):
        with patch("builtins.print"):
            self.game.craft("list")  # must not raise

    def test_craft_refuses_recipe_above_current_level(self):
        self.game.level = 1
        self.game.backpack.food = 5
        self.game.backpack.medicine = 5
        self.game.backpack.weapons = [
            MeleeWeapon("Scrap", 1, 1), MeleeWeapon("Scrap2", 1, 1),
        ]
        weapons_before = len(self.game.backpack.weapons)

        with patch("builtins.print"):
            # apex_blade requires level 18
            self.game.craft("apex_blade")

        self.assertEqual(len(self.game.backpack.weapons), weapons_before)

    def test_craft_allows_recipe_once_level_met(self):
        self.game.level = 18
        self.game.backpack.food = 5
        self.game.backpack.medicine = 5
        self.game.backpack.weapons = [
            MeleeWeapon("Scrap", 1, 1), MeleeWeapon("Scrap2", 1, 1),
        ]

        with patch("builtins.print"):
            self.game.craft("apex_blade")

        self.assertTrue(
            any(w.name.endswith("Apex Blade") for w in self.game.backpack.weapons)
        )

    def test_craft_consumes_the_full_weapon_count_a_recipe_needs(self):
        # Real bug fixed this sprint: a recipe needing 2 weapons
        # (survivor_machete) only ever popped ONE from the backpack -
        # the check only verified "not empty," and consumption always
        # ran exactly once regardless of the required count.
        self.game.level = 9
        self.game.backpack.water = 5
        self.game.backpack.weapons = [
            MeleeWeapon("Scrap", 1, 1), MeleeWeapon("Scrap2", 1, 1),
        ]

        with patch("builtins.print"):
            self.game.craft("survivor_machete")

        # Both scrap weapons consumed, one Survivor Machete added.
        self.assertEqual(len(self.game.backpack.weapons), 1)
        self.assertTrue(
            self.game.backpack.weapons[0].name.endswith("Survivor Machete")
        )

    def test_craft_refuses_when_not_enough_weapons_for_multi_weapon_recipe(self):
        self.game.level = 9
        self.game.backpack.water = 5
        self.game.backpack.weapons = [MeleeWeapon("Scrap", 1, 1)]  # only 1, needs 2

        with patch("builtins.print"):
            self.game.craft("survivor_machete")

        self.assertEqual(len(self.game.backpack.weapons), 1)  # nothing consumed

    def test_describe_recipes_reports_locked_status_by_level(self):
        self.game.level = 1
        recipes = {r["key"]: r for r in self.game.describe_recipes()}

        self.assertFalse(recipes["steel_sword"]["locked"])
        self.assertTrue(recipes["apex_blade"]["locked"])
        self.assertEqual(recipes["apex_blade"]["min_level"], 18)


class TestCraftingQuality(unittest.TestCase):
    """
    Skill-based crafting quality (dexterity-scaled bonus tier on top
    of a recipe's base result) - deliberately additive only, so these
    tests focus on "never worse than base" and "never loses
    ingredients regardless of roll", not on any failure/waste path
    (there isn't one).
    """

    def setUp(self):
        with patch("builtins.print"):
            self.game = Apocrysis("QualityTest", map_size=10, seed=1)

    def test_roll_quality_never_below_base_multiplier(self):
        self.game.dexterity = 5
        for _ in range(50):
            label, multiplier = self.game._roll_craft_quality()
            self.assertIn(label, ("Standard", "Fine", "Masterwork"))
            self.assertGreaterEqual(multiplier, 1.0)

    def test_high_dexterity_can_roll_masterwork(self):
        # dexterity=100 hits the 0.3 masterwork_chance cap - with a
        # fixed seed, at least one of many rolls should land it.
        self.game.dexterity = 100
        labels = {self.game._roll_craft_quality()[0] for _ in range(50)}
        self.assertIn("Masterwork", labels)

    def test_crafted_item_stats_scale_with_quality_label(self):
        self.game.backpack.food = 5
        self.game.backpack.weapons = [MeleeWeapon("Scrap", 1, 1)]
        self.game.dexterity = 100  # maximize odds of a non-Standard roll

        with patch("builtins.print"):
            self.game.craft("steel_sword")

        crafted = next(
            w for w in self.game.backpack.weapons if w.name.endswith("Steel Sword")
        )
        if crafted.name != "Steel Sword":
            # A quality tier was rolled - stats must scale up, never down.
            self.assertGreater(crafted.damage, 20)
            self.assertGreater(crafted.durability, 50)
            self.assertEqual(crafted.durability, crafted.max_durability)

    def test_craft_never_loses_ingredients_regardless_of_quality_roll(self):
        # Same ingredient-consumption assertion as
        # TestCrafting.test_craft_success_consumes_ingredients_and_adds_weapon,
        # just re-run across many seeds to cover every quality branch.
        for seed in range(10):
            with patch("builtins.print"):
                game = Apocrysis("SeedTest", map_size=5, seed=seed)
            game.backpack.food = 5
            game.backpack.weapons = [MeleeWeapon("Scrap", 1, 1)]

            with patch("builtins.print"):
                game.craft("steel_sword")

            self.assertEqual(game.backpack.food, 3)
            self.assertEqual(len(game.backpack.weapons), 1)


class TestSaveLoad(unittest.TestCase):
    SAVE_FILE = "_test_apocrysis_save.json"

    def setUp(self):
        with patch("builtins.print"):
            self.game = Apocrysis("SaveTestPlayer", map_size=10, seed=1)

    def tearDown(self):
        if os.path.exists(self.SAVE_FILE):
            os.remove(self.SAVE_FILE)

    def test_round_trip_preserves_name_and_stats(self):
        self.game.health = 77
        self.game.backpack.food = 3

        with patch("builtins.print"):
            self.game.save_game(self.SAVE_FILE)
            loaded = Apocrysis.load_game(self.SAVE_FILE)

        self.assertIsNotNone(loaded)
        # Real bug found live this session: save_game() didn't persist
        # the player's name at all, so every loaded game silently
        # became "SavedPlayer" - this is the regression test for that
        # fix.
        self.assertEqual(loaded.name, "SaveTestPlayer")
        self.assertEqual(loaded.health, 77)
        self.assertEqual(loaded.backpack.food, 3)

    def test_round_trip_preserves_equipped_weapon(self):
        self.game.equipped_weapon = MeleeWeapon("Test Blade", 9, 40)

        with patch("builtins.print"):
            self.game.save_game(self.SAVE_FILE)
            loaded = Apocrysis.load_game(self.SAVE_FILE)

        self.assertIsNotNone(loaded.equipped_weapon)
        self.assertEqual(loaded.equipped_weapon.name, "Test Blade")
        self.assertEqual(loaded.equipped_weapon.damage, 9)

    def test_load_missing_file_returns_none(self):
        self.assertFalse(os.path.exists("_definitely_missing.json"))
        self.assertIsNone(Apocrysis.load_game("_definitely_missing.json"))

    def test_round_trip_preserves_town_known(self):
        # town_known is per-map state (set by find_loot()'s map item,
        # consumed by ui_mixin._render_map_lines()'s fog-of-war check)
        # - a mid-game save/load must not silently forget it and
        # re-hide a town the player already revealed.
        self.game.town_known = True

        with patch("builtins.print"):
            self.game.save_game(self.SAVE_FILE)
            loaded = Apocrysis.load_game(self.SAVE_FILE)

        self.assertTrue(loaded.town_known)


class TestProfilePersistence(unittest.TestCase):
    """
    v3 SPRINT step 1 - save_profile()/load_profile()/apply_profile()
    are deliberately distinct from save_game()/load_game(): a profile
    carries identity/progression (name/level/stats/backpack/weapon)
    into a BRAND NEW game/map, not a resume of the old map/position.
    """

    PROFILE_FILE = "_test_apocrysis_profile.json"

    def setUp(self):
        if os.path.exists(self.PROFILE_FILE):
            os.remove(self.PROFILE_FILE)

    def tearDown(self):
        if os.path.exists(self.PROFILE_FILE):
            os.remove(self.PROFILE_FILE)

    def test_load_missing_profile_returns_none(self):
        self.assertIsNone(Apocrysis.load_profile(self.PROFILE_FILE))

    def test_save_then_load_profile_round_trips_identity_fields(self):
        with patch("builtins.print"):
            game = Apocrysis("ProfileTest", map_size=8, seed=1)

        game.level = 7
        game.xp = 42
        game.strength = 20
        game.backpack.food = 5

        game.save_profile(self.PROFILE_FILE)
        profile = Apocrysis.load_profile(self.PROFILE_FILE)

        self.assertIsNotNone(profile)
        self.assertEqual(profile["name"], "ProfileTest")
        self.assertEqual(profile["level"], 7)
        self.assertEqual(profile["xp"], 42)
        self.assertEqual(profile["strength"], 20)
        self.assertEqual(profile["backpack_food"], 5)

    def test_apply_profile_adds_backpack_onto_fresh_bonus_not_overwrite(self):
        # Mirrors load_game()'s existing += pattern (not =) for
        # backpack fields - a prize_for_next_game bonus already
        # applied by __init__ must survive apply_profile() on top of
        # it, not be silently overwritten.
        with patch("builtins.print"):
            source = Apocrysis("ProfileTest", map_size=8, seed=1)
        source.backpack.food = 9
        source.level = 5
        source.save_profile(self.PROFILE_FILE)
        profile = Apocrysis.load_profile(self.PROFILE_FILE)

        with patch("builtins.print"):
            fresh = Apocrysis("ProfileTest", map_size=8, level=5, seed=2)
        fresh.backpack.food = 2  # simulates a prize_for_next_game bonus already applied

        fresh.apply_profile(profile)

        self.assertEqual(fresh.backpack.food, 11)
        self.assertEqual(fresh.level, 5)


class TestHardcoreProfiles(unittest.TestCase):
    """
    Hardcore-mode + multi-profile name selection: each player name
    gets its own apocrysis_profile_<name>.json (profile_filename_for_
    name()), list_profile_names()/load_profile_by_name() drive the
    launch-time picker, and delete_profile() is the permadeath path
    for a hardcore character who died.
    """

    def setUp(self):
        # list_profile_names()/load_profile_by_name()/delete_profile()
        # all read/write the LITERAL "apocrysis_profile.json" (the
        # legacy default filename) in the current directory, not a
        # caller-supplied path - unlike TestProfilePersistence above,
        # these tests can't just pick a distinctly-named file to avoid
        # colliding with a real project's own apocrysis_profile.json.
        # Run from an isolated temp directory instead.
        self._orig_cwd = os.getcwd()
        self._tmpdir = tempfile.mkdtemp()
        os.chdir(self._tmpdir)

    def tearDown(self):
        os.chdir(self._orig_cwd)
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_profile_filename_for_name_slugifies_unsafe_characters(self):
        self.assertEqual(
            profile_filename_for_name("Jess"), "apocrysis_profile_Jess.json"
        )
        self.assertEqual(
            profile_filename_for_name("../../etc/passwd"),
            "apocrysis_profile__etc_passwd.json",
        )

    def test_save_profile_persists_hardcore_flag(self):
        with patch("builtins.print"):
            game = Apocrysis("HCTest", map_size=8, seed=1, hardcore=True)

        filename = profile_filename_for_name(game.name)
        game.save_profile(filename)
        profile = Apocrysis.load_profile(filename)

        self.assertTrue(profile["hardcore"])

    def test_apply_profile_restores_hardcore_flag(self):
        with patch("builtins.print"):
            source = Apocrysis("HCTest2", map_size=8, seed=1, hardcore=True)
        filename = profile_filename_for_name(source.name)
        source.save_profile(filename)
        profile = Apocrysis.load_profile(filename)

        with patch("builtins.print"):
            fresh = Apocrysis("HCTest2", map_size=8, seed=2, hardcore=False)
        fresh.apply_profile(profile)

        self.assertTrue(fresh.hardcore)

    def test_apply_profile_restores_flashlight_across_expeditions(self):
        # Found once, carried forward like a weapon - not reset each
        # fresh expedition the way town_known is.
        with patch("builtins.print"):
            source = Apocrysis("FlashlightTest", map_size=8, seed=1)
        source.has_flashlight = True
        filename = profile_filename_for_name(source.name)
        source.save_profile(filename)
        profile = Apocrysis.load_profile(filename)

        with patch("builtins.print"):
            fresh = Apocrysis("FlashlightTest", map_size=8, seed=2)
        fresh.apply_profile(profile)

        self.assertTrue(fresh.has_flashlight)

    def test_list_and_load_profile_by_name_round_trip(self):
        with patch("builtins.print"):
            alice = Apocrysis("Alice", map_size=8, seed=1)
            bob = Apocrysis("Bob", map_size=8, seed=2, hardcore=True)

        alice.save_profile(profile_filename_for_name("Alice"))
        bob.save_profile(profile_filename_for_name("Bob"))

        names = Apocrysis.list_profile_names()
        self.assertIn("Alice", names)
        self.assertIn("Bob", names)

        bob_profile = Apocrysis.load_profile_by_name("Bob")
        self.assertIsNotNone(bob_profile)
        self.assertTrue(bob_profile["hardcore"])

        self.assertIsNone(Apocrysis.load_profile_by_name("NoSuchSurvivor"))

    def test_load_profile_by_name_migrates_legacy_flat_file(self):
        with patch("builtins.print"):
            legacy_player = Apocrysis("LegacySurvivor", map_size=8, seed=1)
        legacy_player.save_profile("apocrysis_profile.json")

        per_name_file = profile_filename_for_name("LegacySurvivor")
        self.assertFalse(os.path.exists(per_name_file))

        migrated = Apocrysis.load_profile_by_name("LegacySurvivor")

        self.assertIsNotNone(migrated)
        self.assertTrue(os.path.exists(per_name_file))
        self.assertIn("LegacySurvivor", Apocrysis.list_profile_names())

    def test_delete_profile_removes_own_file_only(self):
        with patch("builtins.print"):
            doomed = Apocrysis("Doomed", map_size=8, seed=1, hardcore=True)
            survivor = Apocrysis("Survivor", map_size=8, seed=2)

        doomed_file = profile_filename_for_name("Doomed")
        survivor_file = profile_filename_for_name("Survivor")
        doomed.save_profile(doomed_file)
        survivor.save_profile(survivor_file)

        doomed.delete_profile()

        self.assertFalse(os.path.exists(doomed_file))
        self.assertTrue(os.path.exists(survivor_file))


class TestRendering(unittest.TestCase):
    def setUp(self):
        with patch("builtins.print"):
            self.game = Apocrysis("TestPlayer", map_size=12, seed=1)

    def test_render_map_lines_are_uniform_visible_width(self):
        # Real bug found live this session: the color-coded player
        # marker ('P') is wrapped in ANSI escape codes, which are
        # invisible on screen but were still counted by raw len() -
        # only the row containing the player ended up narrower than
        # every other row once padded. _visible_len must agree across
        # every rendered row regardless of the embedded color codes.
        lines = self.game._render_map_lines()
        widths = {_visible_len(line) for line in lines}
        self.assertEqual(len(widths), 1, f"inconsistent visible widths: {widths}")

    def test_display_ljust_pads_by_visible_length_not_raw_length(self):
        colored = "\033[1m\033[92mP\033[0m"
        padded = _display_ljust(colored, 5)
        self.assertEqual(_visible_len(padded), 5)

    def test_town_tiles_show_real_feature_letter_not_hardcoded_T(self):
        # Real bug found live this session: every town tile used to
        # render as a hardcoded 'T' regardless of which feature
        # (House/Road/Shop/Building/Town center) was actually
        # assigned - the real feature letters were computed and
        # stored but never displayed.
        town_tiles = [
            tile
            for row in self.game.map
            for tile in row
            if isinstance(tile, dict) and tile.get("terrain") == "town"
        ]
        self.assertTrue(town_tiles, "expected at least one town tile")
        feature_letters = {t["content"] for t in town_tiles}
        self.assertTrue(feature_letters.issubset({"H", "R", "S", "B", "T"}))

        # v3 #2 - the real bug this sprint fixed: a town used to be
        # able to generate MULTIPLE 'T' tiles (each town tile's
        # feature was chosen independently, 'T' included). Exactly
        # one town center, always.
        town_centers = [t for t in town_tiles if t["content"] == "T"]
        self.assertEqual(len(town_centers), 1)

    def test_town_hidden_by_fog_of_war_until_in_range_or_town_known(self):
        # Real bug found live this session: town tiles used to render
        # their real feature letter completely unconditionally - the
        # one terrain type that ignored fog-of-war entirely, so the
        # win condition's location was always visible from turn one.
        town_pos = next(
            (x, y)
            for y, row in enumerate(self.game.map)
            for x, tile in enumerate(row)
            if isinstance(tile, dict) and tile.get("terrain") == "town"
        )
        tx, ty = town_pos
        dist = abs(tx - self.game.current_position[0]) + abs(ty - self.game.current_position[1])
        self.assertGreater(
            dist, self.game.visibility_radius,
            "test needs a town tile out of spawn's visibility range",
        )

        def _tile_char(lines, tx, ty):
            # Grid labels (chess-style): N header lines above the map,
            # a row-letter gutter to the left. Derive both offsets from
            # the rendered output rather than hard-coding them.
            top = len(lines) - len(self.game.map) - 1  # minus map rows, minus bottom border
            left = lines[-1].index('*') + 1            # first tile column, past the '*' border
            return lines[top + ty][left + tx]

        self.game.town_known = False
        lines = self.game._render_map_lines()
        self.assertIn(_tile_char(lines, tx, ty), (" ", "."))

        self.game.town_known = True
        lines = self.game._render_map_lines()
        self.assertIn(_tile_char(lines, tx, ty), {"H", "R", "S", "B", "T"})

    def test_terrain_symbols_cover_every_generated_terrain_type(self):
        terrains_in_use = {
            tile.get("terrain")
            for row in self.game.map
            for tile in row
            if isinstance(tile, dict) and tile.get("terrain") != "town"
        }
        for terrain in terrains_in_use:
            self.assertIn(terrain, TERRAIN_SYMBOLS)

    def test_print_help_lists_conditional_commands_only_when_available(self):
        self.game.backpack.food = 0
        self.game.backpack.water = 0
        self.game.backpack.medicine = 0

        with patch("builtins.print") as mock_print:
            self.game.print_help()
        printed = "\n".join(str(c.args[0]) for c in mock_print.call_args_list if c.args)
        self.assertNotIn("eat  ", printed.replace("\t", " "))

        self.game.backpack.food = 1
        self.game.backpack.water = 1
        self.game.backpack.medicine = 1

        with patch("builtins.print") as mock_print:
            self.game.print_help()
        printed = "\n".join(str(c.args[0]) for c in mock_print.call_args_list if c.args)
        self.assertIn("eat", printed)
        self.assertIn("drink", printed)
        self.assertIn("medicine", printed)


class TestMapGeneration(unittest.TestCase):
    """v3 SPRINT step 2 - map generation redesign. Fixed seeds
    throughout so generation is reproducible (self.rng, game.py's
    __init__), per the sprint plan's reproducibility requirement."""

    def _find_town_center(self, game):
        for y, row in enumerate(game.map):
            for x, tile in enumerate(row):
                if isinstance(tile, dict) and tile.get("content") == "T":
                    return (x, y)
        return None

    def test_town_center_reachable_from_spawn_across_many_seeds(self):
        # Governing invariant: generate_map() must never return with
        # spawn unable to reach the town center, at any expedition
        # count (obstacle density scales with expeditions_completed,
        # not player level, since the map/player/campaign level split
        # - this is exactly where an unreachable map would show up if
        # the carve-path guarantee were broken).
        for seed in range(20):
            for expeditions_completed in (0, 4, 8, 12, 20):
                with patch("builtins.print"):
                    game = Apocrysis(
                        "ReachTest", map_size=15, seed=seed,
                        expeditions_completed=expeditions_completed,
                    )
                town_center = self._find_town_center(game)
                self.assertIsNotNone(town_center)
                self.assertTrue(
                    game._bfs_reachable(game.current_position, town_center),
                    f"unreachable town at seed={seed} expeditions_completed={expeditions_completed}",
                )

    def test_town_min_distance_grows_with_expeditions_completed(self):
        with patch("builtins.print"):
            low_game = Apocrysis("DistTest", map_size=40, seed=3, expeditions_completed=0)
        with patch("builtins.print"):
            high_game = Apocrysis("DistTest", map_size=40, seed=3, expeditions_completed=15)

        def distance(game):
            tc = self._find_town_center(game)
            sx, sy = game.current_position
            return abs(tc[0] - sx) + abs(tc[1] - sy)

        # Not a strict inequality on a single sample (placement is
        # still randomized above the minimum), but the 15-expedition
        # game's own minimum bound must be higher than the 0-expedition
        # game's.
        self.assertGreater(
            self._min_distance_for(high_game),
            self._min_distance_for(low_game),
        )
        self.assertGreaterEqual(distance(high_game), self._min_distance_for(high_game))

    @staticmethod
    def _min_distance_for(game):
        from src.constants import BASE_TOWN_MIN_DISTANCE, TOWN_DISTANCE_GROWTH_PER_LEVEL
        return min(
            game.map_size - 2,
            BASE_TOWN_MIN_DISTANCE + game.expeditions_completed * TOWN_DISTANCE_GROWTH_PER_LEVEL,
        )

    def test_carve_path_never_touches_spawn_or_town_center(self):
        with patch("builtins.print"):
            # expeditions_completed=20: max obstacle density
            game = Apocrysis("CarveTest", map_size=15, seed=7, expeditions_completed=20)
        town_center = self._find_town_center(game)

        spawn_tile = game.map[game.current_position[1]][game.current_position[0]]
        town_tile = game.map[town_center[1]][town_center[0]]

        self.assertNotIn(spawn_tile.get("terrain"), {"mountain", "river"})
        self.assertEqual(town_tile.get("content"), "T")

    def test_map_size_grows_with_expeditions_completed(self):
        with patch("builtins.print"):
            low = Apocrysis("SizeTest", seed=1, expeditions_completed=0)
        with patch("builtins.print"):
            high = Apocrysis("SizeTest", seed=1, expeditions_completed=15)
        self.assertGreater(high.map_size, low.map_size)

    def test_explicit_map_size_overrides_expeditions_completed_derivation(self):
        with patch("builtins.print"):
            game = Apocrysis("SizeTest", map_size=9, seed=1, expeditions_completed=15)
        self.assertEqual(game.map_size, 9)


class TestExpeditionsAndCampaign(unittest.TestCase):
    """
    Map/player/campaign level split: expeditions_completed (not raw
    player level) now drives map_size/obstacle_density/town distance
    (TestMapGeneration above), and increments on reaching the Town
    Center - these tests cover the win-condition side: the counter
    actually advancing, and the distinct CAMPAIGN_LENGTH milestone.
    """

    def _make_game(self, expeditions_completed=0):
        with patch("builtins.print"):
            game = Apocrysis(
                "ExpTest", map_size=10, seed=1,
                expeditions_completed=expeditions_completed,
            )
        # Deterministic spawn + an adjacent, walkable Town Center tile,
        # regardless of where generate_map()'s random spawn landed.
        game.current_position = (0, 0)
        game.map[0][1] = {"terrain": "plain", "content": "T", "explored": True}
        # Objective-driven win condition investigation: reaching 'T'
        # alone no longer wins - these tests are about the campaign/
        # expedition-counter mechanics specifically, not that gate, so
        # satisfy it directly rather than also staging a settlement
        # tile to walk through first.
        game.settlement_explored = True
        game.mystery = None  # v4: test the no-mystery reach-town fallback
        return game

    def test_reaching_town_increments_expeditions_completed(self):
        game = self._make_game(expeditions_completed=3)
        with patch("builtins.print"):
            game.move_and_search("e")
        self.assertTrue(game.won)
        self.assertEqual(game.expeditions_completed, 4)

    def test_campaign_complete_message_at_campaign_length(self):
        from src.constants import CAMPAIGN_LENGTH
        game = self._make_game(expeditions_completed=CAMPAIGN_LENGTH - 1)

        messages = []
        game.io.say = lambda *a, **k: messages.append(" ".join(str(x) for x in a))
        game.move_and_search("e")

        self.assertEqual(game.expeditions_completed, CAMPAIGN_LENGTH)
        self.assertTrue(any("CAMPAIGN COMPLETE" in m for m in messages))

    def test_ordinary_win_below_campaign_length_uses_the_normal_message(self):
        from src.constants import CAMPAIGN_LENGTH
        game = self._make_game(expeditions_completed=CAMPAIGN_LENGTH - 2)

        messages = []
        game.io.say = lambda *a, **k: messages.append(" ".join(str(x) for x in a))
        game.move_and_search("e")

        self.assertEqual(game.expeditions_completed, CAMPAIGN_LENGTH - 1)
        self.assertFalse(any("CAMPAIGN COMPLETE" in m for m in messages))
        self.assertTrue(any("You WIN" in m for m in messages))


class TestObjectiveDrivenWin(unittest.TestCase):
    """
    Objective-driven win condition investigation: reaching the Town
    Center alone no longer wins - the player must have already set
    foot in a settlement's other tiles first.
    """

    def _make_game(self):
        with patch("builtins.print"):
            game = Apocrysis("ObjectiveTest", map_size=10, seed=1)
        game.current_position = (0, 0)
        game.map[0][1] = {"terrain": "plain", "content": "T", "explored": True}
        game.mystery = None  # v4: these test the pre-mystery Town-Center gate
        return game

    def test_reaching_town_center_before_exploring_does_not_win(self):
        game = self._make_game()
        self.assertFalse(game.settlement_explored)

        with patch("builtins.print"):
            game.move_and_search("e")

        self.assertFalse(game.won)

    def test_stepping_on_a_settlement_tile_sets_the_explored_flag(self):
        game = self._make_game()
        game.map[0][1] = {
            "terrain": "town", "content": "H",
            "explored": True, "district": "residential",
        }

        with patch("builtins.print"), patch("builtins.input", return_value="n"):
            game.move_and_search("e")

        self.assertTrue(game.settlement_explored)
        self.assertFalse(game.won)  # H tile, not T - still no win

    def test_reaching_town_center_after_exploring_wins(self):
        game = self._make_game()
        game.settlement_explored = True

        with patch("builtins.print"):
            game.move_and_search("e")

        self.assertTrue(game.won)


class TestSettlementGeneration(unittest.TestCase):
    """Multiple-settlements + organic-settlement investigations."""

    def _town_tiles(self, game):
        return [
            tile for row in game.map for tile in row
            if isinstance(tile, dict) and tile.get("terrain") == "town"
        ]

    def test_exactly_one_town_center_regardless_of_settlement_count(self):
        with patch("builtins.print"):
            game = Apocrysis("SettleTest", map_size=30, seed=3, expeditions_completed=20)
        centers = [t for t in self._town_tiles(game) if t.get("content") == "T"]
        self.assertEqual(len(centers), 1)

    def test_settlement_count_grows_with_expeditions_completed(self):
        from src.constants import MAX_SETTLEMENTS, SETTLEMENTS_PER_EXPEDITIONS
        with patch("builtins.print"):
            early = Apocrysis("SettleEarly", map_size=30, seed=3, expeditions_completed=0)
        with patch("builtins.print"):
            late = Apocrysis(
                "SettleLate", map_size=30, seed=3,
                expeditions_completed=MAX_SETTLEMENTS * SETTLEMENTS_PER_EXPEDITIONS,
            )
        # Indirect measure: more settlements means more town tiles on
        # the same map size/seed (content varies, but total count of
        # terrain=='town' tiles scales with settlement count).
        self.assertGreater(len(self._town_tiles(late)), len(self._town_tiles(early)))

    def test_settlement_boundary_is_not_a_solid_square(self):
        # Organic-settlement investigation: at least one corner of the
        # bounding box should NOT be settlement terrain, across many
        # seeds (the 0.6 skip-chance makes a solid square on every
        # single seed astronomically unlikely if the skip is wired
        # correctly, but check several seeds rather than one to keep
        # this from being a flaky single-sample assertion).
        found_irregular = False
        for seed in range(10):
            with patch("builtins.print"):
                game = Apocrysis("BoundaryTest", map_size=15, seed=seed)
            town_tiles = self._town_tiles(game)
            if not town_tiles:
                continue
            # Find the bounding box of all town tiles and check
            # whether its four corners are actually town terrain.
            coords = [
                (x, y)
                for y, row in enumerate(game.map)
                for x, t in enumerate(row)
                if isinstance(t, dict) and t.get("terrain") == "town"
            ]
            min_x, max_x = min(c[0] for c in coords), max(c[0] for c in coords)
            min_y, max_y = min(c[1] for c in coords), max(c[1] for c in coords)
            corners = [(min_x, min_y), (min_x, max_y), (max_x, min_y), (max_x, max_y)]
            corner_terrains = {game.map[y][x].get("terrain") for x, y in corners}
            if corner_terrains != {"town"}:
                found_irregular = True
                break
        self.assertTrue(found_irregular, "every sampled settlement was a solid square")

    def test_settlement_tiles_are_tagged_with_a_district(self):
        with patch("builtins.print"):
            game = Apocrysis("DistrictTest", map_size=15, seed=1)
        town_tiles = self._town_tiles(game)
        self.assertTrue(town_tiles)
        self.assertTrue(all("district" in t for t in town_tiles))
        self.assertTrue(
            {t["district"] for t in town_tiles} <= {"downtown", "commercial", "residential"}
        )


class TestChunkBasedTerrain(unittest.TestCase):
    def test_terrain_forms_contiguous_chunks_not_a_checkerboard(self):
        from src.constants import CHUNK_SIZE
        with patch("builtins.print"):
            game = Apocrysis("ChunkTest", map_size=20, seed=1)

        # Every tile within one chunk (excluding town tiles and
        # per-tile mountain/river obstacle overlays) must share the
        # same base terrain - a checkerboard regression would produce
        # a chunk with multiple different non-obstacle terrains.
        found_multi_terrain_chunk = False
        for cy in range(0, game.map_size, CHUNK_SIZE):
            for cx in range(0, game.map_size, CHUNK_SIZE):
                terrains = set()
                for y in range(cy, min(cy + CHUNK_SIZE, game.map_size)):
                    for x in range(cx, min(cx + CHUNK_SIZE, game.map_size)):
                        tile = game.map[y][x]
                        if not isinstance(tile, dict):
                            continue
                        terrain = tile.get("terrain")
                        if terrain not in ("mountain", "river", "town"):
                            terrains.add(terrain)
                if len(terrains) > 1:
                    found_multi_terrain_chunk = True
        self.assertFalse(
            found_multi_terrain_chunk,
            "a chunk contained more than one non-obstacle terrain type",
        )


class TestCombatV3(unittest.TestCase):
    """v3 SPRINT step 3 - yes/no fight prompt, new zombie types."""

    def setUp(self):
        with patch("builtins.print"):
            self.game = Apocrysis("CombatTest", map_size=8, seed=1)

    @patch("builtins.input", side_effect=["maybe", "y"])
    @patch("builtins.print")
    def test_fight_prompt_reprompts_on_unrecognized_input(self, mock_print, mock_input):
        # An unrecognized answer must NOT silently resolve to fight
        # or flee (the original design's "anything else flees" bug) -
        # it re-prompts until a real y/n is given.
        zombie = FreshZombie()
        zombie.health = 1  # one hit kills it, so the fight loop exits fast
        self.game.equipped_weapon = None
        self.game.strength = 100  # guarantee the unarmed hit kills it
        self.game.encounter_zombie(zombie)
        self.assertEqual(mock_input.call_count, 2)

    @patch("builtins.input", return_value="n")
    @patch("builtins.print")
    def test_fight_prompt_no_flees(self, mock_print, mock_input):
        zombie = FreshZombie()
        with patch("random.random", return_value=0.0):  # flee always succeeds
            self.game.encounter_zombie(zombie)
        self.assertGreater(zombie.health, 0)  # never fought

    @patch("builtins.input", return_value="n")
    @patch("builtins.print")
    def test_encounter_zombie_uses_the_passed_tile_not_a_random_one(self, mock_print, mock_input):
        # Real bug fixed this sprint: the isinstance() check gating
        # "use the zombie standing on this tile" only listed Fresh/
        # Regular/Heavy by name - a SwiftZombie/ToxicZombie/
        # ArmoredZombie placed on the map (world_mixin.py's
        # generate_map()) silently failed it and got replaced with a
        # freshly-rolled random zombie instead.
        zombie = ToxicZombie()
        original_name = zombie.name

        with patch.object(
            self.game, "_select_zombie_for_encounter"
        ) as mock_reroll, patch("random.random", return_value=1.0):  # flee always fails
            self.game.encounter_zombie(zombie)

        mock_reroll.assert_not_called()
        self.assertEqual(zombie.name, original_name)

    def test_armored_zombie_reduces_incoming_damage(self):
        zombie = ArmoredZombie()
        health_before = zombie.health
        zombie.take_damage(10)
        self.assertEqual(zombie.health, health_before - 5)  # 50% reduction

    @patch("builtins.input", return_value="y")
    @patch("builtins.print")
    def test_unarmed_combat_damage_scaled_by_condition_penalty(self, mock_print, mock_input):
        # Real gap found live: encounter_zombie()'s unarmed branch dealt
        # a flat 2 damage regardless of the player's condition, while
        # the armed branch already applied _condition_penalty() - the
        # two branches disagreed about whether low health/hunger/
        # fatigue should weaken an attack. Spying on take_damage's
        # exact call argument (rather than just the zombie's final
        # health) is what actually distinguishes "penalty applied"
        # from "not applied" - 2 damage would also kill a 1-health
        # zombie, so a health-only assertion can't tell them apart.
        zombie = FreshZombie()
        zombie.health = 1  # one recorded hit is lethal, ending the loop
        self.game.equipped_weapon = None
        real_take_damage = zombie.take_damage

        with patch.object(self.game, "_condition_penalty", return_value=0.5), \
             patch.object(zombie, "take_damage", side_effect=real_take_damage) as mock_take_damage:
            self.game.encounter_zombie(zombie)

        mock_take_damage.assert_called_once_with(round(2 * 0.5))

    @patch("builtins.input", side_effect=["p", "quit", "n"])
    @patch("builtins.print")
    def test_punch_command_is_wired_into_the_game_loop(self, mock_print, mock_input):
        # Real bug found live: CombatMixin.punch() existed but nothing
        # in run_game_loop()'s dispatch_map called it, so the command
        # was documented (_available_commands()) but never actually
        # reachable from the keyboard.
        with patch.object(self.game, "punch") as mock_punch:
            self.game.run_game_loop()
        mock_punch.assert_called_once_with()

    def test_select_zombie_for_encounter_can_produce_every_v3_type(self):
        # All 6 types (not just the original 3) must be real, reachable
        # outcomes of the weighted choice - world_mixin.py's
        # _select_zombie_for_encounter().
        with patch("builtins.print"):
            game = Apocrysis("ZombieVarietyTest", map_size=8, seed=5)
        # else-branch weights (keyed to expeditions_completed, not
        # in-run day, since the combat-scaling investigation) give
        # every type a real chance.
        game.expeditions_completed = 20
        seen_types = {
            type(game._select_zombie_for_encounter()) for _ in range(200)
        }
        self.assertIn(SwiftZombie, seen_types)
        self.assertIn(ToxicZombie, seen_types)
        self.assertIn(ArmoredZombie, seen_types)

    def test_zombie_composition_keys_off_expeditions_completed_not_day(self):
        # Combat scaling investigation: composition used to shift with
        # in-run day count - now it's expeditions_completed (the same
        # map-level axis map_size/obstacle_density already use), so a
        # long day count on an early expedition doesn't itself make
        # tougher zombie types common.
        with patch("builtins.print"):
            game = Apocrysis("CompositionTest", map_size=8, seed=5)
        game.day = 999
        game.expeditions_completed = 0

        # expeditions_completed<=2 weights give HeavyZombie only 0.03 -
        # a day-driven regression would instead land in the else-
        # branch weights, where it's common (0.25). 500 samples keeps
        # the ~15-expected-vs-~125-expected gap far apart from noise.
        heavy_count = sum(
            1 for _ in range(500)
            if type(game._select_zombie_for_encounter()) is HeavyZombie
        )
        self.assertLess(heavy_count, 60)

    def test_composition_ramps_smoothly_not_in_hard_brackets(self):
        # Real campaign-simulation finding: the old <=2/<=6/else hard
        # brackets produced a severe difficulty cliff right at the
        # <=6/>6 boundary (avg attempts-to-clear jumped from 2-4 to
        # 40+ between expeditions_completed 6 and 7). Composition now
        # interpolates continuously - HeavyZombie's weight at the
        # midpoint (expeditions_completed=5, half of CAMPAIGN_LENGTH)
        # must sit strictly between its early (0.03) and late (0.25)
        # values, not jump straight to either endpoint.
        from src.constants import CAMPAIGN_LENGTH
        with patch("builtins.print"):
            game = Apocrysis("SmoothTest", map_size=8, seed=5)
        game.expeditions_completed = CAMPAIGN_LENGTH // 2

        heavy_count = sum(
            1 for _ in range(1000)
            if type(game._select_zombie_for_encounter()) is HeavyZombie
        )
        # Early-bracket rate (~15/1000) and late-bracket rate (~250/1000)
        # bound the expected midpoint band; a real regression back to
        # hard brackets would land outside it, not just near an edge.
        self.assertGreater(heavy_count, 60)
        self.assertLess(heavy_count, 200)

    def test_elite_variant_boosts_stats_and_renames_zombie(self):
        with patch("builtins.print"):
            game = Apocrysis("EliteTest", map_size=8, seed=1, expeditions_completed=5)
        game.day = 1  # isolate the elite multiplier from the day-based ramp

        with patch.object(game.rng, "random", return_value=0.0):  # guarantees the elite roll
            zombie = game._select_zombie_for_encounter()

        self.assertTrue(zombie.name.startswith("Elite "))
        base_health, base_attack = game._ZOMBIE_BASE_STATS[type(zombie)]
        self.assertEqual(zombie.health, int(base_health * 1.0 * 1.5))
        self.assertEqual(zombie.attack, int(base_attack * 1.0 * 1.5))

    def test_no_elite_variants_before_min_expedition(self):
        from src.constants import ELITE_MIN_EXPEDITION
        with patch("builtins.print"):
            game = Apocrysis(
                "NoEliteTest", map_size=8, seed=1,
                expeditions_completed=ELITE_MIN_EXPEDITION - 1,
            )
        with patch.object(game.rng, "random", return_value=0.0):  # would guarantee elite if eligible
            zombie = game._select_zombie_for_encounter()
        self.assertFalse(zombie.name.startswith("Elite "))

    @patch("builtins.input", return_value="y")
    @patch("builtins.print")
    def test_toxic_zombie_poison_is_guaranteed_and_data_driven(self, mock_print, mock_input):
        # Guaranteed on hit (not a chance roll like Bleeding/Stun) -
        # one round where the player doesn't one-shot the zombie is
        # enough to see it applied.
        zombie = ToxicZombie()
        zombie.health = 1000
        self.game.equipped_weapon = None
        self.game.strength = 0
        with patch("src.mixins.combat_mixin.random.random", return_value=0.9):  # no dodge
            # Zombie health is high enough it won't die in one player
            # turn, so the loop reaches the zombie's attack.
            self.game.health = 100
            self.game.encounter_zombie(zombie)
        self.assertIn("Poison", self.game.status_effects)

    def test_status_effect_damage_expires_after_its_duration(self):
        # Real bug fixed this sprint: effects previously never expired
        # (countdown decremented but the key was never removed at 0).
        # Pre-complete the "kill" goal so its +5 health reward on
        # defeating the zombie doesn't mask the Bleeding damage in the
        # final health check below.
        for goal in self.game.goals:
            if goal.goal_type == "kill":
                goal.completed = True

        self.game.status_effects["Bleeding"] = 1
        health_before = self.game.health

        zombie = FreshZombie()
        zombie.health = 1  # one hit kills it - loop runs exactly once
        self.game.equipped_weapon = None
        self.game.strength = 100
        with patch("builtins.input", return_value="y"), patch("builtins.print"):
            self.game.encounter_zombie(zombie)

        self.assertLess(self.game.health, health_before)  # bleeding applied once
        self.assertNotIn("Bleeding", self.game.status_effects)  # then expired


try:
    from src.tui import ApocrysisApp
    _TEXTUAL_AVAILABLE = True
except ImportError:
    _TEXTUAL_AVAILABLE = False


@unittest.skipUnless(_TEXTUAL_AVAILABLE, "textual not installed - --test never requires it")
class TestTuiWinContinuation(unittest.IsolatedAsyncioTestCase):
    """
    Real bug found live: winning and pressing Enter at the "Press
    Enter to continue..." prompt closed the whole TUI app instead of
    starting the next game with the carried-forward profile - classic
    mode's cli.py main() loop already checked player.won and looped;
    tui.py's _game_thread never had the same check, so ANY reason
    run_game_loop() returned (quit, death, OR a win) exited the app.
    """

    async def asyncSetUp(self):
        self._profile_file = profile_filename_for_name("WinTest")
        if os.path.exists(self._profile_file):
            os.remove(self._profile_file)

    async def asyncTearDown(self):
        # _game_thread runs as a real OS thread (run_worker(thread=
        # True)) - it notices app shutdown by polling every 0.2s
        # (TextualIO._wait_for_answer()), not instantly, so its final
        # save_profile()/delete_profile() call can still be in flight
        # for a moment after run_test()'s `async with` block above has
        # already returned. Give it a beat before the one cleanup
        # check, or a save landing after this check would leak the
        # file into the real project directory.
        await asyncio.sleep(0.3)
        if os.path.exists(self._profile_file):
            os.remove(self._profile_file)

    async def test_winning_starts_a_new_game_instead_of_exiting(self):
        app = ApocrysisApp(name="WinTest", level=1, seed=1)
        async with app.run_test(size=(130, 48)) as pilot:
            await asyncio.wait_for(pilot.pause(), timeout=5)

            original_player = app.player
            app.player.won = True
            app.player.health = 100

            # Re-enter run_game_loop() so it sees won=True and exits
            # the while loop into the victory/continue-prompt path.
            await asyncio.wait_for(pilot.click("#command_input"), timeout=5)
            await asyncio.wait_for(pilot.press("enter"), timeout=5)
            await asyncio.wait_for(pilot.pause(0.5), timeout=5)

            self.assertEqual(
                app.query_one("#command_input").placeholder,
                "Press Enter to continue...",
            )

            await asyncio.wait_for(pilot.press("enter"), timeout=5)
            await asyncio.wait_for(pilot.pause(0.5), timeout=5)

            self.assertTrue(app.is_running, "app exited instead of starting a new game")
            self.assertIsNot(app.player, original_player)
            self.assertFalse(app.player.won)


class TestTuiStaleInputCleared(unittest.IsolatedAsyncioTestCase):
    """
    Real bug found live: entering commands fast could get the player
    killed by what looked like "random" movement/combat. request_input()
    only ever updated the command box's .placeholder (shown when the
    field is empty) - text a player had already TYPED but not yet
    submitted stayed sitting in .value untouched when the prompt
    underneath it changed (e.g. a move triggers a zombie encounter's
    "Do you want to fight?" while the player had already typed their
    next intended move and just hadn't hit Enter yet). Submitting then
    silently answered whatever's being asked NOW with stale text typed
    for a different, no-longer-current prompt - answering a fight
    prompt with a movement letter (which, since 'n' also means "no",
    could decline to fight) with no visible error.
    """

    async def asyncSetUp(self):
        self._profile_file = profile_filename_for_name("StaleInputTest")
        if os.path.exists(self._profile_file):
            os.remove(self._profile_file)

    async def asyncTearDown(self):
        # Same race as TestTuiWinContinuation above: _game_thread's
        # AppClosed-triggered save_profile() can still be in flight
        # briefly after run_test()'s `async with` block has returned.
        await asyncio.sleep(0.3)
        if os.path.exists(self._profile_file):
            os.remove(self._profile_file)

    async def test_request_input_clears_stale_unsent_text(self):
        app = ApocrysisApp(name="StaleInputTest", level=1, seed=1)
        async with app.run_test(size=(130, 48)) as pilot:
            await asyncio.wait_for(pilot.pause(), timeout=5)

            inp = app.query_one("#command_input")
            inp.focus()
            await asyncio.wait_for(pilot.pause(), timeout=5)

            # Player typed "n" meaning "move north" but hasn't hit
            # Enter yet.
            inp.value = "n"

            # The prompt changes underneath them - e.g. a zombie
            # encounter's fight decision.
            app.request_input("Do you want to fight? (y/n)")

            self.assertEqual(
                inp.value, "",
                "stale unsent text survived a prompt change - it would "
                "be submitted as the answer to the NEW prompt, not the "
                "one the player actually typed it for",
            )
            self.assertEqual(inp.placeholder, "Do you want to fight? (y/n)")


if __name__ == "__main__":
    unittest.main(verbosity=2)
