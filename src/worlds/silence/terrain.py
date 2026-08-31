"""World 1 - "The Silence": tile vocabulary, map legend, archetypes,
per-tile move cost. Content only; no engine imports.

Phase F: the engine reads all of this off `game.world.terrain`
(WorldTerrain). `src/constants.py` re-exports the three legacy names
(TERRAIN_SYMBOLS / TERRAIN_LEGEND / MAP_ARCHETYPES) from here as a
back-compat shim until every call site is migrated.

Terrain *mechanics* (forest slows, water chills, river = swim, building
= safe zone, mountain = wall) stay in the engine, keyed to the role -
NOT the name. A world may rename any of these.
"""

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
    'bridge': '#',   # MAP_REALISM_SPEC: a crossing on the river
    'swamp': 's',
}

TERRAIN_LEGEND = (
    "  f = forest   ~ = water   b = building   . = plain   s = swamp (slow)\n"
    "  ^ = mountain (impassable)   = = river (swim or bridge)   # = bridge\n"
    "  T/H/R/S/B = town tiles (Town center/House/Road/Shop/Building)\n"
    "  P = you   Z = zombie (only shown once you've been there)\n"
    "  ! = a lead you've found   + = the way out, now open"
)

# Per-expedition map archetype: biases the per-chunk terrain roll so an
# expedition reads as deep woods / flooded basin / suburban sprawl /
# open country / a plain mix. `weights` is POSITIONAL, matching
# WorldTerrain.generator_terrain_order (worldgen/generator.py):
# ['forest', 'building', 'water', 'plain', 'swamp'].
MAP_ARCHETYPES = {
    'mixed':          {'weights': [0.28, 0.22, 0.15, 0.25, 0.10], 'blurb': 'A patchwork of woods, fields, and scattered buildings.'},
    'deep_woods':     {'weights': [0.46, 0.10, 0.08, 0.28, 0.08], 'blurb': 'Dense old-growth forest closes in on every side.'},
    'flooded_basin':  {'weights': [0.22, 0.07, 0.30, 0.27, 0.14], 'blurb': 'Low, waterlogged ground - a lot of this valley is under water or sinking into it.'},
    'suburban_sprawl':{'weights': [0.18, 0.34, 0.06, 0.34, 0.08], 'blurb': 'Street after street of empty houses - this was somebody\'s whole town.'},
    'open_country':   {'weights': [0.20, 0.12, 0.09, 0.53, 0.06], 'blurb': 'Wide open farmland and fields, with little cover anywhere.'},
}

# Minutes to cross one tile of each terrain (game._update_time). 15 is
# the plain/town/building baseline; slow ground costs more.
TERRAIN_MOVE_MINUTES = {
    'plain': 15,
    'town': 15,
    'building': 15,
    'forest': 20,
    'water': 30,
    'mountain': 40,
    'river': 40,
    'bridge': 15,
    'swamp': 35,
}

IMPASSABLE_TERRAIN = frozenset({'mountain', 'river'})

# worldgen/generator.py's positional terrain roll order - the archetype
# weight vectors above line up with this.
GENERATOR_TERRAIN_ORDER = ('forest', 'building', 'water', 'plain', 'swamp')
