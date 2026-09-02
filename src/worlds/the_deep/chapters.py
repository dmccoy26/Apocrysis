"""World 3 - "The Deep": chapter intros + retrospective framing.
docs/WORLD_3_THE_DEEP.md §5B / §3.9.
"""

CHAPTERS = (
    # CH1 - THE WORKS
    "The lower crews stopped answering weeks ago and the company wrote the site off. You went back down. The cage runs three levels and stops; below that the shaft is dark. Get the works running and find out why the deep levels went quiet.",
    # CH2 - THE WORKING LEVELS
    "Past the seal the workings are still lit in stretches, and there are things moving in them wearing crew coveralls. Some of the people you came for are down here. Work out what happened to them - and how far it has gone.",
    # CH3 - THE DEEP WORKINGS
    "The ore gets richer the deeper you go, and so does the sickness. The medical logs go back years. Cross them against the rosters, follow the paperwork up, and find out what the company knew and when.",
    # CH4 - THE SEALED GALLERIES
    "The galleries below here were welded shut from the inside, the outside line cut hundreds of metres down. This isn't a barricade. Find out who built the thing that holds the deep shut, and who is still down here keeping it that way.",
    # FIN - THE SEAL
    "The bore is ahead and the seam behind it - the place the region's change started. The lucid survivors are on a failing circuit and they don't agree on what to do. One last descent, and then a call about whether the line gets finished.",
)

RETRO_LEAD = "You went down through the workings, one level at a time:"
RETRO_TAIL = ("and every level had a way on down, for someone who worked out "
              "what had been done to it.")
RETRO_EMPTY = "You came back up. Every level had a way through; you found each one."

CHAPTERS_DICT = {
    "chapters": CHAPTERS,
    "retro_lead": RETRO_LEAD,
    "retro_tail": RETRO_TAIL,
    "retro_empty": RETRO_EMPTY,
}
