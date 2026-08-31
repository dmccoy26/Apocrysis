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
import threading
import time
import unittest
from unittest.mock import patch

from src import runtime_paths
from src.mixins.persistence_mixin import profile_filename_for_name


def _profile_path(name):
    return runtime_paths.resolve("player", profile_filename_for_name(name))

try:
    from src.tui import ApocrysisApp, GameScreen, TextualIO, AppClosed, GameClosed
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
            # GameScreen popped - the app is back on its base screen.
            self.assertIs(app.screen, app.screen_stack[0])
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
            self.assertIs(app.screen, app.screen_stack[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
