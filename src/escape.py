# ============================================================
# Apocrysis - procedural escape-mechanism generation (v4 Phase C /
# Stage 4)
# File: src/escape.py
#
# Turns a generated map into an investigation: picks an escape
# mechanism, places its evidence at real locations, carves the actual
# escape route through the mountain boundary, and builds the Escape
# Proof (the src/knowledge.py model) that a player reconstructs.
#
#   generation flows downward  -  mechanism -> geography -> clues
#   player discovery flows upward  -  clues -> facts -> hypothesis
#
# This is the first working generator, not the full contextual-
# generation vision from the design doc (that seeds terrain/settlement
# from the mechanism). Here the map exists first and the mechanism is
# placed onto it - enough to make v4 an investigation game end to end.
# ============================================================

from src.knowledge import Knowledge, Fact, Evidence, Deduction, Hypothesis


# Each mechanism is a reskin of the same four-fact chain:
#   F_CLOSED     the ordinary way out is closed
#   F_ROUTE      a specific alternate route exists
#   F_OBSTACLE   that route is blocked by something the player can clear
#   F_REQUIRE    the thing needed to clear it exists, and where
# plus one physical requirement item and one obstacle tile.
MECHANISMS = {
    "mountain_pass": {
        "name": "the old mountain pass",
        "family": "spatial", "discovery": "find_named_place",
        "reasoning": "locate", "resolution": "clear", "confirmation": "traversal",
        "closed": "The road out of the valley is choked with abandoned vehicles, bumper to bumper for miles. Nothing is driving out that way.",
        "route": "There's an old foot pass over the ridge - the ranger maps still show it.",
        "obstacle": "The pass trailhead is behind a locked forestry gate.",
        "require": "A ranger station keeps the forestry gate keys.",
        "item": "forestry gate key",
        "obstacle_desc": "A locked forestry service gate blocks the trail up to the pass.",
        "escape_desc": "The foot pass switchbacks up over the ridge and down the far side. This is the way out.",
        "roles": {"closed": "the clogged highway", "route": "a trailhead noticeboard",
                  "obstacle": "forestry gate", "require": "the ranger station"},
    },
    "rail_tunnel": {
        "name": "the railway tunnel",
        "family": "spatial", "discovery": "find_document",
        "reasoning": "locate", "resolution": "clear", "confirmation": "traversal",
        "closed": "The main bridge over the river is down - dropped into the water, deliberately by the look of the charges still wired to what's left.",
        "route": "The rail line runs through a tunnel in the eastern hills - it comes out beyond the river entirely.",
        "obstacle": "The tunnel mouth is caved in. Not impassable, but not walkable either without clearing it.",
        "require": "The rail maintenance depot had the tools for exactly this.",
        "item": "rail clearing charge",
        "obstacle_desc": "The railway tunnel entrance is half-collapsed. You'd need something to clear the fall.",
        "escape_desc": "Past the fall the tunnel runs straight and level, a cold draught coming the other way. Daylight, far ahead.",
        "roles": {"closed": "the wrecked bridge", "route": "the rail yard",
                  "obstacle": "collapsed tunnel", "require": "the rail maintenance depot"},
    },
    "service_route": {
        "name": "the dam service road",
        "family": "infrastructural", "discovery": "observe_anomaly",
        "reasoning": "locate", "resolution": "operate", "confirmation": "traversal",
        "closed": "The reservoir has come up over the valley road. It's a lake now, not a road.",
        "route": "There's a service road along the downstream face of the dam that stays above the water line.",
        "obstacle": "The service road is closed by a gate at the dam end.",
        "require": "The gate key is kept in the dam control room.",
        "item": "service gate key",
        "obstacle_desc": "A chained and padlocked service gate blocks the road along the dam.",
        "escape_desc": "The service road runs on past the gate, climbing away from the water and out of the valley.",
        "roles": {"closed": "the flooded road", "route": "the dam",
                  "obstacle": "service gate", "require": "the dam control room"},
        "terrain": "water",
    },
    "boat_crossing": {
        "name": "the boat crossing",
        "family": "transportation", "discovery": "find_object",
        "reasoning": "corroborate", "resolution": "operate", "confirmation": "traversal",
        "closed": "Every road inland is blocked - checkpoints, wrecks, one of them still burning.",
        "route": "The marina still has boats in their slips. Water doesn't have checkpoints.",
        "obstacle": "The boats are dry - no fuel in any of the tanks.",
        "require": "The harbourmaster's shed stores fuel drums.",
        "item": "jerrycan of fuel",
        "obstacle_desc": "A serviceable boat sits ready at the dock, but the fuel gauge reads empty.",
        "escape_desc": "The engine catches. You take the boat out past the harbour wall and open water opens up ahead.",
        "roles": {"closed": "the blocked checkpoint", "route": "the marina",
                  "obstacle": "empty boat", "require": "the harbourmaster's shed"},
        "terrain": "water",
    },
    "evac_corridor": {
        "name": "the evacuation corridor",
        "family": "sequential", "discovery": "find_document",
        "reasoning": "sequence", "resolution": "open", "confirmation": "traversal",
        "closed": "The interstate on-ramp is collapsed - a whole overpass down across all the lanes.",
        "route": "There was a signed evacuation corridor on the surface streets, running north out of town.",
        "obstacle": "The corridor is barricaded where it leaves the built-up area - a checkpoint that was never taken down.",
        "require": "The police station has the corridor's access codes and the barricade key.",
        "item": "barricade key",
        "obstacle_desc": "A military barricade closes the evacuation corridor - concrete, wire, and a locked vehicle gate.",
        "escape_desc": "Past the barricade the corridor runs clear and straight, the evac signs still up, pointing you out.",
        "roles": {"closed": "a collapsed overpass", "route": "an evacuation-route sign",
                  "obstacle": "barricade", "require": "the police station"},
    },
    "power_station": {
        "name": "the road tunnel",
        "family": "infrastructural", "discovery": "observe_anomaly",
        "reasoning": "infer", "resolution": "repair", "confirmation": "environmental",
        "closed": "Every road out ends the same way - a slide, a checkpoint, a bridge dropped in the river. Nothing is driving out.",
        "route": "There's a road tunnel bored straight through the ridge - it comes out on the far side of the mountains.",
        "obstacle": "The tunnel is closed by a heavy electric gate, and the gate is dead. No power, no way to raise it.",
        "require": "Fuel drums are stored at the highway works yard.",
        "item": "jerrycan of fuel",
        "obstacle_desc": "A heavy electric vehicle gate seals the tunnel mouth. The control panel is unlit.",
        "escape_desc": "The gate grinds up. The tunnel runs level and straight through the ridge, and there is light at the far end.",
        "roles": {"closed": "a blocked checkpoint", "route": "the tunnel mouth",
                  "obstacle": "the tunnel gate", "require": "the works yard",
                  "power": "the hydro station"},
        "power_role": "power",
        "power_fact": "The tunnel gate's power comes from the hydro station downriver.",
        "power_obstacle_ev": "The gate is electric and its panel is stone dead. A cable run leaves it heading downriver - the power comes from somewhere else.",
        "power_site_ev": "A heavy cable leaves the switch room here, strung on poles toward the ridge tunnel.",
        "generator_ev": "The generator's fuel gauge sits on empty. It will not turn over dry.",
        "power_restored_desc": "The generator catches and runs. Downriver, the tunnel gate's panel lights up.",
    },
    "dam_valves": {
        "name": "the lower valley road",
        "family": "experimental", "discovery": "observe_anomaly",
        "reasoning": "revise", "resolution": "operate", "confirmation": "environmental",
        "closed": "The main road out is gone - a whole hillside came down across it.",
        "route": "There's a lower road that runs under the dam and out through the far end of the valley. It's still there, under the water.",
        "obstacle": "The lower road is under the reservoir. The water level is held by the dam and set from the control room.",
        "require": "The dam control room holds the gates for the whole reservoir - a bank of controls.",
        "item": None,
        "obstacle_desc": "The lower road runs straight down into the reservoir. Too deep to wade.",
        "escape_desc": "The water's dropped off the lower road. It runs on out through the end of the valley, wet but clear.",
        "roles": {"closed": "the landslide", "route": "the lower road",
                  "obstacle": "the flooded road", "require": "the dam control room"},
        "controls": ["the main sluice", "the east intake", "the west intake"],
        "obvious_control": "the main sluice",
        "control_wrong_obvious": "Water roars away downstream - but the level behind the dam doesn't move. The main sluice feeds the river below, not the valley reservoir.",
        "control_wrong_other": "The gate grinds open. The reservoir drops a hand's width, then holds. This one only takes part of it.",
        "control_correct": "The gate opens and stays open. Behind the dam the reservoir starts falling in earnest - and out on the lower road, the water pulls back off the tarmac.",
    },
    "radio_tower": {
        "name": "the emergency access road",
        "family": "informational", "discovery": "receive_information",
        "reasoning": "infer", "resolution": "repair", "confirmation": "external_response",
        "closed": "Every road out ends the same way - a checkpoint, a slide, a bridge dropped in the river. Nothing is driving out.",
        "route": "An emergency broadcast log, left open on the desk. The valley's channel is still monitored from the regional station - the last entry reads: 'if the tower comes back up, we can talk someone out.'",
        "obstacle": "The broadcast tower stands on the ridge, and the transmitter is dark. The control panel is dead - no power to it at all.",
        "require": "A fuel cache is kept at the ranger depot.",
        "item": "jerrycan of fuel",
        "obstacle_desc": "The transmitter housing at the tower base is silent, its panel unlit.",
        "escape_desc": "The emergency access road climbs the ridge exactly where the voice said it would, and drops away down the far side. This is the way out.",
        "roles": {"closed": "a dropped bridge", "route": "the broadcast log",
                  "obstacle": "the broadcast tower", "require": "the ranger depot",
                  "power": "the generator shed"},
        "power_role": "power",
        "power_fact": "The valley can still be reached from outside - but only if the broadcast tower is transmitting.",
        "power_obstacle_ev": "The transmitter is dead. A conduit runs from it down the slope toward a shed - the power comes from there, and nothing is coming through.",
        "power_site_ev": "A generator sits in the shed, cabled up the slope to the tower. This is what drives the transmitter.",
        "generator_ev": "The generator's tank is bone dry. It will not turn over without fuel.",
        "power_restored_desc": "The generator catches. Up on the ridge the transmitter's panel lights, and the channel opens with a hiss of static.",
        "reveals_route": True,
        "f_obstacle": "There is no way out to be seen - not until the tower is transmitting and someone on the outside answers.",
        "d_route": "The way out isn't a road you can find on your own - it's whatever the people on the other end of that channel tell you.",
        "route_reveal_ev": "The channel crackles, then a voice - clear, close. They read you an emergency access road up the {bearing} ridge, a track that was never on any map. It's marked for you now.",
    },
}

