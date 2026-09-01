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
