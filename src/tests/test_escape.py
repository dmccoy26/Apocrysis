"""v4 Stage 4 - procedural escape-mechanism generation (src/escape.py
+ MysteryMixin)."""

import unittest
from collections import deque

from src.game import Apocrysis
from src.escape import MECHANISMS, choose_mechanism


class _IO:
    renders_natively = True

    def __init__(self):
        self.log = []

    def say(self, *a, **k):
        self.log.append(" ".join(str(x) for x in a))

    def ask(self, prompt=""):
        return "q"

    def ask_yes_no(self, prompt):
        return False


def _reachable(game, start, goal):
    n = game.map_size
    seen = {start}
    q = deque([start])
    while q:
        x, y = q.popleft()
        if (x, y) == goal:
            return True
        for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < n and 0 <= ny < n and (nx, ny) not in seen:
                c = game.map[ny][nx]
                passable = (isinstance(c, dict) and c.get("terrain") not in ("mountain", "river")) \
                    or (not isinstance(c, dict))  # zombie tiles are enterable (fight/flee)
                if passable:
                    seen.add((nx, ny))
                    q.append((nx, ny))
    return False


class TestEscapeGeneration(unittest.TestCase):

    def test_every_seed_produces_a_valid_reachable_mystery(self):
        for seed in range(40):
            with self.subTest(seed=seed):
                game = Apocrysis("EscGen", seed=seed,
                                 expeditions_completed=seed % 8, io=_IO())
                m = game.mystery
                self.assertIsNotNone(m, "generator should produce a mystery on a normal map")
                m.validate()  # raises on a broken chain
                sp = game.current_position
                for role, xy in m.sites.items():
                    self.assertTrue(_reachable(game, sp, xy),
                                    f"seed {seed}: site {role} unreachable")
                self.assertTrue(_reachable(game, sp, m.escape_tile),
                                f"seed {seed}: escape tile unreachable")

    def test_redundancy_every_fact_has_two_evidence_routes(self):
        game = Apocrysis("EscRed", seed=3, io=_IO())
        k = game.mystery.knowledge
        for fid in k.facts:
            routes = [e for e in k.evidence.values() if fid in e.supports]
            self.assertGreaterEqual(len(routes), 2, f"fact {fid} not redundant")

    def test_discovering_all_evidence_confirms_the_hypothesis(self):
        game = Apocrysis("EscSolve", seed=11, io=_IO())
        k = game.mystery.knowledge
        self.assertEqual(k.hypothesis_state(), "unknown")
        for eid in list(k.evidence):
            k.discover(eid)
        self.assertEqual(k.hypothesis_state(), "confirmed")

    def test_hypothesis_only_confirms_on_the_final_observation(self):
        game = Apocrysis("EscConfirm", seed=7, io=_IO())
        k = game.mystery.knowledge
        for eid in list(k.evidence):
            if eid != k.hypothesis.confirmed_by:
                k.discover(eid)
        # everything except the escape-tile sighting - suspected at most
        self.assertIn(k.hypothesis_state(), ("suspected", "unknown"))
        k.discover(k.hypothesis.confirmed_by)
        self.assertEqual(k.hypothesis_state(), "confirmed")

    def test_town_center_does_not_win_when_a_mystery_exists(self):
        game = Apocrysis("EscTC", map_size=12, seed=1, io=_IO())
        self.assertIsNotNone(game.mystery)
        game.current_position = (5, 5)
        game.map[5][6] = {"terrain": "town", "content": "T", "explored": True}
        game.settlement_explored = True
        game.move_and_search("e")
        self.assertFalse(game.won, "Town Center is info-rich, not a win, under a mystery")

    def test_escape_action_wins_only_with_confirmed_hypothesis_and_open_obstacle(self):
        game = Apocrysis("EscWin", seed=5, io=_IO())
        m = game.mystery

        # not at the escape tile
        game.mystery_try_escape()
        self.assertFalse(game.won)

        # at the tile, obstacle open, but hypothesis not confirmed
        game.current_position = m.escape_tile
        m.obstacle_open = True
        game.mystery_try_escape()
        self.assertFalse(game.won, "must have a confirmed hypothesis")

        # confirm it, then escape
        for eid in list(m.knowledge.evidence):
            m.knowledge.discover(eid)
        self.assertEqual(m.knowledge.hypothesis_state(), "confirmed")
        game.mystery_try_escape()
        self.assertTrue(game.won)
        self.assertTrue(m.escaped)

    def test_mechanism_shuffle_bag_no_repeat_until_exhausted(self):
        used = []
        picks = []
        import random
        rng = random.Random(0)
        for _ in range(len(MECHANISMS)):
            p = choose_mechanism(rng, used)
            picks.append(p)
            used.append(p)
        self.assertEqual(sorted(picks), sorted(MECHANISMS),
                         "each mechanism used exactly once before any repeat")

    def test_mystery_round_trips_through_save_load(self):
        import os
        import tempfile
        os.chdir(tempfile.mkdtemp())
        game = Apocrysis("EscSave", seed=9, io=_IO())
        m = game.mystery
        list(map(m.knowledge.discover, list(m.knowledge.evidence)[:3]))
        game.save_game("m.json")
        loaded = Apocrysis.load_game("m.json")
        self.assertEqual(loaded.knowledge.facts_known(), game.knowledge.facts_known())


if __name__ == "__main__":
    unittest.main()
