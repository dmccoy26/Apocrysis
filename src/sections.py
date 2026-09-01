# ============================================================
# Apocrysis - the spatial spine (WAKE_SPINE_INVESTIGATION.md §5)
#
# Sections are a world's *spatial* progression - an ordered walk from
# one end of the place to the other (The Wake: Bridge -> Main
# Engineering, strictly monotone, no backtracking). They are a separate
# axis from chapters (the narrative arc in chapters.py / hypotheses.py):
# a section supplies context (HUD label, terrain archetype, "N sections
# ahead"), a chapter supplies story.
#
# A world with no section_bounds (The Silence) has no spine - every
# function here returns None / a no-op, and nothing downstream changes.
# ============================================================

from src.worlds import get_world


def _manifest(world):
    return (world if world is not None else get_world()).manifest


def has_spine(world):
    return bool(getattr(_manifest(world), "section_bounds", ()))


def section_index_for(expeditions_completed, world=None):
    """0-based section index for a given expedition depth, or None if
    the world has no spine."""
    bounds = getattr(_manifest(world), "section_bounds", ())
    if not bounds:
        return None
    idx = 0
    for i, lo in enumerate(bounds):
        if expeditions_completed >= lo:
            idx = i
    return idx


def section_count(world=None):
    return len(getattr(_manifest(world), "section_bounds", ()))


def section_name_for(expeditions_completed, world=None):
    """The HUD label for the section this depth falls in, or None."""
    i = section_index_for(expeditions_completed, world)
    if i is None:
        return None
    names = getattr(_manifest(world), "section_names", ())
    return names[i] if i < len(names) else None


def section_archetype_for(expeditions_completed, world=None):
    """The terrain archetype this section renders as, or None (the
    generator then keeps its RNG roll)."""
    i = section_index_for(expeditions_completed, world)
    if i is None:
        return None
    arch = getattr(_manifest(world), "section_archetypes", ())
    return arch[i] if i < len(arch) else None


_FACT_TYPES = ("", "fact")
# The types that are TRUE no-mystery section crossings. "encounter" is
# NOT here: an encounter level still carries a WorldFact (it's a
# next_target() level with survivor-contact framing) - the DAG needs
# those slots. WAKE_SPINE_INVESTIGATION.md §5.1/§5.2.
_SECTION_LEVEL_TYPES = ("traversal", "discovery", "quiet")


def level_type_for(expeditions_completed, world=None):
    """The scheduled TYPE of a given level - 'fact' (the ordinary
    escape-mystery level) unless the world's `level_types` says
    otherwise. WAKE_SPINE_INVESTIGATION.md §5.1."""
    lts = getattr(_manifest(world), "level_types", ())
    if not lts or not (0 <= expeditions_completed < len(lts)):
        return "fact"
    return lts[expeditions_completed] or "fact"


def is_section_transit_level(expeditions_completed, world=None):
    """True when this level is a scheduled plain crossing - no mystery,
    no fact, just push through to the far-wall exit. Only meaningful for
    a map_transit world. `encounter` is NOT one of these (see
    is_encounter_level)."""
    if level_type_for(expeditions_completed, world) not in _SECTION_LEVEL_TYPES:
        return False
    return bool(getattr(_manifest(world), "map_transit", False))


def is_encounter_level(expeditions_completed, world=None):
    """True when this level is a scheduled ENCOUNTER beat - a section
    crossing (no mystery, cross to the exit) that ALSO carries its
    DAG-selected WorldFact, delivered through an authored person / scene
    on the critical path rather than a console. WAKE_SPINE_INVESTIGATION
    .md §5 / F.9 correction pass 2. map_transit worlds only."""
    if level_type_for(expeditions_completed, world) != "encounter":
        return False
    return bool(getattr(_manifest(world), "map_transit", False))


def crosses_section(expeditions_completed, world=None):
    """Either kind of crossing (plain OR encounter) - the map is a
    traverse to the far-wall exit, not a mystery."""
    return (is_section_transit_level(expeditions_completed, world)
            or is_encounter_level(expeditions_completed, world))


def campaign_objective_line(player):
    """The CAMPAIGN HUD line (WAKE_SPINE_INVESTIGATION.md §5.5) - the
    long-term purpose: 'REACH MAIN ENGINEERING - 4 SECTIONS AHEAD'.

    Returns None unless the world declares a `campaign_objective` prose
    block AND its `revealed_when` milestone is known (so the objective
    appears the run after the player learns the ship's shape, ~level 3).
    No bearing by design.
    """
    world = getattr(player, "world", None)
    if world is None or not has_spine(world):
        return None
    obj = (getattr(world, "prose", None) or {}).get("campaign_objective")
    if not obj:
        return None
    gate = obj.get("revealed_when")
    wi = getattr(player, "world_investigation", None)
    if gate and not (wi is not None and wi.is_known(gate)):
        return None
    ahead = sections_ahead(getattr(player, "expeditions_completed", 0), world)
    if ahead is None:
        return None
    if ahead <= 0:
        return obj.get("arrived") or obj.get("goal")
    tail = (obj.get("ahead_one") if ahead == 1
            else obj.get("ahead_many", "{n} SECTIONS AHEAD").format(n=ahead))
    return f"{obj.get('goal', 'REACH THE END')} · {tail}"


def sections_ahead(expeditions_completed, world=None):
    """How many section boundaries still lie between here and the last
    section - honest progress, no bearing. 0 = in the final section."""
    i = section_index_for(expeditions_completed, world)
    if i is None:
        return None
    return max(0, section_count(world) - 1 - i)
