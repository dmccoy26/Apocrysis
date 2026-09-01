# G2 (Phase G): the GameClosed lifecycle signal.
#
# G1 put the game body inside a Textual Screen. G2 teaches the worker
# that a *game session* can end while the *application* stays alive -
# a second, distinct shutdown signal (GameClosed) alongside AppClosed.
#
# This file is the G2 acceptance boundary, numbered to match
# PHASE_G_PLAYER_SHELL.md's list:
#   1  a worker blocked in request_input() is released by GameClosed
#   2  every specialised prompt path is released (ask / ask_yes_no /
#      ask_commit / ask_combat_letter - and the P1 gates, which call
#      ask_commit, so the same code path)
#   3  GameClosed cannot masquerade as AppClosed
#   4  Normal GameClosed saves exactly once
#   5  Hardcore GameClosed (alive) writes nothing
#   6  the worker actually terminates
#   7  the answer queue doesn't carry into a future session
#   8  session-local machinery (_expecting_command, playlog) left clean
#   9  AppClosed's existing behaviour is unchanged
#   10 repeated lifecycle cycles don't accumulate threads/queues

import asyncio
import os
import shutil
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from src import runtime_paths
from src.mixins.persistence_mixin import profile_filename_for_name


def _profile_path(name):
    return runtime_paths.resolve("player", profile_filename_for_name(name))

try:
    from src.tui import (ApocrysisApp, GameScreen, MenuScreen, TextualIO,
                         AppClosed, GameClosed)
    _TEXTUAL_AVAILABLE = True
except ImportError:
    _TEXTUAL_AVAILABLE = False


# --------------------------------------------------------------------
# Unit: TextualIO's blocking prompt paths, driven directly with a stub
# host so every path can be exercised without steering the real game
# into a combat encounter / y-n dialog.
# --------------------------------------------------------------------

class _StubApp:
    def __init__(self):
        self.is_running = True

    def call_from_thread(self, fn, *a, **k):
        return fn(*a, **k)


class _StubHost:
    def __init__(self):
        self.app = _StubApp()
        self._session_closing = threading.Event()

    def request_input(self, prompt):
        pass

    def log_message(self, text):
        pass


@unittest.skipUnless(_TEXTUAL_AVAILABLE, "textual not installed")
class TestTextualIOReleasePaths(unittest.TestCase):

    def _assert_released(self, call, *, close=True, stop_app=False):
        host = _StubHost()
        io = TextualIO(host)
        out = {}

        def run():
            try:
                call(io)
            except GameClosed:
                out["signal"] = "game"
            except AppClosed:
                out["signal"] = "app"
            except BaseException as exc:  # pragma: no cover
                out["signal"] = repr(exc)

        t = threading.Thread(target=run, daemon=True)
        t.start()
        time.sleep(0.25)
        self.assertTrue(t.is_alive(), "prompt returned early on its own")
        if stop_app:
            host.app.is_running = False
        if close:
            host._session_closing.set()
        t.join(timeout=3)
        self.assertFalse(t.is_alive(), "worker never released")
        return out.get("signal")

    def test_1_ask_command_prompt_released(self):
        self.assertEqual(self._assert_released(lambda io: io.ask("> ")), "game")

    def test_2_ask_yes_no_released(self):
        self.assertEqual(
            self._assert_released(lambda io: io.ask_yes_no("Fight?")), "game")

    def test_2_ask_commit_released(self):
        # commit_gate() -> io.ask_commit(): also the P1 intervention gates.
        self.assertEqual(
            self._assert_released(lambda io: io.ask_commit("Proceed?")), "game")

    def test_2_ask_combat_letter_released(self):
        self.assertEqual(
            self._assert_released(lambda io: io.ask_combat_letter()), "game")

    def test_3_and_9_app_shutdown_still_reads_as_appclosed(self):
        # Even with BOTH conditions true, is_running is checked first -
        # a real app teardown never gets downgraded to GameClosed.
        sig = self._assert_released(lambda io: io.ask("> "),
                                    close=True, stop_app=True)
        self.assertEqual(sig, "app")

    def test_9_appclosed_alone_unchanged(self):
        sig = self._assert_released(lambda io: io.ask("> "),
                                    close=False, stop_app=True)
        self.assertEqual(sig, "app")


