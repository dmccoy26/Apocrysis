# G7 (Phase G): the acceptance pass (docs/PHASE_G_PLAYER_SHELL.md §9).
#
#   - the full no-flag loop: launch -> NEW CAMPAIGN -> play -> Return to
#     Menu -> LOAD -> resume -> SETTINGS -> toggle -> Continue
#   - the World-3 seam: a third world dropped into F's registry is
#     offered, created, listed and loaded by the shell with ZERO shell
#     code change, and no shell screen names a world.
#
# The §6 worker-lifecycle and §7 state-reset criteria have their own
# files (test_game_lifecycle.py, test_campaign_switching.py).

import asyncio
import inspect
import os
import shutil
import tempfile
import unittest

import src.worlds as _worlds_mod
from src.game import Apocrysis
from src.mixins.persistence_mixin import profile_filename_for_name

try:
    from src.tui import (ApocrysisApp, MenuScreen, NewCampaignScreen,
                         LoadGameScreen, SettingsScreen, GameScreen)
    from src.tests.test_phase_f_seam import COVE
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


async def _type(pilot, text):
    for ch in text:
        await pilot.press(ch)


@unittest.skipUnless(_AVAILABLE, "textual not installed")
class TestFullNoFlagLoop(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self._home = tempfile.mkdtemp(prefix="apoc_g7loop_")
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

    async def _menu_pick(self, app, pilot, label):
        ms = app.screen
        self.assertIsInstance(ms, MenuScreen)
        ms._sel = ms._items().index(label)
        ms._render_items()
        await pilot.press("enter")
        await asyncio.wait_for(pilot.pause(0.4), timeout=5)

    async def _to_menu(self, app, pilot):
        await _type(pilot, "menu")
        await pilot.press("enter")
        # The worker persists + tears down + pops on its own thread;
        # under load that can take more than a fixed pause. Poll.
        for _ in range(40):
            await asyncio.wait_for(pilot.pause(0.15), timeout=5)
            if isinstance(app.screen, MenuScreen):
                return
        self.assertIsInstance(app.screen, MenuScreen)

    async def test_launch_new_play_menu_load_settings_continue(self):
        # No name, no --flags: exactly what `apocrysis` with no args does.
        app = ApocrysisApp(start_log=False)
        async with app.run_test(size=(120, 40)) as pilot:
            await asyncio.wait_for(pilot.pause(), timeout=5)
            self.assertIsInstance(app.screen, MenuScreen)
            self.assertNotIn("CONTINUE", app.screen._items())

            # --- NEW CAMPAIGN: world + name + mode ---
            await self._menu_pick(app, pilot, "NEW CAMPAIGN")
            nc = app.screen
            self.assertIsInstance(nc, NewCampaignScreen)
            nc.query_one("#nc_name").focus()
            await _type(pilot, "Pilot")
            await pilot.pause(0.1)
            nc._start()
            await asyncio.wait_for(pilot.pause(1.0), timeout=8)
            gs = app.screen
            self.assertIsInstance(gs, GameScreen)
            self.assertEqual(gs.player.name, "Pilot")
            self.assertFalse(gs.player.hardcore)

            # --- play an expedition turn ---
            t0 = gs.player.turns
            await pilot.press("right")
            await asyncio.wait_for(pilot.pause(0.5), timeout=5)
            self.assertEqual(gs.player.turns, t0 + 1)

            # --- Return to Menu (autosaves) ---
            await self._to_menu(app, pilot)
            self.assertTrue(os.path.exists(_profile("Pilot")))
            self.assertIn("CONTINUE", app.screen._items())

            # --- LOAD GAME -> resume ---
            await self._menu_pick(app, pilot, "LOAD GAME")
            lg = app.screen
            self.assertIsInstance(lg, LoadGameScreen)
            lg._sel = [r["name"] for r in lg._rows].index("Pilot")
            lg._render_rows()
            await pilot.press("enter")
            await asyncio.wait_for(pilot.pause(1.0), timeout=8)
            self.assertIsInstance(app.screen, GameScreen)
            self.assertEqual(app.screen.player.name, "Pilot")

            await self._to_menu(app, pilot)

            # --- SETTINGS -> toggle -> back ---
            before = dict(app._settings)
            await self._menu_pick(app, pilot, "SETTINGS")
            self.assertIsInstance(app.screen, SettingsScreen)
            await pilot.press("enter")          # toggle play_log
            await asyncio.wait_for(pilot.pause(0.2), timeout=5)
            await pilot.press("escape")
            await asyncio.wait_for(pilot.pause(0.3), timeout=5)
            self.assertIsInstance(app.screen, MenuScreen)
            self.assertNotEqual(app._settings, before)

            # --- CONTINUE ---
            ms = app.screen
            ms._sel = ms._items().index("CONTINUE")
            ms._render_items()
            await pilot.press("enter")          # arm
            await asyncio.wait_for(pilot.pause(0.2), timeout=5)
            await pilot.press("enter")          # resume
            await asyncio.wait_for(pilot.pause(1.0), timeout=8)
            self.assertIsInstance(app.screen, GameScreen)
            self.assertEqual(app.screen.player.name, "Pilot")


def _profile(name):
    from src import runtime_paths
    return runtime_paths.resolve("player", profile_filename_for_name(name))


@unittest.skipUnless(_AVAILABLE, "textual not installed")
class TestWorldThreeSeamThroughShell(unittest.IsolatedAsyncioTestCase):
    """A third world - the hostile Testcove fixture - dropped into F's
    registry. The shell must offer / create / list / load it with no
    change to a single shell class."""

    async def asyncSetUp(self):
        self._home = tempfile.mkdtemp(prefix="apoc_g7w3_")
        self._prev = os.environ.get("APOCRYSIS_HOME")
        os.environ["APOCRYSIS_HOME"] = self._home
        Apocrysis.reset_campaign_state()
        self._orig_worlds = dict(_worlds_mod.WORLDS)
        _worlds_mod.WORLDS[COVE.id] = COVE

    async def asyncTearDown(self):
        await asyncio.sleep(0.2)
        _worlds_mod.WORLDS.clear()
        _worlds_mod.WORLDS.update(self._orig_worlds)
        Apocrysis.reset_campaign_state()
        if self._prev is None:
            os.environ.pop("APOCRYSIS_HOME", None)
        else:
            os.environ["APOCRYSIS_HOME"] = self._prev
        shutil.rmtree(self._home, ignore_errors=True)

    async def test_third_world_is_offered_created_listed_and_loaded(self):
        app = ApocrysisApp(start_log=False)
        async with app.run_test(size=(120, 40)) as pilot:
            await asyncio.wait_for(pilot.pause(), timeout=5)

            ms = app.screen
            ms._sel = ms._items().index("NEW CAMPAIGN")
            ms._render_items()
            await pilot.press("enter")
            await asyncio.wait_for(pilot.pause(0.4), timeout=5)

            nc = app.screen
            self.assertIn("testcove", nc._world_ids)
            i = nc._world_ids.index("testcove")
            nc.query_one("#nc_world").children[i].value = True
            await pilot.pause(0.1)
            nc.query_one("#nc_name").focus()
            await _type(pilot, "Wren")
            await pilot.pause(0.1)
            nc._start()
            await asyncio.wait_for(pilot.pause(1.0), timeout=8)

            gs = app.screen
            self.assertIsInstance(gs, GameScreen)
            self.assertEqual(gs.player.world.id, "testcove")

            # back to menu -> the campaign is on disk under its world
            await _type(pilot, "menu")
            await pilot.press("enter")
            await asyncio.wait_for(pilot.pause(1.0), timeout=8)

            rows = Apocrysis.list_campaign_summaries()
            wren = next(r for r in rows if r["name"] == "Wren")
            self.assertEqual(wren["world_id"], "testcove")
            self.assertEqual(wren["world_title"], "Testcove")

            # LOAD it back
            ms = app.screen
            ms._sel = ms._items().index("LOAD GAME")
            ms._render_items()
            await pilot.press("enter")
            await asyncio.wait_for(pilot.pause(0.4), timeout=5)
            lg = app.screen
            lg._sel = [r["name"] for r in lg._rows].index("Wren")
            lg._render_rows()
            await pilot.press("enter")
            await asyncio.wait_for(pilot.pause(1.0), timeout=8)
            self.assertEqual(app.screen.player.world.id, "testcove")


@unittest.skipUnless(_AVAILABLE, "textual not installed")
class TestShellNamesNoWorld(unittest.TestCase):

    def test_no_shell_class_names_a_world(self):
        from src import tui
        classes = (tui.MenuScreen, tui.NewCampaignScreen, tui.LoadGameScreen,
                   tui.SettingsScreen, tui.GameScreen, tui.ApocrysisApp)
        for cls in classes:
            src = inspect.getsource(cls)
            self.assertNotIn("world.id ==", src, cls.__name__)
            low = src.lower()
            for wid in ("silence", "the_wake", "testcove", "the wake"):
                self.assertNotIn(f'"{wid}"', low, f"{cls.__name__} / {wid}")
                self.assertNotIn(f"'{wid}'", low, f"{cls.__name__} / {wid}")


@unittest.skipUnless(_AVAILABLE, "textual not installed")
class TestShellScreensRenderVisibly(unittest.IsolatedAsyncioTestCase):
    """Regression: the shell screens must put their content ON SCREEN,
    not just in the DOM. MenuScreen once mounted with a width:auto box
    whose auto-width computed to 0 (empty Static at first layout) - the
    DOM was correct, every functional test passed, and the real
    terminal showed an empty bordered box. These assert the compositor
    output, not query_one(...).render()."""

    async def asyncSetUp(self):
        self._home = tempfile.mkdtemp(prefix="apoc_g7vis_")
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

    @staticmethod
    def _visible(app):
        import re
        svg = app.export_screenshot()
        runs = re.findall(r">([^<>]+)</text>", svg)
        return " ".join(runs).replace("&#160;", " ").replace("\xa0", " ")

    async def test_menu_and_each_shell_screen_shows_its_content(self):
        app = ApocrysisApp(start_log=False)
        async with app.run_test(size=(110, 34)) as pilot:
            await asyncio.wait_for(pilot.pause(), timeout=5)
            await asyncio.wait_for(pilot.pause(), timeout=5)

            seen = self._visible(app)
            self.assertIn("REMEMBERS", seen, "MenuScreen title not rendering")
            for word in ("NEW CAMPAIGN", "LOAD GAME", "SETTINGS", "QUIT"):
                self.assertIn(word, seen, f"MenuScreen not rendering: {word}")

            ms = app.screen
            ms._sel = ms._items().index("NEW CAMPAIGN")
            ms._render_items()
            await pilot.press("enter")
            await asyncio.wait_for(pilot.pause(0.4), timeout=5)
            seen = self._visible(app)
            for word in ("WORLD", "SURVIVOR", "MODE", "START CAMPAIGN"):
                self.assertIn(word, seen, f"NewCampaignScreen not rendering: {word}")
            await pilot.press("escape")
            await asyncio.wait_for(pilot.pause(0.3), timeout=5)

            ms = app.screen
            ms._sel = ms._items().index("SETTINGS")
            ms._render_items()
            await pilot.press("enter")
            await asyncio.wait_for(pilot.pause(0.4), timeout=5)
            seen = self._visible(app)
            for word in ("Play log", "Combat card", "HUD density"):
                self.assertIn(word, seen, f"SettingsScreen not rendering: {word}")


@unittest.skipUnless(_AVAILABLE, "textual not installed")
class TestAcceptanceInvariants(unittest.TestCase):

    def test_main_tui_path_has_no_pre_textual_input(self):
        from src import cli
        src = inspect.getsource(cli.main_tui)
        # only the --dev "press Enter" input() survives
        self.assertEqual(src.count("input("), 1)
        self.assertNotIn("_resolve_player_identity(", src)

    def test_reset_and_lifecycle_test_files_exist(self):
        import importlib
        for mod in ("src.tests.test_game_lifecycle",
                    "src.tests.test_campaign_switching"):
            self.assertTrue(importlib.import_module(mod))


if __name__ == "__main__":
    unittest.main(verbosity=2)
