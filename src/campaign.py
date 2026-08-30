# ============================================================
# Apocrysis - campaign framing (v4 Phase E / Stage 5)
# File: src/campaign.py
#
# The campaign as chapters (todo 55df661d): a short line at the start
# of each expedition, keyed to expeditions_completed, plus the
# campaign-victory retrospective (todo 20c9c192). No mechanics - pure
# framing over the same expedition loop.
# ============================================================

from src.constants import CAMPAIGN_LENGTH

# The World-1 arc as 5 chapters + a finale ("The Cordon" -
# docs/WORLD_TRUTH_CANDIDATES.md). One framing line per chapter; the
# expedition loop underneath is unchanged. The arc moves from "get out
# of this valley" to "you have read the whole operation, and it has a
# transmitter that still works".
_CHAPTERS = [
    # CH1 - THE SILENCE
    "You've been walking for a day. The map ends where the hills close in, and the road you came by is gone behind you. No people. Find the way out of this one, and start reading why it's empty.",
    # CH2 - THE INFECTED
    "The settlements are bigger now, and the infected wear the valley's own clothes. This was a place that emptied on purpose - and something was loose here before it did. Find the seam. Find where it started.",
    # CH3 - THE EVACUATION
    "You've seen enough marshalling yards now to know the shape of it: signed corridors, supply caches, a whole region walked out along a handful of roads. Follow one. See where it was meant to lead - and where the manifests stop.",
    # CH4 - THE RESPONSE
    "The corridors closed on a date, not in a panic. Somebody set that date. Every record you pull now has a signature on it; you're starting to recognise the hand. Work out who ran this, and when they decided how it ended.",
    # CH5 - THE LAST SIGNAL
    "The cordon frequency is still live - someone outside has been listening the whole time. And something inside the valley is still transmitting back. Find it. Find out whether anyone is still here to answer.",
    # FIN - THE TRUTH
    "The regional command centre is ahead, and its transmitter still reaches past the cordon. You know what the order said now. There are people who held the line, still waiting. One last walk in - and then a choice about what leaves this valley with you.",
]

# Lowest `expeditions_completed` (0-indexed) at which each chapter
# begins. CH1 exp 0-4, CH2 5-8, CH3 9-13, CH4 14-18, CH5 19-23, FIN 24.
_CHAPTER_BOUNDS = (0, 5, 9, 14, 19, 24)
CHAPTER_TITLES = ("THE SILENCE", "THE INFECTED", "THE EVACUATION",
                  "THE RESPONSE", "THE LAST SIGNAL", "THE TRUTH")


def chapter_for_expedition(expeditions_completed):
    """1-based chapter index (1..6) for a given expedition depth."""
    i = 1
    for lo in _CHAPTER_BOUNDS:
        if expeditions_completed >= lo:
            i = _CHAPTER_BOUNDS.index(lo) + 1
    return i


def chapter_intro(expeditions_completed, milestones_known=0):
    """The short line at the start of an expedition. Keyed to the chapter
    the depth falls in, but the investigation can run ahead of the raw
    count (replaying early maps after deaths) - so a survivor who has
    surfaced more milestones than their depth implies is shown the
    chapter their understanding has reached, never one behind it."""
    by_depth = chapter_for_expedition(expeditions_completed)
    # ~1 milestone per chapter of progress; let it pull the framing
    # forward but never past the finale.
    by_investigation = 1 + max(0, milestones_known - 1)
    ch = min(len(_CHAPTERS), max(by_depth, by_investigation))
    n = expeditions_completed + 1
    return f"-- Expedition {n} of {CAMPAIGN_LENGTH} --\n{_CHAPTERS[ch - 1]}"


def campaign_retrospective(used_mechanisms):
    """Printed at CAMPAIGN_LENGTH: what the player actually did, read
    back to them. The revelation the design asked for is 'here is the
    shape of what you understood', not a lore dump."""
    if not used_mechanisms:
        return "You made it through. Every place had a way out; you found each one."
    from src.escape import MECHANISMS
    lines = ["You got clear of the whole region. Looking back, the way out was never the same twice:"]
    for mech in used_mechanisms:
        name = MECHANISMS.get(mech, {}).get("name", mech)
        lines.append(f"  - {name}")
    lines.append(
        "Different every time, and every time it was there for someone who "
        "worked out what the place was. You were that someone."
    )
    return "\n".join(lines)