_MECH_ORDER = list(MECHANISMS)

STORY_FAMILIES = (
    'spatial', 'directional', 'corroborative', 'infrastructural',
    'environmental', 'informational', 'sequential', 'experimental',
    'transportation', 'time_pressure',
)
DISCOVERY_PATTERNS = (
    'see_route', 'find_document', 'find_named_place', 'observe_anomaly',
    'receive_information', 'find_object',
)
REASONING_PATTERNS = (
    'locate', 'connect', 'corroborate', 'infer', 'experiment', 'revise', 'sequence',
)
RESOLUTION_PATTERNS = (
    'open', 'find', 'repair', 'clear', 'operate', 'reveal', 'follow', 'respond',
)
CONFIRMATION_PATTERNS = (
    'traversal', 'new_information', 'environmental', 'external_response', 'corroboration',
)


def choose_mechanism(rng, already_used, last_family=None):
    """Shuffle-bag on the mechanism NAME (no repeat until the pool is
    exhausted); additionally, don't hand the player the same story
    family two expeditions running (schema invariant 3a) - unless that
    would leave nothing to pick."""
    pool = [m for m in _MECH_ORDER if m not in already_used] or list(_MECH_ORDER)
    if last_family is not None:
        varied = [m for m in pool if MECHANISMS[m].get('family') != last_family]
        if varied:
            pool = varied
    return rng.choice(pool)


