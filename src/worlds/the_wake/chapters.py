"""World 2 - "The Wake": chapter intros + retrospective framing.
docs/WORLD_2_THE_WAKE.md §5.
"""

CHAPTERS = (
    # CH1 - THE WAKE
    "The pod let you out early. The manifest says you're a systems engineer; it doesn't say why you're the one awake. The ship has stopped, the lights are failing in stretches, and half the reports the computer gives you contradict the other half. Find out what's wrong with it and get it moving.",
    # CH2 - THE CREW
    "There are people alive, holding one section, and there are other things in the dark stretches of corridor. Both are wearing crew uniforms. Work out how many are left - and what the others are.",
    # CH3 - THE ISOLATION
    "The sealed decks weren't damaged shut. They're held by standing commands, and every command carries the same authorization code. Follow it back. Find out whose console issued it, and what the seals were actually for.",
    # CH4 - THE ORDER
    "The nav hold, the comms blackout, every deck seal - one signature on all of them. One officer took this ship apart deliberately, and left a record of why. Read it. Work out what they knew that you're only starting to.",
    # FIN - THE REACTOR
    "Main engineering is ahead, and the reactor with it. You know now what bringing it back does. The survivors up in their section are running out of air. One last walk in, and then a call about what this ship's power is worth.",
)

RETRO_LEAD = "You read the ship out of the dark, one deck at a time:"
RETRO_TAIL = ("and every deck had a way through, for someone who worked out what "
              "had been done to it.")
RETRO_EMPTY = "You made it off. Every deck had a way through; you found each one."

CHAPTERS_DICT = {
    "chapters": CHAPTERS,
    "retro_lead": RETRO_LEAD,
    "retro_tail": RETRO_TAIL,
    "retro_empty": RETRO_EMPTY,
}
