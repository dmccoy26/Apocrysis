# Auto-extracted from the original monolithic apocrysis.py during
# the src/ restructuring - see README.md for the project layout.

# ANSI Color Codes for Terminal Emphasis
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"
CYAN = "\033[96m"

# Real bug found live: wilderness terrain ('forest'/'building'/'water'/
# 'plain', set on every non-town tile in generate_map()) only ever
# showed up as flavor text AFTER stepping onto a tile
# ("You move through dense forest.") - print_map() never rendered it,
# so every wilderness tile looked identical (.) regardless of
# terrain. This maps each real terrain type to a map symbol so it's
# visible before you walk into it. No 'mountain'/'river' terrain
# exists in generate_map()'s terrain_types - only what's actually
# generated is mapped here, rather than inventing symbols for terrain
# that was never implemented.
TERRAIN_SYMBOLS = {
    'forest': 'f',
    'water': '~',
    'building': 'b',
    'plain': '.',
    'mountain': '^',
    'river': '=',
}

TERRAIN_LEGEND = (
    "  f = forest   ~ = water   b = building   . = plain\n"
    "  ^ = mountain (impassable)   = = river (impassable)\n"
    "  T/H/R/S/B = town tiles (Town center/House/Road/Shop/Building)\n"
    "  P = you   Z = zombie (only shown once you've been there)"
)

# v3 SPRINT: impassable terrain, introduced from generate_map() -
# movement onto these blocks (world_mixin.py's move_and_search()).
IMPASSABLE_TERRAIN = {'mountain', 'river'}

# v3 SPRINT: map size/town-distance/obstacle-density scale with the
# player's level, not a fixed size chosen at game start. All derived
# in world_mixin.py's generate_map(); named here so the formulas
# aren't buried inline.
BASE_MAP_SIZE = 15
MAP_GROWTH_PER_LEVEL = 2
MAX_MAP_SIZE = 50

BASE_TOWN_MIN_DISTANCE = 6
TOWN_DISTANCE_GROWTH_PER_LEVEL = 2

OBSTACLE_DENSITY_CAP = 0.18
OBSTACLE_DENSITY_PER_LEVEL = 0.015
OBSTACLE_START_LEVEL = 4

# v3 SPRINT: per-turn status-effect damage, data-driven so a new
# status (e.g. ToxicZombie's "Poison") needs no new code path in
# combat_mixin.py's encounter_zombie() - only an entry here.
STATUS_EFFECT_DAMAGE = {
    "Bleeding": 2,
    "Poison": 3,
}

# v3 SPRINT: a full day/night cycle used to be 1440 minutes (24h) at
# 15 min/move - a ~10-move trek to town (150 min) barely dented it.
# Shortened so a normal trek actually crosses meaningful portions of
# a day/night cycle. Terrain-dependent move cost (still 15 as the
# baseline for plain/town/building) replaces the old flat +15.
#
# Implementation note (game.py's _update_time()): time_of_day itself
# stays on the real 1440-minute clock unchanged - hour/minute display
# (ui_mixin.py) and the is_night hour thresholds need no changes at
# all. Only how FAST it advances per move changes: each move's real
# minute cost is scaled up by DAY_COMPRESSION_SCALE before being
# added, so MINUTES_PER_DAY of "trek time" advances a full 1440-minute
# clock instead of only denting it.
MINUTES_PER_DAY = 240
DAY_COMPRESSION_SCALE = 1440 / MINUTES_PER_DAY

TERRAIN_MOVE_MINUTES = {
    'plain': 15,
    'town': 15,
    'building': 15,
    'forest': 20,
    'water': 30,
    'mountain': 40,
    'river': 40,
}

# Real bug found live: world_mixin.py's find_loot() used to build
# every looted weapon as MeleeWeapon(name, 10, 100) regardless of
# which name got picked - a "Rusty Dagger" and a "Steel Katana" were
# mechanically identical, and "Broken Rifle"/"Leather Bow" (names
# that clearly mean a ranged weapon) were built as MeleeWeapon
# instances that could never use ammo/reload at all. Real stat
# variance tied to the name, and the correct weapon type per name.
LOOT_WEAPON_TABLE = {
    "Rusty Dagger": {"type": "melee", "damage": 8, "durability": 40},
    "Chipped Sword": {"type": "melee", "damage": 12, "durability": 50},
    "Iron Axe": {"type": "melee", "damage": 16, "durability": 90},
    "Steel Katana": {"type": "melee", "damage": 20, "durability": 110},
    "Broken Rifle": {"type": "ranged", "damage": 10, "max_ammo": 5, "durability": 15},
    "Leather Bow": {"type": "ranged", "damage": 14, "max_ammo": 8, "durability": 45},
}
