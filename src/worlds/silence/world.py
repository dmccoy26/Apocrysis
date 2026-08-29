"""World 1 - "The Silence". Content only; no engine imports.

This module is the **owner** of World 1's tile vocabulary, map
archetypes and prose. `src/constants.py` re-exports the three data
tables from here as a backwards-compatibility shim while the engine is
migrated to read them off `game.world` (Phase A.0 step 5). Nothing in
here imports from the engine - a World is data the engine reads.
"""
from src.worlds.base import World


# Tile vocabulary -------------------------------------------------------
#
# Real bug found live (kept as history): wilderness terrain only ever
# showed as flavour text AFTER stepping onto a tile - print_map() never
# rendered it, so every wilderness tile looked identical. Each real
# terrain type maps to a map symbol so it's visible before you walk in.
TERRAIN_SYMBOLS = {
    'forest': 'f',
    'water': '~',
    'building': 'b',
    'plain': '.',
    'mountain': '^',
    'river': '=',
    'swamp': 's',
}

TERRAIN_LEGEND = (
    "  f = forest   ~ = water   b = building   . = plain   s = swamp (slow)\n"
    "  ^ = mountain (impassable)   = = river (impassable)\n"
    "  T/H/R/S/B = town tiles (Town center/House/Road/Shop/Building)\n"
    "  P = you   Z = zombie (only shown once you've been there)\n"
    "  ! = a lead you've found   + = the way out, now open"
)


# Map archetypes -------------------------------------------------------
#
# Per-expedition map archetype: biases the per-chunk terrain roll so an
# expedition reads as deep woods / flooded basin / suburban sprawl /
# open country / a plain mix. `weights` is POSITIONAL, matching
# world_mixin.generate_map()'s terrain_types order:
# ['forest', 'building', 'water', 'plain', 'swamp'].
MAP_ARCHETYPES = {
    'mixed':          {'weights': [0.28, 0.22, 0.15, 0.25, 0.10], 'blurb': 'A patchwork of woods, fields, and scattered buildings.'},
    'deep_woods':     {'weights': [0.46, 0.10, 0.08, 0.28, 0.08], 'blurb': 'Dense old-growth forest closes in on every side.'},
    'flooded_basin':  {'weights': [0.22, 0.07, 0.30, 0.27, 0.14], 'blurb': 'Low, waterlogged ground - a lot of this valley is under water or sinking into it.'},
    'suburban_sprawl':{'weights': [0.18, 0.34, 0.06, 0.34, 0.08], 'blurb': 'Street after street of empty houses - this was somebody\'s whole town.'},
    'open_country':   {'weights': [0.20, 0.12, 0.09, 0.53, 0.06], 'blurb': 'Wide open farmland and fields, with little cover anywhere.'},
}


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
