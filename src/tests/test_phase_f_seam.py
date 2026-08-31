"""Phase F - the multi-world seam (docs/PHASE_F_MULTI_WORLD_SEAM.md).

A deliberately HOSTILE second world: it differs on every world-owned
seam (chapter count, campaign length, fact DAG + ids, hypothesis rung
count, mechanism subset, terrain glyphs / archetypes / move cost,
finale). If the engine runs it without a single `world.id ==`
conditional, the seam is real.

This is NOT the authored World 2 - it's a fixture whose only job is to
break anything still wired to "The Silence".
"""
import ast
import pathlib
import unittest
from dataclasses import dataclass

from src.game import Apocrysis
from src.worlds.base import (
    World, WorldManifest, WorldTerrain, WorldFinale,
    DiscoveryTemplate,
)
from src.worlds.silence import population as _silence_population


# --- the hostile fixture world -----------------------------------------

@dataclass(frozen=True)
class _F:
    id: str
    thread: str
    chapter: int
    milestone: bool
    statement: str
    lead: str = ""
    needs: tuple = ()


_COVE_FACTS = (
    _F("C_HARBOUR_EMPTY", "origin", 1, False,
       "The harbour berths are empty and the mooring lines were cast off, not cut.",
       lead="why the boats are gone"),
    _F("C_ORDER_TO_GO", "origin", 2, True,
       "A harbourmaster's log records a departure order, timed and signed.",
       lead="who told the boats to leave", needs=("C_HARBOUR_EMPTY",)),
    _F("C_ORDER_RESCINDED", "order", 3, True,
       "A second signal countermanded the departure order six hours later. It never reached the water.",
       lead="the order that came too late", needs=("C_ORDER_TO_GO",)),
    _F("C_THE_CALL", "order", 4, False,
       "The relay tower can still raise the coast station. The countermand can be sent on - or the cove can stay a closed file.",
       lead="what the tower can still do", needs=("C_ORDER_RESCINDED",)),
)

_COVE_DISCOVERY = {
    "C_HARBOUR_EMPTY": (DiscoveryTemplate("C_HARBOUR_EMPTY", "service_route"),),
    "C_ORDER_TO_GO": (DiscoveryTemplate("C_ORDER_TO_GO", "power_station"),),
    "C_ORDER_RESCINDED": (DiscoveryTemplate("C_ORDER_RESCINDED", "radio_tower"),),
    "C_THE_CALL": (DiscoveryTemplate("C_THE_CALL", "radio_tower"),),
}


@dataclass(frozen=True)
class _RH:
    id: str
    statement: str
    held_until: str
    corrected_to: str


_COVE_HYPS = (
    _RH("CH_STORM", "A storm scattered the fleet. Nobody ordered anything.",
        held_until="C_ORDER_TO_GO",
        corrected_to="The boats left on an order - timed, signed, deliberate."),
    _RH("CH_CLEAN_EVAC", "It was a clean evacuation and everyone got clear.",
        held_until="C_ORDER_RESCINDED",
        corrected_to="The order was cancelled six hours on. The recall never "
                     "reached the water."),
)

_COVE_TERRAIN = WorldTerrain(
    symbols={'forest': 'T', 'water': 'w', 'building': 'H', 'plain': ',',
             'mountain': 'M', 'river': 'r', 'bridge': 'x', 'swamp': 'g'},
    legend="  T=trees w=water H=house ,=open  M=headland (impassable)  r=river",
    archetypes={
        'coast': {'weights': [0.15, 0.30, 0.30, 0.20, 0.05], 'blurb': 'A working harbour town, half of it below the tide line.'},
        'moor':  {'weights': [0.40, 0.10, 0.10, 0.35, 0.05], 'blurb': 'Open moorland running down to the water.'},
    },
    move_minutes={'plain': 12, 'town': 12, 'building': 12, 'forest': 18,
                  'water': 28, 'mountain': 40, 'river': 40, 'bridge': 12, 'swamp': 30},
)

