"""World 3 - "The Deep": the survivor contacts. docs/WORLD_3_THE_DEEP.md
§5B.7 - kill-test B.

NOT a dialogue system, NOT a generic NPC framework, NOT conversation
trees. This is the smallest data a kill-test of "person as evidence
source" needs:

- two people (DEL, MAREK) who speak to the SAME contested WorldFact -
  *why the deep crews sealed themselves in* - with opposed readings;
- each keyed to a level (the schedule's L15 / L20 encounter crossings),
  so the engine places them without touching next_target();
- MAREK's line varies on whether the player has already heard DEL
  (`gate.after_stance`) - the "player's stance affects what the contact
  reveals" requirement, done with a campaign_state check, not a branch;
- a physical fact (`resolved_by`) that later adjudicates the contested
  fact - testimony is a *claim*, physical evidence is what settles it.

Testimony enters the model as `Evidence.method == "testimony"` and marks
its WorldFact SUSPECTED, never KNOWN - distinct from a solved mystery
(physical, KNOWN). See world_mixin._establish_contact_testimony.
"""

# The one contested fact this kill-test exercises.
CONTESTED_FACT = "WORKERS_CHOSE_ISOLATION"
# The physical fact whose discovery settles it (in MAREK's favour - it
# reads the deep layout as a built, maintained containment).
RESOLVED_BY = "CONTAINMENT_INFRASTRUCTURE"

# level index (== expeditions_completed, 0-based) -> contact.
# index 14 == L15 (DEL, §5B.7), index 19 == L20 (MAREK) - both
# `encounter` crossings on the schedule (manifest.LEVEL_TYPES).
CONTACTS = {
    14: {
        "id": "DEL",
        "who": "a rigger - the one who helped rig your descent",
        "stance": "leave",
        "fact": CONTESTED_FACT,
        "reading": ("self-defence - the seam was killing us and the company "
                    "had the curve and wouldn't stop. We sealed it and pulled "
                    "the line so they couldn't send us back down. Now we should "
                    "be getting people OUT."),
        "lines": (
            "The route through the flooded ground is held open with timber "
            "and a come-along, and there's someone sitting by the winch who "
            "did the work. They know your kit - they rigged half of it.",
            "\"You got down. Good.\" Del doesn't get up. \"I rigged the "
            "descent for the ones who came down to look. None of them rigged "
            "one back up.\"",
            "\"You want to know why the deep crews shut the galleries and "
            "cut the line? I'll tell you straight, because I was one of "
            "them.\"",
            "Del tells it as self-defence: the seam was doing this to "
            "everyone who worked it, the company had modelled exactly what it "
            "did and kept the quotas up, and sealing the deep and pulling the "
            "outside line was the only way to stop being ordered back down.",
            "\"We didn't hide. We stopped. And now there are people on a "
            "dead circuit down there running out of air, and every day we "
            "don't open it is a day we chose that too.\"",
        ),
    },
    19: {
        "id": "MAREK",
        "who": "a shift boss, planted in the doorway of the gallery head",
        "stance": "hold",
        "fact": CONTESTED_FACT,
        "reading": ("containment - we understood what the seam had made, and "
                    "that it doesn't leave. The seal stays shut whatever it "
                    "costs the ones behind it. Us included."),
        "lines": (
            "Someone is standing in the gallery-head doorway, square in it, "
            "a pick handle held low. Not coming at you - not moving aside "
            "either.",
            "\"Far as the door. No further, till you've heard me.\" A shift "
            "boss's coat, the name bar worn off. \"You've been talking to "
            "people on your way down. I know what they told you.\"",
        ),
        "lines_after_del": (
            "\"Del's been talking to you.\" Marek doesn't make it a "
            "question. \"Del wants the doors open and everyone walked out. "
            "Del isn't wrong about why we came down here - the seam, the "
            "company, all of it.\"",
            "\"Del's wrong about what it costs. We didn't just stop working. "
            "We worked out what we'd let up that shaft already, and we built "
            "this to hold the rest of it down. The vents, the doors, the way "
            "the power's split - that's us. That's the job now.\"",
            "\"The seal stays shut. However that reads to you. However it "
            "reads to Del.\"",
        ),
        "gate": {"after_stance": "leave"},   # the pointed version needs DEL heard first
    },
}

CONTACTS_FILE = {
    "contested_fact": CONTESTED_FACT,
    "resolved_by": RESOLVED_BY,
    "by_level": CONTACTS,
    # THE_STANCES lands once the player has heard both sides.
    "stances_fact": "THE_STANCES",
    "stances_needed": ("leave", "hold"),
}
