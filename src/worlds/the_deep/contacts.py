"""World 3 - "The Deep": the survivor contacts. docs/WORLD_3_THE_DEEP.md
§5B.7 + the Phase-6 integration pass.

NOT a dialogue system, NOT a generic NPC framework. Kill-test B proved
only a small surface is needed: a person keyed to a level whose
account enters the model as *testimony* (SUSPECTED + attributed +
a stance), plus - added in integration - an optional `establishes`
tuple for facts the person confirms directly (KNOWN), so different
evidence modalities interact.

The roster (§5B.7), keyed by level index (== expeditions_completed):
  KESH   - III, ecology texture only (a Changed present without a
           fight); pure prose on the L11 discovery crossing (world.py).
  DEL    - L15, "leave". Contests WORKERS_CHOSE_ISOLATION - self-defence.
  MAREK  - L20, "hold". Contests it the other way - containment; and
           confirms WORKERS_MAINTAINING_IT directly (he is one of them).
  ORLA   - L22, "choose". Did the maths: establishes ORE_IS_SOURCE and
           SURVIVORS_ON_A_CLOCK (the enclave). No contested claim.
  the three - L24. THE_STANCES: they are all here, and they do not
              agree. The choice is being handed to you.

The contested fact stays SUSPECTED on testimony alone; the L19
discovery crossing (CONTAINMENT_INFRASTRUCTURE, physical) is what
adjudicates it - world_mixin._deep_resolve_contested.
"""

CONTESTED_FACT = "WORKERS_CHOSE_ISOLATION"
RESOLVED_BY = "CONTAINMENT_INFRASTRUCTURE"

CONTACTS = {
    14: {                                            # L15 - DEL
        "id": "DEL",
        "who": "a rigger - the one who helped rig your descent",
        "stance": "leave",
        "fact": CONTESTED_FACT,
        "reading": ("self-defence - the seam was killing us and the company "
                    "had the curve and wouldn't stop. We sealed it and pulled "
                    "the line so they couldn't send us back down. Now we "
                    "should be getting people OUT."),
        "lines": (
            "The route through the flooded ground is held open with timber "
            "and a come-along, and there's someone sitting by the winch who "
            "did the work. They know your kit - they rigged half of it.",
            "\"You got down. Good.\" Del doesn't get up. \"I rigged the "
            "descent for the ones who came down to look. None of them rigged "
            "one back up.\"",
            "\"You want to know why the deep crews shut the galleries and "
            "cut the line? I was one of them. I'll tell you straight.\"",
            "Del tells it as self-defence: the seam was doing this to "
            "everyone who worked it, the company had modelled exactly what it "
            "did and kept the quotas up, and sealing the deep was the only "
            "way to stop being ordered back down.",
            "\"We didn't hide. We stopped. And now there are people on a "
            "dead circuit down there running out of air, and every day we "
            "don't open it is a day we chose that too.\"",
        ),
    },
    19: {                                            # L20 - MAREK
        "id": "MAREK",
        "who": "a shift boss, planted in the doorway of the gallery head",
        "stance": "hold",
        "fact": CONTESTED_FACT,
        "reading": ("containment - we understood what the seam had made, and "
                    "that it doesn't leave. The seal stays shut whatever it "
                    "costs the ones behind it. Us included."),
        "establishes": ("WORKERS_MAINTAINING_IT",),
        "lines": (
            "Someone is standing in the gallery-head doorway, square in it, "
            "a pick handle held low. Not coming at you - not moving aside "
            "either.",
            "\"Far as the door. No further, till you've heard me.\" A shift "
            "boss's coat, the name bar worn off.",
        ),
        "lines_after_del": (
            "\"Del's been talking to you.\" Marek doesn't make it a "
            "question. \"Del wants the doors open and everyone walked out. "
            "Del isn't wrong about why we came down here.\"",
            "\"Del's wrong about what it costs. We didn't just stop working. "
            "We worked out what we'd let up that shaft already, and we built "
            "this to hold the rest of it down. The vents, the doors, the way "
            "the power's split - that's us. Still us. That's the job now.\"",
            "\"The seal stays shut. However that reads to you. However it "
            "reads to Del.\"",
        ),
        "gate": {"after_stance": "leave"},
    },
    21: {                                            # L22 - ORLA
        "id": "ORLA",
        "who": "a deep-crew engineer, early-stage and turning, at a bench "
               "of records on a circuit that still has power",
        "stance": "choose",
        "establishes": ("ORE_IS_SOURCE", "SURVIVORS_ON_A_CLOCK"),
        "lines": (
            "The last held circuit. A camp stove, water cans against one "
            "wall with a line drawn on each, a hand-crank charger someone "
            "keeps turning. And a bench, covered in paper.",
            "The engineer at the bench doesn't look up straight away. When "
            "she does, one eye tracks a beat slow. \"I did the maths. "
            "Somebody had to.\"",
            "She walks you through it: the exposure records, the shipment "
            "manifests, the first cases reported up the line - all of it "
            "lines up. This seam is where the region's change began, and it "
            "went up the shaft with the ore and out the gate with the "
            "crews.",
            "\"And us.\" She nods at the water cans, the stove, the "
            "charger. \"Air, water, power - all of it's counted now. We're "
            "not holding much longer without the site's own systems back.\"",
        ),
    },
    23: {                                            # L24 - the three
        "id": "THE_SEAL_HOLDERS",
        "who": "Del, Marek and Orla, in the same room for the first time",
        "stance": "choose",
        "establishes": ("THE_STANCES",),
        "lines": (
            "They're all here - Del by the door, Marek across the room, "
            "Orla at the bench between them. They've clearly been at this a "
            "while before you walked in.",
            "Del wants the line finished and everyone walked out. Marek "
            "wants the bore brought down and the seal made permanent, "
            "whatever it costs the people on the wrong side of it. Orla "
            "says she can't be the one to call it any more.",
            "\"You've been down the whole shaft,\" Orla says. \"You've seen "
            "all of it. The systems are almost back. So it's a real choice "
            "now, and it isn't ours.\" Nobody in the room disagrees with "
            "her about that.",
        ),
    },
}

CONTACTS_FILE = {
    "contested_fact": CONTESTED_FACT,
    "resolved_by": RESOLVED_BY,
    "by_level": CONTACTS,
}
