"""World 3 - "The Deep": which escape mechanism carries which WorldFact.
docs/WORLD_3_THE_DEEP.md §5B.6 + the Phase-6 integration pass.

Only the 10 mystery-carried facts are here. The rest are carried by
authored beats (manifest.BEAT_CARRIED_FACTS): the L7 combat beat, the
L8/L16 scene beats, the L15/L20/L22/L24 contacts, the L19 discovery
crossing, the L23 campaign_state check, and the finale. next_target()
is given manifest.beat_carried_facts as `exclude` so a generated
mystery never grabs one.

>=2 routes on a fact that sits next to a same-family sibling in DAG
order (the Wake rule), so the variety-aware picker has a choice.
"""
from src.worlds.base import DiscoveryTemplate


def _r(fid, *mechs):
    return (fid, tuple(DiscoveryTemplate(fid, m) for m in mechs))


DISCOVERY_TEMPLATES = dict([
    # BAND I - THE WORKS
    _r("DESCENT_BLOCKED", "mountain_pass", "service_route", "rail_tunnel"),
    _r("SEAL_FROM_INSIDE", "service_route", "mountain_pass"),
    _r("WORK_CONTINUED_BELOW", "service_route", "rail_tunnel"),
    _r("DELIBERATE_OPERATION", "evac_corridor", "service_route"),
    _r("ORE_HAS_VALUE", "power_station", "rail_tunnel"),

    # BAND II - THE WORKING LEVELS
    _r("ANOMALY_REPORTS", "radio_tower", "power_station"),

    # BAND III - THE DEEP WORKINGS
    _r("EXTRACTION_EXPOSURE", "dam_valves", "power_station"),
    _r("ORDERS_AFTER_SEAL", "radio_tower", "evac_corridor"),
    _r("QUOTAS_CONTINUED", "service_route", "radio_tower"),
    _r("COMPANY_KNEW", "power_station", "dam_valves"),

    # the finale always targets THE_CHOICE - it needs a route to build
    # its bespoke last expedition, even though it is beat-carried.
    _r("THE_CHOICE", "power_station"),
])
