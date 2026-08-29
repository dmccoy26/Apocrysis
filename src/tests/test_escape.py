"""v4 Stage 4 - procedural escape-mechanism generation (src/escape.py
+ MysteryMixin)."""

import unittest
from collections import deque

from src.game import Apocrysis
from src.escape import (
    MECHANISMS, choose_mechanism,
    STORY_FAMILIES, DISCOVERY_PATTERNS, REASONING_PATTERNS,
    RESOLUTION_PATTERNS, CONFIRMATION_PATTERNS,
)


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

    def test_every_mechanism_declares_a_valid_classification(self):
        # Escape Story schema v1 - each MECHANISMS entry names a family
        # and the four patterns, all from the closed vocabularies.
        axes = [
            ("family", STORY_FAMILIES), ("discovery", DISCOVERY_PATTERNS),
            ("reasoning", REASONING_PATTERNS), ("resolution", RESOLUTION_PATTERNS),
            ("confirmation", CONFIRMATION_PATTERNS),
        ]
        for name, spec in MECHANISMS.items():
            for key, vocab in axes:
                self.assertIn(spec.get(key), vocab, f"{name}.{key}")

    def test_choose_mechanism_avoids_repeating_the_previous_family(self):
        import random
        rng = random.Random(1)
        used, last_family = [], None
        for _ in range(12):
            m = choose_mechanism(rng, used, last_family)
            fam = MECHANISMS[m]["family"]
            # only enforce when another family was actually available
            others = {MECHANISMS[x]["family"] for x in MECHANISMS} - {last_family}
            if last_family is not None and others:
                self.assertNotEqual(fam, last_family)
            if m not in used:
                used.append(m)
            last_family = fam

    def test_generated_mystery_carries_its_classification(self):
        game = Apocrysis("EscClass", seed=4, io=_IO())
        m = game.mystery
        self.assertIn(m.family, STORY_FAMILIES)
        self.assertIn(m.resolution, RESOLUTION_PATTERNS)

    def _force_mechanism(self, name, seed=0):
        from src.escape import MECHANISMS
        import src.game as gmod
        gmod.Apocrysis._used_mechanisms = [k for k in MECHANISMS if k != name]
        try:
            g = Apocrysis("Force", seed=seed, io=_IO())
            self.assertEqual(g.mystery.mechanism, name)
            return g
        finally:
            gmod.Apocrysis._used_mechanisms = []
            gmod.Apocrysis._last_family = None

    def test_power_station_builds_the_dependency_chain(self):
        g = self._force_mechanism("power_station")
        m = g.mystery
        self.assertEqual(m.power_role, "power")
        self.assertIn("power", m.sites)
        self.assertIn("F_POWER", m.knowledge.facts)
        # F_POWER has >=2 evidence routes
        routes = [e for e in m.knowledge.evidence.values() if "F_POWER" in e.supports]
        self.assertGreaterEqual(len(routes), 2)

    def test_power_station_gate_opens_on_power_not_on_the_item(self):
        g = self._force_mechanism("power_station", seed=3)
        m = g.mystery
        # carry the fuel to the gate: not ready
        g.backpack.add_item(__import__("src.items", fromlist=["Item"]).Item(m.requirement_item))
        self.assertFalse(g._mystery_obstacle_ready())
        # apply it at the hydro station
        g.current_position = m.sites["power"]
        g.mystery_arrive(*m.sites["power"])
        self.assertTrue(m.power_restored)
        self.assertFalse(g._mystery_has_item())      # consumed there
        self.assertTrue(g._mystery_obstacle_ready())  # gate now openable

    def test_dam_valves_obvious_control_is_never_the_answer(self):
        for seed in range(20):
            g = self._force_mechanism("dam_valves", seed=seed)
            m = g.mystery
            self.assertTrue(m.controls)
            self.assertIn(m.correct_control, m.controls)
            self.assertNotEqual(m.correct_control, "the main sluice")

    def test_dam_valves_opens_from_the_control_room_not_the_obstacle(self):
        g = self._force_mechanism("dam_valves", seed=1)
        m = g.mystery
        # no item to carry; the obstacle is not "ready" by walking in
        self.assertFalse(g._mystery_obstacle_ready())
        g.current_position = m.sites["require"]
        # wrong control: truthful consequence, obstacle stays shut
        g.mystery_pull_control("main sluice")
        self.assertFalse(m.obstacle_open)
        self.assertIn("the main sluice", m.controls_tried)
        # right control: opens ("east intake" / "west intake" - the last
        # word alone is ambiguous, so drop only the article)
        g.mystery_pull_control(m.correct_control.replace("the ", "", 1))
        self.assertTrue(m.obstacle_open)
        self.assertTrue(g._mystery_obstacle_ready())

    def test_airfield_plane_two_item_checklist(self):
        from src.items import Item
        g = self._force_mechanism("airfield_plane", seed=2)
        m = g.mystery
        self.assertEqual(m.family, "transportation")
        self.assertEqual(m.requirement_items, ["propeller", "can of avgas"])
        self.assertIn("require2", m.sites)
        self.assertNotEqual(m.sites["require"], m.sites["require2"])
        # F_REQUIRE still has >=2 evidence routes
        routes = [e for e in m.knowledge.evidence.values() if "F_REQUIRE" in e.supports]
        self.assertGreaterEqual(len(routes), 2)
        # one item is not enough
        g.backpack.add_item(Item("propeller"))
        self.assertFalse(g._mystery_obstacle_ready())
        # both items: the checklist is complete, obstacle opens on a bump
        g.backpack.add_item(Item("can of avgas"))
        self.assertTrue(g._mystery_obstacle_ready())
        g.current_position = m.obstacle_tile
        g.mystery_clear_obstacle()
        self.assertTrue(m.obstacle_open)
        # both parts consumed
        held = {getattr(it, "name", None) for it in g.backpack.items}
        self.assertNotIn("propeller", held)
        self.assertNotIn("can of avgas", held)

    def test_airfield_plane_items_are_order_free(self):
        g = self._force_mechanism("airfield_plane", seed=6)
        m = g.mystery
        # arrive at the two stores in reverse order; both hand over a part
        for role in ("require2", "require"):
            g.current_position = m.sites[role]
            g.mystery_arrive(*g.current_position)
        held = {getattr(it, "name", None) for it in g.backpack.items}
        self.assertEqual(held & {"propeller", "can of avgas"},
                         {"propeller", "can of avgas"})

    def test_airfield_plane_round_trips_requirement_items(self):
        import os, tempfile
        os.chdir(tempfile.mkdtemp())
        g = self._force_mechanism("airfield_plane", seed=8)
        g.save_game("plane.json")
        loaded = Apocrysis.load_game("plane.json")
        self.assertEqual(loaded.mystery.requirement_items,
                         ["propeller", "can of avgas"])
        self.assertIn("require2", loaded.mystery.sites)

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
