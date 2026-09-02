"""World 3 - "The Deep": mine terrain. docs/WORLD_3_THE_DEEP.md §5B.10.

The engine's terrain *roles* (barrier / shelter / open / slow / hazard /
very-slow) are keyed to the standard names below - a world may re-glyph
them and retune their cost, not rename the role key. So 'forest' is
spoil / a fall, 'water' is a flooded gallery, 'mountain' is solid rock
(the boundary).
"""
from src.worlds.base import WorldTerrain

# role key (unchanged) -> mine glyph
TERRAIN_SYMBOLS = {
    'forest': 'x',      # spoil - a fall, broken ground, climb over
    'water': '~',       # a flooded gallery - wade, slow
    'building': 'o',    # a compartment / a station - walls and a door
    'plain': '.',       # drift - an open worked passage
    'mountain': '#',    # solid rock - the boundary
    'river': ':',       # (unused in archetypes)
    'bridge': '=',      # a stull / a plank crossing over a winze
    'swamp': ',',       # a drift with the timber gone - pick your way, slow
}

TERRAIN_LEGEND = (
    "  x = fall (broken ground)   ~ = flooded gallery   o = a compartment\n"
    "  . = drift (open passage)   # = solid rock (no way through)   , = bad ground (slow)\n"
    "  C/M/Q/S/D = a held circuit (Circuit/Machine shop/Quarters/Store/Deep muster)\n"
    "  P = you   Z = one of the Changed (only shown once you've been there)\n"
    "  ! = a lead you've found   + = the way down, now open"
)

# positional [forest, building, water, plain, swamp] = fall, compartment,
# flooded, drift, bad ground.
MAP_ARCHETYPES = {
    'upper_works':      {'weights': [0.16, 0.34, 0.06, 0.40, 0.04], 'blurb': "A working maintenance level - corridors, ordinary machinery, the heat still bearable."},
    'extraction_face':  {'weights': [0.30, 0.18, 0.08, 0.34, 0.10], 'blurb': "Active extraction ground - narrower drifts, the heat up, dust in the light, cutting faces off to the sides."},
    'deep_workings':    {'weights': [0.34, 0.14, 0.16, 0.24, 0.12], 'blurb': "Richer ore and worse air. The infra down here has been failing for a while, and the comms are dead."},
    'sealed_galleries': {'weights': [0.30, 0.20, 0.14, 0.20, 0.16], 'blurb': "Welded doors, vent plumbing carved off on its own, the air gone thin. Something built this to hold."},
    'the_bore':         {'weights': [0.24, 0.22, 0.10, 0.36, 0.08], 'blurb': "The deepest working face, and the seal standing across it. Few things move down here. All of the weight is on the decision."},
}

# a drift crosses about as fast as a valley path; the hazards cost more.
TERRAIN_MOVE_MINUTES = {
    'plain': 14, 'town': 14, 'building': 14, 'bridge': 14,
    'forest': 20,     # a fall - climb it
    'water': 30,      # a flooded gallery - wade
    'mountain': 40, 'river': 40,
    'swamp': 34,      # bad ground - pick your way
}

IMPASSABLE_TERRAIN = frozenset({'mountain', 'river'})
GENERATOR_TERRAIN_ORDER = ('forest', 'building', 'water', 'plain', 'swamp')

# §F.11: the fiction of moving through the mine. Same semantic slots as
# The Silence, mine claims. shelter = a compartment, slow = a flooded
# gallery, dense = a fall, barrier = solid rock, crossing = a winze
# blown open in the floor.
TERRAIN_PROSE = {
    "enter": {
        "shelter": "You get the door shut behind you. Four walls and a roof of good rock - safe for now.",
        "slow": "You wade a flooded stretch of gallery - thigh-deep, cold, every step slow.",
        "dense": "You climb through a fall, hand over hand across broken ground.",
    },
    "reenter": {
        "shelter": "Back in a compartment with a door on it. Safe for now.",
        "slow": "More flooded gallery. Slow going.",
    },
    "hazard": {
        "slow": "The bad air reaches you before you're through. You lost some health.",
    },
    "barrier": {
        "edge_first": "Solid rock. No drift, no seam, nothing worked - "
                      "and none you can find anywhere along it.",
        "edge": "Solid rock. There's no way through it here.",
        "interior": "The face is solid rock. Nothing goes through here.",
    },
    "crossing": {
        "blocked": "The floor's gone here - a winze blown open, straight down into the dark. No way across.",
        "title": "THE WINZE",
        "prompt": "Jump it?  ~{pct}% you land clean.",
        "prompt_body": "Miss and you're back on this side, hard - and you "
                       "may lose something loose from your pack.",
        "ask": "Jump for it?",
        "ok": "You land it, jarred but over.",
        "fail": "You come up short and slam back onto this side.",
        "loss": "You lost some {k} down the winze.",
    },
    "spot": {
        "shelter": "A compartment stands off the drift ahead, its door shut.",
        "settlement": "Lights further in - a stretch with power still on it.",
    },
    "label": {
        "forest": "A FALL", "water": "A FLOODED GALLERY", "swamp": "BAD GROUND",
        "plain": "DRIFT", "building": "A COMPARTMENT",
        "mountain": "SOLID ROCK", "settlement": "A HELD CIRCUIT",
    },
    "hud_slow": {
        "water": "flooded - wade it", "swamp": "bad ground - pick your way",
        "forest": "climbing a fall",
    },
}

TERRAIN = WorldTerrain(
    symbols=TERRAIN_SYMBOLS,
    legend=TERRAIN_LEGEND,
    archetypes=MAP_ARCHETYPES,
    move_minutes=TERRAIN_MOVE_MINUTES,
    impassable=IMPASSABLE_TERRAIN,
    generator_terrain_order=GENERATOR_TERRAIN_ORDER,
    prose=TERRAIN_PROSE,
    # a held circuit underground, not a valley town: Circuit / Machine
    # shop / Quarters / Store / Deep muster
    settlement_glyphs=('C', 'M', 'Q', 'S', 'D'),
)
