"""World 2 - "The Wake": ship terrain. docs/WORLD_2_THE_WAKE.md §9.

The engine's terrain *roles* (barrier / shelter / open / slow / hazard /
very-slow) are keyed to the standard names below - a world may re-glyph
them and retune their cost, but not rename the role key (that would be
Tier-2 role-registry work, out of scope). So 'forest' is a debris-
choked section, 'water' is a breach, 'mountain' is the outer hull.
"""
from src.worlds.base import WorldTerrain

# role key (unchanged) -> ship glyph
TERRAIN_SYMBOLS = {
    'forest': 'x',      # wreckage - collapsed, debris-choked section
    'water': '~',       # breach - open to vac / depressurised run
    'building': 'o',    # compartment - a sealed, pressurised room
    'plain': '.',       # corridor - open deck
    'mountain': '#',    # hull - the ship's outer skin; the boundary
    'river': ':',       # (unused in archetypes)
    'bridge': '=',      # gangway
    'swamp': ',',       # driftfield - a section where the gravity failed
}

TERRAIN_LEGEND = (
    "  x = wreckage   ~ = breach (exposed)   o = compartment   . = corridor\n"
    "  # = hull (no way through)   , = driftfield (grav out - slow)\n"
    "  M/H/R/S/B = enclave (Muster/Hab/Run/Store/Bay)\n"
    "  P = you   Z = one of the changed (only shown once you've been there)\n"
    "  ? = the helmet detects something here   ! = identified, or reached on foot\n"
    "  + = the way out, now open"
)

# positional [forest, building, water, plain, swamp] = wreckage,
# compartment, breach, corridor, driftfield.
MAP_ARCHETYPES = {
    'habitation':  {'weights': [0.14, 0.36, 0.05, 0.40, 0.05], 'blurb': "Cabin doors down both sides of a long corridor. Someone lived every one of these."},
    'engineering': {'weights': [0.42, 0.12, 0.10, 0.26, 0.10], 'blurb': "Gantries and conduit and machinery the size of rooms - and half of it torn loose."},
    'open_decks':  {'weights': [0.16, 0.16, 0.06, 0.56, 0.06], 'blurb': "A long open deck, the overhead lights dead in stretches."},
    'damaged':     {'weights': [0.20, 0.10, 0.34, 0.26, 0.10], 'blurb': "The hull's open to vacuum in places. Frost on every surface the air still reaches."},
    'flooded_bay': {'weights': [0.18, 0.14, 0.10, 0.30, 0.28], 'blurb': "Whole compartments adrift - the artificial gravity is gone here, and everything loose with it."},
}

# a ship's rooms cost about the same to cross as a valley path; the
# hazards cost more.
TERRAIN_MOVE_MINUTES = {
    'plain': 14, 'town': 14, 'building': 14, 'bridge': 14,
    'forest': 20,     # wreckage - climb over
    'water': 30,      # breach - suit up, move slow
    'mountain': 40, 'river': 40,
    'swamp': 34,      # driftfield - pull yourself along
}

IMPASSABLE_TERRAIN = frozenset({'mountain', 'river'})
GENERATOR_TERRAIN_ORDER = ('forest', 'building', 'water', 'plain', 'swamp')

# §F.11: the fiction of moving through the ship. Same semantic slots as
# The Silence, ship claims instead of valley claims. Roles: shelter =
# a sealed compartment, slow = a breach open to vac, dense = a section
# torn off its frame, barrier = the outer hull, crossing = a gap blown
# in the deck (rivers don't generate here - kept for completeness).
TERRAIN_PROSE = {
    "enter": {
        "shelter": "You get the hatch shut behind you. Pressurised, and for now safe.",
        "slow": "You work through a stretch open to vacuum - suit stiff, every move slow.",
        "dense": "You climb through a section half torn off its frame.",
    },
    "reenter": {
        "shelter": "Back in a sealed compartment. Safe for now.",
        "slow": "More of the breach. Slow going.",
    },
    "hazard": {
        "slow": "The cold reaches through the suit. You lost some health.",
    },
    "barrier": {
        "edge_first": "The outer hull. Solid plate, and past it nothing - "
                      "no way through here, and none you can see anywhere "
                      "along it.",
        "edge": "The hull. There's no way through it.",
        "interior": "Hull plate. Nothing gets through here.",
    },
    "crossing": {
        "blocked": "The deck's blown out here. No way across.",
        "title": "THE GAP",
        "prompt": "Jump it?  ~{pct}% you land clean.",
        "prompt_body": "Miss and you're back on this side, hard - and you "
                       "may lose something loose from your pack.",
        "ask": "Jump for it?",
        "ok": "You land it, jarred but over.",
        "fail": "You come up short and slam back onto this side.",
        "loss": "You lost some {k} into the gap.",
    },
    "spot": {
        "shelter": "A compartment stands sealed off on its own up ahead.",
        "settlement": "Lights further in - a section with power still on it.",
    },
    "label": {
        "forest": "WRECKAGE", "water": "BREACH", "swamp": "DRIFTFIELD",
        "plain": "CORRIDOR", "building": "A COMPARTMENT",
        "mountain": "THE HULL", "settlement": "AN ENCLAVE",
    },
    "hud_slow": {
        "water": "vac - move slow", "swamp": "grav out - haul yourself along",
        "forest": "climbing through wreckage",
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
    # a ship's enclave, not a valley town: Muster / Hab / Run / Store / Bay
    settlement_glyphs=('M', 'H', 'R', 'S', 'B'),
)
