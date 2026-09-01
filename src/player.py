# The survivor's starting attributes and the level-based stat curve.
#
# v3 SPRINT had no class *choice* at game start, but the progression
# was still implemented through a table of 22 "player classes" (an
# obsolete versions-1-4 abstraction): they were power-ranked, split
# into 5 tiers, and the tier representatives' stat differences were the
# blend applied at levels 5/10/15/20.
#
# The class abstraction is gone (see docs/SESSION_HANDOFF.md). The
# progression it happened to implement is preserved exactly, as data:
#   - STARTING_ATTRS   : what every new survivor begins with
#   - per-level growth  : flat +1 str/dex/int/wis, +5 max_health
#     (combat_mixin.level_up())
#   - TIER_BONUS        : the extra bump at each tier threshold
#     (combat_mixin._apply_tier_blend_if_crossed())
#
# The v5 rule: worlds do not select player classes. Worlds define
# circumstances; the player is given a survivor. Meaningful
# per-survivor starting variation (stats? equipment? knowledge?
# injuries?) is a separate, not-yet-made design decision.

# Every new game starts here (was PLAYER_CLASSES["husband"], the old
# tier-0 representative). The starting weapon is the world's
# (src/loot.py's starter_spec), not defined here.
STARTING_ATTRS = {
    "health": 100,
    "hunger": 90,
    "thirst": 90,
    "fatigue": 5,
    "strength": 12,
    "dexterity": 10,
    "intelligence": 10,
    "wisdom": 10,
}

# Levels at which the tier bonus below is applied. Level 1 is the
# starting baseline (no bonus). Kept as the historical list so
# combat_mixin's per-level-call crossing check is unchanged.
TIER_LEVEL_THRESHOLDS = [1, 5, 10, 15, 20]

# The additive stat bump at each tier threshold, on top of the flat
# per-level growth. These are exactly the old
# `tier_representative(n) - tier_representative(n-1)` deltas
# (max(0, ...) applied), lifted out of the deleted PLAYER_CLASSES
# machinery. test_stat_trajectory.py pins the resulting level 1-20
# curve so this stays byte-identical.
TIER_BONUS = {
    5:  {"strength": 0, "dexterity": 3, "intelligence": 4, "wisdom": 1, "max_health": 0},
    10: {"strength": 0, "dexterity": 0, "intelligence": 0, "wisdom": 2, "max_health": 0},
    15: {"strength": 4, "dexterity": 1, "intelligence": 0, "wisdom": 0, "max_health": 10},
    20: {"strength": 2, "dexterity": 5, "intelligence": 4, "wisdom": 2, "max_health": 10},
}
