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
