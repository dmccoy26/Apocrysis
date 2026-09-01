"""World 1 - "The Silence". Content only; no engine imports.

Assembles the World object the engine consumes from the per-aspect
content modules in this package (truth / discovery / hypotheses / lore /
population / terrain / manifest / chapters / finale). Nothing in here
imports from the engine - a World is data the engine reads.

`src/constants.py` still re-exports TERRAIN_SYMBOLS / TERRAIN_LEGEND /
MAP_ARCHETYPES from this module as a Phase-A.0 back-compat shim; they
now originate in terrain.py.
"""
from src.worlds.base import World
from src.worlds.silence import population as _population

# v4 (todo 7db3c4b5): why a place is empty, and what that looks like on
# the way in - one line, said once per building. World-1 flavour; moved
# out of world_mixin in the Phase F prose-leak sweep.
_ABANDONMENT_FLAVOUR = {
    'evacuated': "Chairs pushed back, a meal half-eaten, a door left standing open. People left here fast.",
    'barricaded': "The windows are boarded from the inside. Whoever did it isn't here now.",
    'burned': "The ceiling is black and sagging. Something burned here, a while ago.",
    'looted': "Cupboards open, drawers pulled out and dropped. Someone stripped this place.",
    'occupied_recently': "A camp stove, still-greasy tins, a bedroll. Someone was here more recently than the dust says.",
    'sealed': "The door was nailed shut from the outside. Someone made a decision about this room.",
    'flooded': "Standing water on the floor, a tide line up the wall. It drains and fills with the reservoir.",
    'quiet': "Undisturbed. Dust on every surface, nothing out of place. It was just left.",
}
from src.worlds.silence.chapters import CHAPTERS_DICT
from src.worlds.silence.discovery import DISCOVERY_TEMPLATES
from src.worlds.silence.finale import FINALE
from src.worlds.silence.hypotheses import REGIONAL_HYPOTHESES
from src.worlds.silence.lore import SURVIVOR_LORE, LORE_TRIGGERS
from src.worlds.silence.manifest import MANIFEST
from src.worlds.silence.mechanism_prose import MECHANISM_PROSE
from src.worlds.silence.loot import SILENCE_LOOT
from src.worlds.silence.terrain import (
    TERRAIN_SYMBOLS,          # re-exported for the constants.py shim
    TERRAIN_LEGEND,
    MAP_ARCHETYPES,
    TERRAIN_MOVE_MINUTES,
    IMPASSABLE_TERRAIN,
    TERRAIN_PROSE,
    GENERATOR_TERRAIN_ORDER,
)
from src.worlds.silence.truth import WORLD_FACTS
from src.worlds.base import WorldTerrain


_TERRAIN = WorldTerrain(
    symbols=TERRAIN_SYMBOLS,
    legend=TERRAIN_LEGEND,
    archetypes=MAP_ARCHETYPES,
    move_minutes=TERRAIN_MOVE_MINUTES,
    impassable=IMPASSABLE_TERRAIN,
    generator_terrain_order=GENERATOR_TERRAIN_ORDER,
    prose=TERRAIN_PROSE,
)


SILENCE = World(
    id="silence",
    name="Apocrysis",
    description=(
        "You wake in a valley that has gone quiet. No people. The "
        "infected. Infrastructure half standing. You do not know why, "
        "and nothing here will tell you."
    ),
    terrain_symbols=TERRAIN_SYMBOLS,
    terrain_legend=TERRAIN_LEGEND,
    map_archetypes=MAP_ARCHETYPES,
    prose={
        "place_name_fallback": "THE VALLEY",
        "leave_verb": "leave the valley",
        "region_edge": "edge of the valley",
        "region_noun": "the valley",          # "the way out of {region_noun}"
        "hostile_noun": "the infected",        # round-by-round combat text
        "map_item": ("a weathered survey map of the whole valley",
                     "The lay of the land - roads, buildings, settlements, "
                     "where the hills close in - is all laid out now. It "
                     "won't tell you what's moving out there."),
        "abandonment_flavour": _ABANDONMENT_FLAVOUR,
        # HUD location sub-label: the generator's zone key -> the word
        # the player sees. This vocabulary is The Silence's; a world
        # that wants a location sub-label declares its own (F.11 class -
        # 'downtown' must never surface on a starship).
        "zone_labels": {
            "rural": "rural", "suburban": "suburban",
            "industrial": "industrial", "downtown": "downtown",
            "wilderness": "wilderness",
        },
        # The town / settlement subsystem is player-facing built
        # environment - 'Town Center', 'settlement street', the
        # districts. World-owned (F.11 class). Values here reproduce the
        # pre-refactor strings exactly.
        "places": {
            "settlement_found": "You've found a settlement - it's worth exploring before moving on.",
            "district_line": "You're in the {d} district.",
            "district_words": {"downtown": "downtown", "commercial": "commercial",
                               "residential": "residential"},
            "center_quiet": ("The Town Center looks quiet - too quiet. You should "
                             "search the settlement's buildings and streets before "
                             "assuming it's safe to call this home."),
            "center_info": ("The Town Center. Records, notices, a wall of missing-person "
                            "photos - the most information in one place you've found. "
                            "But no one's here, and this isn't the way out."),
            "center_reached": "reached the Town Center",
            "look_building": "A building. Empty.",
            "look_settlement": "A settlement street. Quiet.",
            "look_open": "Open {t}. Nothing here that matters.",
            "look_terrain_words": {},   # {} -> the raw role name, unchanged
        },
        # World Investigation screen: player-facing name + question per
        # thread. The player never sees the raw thread id.
        "thread_titles": {
            "disappearance": ("THE SILENCE", "Where did the people go?"),
            "dead": ("THE INFECTED", "What are they, and where did they start?"),
            "response": ("THE RESPONSE", "Who ordered it, and why?"),
        },
        # v4 Phase B stopgap ambient flavour clues, surfaced in buildings
        # so the journal/inspect interface has content. WORLD_1_LORE_PASS
        # replaces these with authored per-band lore. (text, journal_line)
        "ambient_clues": (
            ("Someone scratched a tally of days into the doorframe - it stops at 46.",
             "A tally of days scratched by the door stops at 46."),
            ("A child's drawing is taped to the wall: stick figures walking toward mountains.",
             "A child's drawing shows people walking toward the mountains."),
            ("A note on the fridge: 'Gone to the muster point. Back by dark. - R'",
             "A fridge note mentions a 'muster point'."),
            ("The calendar is turned to a month with one date circled hard enough to tear it.",
             "A calendar has a single date circled hard enough to tear the paper."),
            ("Boot prints in the dried mud all lead the same way - out the back, north.",
             "Boot prints here all lead north."),
        ),
    },
    discovery_templates=DISCOVERY_TEMPLATES,
    world_facts=WORLD_FACTS,
    survivor_lore=SURVIVOR_LORE,
    lore_triggers=LORE_TRIGGERS,
    regional_hypotheses=REGIONAL_HYPOTHESES,
    manifest=MANIFEST,
    terrain=_TERRAIN,
    finale=FINALE,
    population=_population,
    chapters=CHAPTERS_DICT,
    mechanism_prose=MECHANISM_PROSE,
    loot=SILENCE_LOOT,
)
