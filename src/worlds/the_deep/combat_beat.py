"""World 3 - "The Deep": the L7 stationed-pair combat beat.
docs/WORLD_3_THE_DEEP.md §5B.3 - kill-test C.

The authored dramatic beat, and the ONLY thing this kill-test builds:

    I saw one thing. I committed. The situation got worse. I still had
    a way out.

Not a multi-enemy combat system. The floor (§4.4): one visible hostile
-> engage -> a second arrives -> retreat is still a real choice. It
runs on the EXISTING `encounter_zombie` - two placed hostiles and an
authored line between them - plus the smallest hook that sequences the
second and lets breaking contact count as a legitimate success (§3.3
C: walking away from a stationed guard is not a failure).

Witnessing the pair work you from two sides IS the evidence for
`CHANGED_HAVE_STRUCTURE` ("they're stationed") - the fact lands whether
you finish the fight or break for the way through.
"""

# The two hostiles are AUTHORED, not rolled. Kill-test C found the
# floor (place + fight the difficulty roll) could not carry the beat:
# the roll can give a skittish infected (flees - no "I committed"), a
# passive one (no fight at all), a fast one (retreat becomes a forced
# fight - no "way out"), or a full-strength / elite one (a fresh-kit
# L7 survivor just dies - "I couldn't have won", not "I shouldn't have
# taken it"). So the pair is declared here: `Fresh` class (speed
# "normal"), stats tuned so a starter-kit survivor wins BOTH while
# clearly hurt, and either one alone is cheap - the cost is in taking
# the second. `flags` cleared - they hold ground, they do not flee.
_STATIONED = {"cls": "Fresh", "health": 24, "attack": 6, "flags": ()}

COMBAT_BEAT = {
    "level": 6,                       # index == expeditions_completed; L7
    "fact": "CHANGED_HAVE_STRUCTURE",
    "z1": {**_STATIONED,
           "label": "ONE OF THE CHANGED - HOLDING THE DOORWAY",
           "line": "Crew coveralls, a lamp bracket still clipped to the "
                   "belt. It sets its feet and waits for you to come to it."},
    "z2": {**_STATIONED,
           "label": "A SECOND - OFF YOUR FLANK",
           "line": "It came from the side gallery, not the dark. It was "
                   "where it was meant to be."},
    "first_line": (
        "One of them is in the drift ahead, planted in the doorway of "
        "the gallery head. Not wandering - set there, facing the way you're "
        "coming. It doesn't move until you're close."
    ),
    "flank_line": (
        "You're still catching your breath when the second one comes - "
        "out of the side gallery, fast, onto the flank the first one had "
        "you turned away from. They worked you from two sides. This wasn't "
        "chance; it was a position, held. You're hurt now, and the way "
        "through is closer to you than this one is."
    ),
    "pushed_line": (
        "You put the second one down too, and stand there breathing hard "
        "in the quiet. That was a bad fight to take. You knew the first "
        "one was there. You did not know it was not alone - and now you do."
    ),
    "retreat_line": (
        "You break contact and go for the gap, and it doesn't chase far - "
        "it holds the ground instead, back to back with where the first "
        "one fell. That's the whole of it: they don't hunt. They hold."
    ),
}
