# ============================================================
# Apocrysis - "Dam Service Road" vertical-slice content
# File: src/slice_dam_road.py
#
# HAND-AUTHORED, FIXED (non-procedural) content for the v4
# vertical-slice mystery. This is deliberately NOT generated - it is
# the reference specimen the eventual procedural generator has to be
# able to reproduce at scale. See "Vertical slice prototype" and
# "Escape proof & causal-chain validation" in
# docs/ESCAPE_WORLD_DESIGN_ASSESSMENT.md.
#
# Pure data + pure helpers only. No game-loop logic, no imports from
# src/ - the engine integration lives in src/mixins/slice_mixin.py.
# ============================================================

SLICE_MAP_SIZE = 19

# (x, y) player start - south edge, so the flooded main road (north)
# and the locked service gate (east) are both discoveries, not things
# visible from spawn.
SLICE_SPAWN = (9, 17)

# Terrain uses the engine's existing vocabulary (see
# constants.TERRAIN_SYMBOLS): 'plain' . / 'forest' f / 'building' b /
# 'water' ~ / 'river' = (impassable). The flooded road is 'river' so
# it genuinely blocks movement the way the mystery needs.
SLICE_LOCATIONS = {
    'dam': {
        'coord': (9, 3),
        'name': 'the dam',
        'terrain': 'building',
        'blurb': (
            "A concrete gravity dam holds back a swollen reservoir. The "
            "spillway is roaring. Below it, the highway you came in on "
            "runs north - straight down into the water."
        ),
    },
    'flooded_road': {
        'coord': (9, 6),
        'name': 'the flooded highway',
        'terrain': 'plain',
        'blurb': (
            "The main road north ends here. A dozen paces on it "
            "disappears under brown, moving water. Whatever is on the "
            "far side, you are not walking there."
        ),
    },
    'control_room': {
        'coord': (11, 3),
        'name': 'the dam control room',
        'terrain': 'building',
        'blurb': (
            "A low blockhouse bolted to the dam's east abutment. "
            "Control panels, a wall of labelled keys, a cot someone "
            "slept on more recently than the dust suggests."
        ),
    },
    'utility_shed': {
        'coord': (6, 8),
        'name': 'the utility shed',
        'terrain': 'building',
        'blurb': (
            "A maintenance shed. Shelving, a workbench, a clipboard "
            "still hanging by the door. Someone kept this place in "
            "order."
        ),
    },
    'service_gate': {
        'coord': (14, 12),
        'name': 'the service gate',
        'terrain': 'building',
        'blurb': (
            "A steel vehicle gate across a gravel service road. "
            "Chained, padlocked, topped with wire. Through the bars the "
            "road keeps going east, up out of the valley."
        ),
    },
    'service_road_beyond': {
        'coord': (16, 12),
        'name': 'the service road',
        'terrain': 'plain',
        'blurb': (
            "The far side of the gate. The service road climbs away "
            "from the reservoir and over the ridge - out."
        ),
    },
    'farmhouse': {
        'coord': (3, 15),
        'name': 'the farmhouse',
        'terrain': 'building',
        'blurb': (
            "A clapboard farmhouse, doors open, curtains moving. A "
            "child's bicycle on its side in the yard."
        ),
    },
    'graffiti_wall': {
        'coord': (16, 6),
        'name': 'the tagged wall',
        'terrain': 'building',
        'blurb': (
            "A pumphouse wall facing the road. Someone has covered it, "
            "shoulder height, in dripping red letters."
        ),
    },
}

# A band of impassable 'river' tiles across the north of the map: the
# flood that closes the main road. The dam (9,3) and control room
# (11,3) sit on the far side and are reached by going around the ends
# of the band (x<7 or x>11), never straight up the highway.
_FLOOD_TILES = [(7, 5), (8, 5), (9, 5), (10, 5), (11, 5)]

# A steep rocky ridge boxing in the service-road corridor (y=12,
# x>=14). The gate at (14,12) is the ONLY gap in it - there is no
# walking around the gate to the road beyond.
_RIDGE_TILES = [
    (14, 11), (15, 11), (16, 11), (17, 11), (18, 11),
    (14, 13), (15, 13), (16, 13), (17, 13), (18, 13),
    (17, 12), (18, 12),  # corridor pinches out east - "off map" wall
]

# A little forest texture on the approach so the map isn't a blank
# plain. Purely atmospheric - none of these tiles carry content.
_FOREST_TILES = [
    (2, 10), (3, 10), (2, 11), (4, 11), (3, 12),
    (15, 15), (16, 15), (16, 16), (17, 15),
    (1, 4), (2, 4), (1, 5), (2, 6),
]


def build_slice_map():
    """A 19x19 grid indexed [y][x] of engine-shaped terrain cells.

    Cell shape matches world_mixin.generate_map():
    {'terrain': str, 'content': str, 'explored': bool}.
    Deterministic, no RNG.
    """
    grid = [
        [{'terrain': 'plain', 'content': '-', 'explored': False}
         for _ in range(SLICE_MAP_SIZE)]
        for _ in range(SLICE_MAP_SIZE)
    ]
    for x, y in _FOREST_TILES:
        grid[y][x]['terrain'] = 'forest'
    for x, y in _FLOOD_TILES:
        grid[y][x]['terrain'] = 'river'
    for x, y in _RIDGE_TILES:
        grid[y][x]['terrain'] = 'mountain'
    for loc in SLICE_LOCATIONS.values():
        x, y = loc['coord']
        grid[y][x]['terrain'] = loc['terrain']
    return grid


