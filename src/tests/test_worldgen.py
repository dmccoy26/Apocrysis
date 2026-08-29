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



class TestMapGeneration(unittest.TestCase):
    """v3 SPRINT step 2 - map generation redesign. Fixed seeds
    throughout so generation is reproducible (self.rng, game.py's
    __init__), per the sprint plan's reproducibility requirement."""

    def _find_town_center(self, game):
        for y, row in enumerate(game.map):
            for x, tile in enumerate(row):
                if isinstance(tile, dict) and tile.get("content") == "T":
                    return (x, y)
        return None

    def test_town_center_reachable_from_spawn_across_many_seeds(self):
        # Governing invariant: generate_map() must never return with
        # spawn unable to reach the town center, at any expedition
        # count (obstacle density scales with expeditions_completed,
        # not player level, since the map/player/campaign level split
        # - this is exactly where an unreachable map would show up if
        # the carve-path guarantee were broken).
        for seed in range(20):
            for expeditions_completed in (0, 4, 8, 12, 20):
                with patch("builtins.print"):
                    game = Apocrysis(
                        "ReachTest", map_size=15, seed=seed,
                        expeditions_completed=expeditions_completed,
                    )
                town_center = self._find_town_center(game)
                self.assertIsNotNone(town_center)
                from src.worldgen.reachable import is_reachable
                self.assertTrue(
                    is_reachable([[c for c in row] for row in game.map],
                                 game.map_size, game.current_position, town_center),
                    f"unreachable town at seed={seed} expeditions_completed={expeditions_completed}",
                )

    def test_town_min_distance_grows_with_expeditions_completed(self):
        with patch("builtins.print"):
            low_game = Apocrysis("DistTest", map_size=40, seed=3, expeditions_completed=0)
        with patch("builtins.print"):
            high_game = Apocrysis("DistTest", map_size=40, seed=3, expeditions_completed=15)

        def distance(game):
            tc = self._find_town_center(game)
            sx, sy = game.current_position
            return abs(tc[0] - sx) + abs(tc[1] - sy)

        # Not a strict inequality on a single sample (placement is
        # still randomized above the minimum), but the 15-expedition
        # game's own minimum bound must be higher than the 0-expedition
        # game's.
        self.assertGreater(
            self._min_distance_for(high_game),
            self._min_distance_for(low_game),
        )
        self.assertGreaterEqual(distance(high_game), self._min_distance_for(high_game))

    @staticmethod
    def _min_distance_for(game):
        from src.constants import BASE_TOWN_MIN_DISTANCE, TOWN_DISTANCE_GROWTH_PER_LEVEL
        return min(
            game.map_size - 2,
            BASE_TOWN_MIN_DISTANCE + game.expeditions_completed * TOWN_DISTANCE_GROWTH_PER_LEVEL,
        )

    def test_carve_path_never_touches_spawn_or_town_center(self):
        with patch("builtins.print"):
            # expeditions_completed=20: max obstacle density
            game = Apocrysis("CarveTest", map_size=15, seed=7, expeditions_completed=20)
        town_center = self._find_town_center(game)

        spawn_tile = game.map[game.current_position[1]][game.current_position[0]]
        town_tile = game.map[town_center[1]][town_center[0]]

        self.assertNotIn(spawn_tile.get("terrain"), {"mountain", "river"})
        self.assertEqual(town_tile.get("content"), "T")

    def test_map_size_grows_with_expeditions_completed(self):
        with patch("builtins.print"):
            low = Apocrysis("SizeTest", seed=1, expeditions_completed=0)
        with patch("builtins.print"):
            high = Apocrysis("SizeTest", seed=1, expeditions_completed=15)
        self.assertGreater(high.map_size, low.map_size)

    def test_explicit_map_size_overrides_expeditions_completed_derivation(self):
        with patch("builtins.print"):
            game = Apocrysis("SizeTest", map_size=9, seed=1, expeditions_completed=15)
        self.assertEqual(game.map_size, 9)


