"""`--dev` story-inspection harness — the multi-world extension
(2026-09-02). `docs/DEV_PLAYTEST.md`.

The harness began Silence-only; `DevConfig` gained `world` + `expedition`
so any world can be inspected at any level. Every old `--dev` command
must still resolve.
"""
import unittest

from src.dev import DevConfig, synthetic_state, entry_label, banner, equip_for_depth
from src.worlds import get_world
from src.game import Apocrysis


class _IO:
    renders_natively = True

    def say(self, *a, **k):
        pass

    def ask(self, prompt=""):
        return ""

    def ask_yes_no(self, prompt):
        return False


class TestDevConfigBackCompat(unittest.TestCase):
    def test_old_three_arg_style_still_builds(self):
        c = DevConfig(seed=42, chapter=3, finale=False)
        self.assertEqual(c.world, "silence")
        self.assertIsNone(c.expedition)
        depth, wi = synthetic_state(c)
        self.assertEqual(depth, get_world("silence").manifest.chapter_bounds[2])

    def test_finale_drops_at_the_last_expedition_not_the_last_chapter(self):
        for wid in ("silence", "the_wake"):
            c = DevConfig(seed=1, chapter=None, finale=True, world=wid,
                          expedition=None)
            depth, _ = synthetic_state(c)
            self.assertEqual(depth, get_world(wid).manifest.campaign_length - 1,
                             wid)


class TestDevMultiWorld(unittest.TestCase):
    def tearDown(self):
        Apocrysis.reset_campaign_state()

    def test_expedition_flag_drops_at_that_level_in_that_world(self):
        c = DevConfig(seed=7, chapter=None, finale=False, world="the_wake",
                      expedition=13)
        depth, wi = synthetic_state(c)
        self.assertEqual(depth, 12)                      # 1-based -> 0-based
        # CH1 + CH2 facts (chapter < 3) marked known
        wake = get_world("the_wake")
        want = {f.id for f in wake.world_facts if f.chapter < 3}
        self.assertEqual(set(wi), want)
        self.assertIn("expedition 13 of 25", entry_label(c))
        self.assertIn("The Wake", banner(c, depth))

    def test_the_built_game_is_the_right_world_and_level(self):
        Apocrysis.reset_campaign_state()
        c = DevConfig(seed=7, chapter=None, finale=False, world="the_wake",
                      expedition=13)
        depth, wi = synthetic_state(c)
        Apocrysis._world_investigation = dict(wi)
        g = Apocrysis("Dev", level=1, seed=7, hardcore=False,
                      expeditions_completed=depth, io=_IO(), world="the_wake")
        equip_for_depth(g, depth)
        self.assertEqual(g.world.id, "the_wake")
        self.assertEqual(g.expeditions_completed, 12)
        # L13 is a traversal crossing on the Wake spine
        self.assertIsNone(g.mystery)
        self.assertIsNotNone(g.section_exit)

    def test_equip_grants_the_persistent_kit_a_deep_survivor_would_hold(self):
        Apocrysis.reset_campaign_state()
        c = DevConfig(seed=3, chapter=None, finale=False, world="the_wake",
                      expedition=13)
        depth, wi = synthetic_state(c)
        Apocrysis._world_investigation = dict(wi)
        g = Apocrysis("Dev", level=1, seed=3, hardcore=False,
                      expeditions_completed=depth, io=_IO(), world="the_wake")
        equip_for_depth(g, depth)
        self.assertTrue(g.has_flashlight)
        self.assertTrue(g.has_scanner, "past L5 -> the helmet is held")
        self.assertFalse(g._markers_gated())
        # world-owned loot: a ship weapon name, not a valley one
        self.assertIsNotNone(g.equipped_weapon)

    def test_pre_helmet_drop_does_not_grant_the_scanner(self):
        Apocrysis.reset_campaign_state()
        c = DevConfig(seed=3, chapter=None, finale=False, world="the_wake",
                      expedition=3)                       # L3, before L5
        depth, wi = synthetic_state(c)
        Apocrysis._world_investigation = dict(wi)
        g = Apocrysis("Dev", level=1, seed=3, hardcore=False,
                      expeditions_completed=depth, io=_IO(), world="the_wake")
        equip_for_depth(g, depth)
        self.assertFalse(g.has_scanner)
        self.assertTrue(g._markers_gated())

    def test_silence_dev_still_works(self):
        Apocrysis.reset_campaign_state()
        c = DevConfig(seed=1, chapter=3, finale=False, world="silence",
                      expedition=None)
        depth, wi = synthetic_state(c)
        Apocrysis._world_investigation = dict(wi)
        g = Apocrysis("Dev", level=1, seed=1, hardcore=False,
                      expeditions_completed=depth, io=_IO(), world="silence")
        equip_for_depth(g, depth)
        self.assertEqual(g.world.id, "silence")


if __name__ == "__main__":
    unittest.main()
