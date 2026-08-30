# Auto-extracted from the original monolithic apocrysis.py during
# the src/ restructuring - see README.md for the project layout.

# ANSI Color Codes for Terminal Emphasis
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"
CYAN = "\033[96m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
GREY = "\033[90m"
# 256-colour; the deterioration middle band (docs/ATTENTION_SYSTEM_SPEC.md).
# Degrades to a yellow-ish tone on a 16-colour terminal - acceptable.
ORANGE = "\033[38;5;208m"


def stat_band(kind, value, maximum=100):
    """docs/ATTENTION_SYSTEM_SPEC.md - the HUD escalation ladder.
    'normal' | 'warning' | 'danger' for a resource readout. kind:
    'hunger' | 'thirst' | 'hp' | 'fatigue' | 'food' | 'water' |
    'weapon' (value = durability fraction 0..1)."""
    if kind in ("hunger", "thirst"):
        return "danger" if value < 15 else "warning" if value < 40 else "normal"
    if kind == "hp":
        pct = 100 * value / max(1, maximum)
        return "danger" if pct < 20 else "warning" if pct <= 40 else "normal"
    if kind == "fatigue":
        return "danger" if value > 85 else "warning" if value > 50 else "normal"
    if kind in ("food", "water"):
        return "danger" if value <= 0 else "warning" if value < 15 else "normal"
    if kind == "weapon":
        return "danger" if value <= 0.10 else "warning" if value <= 0.25 else "normal"
    return "normal"

# Per-terrain map colour (playtest: "colour the squares so the map is
# easier to read"). Keyed by terrain name; the tile keeps its own
# glyph, this only tints it. Fog / unexplored stays uncoloured.
TERRAIN_COLOR = {
    "forest": GREEN,
    "water": BLUE,
    "river": CYAN,
    "bridge": "\033[38;5;130m",   # brown - a way across
    "swamp": "\033[33m",   # dim yellow-green
    "building": YELLOW,
    "plain": GREY,
    "mountain": "\033[97m",  # bright white - reads as a wall
    "town": BOLD + MAGENTA,
}

# Phase A.0: the tile vocabulary, the map legend and the map archetypes
# are World 1 content and now live in the World that owns them
# (src/worlds/silence/world.py). Re-exported here so existing
# `from src.constants import ...` call sites keep working while the
# engine is migrated to read them off `game.world` (Phase A.0 step 5).
from src.worlds.silence.world import (  # noqa: F401
    TERRAIN_SYMBOLS,
    TERRAIN_LEGEND,
    MAP_ARCHETYPES,
)

# v3 SPRINT: impassable terrain, introduced from generate_map() -
# movement onto these blocks (world_mixin.py's move_and_search()).
IMPASSABLE_TERRAIN = {'mountain', 'river'}

# v4: survival pressure retuned down so a full generated expedition can
# carry a 25-35 turn investigation without the player dying to combat
# first (the architecture conflict the vertical slice isolated). Not
# eliminated - combat is still the pressure system - just dialled to
# where it stops overwriting the investigation loop. Tune against
# tools/mystery_solver.py's solve rate + the balance harness.
ZOMBIE_MAP_DENSITY = 0.04        # was 0.10
ENCOUNTER_CHANCE_DAY = 0.10       # was 0.30
ENCOUNTER_CHANCE_NIGHT = 0.20     # was 0.50

# v3 SPRINT: map size/town-distance/obstacle-density scale with the
# player's level, not a fixed size chosen at game start. All derived
# in world_mixin.py's generate_map(); named here so the formulas
# aren't buried inline.
#
# v4 Phase A (todo aa461cec): a hard gameplay ceiling instead of open
# growth to 50x50. Map dimensions are bounded by player comprehension,
# not renderer capability - the world must be small enough to hold a
# mental model of within one expedition. Later expeditions get
# *conceptually* harder (richer mystery), not physically larger, so
# the growth curve is still bounded: 15x15 at expedition 0, growing
# 3/expedition and hard-capped at MAX_MAP_SIZE. See "Physical &
# information budget" in docs/ESCAPE_WORLD_DESIGN_ASSESSMENT.md.
BASE_MAP_SIZE = 15
MAP_GROWTH_PER_LEVEL = 3
MAX_MAP_SIZE = 34
# docs/MAP_REALISM_SPEC.md 1b - the "landscape" generator's width:height.
MAP_ASPECT = 1.6
# The full World-1 arc: 5 chapters + finale (docs/APOCRYSIS_ROADMAP.md
# section 9, docs/ROADMAP_STATUS.md). Expeditions 0..DIFFICULTY_RAMP_LENGTH
# are the fresh-survivor-viable band; past that, deep expeditions are
# inheritance-scaled (docs/PHASE_C3_2_7_SUPPORTED_DEPTH.md).
CAMPAIGN_LENGTH = 25  # expeditions_completed value at which the campaign is beaten
# The combat / encounter difficulty ramp reaches full strength at this
# many expeditions and HOLDS there - it is deliberately NOT tied to
# CAMPAIGN_LENGTH, so extending the arc past 10 does not stretch (and
# thereby soften) the frozen difficulty curve it was tuned against.
DIFFICULTY_RAMP_LENGTH = 10

