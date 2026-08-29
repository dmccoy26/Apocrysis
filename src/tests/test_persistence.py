import asyncio
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from src.constants import TERRAIN_SYMBOLS
from src.game import Apocrysis
from src.items import Backpack, MeleeWeapon, RangedWeapon, Armor
from src.mixins.persistence_mixin import (
    profile_filename_for_name, clean_display_name,
)
from src.player import PlayerClass
from src.text_utils import _visible_len, _display_ljust
from src.zombies import (
    FreshZombie, RegularZombie, HeavyZombie,
    SwiftZombie, ToxicZombie, ArmoredZombie,
)



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
        self.assertEqual(profile["survivor"]["name"], "ProfileTest")
        self.assertEqual(profile["survivor"]["level"], 7)
        self.assertEqual(profile["survivor"]["xp"], 42)
        self.assertEqual(profile["survivor"]["strength"], 20)
        self.assertEqual(profile["survivor"]["backpack_food"], 5)

    def test_apply_profile_preserves_win_prize_on_top_of_saved_backpack(self):
        # A prize_for_next_game bonus applied by __init__ must survive
        # apply_profile() - v4 records it on self._prize_bonus and
        # re-adds it after SETting the backpack from the profile.
        with patch("builtins.print"):
            source = Apocrysis("ProfileTest", map_size=8, seed=1)
        source.backpack.food = 9
        source.level = 5
        source.save_profile(self.PROFILE_FILE)
        profile = Apocrysis.load_profile(self.PROFILE_FILE)

        Apocrysis.prize_for_next_game = True
        try:
            with patch("builtins.print"):
                fresh = Apocrysis("ProfileTest", map_size=8, level=5, seed=2)
        finally:
            Apocrysis.prize_for_next_game = False

        fresh.apply_profile(profile)

        # 9 saved + 10 prize
        self.assertEqual(fresh.backpack.food, 19)
        self.assertEqual(fresh.level, 5)

    def test_escape_story_history_survives_quit_and_relaunch(self):
        # A kid playing one expedition per sitting got power_station
        # twice - _used_mechanisms / _last_family were session-only.
        Apocrysis._used_mechanisms = ["power_station"]
        Apocrysis._last_family = "infrastructural"
        try:
            with patch("builtins.print"):
                won = Apocrysis("ProfileTest", map_size=8, seed=1)
            won.save_profile(self.PROFILE_FILE)
            profile = Apocrysis.load_profile(self.PROFILE_FILE)
            self.assertEqual(profile["campaign"]["used_mechanisms"], ["power_station"])
            self.assertEqual(profile["campaign"]["last_family"], "infrastructural")

            # simulate an app restart: class state wiped
            Apocrysis._used_mechanisms = []
            Apocrysis._last_family = None
            with patch("builtins.print"):
                relaunched = Apocrysis("ProfileTest", map_size=8, seed=2)
            relaunched.apply_profile(profile)
            self.assertEqual(Apocrysis._used_mechanisms, ["power_station"])
            self.assertEqual(Apocrysis._last_family, "infrastructural")

            # and choose_mechanism now refuses the whole infra family
            from src.escape import choose_mechanism, MECHANISMS
            import random
            for i in range(40):
                pick = choose_mechanism(random.Random(i),
                                        Apocrysis._used_mechanisms,
                                        Apocrysis._last_family)
                self.assertNotEqual(MECHANISMS[pick]["family"], "infrastructural")
        finally:
            Apocrysis._used_mechanisms = []
            Apocrysis._last_family = None


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

    def test_clean_display_name_strips_markup_and_backslashes(self):
        # a stray '\' or '[' in the name corrupts the Rich HUD
        # (f"[bold]{name}[/bold]") and desyncs the profile slug.
        self.assertEqual(clean_display_name("Balthus\\"), "Balthus")
        self.assertEqual(clean_display_name("[red]Ada[/]"), "redAda")
        self.assertEqual(clean_display_name("  Jo   Anne  "), "Jo Anne")
        self.assertEqual(clean_display_name("O'Brien-7"), "O'Brien-7")
        self.assertEqual(clean_display_name(""), "Survivor")
        self.assertEqual(clean_display_name("\\\\"), "Survivor")
        self.assertLessEqual(len(clean_display_name("x" * 50)), 24)

    def test_save_profile_persists_hardcore_flag(self):
        with patch("builtins.print"):
            game = Apocrysis("HCTest", map_size=8, seed=1, hardcore=True)

        filename = profile_filename_for_name(game.name)
        game.save_profile(filename)
        profile = Apocrysis.load_profile(filename)

        self.assertTrue(profile["campaign"]["hardcore"])

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
        self.assertTrue(bob_profile["campaign"]["hardcore"])

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
