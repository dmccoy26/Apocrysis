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
        "closed": "The reservoir has come up over the valley road. It's a lake now, not a road.",
        "route": "There's a service road along the downstream face of the dam that stays above the water line.",
        "obstacle": "The service road is closed by a gate at the dam end.",
        "require": "The gate key is kept in the dam control room.",
        "item": "service gate key",
        "obstacle_desc": "A chained and padlocked service gate blocks the road along the dam.",
        "escape_desc": "The service road runs on past the gate, climbing away from the water and out of the valley.",
        "roles": {"closed": "the flooded road", "route": "the dam",
                  "obstacle": "service gate", "require": "the dam control room"},
    },
    "boat_crossing": {
        "name": "the boat crossing",
        "closed": "Every road inland is blocked - checkpoints, wrecks, one of them still burning.",
        "route": "The marina still has boats in their slips. Water doesn't have checkpoints.",
        "obstacle": "The boats are dry - no fuel in any of the tanks.",
        "require": "The harbourmaster's shed stores fuel drums.",
        "item": "jerrycan of fuel",
        "obstacle_desc": "A serviceable boat sits ready at the dock, but the fuel gauge reads empty.",
        "escape_desc": "The engine catches. You take the boat out past the harbour wall and open water opens up ahead.",
        "roles": {"closed": "the blocked checkpoint", "route": "the marina",
                  "obstacle": "empty boat", "require": "the harbourmaster's shed"},
    },
    "evac_corridor": {
        "name": "the evacuation corridor",
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
}

_MECH_ORDER = list(MECHANISMS)


def choose_mechanism(rng, already_used):
    """Shuffle-bag: no repeat until the pool is exhausted."""
    pool = [m for m in _MECH_ORDER if m not in already_used] or _MECH_ORDER
    return rng.choice(pool)


class Mystery:
    """The generated escape mystery for one expedition - the knowledge
    catalogue plus the physical bits the engine needs (obstacle tile,
    requirement item, escape tile)."""

    def __init__(self):
        self.mechanism = None
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
        # farthest from spawn - escape should feel like a journey
        bx, by, ix, iy = max(reachable_gaps,
                             key=lambda g: abs(g[2] - sx) + abs(g[3] - sy))
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


def build_mystery(game):
    """Populate game.knowledge and return a Mystery for this expedition.
    Called from world_mixin.generate_map() for non-slice games."""
    rng = game.rng
    m = Mystery()
    m.mechanism = choose_mechanism(rng, getattr(game.__class__, '_used_mechanisms', []))
    spec = MECHANISMS[m.mechanism]

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

    # Assign the three non-obstacle roles to distinct sites. 'closed'
    # and 'route' near spawn (early discoveries); 'require' anywhere.
    sites = [s for s in sites if s != m.obstacle_tile]
    near = sites[: max(2, len(sites) // 2)]
    role_closed = near[0]
    role_route = near[1] if len(near) > 1 else sites[1]
    remaining = [s for s in sites if s not in (role_closed, role_route)] or [sites[-1]]
    rng.shuffle(remaining)
    role_require = remaining[0]

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

    # --- build the Escape Proof ---
    k = m.knowledge
    F = {
        'F_CLOSED': "The usual way out is closed.",
        'F_ROUTE': f"There is another route out: {spec['name']}.",
        'F_OBSTACLE': "That route is blocked by something that can be cleared or opened.",
        'F_REQUIRE': f"The thing needed to get past it exists - a {spec['item']}, and you know where.",
    }
    for fid, s in F.items():
        k.add_fact(Fact(fid, s))

    # evidence, each with >=2 routes per load-bearing fact
    ev = [
        Evidence('E_closed_a', spec["closed"], supports=['F_CLOSED'],
                 location='closed', method='observe'),
        Evidence('E_closed_b',
                 "Everyone who left went the same way, and none of it worked - you can see that from here.",
                 supports=['F_CLOSED'], location='closed', method='observe'),
        Evidence('E_route_a', spec["route"], supports=['F_ROUTE'],
                 location='route', method='search'),
        Evidence('E_route_b',
                 f"A hand-drawn note, more than one place: 'try {spec['name']}'.",
                 supports=['F_ROUTE', 'F_REQUIRE'], location='closed', method='search'),
        Evidence('E_obstacle_a', spec["obstacle"], supports=['F_ROUTE', 'F_OBSTACLE'],
                 location='route', method='search'),
        Evidence('E_obstacle_b', spec["obstacle_desc"], supports=['F_OBSTACLE'],
                 location='obstacle', method='observe'),
        Evidence('E_require_a', spec["require"], supports=['F_REQUIRE'],
                 location='obstacle', method='search'),
        Evidence('E_require_b', f"You find the {spec['item']} here.",
                 supports=['F_REQUIRE'], location='require', method='search'),
        Evidence('E_confirm', spec["escape_desc"], supports=['F_ROUTE'],
                 location='escape', method='observe'),
    ]
    for e in ev:
        k.add_evidence(e)

    k.add_deduction(Deduction('D_need_other', "The way you came in is closed. You need another way out.",
                              needs=['F_CLOSED']))
    k.add_deduction(Deduction('D_the_route', f"{spec['name'].capitalize()} is that other way - and it's only blocked, not gone.",
                              needs=['F_CLOSED', 'F_ROUTE', 'F_OBSTACLE']))
    k.set_hypothesis(Hypothesis('H_escape', f"{spec['name'].capitalize()} is the way out.",
                                suspected_when=['D_the_route'], confirmed_by='E_confirm'))

    # index evidence by site role for arrival/search
    for e in ev:
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
