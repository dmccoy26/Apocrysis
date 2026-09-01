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
    # GRAMMAR ONLY (Phase F §10.1). The FICTION - name / closed / route /
    # obstacle / require / item labels / roles / evidence templates /
    # landmark - lives in world.mechanism_prose (default:
    # worlds/silence/mechanism_prose.py). `build_mystery` merges the two
    # into a local `spec`; module-level helpers that have no world
    # (story_signature, choose_mechanism) read only the grammar here.
    "mountain_pass": {
        "family": "spatial", "discovery": "find_named_place",
        "reasoning": "locate", "resolution": "clear", "confirmation": "traversal",
        "has_item": True,
    },
    "rail_tunnel": {
        "family": "spatial", "discovery": "find_document",
        "reasoning": "locate", "resolution": "clear", "confirmation": "traversal",
        "has_item": True,
    },
    "service_route": {
        "family": "infrastructural", "discovery": "observe_anomaly",
        "reasoning": "locate", "resolution": "operate", "confirmation": "traversal",
        "has_item": True, "terrain": "water",
    },
    "boat_crossing": {
        "family": "transportation", "discovery": "find_object",
        "reasoning": "corroborate", "resolution": "operate", "confirmation": "traversal",
        "has_item": True, "terrain": "water",
    },
    "evac_corridor": {
        "family": "sequential", "discovery": "find_document",
        "reasoning": "sequence", "resolution": "open", "confirmation": "traversal",
        "has_item": True,
    },
    "power_station": {
        "family": "infrastructural", "discovery": "observe_anomaly",
        "reasoning": "infer", "resolution": "repair", "confirmation": "environmental",
        "has_item": True, "power_role": "power",
    },
    "dam_valves": {
        "family": "experimental", "discovery": "observe_anomaly",
        "reasoning": "revise", "resolution": "operate", "confirmation": "environmental",
        "has_item": False, "controls_count": 3,
    },
    "radio_tower": {
        "family": "informational", "discovery": "receive_information",
        "reasoning": "infer", "resolution": "repair", "confirmation": "external_response",
        "has_item": True, "power_role": "power", "reveals_route": True,
    },
    "airfield_plane": {
        "family": "transportation", "discovery": "find_object",
        "reasoning": "sequence", "resolution": "repair", "confirmation": "traversal",
        "has_item": True, "has_item2": True,
    },
    "tidal_causeway": {
        "family": "time_pressure", "discovery": "find_document",
        "reasoning": "triage", "resolution": "follow", "confirmation": "traversal",
        "has_item": False, "deadline_turns": 22, "flood_recovery": 24,
    },
}

_MECH_ORDER = list(MECHANISMS)


# Phase F §10.1: the generic fallback fiction for a mechanism a world's
# mechanism_prose does not define (a fixture / partial world). An
# authored world is expected to supply its own - this only exists so a
# minimal world still runs. Deliberately bland. Its SHAPE must match the
# mechanism's grammar (MECHANISMS[mechanism]) exactly - a field a world
# entry wouldn't carry must not be here either, or the merge in
# build_mystery would give e.g. a spatial mechanism a phantom `item2`.
def _fallback_prose(mechanism):
    g = MECHANISMS.get(mechanism, {})
    roles = {"closed": "the blocked way", "route": "the alternate route",
             "obstacle": "the obstruction", "require": "where the access is kept"}
    p = {
        "name": "the way out",
        "closed": "The ordinary way out is closed.",
        "route": "There is another way through.",
        "obstacle": "Something blocks the route.",
        "require": "What you need to clear it is kept nearby.",
        "obstacle_desc": "The way is obstructed.",
        "escape_desc": "The route runs on, clear. This is the way out.",
        "roles": roles,
        "landmark": "A feature stands out in the distance, the way through",
    }
    if g.get("has_item", True):
        p["item"] = "the access you need"
    else:
        p["item"] = None
    if g.get("has_item2"):
        p["require2"] = "A second part is stored elsewhere."
        p["item2"] = "the second part"
        p["assemble_desc"] = "You fit the parts. It is ready."
        roles["require2"] = "the second store"
    if g.get("controls_count"):
        n = g["controls_count"]
        p["controls"] = [f"the {o} control" for o in
                         ("first", "second", "third", "fourth", "fifth")[:n]]
        p["obvious_control"] = p["controls"][0]
        p["controls_prompt"] = "One of them opens the way - but which?"
        p["controls_lore"] = "opens the way"
        p["control_wrong_obvious"] = "Nothing changes. That was not it."
        p["control_wrong_other"] = "Something shifts, then holds. Not that one either."
        p["control_correct"] = "It works. The way opens."
    if g.get("power_role"):
        roles["power"] = "the power source"
        p["power_fact"] = "The way out has no power."
        p["power_obstacle_ev"] = "The mechanism is dead - no power reaching it."
        p["power_site_ev"] = "The power for it is fed from here."
        p["generator_ev"] = "The generator is out of fuel."
        p["power_restored_desc"] = "Power comes back. The way out responds."
    if g.get("reveals_route"):
        p["f_obstacle"] = "There is no way out to be seen yet."
        p["d_route"] = "The way out is whatever the other end tells you."
        p["route_reveal_ev"] = ("A route opens up to the {bearing}, one that was "
                                "never on the map. It's marked for you now.")
    if g.get("deadline_turns"):
        p["require_fact"] = "There is a window, and it will not last."
        p["require_ev"] = "The window is open now. It will close."
    return p