BASE_TOWN_MIN_DISTANCE = 6
TOWN_DISTANCE_GROWTH_PER_LEVEL = 2

# Chunk-based terrain generation investigation: one terrain type rolls
# per CHUNK_SIZE x CHUNK_SIZE block instead of per tile, so forests/
# plains/etc form contiguous regions rather than an independent-roll
# checkerboard. Obstacle terrain (mountain/river) still rolls per-tile
# as an overlay inside any chunk - see generate_map().
CHUNK_SIZE = 4

# MAP_ARCHETYPES moved to src/worlds/silence/world.py (re-exported at the
# top of this file). The generator reads it via world.map_archetypes.

# Multiple-settlements investigation: how many populated areas a map
# can contain, scaling with expeditions_completed (1 early, up to 3
# later) - only one ever holds the real Town Center; the rest are
# decoys with no win-triggering tile at all.
MAX_SETTLEMENTS = 3
SETTLEMENTS_PER_EXPEDITIONS = 4  # +1 settlement every this-many expeditions_completed

# Combat difficulty scaling (world_mixin.py's _select_zombie_for_
# encounter()) - composition (which zombie types appear, and whether
# an elite variant rolls) now does most of the scaling work, keyed to
# expeditions_completed rather than raw player level or in-run day.
# MAX_DAY_DIFFICULTY_FACTOR caps the old flat per-day stat multiplier
# (previously unbounded: day * 0.2, ~3x by day 15) so it's a mild
# in-run ramp rather than the primary difficulty lever.
MAX_DAY_DIFFICULTY_FACTOR = 1.5
ELITE_MIN_EXPEDITION = 3
ELITE_STAT_MULTIPLIER = 1.5

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
    'bridge': 15,
    'swamp': 35,
}

# Real bug found live: world_mixin.py's find_loot() used to build
# every looted weapon as MeleeWeapon(name, 10, 100) regardless of
# which name got picked - a "Rusty Dagger" and a "Steel Katana" were
# mechanically identical, and "Broken Rifle"/"Leather Bow" (names
# that clearly mean a ranged weapon) were built as MeleeWeapon
# instances that could never use ammo/reload at all. Real stat
# variance tied to the name, and the correct weapon type per name.
LOOT_WEAPON_TABLE = {
    "Rusty Dagger": {"type": "melee", "damage": 8, "durability": 40, "min_expedition": 0},
    "Chipped Sword": {"type": "melee", "damage": 12, "durability": 50, "min_expedition": 0},
    "Iron Axe": {"type": "melee", "damage": 16, "durability": 90, "min_expedition": 4},
    "Steel Katana": {"type": "melee", "damage": 20, "durability": 110, "min_expedition": 6},
    "Broken Rifle": {"type": "ranged", "damage": 10, "max_ammo": 5, "durability": 15, "min_expedition": 0},
    "Leather Bow": {"type": "ranged", "damage": 14, "max_ammo": 8, "durability": 45, "min_expedition": 2},
}

# Equipment-slot investigation, multi-piece follow-up: four slots
# (head/body/hands/feet), each banded by expeditions_completed the
# same way LOOT_WEAPON_TABLE is. Per-slot reductions are kept modest
# (a full head+body+hands+feet loadout at max expedition sums to 13)
# so gearing out doesn't dwarf the old single-slot design's max of 10
# - more pieces to find/maintain, not a flat power multiplier.
ARMOR_TABLE = {
    "Bandana": {"slot": "head", "reduction": 1, "durability": 20, "min_expedition": 0},
    "Combat Helmet": {"slot": "head", "reduction": 3, "durability": 50, "min_expedition": 4},
    "Padded Vest": {"slot": "body", "reduction": 2, "durability": 30, "min_expedition": 0},
    "Kevlar Vest": {"slot": "body", "reduction": 4, "durability": 70, "min_expedition": 3},
    "Riot Armor": {"slot": "body", "reduction": 6, "durability": 100, "min_expedition": 6},
    "Work Gloves": {"slot": "hands", "reduction": 1, "durability": 25, "min_expedition": 0},
    "Reinforced Gauntlets": {"slot": "hands", "reduction": 2, "durability": 50, "min_expedition": 3},
    "Sneakers": {"slot": "feet", "reduction": 1, "durability": 25, "min_expedition": 0},
    "Steel-Toe Boots": {"slot": "feet", "reduction": 2, "durability": 50, "min_expedition": 3},
}