class Mystery:
    """The generated escape mystery for one expedition - the knowledge
    catalogue plus the physical bits the engine needs (obstacle tile,
    requirement item, escape tile)."""

    def __init__(self):
        self.mechanism = None
        self.family = None          # STORY_FAMILIES value
        self.discovery = None       # DISCOVERY_PATTERNS value
        self.reasoning = None       # REASONING_PATTERNS value
        self.resolution = None      # RESOLUTION_PATTERNS value
        self.confirmation = None    # CONFIRMATION_PATTERNS value
        self.power_role = None       # role of the 'apply the fix here' site (infrastructural family), else None
        self.power_restored = False  # infrastructural: the dependency chain is satisfied
        self.controls = []            # experimental family: candidate controls, or []
        self.correct_control = None   # the control that opens the obstacle
        self.controls_tried = []      # control names pulled so far
        self.knowledge = Knowledge()
        self.sites = {}            # role -> (x, y)
        self.site_labels = {}      # role -> "the harbourmaster's shed"
        self.obstacle_tile = None  # (x, y) - blocked until cleared
        self.obstacle_open = False
        self.escape_tile = None    # (x, y) - reaching it (cleared + confirmed) wins
        self.requirement_item = None   # item name the player must acquire + use
        self.saw_obstacle = False
        self.escaped = False
        # role -> list of evidence ids observed/searchable at that site
        self._site_evidence = {}

    # ---- validation -------------------------------------------

    def validate(self):
        """The knowledge-chain analogue of _ensure_reachable(): every
        load-bearing fact must have >=2 independent evidence routes, and
        the hypothesis must be confirmable. Raises on failure - a
        broken mystery is a generation bug, caught before the player
        sees it."""
        k = self.knowledge
        problems = []
        for fid in k.facts:
            routes = [e for e in k.evidence.values() if fid in e.supports]
            if len(routes) < 2:
                problems.append(f"fact {fid} has only {len(routes)} evidence route(s)")
        if k.hypothesis is None:
            problems.append("no hypothesis")
        elif k.hypothesis.confirmed_by not in k.evidence:
            problems.append("hypothesis.confirmed_by is not a real evidence id")
        if self.obstacle_tile is None or self.escape_tile is None:
            problems.append("missing obstacle or escape tile")
        if self.power_role and self.power_role not in self.sites:
            problems.append("power_role set but no such site")
        if self.controls and self.correct_control not in self.controls:
            problems.append("experimental: correct_control not among controls")
        # Classification must come from the closed vocabularies - catches
        # a typo in a new MECHANISMS entry before a player sees it.
        for attr, vocab in (
            ("family", STORY_FAMILIES), ("discovery", DISCOVERY_PATTERNS),
            ("reasoning", REASONING_PATTERNS), ("resolution", RESOLUTION_PATTERNS),
            ("confirmation", CONFIRMATION_PATTERNS),
        ):
            val = getattr(self, attr)
            if val is not None and val not in vocab:
                problems.append(f"{attr} {val!r} is not in the vocabulary")
        if problems:
            raise RuntimeError("escape mystery failed validation: " + "; ".join(problems))

    # ---- knowledge helpers -----------------------------------

    def _has_searchable(self, role):
        return any(
            self.knowledge.evidence[eid].method == 'search'
            and eid not in self.knowledge.found
            for eid in self._site_evidence.get(role, [])
        )

    def facts_known(self):
        return self.knowledge.facts_known()

    def hypothesis_state(self):
        return self.knowledge.hypothesis_state()

    def to_dict(self):
        return {
            "mechanism": self.mechanism,
            "family": self.family,
            "discovery": self.discovery,
            "reasoning": self.reasoning,
            "resolution": self.resolution,
            "confirmation": self.confirmation,
            "power_role": self.power_role,
            "power_restored": self.power_restored,
            "controls": list(self.controls),
            "correct_control": self.correct_control,
            "controls_tried": list(self.controls_tried),
            "knowledge": self.knowledge.to_dict(),
            "sites": {r: list(xy) for r, xy in self.sites.items()},
            "site_labels": dict(self.site_labels),
            "obstacle_tile": list(self.obstacle_tile) if self.obstacle_tile else None,
            "obstacle_open": self.obstacle_open,
            "escape_tile": list(self.escape_tile) if self.escape_tile else None,
            "requirement_item": self.requirement_item,
            "saw_obstacle": self.saw_obstacle,
            "escaped": self.escaped,
            "site_evidence": {r: list(v) for r, v in self._site_evidence.items()},
        }

    @classmethod
    def from_dict(cls, d):
        m = cls()
        if not d:
            return m
        m.mechanism = d.get("mechanism")
        m.family = d.get("family")
        m.discovery = d.get("discovery")
        m.reasoning = d.get("reasoning")
        m.resolution = d.get("resolution")
        m.confirmation = d.get("confirmation")
        m.power_role = d.get("power_role")
        m.power_restored = d.get("power_restored", False)
        m.controls = list(d.get("controls", []))
        m.correct_control = d.get("correct_control")
        m.controls_tried = list(d.get("controls_tried", []))
        m.knowledge = Knowledge.from_dict(d.get("knowledge"))
        m.sites = {r: tuple(xy) for r, xy in d.get("sites", {}).items()}
        m.site_labels = dict(d.get("site_labels", {}))
        m.obstacle_tile = tuple(d["obstacle_tile"]) if d.get("obstacle_tile") else None
        m.obstacle_open = d.get("obstacle_open", False)
        m.escape_tile = tuple(d["escape_tile"]) if d.get("escape_tile") else None
        m.requirement_item = d.get("requirement_item")
        m.saw_obstacle = d.get("saw_obstacle", False)
        m.escaped = d.get("escaped", False)
        m._site_evidence = {r: list(v) for r, v in d.get("site_evidence", {}).items()}
        return m