def mechanism_prose(mechanism, world=None):
    """The FICTION for `mechanism` in `world` (falling back to the
    grammar-shaped generic set). Phase F §10.1."""
    wp = getattr(world, "mechanism_prose", None) if world is not None else None
    if wp is not None and mechanism in wp:
        return {**_fallback_prose(mechanism), **wp[mechanism]}
    return _fallback_prose(mechanism)


def mech_spec(mechanism, world=None):
    """Grammar + prose merged, the shape the pre-Phase-F MECHANISMS
    entry had. `build_mystery` and per-mystery presentation use this."""
    return {**MECHANISMS.get(mechanism, {}), **mechanism_prose(mechanism, world)}

_MECH_ORDER = list(MECHANISMS)

# audit 1b - the physical landmark at each mechanism's 'route' site.
# The way out of the valley is a real feature you can see from a
# distance (a dam, a mast, a tunnel mouth) BEFORE you know it's the way
# out and independent of the map's '!' marker. Written to take a
# trailing ", <bearing> of here." clause. Says WHERE, never WHY - no
# investigation content leaks here.

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
    'triage',   # time-pressure: the window fits the critical path, not the optional evidence
)
RESOLUTION_PATTERNS = (
    'open', 'find', 'repair', 'clear', 'operate', 'reveal', 'follow', 'respond',
)
CONFIRMATION_PATTERNS = (
    'traversal', 'new_information', 'environmental', 'external_response', 'corroboration',
)


def story_signature(mechanism):
    """The player-facing SHAPE of a mechanism, coarser than its name:
    (family, dependency-class, exit-type) as a '|'-joined string.
    `key->gate`, `fuel->gate` and `battery->gate` all reduce to the
    same signature, so variety Rule C can steer away from repeating a
    shape even across different mechanism names (SCENARIO_EXPANSION.md
    §3). A string so it round-trips through JSON cleanly."""
    spec = MECHANISMS.get(mechanism, {})
    if spec.get('controls_count'):
        dep = 'control-choice'
    elif spec.get('has_item2'):
        dep = 'checklist'
    elif spec.get('power_role'):
        dep = 'restore-chain'
    elif spec.get('has_item'):
        dep = 'single-item'
    else:
        dep = 'none'
    exit_type = ('revealed-route' if spec.get('reveals_route')
                 else 'crossing' if spec.get('deadline_turns')
                 else 'gap')
    return f"{spec.get('family')}|{dep}|{exit_type}"


def choose_mechanism(rng, already_used, last_family=None,
                     recent_mechanisms=(), recent_signatures=(),
                     supported=()):
    """Shuffle-bag on the mechanism NAME (no repeat until the pool is
    exhausted), then three variety filters, each applied only if it
    leaves something to pick (SCENARIO_EXPANSION.md §3):
      A - not the same story family two expeditions running (3a);
      B - not one of the last couple of mechanisms (stops
          power_station -> dam_valves -> power_station);
      C - not one of the last couple of story SIGNATURES (stops
          three 'fetch an item, open a gate' shapes in a row even
          when the mechanism names differ).

    Phase F: `supported` (world.manifest.supported_mechanisms) restricts
    the pool to a world's subset. Empty = every mechanism (World 1)."""
    _order = [m for m in _MECH_ORDER if m in supported] if supported else _MECH_ORDER
    pool = [m for m in _order if m not in already_used] or list(_order)
    if last_family is not None:
        varied = [m for m in pool if MECHANISMS[m].get('family') != last_family]
        if varied:
            pool = varied
    recent_mechanisms = set(recent_mechanisms or ())
    fresh = [m for m in pool if m not in recent_mechanisms]
    if fresh:
        pool = fresh
    recent_signatures = set(recent_signatures or ())
    unshaped = [m for m in pool if story_signature(m) not in recent_signatures]
    if unshaped:
        pool = unshaped
    return rng.choice(pool)


