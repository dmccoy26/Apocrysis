# G6 (Phase G, §8): a small set of player-global preferences in
# .apocrysis/settings.json, a real SettingsScreen, and four behaviours
# the game actually reads.

import asyncio
import json
import os
import shutil
import tempfile
import unittest

from src import settings

try:
    from src.tui import ApocrysisApp, MenuScreen, SettingsScreen, GameScreen
    from src.tui import _status_block
    _TEXTUAL_AVAILABLE = True
except ImportError:
    _TEXTUAL_AVAILABLE = False

from src.game import Apocrysis


class TestSettingsModule(unittest.TestCase):

    def setUp(self):
        self._home = tempfile.mkdtemp(prefix="apoc_set_")
        self._prev = os.environ.get("APOCRYSIS_HOME")
        os.environ["APOCRYSIS_HOME"] = self._home

    def tearDown(self):
        if self._prev is None:
            os.environ.pop("APOCRYSIS_HOME", None)
        else:
            os.environ["APOCRYSIS_HOME"] = self._prev
        shutil.rmtree(self._home, ignore_errors=True)

    def test_load_is_defaults_when_no_file(self):
        self.assertEqual(settings.load(), settings.DEFAULTS)

    def test_save_then_load_round_trips(self):
        settings.save({"play_log": True, "combat_card": "terse",
                       "command_hints": False, "hud_density": "compact"})
        self.assertEqual(settings.load(), {
            "play_log": True, "combat_card": "terse",
            "command_hints": False, "hud_density": "compact"})

    def test_load_tolerates_a_broken_or_partial_file(self):
        with open(settings._path(), "w") as f:
            f.write("{not json")
        self.assertEqual(settings.load(), settings.DEFAULTS)

        with open(settings._path(), "w") as f:
            json.dump({"play_log": "yes", "hud_density": "huge",
                       "command_hints": False}, f)
        got = settings.load()
        self.assertFalse(got["command_hints"])        # valid, applied
        self.assertEqual(got["play_log"], False)      # wrong type, ignored
        self.assertEqual(got["hud_density"], "full")  # bad enum, ignored

    def test_toggled_flips_bools_and_advances_enums(self):
        v = dict(settings.DEFAULTS)
        self.assertTrue(settings.toggled(v, "play_log")["play_log"])
        self.assertEqual(settings.toggled(v, "combat_card")["combat_card"],
                         "terse")
        self.assertEqual(
            settings.toggled({"combat_card": "terse"}, "combat_card")["combat_card"],
            "full")


@unittest.skipUnless(_TEXTUAL_AVAILABLE, "textual not installed")
class TestSettingsScreen(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self._home = tempfile.mkdtemp(prefix="apoc_set6_")
        self._prev = os.environ.get("APOCRYSIS_HOME")
        os.environ["APOCRYSIS_HOME"] = self._home
        Apocrysis.reset_campaign_state()

    async def asyncTearDown(self):
        await asyncio.sleep(0.2)
        if self._prev is None:
            os.environ.pop("APOCRYSIS_HOME", None)
        else:
            os.environ["APOCRYSIS_HOME"] = self._prev
        shutil.rmtree(self._home, ignore_errors=True)

    async def test_toggle_writes_the_file_and_updates_the_app_copy(self):
        app = ApocrysisApp(start_log=False)
        async with app.run_test(size=(120, 40)) as pilot:
            await asyncio.wait_for(pilot.pause(), timeout=5)
            ms = app.screen
            ms._sel = ms._items().index("SETTINGS")
            ms._render_items()
            await pilot.press("enter")
            await asyncio.wait_for(pilot.pause(0.4), timeout=5)
            ss = app.screen
            self.assertIsInstance(ss, SettingsScreen)

            await pilot.press("enter")               # toggle play_log
            await asyncio.wait_for(pilot.pause(0.2), timeout=5)
            self.assertTrue(json.load(open(settings._path()))["play_log"])

            await pilot.press("escape")
            await asyncio.wait_for(pilot.pause(0.3), timeout=5)
            self.assertIsInstance(app.screen, MenuScreen)
            self.assertTrue(app._settings["play_log"])


@unittest.skipUnless(_TEXTUAL_AVAILABLE, "textual not installed")
class TestGameReadsSettings(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self._home = tempfile.mkdtemp(prefix="apoc_setg_")
        self._prev = os.environ.get("APOCRYSIS_HOME")
        os.environ["APOCRYSIS_HOME"] = self._home
        Apocrysis.reset_campaign_state()

    async def asyncTearDown(self):
        await asyncio.sleep(0.2)
        if self._prev is None:
            os.environ.pop("APOCRYSIS_HOME", None)
        else:
            os.environ["APOCRYSIS_HOME"] = self._prev
        shutil.rmtree(self._home, ignore_errors=True)

    async def _boot(self, values):
        settings.save(values)
        app = ApocrysisApp(name="SetPlay", level=1, seed=1)
        return app

    async def test_command_hints_off_empties_the_actions_panel(self):
        app = await self._boot({**settings.DEFAULTS, "command_hints": False})
        async with app.run_test(size=(120, 40)) as pilot:
            await asyncio.wait_for(pilot.pause(), timeout=5)
            gs = app.screen
            self.assertEqual(gs._settings["command_hints"], False)
            gs.refresh_panels()
            self.assertEqual(
                str(gs.query_one("#commands_text").render()).strip(), "")

    async def test_play_log_setting_turns_the_transcript_on(self):
        app = await self._boot({**settings.DEFAULTS, "play_log": True})
        async with app.run_test(size=(120, 40)) as pilot:
            await asyncio.wait_for(pilot.pause(0.5), timeout=5)
            gs = app.screen
            self.assertTrue(gs._start_log)
            self.assertIsNotNone(getattr(gs.player, "playlog", None))

    async def test_combat_card_terse_propagates_to_the_player(self):
        app = await self._boot({**settings.DEFAULTS, "combat_card": "terse"})
        async with app.run_test(size=(120, 40)) as pilot:
            await asyncio.wait_for(pilot.pause(), timeout=5)
            self.assertEqual(app.screen.player._settings["combat_card"], "terse")

    def test_status_block_compact_collapses_warnings(self):
        from unittest.mock import patch
        with patch("builtins.print"):
            g = Apocrysis("Comp", map_size=12, seed=1)
        g.equipped_weapon = None          # forces a "no weapon" warning
        full = _status_block(g, compact=False)
        terse = _status_block(g, compact=True)
        self.assertIn("WARNINGS", full)
        self.assertNotIn("WARNINGS", terse)
        self.assertIn("no weapon equipped", terse)


if __name__ == "__main__":
    unittest.main(verbosity=2)