_IMPASSABLE = ('mountain', 'river')


def _reachable_from(game, start):
    """Set of tiles walkable-reachable from start over non-impassable
    terrain."""
    from collections import deque
    n = game.map_size
    seen = {start}
    q = deque([start])
    while q:
        x, y = q.popleft()
        for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < n and 0 <= ny < n and (nx, ny) not in seen:
                c = game.map[ny][nx]
                if isinstance(c, dict) and c.get('terrain') not in _IMPASSABLE:
                    seen.add((nx, ny))
                    q.append((nx, ny))
    return seen


def _carve_line(game, a, b):
    """L-shaped carve (clears impassable interior tiles) so b is
    reachable from a. Never touches the boundary ring."""
    n = game.map_size
    x, y = a
    tx, ty = b
    path = []
    sx = 1 if tx > x else -1
    while x != tx:
        x += sx
        path.append((x, y))
    sy = 1 if ty > y else -1
    while y != ty:
        y += sy
        path.append((x, y))
    for px, py in path:
        if not (1 <= px < n - 1 and 1 <= py < n - 1):
            continue
        cell = game.map[py][px]
        if isinstance(cell, dict) and cell.get('terrain') in _IMPASSABLE:
            cell['terrain'] = 'plain'


def _building_sites(game, reachable):
    """Reachable building / settlement tiles, nearest-spawn first."""
    sx, sy = game.current_position
    sites = [
        (x, y)
        for y, row in enumerate(game.map)
        for x, cell in enumerate(row)
        if (x, y) in reachable and isinstance(cell, dict)
        and cell.get('terrain') in ('building', 'town')
    ]
    sites.sort(key=lambda p: abs(p[0] - sx) + abs(p[1] - sy))
    return sites


