"""Phase C structural tests - deterministic, no rendering.

C.1: the worldgen extraction must be byte-identical to the pre-refactor
pipeline (a golden fixture captured before the move).
C.4 adds the graph tests here.
"""
import ast
import json
import os
import pathlib
import statistics
import unittest

from src.game import Apocrysis

_FIX = os.path.join(os.path.dirname(__file__), "fixtures", "worldgen_golden.json")


class _IO:
    renders_natively = True

    def say(self, *a, **k):
        pass

    def ask(self, prompt=""):
        return ""

    def ask_yes_no(self, prompt):
        return False


def _terrain(c):
    return c.get("terrain") if isinstance(c, dict) else "ZOMBIE"


def _zone(c):
    return c.get("zone") if isinstance(c, dict) else None


def _town_center(game):
    for y, row in enumerate(game.map):
        for x, c in enumerate(row):
            if isinstance(c, dict) and c.get("content") == "T":
                return [x, y]
    return None


class TestWorldgenGolden(unittest.TestCase):
    """The C.1 relocation preserves the RNG stream exactly - same seed,
    same map, down to every tile and the zone tags."""

    def test_generation_matches_the_pre_refactor_golden(self):
        golden = json.load(open(_FIX))
        self.assertGreaterEqual(len(golden), 20)
        for key, want in golden.items():
            seed, exp = key.split("_")
            g = Apocrysis("G", seed=int(seed), io=_IO(),
                          expeditions_completed=int(exp))
            self.assertEqual(list(g.current_position), want["spawn"], f"{key} spawn")
            self.assertEqual(g.map_archetype, want["archetype"], f"{key} archetype")
            self.assertEqual(_town_center(g), want["town_center"], f"{key} town")
            self.assertEqual([[_terrain(c) for c in row] for row in g.map],
                             want["grid"], f"{key} terrain grid")
            self.assertEqual([[_zone(c) for c in row] for row in g.map],
                             want["zones"], f"{key} zone grid")


class TestSameSeedSameMap(unittest.TestCase):
    def test_two_games_same_seed_identical_structure(self):
        for seed in (5, 33, 404):
            a = Apocrysis("A", seed=seed, io=_IO(), expeditions_completed=4)
            b = Apocrysis("B", seed=seed, io=_IO(), expeditions_completed=4)
            self.assertEqual(a.current_position, b.current_position)
            self.assertEqual(a.map_archetype, b.map_archetype)
            self.assertEqual([[_terrain(c) for c in r] for r in a.map],
                             [[_terrain(c) for c in r] for r in b.map])

    def test_two_games_same_seed_identical_graph(self):
        for seed in (5, 33, 404):
            a = Apocrysis("A", seed=seed, io=_IO(), expeditions_completed=4)
            b = Apocrysis("B", seed=seed, io=_IO(), expeditions_completed=4)
            self.assertEqual(a._map_graph.nodes, b._map_graph.nodes)
            self.assertEqual(a._map_graph.adj, b._map_graph.adj)


class TestWorldgenIsolation(unittest.TestCase):
    def test_worldgen_never_imports_the_engine(self):
        root = pathlib.Path(__file__).resolve().parents[1] / "worldgen"
        forbidden = ("src.mixins", "src.game", "src.escape")
        offenders = []
        for path in root.rglob("*.py"):
            for node in ast.walk(ast.parse(path.read_text(), str(path))):
                mods = []
                if isinstance(node, ast.Import):
                    mods = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    mods = [node.module]
                for m in mods:
                    if any(m == f or m.startswith(f + ".") for f in forbidden):
                        offenders.append(f"{path.name}: {m}")
        self.assertEqual(offenders, [])


class TestReachabilitySweep(unittest.TestCase):
    """C.1 already guarantees spawn->real-town-centre. A wide sweep that
    it never raises and the boundary is always intact."""

    def test_sweep(self):
        from src.worldgen.reachable import is_reachable

        for seed in range(300):
            exp = (0, 3, 6, 9, 12)[seed % 5]
            g = Apocrysis("S", seed=seed, io=_IO(), expeditions_completed=exp)
            n = g.map_size
            # boundary ring intact except the mystery's single carved
            # escape gap (build_mystery._carve_escape_pass).
            gap = g.mystery.escape_tile if g.mystery is not None else None
            for i in range(n):
                for (bx, by) in ((i, 0), (i, n - 1), (0, i), (n - 1, i)):
                    if (bx, by) == gap:
                        continue
                    self.assertEqual(g.map[by][bx]["terrain"], "mountain",
                                     f"seed {seed}: ring hole at {(bx, by)}")
            tc = _town_center(g)
            self.assertIsNotNone(tc, f"seed {seed}: no town centre")
            grid = [[c for c in row] for row in g.map]
            self.assertTrue(
                is_reachable(grid, n, g.current_position, tuple(tc)),
                f"seed {seed} exp {exp}: town unreachable")
            if g.mystery is not None:
                for role, xy in g.mystery.sites.items():
                    self.assertTrue(
                        is_reachable(grid, n, g.current_position, xy),
                        f"seed {seed}: mystery site {role} unreachable")
                self.assertTrue(
                    is_reachable(grid, n, g.current_position, g.mystery.escape_tile),
                    f"seed {seed}: escape tile unreachable")