class Mystery:
    """The generated escape mystery for one expedition - the knowledge
    catalogue plus the physical bits the engine needs (obstacle tile,
    requirement item, escape tile)."""

    def __init__(self):
        self.mechanism = None
        # A.2: the authored WorldFact this mystery was generated to
        # surface, or None for a plain random expedition. A tag only -
        # the mystery is still solved by its own evidence; nothing in
        # the build reads this. See docs/PHASE_A2_DISCOVERY.md.
        self.world_fact_id = None
        self.family = None          # STORY_FAMILIES value
        self.discovery = None       # DISCOVERY_PATTERNS value
        self.reasoning = None       # REASONING_PATTERNS value
        self.resolution = None      # RESOLUTION_PATTERNS value
        self.confirmation = None    # CONFIRMATION_PATTERNS value
        self.power_role = None       # role of the 'apply the fix here' site (infrastructural family), else None
        self.power_restored = False  # infrastructural: the dependency chain is satisfied
        self.controls = []            # experimental family: candidate controls, or []
        self.obvious_control = None   # the decoy control (prose)
        self.correct_control = None   # the control that opens the obstacle
        self.controls_tried = []      # control names pulled so far
        self.knowledge = Knowledge()
        self.sites = {}            # role -> (x, y)
        self.site_labels = {}      # role -> "the harbourmaster's shed"
        self.obstacle_tile = None  # (x, y) - blocked until cleared
        self.obstacle_open = False
        self.escape_tile = None    # (x, y) - reaching it (cleared + confirmed) wins
        self.requirement_item = None   # item name the player must acquire + use (primary)
        self.requirement_items = []    # transportation: EVERY item the machine needs, order-free.
                                       # [] or [requirement_item] means "single-item" - unchanged
                                       # behaviour for the other 8 mechanisms.
        self.saw_obstacle = False
        self.escaped = False
        # Phase F §10.1: world-owned mechanism prose the presentation
        # code reads after the build (set by build_mystery / from_dict).
        self.mech_name = "the way out"
        self.mech_landmark = ""
        self.power_restored_desc = "The way out has power now."
        self.assemble_desc = "You fit the parts. The machine is ready."
        self.control_correct = "It works. The way opens."
        self.control_wrong_obvious = "Nothing changes. That was not it."
        self.control_wrong_other = "Something shifts, then holds."
        # time-pressure family (tidal_causeway): a diegetic clock.
        self.deadline = None       # turns until the tide turns; None = no clock / not armed yet
        self.tide_recovery = 0     # while flooded: turns until the causeway reopens
        self.crossed = False       # stood on the far side with it open - the tide can't trap you now
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
        # transportation: a checklist of >1 parallel items needs a
        # require2 site and every entry non-empty.
        if len(self.requirement_items) > 1:
            if any(not it for it in self.requirement_items):
                problems.append("transportation: an empty requirement item")
            if 'require2' not in self.sites:
                problems.append("transportation: >1 requirement item but no require2 site")
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
            "world_fact_id": self.world_fact_id,
            "family": self.family,
            "discovery": self.discovery,
            "reasoning": self.reasoning,
            "resolution": self.resolution,
            "confirmation": self.confirmation,
            "power_role": self.power_role,
            "power_restored": self.power_restored,
            "controls": list(self.controls),
            "obvious_control": self.obvious_control,
            "correct_control": self.correct_control,
            "controls_tried": list(self.controls_tried),
            "knowledge": self.knowledge.to_dict(),
            "sites": {r: list(xy) for r, xy in self.sites.items()},
            "site_labels": dict(self.site_labels),
            "obstacle_tile": list(self.obstacle_tile) if self.obstacle_tile else None,
            "obstacle_open": self.obstacle_open,
            "escape_tile": list(self.escape_tile) if self.escape_tile else None,
            "requirement_item": self.requirement_item,
            "requirement_items": list(self.requirement_items),
            "deadline": self.deadline,
            "tide_recovery": self.tide_recovery,
            "crossed": self.crossed,
            "saw_obstacle": self.saw_obstacle,
            "escaped": self.escaped,
            "site_evidence": {r: list(v) for r, v in self._site_evidence.items()},
            "mech_name": self.mech_name,
            "mech_landmark": self.mech_landmark,
            "power_restored_desc": self.power_restored_desc,
            "assemble_desc": self.assemble_desc,
            "control_correct": self.control_correct,
            "control_wrong_obvious": self.control_wrong_obvious,
            "control_wrong_other": self.control_wrong_other,
        }

    @classmethod
    def from_dict(cls, d):
        m = cls()
        if not d:
            return m
        m.mechanism = d.get("mechanism")
        m.world_fact_id = d.get("world_fact_id")
        m.family = d.get("family")
        m.discovery = d.get("discovery")
        m.reasoning = d.get("reasoning")
        m.resolution = d.get("resolution")
        m.confirmation = d.get("confirmation")
        m.power_role = d.get("power_role")
        m.power_restored = d.get("power_restored", False)
        m.controls = list(d.get("controls", []))
        m.obvious_control = d.get("obvious_control")
        m.correct_control = d.get("correct_control")
        m.controls_tried = list(d.get("controls_tried", []))
        m.knowledge = Knowledge.from_dict(d.get("knowledge"))
        m.sites = {r: tuple(xy) for r, xy in d.get("sites", {}).items()}
        m.site_labels = dict(d.get("site_labels", {}))
        m.obstacle_tile = tuple(d["obstacle_tile"]) if d.get("obstacle_tile") else None
        m.obstacle_open = d.get("obstacle_open", False)
        m.escape_tile = tuple(d["escape_tile"]) if d.get("escape_tile") else None
        m.requirement_item = d.get("requirement_item")
        m.requirement_items = list(d.get("requirement_items", []))
        m.deadline = d.get("deadline")
        m.tide_recovery = d.get("tide_recovery", 0)
        m.crossed = d.get("crossed", False)
        m.saw_obstacle = d.get("saw_obstacle", False)
        m.escaped = d.get("escaped", False)
        m._site_evidence = {r: list(v) for r, v in d.get("site_evidence", {}).items()}
        for _k in ("mech_name", "mech_landmark", "power_restored_desc",
                   "assemble_desc", "control_correct", "control_wrong_obvious",
                   "control_wrong_other"):
            if d.get(_k) is not None:
                setattr(m, _k, d[_k])
        return m


