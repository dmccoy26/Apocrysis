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

# One line per expedition tier (0..CAMPAIGN_LENGTH-1). The arc: you
# start just trying to get clear of one valley, and by the end you're
# reading the shape of what happened across a whole region.
_CHAPTERS = [
    "You've been walking for a day. The map ends where the hills close in - and the road you came by is behind you, gone. Find the way out of this one.",
    "Another valley, another dead end. You're starting to notice the pattern in how places fail: the road, the bridge, the water. Something to learn here.",
    "The settlements are bigger now, and emptier. Whatever moved through cleared them methodically. Read the place. Find the seam.",
    "You've done this enough times to trust the method: understand what a place was, and it tells you where it has to give.",
    "Halfway. The country is getting harder to read - more history stacked on more history. Take your time.",
    "You keep finding the same kinds of evidence in different hands. People were trying to tell each other something. Listen.",
    "The maps you find now contradict each other. Someone was lying, or someone was wrong. Work out which.",
    "Fewer survivors passed this way. The routes out are stranger, older - the obvious ones were used up long ago.",
    "Almost through. Every valley has had a way out for someone who understood it. This one does too.",
    "Last one. Whatever this whole region was - and you've seen most of it now - this is where you finally get clear of it.",
]


def chapter_intro(expeditions_completed):
    i = max(0, min(expeditions_completed, len(_CHAPTERS) - 1))
    n = expeditions_completed + 1
    return f"-- Expedition {n} of {CAMPAIGN_LENGTH} --\n{_CHAPTERS[i]}"


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