def _carve_escape_pass(game, reachable):
    """Open a one-tile gap in the mountain boundary ring whose interior
    neighbour is reachable from spawn (carving an approach if needed),
    and return that interior tile - the escape location. Mountain-
    boundary Phase 3 (todo 0b052554)."""
    n = game.map_size
    rng = game.rng
    sx, sy = game.current_position
    all_gaps = []
    for i in range(1, n - 1):
        for (bx, by, ix, iy) in (
            (i, 0, i, 1), (i, n - 1, i, n - 2),
            (0, i, 1, i), (n - 1, i, n - 2, i),
        ):
            inner = game.map[iy][ix]
            if isinstance(inner, dict) and inner.get('terrain') not in _IMPASSABLE:
                all_gaps.append((bx, by, ix, iy))

    reachable_gaps = [g for g in all_gaps if (g[2], g[3]) in reachable]
    if reachable_gaps:
        # A gap at a MODERATE remove from spawn - a journey, not a
        # half-map hike on a 34^2 (pacing invariant 3d). Sort by
        # spawn distance and take the ~65th-percentile gap rather than
        # the max.
        _by_dist = sorted(reachable_gaps,
                          key=lambda g: abs(g[2] - sx) + abs(g[3] - sy))
        bx, by, ix, iy = _by_dist[min(len(_by_dist) - 1,
                                      int(len(_by_dist) * 0.65))]
    elif all_gaps:
        bx, by, ix, iy = rng.choice(all_gaps)
        _carve_line(game, (sx, sy), (ix, iy))
    else:
        bx, by, ix, iy = 1, 0, 1, 1
        game.map[iy][ix] = {'terrain': 'plain', 'content': '-',
                            'zone': 'wilderness', 'explored': False}
        _carve_line(game, (sx, sy), (ix, iy))

    game.map[by][bx] = {'terrain': 'plain', 'content': '-', 'zone': 'wilderness',
                        'explored': False, 'escape_gap': True}
    return (bx, by), (ix, iy)


