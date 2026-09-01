# G5 (Phase G, §7): campaign state must hard-reset on a load-switch.
#
# Apocrysis keeps campaign state as CLASS variables. One process ran
# one campaign, so it never mattered. The shell lets you play A,
# return to the menu, and load B - a different world - in one process.
# Loading a campaign must be reset-then-restore, never a merge.
#
# The headline test: A -> Menu -> B -> Menu -> A. None of A's
# identity / investigation / mechanisms / survivors-lost / ending
# crosses into B; returning to A rebuilds it from PERSISTED state.

import asyncio
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
from src.mixins.persistence_mixin import (profile_filename_for_name,
                                         campaign_filename)


@unittest.skipUnless(_TEXTUAL_AVAILABLE, "textual not installed")
class TestCampaignSwitching(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self._home = tempfile.mkdtemp(prefix="apoc_g5_")
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

    # ---- fixtures ------------------------------------------------

    def _save_A(self):
        """Campaign A: The Silence, well advanced."""
        Apocrysis.reset_campaign_state()
        Apocrysis._used_mechanisms = ["power_station", "radio_tower"]
        Apocrysis._recent_mechanisms = ["radio_tower"]
        Apocrysis._world_investigation = {
            "DIS_FEW_REMAINS": "known", "DIS_MOVED_TOGETHER": "suspected"}
        Apocrysis._survivors_lost = 3
        Apocrysis._campaign_ending = "the_broadcast"
        a = Apocrysis("Alba", seed=1, world="silence")
        a.save_profile(campaign_filename("silence", "Alba"))
        Apocrysis.reset_campaign_state()

    def _save_B(self):
        """Campaign B: The Wake, barely started."""
        Apocrysis.reset_campaign_state()
        Apocrysis._world_investigation = {"WAKE_ALONE": "known"}
        b = Apocrysis("Bront", seed=2, world="the_wake")
        b.save_profile(campaign_filename("the_wake", "Bront"))
        Apocrysis.reset_campaign_state()

    # ---- navigation helpers -------------------------------------

    async def _load(self, app, pilot, name):
        ms = app.screen
        self.assertIsInstance(ms, MenuScreen)
        ms._sel = ms._items().index("LOAD GAME")
        ms._render_items()
        await pilot.press("enter")
        await asyncio.wait_for(pilot.pause(0.4), timeout=5)
        lg = app.screen
        self.assertIsInstance(lg, LoadGameScreen)
        lg._sel = [r["name"] for r in lg._rows].index(name)
        lg._render_rows()
        await pilot.press("enter")
        await asyncio.wait_for(pilot.pause(1.0), timeout=8)
        self.assertIsInstance(app.screen, GameScreen)
        return app.screen

    async def _to_menu(self, app, pilot):
        for ch in "menu":
            await pilot.press(ch)
        await pilot.press("enter")
        await asyncio.wait_for(pilot.pause(1.0), timeout=8)
        self.assertIsInstance(app.screen, MenuScreen)

    # ---- the headline -----------------------------------------

    async def test_A_to_menu_to_B_to_menu_to_A(self):
        self._save_A()
        self._save_B()
        Apocrysis.reset_campaign_state()      # a fresh process

        app = ApocrysisApp(start_log=False)
        async with app.run_test(size=(120, 40)) as pilot:
            await asyncio.wait_for(pilot.pause(), timeout=5)

            # --- load A ---
            gsA = await self._load(app, pilot, "Alba")
            self.assertEqual(gsA.player.world.id, "silence")
            self.assertEqual(sorted(Apocrysis._used_mechanisms),
                             ["power_station", "radio_tower"])
            self.assertEqual(Apocrysis._survivors_lost, 3)
            self.assertEqual(Apocrysis._campaign_ending, "the_broadcast")
            self.assertIn("DIS_FEW_REMAINS", Apocrysis._world_investigation)

            await self._to_menu(app, pilot)

            # --- load B: NONE of A's campaign state survives ---
            gsB = await self._load(app, pilot, "Bront")
            self.assertEqual(gsB.player.world.id, "the_wake")

            self.assertNotIn("power_station", Apocrysis._used_mechanisms)
            self.assertNotIn("radio_tower", Apocrysis._used_mechanisms)
            self.assertNotIn("DIS_FEW_REMAINS", Apocrysis._world_investigation)
            self.assertNotIn("DIS_MOVED_TOGETHER", Apocrysis._world_investigation)
            self.assertEqual(Apocrysis._survivors_lost, 0)
            self.assertIsNone(Apocrysis._campaign_ending)

            # the live investigation resolves only against The Wake's DAG
            wake_ids = {f.id for f in gsB.player.world.world_facts}
            self.assertNotIn("DIS_FEW_REMAINS", wake_ids)
            live = gsB.player.world_investigation.snapshot()["status"]
            self.assertEqual(set(live), {"WAKE_ALONE"})
            self.assertTrue(set(live).issubset(wake_ids))

            await self._to_menu(app, pilot)

            # --- back to A: restored from DISK, exactly ---
            gsA2 = await self._load(app, pilot, "Alba")
            self.assertEqual(gsA2.player.world.id, "silence")
            self.assertEqual(sorted(Apocrysis._used_mechanisms),
                             ["power_station", "radio_tower"])
            self.assertEqual(Apocrysis._survivors_lost, 3)
            self.assertEqual(Apocrysis._campaign_ending, "the_broadcast")
            self.assertIn("DIS_FEW_REMAINS", Apocrysis._world_investigation)

    async def test_new_campaign_after_a_dirty_campaign_is_clean(self):
        self._save_A()
        # class-vars dirty, as if A had just finished a winning expedition
        Apocrysis._used_mechanisms = ["power_station"]
        Apocrysis._world_investigation = {"DIS_FEW_REMAINS": "known"}
        Apocrysis._survivors_lost = 2
        Apocrysis._campaign_ending = "the_broadcast"
        Apocrysis.prize_for_next_game = True

        app = ApocrysisApp(start_log=False)
        async with app.run_test(size=(120, 40)) as pilot:
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
            for ch in "Cyra":
                await pilot.press(ch)
            await pilot.pause(0.1)
            nc._start()
            await asyncio.wait_for(pilot.pause(1.0), timeout=8)

            gs = app.screen
            self.assertIsInstance(gs, GameScreen)
            self.assertEqual(gs.player.world.id, "the_wake")
            self.assertEqual(Apocrysis._used_mechanisms, [])
            self.assertNotIn("DIS_FEW_REMAINS", Apocrysis._world_investigation)
            self.assertEqual(Apocrysis._survivors_lost, 0)
            self.assertIsNone(Apocrysis._campaign_ending)
            self.assertFalse(Apocrysis.prize_for_next_game)

    async def test_same_survivor_name_runs_a_campaign_in_each_world(self):
        # The reported bug: a "Balthus" in The Silence blocked making a
        # "Balthus" in The Wake. Campaign identity is (world, survivor).
        from src import runtime_paths
        Apocrysis("Balthus", seed=1, world="silence").save_profile(
            campaign_filename("silence", "Balthus"))

        app = ApocrysisApp(start_log=False)
        async with app.run_test(size=(120, 40)) as pilot:
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
            for ch in "Balthus":
                await pilot.press(ch)
            await pilot.pause(0.1)
            nc._start()
            await asyncio.wait_for(pilot.pause(1.0), timeout=8)

            gs = app.screen
            self.assertIsInstance(gs, GameScreen, "Wake Balthus was rejected")
            self.assertEqual(gs.player.world.id, "the_wake")
            self.assertEqual(gs.player.name, "Balthus")
            # the Silence Balthus is a separate file, untouched
            self.assertTrue(os.path.exists(runtime_paths.resolve(
                "player", campaign_filename("silence", "Balthus"))))

            await self._to_menu(app, pilot)
            # LOAD now lists two Balthus rows, one per world
            rows = Apocrysis.list_campaign_summaries()
            worlds = sorted(r["world_id"] for r in rows if r["name"] == "Balthus")
            self.assertEqual(worlds, ["silence", "the_wake"])

    async def test_second_campaign_same_name_same_world_is_still_rejected(self):
        Apocrysis("Twin", seed=1, world="the_wake").save_profile(
            campaign_filename("the_wake", "Twin"))
        app = ApocrysisApp(start_log=False)
        async with app.run_test(size=(120, 40)) as pilot:
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
            for ch in "Twin":
                await pilot.press(ch)
            await pilot.pause(0.1)
            nc._start()
            await asyncio.wait_for(pilot.pause(0.4), timeout=5)
            self.assertIsInstance(app.screen, NewCampaignScreen)
            self.assertIn("already has a campaign",
                          str(nc.query_one("#nc_error").render()))


@unittest.skipUnless(_TEXTUAL_AVAILABLE, "textual not installed")
class TestResetCampaignState(unittest.TestCase):

    def test_reset_wipes_every_campaign_var(self):
        Apocrysis._used_mechanisms = ["x"]
        Apocrysis._recent_mechanisms = ["x"]
        Apocrysis._recent_signatures = ["s"]
        Apocrysis._world_investigation = {"F": "known"}
        Apocrysis._survivor_knowledge = ["lore"]
        Apocrysis._survivors_lost = 4
        Apocrysis._campaign_ending = "e"
        Apocrysis._last_family = "fam"
        Apocrysis.prize_for_next_game = True

        Apocrysis.reset_campaign_state()

        self.assertEqual(Apocrysis._used_mechanisms, [])
        self.assertEqual(Apocrysis._recent_mechanisms, [])
        self.assertEqual(Apocrysis._recent_signatures, [])
        self.assertEqual(Apocrysis._world_investigation, {})
        self.assertEqual(Apocrysis._survivor_knowledge, [])
        self.assertEqual(Apocrysis._survivors_lost, 0)
        self.assertIsNone(Apocrysis._campaign_ending)
        self.assertIsNone(Apocrysis._last_family)
        self.assertFalse(Apocrysis.prize_for_next_game)

    def test_reset_then_restore_from_a_flat_profile(self):
        Apocrysis.reset_campaign_state()
        Apocrysis.reset_campaign_state(restore_from={
            "used_mechanisms": ["power_station"],
            "world_investigation": {"WAKE_ALONE": "known"},
            "survivors_lost": 2,
            "ending": "restart",
            "prize_for_next_game": True,      # ignored on purpose
        })
        self.assertEqual(Apocrysis._used_mechanisms, ["power_station"])
        self.assertEqual(Apocrysis._world_investigation, {"WAKE_ALONE": "known"})
        self.assertEqual(Apocrysis._survivors_lost, 2)
        self.assertEqual(Apocrysis._campaign_ending, "restart")
        self.assertFalse(Apocrysis.prize_for_next_game)
        Apocrysis.reset_campaign_state()


if __name__ == "__main__":
    unittest.main(verbosity=2)
