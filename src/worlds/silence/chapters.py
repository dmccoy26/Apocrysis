"""World 1 - "The Silence": the per-chapter intro lines and the
campaign retrospective framing. Content only.

Phase F: moved out of src/campaign.py (which keeps the engine-level
chapter *machinery* - chapter_for_expedition, chapter_intro - and reads
this text off game.world.chapters).
"""

# One framing line per chapter, keyed by chapter index (1..6). The
# expedition loop underneath is unchanged - pure framing. The arc moves
# from "get out of this valley" to "you have read the whole operation,
# and it has a transmitter that still works".
CHAPTERS = (
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
)

# The campaign-victory retrospective (printed at campaign_length). The
# revelation the design asked for is "here is the shape of what you
# understood", not a lore dump.
RETRO_LEAD = "You got clear of the whole region. Looking back, the way out was never the same twice:"
RETRO_TAIL = ("Different every time, and every time it was there for someone who "
              "worked out what the place was. You were that someone.")
RETRO_EMPTY = "You made it through. Every place had a way out; you found each one."

CHAPTERS_DICT = {
    "chapters": CHAPTERS,
    "retro_lead": RETRO_LEAD,
    "retro_tail": RETRO_TAIL,
    "retro_empty": RETRO_EMPTY,
}
