"""World 3 - "The Deep": the manifest. docs/WORLD_3_THE_DEEP.md §5B.1.

Kill-test 0 (the world shell). Five depth bands that are simultaneously
the physical identity AND the act structure (§3.9), so section_bounds
and chapter_bounds coincide - a world choice the seam allows, not an
engine constraint. The belief ladder (hypotheses.py) is the axis that
deliberately does NOT align (§3.9a).
"""
from src.worlds.base import WorldManifest

# The five depth bands ARE the five chapters (§5B.1).
CHAPTER_BOUNDS = (0, 5, 10, 15, 20)
CHAPTER_TITLES = ("THE WORKS", "THE WORKING LEVELS", "THE DEEP WORKINGS",
                  "THE SEALED GALLERIES", "THE SEAL")

SECTION_BOUNDS = (0, 5, 10, 15, 20)
SECTION_NAMES = ("THE WORKS", "WORKING LEVELS", "DEEP WORKINGS",
                 "SEALED GALLERIES", "THE SEAL")
SECTION_ARCHETYPES = ("upper_works", "extraction_face", "deep_workings",
                      "sealed_galleries", "the_bore")

# §5B.3 - one entry per pre-finale level (index == expeditions_completed;
# L25 is the special-cased finale). Mapped from §3.10's Type column onto
# the engine vocabulary. Counts: fact 11 / encounter 6 / quiet 3 /
# discovery 3 / traversal 1 = 24. Heavier on encounter + quiet than The
# Wake, lighter on traversal - people are central in III-V and the
# belief ladder needs decision-recovery rooms; §3.9 V is deliberately
# less combat-dense.
LEVEL_TYPES = (
    "fact", "quiet", "fact", "fact", "fact",             # 1-5   THE WORKS
    "fact", "encounter", "encounter", "fact", "traversal",  # 6-10  WORKING LEVELS
    "discovery", "quiet", "fact", "fact", "encounter",   # 11-15 DEEP WORKINGS
    "encounter", "fact", "fact", "discovery", "encounter",  # 16-20 SEALED GALLERIES
    "quiet", "fact", "discovery", "encounter",           # 21-24 THE SEAL
)

MANIFEST = WorldManifest(
    id="the_deep",
    title="The Deep",
    subtitle="You go back down to a mine the lower crews stopped answering.",
    campaign_length=25,
    difficulty_ramp_length=10,
    chapter_bounds=CHAPTER_BOUNDS,
    chapter_titles=CHAPTER_TITLES,
    section_bounds=SECTION_BOUNDS,
    section_names=SECTION_NAMES,
    section_archetypes=SECTION_ARCHETYPES,
    level_types=LEVEL_TYPES,
    # ⟐ deliberate contrast with The Wake. The Deep's information tension
    # is "records are competing evidence" (§3.10 L12), not "you can't see
    # the map".
    markers_need_device=False,
    # §5B.1 - the mine's eight grammars.
    supported_mechanisms=(
        "service_route", "radio_tower", "power_station", "dam_valves",
        "rail_tunnel", "evac_corridor", "mountain_pass", "airfield_plane",
    ),
    # §F.12 vertical: spawn at the top of the band, the way down at the
    # bottom. Kill-test 0 uses the existing west/east transit; §5B.11
    # flags a top/bottom axis as a Phase-6 wording/param refinement.
    map_transit=True,
)