_IMPASSABLE = ('mountain', 'river')

_CARDINALS = ('north', 'south', 'east', 'west')
_OPPOSITE = {'north': 'south', 'south': 'north', 'east': 'west', 'west': 'east'}


def _compass_tokens(text):
    """Cardinal words in a string - matches 'north', 'north-east',
    'northward', 'to the east'. Case-insensitive."""
    t = text.lower()
    return {c for c in _CARDINALS if c in t}


def _flatten_strs(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _flatten_strs(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _flatten_strs(v)


def _assert_directional_truth(spawn, escape_tile, mystery, spec):
    """Build-time invariant (SCENARIO_EXPANSION.md §5): any compass word
    the GENERATOR put into a piece of evidence must agree with the real
    vector from spawn to the carved gap. Authored scenery in the
    MECHANISMS entry ('the eastern hills') gets a pass - only tokens the
    generator added on top are held to the standard. A scenario may be
    hard; it may not point the player the wrong way."""
    dx = escape_tile[0] - spawn[0]
    dy = escape_tile[1] - spawn[1]
    true_ns = 'north' if dy < -2 else 'south' if dy > 2 else None
    true_ew = 'west' if dx < -2 else 'east' if dx > 2 else None
    authored = _compass_tokens(" ".join(_flatten_strs(spec)))
    problems = []
    for eid, e in mystery.knowledge.evidence.items():
        for tok in _compass_tokens(e.text) - authored:
            if tok in ('north', 'south') and true_ns and tok == _OPPOSITE[true_ns]:
                problems.append(f"{eid} says {tok!r}, the gap is {true_ns}")
            if tok in ('east', 'west') and true_ew and tok == _OPPOSITE[true_ew]:
                problems.append(f"{eid} says {tok!r}, the gap is {true_ew}")
    # The two bearing-injected clues must, positively, carry the right
    # direction (a derivation-refactor guard, not just a contradiction
    # check).
    for eid in ('E_obstacle_a', 'E_route_reveal'):
        e = mystery.knowledge.evidence.get(eid)
        if e is None:
            continue
        toks = _compass_tokens(e.text)
        for real in (true_ns, true_ew):
            if real and real not in toks and _OPPOSITE[real] in toks:
                problems.append(f"{eid} bearing text disagrees with spawn->gap ({real})")
    if problems:
        raise RuntimeError("directional-truth violation: " + "; ".join(problems))


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

    # §F.12: a transit world (WorldManifest.map_transit) wakes the
    # player against one side wall - the way out is the OPPOSITE wall,
    # as level with the spawn as the ring allows, so the expedition
    # reads as crossing the ship rather than stepping out the nearest
    # door. Only reached when a world opts in; every other world falls
    # through to the historical selection below unchanged.
    _tside = getattr(game, "_transit_side", None)
    if _tside:
        want_ix = n - 2 if _tside == 'west' else 1    # inner col of the far wall
        want_bx = n - 1 if _tside == 'west' else 0
        spawn_y = getattr(game, "_transit_spawn_y", sy)
        far = [g for g in all_gaps if g[2] == want_ix]
        far_reach = [g for g in far if (g[2], g[3]) in reachable]
        pool = far_reach or far
        if pool:
            bx, by, ix, iy = min(pool, key=lambda g: abs(g[3] - spawn_y))
            if not far_reach:
                _carve_line(game, (sx, sy), (ix, iy))
        else:
            iy = min(max(spawn_y, 1), n - 2)
            ix, bx, by = want_ix, want_bx, iy
            game.map[iy][ix] = {'terrain': 'plain', 'content': '-',
                                'zone': 'wilderness', 'explored': False}
            _carve_line(game, (sx, sy), (ix, iy))
        game.map[by][bx] = {'terrain': 'plain', 'content': '-', 'zone': 'wilderness',
                            'explored': False, 'escape_gap': True}
        return (bx, by), (ix, iy)

    _bound = getattr(game, "_lever_bound_gap", None)   # C.3.2a-5 lever 2
    if reachable_gaps and _bound is not None:
        # measurement-only. The gap is kept within a bounded distance of
        # the required-investigation centroid (nearest-3 buildings).
        _bs = _building_sites(game, reachable)[:3]
        if _bs:
            ax = sum(p[0] for p in _bs) / len(_bs)
            ay = sum(p[1] for p in _bs) / len(_bs)
        else:
            ax, ay = sx, sy
        _cd = lambda g: abs(g[2] - ax) + abs(g[3] - ay)
        if isinstance(_bound, (tuple, list)):
            # Gate 8 (docs/PHASE_C3_2_5_GATE8_SPEC.md): the bound is a
            # CEILING, not a target distance. ("sqrt", k) -> ceiling
            # k*sqrt(playable tiles), so the leg may grow with the map's
            # linear dimension but not its area; ("cap", C) -> a flat
            # ceiling (comparison baseline). Take the FARTHEST gap still
            # under the ceiling (keep the journey), else the closest to it.
            _kind, _val = _bound[0], _bound[1]
            _ceil = _val * (len(reachable) ** 0.5) if _kind == "sqrt" else float(_val)
            _within = [g for g in reachable_gaps if _cd(g) <= _ceil]
            if _within:
                bx, by, ix, iy = max(_within, key=_cd)
            else:
                bx, by, ix, iy = min(reachable_gaps,
                                     key=lambda g: abs(_cd(g) - _ceil))
        else:
            # legacy int TARGET form (the C.3.2a-5 lever matrix variants,
            # docs/PHASE_C3_2_5_LEVER_MATRIX.md) - unchanged.
            bx, by, ix, iy = min(reachable_gaps,
                                 key=lambda g: abs(_cd(g) - _bound))
    elif reachable_gaps:
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


def _scaled_beat_count(game, form, reachable):
    """C.3.2a-6 (measurement-only, docs/PHASE_C3_2_6_SPEC.md): how many
    extra required intermediate beats to insert, as a function of map
    size. `form` is (id, c) - id in {fixed, log, sqrt, linear}. Capped
    at 4 so a 34^2 map doesn't get a dozen. Byte-identical baseline:
    called only when _lever_scaled_beats is set."""
    import math
    kind, c = form
    n = game.map_size
    n0 = 15                       # the depth-0 base map dimension
    play = max(1, len(reachable))
    play0 = n0 * n0 * 0.7         # ~playable tiles on the base map
    if kind == "fixed":
        k = c
    elif kind == "log":
        k = c * math.log2(max(1.0, n / n0))
    elif kind == "sqrt":
        k = c * (math.sqrt(play) - math.sqrt(play0)) / 6.0
    elif kind == "linear":
        k = c * (n - n0) / 6.0
    else:
        k = 0
    return max(0, min(4, round(k)))


def _place_scaled_beats(game, m, reachable, k, spawn):
    """Pick up to k reachable building sites strung along the ACTUAL
    required spine (spawn -> route -> obstacle), each a genuine
    on-the-way stop: near-zero detour over walking that spine anyway,
    and >= 3 tiles from every other beat and every role site (no
    clustering - GATE6_SPEC section 3). Registers them as
    m.sites['beat_1'..] and m.required_beats.

    A beat withholds the location of the next required site (section
    3.1); for the experiment that gating is structural - the harness
    walks m.required_beats as required stops on the corridor. Fewer than
    k may land when the spine has no low-detour building for a slot;
    story_nodes_p50 in the report shows what actually placed."""
    sx, sy = spawn
    rx, ry = m.sites["route"]
    ox, oy = m.obstacle_tile
    # the spine as two segments; interpolate k points evenly across the
    # whole spine length so beats sit between real beats, not stacked.
    seg = [((sx, sy), (rx, ry)), ((rx, ry), (ox, oy))]
    seglen = [abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in seg]
    total = sum(seglen) or 1

    def spine_point(f):
        d = f * total
        for (a, b), L in zip(seg, seglen):
            if d <= L or L == 0:
                t = 0 if L == 0 else d / L
                return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
            d -= L
        return seg[-1][1]

    def spine_detour(p):
        # extra over spawn->route->obstacle if the walk stops at p
        best = 1e9
        for (a, b) in seg:
            base = abs(a[0] - b[0]) + abs(a[1] - b[1])
            via = (abs(a[0] - p[0]) + abs(a[1] - p[1])
                   + abs(p[0] - b[0]) + abs(p[1] - b[1]))
            best = min(best, via - base)
        return best

    taken = [tuple(v) for v in m.sites.values()]
    pool = [s for s in _building_sites(game, reachable)
            if s not in taken and s != m.obstacle_tile
            and spine_detour(s) <= 4]

    def far_enough(p, chosen):
        return all(abs(p[0] - q[0]) + abs(p[1] - q[1]) >= 3
                   for q in chosen)

    beats = []
    for i in range(1, k + 1):
        tx, ty = spine_point(i / (k + 1))
        cands = sorted(
            (p for p in pool if far_enough(p, taken + beats)),
            key=lambda p: abs(p[0] - tx) + abs(p[1] - ty))
        if cands:
            beats.append(cands[0])
    m.required_beats = []
    for i, b in enumerate(beats, 1):
        key = f"beat_{i}"
        m.sites[key] = b
        m.required_beats.append(key)


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


def build_mystery(game, target_fact=None):
    """Populate game.knowledge and return a Mystery for this expedition.
    Called from world_mixin.generate_map().

    A.2: if `target_fact` is a WorldFact id with a DiscoveryTemplate on
    `game.world`, the mechanism is chosen to carry that fact (and
    stamped on `m.world_fact_id`) instead of the random variety roll.
    The mystery is otherwise built and solved exactly the same way -
    `target_fact` never enters the evidence. See PHASE_A2_DISCOVERY.md.
    """
    rng = game.rng
    m = Mystery()
    _routes = None
    if target_fact is not None:
        _routes = getattr(game.world, 'discovery_templates', {}).get(target_fact)
    if _routes:
        # A.4.2: the targeted path bypasses choose_mechanism's variety
        # rules, so honour the one that matters most here - don't repeat
        # the previous expedition's story family - when a route allows.
        _last_family = getattr(game.__class__, '_last_family', None)
        _varied = [t for t in _routes
                   if MECHANISMS.get(t.mechanism, {}).get('family') != _last_family]
        m.mechanism = rng.choice(_varied or list(_routes)).mechanism
        m.world_fact_id = target_fact
    else:
        _manifest = getattr(game.world, 'manifest', None)
        m.mechanism = choose_mechanism(
            rng,
            getattr(game.__class__, '_used_mechanisms', []),
            last_family=getattr(game.__class__, '_last_family', None),
            recent_mechanisms=getattr(game.__class__, '_recent_mechanisms', ()),
            recent_signatures=getattr(game.__class__, '_recent_signatures', ()),
            supported=(_manifest.supported_mechanisms if _manifest else ()),
        )
    # Phase F §10.1: grammar (MECHANISMS) + fiction (world.mechanism_prose)
    # merged. Every `spec[...]` below is shape-agnostic from here.
    spec = mech_spec(m.mechanism, getattr(game, 'world', None))
    m.family = spec.get('family')
    m.discovery = spec.get('discovery')
    m.reasoning = spec.get('reasoning')
    m.resolution = spec.get('resolution')
    m.confirmation = spec.get('confirmation')
    # prose the per-mystery presentation code (mystery_mixin / tui /
    # world_mixin) needs after the build - stamped so those call sites
    # don't have to re-resolve the world.
    m.mech_name = spec.get('name', 'the way out')
    m.mech_landmark = spec.get('landmark', '')
    m.power_restored_desc = spec.get('power_restored_desc', 'The way out has power now.')
    m.assemble_desc = spec.get('assemble_desc', 'You fit the parts. The machine is ready.')
    m.control_correct = spec.get('control_correct', 'It works. The way opens.')
    m.control_wrong_obvious = spec.get('control_wrong_obvious', 'Nothing changes. That was not it.')
    m.control_wrong_other = spec.get('control_wrong_other', 'Something shifts, then holds.')

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
    # out". Transportation: the machine (the plane) sits at the valley's
    # edge, so its site is the one NEAREST the carved gap - "head for the
    # airstrip" and "head for the way out" are the same vector (pacing
    # invariant 3d). Everyone else: low detour, middle band of the
    # spawn->exit run.
    _transport = bool(spec.get('item2'))
    _deadline = bool(spec.get('deadline_turns'))
    if _transport or _deadline:
        # transportation: the plane sits at the valley's edge.
        # time-pressure: the causeway runs to the valley's edge.
        # Either way the route site IS the way out - same vector.
        role_route = min(_rest, key=lambda s: abs(s[0] - ex) + abs(s[1] - ey))
    else:
        _band = sorted((s for s in _rest
                        if 0.25 * _sp_ex <= _from_spawn(s) <= 0.85 * _sp_ex),
                       key=_detour)
        role_route = (_band[0] if _band
                      else (sorted(_rest, key=_detour)[0] if _rest else role_closed))
    _rest = [s for s in _rest if s != role_route] or [role_route]

    # 'require' (+ 'require2' for transportation) - a real side-trip is
    # fine, a straight shot off-axis is not; cap the detour.
    def _pick_side(pool):
        ranked = (sorted((s for s in pool if _detour(s) <= game.map_size * 0.5),
                         key=_detour) or sorted(pool, key=_detour))
        return ranked[0]

    def _staging(pool):
        # C.3.2a-5 lever 4 (measurement-only): put the require site on
        # the way from the route toward the exit - a staging point
        # between the investigation and the escape, shortening the
        # require->obstacle leg without a retrace.
        rx, ry = role_route
        mx, my = (rx + ex) / 2, (ry + ey) / 2
        return min(pool or _rest,
                   key=lambda s: abs(s[0] - mx) + abs(s[1] - my))

    _spread = getattr(game, "_lever_spread_sites", False)
    role_require = _staging(_rest) if _spread else _pick_side(_rest)

    m.sites = {
        'closed': role_closed,
        'route': role_route,
        'obstacle': m.obstacle_tile,
        'require': role_require,
    }
    m.requirement_item = spec["item"]
    m.requirement_items = ([spec["item"]] + [spec["item2"]]) if _transport else []
    if _transport:
        _rest2 = [s for s in _rest if s != role_require] or [role_require]
        m.sites['require2'] = _staging(_rest2) if _spread else _pick_side(_rest2)
    if _deadline:
        # time-pressure: the tide is OUT when the mystery starts - the
        # causeway tile is passable. There is nothing to unlock; the
        # clock (armed when F_ROUTE lands) is the whole obstacle. The
        # tick flips obstacle_open False when the tide floods.
        m.obstacle_open = True
        game.map[inner_tile[1]][inner_tile[0]]['obstacle'] = False

    # C.3.2a-6 (measurement-only, docs/PHASE_C3_2_6_SPEC.md): when
    # _lever_scaled_beats is set, insert k = f(map size) extra required
    # intermediate beats along the corridor. Flag off (the default) ->
    # this is skipped entirely and the mystery is byte-identical.
    _beats_form = getattr(game, "_lever_scaled_beats", None)
    if _beats_form:
        _k = _scaled_beat_count(game, _beats_form, reachable)
        if _k:
            _place_scaled_beats(game, m, reachable, _k, spawn)

    # World grammar: each role-site is a NAMED place, not a generic
    # building. The evidence chain references these same names ("the
    # fuel is in the harbourmaster's shed"), so once the player reads
    # that they can recognise the place when they reach it - the boat
    # -> fuel inference the design wants, instead of "search every
    # building". Tagged on the tile; mystery_arrive leads with it.
    roles = spec.get("roles", {})
    m.site_labels = {}
    for role in ('closed', 'route', 'require', 'require2'):
        label = roles.get(role)
        if label and role in m.sites:
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
        m.obvious_control = spec.get('obvious_control')
        m.correct_control = rng.choice(
            [c for c in m.controls if c != m.obvious_control])

    # --- build the Escape Proof ---
    k = m.knowledge
    _req_line = (f"The thing needed to get past it exists - a {spec['item']}, "
                 f"and you know where." if spec.get('item')
                 else spec.get('require_fact',
                               "What clears it is something you have to work out on the spot."))
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
                  + spec.get('controls_prompt', "One of them opens the way - but which?")
                  if spec.get('controls')
                  else spec.get('require_ev') or f"You find the {spec['item']} here."),
                 supports=['F_REQUIRE'], location='require', method='search'),
        Evidence('E_confirm', spec["escape_desc"], supports=['F_ROUTE'],
                 location='escape', method='observe'),
    ]
    if _transport:
        # transportation: the second parallel requirement. The route
        # site (the airstrip) briefs BOTH stores; the require2 site
        # itself holds the item. Both support F_REQUIRE ("the machine
        # needs things", plural).
        ev.append(Evidence('E_require2_a', spec['require2'], supports=['F_REQUIRE'],
                           location='route', method='search'))
        ev.append(Evidence('E_require2_b', f"You find the {spec['item2']} here.",
                           supports=['F_REQUIRE'], location='require2', method='search'))
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
    _edge = (getattr(getattr(game, 'world', None), 'prose', {}) or {}).get(
        "region_edge", "edge of the map")
    for e in ev:
        if e.id == 'E_obstacle_a' and not _reveal:
            e.text = f"{e.text} It's out toward the {_bearing} {_edge}."
        elif e.id == 'E_route_reveal':
            e.text = e.text.replace('{bearing}', _bearing)

    # B.2 COMMAND_FREQUENCY: a survivor who learned that regional command
    # held one emergency frequency reads the broadcast log at the route
    # site as an arrival observation, not a thing to dig for - one fewer
    # `search` step in a radio_tower mystery. Legibility, not power: same
    # site, same solve, the item just surfaces on arrival.
    _sk = getattr(game, 'survivor_knowledge', None)
    if _reveal and _sk is not None and _sk.has('COMMAND_FREQUENCY'):
        for e in ev:
            if e.id == 'E_route_a':
                e.method = 'observe'

    # B.2 RESERVOIR_CONTROLS: informational only. A survivor who's done a
    # dam_valves mystery before reads the control-room notes and knows
    # which control governs the reservoir - they still operate it, still
    # revise if they pull a wrong one. Control count and the obstacle's
    # open condition are unchanged (invariant 4).
    if spec.get('controls') and _sk is not None and _sk.has('RESERVOIR_CONTROLS'):
        for e in ev:
            if e.id == 'E_require_b':
                e.text = (f"A bank of controls: {', '.join(spec['controls'])}. "
                          f"The control-room notes are clear: {m.correct_control} "
                          f"{spec.get('controls_lore', 'opens the way')}.")

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

    _assert_directional_truth(spawn, m.escape_tile, m, spec)
    m.validate()
    return m
