"""World 1 - "The Silence": the concrete survival lessons this campaign
can teach. Each is legibility, not power - it changes what a mystery
surfaces and when, never a stat. See docs/PHASE_B_SPEC.md.
"""
from src.worlds.base import SurvivorLore

SURVIVOR_LORE = (
    SurvivorLore(
        id="BLUE_SIGNS",
        learned_when="solve an evac_corridor mystery",
        blurb="Protocol Seven marked its evacuation routes with blue signs.",
        effect=(
            "The signed-route site shows on your map from the start of an "
            "expedition - you still have to reach it."
        ),
    ),
    SurvivorLore(
        id="COMMAND_FREQUENCY",
        learned_when="solve a radio_tower mystery",
        blurb="Regional command held one emergency frequency for the valley.",
        effect=(
            "In a radio-tower mystery the transmitter briefing names the "
            "frequency up front, instead of it being a search step."
        ),
    ),
    SurvivorLore(
        id="RESERVOIR_CONTROLS",
        learned_when="solve a dam_valves mystery",
        blurb=(
            "The valley reservoir is governed from the control room, not "
            "the main sluice."
        ),
        effect=(
            "In a dam-valves mystery the control-room evidence identifies "
            "which control governs the reservoir - you still operate it "
            "and revise as normal."
        ),
    ),
)

SURVIVOR_LORE_BY_ID = {lore.id: lore for lore in SURVIVOR_LORE}
