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

# §F.11: the fiction of moving through the valley. Verbatim the strings
# that were hard-coded in world_mixin / tui - so The Silence's output
# is byte-identical.
TERRAIN_PROSE = {
    "enter": {
        "shelter": "You enter a building. It's a safe zone.",
        "slow": "You wade through water. Movement is difficult.",
        "dense": "You move through dense forest.",
    },
    "reenter": {
        "shelter": "Back inside - safe for now.",
        "slow": "More water. Slow going.",
    },
    "hazard": {
        "slow": "The cold water chills you. You lost some health.",
    },
    "barrier": {
        "edge_first": "The mountains rise up sheer and impossibly high. "
                      "There's no way through here - and looking along "
                      "them, no obvious way through anywhere.",
        "edge": "The mountains block the way. There's no crossing them.",
        "interior": "You can't cross the mountain here.",
    },
    "crossing": {
        "blocked": "You can't cross the river here.",
        "title": "THE RIVER",
        "prompt": "Swim across?  ~{pct}% you make it clean.",
        "prompt_body": "Fail and you're swept back to this bank - a hard "
                       "knock and you may lose something loose from your "
                       "pack. Waders help a lot.",
        "ask": "Swim for it?",
        "ok": "You get across, soaked and cold but on the far bank.",
        "fail": "The current takes you and dumps you back where you started.",
        "loss": "You lost some {k} to the water.",
    },
    "spot": {
        "shelter": "You spot a building standing alone in the distance.",
        "settlement": "Rooftops in the distance - there's a settlement out there.",
    },
    "label": {
        "forest": "FOREST", "water": "WATER", "swamp": "SWAMP",
        "plain": "OPEN GROUND", "building": "A BUILDING",
        "mountain": "THE MOUNTAIN WALL", "settlement": "SETTLEMENT",
    },
    "hud_slow": {
        "water": "slow going", "swamp": "slow, tiring ground",
        "forest": "slower under cover",
    },
}
