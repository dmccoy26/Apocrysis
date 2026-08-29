"""Phase A.0 - the World seam. These tests only assert that the seam
exists and is data-only; nothing about gameplay (that's covered by the
engine's own suite, which must stay green with the seam in place)."""
import dataclasses
import unittest

from src import constants
from src.worlds.base import World
from src.worlds.silence import SILENCE


class TestWorldSeam(unittest.TestCase):
    def test_silence_identity(self):
        self.assertEqual(SILENCE.id, "silence")
        self.assertEqual(SILENCE.name, "Apocrysis")
        self.assertIsInstance(SILENCE, World)

    def test_silence_owns_the_tile_vocabulary(self):
        # worlds/silence/world.py is the OWNER of these tables.
        # constants.py re-exports them as a back-compat shim, so the
        # shim must point at the World-owned object, not a copy.
        self.assertIs(constants.TERRAIN_SYMBOLS, SILENCE.terrain_symbols)
        self.assertIs(constants.TERRAIN_LEGEND, SILENCE.terrain_legend)
        self.assertIs(constants.MAP_ARCHETYPES, SILENCE.map_archetypes)

    def test_silence_map_archetype_values_unchanged(self):
        # The relocation must not touch a single weight or blurb.
        self.assertEqual(set(SILENCE.map_archetypes), {
            "mixed", "deep_woods", "flooded_basin",
            "suburban_sprawl", "open_country",
        })
        self.assertEqual(
            SILENCE.map_archetypes["deep_woods"]["weights"],
            [0.46, 0.10, 0.08, 0.28, 0.08],
        )
        self.assertEqual(SILENCE.terrain_symbols["swamp"], "s")
        self.assertIn("way out, now open", SILENCE.terrain_legend)

    def test_world_is_frozen(self):
        with self.assertRaises(dataclasses.FrozenInstanceError):
            SILENCE.id = "other"

    def test_world_is_data_only(self):
        # No callables on the dataclass surface - a World is data the
        # engine reads, never behaviour it delegates to.
        for f in dataclasses.fields(World):
            self.assertNotIn(
                "Callable", str(f.type),
                f"World.{f.name} looks behavioural",
            )

    def test_world_layer_has_no_engine_imports(self):
        # The seam only holds if world code never reaches back into the
        # engine. Parse every src/worlds/ module's imports (AST, so a
        # docstring mentioning "src.game" doesn't count).
        import ast
        import pathlib

        root = pathlib.Path(__file__).resolve().parents[1] / "worlds"
        forbidden = ("src.mixins", "src.game")
        offenders = []
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(), str(path))
            mods = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    mods += [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    mods.append(node.module)
            for m in mods:
                if any(m == f or m.startswith(f + ".") for f in forbidden):
                    offenders.append(f"{path.name}: {m}")
        self.assertEqual(offenders, [], f"world layer imports engine: {offenders}")

    def test_a_second_world_needs_no_engine_code(self):
        # The whole point: another World can be constructed from data
        # alone, without touching the engine.
        other = World(
            id="testworld",
            name="Testworld",
            description="a fixture",
            terrain_symbols={"plain": "."},
            terrain_legend="  . = plain",
            map_archetypes={"flat": {"weights": [1, 0, 0, 0, 0], "blurb": "flat"}},
        )
        self.assertEqual(other.id, "testworld")
        self.assertIsNot(other.map_archetypes, SILENCE.map_archetypes)


if __name__ == "__main__":
    unittest.main(verbosity=2)
