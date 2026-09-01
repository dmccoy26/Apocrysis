# G3.2 (Phase G): MenuScreen wires CONTINUE + NEW CAMPAIGN; a real
# in-TUI NewCampaignScreen collects world + survivor + mode; the
# pre-Textual identity prompt is gone from cli.main_tui.
#
# Each test runs against a throwaway APOCRYSIS_HOME so campaign
# discovery (list_campaign_summaries) sees only what the test created.

import asyncio
import inspect
import os
import shutil
import tempfile
import unittest

try:
    from src.tui import (ApocrysisApp, MenuScreen, NewCampaignScreen,
                         LoadGameScreen, GameScreen)
    _TEXTUAL_AVAILABLE = True
except ImportError:
    _TEXTUAL_AVAILABLE = False

from src.game import Apocrysis


@unittest.skipUnless(_TEXTUAL_AVAILABLE, "textual not installed")
class TestShellScreens(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self._home = tempfile.mkdtemp(prefix="apoc_g32_")
        self._prev_home = os.environ.get("APOCRYSIS_HOME")
        os.environ["APOCRYSIS_HOME"] = self._home
        Apocrysis.reset_campaign_state()

    async def asyncTearDown(self):
        await asyncio.sleep(0.2)
        if self._prev_home is None:
            os.environ.pop("APOCRYSIS_HOME", None)
        else:
            os.environ["APOCRYSIS_HOME"] = self._prev_home
        shutil.rmtree(self._home, ignore_errors=True)

    async def _type(self, pilot, text):
        for ch in text:
            await pilot.press(ch)

    async def _select(self, screen, label):
        screen._sel = screen._items().index(label)
        screen._render_items()

    # ---- launch ---------------------------------------------------

    async def test_launch_with_no_name_lands_on_menu_only(self):
        app = ApocrysisApp(start_log=False)
        async with app.run_test(size=(120, 40)) as pilot:
            await asyncio.wait_for(pilot.pause(), timeout=5)
            self.assertIsInstance(app.screen, MenuScreen)
            self.assertFalse(any(isinstance(s, GameScreen)
                                 for s in app.screen_stack))

    async def test_no_campaigns_hides_continue(self):
        app = ApocrysisApp(start_log=False)
        async with app.run_test(size=(120, 40)) as pilot:
            await asyncio.wait_for(pilot.pause(), timeout=5)
            self.assertNotIn("CONTINUE", app.screen._items())

    # ---- NEW CAMPAIGN --------------------------------------------

    async def test_new_campaign_normal_creates_a_resumable_campaign(self):
        from src import runtime_paths
        from src.mixins.persistence_mixin import profile_filename_for_name
        app = ApocrysisApp(start_log=False)
        async with app.run_test(size=(120, 40)) as pilot:
            await asyncio.wait_for(pilot.pause(), timeout=5)
            await self._select(app.screen, "NEW CAMPAIGN")
            await pilot.press("enter")
            await asyncio.wait_for(pilot.pause(0.4), timeout=5)
            self.assertIsInstance(app.screen, NewCampaignScreen)

            nc = app.screen
            nc.query_one("#nc_name").focus()
            await self._type(pilot, "Rosa")
            await pilot.pause(0.1)
            nc._start()
            await asyncio.wait_for(pilot.pause(0.8), timeout=5)

            gs = app.screen
            self.assertIsInstance(gs, GameScreen)
            self.assertEqual(gs.player.name, "Rosa")
            self.assertFalse(gs.player.hardcore)
            # NewCampaignScreen was dismissed, not left on the stack.
            self.assertEqual(
                [type(s).__name__ for s in app.screen_stack],
                ["Screen", "MenuScreen", "GameScreen"])

            # menu -> the campaign is now on disk and offers CONTINUE.
            await self._type(pilot, "menu")
            await pilot.press("enter")
            await asyncio.wait_for(pilot.pause(0.8), timeout=5)
            self.assertIsInstance(app.screen, MenuScreen)
            path = runtime_paths.resolve(
                "player", profile_filename_for_name("Rosa"))
            self.assertTrue(os.path.exists(path))
            self.assertIn("CONTINUE", app.screen._items())

    async def test_new_campaign_can_pick_the_second_world_and_hardcore(self):
        app = ApocrysisApp(start_log=False)
        async with app.run_test(size=(120, 40)) as pilot:
            await asyncio.wait_for(pilot.pause(), timeout=5)
            await self._select(app.screen, "NEW CAMPAIGN")
            await pilot.press("enter")
            await asyncio.wait_for(pilot.pause(0.4), timeout=5)

            nc = app.screen
            second = nc._world_ids[1]
            # Select world #2 and Hardcore via the RadioButtons; the
            # RadioSet deselects the siblings.
            nc.query_one("#nc_world").children[1].value = True
            nc.query_one("#nc_mode").children[1].value = True
            await pilot.pause(0.1)
            self.assertEqual(nc.query_one("#nc_world").pressed_index, 1)
            self.assertEqual(nc.query_one("#nc_mode").pressed_index, 1)
            nc.query_one("#nc_name").focus()
            await self._type(pilot, "Vale")
            await pilot.pause(0.1)
            nc._start()
            await asyncio.wait_for(pilot.pause(0.8), timeout=5)

            gs = app.screen
            self.assertIsInstance(gs, GameScreen)
            self.assertEqual(gs.player.world.id, second)
            self.assertTrue(gs.player.hardcore)

    async def test_new_campaign_rejects_a_colliding_normal_name(self):
        from src import runtime_paths
        from src.mixins.persistence_mixin import profile_filename_for_name
        # Pre-seed a Normal profile on disk.
        Apocrysis("Dup", seed=1).save_profile(
            profile_filename_for_name("Dup"))

        app = ApocrysisApp(start_log=False)
        async with app.run_test(size=(120, 40)) as pilot:
            await asyncio.wait_for(pilot.pause(), timeout=5)
            await self._select(app.screen, "NEW CAMPAIGN")
            await pilot.press("enter")
            await asyncio.wait_for(pilot.pause(0.4), timeout=5)

            nc = app.screen
            nc.query_one("#nc_name").focus()
            await self._type(pilot, "Dup")
            await pilot.pause(0.1)
            nc._start()
            await asyncio.wait_for(pilot.pause(0.4), timeout=5)

            self.assertIsInstance(app.screen, NewCampaignScreen)
            self.assertIn("already has a campaign",
                          str(nc.query_one("#nc_error").render()))

    # ---- CONTINUE ------------------------------------------------

    async def test_continue_resumes_the_newest_campaign(self):
        from src.mixins.persistence_mixin import profile_filename_for_name
        import time
        older = Apocrysis("Older", seed=1)
        older.save_profile(profile_filename_for_name("Older"))
        time.sleep(0.05)
        newer = Apocrysis("Newer", seed=2)
        newer.save_profile(profile_filename_for_name("Newer"))

        app = ApocrysisApp(start_log=False)
        async with app.run_test(size=(120, 40)) as pilot:
            await asyncio.wait_for(pilot.pause(), timeout=5)
            ms = app.screen
            await self._select(ms, "CONTINUE")
            await pilot.press("enter")            # arm (show card)
            await asyncio.wait_for(pilot.pause(0.2), timeout=5)
            self.assertEqual(ms._armed, "continue")
            self.assertIn("Newer", str(ms.query_one("#menu_note").render()))
            await pilot.press("enter")            # confirm
            await asyncio.wait_for(pilot.pause(0.8), timeout=5)

            self.assertIsInstance(app.screen, GameScreen)
            self.assertEqual(app.screen.player.name, "Newer")

    async def test_continue_skips_a_finished_campaign(self):
        from src.mixins.persistence_mixin import profile_filename_for_name
        g = Apocrysis("Done", seed=1)
        Apocrysis._campaign_ending = "the_broadcast"
        g.save_profile(profile_filename_for_name("Done"))
        Apocrysis.reset_campaign_state()

        app = ApocrysisApp(start_log=False)
        async with app.run_test(size=(120, 40)) as pilot:
            await asyncio.wait_for(pilot.pause(), timeout=5)
            # Only a finished campaign exists -> no CONTINUE.
            self.assertNotIn("CONTINUE", app.screen._items())


@unittest.skipUnless(_TEXTUAL_AVAILABLE, "textual not installed")
class TestLoadGameScreen(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self._home = tempfile.mkdtemp(prefix="apoc_g4_")
        self._prev_home = os.environ.get("APOCRYSIS_HOME")
        os.environ["APOCRYSIS_HOME"] = self._home
        Apocrysis.reset_campaign_state()

    async def asyncTearDown(self):
        await asyncio.sleep(0.2)
        if self._prev_home is None:
            os.environ.pop("APOCRYSIS_HOME", None)
        else:
            os.environ["APOCRYSIS_HOME"] = self._prev_home
        shutil.rmtree(self._home, ignore_errors=True)

    def _seed(self, *names):
        import time
        from src.mixins.persistence_mixin import profile_filename_for_name
        for n in names:
            Apocrysis(n, seed=1).save_profile(profile_filename_for_name(n))
            time.sleep(0.03)

    async def _open_load(self, pilot, app):
        ms = app.screen
        ms._sel = ms._items().index("LOAD GAME")
        ms._render_items()
        await pilot.press("enter")
        await asyncio.wait_for(pilot.pause(0.4), timeout=5)
        return app.screen

    async def test_lists_campaigns_newest_first_and_loads_one(self):
        self._seed("Ada", "Cole")            # Cole newest
        app = ApocrysisApp(start_log=False)
        async with app.run_test(size=(120, 40)) as pilot:
            await asyncio.wait_for(pilot.pause(), timeout=5)
            lg = await self._open_load(pilot, app)
            self.assertIsInstance(lg, LoadGameScreen)
            self.assertEqual([r["name"] for r in lg._rows], ["Cole", "Ada"])

            lg._sel = 1                       # Ada
            lg._render_rows()
            await pilot.press("enter")
            await asyncio.wait_for(pilot.pause(0.8), timeout=5)
            self.assertIsInstance(app.screen, GameScreen)
            self.assertEqual(app.screen.player.name, "Ada")

    async def test_delete_is_two_press_and_removes_the_file(self):
        from src import runtime_paths
        from src.mixins.persistence_mixin import profile_filename_for_name
        self._seed("Ada", "Cole")
        app = ApocrysisApp(start_log=False)
        async with app.run_test(size=(120, 40)) as pilot:
            await asyncio.wait_for(pilot.pause(), timeout=5)
            lg = await self._open_load(pilot, app)

            await pilot.press("d")            # arm
            await asyncio.wait_for(pilot.pause(0.1), timeout=5)
            self.assertEqual(lg._armed_delete[1], "Cole")
            path = runtime_paths.resolve(
                "player", profile_filename_for_name("Cole"))
            self.assertTrue(os.path.exists(path))

            await pilot.press("d")            # confirm
            await asyncio.wait_for(pilot.pause(0.3), timeout=5)
            self.assertFalse(os.path.exists(path))
            self.assertEqual([r["name"] for r in lg._rows], ["Ada"])

    async def test_moving_the_cursor_disarms_a_pending_delete(self):
        self._seed("Ada", "Cole")
        app = ApocrysisApp(start_log=False)
        async with app.run_test(size=(120, 40)) as pilot:
            await asyncio.wait_for(pilot.pause(), timeout=5)
            lg = await self._open_load(pilot, app)
            await pilot.press("d")
            await asyncio.wait_for(pilot.pause(0.1), timeout=5)
            self.assertEqual(lg._armed_delete[1], "Cole")
            await pilot.press("down")
            await asyncio.wait_for(pilot.pause(0.1), timeout=5)
            self.assertIsNone(lg._armed_delete)

    async def test_finished_campaign_appears_marked_done(self):
        from src.mixins.persistence_mixin import profile_filename_for_name
        g = Apocrysis("Fin", seed=1)
        Apocrysis._campaign_ending = "the_broadcast"
        g.save_profile(profile_filename_for_name("Fin"))
        Apocrysis.reset_campaign_state()

        app = ApocrysisApp(start_log=False)
        async with app.run_test(size=(120, 40)) as pilot:
            await asyncio.wait_for(pilot.pause(), timeout=5)
            lg = await self._open_load(pilot, app)
            self.assertEqual([r["name"] for r in lg._rows], ["Fin"])
            self.assertIn("DONE", str(lg.query_one("#lg_rows").render()))

    async def test_empty_list_backs_out_to_menu(self):
        app = ApocrysisApp(start_log=False)
        async with app.run_test(size=(120, 40)) as pilot:
            await asyncio.wait_for(pilot.pause(), timeout=5)
            lg = await self._open_load(pilot, app)
            self.assertEqual(lg._rows, [])
            self.assertIn("No saved campaigns",
                          str(lg.query_one("#lg_rows").render()))
            await pilot.press("escape")
            await asyncio.wait_for(pilot.pause(0.3), timeout=5)
            self.assertIsInstance(app.screen, MenuScreen)


@unittest.skipUnless(_TEXTUAL_AVAILABLE, "textual not installed")
class TestShellDecoupling(unittest.TestCase):

    def test_main_tui_has_no_pre_textual_identity_prompt(self):
        from src import cli
        src = inspect.getsource(cli.main_tui)
        self.assertNotIn("_resolve_player_identity(", src)
        # the only input() left in main_tui is the --dev "press Enter".
        self.assertEqual(src.count("input("), 1)

    def test_shell_screens_carry_no_world_fiction(self):
        from src import tui
        for cls in (tui.MenuScreen, tui.NewCampaignScreen, tui.LoadGameScreen,
                    tui.SettingsScreen):
            src = inspect.getsource(cls).lower()
            for needle in ("silence", "the_wake", "the wake", "valley",
                           "world.id =="):
                self.assertNotIn(needle, src, f"{cls.__name__} / {needle}")

    def test_list_campaign_summaries_is_newest_first_with_world_title(self):
        import tempfile, shutil, time
        home = tempfile.mkdtemp(prefix="apoc_lcs_")
        prev = os.environ.get("APOCRYSIS_HOME")
        os.environ["APOCRYSIS_HOME"] = home
        try:
            from src.mixins.persistence_mixin import profile_filename_for_name
            Apocrysis.reset_campaign_state()
            Apocrysis("A", seed=1).save_profile(profile_filename_for_name("A"))
            time.sleep(0.05)
            Apocrysis("B", seed=1).save_profile(profile_filename_for_name("B"))
            rows = Apocrysis.list_campaign_summaries()
            self.assertEqual([r["name"] for r in rows], ["B", "A"])
            self.assertTrue(all(r["world_title"] for r in rows))
        finally:
            if prev is None:
                os.environ.pop("APOCRYSIS_HOME", None)
            else:
                os.environ["APOCRYSIS_HOME"] = prev
            shutil.rmtree(home, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
