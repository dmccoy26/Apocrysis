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

# One entry per pre-finale level (index == expeditions_completed; L25
# is the special-cased finale). Integration pass: L22 (index 21) moved
# fact -> encounter to seat ORLA. Counts now: fact 10 / encounter 7 /
# quiet 3 / discovery 3 / traversal 1 = 24.
LEVEL_TYPES = (
    "fact", "quiet", "fact", "fact", "fact",             # 1-5   THE WORKS
    "fact", "encounter", "encounter", "fact", "traversal",  # 6-10  WORKING LEVELS
    "discovery", "quiet", "fact", "fact", "encounter",   # 11-15 DEEP WORKINGS
    "encounter", "fact", "fact", "discovery", "encounter",  # 16-20 SEALED GALLERIES
    "quiet", "encounter", "discovery", "encounter",      # 21-24 THE SEAL
)

# The Phase-6 carrier map (docs/WORLD_3_THE_DEEP.md integration pass).
# Facts a specific authored beat carries - a generated mystery must
# never target one (world_investigation.next_target(exclude=...)).
BEAT_CARRIED_FACTS = frozenset({
    "CHANGED_ARE_CREW",            # auto - first Changed seen (AUTO_FACTS)
    "CHANGED_HAVE_STRUCTURE",      # L7  combat beat
    "CHANGED_BY_DEPTH",            # L8  scene beat
    "WORKERS_CHOSE_ISOLATION",     # L15 DEL (contested) -> L19 adjudicates
    "COMMS_CUT_FROM_BELOW",        # L16 scene beat
    "CONTAINMENT_INFRASTRUCTURE",  # L19 discovery crossing (physical)
    "WORKERS_MAINTAINING_IT",      # L20 MAREK
    "ORE_IS_SOURCE",              # L22 ORLA
    "SURVIVORS_ON_A_CLOCK",        # L22 ORLA
    "RESTART_REOPENS_THE_ROUTE",   # L23 restoration hinge (campaign_state)
    "THE_STANCES",                # L24 the three of them
    "SOMEONE_IS_COMING",          # finale also_establishes (texture)
    "THE_CHOICE",                 # the finale
})

# Plain scene-beat encounter crossings: {level_idx: fact_id}. Not a
# person to weigh (that's contacts.py) and not a fight (combat_beat.py)
# - an authored scene that carries a fact.
BEAT_FACTS = {
    7: "CHANGED_BY_DEPTH",         # L8  - one slumped at a junction, further gone
    15: "COMMS_CUT_FROM_BELOW",    # L16 - the comms junction, cut from the deep side
}

# Facts established by a world event rather than an investigation step.
# {trigger: fact_id}. "first_hostile" -> the first Changed encounter.
AUTO_FACTS = {"first_hostile": "CHANGED_ARE_CREW"}

# The L23 restoration-hinge discovery crossing also carries a physical
# reading (the containment layout) - {level_idx: fact_id}. It lands
# AFTER both contested accounts are heard (DEL L15, MAREK L20), so it
# reads as the site settling the disagreement, and it feeds the L23
# extraction-line check. L19 stays a plain kit-grant discovery.
DISCOVERY_FACTS = {22: "CONTAINMENT_INFRASTRUCTURE"}

# §3.1 kill-test D1: the capability floor. The Band V bore crossing
# (L21, index 20) cannot be taken without sealed breathing gear - the
# air past the last sealed galleries has gone. One declarative
# requirement; `has_waders` is the Deep's breathing gear (world.prose
# ["discoverables"]["waders"]), obtained from the loot pool.
SECTION_KIT = {20: ("has_waders", "sealed breathing gear")}
# ...guaranteed on the L19 discovery crossing (index 18) - "the crew
# left kit" (§5B.10). L19 < L21, so the requirement is always meetable.
DISCOVERY_GRANTS = {18: ("has_waders", "waders")}

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
    section_kit=SECTION_KIT,
    discovery_grants=DISCOVERY_GRANTS,
    beat_carried_facts=BEAT_CARRIED_FACTS,
    beat_facts=BEAT_FACTS,
    auto_facts=AUTO_FACTS,
    discovery_facts=DISCOVERY_FACTS,
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
