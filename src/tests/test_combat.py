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
        from src.constants import DIFFICULTY_RAMP_LENGTH
        with patch("builtins.print"):
            game = Apocrysis("SmoothTest", map_size=8, seed=5)
        game.expeditions_completed = DIFFICULTY_RAMP_LENGTH // 2

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


class TestStatusEffectsOutOfCombat(unittest.TestCase):
    """1d bug: Bleeding / Poison only ticked inside combat rounds, so an
    effect left over from a fight sat frozen forever while exploring -
    visible, harmless, incurable. Now it ticks every game-turn and
    medicine treats it. Damage/duration numbers unchanged."""

    def setUp(self):
        with patch("builtins.print"):
            self.game = Apocrysis("StatusTest", map_size=8, seed=1)
        # keep the survivor off building tiles so heal-on-entry doesn't
        # mask the bleed damage
        g = self.game
        for row in g.map:
            for i, c in enumerate(row):
                if isinstance(c, dict) and c.get("terrain") == "building":
                    c["terrain"] = "plain"
        g.turns = 0

    def _walk(self, n):
        for _ in range(n):
            self.game.turns += 1
            self.game._tick_status_effects()

    def test_bleeding_ticks_while_walking(self):
        self.game.status_effects["Bleeding"] = 3
        hp = self.game.health
        self._walk(1)
        self.assertEqual(self.game.health, hp - 2)          # STATUS_EFFECT_DAMAGE
        self.assertEqual(self.game.status_effects["Bleeding"], 2)

    def test_poison_ticks_while_walking(self):
        from src.constants import STATUS_EFFECT_DAMAGE
        self.game.status_effects["Poison"] = 4
        hp = self.game.health
        self._walk(1)
        self.assertEqual(self.game.health, hp - STATUS_EFFECT_DAMAGE["Poison"])
        self.assertEqual(self.game.status_effects["Poison"], 3)

    def test_effects_expire_after_their_duration(self):
        self.game.status_effects["Bleeding"] = 3
        self._walk(3)
        self.assertNotIn("Bleeding", self.game.status_effects)

    def test_only_one_tick_per_game_turn(self):
        self.game.status_effects["Bleeding"] = 3
        self.game.turns = 5
        self.game._tick_status_effects()
        self.game._tick_status_effects()          # same turn - no-op
        self.game._tick_status_effects()
        self.assertEqual(self.game.status_effects["Bleeding"], 2)

    def test_medicine_clears_bleeding(self):
        self.game.status_effects["Bleeding"] = 3
        self.game.backpack.medicine = 1
        with patch("builtins.print"):
            self.game.use_medicine()
        self.assertNotIn("Bleeding", self.game.status_effects)

    def test_medicine_clears_poison(self):
        self.game.status_effects["Poison"] = 4
        self.game.backpack.medicine = 1
        with patch("builtins.print"):
            self.game.use_medicine()
        self.assertNotIn("Poison", self.game.status_effects)

    def test_medicine_does_not_clear_stun(self):
        self.game.status_effects["Stun"] = 1
        self.game.backpack.medicine = 1
        with patch("builtins.print"):
            self.game.use_medicine()
        self.assertIn("Stun", self.game.status_effects)

    def test_stun_counts_down_while_walking(self):
        self.game.status_effects["Stun"] = 1
        self._walk(1)
        self.assertNotIn("Stun", self.game.status_effects)

    def test_no_double_tick_when_a_move_walks_into_combat(self):
        # _tick_status_effects (from the move's _apply_decay) stamps the
        # game-turn; combat round 1 must then skip its own tick.
        self.game.status_effects["Bleeding"] = 3
        self.game.turns = 7
        self.game._tick_status_effects()                     # the move's decay tick
        self.assertEqual(self.game.status_effects["Bleeding"], 2)
        z = FreshZombie()
        z.health = 1                                         # 1 round, then it dies
        self.game.equipped_weapon = None
        self.game.strength = 100
        with patch("builtins.input", return_value="y"), patch("builtins.print"):
            self.game.encounter_zombie(z)
        # round 1 saw the stamp and skipped -> Bleeding is still at 2,
        # not 1 (no double-count for the turn the move started the fight)
        self.assertEqual(self.game.status_effects.get("Bleeding"), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
