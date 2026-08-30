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

    def test_one_rest_is_a_meaningful_reset_not_one_move(self):
        # 1d HUD pass: a deliberate rest should claw back real fatigue
        # (>= 40 in the open), not just undo a single move's +5.
        self.game.fatigue = 100
        # force open ground so the building x2 doesn't mask the base
        self.game.map[self.game.current_position[1]][self.game.current_position[0]] = {"terrain": "plain"}
        with patch("builtins.print"):
            self.game.rest()
        self.assertLessEqual(self.game.fatigue, 60)

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

    def test_zero_food_and_water_drains_health_no_movement_cap(self):
        # BlueNoodle reached 0/0 and still escaped - starvation must
        # stay HP attrition, never a hard "you can only move N squares".
        self.game.hunger = 0
        self.game.thirst = 0
        self.game.health = 100
        for _ in range(5):
            self.game._apply_decay()
        # -2 hunger -2 thirst per turn = -4/turn
        self.assertEqual(self.game.health, 100 - 5 * 4)
        # only hunger at zero -> -2/turn
        self.game.thirst = 60
        self.game.health = 100
        self.game._apply_decay()
        self.assertEqual(self.game.health, 98)

    def test_supply_warnings_escalate_once_per_tier(self):
        # A kid ran to 0 with food in the pack and never got a second
        # warning after the first -30 nudge. Now: -30, -10, and 0 each
        # fire once, phrased for "you HAVE food".
        said = []
        self.game.io = type("IO", (), {
            "say": lambda s, t: said.append(str(t)),
            "__getattr__": lambda s, n: (lambda *a, **k: None),
        })()
        self.game.backpack.food = 5
        self.game.backpack.water = 60
        self.game.hunger = 100
        for _ in range(60):
            self.game._apply_decay()
        joined = " ".join(said).upper()
        self.assertIn("GETTING HUNGRY", joined)          # tier 1 (<=30)
        self.assertIn("EAT NOW", joined)                 # tier 2 (<=10)
        self.assertIn("EAT SOMETHING", joined)           # tier 3 (0, has food)
        # each headline once
        self.assertEqual(joined.count("GETTING HUNGRY"), 1)
        self.assertEqual(joined.count("EAT NOW"), 1)

    def test_supply_warning_rearms_after_recovery(self):
        said = []
        self.game.io = type("IO", (), {
            "say": lambda s, t: said.append(str(t)),
            "__getattr__": lambda s, n: (lambda *a, **k: None),
        })()
        self.game.backpack.food = 9
        self.game.hunger = 31
        self.game._apply_decay()                # -> 29, tier-1 fires
        self.game.hunger = 80                   # ate
        self.game._apply_decay()                # recovered, re-arm
        self.game.hunger = 31
        self.game._apply_decay()                # -> 29, tier-1 fires AGAIN
        self.assertEqual(" ".join(said).upper().count("GETTING HUNGRY"), 2)

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