_COVE_FINALE = WorldFinale(
    converge_fact="C_THE_CALL",
    also_establishes=("C_ORDER_RESCINDED",),
    escape_kind="checkpoint",
    site_labels={"route": "the relay tower", "power": "the coast station house"},
    arrival_title="the relay tower",
    arrival_prose="The tower still has power and the coast station answers on the "
                  "first call. The rescinded order is in your hand. The road down "
                  "off the headland is open.",
    choice_title="THE COAST STATION IS ON THE LINE",
    choice_intro="You can pass the countermand on, or close the file.",
    option_a=("send", "SEND - pass the rescinded order to the coast station. "
                       "The cove's boats are logged as recallable. Someone will come looking."),
    option_b=("close", "CLOSE - say nothing. The cove stays a finished file and "
                        "the people who left keep their head start."),
    endings={
        "send": ("You read the countermand out and the coast station copies it back.",
                 "The file is open again. What that brings, you won't be here for."),
        "close": ("You set the handset down without keying it.",
                  "The cove keeps its silence. You carry the order out alone."),
    },
)

COVE = World(
    id="testcove",
    name="Testcove",
    description="a hostile Phase-F fixture world",
    terrain_symbols=_COVE_TERRAIN.symbols,
    terrain_legend=_COVE_TERRAIN.legend,
    map_archetypes=_COVE_TERRAIN.archetypes,
    prose={"place_name_fallback": "THE COVE", "leave_verb": "leave the cove",
           "thread_titles": {"origin": ("THE HARBOUR", "Where did the boats go?"),
                             "order": ("THE ORDER", "Who signed it, and who cancelled it?")},
           "ambient_clues": (("A tide table on the wall, one date ringed.",
                              "A tide table has one date ringed."),)},
    discovery_templates=_COVE_DISCOVERY,
    world_facts=_COVE_FACTS,
    regional_hypotheses=_COVE_HYPS,
    manifest=WorldManifest(
        id="testcove", title="Testcove", subtitle="a cove that emptied",
        campaign_length=8, difficulty_ramp_length=4,
        chapter_bounds=(0, 2, 4, 6), chapter_titles=("HARBOUR", "ORDER", "SIGNAL", "CALL"),
        supported_mechanisms=("service_route", "radio_tower", "power_station"),
    ),
    terrain=_COVE_TERRAIN,
    finale=_COVE_FINALE,
    population=_silence_population,   # reuse the archetype->identity machinery
    chapters={"chapters": ("Find the harbour. Read why it's empty.",
                           "Someone ordered the boats out. Find the log.",
                           "A second order came. Find where it stopped.",
                           "The tower still works. Decide what leaves with you."),
              "retro_lead": "You worked the cove out, one berth at a time:",
              "retro_tail": "and every time the way through was there to be read."},
)


class _IO:
    renders_natively = True

    def __init__(self, answers=()):
        self.log = []
        self._answers = list(answers)

    def say(self, *a, **k):
        self.log.append(" ".join(str(x) for x in a))

    def ask(self, prompt=""):
        return self._answers.pop(0) if self._answers else ""

    def ask_yes_no(self, prompt):
        return False


def _reset():
    Apocrysis.reset_campaign_state()


def _solve(g):
    m = g.mystery
    for ev in list(m.knowledge.evidence):
        m.knowledge.discover(ev)
    for fid in list(m.knowledge.facts):
        m.knowledge.observe_fact(fid)
    m.obstacle_open = True
    g.current_position = m.escape_tile
    g.io.log.clear()
    g.mystery_try_escape()
    return "\n".join(g.io.log)