# --------------------------------------------------------------------
# Integration: the real app + GameScreen + worker thread.
# --------------------------------------------------------------------

@unittest.skipUnless(_TEXTUAL_AVAILABLE, "textual not installed")
class TestGameClosedLifecycle(unittest.IsolatedAsyncioTestCase):

    _NAMES = ("G2Normal", "G2Hard", "G2Neg", "G2NegTwo", "G2Cycle", "G2Once")

    def _clean(self):
        for n in self._NAMES:
            f = _profile_path(n)
            if os.path.exists(f):
                os.remove(f)

    async def asyncSetUp(self):
        # Other suites (test_finale, story playthroughs) leave the
        # Apocrysis campaign class-vars populated - e.g.
        # prize_for_next_game, which makes Apocrysis.__init__ emit a
        # line, which _new_player() on the app thread cannot marshal.
        # G5 owns the real reset contract; here we just start clean.
        from src.game import Apocrysis
        Apocrysis.reset_campaign_state()
        self._clean()

    async def asyncTearDown(self):
        await asyncio.sleep(0.3)
        self._clean()

    async def test_3_6_close_game_ends_session_app_survives(self):
        app = ApocrysisApp(name="G2Neg", level=1, seed=1)
        async with app.run_test(size=(130, 48)) as pilot:
            await asyncio.wait_for(pilot.pause(), timeout=5)
            gs = app.screen
            self.assertIsInstance(gs, GameScreen)
            worker = gs._game_worker
            self.assertIsNotNone(worker)

            await asyncio.wait_for(gs.close_game(), timeout=8)

            self.assertTrue(app.is_running, "app exited on GameClosed (#3)")
            self.assertTrue(worker.is_finished, "worker did not terminate (#6)")
            self.assertIsNone(gs._game_worker)
            # G3: GameScreen popped, revealing the MenuScreen beneath.
            self.assertIsInstance(app.screen, MenuScreen)
            self.assertNotIn(gs, app.screen_stack)
            # #8: session-local flag cleared, close event reset.
            self.assertFalse(gs._expecting_command)
            self.assertFalse(gs._session_closing.is_set())

    async def test_4_normal_session_saves_exactly_once(self):
        from src.game import Apocrysis
        app = ApocrysisApp(name="G2Once", level=1, seed=1)
        async with app.run_test(size=(130, 48)) as pilot:
            await asyncio.wait_for(pilot.pause(), timeout=5)
            gs = app.screen
            self.assertGreater(gs.player.health, 0)

            real_save = Apocrysis.save_profile
            calls = []

            def counting_save(self, *a, **k):
                calls.append(1)
                return real_save(self, *a, **k)

            with patch.object(Apocrysis, "save_profile", counting_save):
                await asyncio.wait_for(gs.close_game(), timeout=8)

            self.assertEqual(len(calls), 1, "Normal GameClosed must save once (#4)")
            self.assertTrue(os.path.exists(_profile_path("G2Once")))

    async def test_5_hardcore_alive_session_writes_nothing(self):
        from src.game import Apocrysis
        app = ApocrysisApp(name="G2Hard", level=1, seed=1, hardcore=True)
        async with app.run_test(size=(130, 48)) as pilot:
            await asyncio.wait_for(pilot.pause(), timeout=5)
            gs = app.screen
            self.assertGreater(gs.player.health, 0)

            with patch.object(Apocrysis, "save_profile") as msave, \
                    patch.object(Apocrysis, "delete_profile") as mdel:
                await asyncio.wait_for(gs.close_game(), timeout=8)
                msave.assert_not_called()
                mdel.assert_not_called()

            self.assertFalse(
                os.path.exists(_profile_path("G2Hard")),
                "Hardcore GameClosed left a profile behind (#5)")

    async def test_7_answer_queue_does_not_survive_into_next_session(self):
        app = ApocrysisApp(name="G2Neg", level=1, seed=1)
        async with app.run_test(size=(130, 48)) as pilot:
            await asyncio.wait_for(pilot.pause(), timeout=5)
            gs1 = app.screen
            io1 = gs1.io

            # A keypress that lands in the queue but is never consumed
            # (worker is blocked at "> "; close_game beats it there).
            io1._answers.put("STALE-DIRECTION")
            await asyncio.wait_for(gs1.close_game(), timeout=8)
            self.assertTrue(io1._answers.empty(),
                            "stale answer survived teardown (#7)")

            gs2 = GameScreen(game_name="G2NegTwo", level=1, seed=1)
            await app.push_screen(gs2)
            await asyncio.wait_for(pilot.pause(), timeout=5)

            self.assertIsNot(gs2.io, io1)
            self.assertIsNot(gs2.io._answers, io1._answers)
            self.assertTrue(gs2.io._answers.empty())

            # The fresh worker responds to fresh input and nothing else.
            t0 = gs2.player.turns
            await asyncio.wait_for(pilot.press("right"), timeout=5)
            await asyncio.wait_for(pilot.pause(0.4), timeout=5)
            self.assertEqual(gs2.player.turns, t0 + 1)
            await asyncio.wait_for(gs2.close_game(), timeout=8)

    async def test_10_repeated_cycles_do_not_accumulate_threads(self):
        app = ApocrysisApp(name="G2Cycle", level=1, seed=1)
        async with app.run_test(size=(130, 48)) as pilot:
            await asyncio.wait_for(pilot.pause(), timeout=5)
            await asyncio.wait_for(app.screen.close_game(), timeout=8)
            await asyncio.sleep(0.3)
            baseline = threading.active_count()

            for i in range(3):
                gs = GameScreen(game_name="G2Cycle", level=1, seed=1)
                await app.push_screen(gs)
                await asyncio.wait_for(pilot.pause(), timeout=5)
                await asyncio.wait_for(gs.close_game(), timeout=8)
                await asyncio.sleep(0.3)

            self.assertLessEqual(
                threading.active_count(), baseline + 1,
                "worker threads accumulated across sessions (#10)")
            self.assertIsInstance(app.screen, MenuScreen)
            # No Screen pile-up either: base + one MenuScreen.
            self.assertEqual(len(app.screen_stack), 2)


