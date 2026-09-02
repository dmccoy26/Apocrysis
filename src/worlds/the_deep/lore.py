"""World 3 - "The Deep": survivor lore. docs/WORLD_3_THE_DEEP.md §5B.

Phase F contract: a world's lore.py opts into the engine's existing
effect ids (their behaviour is engine code keyed to the literal id) - it
does not invent new ones. The Deep reuses all three with rewritten text.
"""
from src.worlds.base import SurvivorLore

SURVIVOR_LORE = (
    SurvivorLore(
        id="BLUE_SIGNS",
        learned_when="solve an evac_corridor mystery",
        blurb="A deputy chalk-marked the escapeways that still hold air.",
        effect=(
            "The marked escapeway shows on your map from the start of an "
            "expedition - you still have to reach it."
        ),
    ),
    SurvivorLore(
        id="COMMAND_FREQUENCY",
        learned_when="solve a radio_tower mystery",
        blurb="The control room kept one loop live for the deputies underground.",
        effect=(
            "In a routing-system mystery the shift briefing names the loop up "
            "front, instead of it being a search step."
        ),
    ),
    SurvivorLore(
        id="RESERVOIR_CONTROLS",
        learned_when="solve a dam_valves mystery",
        blurb=(
            "The level overrides are wired by circuit, not by the labels on "
            "the switches."
        ),
        effect=(
            "In a level-override mystery the control-cabin notes identify "
            "which switch lifts this level's seal - you still throw it and "
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