class TestPhaseFSeam(unittest.TestCase):
    def setUp(self):
        _reset()

    def tearDown(self):
        _reset()

    def test_world_2_constructs_and_generates_a_map(self):
        g = Apocrysis("Cove", seed=3, io=_IO(), world=COVE)
        self.assertIs(g.world, COVE)
        self.assertTrue(g.map and g.mystery is not None)
        # the archetype came from COVE, not Silence
        self.assertIn(g.map_archetype, ("coast", "moor"))

    def test_world_id_string_resolves_via_registry_default(self):
        # an unknown id falls back to the default world (not a crash)
        g = Apocrysis("X", seed=1, io=_IO(), world="no-such-world")
        self.assertEqual(g.world.id, "silence")

    def test_mechanism_is_always_from_the_supported_subset(self):
        from src.escape import choose_mechanism
        picked = set()
        for s in range(40):
            picked.add(choose_mechanism(
                __import__("random").Random(s), [], supported=COVE.manifest.supported_mechanisms))
        self.assertTrue(picked)
        self.assertTrue(picked <= set(COVE.manifest.supported_mechanisms),
                        f"picked outside subset: {picked}")

    def test_solving_an_expedition_marks_a_cove_fact_not_a_silence_fact(self):
        g = Apocrysis("Cove", seed=5, io=_IO(), world=COVE, expeditions_completed=0)
        self.assertEqual(g.mystery.world_fact_id, "C_HARBOUR_EMPTY")
        _solve(g)
        self.assertTrue(g.world_investigation.is_known("C_HARBOUR_EMPTY"))
        # no Silence id exists in this campaign's investigation at all
        self.assertIsNone(g.world_investigation.fact("DIS_ORGANISED"))
        self.assertIsNone(g.world_investigation.fact("RESP_THE_CHOICE"))

    def test_the_finale_uses_cove_content(self):
        _reset()
        Apocrysis._world_investigation = {
            "C_HARBOUR_EMPTY": "known", "C_ORDER_TO_GO": "known",
        }
        g = Apocrysis("Cove", seed=4, io=_IO(["1"]), world=COVE,
                      expeditions_completed=7)
        self.assertTrue(getattr(g.mystery, "is_finale", False))
        self.assertEqual(g.mystery.world_fact_id, "C_THE_CALL")
        self.assertIn("the relay tower", g.mystery.site_labels.values())
        out = _solve(g)
        self.assertIn("THE COAST STATION IS ON THE LINE", out)
        self.assertIn("pass the rescinded order", out)
        self.assertEqual(Apocrysis._campaign_ending, "send")
        self.assertNotIn("Protocol Seven", out)
        self.assertNotIn("cordon", out)

    def test_hypothesis_ladder_is_cove_specific(self):
        g = Apocrysis("Cove", seed=1, io=_IO(), world=COVE)
        h = g.world_investigation.current_hypothesis()
        self.assertEqual(h.id, "CH_STORM")

    def test_chapter_framing_uses_cove_manifest(self):
        from src.campaign import chapter_intro, chapter_for_expedition
        # 4 chapters, campaign length 8
        self.assertEqual(chapter_for_expedition(7, COVE), 4)
        intro = chapter_intro(0, 0, COVE)
        self.assertIn("of 8", intro)
        self.assertIn("Find the harbour", intro)


class TestNoWorldOneConditionalsInEngine(unittest.TestCase):
    def test_engine_has_no_world_id_branching_or_concrete_world_imports(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        engine = [
            root / "game.py", root / "campaign.py", root / "escape.py",
            root / "escape_model.py", root / "knowledge.py",
            root / "combat_forecast.py", root / "world_investigation.py",
        ]
        engine += list((root / "mixins").glob("*.py"))
        engine += list((root / "worldgen").glob("*.py"))

        offenders = []
        for path in engine:
            src = path.read_text()
            tree = ast.parse(src, str(path))
            for node in ast.walk(tree):
                # `world.id == ...`  /  `... == world.id`
                if isinstance(node, ast.Compare):
                    for side in [node.left, *node.comparators]:
                        if (isinstance(side, ast.Attribute) and side.attr == "id"
                                and isinstance(side.value, ast.Attribute)
                                and side.value.attr == "world"):
                            offenders.append(f"{path.name}: world.id comparison")
                # `from src.worlds.silence[...] import ...`
                if isinstance(node, ast.ImportFrom) and node.module \
                        and node.module.startswith("src.worlds.silence"):
                    offenders.append(f"{path.name}: imports {node.module}")
                if isinstance(node, ast.Import):
                    for a in node.names:
                        if a.name.startswith("src.worlds.silence"):
                            offenders.append(f"{path.name}: imports {a.name}")
        self.assertEqual(offenders, [], f"engine still knows about a concrete world: {offenders}")


if __name__ == "__main__":
    unittest.main()