def _paint_terrain_near(game, center, terrain, count, protected):
    """Set up to `count` walkable, non-boundary, non-protected tiles
    around `center` to `terrain` - world coherence only (a marina needs
    water beside it), so `terrain` must stay passable. Skips town tiles
    and anything already the target terrain."""
    cx, cy = center
    n = game.map_size
    cands = []
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if (dx, dy) == (0, 0):
                continue
            x, y = cx + dx, cy + dy
            if not (1 <= x < n - 1 and 1 <= y < n - 1) or (x, y) in protected:
                continue
            cell = game.map[y][x]
            if isinstance(cell, dict) and cell.get('terrain') not in ('town', terrain):
                cands.append((x, y))
    game.rng.shuffle(cands)
    for x, y in cands[:count]:
        game.map[y][x]['terrain'] = terrain


def build_mystery(game):
    """Populate game.knowledge and return a Mystery for this expedition.
    Called from world_mixin.generate_map() for non-slice games."""
    rng = game.rng
    m = Mystery()
    m.mechanism = choose_mechanism(
        rng,
        getattr(game.__class__, '_used_mechanisms', []),
        last_family=getattr(game.__class__, '_last_family', None),
    )
    spec = MECHANISMS[m.mechanism]
    m.family = spec.get('family')
    m.discovery = spec.get('discovery')
    m.reasoning = spec.get('reasoning')
    m.resolution = spec.get('resolution')
    m.confirmation = spec.get('confirmation')

    spawn = game.current_position
    reachable = _reachable_from(game, spawn)

    sites = _building_sites(game, reachable)
    if len(sites) < 3:
        # Degenerate map (rare) - no mystery, fall back to reach-town.
        return None

    # The escape gap + its interior tile (obstacle sits there).
    gap_tile, inner_tile = _carve_escape_pass(game, reachable)
    m.escape_tile = gap_tile
    m.obstacle_tile = inner_tile
    game.map[inner_tile[1]][inner_tile[0]]['obstacle'] = True
    # carving may have changed connectivity - recompute
    reachable = _reachable_from(game, spawn)
    sites = _building_sites(game, reachable)
    if len(sites) < 3:
        return None

    # Assign the non-obstacle roles. Critical-path sites get geographic
    # momentum toward the exit; side sites may detour, but bounded
    # (pacing invariant 3d - "solve then trek" was every playtest death).
    sites = [s for s in sites if s != m.obstacle_tile]
    ex, ey = m.escape_tile
    _sp_ex = abs(spawn[0] - ex) + abs(spawn[1] - ey) or 1

    def _from_spawn(p):
        return abs(spawn[0] - p[0]) + abs(spawn[1] - p[1])

    def _detour(p):
        # extra distance spawn->p->exit costs over spawn->exit direct;
        # ~0 means p is on the way out.
        return (_from_spawn(p) + abs(p[0] - ex) + abs(p[1] - ey)) - _sp_ex

    # 'closed' - where you came in; keep it near spawn (list is
    # nearest-spawn-first).
    role_closed = sites[0]
    _rest = [s for s in sites if s != role_closed] or [sites[0]]

    # 'route' - the site that turns "wander" into "head for the way
    # out": low detour, in the middle band of the spawn->exit run.
    _band = sorted((s for s in _rest
                    if 0.25 * _sp_ex <= _from_spawn(s) <= 0.85 * _sp_ex),
                   key=_detour)
    role_route = (_band[0] if _band
                  else (sorted(_rest, key=_detour)[0] if _rest else role_closed))
    _rest = [s for s in _rest if s != role_route] or [role_route]

    # 'require' - a real side-trip is fine, a straight shot off-axis is
    # not; cap the detour.
    _side = sorted((s for s in _rest if _detour(s) <= game.map_size * 0.5),
                   key=_detour) or sorted(_rest, key=_detour)
    role_require = _side[0]

    m.sites = {
        'closed': role_closed,
        'route': role_route,
        'obstacle': m.obstacle_tile,
        'require': role_require,
    }
    m.requirement_item = spec["item"]

    # World grammar: each role-site is a NAMED place, not a generic
    # building. The evidence chain references these same names ("the
    # fuel is in the harbourmaster's shed"), so once the player reads
    # that they can recognise the place when they reach it - the boat
    # -> fuel inference the design wants, instead of "search every
    # building". Tagged on the tile; mystery_arrive leads with it.
    roles = spec.get("roles", {})
    m.site_labels = {}
    for role in ('closed', 'route', 'require'):
        label = roles.get(role)
        if label:
            m.site_labels[role] = label
            sx_, sy_ = m.sites[role]
            cell = game.map[sy_][sx_]
            if isinstance(cell, dict):
                cell['site_label'] = label

    # World coherence (playtest: "a marina in the middle of a forest").
    # A water-themed mechanism needs water where the boats / dam are and
    # where the boat launches. Paint a little in if the generator didn't
    # put it there - never over the boundary ring or a role tile.
    if spec.get("terrain") == "water":
        _protected_xy = set(m.sites.values()) | {m.obstacle_tile, m.escape_tile}
        _paint_terrain_near(game, m.sites['route'], 'water', 3, _protected_xy)
        _paint_terrain_near(game, m.obstacle_tile, 'water', 2, _protected_xy)

    # Experimental family (dam_valves): no fetch item - the obstacle is
    # opened by working out which control does it, from the control
    # room. The obvious control is never the right one.
    if spec.get('controls'):
        m.controls = list(spec['controls'])
        m.correct_control = rng.choice(
            [c for c in m.controls if c != spec.get('obvious_control')])

    # --- build the Escape Proof ---
    k = m.knowledge
    _req_line = (f"The thing needed to get past it exists - a {spec['item']}, "
                 f"and you know where." if spec.get('item')
                 else "What clears it is something you have to work out on the spot.")
    _reveal = bool(spec.get('reveals_route'))
    F = {
        'F_CLOSED': "The usual way out is closed.",
        'F_ROUTE': f"There is another route out: {spec['name']}.",
        'F_OBSTACLE': spec.get('f_obstacle',
                               "That route is blocked by something that can be cleared or opened."),
        'F_REQUIRE': _req_line,
    }
    if spec.get('power_role'):
        # F_POWER used to be added inside the power block below; hoisted
        # here so evidence built in the main list can support it.
        F['F_POWER'] = spec['power_fact']
    for fid, s in F.items():
        k.add_fact(Fact(fid, s))

    # evidence, each with >=2 routes per load-bearing fact
    ev = [
        Evidence('E_closed_a', spec["closed"], supports=['F_CLOSED'],
                 location='closed', method='observe'),
        Evidence('E_closed_b',
                 "Everyone who left went the same way, and none of it worked - you can see that from here.",
                 supports=['F_CLOSED'], location='closed', method='observe'),
        # informational (reveals_route): F_ROUTE is NOT known from any
        # early site - it only lands via E_route_reveal after the
        # system comes back up. The route site's own evidence (the
        # broadcast log) instead carries F_POWER + F_OBSTACLE.
        Evidence('E_route_a', spec["route"],
                 supports=['F_POWER', 'F_OBSTACLE'] if _reveal else ['F_ROUTE'],
                 location='route', method='search'),
        Evidence('E_route_b',
                 f"A hand-drawn note, more than one place: 'try {spec['name']}'.",
                 supports=['F_ROUTE', 'F_REQUIRE'], location='closed', method='search'),
        Evidence('E_obstacle_a', spec["obstacle"],
                 supports=['F_OBSTACLE'] if _reveal else ['F_ROUTE', 'F_OBSTACLE'],
                 location='route', method='search'),
        Evidence('E_obstacle_b', spec["obstacle_desc"], supports=['F_OBSTACLE'],
                 location='obstacle', method='observe'),
        # At the ROUTE site (the noticeboard / marina / tunnel mouth),
        # not the obstacle: the player should get the whole briefing -
        # "there's a route, it's blocked, here's what clears it and
        # where" - in one place, before trekking to the obstacle only
        # to be sent back for the key (playtest).
        Evidence('E_require_a', spec["require"], supports=['F_REQUIRE'],
                 location='route', method='search'),
        Evidence('E_require_b',
                 (f"A bank of controls: {', '.join(spec['controls'])}. "
                  "One of them sets the valley reservoir - but which?"
                  if spec.get('controls')
                  else f"You find the {spec['item']} here."),
                 supports=['F_REQUIRE'], location='require', method='search'),
        Evidence('E_confirm', spec["escape_desc"], supports=['F_ROUTE'],
                 location='escape', method='observe'),
    ]
    if _reveal:
        # E_route_b names the route ("try the emergency access road") -
        # a leak before radio contact. Drop it; F_ROUTE is carried by
        # E_route_reveal + E_confirm, F_REQUIRE by E_require_a/b + the
        # generator evidence.
        ev = [e for e in ev if e.id != 'E_route_b']
        ev.append(Evidence(
            'E_route_reveal',
            spec.get('route_reveal_ev',
                     "A voice on the channel reads you a way out. It's marked on your map now."),
            supports=['F_ROUTE'], location='_deferred', method='observe'))
    # Playtest: "every clue said north, but the escape was southwest."
    # The sites cluster near spawn; the gap is deliberately the far
    # corner. Without a bearing, the evidence points the player the
    # wrong way. Fold the real gap direction into the obstacle clue so
    # evidence actually leads where the route is - or, for a
    # reveals_route mystery, into the response that first names it.
    _gx, _gy = m.escape_tile
    _dx, _dy = _gx - spawn[0], _gy - spawn[1]
    _ns = "north" if _dy < -2 else "south" if _dy > 2 else ""
    _ew = "west" if _dx < -2 else "east" if _dx > 2 else ""
    _bearing = ("-".join(p for p in (_ns, _ew) if p)) or "far"
    for e in ev:
        if e.id == 'E_obstacle_a' and not _reveal:
            e.text = f"{e.text} It's out toward the {_bearing} edge of the valley."
        elif e.id == 'E_route_reveal':
            e.text = e.text.replace('{bearing}', _bearing)

    for e in ev:
        k.add_evidence(e)

    k.add_deduction(Deduction('D_need_other', "The way you came in is closed. You need another way out.",
                              needs=['F_CLOSED']))
    k.add_deduction(Deduction('D_the_route',
                              spec.get('d_route',
                                       f"{spec['name'].capitalize()} is that other way - and it's only blocked, not gone."),
                              needs=['F_CLOSED', 'F_ROUTE', 'F_OBSTACLE']))
    # informational (reveals_route): the RESPONSE is the confirmation -
    # `confirmation: external_response`. A voice reading you a clear
    # road IS knowing the way out; don't then make the player march to
    # a far corner just to "see it for themselves" (pacing invariant:
    # mystery-to-exit continuity - the resolution must not require an
    # unrelated post-solution trek).
    k.set_hypothesis(Hypothesis(
        'H_escape', f"{spec['name'].capitalize()} is the way out.",
        suspected_when=['D_the_route'],
        confirmed_by='E_route_reveal' if _reveal else 'E_confirm'))

    # index evidence by site role for arrival/search
    for e in ev:
        m._site_evidence.setdefault(e.location, []).append(e.id)

    # --- infrastructural family (power_station): the obstacle depends
    # on a system somewhere ELSE. A 5th site (the hydro station), a new
    # F_POWER fact, and the requirement item is applied THERE - the
    # gate opens on m.power_restored, not on carrying the item to it.
    if spec.get('power_role'):
        m.power_role = spec['power_role']
        plabel = spec['roles']['power']
        used_xy = set(m.sites.values())
        pool = [s for s in sites if s not in used_xy]
        # power is a side-trip too - keep it low-detour (pacing 3d).
        pool.sort(key=_detour)
        p_xy = pool[0] if pool else role_require
        m.sites['power'] = p_xy
        m.site_labels['power'] = plabel
        pcell = game.map[p_xy[1]][p_xy[0]]
        if isinstance(pcell, dict):
            pcell['site_label'] = plabel
        # F_POWER is added to the fact set earlier now (see F dict).
        for e in (
            Evidence('E_power_a', spec['power_obstacle_ev'],
                     supports=['F_OBSTACLE', 'F_POWER'], location='obstacle', method='observe'),
            Evidence('E_power_b', spec['power_site_ev'],
                     supports=['F_POWER'], location='power', method='observe'),
            Evidence('E_generator', spec['generator_ev'],
                     supports=['F_REQUIRE'], location='power', method='observe'),
        ):
            k.add_evidence(e)
            m._site_evidence.setdefault(e.location, []).append(e.id)

    # Physical guarantee: every site and the escape tile must be
    # reachable from spawn (with the obstacle open). Carve an approach
    # for any that isn't - the knowledge-chain analogue of
    # _ensure_reachable, plus the physical one.
    reachable = _reachable_from(game, spawn)
    for xy in list(m.sites.values()) + [m.escape_tile]:
        if xy not in reachable:
            _carve_line(game, spawn, xy)
            reachable = _reachable_from(game, spawn)

    m.validate()
    return m
