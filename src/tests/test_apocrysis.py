import os
import re
import unittest
from unittest.mock import patch

from src.constants import TERRAIN_SYMBOLS
from src.game import Apocrysis
from src.items import Backpack, ConsumableType, MeleeWeapon, RangedWeapon
from src.player import PlayerClass
from src.text_utils import _visible_len, _display_ljust
from src.zombies import FreshZombie, RegularZombie, HeavyZombie


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
            self.game = Apocrysis("TestPlayer", "gamer", 10)

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
    # real stdin on an unlucky random draw. "flee" resolves either way
    # (the 50% flee-success roll doesn't call input() again), and the
    # position assertions only depend on where move_and_search() puts
    # the player, not on the fight outcome.
    @patch("builtins.input", return_value="flee")
    @patch("builtins.print")
    def test_move_and_search_bounds(self, mock_print, mock_input):
        self.game.move_and_search("n")
        self.assertEqual(self.game.current_position[1], 4)

        self.game.current_position = (9, 5)
        self.game.move_and_search("e")
        self.assertEqual(self.game.current_position[0], 9)

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


class TestTimeAndDecay(unittest.TestCase):
    def setUp(self):
        with patch("builtins.print"):
            self.game = Apocrysis("TestPlayer", "gamer", 10)

    def test_update_time_advances_and_wraps(self):
        self.game.time_of_day = 1430
        self.game._update_time()
        self.assertEqual(self.game.time_of_day, 5)  # wraps past midnight

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


class TestCrafting(unittest.TestCase):
    def setUp(self):
        with patch("builtins.print"):
            self.game = Apocrysis("TestPlayer", "gamer", 10)

    def test_craft_success_consumes_ingredients_and_adds_weapon(self):
        self.game.backpack.food = 5
        self.game.backpack.weapons.append(MeleeWeapon("Scrap", 1, 1))
        weapons_before = len(self.game.backpack.weapons)

        with patch("builtins.print"):
            self.game.craft("steel_sword")

        self.assertEqual(self.game.backpack.food, 3)  # steel_sword costs 2 food
        # one weapon consumed as an ingredient, one crafted result added
        self.assertEqual(len(self.game.backpack.weapons), weapons_before)
        self.assertTrue(
            any(w.name == "Steel Sword" for w in self.game.backpack.weapons)
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


class TestSaveLoad(unittest.TestCase):
    SAVE_FILE = "_test_apocrysis_save.json"

    def setUp(self):
        with patch("builtins.print"):
            self.game = Apocrysis("SaveTestPlayer", "gamer", 10)

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


class TestRendering(unittest.TestCase):
    def setUp(self):
        with patch("builtins.print"):
            self.game = Apocrysis("TestPlayer", "gamer", 12)

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
