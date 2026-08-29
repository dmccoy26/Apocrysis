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


class _CapturingIO:
    """Collects say() output; never blocks on ask()."""
    renders_natively = True  # skip the classic per-turn ASCII block

    def __init__(self):
        self.lines = []

    def say(self, *args, **kwargs):
        self.lines.append(" ".join(str(a) for a in args))

    def ask(self, prompt=""):
        return ""

    def ask_yes_no(self, prompt):
        return False

    @property
    def text(self):
        return "\n".join(self.lines)


# The DUMMY world: deliberately weird values in every A.0 slot, so a
# passing render is proof the engine reads world data at render time
# rather than a relocated constant.
DUMMY = World(
    id="dummy",
    name="TEST WORLD",
    description="a deliberately weird fixture world",
    terrain_symbols={
        "forest": "F", "building": "H", "water": "W",
        "plain": "Q", "swamp": "G", "mountain": "M", "river": "R",
    },
    terrain_legend="=== DUMMY LEGEND: Q means open ground ===",
    # weights are positional [forest, building, water, plain, swamp];
    # force ~all-plain so every rendered in-range tile is 'Q'.
    map_archetypes={"allplain": {"weights": [0, 0, 0, 1, 0], "blurb": "nothing but Q"}},
    prose={"place_name_fallback": "DUMMYLAND", "leave_verb": "leave DUMMYLAND"},
)


class TestDummyWorldActuallyRenders(unittest.TestCase):
    """Change world data -> different world behaviour, no engine change.
    This is the test that says A.0 extracted a seam, not just moved a
    constant."""

    def setUp(self):
        from src.game import Apocrysis
        self.io = _CapturingIO()
        self.game = Apocrysis(name="Dummy", seed=1, io=self.io, world=DUMMY)

    def test_generate_map_used_the_dummy_archetypes(self):
        # generate_map() rolled from DUMMY.map_archetypes, not SILENCE's.
        self.assertEqual(self.game.map_archetype, "allplain")
        self.assertEqual(self.game.map_archetype_blurb, "nothing but Q")

    def test_map_renders_dummy_terrain_symbols(self):
        rendered = "\n".join(self.game._render_map_lines())
        # 'Q' is DUMMY's plain symbol and does not appear in SILENCE's
        # vocabulary at all - its presence proves the renderer read
        # self.world.terrain_symbols.
        self.assertIn("Q", rendered)
        self.assertNotIn("f", rendered)  # SILENCE's forest symbol

    def test_print_map_uses_dummy_legend(self):
        self.io.lines.clear()
        self.game.print_map()
        self.assertIn("DUMMY LEGEND", self.io.text)

    def test_location_name_falls_back_to_dummy_prose(self):
        from src.tui import _location_name
        # a terrain with no entry in _location_name's own names dict ->
        # the branch that returns the world's place-name fallback.
        x, y = self.game.current_position
        self.game.map[y][x] = {"terrain": "void", "content": "P"}
        self.assertEqual(_location_name(self.game), "DUMMYLAND")

    def test_end_screen_uses_dummy_place_name(self):
        self.io.lines.clear()
        self.game._render_end_screen()
        self.assertIn("DUMMYLAND", self.io.text)


class TestConstructionUnchanged(unittest.TestCase):
    def test_default_world_is_silence(self):
        from src.game import Apocrysis
        g = Apocrysis(name="Jess", seed=1, io=_CapturingIO())
        self.assertIs(g.world, SILENCE)

    def test_explicit_world_is_honoured(self):
        from src.game import Apocrysis
        g = Apocrysis(name="Jess", seed=1, io=_CapturingIO(), world=DUMMY)
        self.assertIs(g.world, DUMMY)


if __name__ == "__main__":
    unittest.main(verbosity=2)