def slice_location_at(x, y):
    """Return the SLICE_LOCATIONS key at (x, y), or None."""
    for key, loc in SLICE_LOCATIONS.items():
        if loc['coord'] == (x, y):
            return key
    return None


# ------------------------------------------------------------
# The Escape Proof - the generator-internal structure that a
# procedural version would have to build and validate BACKWARD from
# the escape. Here it is authored directly. Never shown to the player
# as a structure; they only ever see the individual `text` leaves.
# ------------------------------------------------------------

SLICE_FACTS = {
    'F1': "The main road out is flooded and impassable.",
    'F2': "A service road bypasses the flooded road.",
    'F3': "The service road is closed by a locked gate.",
    'F4': "A key that opens the gate exists, kept in the dam control room.",
}

# method:
#   'observe' - recorded automatically the first time the player is at
#               the location (ordinary movement / looking around).
#   'search'  - only recorded if the player deliberately `search`es
#               the location.
# Every FACT has at least two independent evidence routes so the
# player can miss a clue and still solve it (redundancy is a
# requirement, not a nicety - see the design doc):
#   F1 <- E1 (observe dam), E1b (observe flooded_road)
#   F2 <- E2 (search shed log), E3 (observe gate - road visible through it),
#         E6 (observe beyond gate)
#   F3 <- E2 (search shed log), E3 (observe gate itself)
#   F4 <- E2 (search shed log), E4 (search shed requisition), E5 (search control room)
SLICE_EVIDENCE = [
    {
        'id': 'E1', 'location': 'dam', 'method': 'observe', 'supports': ['F1'],
        'text': ("From the dam you can see the whole north road. It runs "
                 "straight into the reservoir and does not come back out."),
    },
    {
        'id': 'E1b', 'location': 'flooded_road', 'method': 'observe', 'supports': ['F1'],
        'text': ("Standing at the water's edge: the road is under a moving "
                 "current, deepening fast. There is no wading this."),
    },
    {
        'id': 'E2', 'location': 'utility_shed', 'method': 'search', 'supports': ['F2', 'F3', 'F4'],
        'text': ("Maintenance log, last entry: 'Downstream access is the "
                 "south service road only while the highway's shut. Gate "
                 "stays locked - valve key's up in the control room now, "
                 "not the shed.'"),
    },
    {
        'id': 'E3', 'location': 'service_gate', 'method': 'observe', 'supports': ['F2', 'F3'],
        'text': ("The gate is chained and padlocked. But it is a gate, on a "
                 "road, and through the bars that road plainly keeps going."),
    },
    {
        'id': 'E4', 'location': 'utility_shed', 'method': 'search', 'supports': ['F4'],
        'text': ("A requisition slip spiked to the wall: 'Valve key moved to "
                 "control room safe after the break-in. See M. for access.'"),
    },
    {
        'id': 'E5', 'location': 'control_room', 'method': 'search', 'supports': ['F4'],
        'text': ("On the wall of labelled keys, one hook reads VALVE / "
                 "SERVICE GATE. The key is still on it."),
    },
    {
        'id': 'E6', 'location': 'service_road_beyond', 'method': 'observe', 'supports': ['F2'],
        'text': ("Past the open gate the service road climbs steadily out of "
                 "the valley. This goes somewhere. This is the way out."),
    },
]

# Deductions the player is expected to make by combining facts. These
# are not shown as checkboxes; `remember` synthesises them in prose
# once their supporting facts are known.
SLICE_DEDUCTIONS = [
    {
        'id': 'D1', 'needs': ['F1'],
        'text': "The way you came in is closed. You need another way out.",
    },
    {
        'id': 'D2', 'needs': ['F1', 'F2', 'F3'],
        'text': ("There is another road - the service road - and it is only "
                 "blocked by a gate, not by water. A gate can be opened."),
    },
]

SLICE_HYPOTHESIS = {
    'id': 'H1',
    'text': "The south service road, past the locked gate, is the way out.",
    # 'suspected' once these deductions are available:
    'suspected_when': ['D2'],
    # 'confirmed' only by physically seeing E6 (road continues past the
    # opened gate) - never by a status message.
    'confirmed_by': 'E6',
}

SLICE_KEY_ITEM = "valve key"
SLICE_KEY_EVIDENCE = 'E5'        # searching the control room is what yields the key
SLICE_GATE_LOCATION = 'service_gate'
SLICE_ESCAPE_LOCATION = 'service_road_beyond'

# ------------------------------------------------------------
# Irrelevant leads. Genuinely evocative, mechanically inert. The slice
# exists partly to test whether a player can chase these and recover
# without the interface ever telling them they are a dead end.
# ------------------------------------------------------------

SLICE_IRRELEVANT = {
    'farmhouse': (
        "The kitchen table is set for three. A diary is open on it, a "
        "girl's round handwriting:\n"
        "  'Day 9. Sarah still isn't back. Dad went to the checkpoint to "
        "ask and they turned him around at the wire. He says the men "
        "there aren't ours. Mom won't stop watching the road.'\n"
        "The last page is torn out. There is nothing else here - no "
        "supplies, no way through, just the diary and the moving "
        "curtains."
    ),
    'graffiti_wall': (
        "The red letters read: THEY LIED.\n"
        "That is all. No arrow, no name, no date. Someone needed to say "
        "it and had paint."
    ),
}


def evidence_by_id(eid):
    for e in SLICE_EVIDENCE:
        if e['id'] == eid:
            return e
    return None


def evidence_at(location_key, method=None):
    """All evidence entries at a location, optionally filtered by method."""
    return [
        e for e in SLICE_EVIDENCE
        if e['location'] == location_key and (method is None or e['method'] == method)
    ]
