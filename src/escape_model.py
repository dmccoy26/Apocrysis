"""The escape model — the single source of truth for P(escape).

docs/DESIGN_ESCAPE_MODEL.md. Both the flee roll (`combat_mixin`) and
the encounter card's escape % (`combat_forecast.escape_pct`) call this
function. Never two formulas.

Two separated quantities (the intrinsic / contextual split):

  intrinsic P(escape)  = "can I outrun this thing" — zombie speed class
                         (dominant), player Dexterity / fatigue / HP
  terrain availability = "is there anywhere to run" — open ground vs a
                         confined building
  resolved P(escape)   = intrinsic × availability  (what the flee roll
                         and the card use)

The candidate model here is the one proven in `tools/escape_model.py`
against the R1–R6 fixtures + monotonicity + bounded influence + the
empirical trust check. Changing a coefficient here means re-running
that harness.
"""

# Dominant factor: zombie speed class. Survivor state is secondary and
# capped (bounded influence, §4b) so it can never flip the fundamental
# fast/slow relationship except in a genuinely extreme state.
SPEED_BASE = {"slow": 0.88, "normal": 0.55, "fast": 0.24}

_DEX_PER_POINT = 0.012
_DEX_CAP = 0.12

_INTRINSIC_FLOOR, _INTRINSIC_CEIL = 0.05, 0.97
_RESOLVED_FLOOR, _RESOLVED_CEIL = 0.02, 0.97

# "can I outrun it" is intrinsic; "is there room to run" is contextual.
TERRAIN_AVAILABILITY = {"open": 1.00, "reduced": 0.60, "confined": 0.22}

_TERRAIN_CLASS = {
    "plain": "open", "road": "open",
    "forest": "reduced", "town": "reduced", "swamp": "reduced", "water": "reduced",
    "building": "confined",
    # impassable terrain never actually hosts an encounter, but keep a
    # sane default rather than KeyError
    "mountain": "open", "river": "open",
}


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


def _fatigue_mod(fatigue):
    if fatigue > 80:
        return -0.15
    if fatigue > 50:
        return -0.08
    return 0.0


def _hp_mod(hp_frac):
    if hp_frac < 0.25:
        return -0.15
    if hp_frac < 0.50:
        return -0.08
    return 0.0


def terrain_availability(terrain):
    """Availability multiplier for a terrain name or availability class."""
    if terrain in TERRAIN_AVAILABILITY:
        return TERRAIN_AVAILABILITY[terrain]
    return TERRAIN_AVAILABILITY[_TERRAIN_CLASS.get(terrain, "reduced")]


def intrinsic_escape(speed_class, dexterity, fatigue, hp_frac):
    base = SPEED_BASE[speed_class]
    dex = _clamp((dexterity - 10) * _DEX_PER_POINT, -_DEX_CAP, _DEX_CAP)
    return _clamp(base + dex + _fatigue_mod(fatigue) + _hp_mod(hp_frac),
                  _INTRINSIC_FLOOR, _INTRINSIC_CEIL)


def escape_chance(speed_class, dexterity, fatigue, hp_frac, terrain):
    """Resolved P(escape) — the number the flee roll compares against
    and the encounter card displays."""
    intr = intrinsic_escape(speed_class, dexterity, fatigue, hp_frac)
    return _clamp(intr * terrain_availability(terrain),
                  _RESOLVED_FLOOR, _RESOLVED_CEIL)


def escape_breakdown(speed_class, dexterity, fatigue, hp_frac, terrain):
    """intrinsic / availability / resolved, kept separate so the UI can
    say both "this thing is slow" and "you can't run here"."""
    intr = intrinsic_escape(speed_class, dexterity, fatigue, hp_frac)
    avail = terrain_availability(terrain)
    return {
        "intrinsic": intr,
        "availability": avail,
        "resolved": _clamp(intr * avail, _RESOLVED_FLOOR, _RESOLVED_CEIL),
    }


def escape_chance_for(player, zombie, terrain):
    """Convenience: pull the inputs off the live game objects."""
    from src.zombies import speed_class_of
    hp_frac = player.health / max(1, player.max_health)
    return escape_chance(speed_class_of(zombie), player.dexterity,
                         player.fatigue, hp_frac, terrain)
