"""World 2 - "The Wake": which escape mechanism carries which WorldFact.
docs/WORLD_2_THE_WAKE.md §7.

>=1 route per fact (a fact with no route would be targeted but never
tagged onto a mystery, and the campaign would stall). Facts that land
consecutively in DAG order and would otherwise repeat a story family
get a second route of a different family, so A.4.2's variety-aware
picker has a choice.

The 8-mechanism subset (manifest.supported_mechanisms), by family:
  spatial         mountain_pass, rail_tunnel
  infrastructural  service_route, power_station
  sequential       evac_corridor
  experimental     dam_valves
  informational    radio_tower
  transportation    airfield_plane
"""
from src.worlds.base import DiscoveryTemplate


def _r(fid, *mechs):
    return (fid, tuple(DiscoveryTemplate(fid, m) for m in mechs))


DISCOVERY_TEMPLATES = dict([
    # CH1 - THE WAKE
    _r("WAKE_ALONE", "mountain_pass"),              # a locked bay, find the access card
    _r("POWER_PARTITIONED", "power_station", "dam_valves"),
    _r("NAV_ON_HOLD", "radio_tower"),               # a nav console reads you the held command
    _r("SECTIONS_SEALED", "service_route", "rail_tunnel"),

    # CH2 - THE CREW
    _r("SURVIVORS_FEW", "evac_corridor"),           # follow a marked route to the enclave
    _r("THE_CHANGED", "service_route", "rail_tunnel"),
    _r("CHANGE_IS_STAGED", "radio_tower", "power_station"),
    _r("CHANGE_BEGAN_IN_CRYO", "power_station"),    # restart a cryo-bank diagnostic

    # CH3 - THE ISOLATION
    _r("SEAL_CODE_IS_MEDICAL", "dam_valves", "service_route"),
    _r("MEDICAL_DENIES_IT", "radio_tower"),
    _r("COMMS_CUT_OUTWARD", "radio_tower", "dam_valves"),
    _r("SEALS_ARE_QUARANTINE", "rail_tunnel", "evac_corridor"),

    # CH4 - THE ORDER
    _r("ONE_AUTHORIZATION", "radio_tower", "power_station"),
    _r("THE_OFFICERS_LOG", "service_route"),
    _r("SHUTDOWN_WAS_THE_CONTAINMENT", "dam_valves", "power_station"),
    _r("CONTAINMENT_FILED_CLEAN", "power_station"),
    _r("WAKE_YOU_BEFORE", "mountain_pass", "rail_tunnel"),  # found in a locker / crawlway

    # FIN - THE REACTOR
    _r("SURVIVORS_ON_A_CLOCK", "evac_corridor", "airfield_plane"),  # the enclave, and a pod
    _r("WAKE_RESTART_RELEASES", "power_station", "dam_valves"),
    _r("WAKE_THE_CHOICE", "power_station"),         # the finale - always
])
