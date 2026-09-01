"""World 2 - "The Wake": the manifest. docs/WORLD_2_THE_WAKE.md §5, §12.

Deliberately different from World 1 to exercise the Phase F seam: a
shorter arc, fewer chapters, a smaller mechanism subset.
"""
from src.worlds.base import WorldManifest

# CH1 exp 0-3, CH2 4-8, CH3 9-12, CH4 13-16, FIN 17.
CHAPTER_BOUNDS = (0, 4, 9, 13, 17)
CHAPTER_TITLES = ("THE WAKE", "THE CREW", "THE ISOLATION", "THE ORDER", "THE REACTOR")

MANIFEST = WorldManifest(
    id="the_wake",
    title="The Wake",
    subtitle="You wake alone on a colony ship that has stopped.",
    campaign_length=18,
    # the zombie/encounter curve is engine and frozen; it just reaches
    # full strength sooner relative to this shorter arc.
    difficulty_ramp_length=10,
    chapter_bounds=CHAPTER_BOUNDS,
    chapter_titles=CHAPTER_TITLES,
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
