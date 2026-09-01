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
    Four semantic states so the colour shifts BEFORE the player is in
    real trouble, not only at empty:  'normal' | 'watch' | 'warning' |
    'danger'.  kind: 'hunger' | 'thirst' | 'hp' | 'fatigue' | 'food' |
    'water' | 'weapon' (value = durability fraction 0..1)."""
    if kind in ("hunger", "thirst"):
        return ("danger" if value < 15 else "warning" if value < 40
                else "watch" if value < 60 else "normal")
    if kind == "hp":
        pct = 100 * value / max(1, maximum)
        return ("danger" if pct < 20 else "warning" if pct <= 40
                else "watch" if pct <= 65 else "normal")
    if kind == "fatigue":   # inverted - higher is worse
        return ("danger" if value > 85 else "warning" if value > 55
                else "watch" if value > 35 else "normal")
    if kind in ("food", "water"):
        return ("danger" if value <= 0 else "warning" if value < 12
                else "watch" if value < 25 else "normal")
    if kind == "weapon":
        return ("danger" if value <= 0.10 else "warning" if value <= 0.25
                else "watch" if value <= 0.45 else "normal")
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

# Phase A.0 / Phase F: the tile vocabulary, legend, archetypes and
# per-tile move cost are World content and live in the World that owns
# them (src/worlds/<w>/terrain.py -> game.world.terrain). Re-exported
# here from the DEFAULT world so existing `from src.constants import
# ...` call sites keep working while the engine is migrated to read
# them off `game.world.terrain`.
from src.worlds.silence.terrain import (  # noqa: F401
    TERRAIN_SYMBOLS,
    TERRAIN_LEGEND,
    MAP_ARCHETYPES,
    TERRAIN_MOVE_MINUTES,
    IMPASSABLE_TERRAIN,
)

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
# Phase F: campaign length and the difficulty-ramp length are per-world
# (world.manifest). Re-exported here from the DEFAULT world for legacy
# `from src.constants import CAMPAIGN_LENGTH` call sites; engine code
# with a game in hand should read game.world.manifest instead.
from src.worlds.silence.manifest import MANIFEST as _DEFAULT_MANIFEST
CAMPAIGN_LENGTH = _DEFAULT_MANIFEST.campaign_length
DIFFICULTY_RAMP_LENGTH = _DEFAULT_MANIFEST.difficulty_ramp_length

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

# TERRAIN_MOVE_MINUTES moved to src/worlds/silence/terrain.py (Phase F);
# re-exported at the top of this file.

# Phase F §F.10: equipment vocabulary is world-owned
# (src/worlds/<w>/loot.py, read via src/loot.py). Re-exported here from
# the DEFAULT world for legacy `from src.constants import
# LOOT_WEAPON_TABLE` call sites (tests, dev.py); engine code with a
# game in hand goes through src.loot.weapon_table(game.world).
from src.worlds.silence.loot import (  # noqa: F401
    WEAPONS as LOOT_WEAPON_TABLE,
    ARMOR as ARMOR_TABLE,
)
