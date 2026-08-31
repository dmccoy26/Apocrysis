# ============================================================
# Apocrysis - campaign framing (v4 Phase E / Stage 5)
# File: src/campaign.py
#
# The campaign as chapters (todo 55df661d): a short line at the start
# of each expedition, keyed to expeditions_completed, plus the
# campaign-victory retrospective (todo 20c9c192). No mechanics - pure
# framing over the same expedition loop.
#
# Phase F: this file keeps the engine-level chapter *machinery*
# (chapter_for_expedition, chapter_intro) and reads the per-chapter
# text, bounds, titles and endings off a World. Every function takes an
# optional `world`; when omitted it falls back to the default world so
# legacy call sites and the test suite keep working.
# ============================================================

from src.worlds import get_world


def _w(world):
    return world if world is not None else get_world()


def _bounds(world=None):
    return _w(world).manifest.chapter_bounds


def _chapters(world=None):
    return _w(world).chapters.get("chapters", ())


def _campaign_length(world=None):
    return _w(world).manifest.campaign_length


# --- back-compat module names (default world) ----------------------
_CHAPTER_BOUNDS = get_world().manifest.chapter_bounds
CHAPTER_TITLES = get_world().manifest.chapter_titles
_CHAPTERS = get_world().chapters.get("chapters", ())


def chapter_for_expedition(expeditions_completed, world=None):
    """1-based chapter index for a given expedition depth."""
    bounds = _bounds(world)
    i = 1
    for lo in bounds:
        if expeditions_completed >= lo:
            i = bounds.index(lo) + 1
    return i


def chapter_intro(expeditions_completed, milestones_known=0, world=None):
    """The short line at the start of an expedition. Keyed to the chapter
    the depth falls in, but the investigation can run ahead of the raw
    count (replaying early maps after deaths) - so a survivor who has
    surfaced more milestones than their depth implies is shown the
    chapter their understanding has reached, never one behind it."""
    chapters = _chapters(world)
    by_depth = chapter_for_expedition(expeditions_completed, world)
    # ~1 milestone per chapter of progress; let it pull the framing
    # forward but never past the finale.
    by_investigation = 1 + max(0, milestones_known - 1)
    ch = min(len(chapters), max(by_depth, by_investigation))
    n = expeditions_completed + 1
    return f"-- Expedition {n} of {_campaign_length(world)} --\n{chapters[ch - 1]}"


def campaign_ending(choice, used_mechanisms, world=None):
    """The finale screen for a chosen ending, then the ordinary
    what-you-did retrospective underneath."""
    endings = _w(world).finale.endings
    lead, body = endings.get(choice) or next(iter(endings.values()))
    parts = [lead, "", body, "", "--", "",
             campaign_retrospective(used_mechanisms, world)]
    return "\n".join(parts)


def campaign_retrospective(used_mechanisms, world=None):
    """Printed at campaign_length: what the player actually did, read
    back to them. The revelation the design asked for is 'here is the
    shape of what you understood', not a lore dump."""
    ch = _w(world).chapters
    if not used_mechanisms:
        return ch.get("retro_empty",
                      "You made it through. Every place had a way out; "
                      "you found each one.")
    from src.escape import MECHANISMS
    lines = [ch.get("retro_lead", "Looking back, the way out was never the same twice:")]
    for mech in used_mechanisms:
        name = MECHANISMS.get(mech, {}).get("name", mech)
        lines.append(f"  - {name}")
    lines.append(ch.get("retro_tail",
                        "Different every time, and every time it was there "
                        "for someone who worked out what the place was."))
    return "\n".join(lines)
