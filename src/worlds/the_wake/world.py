"""World 2 - "The Wake". Assembles the World the engine consumes from
the per-aspect content modules in this package. No engine imports.
docs/WORLD_2_THE_WAKE.md.
"""
from src.worlds.base import World
from src.worlds.the_wake import population as _population
from src.worlds.the_wake.chapters import CHAPTERS_DICT
from src.worlds.the_wake.discovery import DISCOVERY_TEMPLATES
from src.worlds.the_wake.finale import FINALE
from src.worlds.the_wake.hypotheses import REGIONAL_HYPOTHESES
from src.worlds.the_wake.lore import SURVIVOR_LORE, LORE_TRIGGERS
from src.worlds.the_wake.manifest import MANIFEST
from src.worlds.the_wake.mechanism_prose import MECHANISM_PROSE
from src.worlds.the_wake.loot import THE_WAKE_LOOT
from src.worlds.the_wake.terrain import TERRAIN
from src.worlds.the_wake.truth import WORLD_FACTS


THE_WAKE = World(
    id="the_wake",
    name="The Wake",
    description=(
        "You wake from cryo, alone and out of sequence, aboard a colony "
        "ship that has stopped. You are a systems engineer. The ship is "
        "badly hurt, and something is wrong with the people aboard - and "
        "you do not remember why you're the one awake."
    ),
    terrain_symbols=TERRAIN.symbols,
    terrain_legend=TERRAIN.legend,
    map_archetypes=TERRAIN.archetypes,
    prose={
        "place_name_fallback": "THE SHIP",
        "leave_verb": "get off the ship",
        "region_edge": "outer hull",
        "region_noun": "the ship",
        "hostile_noun": "the changed",       # round-by-round combat text
        # The spatial spine's CAMPAIGN objective line (WAKE_SPINE §5.5):
        # the long-term purpose, shown once the ship's shape is
        # understood (SECTIONS_SEALED, ~level 3) and updated each
        # section. No bearing - "N sections ahead" is honest progress,
        # a compass claim across freshly-generated sections would be a
        # lie. World-owned: a world without this block shows no line.
        # WAKE_SPINE §5.1: the framing for a scheduled non-fact level - a
        # section crossing with no mystery. (scene line, objective line)
        # per type; "reached" is the finish reason. World-owned: a world
        # with no map_transit / level_types never shows any of it.
        "section_levels": {
            "traversal": (
                "This stretch is a hard push - a section open to vacuum, "
                "or torn half off its frame. No time to read the ground; "
                "just get across.",
                "Push through to the next section."),
            "discovery": (
                "There's something worth having in this section - the crew "
                "left kit behind when they pulled back. Cross it with your "
                "eyes open.",
                "Work across the section."),
            "encounter": (
                "This section still has people in it. Or things that used "
                "to be. Either way you're not crossing it quietly.",
                "Get through to the far side."),
            "quiet": (
                "A quieter stretch of the ship. Nothing moving. Catch your "
                "breath and keep going.",
                "Cross to the next section."),
            "reached": "reach the section boundary and cross into the next",
            # F.9 pass 2: an ENCOUNTER crossing delivers its WorldFact
            # through a person / a scene on the walk, not a console.
            # KEYED BY THE FACT ID the DAG selects for that level, so the
            # scene can never assert a different fact than the one it
            # establishes. `lines` play on reaching the beat; the fact
            # (+ its milestone / correction banner) lands on completion.
            # DRAFT PROSE - review pending the 2nd F.9 read.
            "encounter_beats": {
                # L8 - THE_CHANGED: the Changed stop being something you
                # found in the dark and become crew, told by one who
                # lived through the change starting.
                "THE_CHANGED": {
                    "marker": "someone in there is still alive",
                    "lines": (
                        "There's a light on in the compartment ahead - "
                        "steady, not the flicker of a failing panel. Someone "
                        "wired a lamp straight off a cell.",
                        "A woman in a torn duty jacket sits against the far "
                        "bulkhead, a length of pipe across her knees. She "
                        "watches you the whole way in and doesn't get up.",
                        "\"You came from forward.\" Not a question. She looks "
                        "you over again. \"Forward's clear enough to walk. "
                        "God. We'd stopped thinking anyone was.\"",
                        "She talks low and fast while you catch your breath - "
                        "then she tells you what happened to the ones who "
                        "didn't make it this far.",
                        "\"They changed before they died. Not all at once. "
                        "First they stopped knowing us. Then they started "
                        "coming after us.\" Her hand tightens on the pipe. "
                        "\"That's what you've been fighting. That's the "
                        "crew.\"",
                    ),
                },
                # L17 - ONE_AUTHORIZATION: one signature on all of it,
                # one officer, alone. NOT the reasoning (L18) and NOT
                # that it was deliberate containment (L19) - only the
                # single hand behind everything. The dead officer is a
                # witness who got here first, not the one who did it.
                "ONE_AUTHORIZATION": {
                    "marker": "there's someone at the records console",
                    "lines": (
                        "The records office door is wedged half open. The "
                        "screens inside are still lit.",
                        "Someone is in the chair, and has been a long time - "
                        "a section officer's coat, the seat turned to face "
                        "the door. They pulled the seal logs before the end "
                        "and were still looking at them when it came.",
                        "The screen is frozen on what they found: every "
                        "deck-seal command on the ship, the nav hold, the "
                        "comms cut - and one authorization signature under "
                        "all of them. The same hand, every time.",
                        "One person did this. Closed the ship up, section by "
                        "section, alone. This officer worked that out too, "
                        "and stayed in the chair with it.",
                    ),
                },
                # L24 - SURVIVORS_ON_A_CLOCK: nothing explains the clock.
                # The player observes it and does the inference.
                "SURVIVORS_ON_A_CLOCK": {
                    "marker": "the last held section is on the way",
                    "lines": (
                        "The passage opens onto the last held section - "
                        "right up against engineering. Blankets. Water cans. "
                        "A camp stove. People.",
                        "They've been living this for days: the light "
                        "rationed, a hand-crank charger going in the corner, "
                        "the person on it not stopping when you come in.",
                        "Nobody asks who you are. One of them just looks from "
                        "the thermometer on the bulkhead, to the line marked "
                        "on the water tank, to the door to engineering, and "
                        "back to you.",
                        "The temperature is still falling. The water is still "
                        "going down. The reactor is still cold behind that "
                        "door. They don't need to explain it.",
                        "You do the arithmetic they finished days ago.",
                    ),
                },
            },
        },
        "campaign_objective": {
            "revealed_when": "SECTIONS_SEALED",
            "goal": "REACH MAIN ENGINEERING",
            "arrived": "MAIN ENGINEERING - THE REACTOR IS HERE",
            "ahead_one": "1 SECTION AHEAD",
            "ahead_many": "{n} SECTIONS AHEAD",
        },
        "map_item": ("a full deck-plan of the ship",
                     "Every section, passage, and compartment is on it now - "
                     "including the ones the working schematics leave blank. "
                     "It won't tell you what's moving in them."),
        # F.11-class: the one-time discoverables. Engine keeps the
        # mechanic (visibility relief / move-cost relief on the vac +
        # grav-out roles); the ship names its own kit.
        "discoverables": {
            "flashlight": "You found a working hand lamp! The dark stretches "
                          "are much easier to move through now.",
            "waders": "You found a sealed hardsuit! Breaches and grav-out "
                      "sections no longer slow you down as much.",
        },
        # No `zone_labels`: the HUD location sub-label stays blank on The
        # Wake rather than borrowing Silence's valley zone words. The
        # 25-level section system (docs/WAKE_SPINE_INVESTIGATION.md) will
        # fill this slot with the ship-section name.
        #
        # The town / settlement subsystem, ship-fictioned (F.11 class):
        # a generated "settlement" is a held section / the muster point,
        # not a town with streets and a centre. The T/H/R/S/B map glyphs
        # are re-captioned in the terrain legend (Muster/Hab/Run/Store/
        # Bay); this covers the prose. Districts: the enclave is small,
        # so its "downtown/commercial/residential" rings read as core /
        # stores / quarters.
        "places": {
            "settlement_found": "You've reached a section someone's still holding - search it before you move on.",
            "district_line": "You're in {d}.",
            "district_words": {"downtown": "the muster point",
                               "commercial": "the stores",
                               "residential": "the crew quarters"},
            "center_quiet": ("The muster point is dark and cold. Check the "
                             "compartments around it before you trust it."),
            "center_info": ("The muster point. A crew roster with names struck "
                            "through, standing notices, a status log still ticking "
                            "over - the most in one place you've found. No one here "
                            "now, and this isn't the way off."),
            "center_reached": "reached the muster point",
            "look_building": "A compartment. Sealed and empty.",
            "look_settlement": "A passage through the held section. Quiet.",
            "look_open": "{t}. Nothing here worth stopping for.",
            "look_terrain_words": {
                "forest": "Wreckage", "water": "A run open to vacuum",
                "swamp": "A stretch with the gravity gone", "plain": "Open deck",
                "mountain": "Hull plate", "town": "The held section",
                "bridge": "A gangway", "building": "A compartment",
            },
        },
        #
        # The ship has no sky - it keeps a clock and a lighting
        # schedule. Same four internal phase roles, ship words.
        "day_cycle": {
            "labels": {"day": "ship day", "night": "ship night",
                       "dawn": "lights up", "dusk": "lights down"},
            "glyphs": {"day": "○", "night": "●", "dawn": "◔", "dusk": "◑"},
        },
        # same keys as the engine's _ABANDONMENT_FLAVOUR (a per-tile RNG
        # draw); ship text.
        "abandonment_flavour": {
            'evacuated': "Kit half-packed, a hatch left open, a meal going cold on a table. This section emptied in a hurry.",
            'barricaded': "Furniture stacked against the door from the inside. Whoever did it isn't here now.",
            'burned': "Scorched bulkheads, the overhead panels sagging. An electrical fire, a while back.",
            'looted': "Lockers forced, storage bins tipped out. Someone went through this space fast.",
            'occupied_recently': "A camp roll, ration wrappers, a heater still faintly warm. Someone was here not long ago.",
            'sealed': "Welded shut from the outside, a seam of slag down the frame. Someone made a decision about this room.",
            'flooded': "Coolant standing on the deck and a line up the wall - a loop somewhere still fills and drains this space.",
            'quiet': "Untouched. A film of dust on every surface. It was just left.",
        },
        "thread_titles": {
            "ship": ("THE SHIP", "What is actually wrong with it?"),
            "crew": ("THE CREW", "What happened to the people aboard?"),
            "order": ("THE ORDER", "Who took the ship apart, and why?"),
        },
        # ambient flavour surfaced in compartments - the crew, in traces.
        # (line shown, journal line)
        "ambient_clues": (
            ("A shift rota is still pinned by the door, names crossed off one by one down the list.",
             "A shift rota has its names crossed off one by one."),
            ("Someone has written 'DO NOT OPEN' across a bulkhead in grease pencil, twice, hard.",
             "'DO NOT OPEN' is written across a bulkhead, twice."),
            ("A child's drawing taped to a locker: a ship, and a lot of small stick figures inside it, and a few outside.",
             "A child's drawing shows people inside a ship and a few outside."),
            ("A medical bay sign-in slate, the last dozen entries all the same three words: 'not responding. isolate.'",
             "A medical slate's last entries all read 'not responding. isolate.'"),
            ("A recorded message cued up and never sent: a woman's voice, mid-sentence - 'tell them it wasn't the crew's -'",
             "An unsent message breaks off at 'it wasn't the crew's -'."),
            ("A hand-lettered card on a pressure door: 'we're still in here. day 60-something. we can hear you.'",
             "A card on a pressure door: 'we're still in here... we can hear you.'"),
        ),
    },
    discovery_templates=DISCOVERY_TEMPLATES,
    world_facts=WORLD_FACTS,
    survivor_lore=SURVIVOR_LORE,
    lore_triggers=LORE_TRIGGERS,
    regional_hypotheses=REGIONAL_HYPOTHESES,
    manifest=MANIFEST,
    terrain=TERRAIN,
    finale=FINALE,
    population=_population,
    chapters=CHAPTERS_DICT,
    mechanism_prose=MECHANISM_PROSE,
    loot=THE_WAKE_LOOT,
)
