"""World 3 - "The Deep": which escape mechanism carries which WorldFact.
docs/WORLD_3_THE_DEEP.md §5B.6.

>=1 route per fact (a fact with no route stalls the campaign). Facts
that land consecutively in DAG order and would repeat a story family
get a second route of a different family, so the variety-aware picker
has a choice.

Kill-test 0: the facts §5B.6 spec's for `WorldContact` (kill-test B) and
the `campaign_state` check (kill-test A) are carried here by ordinary
mechanism routes for now. Kill-tests A/B move them to their real
carriers.

The 8-mechanism subset, by family:
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
    # BAND I - THE WORKS
    # three routes off the cage head so expedition 1 isn't the same map
    # every campaign: the man-way (find the key), the maintenance
    # crawlway (find the panel key), the haulage drift (cut the fall).
    _r("DESCENT_BLOCKED", "mountain_pass", "service_route", "rail_tunnel"),
    _r("SEAL_FROM_INSIDE", "service_route", "mountain_pass"),
    _r("WORK_CONTINUED_BELOW", "service_route", "rail_tunnel"),
    _r("ORE_HAS_VALUE", "power_station", "rail_tunnel"),
    _r("DELIBERATE_OPERATION", "evac_corridor", "service_route"),

    # BAND II - THE WORKING LEVELS
    _r("CHANGED_ARE_CREW", "service_route", "rail_tunnel"),
    _r("CHANGED_BY_DEPTH", "radio_tower", "power_station"),
    _r("CHANGED_HAVE_STRUCTURE", "rail_tunnel", "evac_corridor"),
    _r("ANOMALY_REPORTS", "radio_tower", "power_station"),

    # BAND III - THE DEEP WORKINGS
    _r("EXTRACTION_EXPOSURE", "dam_valves", "power_station"),
    _r("COMPANY_CORRELATION", "radio_tower", "power_station"),
    _r("QUOTAS_CONTINUED", "service_route", "radio_tower"),
    _r("COMPANY_KNEW", "power_station", "dam_valves"),
    _r("ORDERS_AFTER_SEAL", "radio_tower"),

    # BAND IV - THE SEALED GALLERIES
    _r("COMMS_CUT_FROM_BELOW", "radio_tower", "dam_valves"),
    _r("WORKERS_CHOSE_ISOLATION", "service_route", "evac_corridor"),
    _r("CASE_TIMING", "rail_tunnel", "radio_tower"),
    _r("CONTAINMENT_INFRASTRUCTURE", "dam_valves", "power_station"),
    _r("WORKERS_MAINTAINING_IT", "evac_corridor", "service_route"),

    # BAND V - THE SEAL
    _r("ORE_IS_SOURCE", "dam_valves", "radio_tower"),
    _r("SURVIVORS_ON_A_CLOCK", "evac_corridor", "airfield_plane"),
    _r("RESTART_REOPENS_THE_ROUTE", "power_station", "dam_valves"),
    _r("THE_STANCES", "evac_corridor", "radio_tower"),
    _r("THE_CHOICE", "power_station"),          # the finale - always

    # TEXTURE
    _r("SOMEONE_IS_COMING", "mountain_pass", "rail_tunnel"),
])
