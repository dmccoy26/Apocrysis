"""World 1 - "The Silence". Content only; no engine imports.

Assembles the World object the engine consumes from the per-aspect
content modules in this package (truth / discovery / hypotheses / lore /
population / terrain / manifest / chapters / finale). Nothing in here
imports from the engine - a World is data the engine reads.

`src/constants.py` still re-exports TERRAIN_SYMBOLS / TERRAIN_LEGEND /
MAP_ARCHETYPES from this module as a Phase-A.0 back-compat shim; they
now originate in terrain.py.
"""
from src.worlds.base import World
from src.worlds.silence import population as _population
from src.worlds.silence.chapters import CHAPTERS_DICT
from src.worlds.silence.discovery import DISCOVERY_TEMPLATES
from src.worlds.silence.finale import FINALE
from src.worlds.silence.hypotheses import REGIONAL_HYPOTHESES
from src.worlds.silence.lore import SURVIVOR_LORE, LORE_TRIGGERS
from src.worlds.silence.manifest import MANIFEST
from src.worlds.silence.terrain import (
    TERRAIN_SYMBOLS,          # re-exported for the constants.py shim
    TERRAIN_LEGEND,
    MAP_ARCHETYPES,
    TERRAIN_MOVE_MINUTES,
    IMPASSABLE_TERRAIN,
    GENERATOR_TERRAIN_ORDER,
)
from src.worlds.silence.truth import WORLD_FACTS
from src.worlds.base import WorldTerrain


_TERRAIN = WorldTerrain(
    symbols=TERRAIN_SYMBOLS,
    legend=TERRAIN_LEGEND,
    archetypes=MAP_ARCHETYPES,
    move_minutes=TERRAIN_MOVE_MINUTES,
    impassable=IMPASSABLE_TERRAIN,
    generator_terrain_order=GENERATOR_TERRAIN_ORDER,
)


SILENCE = World(
    id="silence",
    name="Apocrysis",
    description=(
        "You wake in a valley that has gone quiet. No people. The "
        "infected. Infrastructure half standing. You do not know why, "
        "and nothing here will tell you."
    ),
    terrain_symbols=TERRAIN_SYMBOLS,
    terrain_legend=TERRAIN_LEGEND,
    map_archetypes=MAP_ARCHETYPES,
    prose={
        "place_name_fallback": "THE VALLEY",
        "leave_verb": "leave the valley",
        # World Investigation screen: player-facing name + question per
        # thread. The player never sees the raw thread id.
        "thread_titles": {
            "disappearance": ("THE SILENCE", "Where did the people go?"),
            "dead": ("THE INFECTED", "What are they, and where did they start?"),
            "response": ("THE RESPONSE", "Who ordered it, and why?"),
        },
        # v4 Phase B stopgap ambient flavour clues, surfaced in buildings
        # so the journal/inspect interface has content. WORLD_1_LORE_PASS
        # replaces these with authored per-band lore. (text, journal_line)
        "ambient_clues": (
            ("Someone scratched a tally of days into the doorframe - it stops at 46.",
             "A tally of days scratched by the door stops at 46."),
            ("A child's drawing is taped to the wall: stick figures walking toward mountains.",
             "A child's drawing shows people walking toward the mountains."),
            ("A note on the fridge: 'Gone to the muster point. Back by dark. - R'",
             "A fridge note mentions a 'muster point'."),
            ("The calendar is turned to a month with one date circled hard enough to tear it.",
             "A calendar has a single date circled hard enough to tear the paper."),
            ("Boot prints in the dried mud all lead the same way - out the back, north.",
             "Boot prints here all lead north."),
        ),
    },
    discovery_templates=DISCOVERY_TEMPLATES,
    world_facts=WORLD_FACTS,
    survivor_lore=SURVIVOR_LORE,
    lore_triggers=LORE_TRIGGERS,
    regional_hypotheses=REGIONAL_HYPOTHESES,
    manifest=MANIFEST,
    terrain=_TERRAIN,
    finale=FINALE,
    population=_population,
    chapters=CHAPTERS_DICT,
)
