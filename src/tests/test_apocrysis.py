import os
import re
import unittest
from unittest.mock import patch

from src.constants import TERRAIN_SYMBOLS
from src.game import Apocrysis
from src.items import Backpack, ConsumableType, MeleeWeapon, RangedWeapon
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
            any(w.name == "Apex Blade" for w in self.game.backpack.weapons)
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
        self.assertEqual(self.game.backpack.weapons[0].name, "Survivor Machete")

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
        # spawn unable to reach the town center, at any level
        # (obstacle density scales with level - this is exactly where
        # an unreachable map would show up if the carve-path guarantee
        # were broken).
        for seed in range(20):
            for level in (1, 4, 8, 12, 20):
                with patch("builtins.print"):
                    game = Apocrysis("ReachTest", map_size=15, level=level, seed=seed)
                town_center = self._find_town_center(game)
                self.assertIsNotNone(town_center)
                self.assertTrue(
                    game._bfs_reachable(game.current_position, town_center),
                    f"unreachable town at seed={seed} level={level}",
                )

    def test_town_min_distance_grows_with_level(self):
        with patch("builtins.print"):
            low_level_game = Apocrysis("DistTest", map_size=40, level=1, seed=3)
        with patch("builtins.print"):
            high_level_game = Apocrysis("DistTest", map_size=40, level=15, seed=3)

        def distance(game):
            tc = self._find_town_center(game)
            sx, sy = game.current_position
            return abs(tc[0] - sx) + abs(tc[1] - sy)

        # Not a strict inequality on a single sample (placement is
        # still randomized above the minimum), but the level-15 game's
        # own minimum bound must be higher than level-1's.
        self.assertGreater(
            self._min_distance_for(high_level_game),
            self._min_distance_for(low_level_game),
        )
        self.assertGreaterEqual(distance(high_level_game), self._min_distance_for(high_level_game))

    @staticmethod
    def _min_distance_for(game):
        from src.constants import BASE_TOWN_MIN_DISTANCE, TOWN_DISTANCE_GROWTH_PER_LEVEL
        return min(
            game.map_size - 2,
            BASE_TOWN_MIN_DISTANCE + (game.level - 1) * TOWN_DISTANCE_GROWTH_PER_LEVEL,
        )

    def test_carve_path_never_touches_spawn_or_town_center(self):
        with patch("builtins.print"):
            game = Apocrysis("CarveTest", map_size=15, level=20, seed=7)  # max obstacle density
        town_center = self._find_town_center(game)

        spawn_tile = game.map[game.current_position[1]][game.current_position[0]]
        town_tile = game.map[town_center[1]][town_center[0]]

        self.assertNotIn(spawn_tile.get("terrain"), {"mountain", "river"})
        self.assertEqual(town_tile.get("content"), "T")

    def test_map_size_grows_with_level(self):
        with patch("builtins.print"):
            low = Apocrysis("SizeTest", level=1, seed=1)
        with patch("builtins.print"):
            high = Apocrysis("SizeTest", level=15, seed=1)
        self.assertGreater(high.map_size, low.map_size)

    def test_explicit_map_size_overrides_level_derivation(self):
        with patch("builtins.print"):
            game = Apocrysis("SizeTest", map_size=9, level=15, seed=1)
        self.assertEqual(game.map_size, 9)


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

    def test_select_zombie_for_encounter_can_produce_every_v3_type(self):
        # All 6 types (not just the original 3) must be real, reachable
        # outcomes of the weighted choice - world_mixin.py's
        # _select_zombie_for_encounter().
        with patch("builtins.print"):
            game = Apocrysis("ZombieVarietyTest", map_size=8, seed=5)
        game.day = 20  # else-branch weights give every type a real chance
        seen_types = {
            type(game._select_zombie_for_encounter()) for _ in range(200)
        }
        self.assertIn(SwiftZombie, seen_types)
        self.assertIn(ToxicZombie, seen_types)
        self.assertIn(ArmoredZombie, seen_types)

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
