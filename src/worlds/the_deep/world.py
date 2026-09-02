"""World 3 - "The Deep". Assembles the World the engine consumes from
the per-aspect content modules in this package. No engine imports.
docs/WORLD_3_THE_DEEP.md §5B.

Kill-test 0 - the world shell. `campaign_state` (kill-test A),
`WorldContact` (kill-test B), the L7 combat experiment (kill-test C) and
the capability-floor kit seam (kill-test D) are NOT in this file yet.
The DAG is carried entirely by escape mechanisms + the finale's
`also_establishes`; the six `encounter` crossings deliver whichever
fact the DAG selects for them, through an authored scene.
"""
from src.worlds.base import World
from src.worlds.the_deep import population as _population
from src.worlds.the_deep.chapters import CHAPTERS_DICT
from src.worlds.the_deep.discovery import DISCOVERY_TEMPLATES
from src.worlds.the_deep.finale import FINALE
from src.worlds.the_deep.hypotheses import REGIONAL_HYPOTHESES
from src.worlds.the_deep.lore import SURVIVOR_LORE, LORE_TRIGGERS
from src.worlds.the_deep.manifest import MANIFEST
from src.worlds.the_deep.mechanism_prose import MECHANISM_PROSE
from src.worlds.the_deep.loot import THE_DEEP_LOOT
from src.worlds.the_deep.terrain import TERRAIN
from src.worlds.the_deep.truth import WORLD_FACTS


