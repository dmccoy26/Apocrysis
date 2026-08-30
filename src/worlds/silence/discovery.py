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

    # CH3 - THE EVACUATION
    "RESP_CORRIDORS_LED_OUT": (
        DiscoveryTemplate("RESP_CORRIDORS_LED_OUT", "evac_corridor"),
    ),
    "RESP_NOT_ALL_REACHED": (
        DiscoveryTemplate("RESP_NOT_ALL_REACHED", "rail_tunnel"),
        DiscoveryTemplate("RESP_NOT_ALL_REACHED", "service_route"),
    ),
    "RESP_COMMS_CUT_DELIBERATE": (
        DiscoveryTemplate("RESP_COMMS_CUT_DELIBERATE", "radio_tower"),
    ),
    "RESP_CORDON_HELD_OUTSIDE": (
        DiscoveryTemplate("RESP_CORDON_HELD_OUTSIDE", "mountain_pass"),
        DiscoveryTemplate("RESP_CORDON_HELD_OUTSIDE", "tidal_causeway"),
    ),

    # CH4 - THE RESPONSE
    "RESP_PROTOCOL_SEVEN": (
        DiscoveryTemplate("RESP_PROTOCOL_SEVEN", "service_route"),
    ),
    "RESP_SEAL_SCHEDULED": (
        DiscoveryTemplate("RESP_SEAL_SCHEDULED", "dam_valves"),
        DiscoveryTemplate("RESP_SEAL_SCHEDULED", "tidal_causeway"),
    ),
    "RESP_ONE_COMMAND": (
        DiscoveryTemplate("RESP_ONE_COMMAND", "radio_tower"),
        DiscoveryTemplate("RESP_ONE_COMMAND", "power_station"),
    ),
    "RESP_CONTAINMENT_WORKED": (
        DiscoveryTemplate("RESP_CONTAINMENT_WORKED", "power_station"),
    ),

    # CH5 - THE LAST SIGNAL
    "RESP_STILL_MONITORED": (
        DiscoveryTemplate("RESP_STILL_MONITORED", "radio_tower"),
    ),
    "RESP_A_POST_TRANSMITS": (
        DiscoveryTemplate("RESP_A_POST_TRANSMITS", "power_station"),
        DiscoveryTemplate("RESP_A_POST_TRANSMITS", "radio_tower"),
    ),
    "RESP_CONSOLIDATION_HELD": (
        DiscoveryTemplate("RESP_CONSOLIDATION_HELD", "boat_crossing"),
        DiscoveryTemplate("RESP_CONSOLIDATION_HELD", "evac_corridor"),
    ),
    "RESP_PEOPLE_ALIVE": (
        DiscoveryTemplate("RESP_PEOPLE_ALIVE", "airfield_plane"),
    ),

    # FIN - THE TRUTH
    "RESP_THE_ORDER": (
        DiscoveryTemplate("RESP_THE_ORDER", "dam_valves"),
        DiscoveryTemplate("RESP_THE_ORDER", "radio_tower"),
    ),
    "RESP_THE_CHOICE": (
        DiscoveryTemplate("RESP_THE_CHOICE", "radio_tower"),
    ),
}
