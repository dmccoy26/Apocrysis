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

        import re
        _ansi = re.compile(r"\x1b\[[0-9;]*m")

        def _tile_char(lines, tx, ty):
            # The map renders as a bare grid (no header / gutter /
            # border) - row ty, column tx. Glyphs are ANSI-tinted, so
            # strip codes; each tile is glyph + space (MAP_REALISM_SPEC
            # Fix A), so the visible column is tx * 2.
            return _ansi.sub("", lines[ty])[tx * 2]

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

    def test_empty_ammo_alarms_only_for_the_equipped_weapon(self):
        # bug: a benched Gun at 0 rounds rendered its "ammo 0/5" in red,
        # reading as a warning about a weapon you aren't holding.
        from src.tui import _fmt_gear
        gun = RangedWeapon("Gun", 20, 5)
        gun.ammo = 0
        self.assertIn("[red]ammo 0/5[/]", _fmt_gear(gun, equipped=True))
        self.assertNotIn("[red]", _fmt_gear(gun))          # in the pack
        gun.ammo = 3
        self.assertNotIn("[red]", _fmt_gear(gun, equipped=True))

    def test_print_help_is_a_static_player_facing_reference(self):
        # print_help is now a fixed controls reference (not a
        # conditional list): it always names the core verbs, teaches
        # WASD, and does not advertise the v3 debug leftovers.
        with patch("builtins.print") as mock_print:
            self.game.print_help()
        printed = "\n".join(str(c.args[0]) for c in mock_print.call_args_list if c.args)
        for verb in ("Move", "eat", "drink", "journal", "think", "escape", "equip"):
            self.assertIn(verb, printed)
        for leftover in ("goals", "complete", "auto"):
            self.assertNotIn(leftover, printed)


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

            original_player = app.screen.player
            app.screen.player.won = True
            app.screen.player.health = 100

            # Re-enter run_game_loop() so it sees won=True and exits
            # the while loop into the victory/continue-prompt path.
            # Type 'l' (look) + Enter: completes the current iteration
            # without moving (so no chance of a random encounter); the
            # loop condition then sees won=True.
            await asyncio.wait_for(pilot.press("l", "enter"), timeout=5)
            await asyncio.wait_for(pilot.pause(0.5), timeout=5)

            self.assertEqual(
                app.screen.query_one("#command_input").placeholder,
                "Press Enter to continue...",
            )

            # The continue prompt: the box is focused, Enter submits.
            await asyncio.wait_for(pilot.press("enter"), timeout=5)
            await asyncio.wait_for(pilot.pause(0.5), timeout=5)

            self.assertTrue(app.is_running, "app exited instead of starting a new game")
            self.assertIsNot(app.screen.player, original_player)
            self.assertFalse(app.screen.player.won)


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

            inp = app.screen.query_one("#command_input")
            inp.focus()
            await asyncio.wait_for(pilot.pause(), timeout=5)

            # Player typed "n" meaning "move north" but hasn't hit
            # Enter yet.
            inp.value = "n"

            # The prompt changes underneath them - e.g. a zombie
            # encounter's fight decision.
            app.screen.request_input("Do you want to fight? (y/n)")

            self.assertEqual(
                inp.value, "",
                "stale unsent text survived a prompt change - it would "
                "be submitted as the answer to the NEW prompt, not the "
                "one the player actually typed it for",
            )
            self.assertEqual(inp.placeholder, "Do you want to fight? (y/n)")


if __name__ == "__main__":
    unittest.main(verbosity=2)
