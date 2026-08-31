"""World 1 - "The Silence": the manifest. Content only.

Phase F: the numbers that used to be constants.CAMPAIGN_LENGTH /
DIFFICULTY_RAMP_LENGTH and campaign._CHAPTER_BOUNDS / CHAPTER_TITLES.
"""
from src.worlds.base import WorldManifest

# CH1 exp 0-4, CH2 5-8, CH3 9-13, CH4 14-18, CH5 19-23, FIN 24.
CHAPTER_BOUNDS = (0, 5, 9, 14, 19, 24)
CHAPTER_TITLES = ("THE SILENCE", "THE INFECTED", "THE EVACUATION",
                  "THE RESPONSE", "THE LAST SIGNAL", "THE TRUTH")

MANIFEST = WorldManifest(
    id="silence",
    title="The Silence",
    subtitle="A valley that went quiet. No people. You do not know why.",
    # expeditions_completed value at which the campaign is beaten.
    campaign_length=25,
    # the combat/encounter difficulty ramp reaches full strength here and
    # HOLDS - deliberately not tied to campaign_length so a longer arc
    # doesn't stretch (and soften) the frozen curve.
    difficulty_ramp_length=10,
    chapter_bounds=CHAPTER_BOUNDS,
    chapter_titles=CHAPTER_TITLES,
    # empty = every mechanism in escape.MECHANISMS (World 1's historical
    # behaviour - all 10 are valley-shaped).
    supported_mechanisms=(),
)
