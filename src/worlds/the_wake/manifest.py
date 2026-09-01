"""World 2 - "The Wake": the manifest. docs/WORLD_2_THE_WAKE.md §5, §12.

Deliberately different from World 1 to exercise the Phase F seam: a
shorter arc, fewer chapters, a smaller mechanism subset.
"""
from src.worlds.base import WorldManifest

# The spine re-paces the campaign to 25 levels (WAKE_SPINE_INVESTIGATION
# .md §5). Chapters stay 5 and their text is unchanged - only re-spaced,
# and aligned so each chapter intro fires on entering a section:
#   CH1 THE WAKE      -> BRIDGE            (exp 0-2)
#   CH2 THE CREW      -> CREW SECTION      (exp 3-6)
#   CH3 THE ISOLATION -> CRYO/MED + HAB    (exp 7-14)
#   CH4 THE ORDER     -> OFFICER/RECORDS   (exp 15-18)
#   CH5 THE REACTOR   -> ENG APPROACH + ENGINEERING + FIN (exp 19-24)
CHAPTER_BOUNDS = (0, 3, 7, 15, 19)
CHAPTER_TITLES = ("THE WAKE", "THE CREW", "THE ISOLATION", "THE ORDER", "THE REACTOR")

# The spatial spine: 7 depth-ordered sections, Bridge -> Main
# Engineering. section_bounds is the owner-locked step function (§0).
# Each section names a terrain archetype from terrain.py's MAP_ARCHETYPES
# (several may share one - the mapping is deliberate, not 1:1).
SECTION_BOUNDS = (0, 3, 7, 11, 15, 19, 22)
SECTION_NAMES = (
    "BRIDGE", "CREW SECTION", "CRYO / MEDICAL", "HABITATION",
    "OFFICER / RECORDS", "ENGINEERING APPROACH", "MAIN ENGINEERING",
)
SECTION_ARCHETYPES = (
    "habitation", "habitation", "damaged", "habitation",
    "damaged", "open_decks", "engineering",
)

# The per-level type schedule (WAKE_SPINE_INVESTIGATION.md §5.2), one
# entry per pre-finale level (index == expeditions_completed; level 25
# is the special-cased finale). "fact" = the ordinary escape-mystery
# level; the rest are section-transit beats (no mystery, cross to the
# far-wall exit). 15 fact / 3 traversal / 2 discovery / 3 encounter /
# 1 quiet = 24. Chapters / hypotheses / finale are unchanged - this is
# pacing, not re-authoring.
# F.9 correction pass (2026-09-01): L4 was a traversal, giving the
# opening "L3 hook -> traversal -> traversal -> payoff". Moved the
# traversal to L7 so L3's hook is answered first: "hook -> payoff ->
# device -> traversal -> contact". L5 stays a discovery (the H1
# device-recovery slot). Endgame unchanged here - L24's fix is that
# `encounter` becomes a real convergence beat (separate change).
LEVEL_TYPES = (
    "fact", "fact", "fact",                       # 1-3   BRIDGE
    "fact", "discovery", "fact", "traversal",      # 4-7   CREW SECTION
    "encounter", "fact", "fact", "fact",           # 8-11  CRYO / MEDICAL
    "quiet", "traversal", "fact", "fact",          # 12-15 HABITATION
    "fact", "encounter", "fact", "fact",           # 16-19 OFFICER / RECORDS
    "fact", "discovery", "fact",                   # 20-22 ENGINEERING APPROACH
    "traversal", "encounter",                      # 23-24 MAIN ENGINEERING
)

MANIFEST = WorldManifest(
    id="the_wake",
    title="The Wake",
    subtitle="You wake alone on a colony ship that has stopped.",
    campaign_length=25,
    # the zombie/encounter curve is engine and frozen; it just reaches
    # full strength sooner relative to this shorter arc.
    difficulty_ramp_length=10,
    chapter_bounds=CHAPTER_BOUNDS,
    chapter_titles=CHAPTER_TITLES,
    section_bounds=SECTION_BOUNDS,
    section_names=SECTION_NAMES,
    section_archetypes=SECTION_ARCHETYPES,
    level_types=LEVEL_TYPES,
    # 8 of the 10 grammars - the ones whose shape fits a ship (§7).
    # boat_crossing and tidal_causeway are dropped (§10.3).
    supported_mechanisms=(
        "power_station", "radio_tower", "service_route", "dam_valves",
        "rail_tunnel", "evac_corridor", "airfield_plane", "mountain_pass",
    ),
    # §F.12: an expedition on the ship is a traverse - you wake against
    # one end bulkhead and the way out is the far one. Not a valley you
    # wander out of the nearest side of.
    map_transit=True,
)
