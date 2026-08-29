"""World 1 - "The Silence": which escape mechanism can carry which
authored WorldFact (docs/PHASE_A2_DISCOVERY.md).

A DiscoveryTemplate is a routing entry: solving that mechanism's escape
mystery is a plausible way this survivor would come to that conclusion.
It is NOT the mystery's answer - the player still solves the mystery by
its own evidence. >=1 route per CH1/CH2 fact.
"""
from src.worlds.base import DiscoveryTemplate

# Facts that land consecutively in DAG order and would otherwise repeat
# a story family get a 2nd route of a different family, so A.4.2's
# variety-aware picker has something to choose (see PHASE_A4_SURFACE.md).
DISCOVERY_TEMPLATES = {
    "DIS_FEW_REMAINS": (
        DiscoveryTemplate("DIS_FEW_REMAINS", "mountain_pass"),
    ),
    "DIS_MOVED_TOGETHER": (
        DiscoveryTemplate("DIS_MOVED_TOGETHER", "rail_tunnel"),
        DiscoveryTemplate("DIS_MOVED_TOGETHER", "boat_crossing"),
    ),
    "DIS_ROUTES_PREPARED": (
        DiscoveryTemplate("DIS_ROUTES_PREPARED", "evac_corridor"),
    ),
    "DIS_ORGANISED": (
        DiscoveryTemplate("DIS_ORGANISED", "evac_corridor"),
        DiscoveryTemplate("DIS_ORGANISED", "airfield_plane"),
    ),
    "DEAD_WERE_LOCALS": (
        DiscoveryTemplate("DEAD_WERE_LOCALS", "service_route"),
    ),
    "DEAD_STAGES_DIFFER": (
        DiscoveryTemplate("DEAD_STAGES_DIFFER", "radio_tower"),
    ),
    "DEAD_CONTAINED_FIRST": (
        DiscoveryTemplate("DEAD_CONTAINED_FIRST", "power_station"),
    ),
    "DEAD_REGIONAL_CRISIS": (
        DiscoveryTemplate("DEAD_REGIONAL_CRISIS", "radio_tower"),
        DiscoveryTemplate("DEAD_REGIONAL_CRISIS", "boat_crossing"),
    ),
    "DEAD_INFECTION_PREDATES_EVAC": (
        DiscoveryTemplate("DEAD_INFECTION_PREDATES_EVAC", "rail_tunnel"),
    ),
}
