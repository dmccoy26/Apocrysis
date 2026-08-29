"""World 1 - "The Silence". Content only; no engine imports.

For Phase A.0 the tile vocabulary / legend / map archetypes are still
*defined* in src/constants.py and imported here by reference, so this
is a pure re-packaging with no value duplicated. A later step moves the
definitions here and leaves constants.py re-exporting them.
"""
from src.worlds.base import World
from src.constants import TERRAIN_SYMBOLS, TERRAIN_LEGEND, MAP_ARCHETYPES

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
    },
)