class TestExpeditionsAndCampaign(unittest.TestCase):
    """
    Map/player/campaign level split: expeditions_completed (not raw
    player level) now drives map_size/obstacle_density/town distance
    (TestMapGeneration above), and increments on reaching the Town
    Center - these tests cover the win-condition side: the counter
    actually advancing, and the distinct CAMPAIGN_LENGTH milestone.
    """

    def _make_game(self, expeditions_completed=0):
        with patch("builtins.print"):
            game = Apocrysis(
                "ExpTest", map_size=10, seed=1,
                expeditions_completed=expeditions_completed,
            )
        # Deterministic spawn + an adjacent, walkable Town Center tile,
        # regardless of where generate_map()'s random spawn landed.
        game.current_position = (0, 0)
        game.map[0][1] = {"terrain": "plain", "content": "T", "explored": True}
        # Objective-driven win condition investigation: reaching 'T'
        # alone no longer wins - these tests are about the campaign/
        # expedition-counter mechanics specifically, not that gate, so
        # satisfy it directly rather than also staging a settlement
        # tile to walk through first.
        game.settlement_explored = True
        game.mystery = None  # v4: test the no-mystery reach-town fallback
        return game

    def test_reaching_town_increments_expeditions_completed(self):
        game = self._make_game(expeditions_completed=3)
        with patch("builtins.print"):
            game.move_and_search("e")
        self.assertTrue(game.won)
        self.assertEqual(game.expeditions_completed, 4)

    def test_campaign_complete_message_at_campaign_length(self):
        from src.constants import CAMPAIGN_LENGTH
        game = self._make_game(expeditions_completed=CAMPAIGN_LENGTH - 1)

        messages = []
        game.io.say = lambda *a, **k: messages.append(" ".join(str(x) for x in a))
        game.move_and_search("e")

        self.assertEqual(game.expeditions_completed, CAMPAIGN_LENGTH)
        self.assertTrue(any("CAMPAIGN COMPLETE" in m for m in messages))

    def test_ordinary_win_below_campaign_length_uses_the_normal_message(self):
        from src.constants import CAMPAIGN_LENGTH
        game = self._make_game(expeditions_completed=CAMPAIGN_LENGTH - 2)

        messages = []
        game.io.say = lambda *a, **k: messages.append(" ".join(str(x) for x in a))
        game.move_and_search("e")

        self.assertEqual(game.expeditions_completed, CAMPAIGN_LENGTH - 1)
        self.assertFalse(any("CAMPAIGN COMPLETE" in m for m in messages))
        self.assertTrue(any("You WIN" in m for m in messages))


class TestObjectiveDrivenWin(unittest.TestCase):
    """
    Objective-driven win condition investigation: reaching the Town
    Center alone no longer wins - the player must have already set
    foot in a settlement's other tiles first.
    """

    def _make_game(self):
        with patch("builtins.print"):
            game = Apocrysis("ObjectiveTest", map_size=10, seed=1)
        game.current_position = (0, 0)
        game.map[0][1] = {"terrain": "plain", "content": "T", "explored": True}
        game.mystery = None  # v4: these test the pre-mystery Town-Center gate
        return game

    def test_reaching_town_center_before_exploring_does_not_win(self):
        game = self._make_game()
        self.assertFalse(game.settlement_explored)

        with patch("builtins.print"):
            game.move_and_search("e")

        self.assertFalse(game.won)

    def test_stepping_on_a_settlement_tile_sets_the_explored_flag(self):
        game = self._make_game()
        game.map[0][1] = {
            "terrain": "town", "content": "H",
            "explored": True, "district": "residential",
        }

        with patch("builtins.print"), patch("builtins.input", return_value="n"):
            game.move_and_search("e")

        self.assertTrue(game.settlement_explored)
        self.assertFalse(game.won)  # H tile, not T - still no win

    def test_reaching_town_center_after_exploring_wins(self):
        game = self._make_game()
        game.settlement_explored = True

        with patch("builtins.print"):
            game.move_and_search("e")

        self.assertTrue(game.won)