class TestMapGeneratorV2(unittest.TestCase):
    """C.3 experiment: the irregular-valley generator. v1 is unchanged
    (the golden test covers that); v2 must still be seed-deterministic,
    single-region, and keep every mystery site + exit reachable."""

    def _v2(self, seed, exp):
        return Apocrysis("V2", seed=seed, io=_IO(),
                         expeditions_completed=exp, mapgen="v2")

    def test_v1_is_the_default(self):
        self.assertEqual(Apocrysis("D", seed=1, io=_IO())._mapgen, "v1")

    def test_v2_is_seed_deterministic(self):
        for seed in (7, 88, 250):
            a = self._v2(seed, 6)
            b = self._v2(seed, 6)
            self.assertEqual(
                [[_terrain(c) for c in r] for r in a.map],
                [[_terrain(c) for c in r] for r in b.map])
            self.assertEqual(a.current_position, b.current_position)

    def test_v2_reachability_sweep(self):
        from src.worldgen.reachable import is_reachable
        for seed in range(150):
            exp = (0, 3, 6, 9, 12)[seed % 5]
            g = self._v2(seed, exp)
            n = g.map_size
            grid = [[c if isinstance(c, dict) else {"terrain": "plain"}
                     for c in row] for row in g.map]
            if g.mystery is None:
                continue
            for role, xy in g.mystery.sites.items():
                self.assertTrue(is_reachable(grid, n, g.current_position, xy),
                                f"v2 seed {seed}: site {role} unreachable")
            self.assertTrue(
                is_reachable(grid, n, g.current_position, g.mystery.escape_tile),
                f"v2 seed {seed}: escape tile unreachable")

    def test_v2_valley_is_meaningfully_smaller_than_v1(self):
        # the intentional change: v2 is an irregular valley, not a box.
        def playable_pct(g):
            n = g.map_size
            interior = (n - 2) ** 2
            p = sum(1 for y in range(1, n - 1) for x in range(1, n - 1)
                    if isinstance(g.map[y][x], dict)
                    and g.map[y][x].get("terrain") not in ("mountain", "river"))
            return 100 * p / interior
        v1 = statistics.mean(playable_pct(Apocrysis("A", seed=s, io=_IO(),
                             expeditions_completed=6)) for s in range(30))
        v2 = statistics.mean(playable_pct(self._v2(s, 6)) for s in range(30))
        self.assertGreater(v1, 80)
        self.assertLess(v2, 78)


class TestMapGraph(unittest.TestCase):
    def test_graph_over_a_tiny_hand_map(self):
        from src.worldgen.graph import MapGraph
        # 5x5, ring of mountain, plain interior, one wall at x=2
        n = 5
        grid = [[{"terrain": "mountain"} for _ in range(n)] for _ in range(n)]
        for y in range(1, 4):
            for x in range(1, 4):
                grid[y][x] = {"terrain": "plain"}
        grid[1][2] = grid[2][2] = grid[3][2] = {"terrain": "river"}  # wall
        g = MapGraph(grid, n, {"a": (1, 1), "b": (3, 3), "c": (1, 3)})
        self.assertFalse(g.reachable("a", "b"))     # wall between
        self.assertTrue(g.reachable("a", "c"))      # same side
        self.assertEqual(g.unreachable_from("a"), ["b"])
        self.assertEqual(g.distance("a", "c"), 2)
        self.assertIn((1, 2), g.critical_path_tiles("a", "c"))

    def test_generate_map_attaches_a_graph_with_the_expected_nodes(self):
        g = Apocrysis("Graph", seed=11, io=_IO(), expeditions_completed=3)
        mg = g._map_graph
        self.assertIn("spawn", mg.nodes)
        if g.mystery is not None:
            self.assertIn("exit", mg.nodes)
            for role in g.mystery.sites:
                self.assertIn(f"site_{role}", mg.nodes)
            # every required node reachable from spawn (else generate
            # would have raised)
            self.assertEqual(
                [n for n in mg.unreachable_from("spawn")
                 if n.startswith("site_") or n == "exit"],
                [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
