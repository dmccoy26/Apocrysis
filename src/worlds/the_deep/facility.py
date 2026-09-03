"""World 3 - "The Deep": the facility-systems table.
docs/WORLD_3_THE_DEEP.md §5B.8 - kill-test A.

`campaign_state["restored"]` is a persistent set of system ids the
player has brought back online over the campaign (beside
`world_investigation`, same persistence pattern). This table is what
those ids mean.

Two things a build of kill-test A must decide, and how §5B answers them:
- **what restoring a system means mechanically** - §5B.10: a `discovery`
  crossing is "a system to bring back"; §5B.6: a few infra mysteries
  are "restore-to-read". So a system enters `restored` when its
  trigger fact is established OR its discovery crossing completes.
- **what `RESTART_REOPENS_THE_ROUTE` ★23 is** - §5B.4: NOT a normal
  `WorldFact` with `needs`, NOT a discoverable. It is derived from
  `campaign_state`: it fires the moment `restored` covers every
  `on_extraction_path` system (§5B.8 hook 3), which by schedule is on
  completing the L23 discovery crossing.
"""

# §5B.8 verbatim shape. `on_extraction_path` = a piece of the road the
# seam travels up (the L23 sting). `is_containment` = a piece of the
# thing that holds the deep shut (feeds CONTAINMENT_INFRASTRUCTURE's
# text and, later, generate_map's clear-air consult - deferred past
# kill-test A).
FACILITY_SYSTEMS = {
    "power":          {"on_extraction_path": True,  "is_containment": False,
                       "prose": "Main power back on the deep bus - the decline doors, the pumps, the cages all have a supply again."},
    "lift_deep":      {"on_extraction_path": True,  "is_containment": False,
                       "prose": "The deep cage runs. Whatever's below the seal can be reached, and carried, on a rope again."},
    "haulage":        {"on_extraction_path": True,  "is_containment": False,
                       "prose": "The haulage line turns over - tubs, skips, the ore road, all the way to the pass."},
    "extraction":     {"on_extraction_path": True,  "is_containment": False,
                       "prose": "Main extraction control answers. The last of the line is live: the seam can be worked and moved out."},
    "ventilation":    {"on_extraction_path": False, "is_containment": True,
                       "prose": "The main fans turn. Air moves down the intakes and the dead-air pockets start to clear."},
    "vent_split_deep":{"on_extraction_path": False, "is_containment": True,
                       "prose": "The deep vent split is back under control - the galleries below the seal are held on their own air, cut from the rest."},
    "bore_doors":     {"on_extraction_path": False, "is_containment": True,
                       "prose": "The bore doors have power and a control. They can be run - either way."},
    "lighting":       {"on_extraction_path": False, "is_containment": False,
                       "prose": "The level lighting comes up in stretches - the dark runs are shorter now."},
    "comms":          {"on_extraction_path": False, "is_containment": False,
                       "prose": "The internal loop is live again. Not the outside line - just voice, level to level."},
}

EXTRACTION_PATH = tuple(s for s, v in FACILITY_SYSTEMS.items()
                        if v["on_extraction_path"])
CONTAINMENT_SYSTEMS = tuple(s for s, v in FACILITY_SYSTEMS.items()
                            if v["is_containment"])

# What restores what. Keys are either a WorldFact id (the fact is
# established -> the system comes back, for the infra "restore-to-read"
# mysteries) or "discovery:<n>" (the nth `discovery` crossing on the
# schedule completes -> the system comes back). Every EXTRACTION_PATH
# system must be reachable by L23 so ★23 can fire.
RESTORES = {
    "ORE_HAS_VALUE":              "power",        # a working face / a loaded hopper -> the bus is live
    "discovery:0":                "lift_deep",    # L11 crossing - the deep cage
    "discovery:1":                "haulage",      # L19 crossing - the ore road
    "discovery:2":                "extraction",   # L23 crossing - the last piece (§5B.3 special)
    "ANOMALY_REPORTS":            "ventilation",  # restore-to-read the medical station
    "CONTAINMENT_INFRASTRUCTURE": "vent_split_deep",
}

# The campaign-state-derived fact ★23 (§5B.4). Fired by the engine's
# restoration hook, not by a mystery or a discoverable.
RESTART_FACT = "RESTART_REOPENS_THE_ROUTE"

FACILITY = {
    "systems": FACILITY_SYSTEMS,
    "extraction_path": EXTRACTION_PATH,
    "containment_systems": CONTAINMENT_SYSTEMS,
    "restores": RESTORES,
    "restart_fact": RESTART_FACT,
}