# --------------------------------------------------------------------
# G3 milestone 1: the `menu` command is a real, working exit from
# GameScreen into a real MenuScreen. No campaign management yet.
# --------------------------------------------------------------------

@unittest.skipUnless(_TEXTUAL_AVAILABLE, "textual not installed")
class TestReturnToMenu(unittest.IsolatedAsyncioTestCase):

    _NAMES = ("G3Normal", "G3Hard")

    def _clean(self):
        for n in self._NAMES:
            f = _profile_path(n)
            if os.path.exists(f):
                os.remove(f)

    async def asyncSetUp(self):
        from src.game import Apocrysis
        Apocrysis.reset_campaign_state()
        self._clean()

    async def asyncTearDown(self):
        await asyncio.sleep(0.3)
        self._clean()

    async def _type(self, pilot, text):
        for ch in text:
            await pilot.press(ch)
        await pilot.press("enter")

    async def test_menu_command_from_normal_game_lands_on_menuscreen(self):
        app = ApocrysisApp(name="G3Normal", level=1, seed=1)
        async with app.run_test(size=(130, 48)) as pilot:
            await asyncio.wait_for(pilot.pause(), timeout=5)
            gs = app.screen
            self.assertIsInstance(gs, GameScreen)

            await self._type(pilot, "menu")
            await asyncio.wait_for(pilot.pause(0.6), timeout=5)

            self.assertIsInstance(app.screen, MenuScreen)
            self.assertTrue(app.is_running)
            self.assertTrue(gs._game_worker is None)
            # Normal return-to-menu is silent + autosaves.
            self.assertTrue(os.path.exists(_profile_path("G3Normal")))

    async def test_menu_from_hardcore_stay_is_a_true_noop(self):
        app = ApocrysisApp(name="G3Hard", level=1, seed=1, hardcore=True)
        async with app.run_test(size=(130, 48)) as pilot:
            await asyncio.wait_for(pilot.pause(), timeout=5)
            gs = app.screen
            worker = gs._game_worker

            await self._type(pilot, "menu")
            await asyncio.wait_for(pilot.pause(0.4), timeout=5)
            # The abandon confirm is up.
            self.assertIn("HARDCORE",
                          gs.query_one("#command_input").placeholder)

            # Bare Enter = stay (default cancel).
            await pilot.press("enter")
            await asyncio.wait_for(pilot.pause(0.4), timeout=5)

            self.assertIs(app.screen, gs, "left the game on 'stay'")
            self.assertIs(gs._game_worker, worker, "worker was signalled on 'stay'")
            self.assertFalse(gs._session_closing.is_set())

    async def test_menu_from_hardcore_leave_abandons_the_campaign(self):
        app = ApocrysisApp(name="G3Hard", level=1, seed=1, hardcore=True)
        async with app.run_test(size=(130, 48)) as pilot:
            await asyncio.wait_for(pilot.pause(), timeout=5)
            gs = app.screen

            await self._type(pilot, "menu")
            await asyncio.wait_for(pilot.pause(0.4), timeout=5)
            await self._type(pilot, "y")           # leave
            await asyncio.wait_for(pilot.pause(0.6), timeout=5)

            self.assertIsInstance(app.screen, MenuScreen)
            self.assertFalse(os.path.exists(_profile_path("G3Hard")),
                             "Hardcore abandon wrote a profile")

    async def test_menuscreen_quit_exits_the_app(self):
        app = ApocrysisApp(name="G3Normal", level=1, seed=1)
        async with app.run_test(size=(130, 48)) as pilot:
            await asyncio.wait_for(pilot.pause(), timeout=5)
            await self._type(pilot, "menu")
            await asyncio.wait_for(pilot.pause(0.6), timeout=5)
            self.assertIsInstance(app.screen, MenuScreen)

            # QUIT is the selected item by... navigate to it (last).
            for _ in range(4):
                await pilot.press("down")
            await pilot.press("enter")
            await asyncio.wait_for(pilot.pause(0.3), timeout=5)
            self.assertFalse(app.is_running)


