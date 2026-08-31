"""World 2 - "The Wake": survivor lore. docs/WORLD_2_THE_WAKE.md §7.

Phase F contract: a world's lore.py opts into the engine's existing
effect ids (their behaviour is engine code keyed to the literal id) -
it does not invent new ones. The Wake reuses all three with rewritten
text.
"""
from src.worlds.base import SurvivorLore

SURVIVOR_LORE = (
    SurvivorLore(
        id="BLUE_SIGNS",
        learned_when="solve an evac_corridor mystery",
        blurb="Bwinh from maintenance chalk-marked the routes that still hold air.",
        effect=(
            "The marked evacuation route shows on your map from the start of "
            "an expedition - you still have to reach it."
        ),
    ),
    SurvivorLore(
        id="COMMAND_FREQUENCY",
        learned_when="solve a radio_tower mystery",
        blurb="The bridge kept one internal channel live for damage control.",
        effect=(
            "In a routing-system mystery the damage-control briefing names the "
            "channel up front, instead of it being a search step."
        ),
    ),
    SurvivorLore(
        id="RESERVOIR_CONTROLS",
        learned_when="solve a dam_valves mystery",
        blurb=(
            "The section overrides are wired by deck, not by the labels on "
            "the switches."
        ),
        effect=(
            "In a section-override mystery the control-room notes identify "
            "which switch lifts this deck's seal - you still throw it and "
            "revise as normal."
        ),
    ),
)

SURVIVOR_LORE_BY_ID = {lore.id: lore for lore in SURVIVOR_LORE}

LORE_TRIGGERS = {
    "evac_corridor": "BLUE_SIGNS",
    "radio_tower": "COMMAND_FREQUENCY",
    "dam_valves": "RESERVOIR_CONTROLS",
}