THE_DEEP = World(
    id="the_deep",
    name="The Deep",
    description=(
        "The lower crews of a deep mine stopped answering, and the company "
        "wrote the site off. You go back down. The cage runs three levels "
        "and stops; below that the shaft is dark, and something is wrong "
        "with the people who kept working."
    ),
    terrain_symbols=TERRAIN.symbols,
    terrain_legend=TERRAIN.legend,
    map_archetypes=TERRAIN.archetypes,
    prose={
        "place_name_fallback": "THE WORKINGS",
        "leave_verb": "get back up the shaft",
        "region_edge": "solid rock",
        "region_noun": "the site",
        "hostile_noun": "the Changed",       # round-by-round combat text
        # WAKE_SPINE §5.1 - the framing for a scheduled non-fact level: a
        # section crossing with no mystery. (scene line, objective line)
        # per type; "reached" is the finish reason.
        "section_levels": {
            "traversal": (
                "This stretch is a hard push - a run half fallen in, or a "
                "gallery down to the roof in water. No time to read the "
                "ground; just get down through it.",
                "Push on down to the next level."),
            "discovery": (
                "The crew left kit in this stretch when they pulled back - "
                "worth having. Work down through it with your lamp up.",
                "Work down through the level."),
            "encounter": (
                "This stretch still has people in it. Or things that used "
                "to be. Either way you're not going through it quietly.",
                "Get down to the level below."),
            "quiet": (
                "A worked-out stretch. Nothing moving, the air not too bad. "
                "Catch your breath and keep going down.",
                "Cross to the next level."),
            "reached": "reach the level boundary and go on down",
            # KEYED BY THE FACT ID the DAG selects for that crossing (the
            # Wake pattern). DRAFT prose - the wording pass (§5B.11) and
            # kill-tests B/C re-align these to the spec's intent (combat
            # at L7, the DEL / MAREK / stances contacts at L15/L20/L24).
            "encounter_beats": {
                "CHANGED_ARE_CREW": {
                    "marker": "one of them is right in the drift ahead",
                    "lines": (
                        "There's one standing in the middle of the drift, not "
                        "moving, lamp-shadow long behind it.",
                        "Crew coveralls. A check tag still on a string at the "
                        "neck. Boots worn down the same way yours are.",
                        "It comes at you slow, and wrong, and you do what you "
                        "have to. Afterwards you crouch and read the tag. A "
                        "name, a number, a level. This was one of the people "
                        "you came down here for.",
                    ),
                },
                "CHANGED_BY_DEPTH": {
                    "marker": "there's one slumped at the junction",
                    "lines": (
                        "Another one, further down, sat against the rib at a "
                        "junction. It doesn't get up. It doesn't flinch from "
                        "the lamp the way the last one did.",
                        "You go past close enough to see its eyes track "
                        "nothing at all.",
                        "The ones near the top still knew enough to be afraid "
                        "of a light. This one is further gone than that, and "
                        "it's only a hundred metres deeper. The change runs "
                        "with the depth.",
                    ),
                },
                "COMPANY_CORRELATION": {
                    "marker": "the records terminal is still lit",
                    "lines": (
                        "The occupational-health office, off the drift. One "
                        "terminal still has power, a chair pulled up to it.",
                        "Whoever sat here last had the exposure model open - "
                        "not the symptom log, the model. Dose in one column, "
                        "severity out the other, a fitted curve down the "
                        "middle.",
                        "The company didn't just record the sickness. It "
                        "modelled it. Somebody built this curve and kept it "
                        "current.",
                    ),
                },
                "QUOTAS_CONTINUED": {
                    "marker": "the shift office is on the way through",
                    "lines": (
                        "The shift office. Boards on every wall - rotations, "
                        "exposure caps, mask issue, a monitoring roster.",
                        "And next to all of it, untouched, the extraction "
                        "targets. Tonne for tonne, month on month, not one of "
                        "them ever revised down.",
                        "A managed-harm programme running right alongside a "
                        "production plan that never once gave ground to it.",
                    ),
                },
                "COMMS_CUT_FROM_BELOW": {
                    "marker": "someone's at the comms junction ahead",
                    "lines": (
                        "The main comms junction, deep on the level. The "
                        "external line runs through here on its way up the "
                        "shaft.",
                        "It's been cut - a clean break, the ends dressed "
                        "back. The tool marks are on the deep side of the "
                        "cut. Whoever did it was standing where you are, "
                        "facing up.",
                        "The site wasn't cut off from the surface. It cut "
                        "itself off, from down here, so no order could come "
                        "the other way.",
                    ),
                },
                "CASE_TIMING": {
                    "marker": "the dispatch office is on the route",
                    "lines": (
                        "The ore dispatch office. Shipment manifests still "
                        "spiked on the desk, the rotation sheets filed beside "
                        "them.",
                        "You line the outbound dates against the first "
                        "reported cases up the line. They march together - "
                        "shipment, then case; crew rotates out, then case.",
                        "It didn't travel on the wind. It went up the shaft "
                        "with the ore and out the gate with the men.",
                    ),
                },
            },
        },
        "campaign_objective": {
            "revealed_when": "SEAL_FROM_INSIDE",
            "goal": "REACH THE BORE",
            "arrived": "THE SEAL - THE BORE IS HERE",
            "ahead_one": "1 LEVEL DOWN",
            "ahead_many": "{n} LEVELS DOWN",
        },
        "map_item": ("a full survey of the workings",
                     "Every level, drift and gallery is on it now - including "
                     "the ones the working plans leave blank. It won't tell "
                     "you what's moving in them."),
        # F.11-class one-time discoverables. NO `scanner` - the Deep does
        # not gate its markers (markers_need_device=False).
        "discoverables": {
            "flashlight": "You found a working cap lamp! The dark stretches "
                          "are much easier to move through now.",
            "waders": "You found sealed breathing gear! Bad air and flooded "
                      "ground no longer slow you down as much.",
        },
        # The town / settlement subsystem, mine-fictioned: a generated
        # "settlement" is a held circuit / a crew station / the deep
        # muster, not a town. The C/M/Q/S/D glyphs are captioned in the
        # terrain legend; this covers the prose.
        "places": {
            "settlement_found": "You've reached a stretch someone's still holding - search it before you move on.",
            "district_line": "You're in {d}.",
            "district_words": {"downtown": "the deep muster",
                               "commercial": "the machine shop",
                               "residential": "the crew quarters"},
            "center_quiet": ("The deep muster is dark and cold. Check the "
                             "compartments around it before you trust it."),
            "center_info": ("The deep muster. A crew roster with names struck "
                            "through, standing notices, a status board still "
                            "ticking over - the most in one place you've found. "
                            "No one here now, and this isn't the way up."),
            "center_reached": "reached the deep muster",
            "look_building": "A compartment. A door on it, and empty.",
            "look_settlement": "A drift through the held circuit. Quiet.",
            "look_open": "{t}. Nothing here worth stopping for.",
            "look_terrain_words": {
                "forest": "A fall", "water": "A flooded gallery",
                "swamp": "Bad ground", "plain": "Open drift",
                "mountain": "Solid rock", "town": "The held circuit",
                "bridge": "A stull crossing", "building": "A compartment",
            },
        },
        # No day underground - the site runs a shift clock. Same four
        # internal phase roles, mine words.
        "day_cycle": {
            "labels": {"day": "shift on", "night": "shift off",
                       "dawn": "shift change", "dusk": "shift change"},
            "glyphs": {"day": "○", "night": "●", "dawn": "◔", "dusk": "◑"},
        },
        # same keys as the engine's _ABANDONMENT_FLAVOUR (per-tile RNG
        # draw); mine text.
        "abandonment_flavour": {
            'evacuated': "A drift left mid-cut, the machine still parked at the face, crib bags on the floor. This stretch emptied fast.",
            'barricaded': "Timber and spoil stacked across the drift from the far side. Whoever did it isn't here now.",
            'burned': "Scorched timber, the roof bolts sagging. A fire down here, a while back.",
            'looted': "Lockers forced, crib boxes tipped out. Someone went through this fast.",
            'occupied_recently': "A bed roll, ration wrappers, a lamp still faintly warm on the charger. Someone was here not long ago.",
            'sealed': "Welded shut, a seam of slag down the frame. Someone made a decision about this gallery.",
            'flooded': "Water standing on the floor and a tide line up the rib - a pump somewhere still fills and drains this ground.",
            'quiet': "Untouched. Rock dust on every surface. It was just left.",
        },
        "thread_titles": {
            "facility": ("THE FACILITY", "What actually happened down here?"),
            "order": ("THE ORDER", "Who ran this, and what did they decide?"),
            "seam": ("THE SEAM", "What is the ore, and what did working it do?"),
        },
        # ambient flavour surfaced in compartments - the crew, in traces.
        "ambient_clues": (
            ("A shift tally is chalked by a bunk, one stroke a day, stopping partway through a week.",
             "A shift tally by a bunk stops partway through a week."),
            ("Someone has written 'DO NOT OPEN' across a bulkhead in crayon, twice, hard.",
             "'DO NOT OPEN' is written across a bulkhead, twice."),
            ("A child's drawing pinned to a locker: a cage going down a shaft, small stick figures inside it.",
             "A child's drawing shows a cage going down a shaft."),
            ("A medical station sign-in slate, the last dozen entries the same two words: 'not responding.'",
             "A medical slate's last entries all read 'not responding.'"),
            ("A dosimeter left hanging on a nail, its reading pinned hard against the top of the scale.",
             "A dosimeter on a nail reads against the top of the scale."),
            ("A board chalked at a drift mouth: 'still working. day 40-something. leave the door shut.'",
             "A board at a drift mouth: 'still working... leave the door shut.'"),
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
    loot=THE_DEEP_LOOT,
)