class TestSettlementGeneration(unittest.TestCase):
    """Multiple-settlements + organic-settlement investigations."""

    def _town_tiles(self, game):
        return [
            tile for row in game.map for tile in row
            if isinstance(tile, dict) and tile.get("terrain") == "town"
        ]

    def test_exactly_one_town_center_regardless_of_settlement_count(self):
        with patch("builtins.print"):
            game = Apocrysis("SettleTest", map_size=30, seed=3, expeditions_completed=20)
        centers = [t for t in self._town_tiles(game) if t.get("content") == "T"]
        self.assertEqual(len(centers), 1)

    def test_settlement_count_grows_with_expeditions_completed(self):
        from src.constants import MAX_SETTLEMENTS, SETTLEMENTS_PER_EXPEDITIONS
        with patch("builtins.print"):
            early = Apocrysis("SettleEarly", map_size=30, seed=3, expeditions_completed=0)
        with patch("builtins.print"):
            late = Apocrysis(
                "SettleLate", map_size=30, seed=3,
                expeditions_completed=MAX_SETTLEMENTS * SETTLEMENTS_PER_EXPEDITIONS,
            )
        # Indirect measure: more settlements means more town tiles on
        # the same map size/seed (content varies, but total count of
        # terrain=='town' tiles scales with settlement count).
        self.assertGreater(len(self._town_tiles(late)), len(self._town_tiles(early)))

    def test_settlement_boundary_is_not_a_solid_square(self):
        # Organic-settlement investigation: at least one corner of the
        # bounding box should NOT be settlement terrain, across many
        # seeds (the 0.6 skip-chance makes a solid square on every
        # single seed astronomically unlikely if the skip is wired
        # correctly, but check several seeds rather than one to keep
        # this from being a flaky single-sample assertion).
        found_irregular = False
        for seed in range(10):
            with patch("builtins.print"):
                game = Apocrysis("BoundaryTest", map_size=15, seed=seed)
            town_tiles = self._town_tiles(game)
            if not town_tiles:
                continue
            # Find the bounding box of all town tiles and check
            # whether its four corners are actually town terrain.
            coords = [
                (x, y)
                for y, row in enumerate(game.map)
                for x, t in enumerate(row)
                if isinstance(t, dict) and t.get("terrain") == "town"
            ]
            min_x, max_x = min(c[0] for c in coords), max(c[0] for c in coords)
            min_y, max_y = min(c[1] for c in coords), max(c[1] for c in coords)
            corners = [(min_x, min_y), (min_x, max_y), (max_x, min_y), (max_x, max_y)]
            # A corner tile can be a non-dict (e.g. a zombie standing on
            # it) - that's still "not solid town", which is what we're
            # checking for.
            corner_terrains = {
                game.map[y][x].get("terrain") if isinstance(game.map[y][x], dict) else None
                for x, y in corners
            }
            if corner_terrains != {"town"}:
                found_irregular = True
                break
        self.assertTrue(found_irregular, "every sampled settlement was a solid square")

    def test_settlement_tiles_are_tagged_with_a_district(self):
        with patch("builtins.print"):
            game = Apocrysis("DistrictTest", map_size=15, seed=1)
        town_tiles = self._town_tiles(game)
        self.assertTrue(town_tiles)
        self.assertTrue(all("district" in t for t in town_tiles))
        self.assertTrue(
            {t["district"] for t in town_tiles} <= {"downtown", "commercial", "residential"}
        )


class TestChunkBasedTerrain(unittest.TestCase):
    def test_terrain_forms_contiguous_chunks_not_a_checkerboard(self):
        from src.constants import CHUNK_SIZE
        from src.game import Apocrysis as _A
        from src.worlds.silence.truth import WORLD_FACTS
        # Force a non-water mechanism: build_mystery's _paint_terrain_near
        # deliberately drops small water patches for boat/dam mysteries
        # (world coherence), which is not what this test is about - and
        # which mechanism a bare seed picks shifts whenever MECHANISMS
        # grows. Mark every WorldFact known so A.4.2 targeting is off and
        # the choose_mechanism patch below is what decides the mechanism.
        _saved = dict(_A._world_investigation)
        _A._world_investigation = {f.id: "known" for f in WORLD_FACTS}
        self.addCleanup(lambda: setattr(_A, "_world_investigation", _saved))
        with patch("builtins.print"), \
             patch("src.escape.choose_mechanism", return_value="mountain_pass"):
            game = Apocrysis("ChunkTest", map_size=20, seed=1)

        # Every tile within one chunk (excluding town tiles and
        # per-tile mountain/river obstacle overlays) must share the
        # same base terrain - a checkerboard regression would produce
        # a chunk with multiple different non-obstacle terrains.
        found_multi_terrain_chunk = False
        for cy in range(0, game.map_size, CHUNK_SIZE):
            for cx in range(0, game.map_size, CHUNK_SIZE):
                terrains = set()
                for y in range(cy, min(cy + CHUNK_SIZE, game.map_size)):
                    for x in range(cx, min(cx + CHUNK_SIZE, game.map_size)):
                        tile = game.map[y][x]
                        if not isinstance(tile, dict):
                            continue
                        terrain = tile.get("terrain")
                        if terrain not in ("mountain", "river", "town"):
                            terrains.add(terrain)
                if len(terrains) > 1:
                    found_multi_terrain_chunk = True
        self.assertFalse(
            found_multi_terrain_chunk,
            "a chunk contained more than one non-obstacle terrain type",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