@unittest.skipUnless(_TEXTUAL_AVAILABLE, "textual not installed")
class TestDeathEndsTheSessionNotTheApp(unittest.IsolatedAsyncioTestCase):
    """Reported: dying closed the whole TUI. Death (like the `menu`
    command) ends the game SESSION - the app stays alive and returns to
    the menu. For a Normal campaign the heir is persisted and CONTINUE
    resumes it."""

    async def asyncSetUp(self):
        self._home = tempfile.mkdtemp(prefix="apoc_death_")
        self._prev = os.environ.get("APOCRYSIS_HOME")
        os.environ["APOCRYSIS_HOME"] = self._home
        from src.game import Apocrysis
        Apocrysis.reset_campaign_state()

    async def asyncTearDown(self):
        await asyncio.sleep(0.3)
        if self._prev is None:
            os.environ.pop("APOCRYSIS_HOME", None)
        else:
            os.environ["APOCRYSIS_HOME"] = self._prev
        shutil.rmtree(self._home, ignore_errors=True)

    async def _wait_menu(self, app, pilot):
        for _ in range(40):
            await asyncio.wait_for(pilot.pause(0.15), timeout=5)
            if isinstance(app.screen, MenuScreen):
                return
        self.assertIsInstance(app.screen, MenuScreen)

    async def test_normal_death_returns_to_menu_and_heir_is_resumable(self):
        from src.game import Apocrysis
        app = ApocrysisApp(name="Fallen", level=1, seed=1)
        async with app.run_test(size=(130, 48)) as pilot:
            await asyncio.wait_for(pilot.pause(), timeout=5)
            gs = app.screen
            self.assertIsInstance(gs, GameScreen)
            dead_name = gs.player.name

            # kill the survivor, then drive one command so run_game_loop
            # re-checks its `while health > 0` guard and exits.
            gs.player.health = 0
            await pilot.press("l")
            await pilot.press("enter")
            await asyncio.wait_for(pilot.pause(0.5), timeout=5)
            # the end screen's "Press Enter to continue..."
            await pilot.press("enter")

            await self._wait_menu(app, pilot)
            self.assertTrue(app.is_running, "the app exited on death")

            # the campaign persisted, now carried by an heir
            rows = Apocrysis.list_campaign_summaries()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["key"], "Fallen")
            self.assertNotEqual(rows[0]["name"], dead_name)  # the heir
            self.assertIn("CONTINUE", app.screen._items())

            # CONTINUE resumes the heir campaign (by key, not the
            # changed survivor name)
            ms = app.screen
            ms._sel = ms._items().index("CONTINUE")
            ms._render_items()
            await pilot.press("enter")           # arm
            await asyncio.wait_for(pilot.pause(0.2), timeout=5)
            await pilot.press("enter")           # resume
            for _ in range(40):
                await asyncio.wait_for(pilot.pause(0.15), timeout=5)
                if isinstance(app.screen, GameScreen):
                    break
            self.assertIsInstance(app.screen, GameScreen)
            self.assertEqual(app.screen.player.name, rows[0]["name"])

    async def test_death_in_a_non_default_world_keeps_the_heir_in_that_world(self):
        # Regression: persist_new_survivor built the heir for the
        # DEFAULT world, so a Normal death in The Wake stamped
        # world_id="silence" onto the campaign file - it then showed up
        # under The Silence and collided invisibly.
        from src.game import Apocrysis
        from src.mixins.persistence_mixin import campaign_filename
        import json
        from src import runtime_paths

        app = ApocrysisApp(start_log=False)
        async with app.run_test(size=(130, 48)) as pilot:
            await asyncio.wait_for(pilot.pause(), timeout=5)
            ms = app.screen
            ms._sel = ms._items().index("NEW CAMPAIGN")
            ms._render_items()
            await pilot.press("enter")
            await asyncio.wait_for(pilot.pause(0.4), timeout=5)
            nc = app.screen
            nc.query_one("#nc_world").children[1].value = True   # the_wake
            await pilot.pause(0.1)
            nc.query_one("#nc_name").focus()
            for ch in "Kessel":
                await pilot.press(ch)
            await pilot.pause(0.1)
            nc._start()
            for _ in range(40):
                await asyncio.wait_for(pilot.pause(0.15), timeout=5)
                if isinstance(app.screen, GameScreen):
                    break
            gs = app.screen
            self.assertEqual(gs.player.world.id, "the_wake")

            gs.player.health = 0
            await pilot.press("l")
            await pilot.press("enter")
            await asyncio.wait_for(pilot.pause(0.5), timeout=5)
            await pilot.press("enter")
            await self._wait_menu(app, pilot)

            path = runtime_paths.resolve(
                "player", campaign_filename("the_wake", "Kessel"))
            self.assertTrue(os.path.exists(path))
            saved = json.load(open(path))
            self.assertEqual(saved["campaign"]["world_id"], "the_wake")

            rows = Apocrysis.list_campaign_summaries()
            wake = [r for r in rows if r["key"] == "Kessel"]
            self.assertEqual(len(wake), 1)
            self.assertEqual(wake[0]["world_id"], "the_wake")

    async def test_hardcore_death_returns_to_menu_with_no_saved_campaign(self):
        from src.game import Apocrysis
        app = ApocrysisApp(name="HardFall", level=1, seed=1, hardcore=True)
        async with app.run_test(size=(130, 48)) as pilot:
            await asyncio.wait_for(pilot.pause(), timeout=5)
            gs = app.screen
            gs.player.health = 0
            await pilot.press("l")
            await pilot.press("enter")
            await asyncio.wait_for(pilot.pause(0.5), timeout=5)
            await pilot.press("enter")

            await self._wait_menu(app, pilot)
            self.assertTrue(app.is_running)
            self.assertEqual(Apocrysis.list_campaign_summaries(), [])
            self.assertNotIn("CONTINUE", app.screen._items())


@unittest.skipUnless(_TEXTUAL_AVAILABLE, "textual not installed")
class TestMenuCommandDecoupling(unittest.TestCase):

    def test_menu_command_is_a_noop_message_without_a_shell_hook(self):
        # Classic mode / bots never install _return_to_menu_hook.
        from src.game import Apocrysis
        Apocrysis.reset_campaign_state()
        said = []

        class _IO:
            renders_natively = False
            def say(self, *a, **k): said.append(" ".join(str(x) for x in a))
            def ask(self, *a, **k): return ""
            def ask_yes_no(self, *a, **k): return False

        g = Apocrysis("Classic", seed=1, io=_IO())
        g._request_return_to_menu()
        self.assertTrue(any("main menu isn't available" in s for s in said))

    def test_menuscreen_carries_no_world_fiction(self):
        # The World-3 seam: adding a world must never touch the shell.
        import inspect
        from src.tui import MenuScreen
        src = inspect.getsource(MenuScreen).lower()
        for needle in ("silence", "the_wake", "valley", "world.id"):
            self.assertNotIn(needle, src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
