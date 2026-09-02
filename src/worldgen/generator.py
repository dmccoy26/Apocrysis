"""MapGenerator - the base-map generation pipeline, moved verbatim out
of world_mixin.generate_map() in Phase C (C.1). Behaviour and RNG
consumption order are unchanged: this is a relocation, not a rewrite.

Produces game.map / game.current_position / game.map_archetype /
game.map_archetype_blurb and returns the real town centre (or None).
The engine then embeds the mystery, places zombies, and adds flavour.

No imports from src.game / src.mixins / src.escape.
"""
from collections import deque

from src.constants import (
    IMPASSABLE_TERRAIN as _DEFAULT_IMPASSABLE,
    BASE_MAP_SIZE,
    BASE_TOWN_MIN_DISTANCE, TOWN_DISTANCE_GROWTH_PER_LEVEL,
    OBSTACLE_DENSITY_CAP, OBSTACLE_DENSITY_PER_LEVEL, OBSTACLE_START_LEVEL,
    CHUNK_SIZE, MAX_SETTLEMENTS, SETTLEMENTS_PER_EXPEDITIONS,
)
from src.worlds.base import WorldTerrain as _WT

_ZONE_TYPES = ('rural', 'suburban', 'industrial', 'downtown', 'wilderness')
_DEFAULT_TERRAIN_ORDER = _WT.__dataclass_fields__['generator_terrain_order'].default


class MapGenerator:
    def __init__(self, game, variant="v1"):
        self.g = game
        self.variant = variant

    # Phase F: terrain vocabulary is world-owned. Fall back to the
    # default world's tables for a world that doesn't set `terrain`.
    @property
    def _impassable(self):
        t = getattr(self.g.world, "terrain", None)
        return t.impassable if t is not None else _DEFAULT_IMPASSABLE

    @property
    def _terrain_order(self):
        t = getattr(self.g.world, "terrain", None)
        return list(t.generator_terrain_order) if t is not None else list(_DEFAULT_TERRAIN_ORDER)

    @property
    def _settlement_glyphs(self):
        """(centre, *feature letters) - world-owned. The Wake is a ship,
        not a valley town, so it re-letters the block."""
        t = getattr(self.g.world, "terrain", None)
        g = getattr(t, "settlement_glyphs", None) if t is not None else None
        return tuple(g) if g else ('T', 'H', 'R', 'S', 'B')

    # ---- zones / terrain -------------------------------------------

    def _zone_for_terrain(self, terrain):
        rng = self.g.rng
        if terrain in ('forest', 'swamp', 'water'):
            return rng.choices(('wilderness', 'rural'), weights=(0.8, 0.2))[0]
        if terrain == 'building':
            return rng.choices(
                ('suburban', 'downtown', 'industrial'), weights=(0.45, 0.3, 0.25))[0]
        return rng.choices(('rural', 'suburban', 'wilderness'), weights=(0.55, 0.25, 0.2))[0]

    def _pick_terrain(self, base_terrain, obstacle_density):
        rng = self.g.rng
        if obstacle_density > 0 and rng.random() < obstacle_density:
            return rng.choice(['mountain', 'river'])
        return base_terrain

    # ---- spawn / settlements -------------------------------------

    def _transit_layout(self):
        """World opts into a traverse: spawn on one side wall, the way
        out on the opposite one (WorldManifest.map_transit). Off by
        default - the historical random-interior spawn is unchanged."""
        m = getattr(self.g.world, "manifest", None)
        return bool(m is not None and getattr(m, "map_transit", False))

    def _transit_spawn(self):
        """Wake against the middle of one end wall. Records the side on
        `game._transit_side` so the escape pass (src/escape.py) carves
        the way out in the OPPOSITE wall, roughly level. One rng.choice
        + one rng.shuffle - only reached when a world opts in, so no
        other world's RNG stream moves."""
        g = self.g
        side = g.rng.choice(('west', 'east'))
        x = 1 if side == 'west' else g.map_w - 2
        band = list(range(g.map_h // 4, g.map_h - g.map_h // 4)) or [g.map_h // 2]
        g.rng.shuffle(band)
        y = next((yy for yy in band
                  if g.map[yy][x]['terrain'] not in self._impassable), None)
        if y is None:
            y = g.map_h // 2
            g.map[y][x] = {'terrain': 'plain', 'zone': 'wilderness',
                           'content': '-', 'explored': False}
        g._transit_side = side
        g._transit_spawn_y = y
        return (x, y)

    def _pick_random_walkable_tile(self):
        g = self.g
        margin = 3 if g.map_size >= 10 else 1
        lo = margin
        hix, hiy = g.map_w - 1 - margin, g.map_h - 1 - margin
        good_terrain = ('plain', 'building', 'forest')

        best = None
        for _ in range(300):
            x = g.rng.randint(0, g.map_w - 1)
            y = g.rng.randint(0, g.map_h - 1)
            terrain = g.map[y][x]['terrain']
            if terrain in self._impassable:
                continue
            interior = lo <= x <= hix and lo <= y <= hiy
            if interior and terrain in good_terrain:
                return (x, y)
            if best is None or (interior and g.map[best[1]][best[0]]['terrain'] not in good_terrain):
                best = (x, y)
        return best if best is not None else (g.map_w // 2, g.map_h // 2)

    def _pick_town_position(self, town_size, spawn, min_distance):
        g = self.g
        max_x = max(0, g.map_w - town_size)
        max_y = max(0, g.map_h - town_size)

        def center_of(top_left):
            return (top_left[0] + town_size // 2, top_left[1] + town_size // 2)

        def distance_from_spawn(top_left):
            cx, cy = center_of(top_left)
            return abs(cx - spawn[0]) + abs(cy - spawn[1])

        for _ in range(200):
            candidate = (
                g.rng.randint(0, max_x),
                g.rng.randint(0, max_y),
            )
            if distance_from_spawn(candidate) >= min_distance:
                return candidate

        corners = [
            (0, 0), (0, max_y), (max_x, 0), (max_x, max_y),
        ]
        return max(corners, key=distance_from_spawn)

    def _generate_settlement(self, top_left, size, is_real):
        g = self.g
        _glyphs = self._settlement_glyphs
        centre_glyph, town_features = _glyphs[0], list(_glyphs[1:])
        cx = top_left[0] + size // 2
        cy = top_left[1] + size // 2
        max_dist = max(1, size // 2)

        for y in range(top_left[1], top_left[1] + size):
            for x in range(top_left[0], top_left[0] + size):
                if not (0 <= x < g.map_w and 0 <= y < g.map_h):
                    continue

                dist = abs(x - cx) + abs(y - cy)

                if dist > max_dist and g.rng.random() < 0.6:
                    continue

                is_center = is_real and (x, y) == (cx, cy)
                feature = centre_glyph if is_center else g.rng.choice(town_features)
                district = (
                    "downtown" if dist <= max_dist // 2
                    else "commercial" if dist <= max_dist
                    else "residential"
                )
                g.map[y][x] = {
                    'terrain': 'town', 'content': feature,
                    'explored': False, 'district': district,
                }

        return (cx, cy) if is_real else None

    # ---- boundary / reachability --------------------------------

    def force_boundary_ring(self):
        g = self.g
        lx, ly = g.map_w - 1, g.map_h - 1
        for i in range(max(g.map_w, g.map_h)):
            edges = []
            if i < g.map_w:
                edges += [(i, 0), (i, ly)]
            if i < g.map_h:
                edges += [(0, i), (lx, i)]
            for (bx, by) in edges:
                cell = g.map[by][bx]
                if isinstance(cell, dict):
                    cell['terrain'] = 'mountain'
                    cell['content'] = '-'
                    cell.setdefault('zone', 'wilderness')
                else:
                    g.map[by][bx] = {'terrain': 'mountain', 'content': '-',
                                     'zone': 'wilderness', 'explored': False}

    def bfs_reachable(self, start, goal):
        g = self.g
        if start == goal:
            return True
        visited = {start}
        queue = deque([start])
        while queue:
            x, y = queue.popleft()
            for dx, dy in ((0, -1), (0, 1), (1, 0), (-1, 0)):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < g.map_w and 0 <= ny < g.map_h):
                    continue
                if (nx, ny) in visited:
                    continue
                cell = g.map[ny][nx]
                terrain = cell.get('terrain') if isinstance(cell, dict) else None
                if terrain in self._impassable:
                    continue
                if (nx, ny) == goal:
                    return True
                visited.add((nx, ny))
                queue.append((nx, ny))
        return False

    def _carve_path(self, spawn, town_center):
        g = self.g
        x, y = spawn
        tx, ty = town_center
        path = []

        step_x = 1 if tx > x else -1
        while x != tx:
            x += step_x
            path.append((x, y))

        step_y = 1 if ty > y else -1
        while y != ty:
            y += step_y
            path.append((x, y))

        for px, py in path:
            if (px, py) in (spawn, town_center):
                continue
            cell = g.map[py][px]
            if isinstance(cell, dict) and cell.get('terrain') in self._impassable:
                cell['terrain'] = 'plain'

    def ensure_reachable(self, spawn, town_center):
        if self.bfs_reachable(spawn, town_center):
            return
        self._carve_path(spawn, town_center)
        if not self.bfs_reachable(spawn, town_center):
            raise RuntimeError(
                "generate_map(): spawn-to-town-center reachability "
                "could not be guaranteed after carving a path"
            )


    # ---- landscape variant: terrain mass + a real river ---------
    #   docs/MAP_REALISM_SPEC.md problems 2 + 3. Gated on
    #   variant == "landscape"; v1 never calls any of this.

    def _boundary_band(self, thickness=2):
        """A mountain BAND, not a 1-tile ring - the valley wall has
        depth. Thicker at the corners."""
        g = self.g
        w, h = g.map_w, g.map_h
        for y in range(h):
            for x in range(w):
                edge = min(x, y, w - 1 - x, h - 1 - y)
                corner = (min(x, w - 1 - x) < thickness
                          and min(y, h - 1 - y) < thickness)
                if edge < thickness or (corner and edge < thickness + 1):
                    g.map[y][x] = {'terrain': 'mountain', 'content': '-',
                                   'zone': 'wilderness', 'explored': False}

    def _mountain_blobs(self, count=None):
        """Interior mountains as connected masses (seed + grow), not the
        singletons `_pick_terrain` scatters. A mountain outweighs a
        house."""
        g = self.g
        rng = g.rng
        w, h = g.map_w, g.map_h
        n = count if count is not None else max(1, (w * h) // 260)
        for _ in range(n):
            sx = rng.randint(3, w - 4)
            sy = rng.randint(3, h - 4)
            size = rng.randint(5, 11)
            frontier = [(sx, sy)]
            grown = 0
            while frontier and grown < size:
                cx, cy = frontier.pop(rng.randrange(len(frontier)))
                if not (2 <= cx < w - 2 and 2 <= cy < h - 2):
                    continue
                cell = g.map[cy][cx]
                if isinstance(cell, dict) and cell.get('terrain') == 'town':
                    continue
                g.map[cy][cx] = {'terrain': 'mountain', 'content': '-',
                                 'zone': 'wilderness', 'explored': False}
                grown += 1
                for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                    if rng.random() < 0.55:
                        frontier.append((cx + dx, cy + dy))

    def _river_with_bridges(self):
        """One connected river from edge to edge - a genuine boundary
        the required circuit may have to cross - plus 2 bridges so it
        never fully seals a region off (docs/MAP_REALISM_SPEC 2b + 3a)."""
        g = self.g
        rng = g.rng
        w, h = g.map_w, g.map_h
        # a mostly-vertical river: start on the top interior edge, walk
        # to the bottom, meandering.
        x = rng.randint(w // 4, 3 * w // 4)
        path = []
        for y in range(1, h - 1):
            for wx in (x, x + 1) if rng.random() < 0.5 else (x,):
                if 1 <= wx < w - 1:
                    cell = g.map[y][wx]
                    if isinstance(cell, dict) and cell.get('terrain') != 'town':
                        cell['terrain'] = 'river'
                        cell['content'] = '-'
                        path.append((wx, y))
            x += rng.choice((-1, 0, 0, 1))
            x = max(2, min(w - 3, x))
        # bridges: 2 river tiles, spaced, turned passable
        if len(path) >= 6:
            for frac in (0.33, 0.72):
                bx, by = path[int(len(path) * frac)]
                g.map[by][bx] = {'terrain': 'bridge', 'content': '#',
                                 'zone': 'wilderness', 'explored': False}

    def _landscape_terrain(self):
        self._boundary_band(thickness=2)
        self._mountain_blobs()
        self._river_with_bridges()

    # ---- v2: irregular valley mask (C.3 experiment) -------------

    def _grow_valley_mask(self):
        """C.3 v2: instead of a rectangular playable field, seed-and-grow
        one irregular connected valley region across the interior and
        mountain-fill the rest. The 34x34 array storage is unchanged;
        the *shape* is not a box any more. Deterministic on g.rng.

        Preserves: one connected region, a boundary of mountain,
        terrain vocabulary. Intentionally changes: the map's outline
        and internal shape (peninsulas, basins, lobes).
        """
        g = self.g
        n = g.map_size
        rng = g.rng
        interior = [(x, y) for y in range(1, n - 1) for x in range(1, n - 1)]
        if len(interior) < 16:
            return  # too small to carve a shape - leave it a box

        # target ~55-75% of the interior stays valley, with an absolute
        # floor so the region always holds a full mystery (>=3 sites +
        # a trek). Below the floor v2 would spit out degenerate
        # reach-the-town maps far more often than v1.
        target = max(
            int(len(interior) * rng.uniform(0.55, 0.75)),
            min(len(interior) - 20, 300),
        )

        # 1-3 growth seeds so a valley can be single-lobed or two-lobed
        seeds = rng.randint(1, 3)
        frontier = []
        valley = set()
        for _ in range(seeds):
            sx = rng.randint(n // 4, 3 * n // 4)
            sy = rng.randint(n // 4, 3 * n // 4)
            if (sx, sy) not in valley:
                valley.add((sx, sy))
                frontier.append((sx, sy))

        # random-frontier flood: pick a random frontier cell, add a
        # random passable neighbour. Gives blobby, organic outlines.
        while frontier and len(valley) < target:
            i = rng.randrange(len(frontier))
            x, y = frontier[i]
            nbrs = [(x + dx, y + dy) for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0))
                    if 1 <= x + dx < n - 1 and 1 <= y + dy < n - 1
                    and (x + dx, y + dy) not in valley]
            if not nbrs:
                frontier.pop(i)
                continue
            nb = rng.choice(nbrs)
            valley.add(nb)
            frontier.append(nb)

        # keep only the LARGEST connected component of the grown region
        # so the valley is always ONE place - no isolated pockets the
        # player can see but never reach. (Multi-seed growth can leave
        # lobes that never joined up.)
        remaining = set(valley)
        best = set()
        while remaining:
            root = next(iter(remaining))
            comp = {root}
            stack = [root]
            while stack:
                cx, cy = stack.pop()
                for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                    nb = (cx + dx, cy + dy)
                    if nb in remaining and nb not in comp:
                        comp.add(nb)
                        stack.append(nb)
            remaining -= comp
            if len(comp) > len(best):
                best = comp
        valley = best

        # everything interior not in the (single, connected) valley
        # becomes mountain.
        for (x, y) in interior:
            if (x, y) not in valley:
                cell = g.map[y][x]
                if isinstance(cell, dict):
                    cell['terrain'] = 'mountain'
                    cell['content'] = '-'

        # final pass: obstacle rivers/mountains from the per-tile
        # overlay can still split the valley. Keep the largest
        # PASSABLE component and mountain-fill any other passable
        # islands, so the realised map is one connected place.
        def _pass(x, y):
            c = g.map[y][x]
            return isinstance(c, dict) and c.get('terrain') not in ('mountain', 'river')

        passable = {(x, y) for (x, y) in interior if _pass(x, y)}
        seen_all = set()
        biggest = set()
        for cell0 in passable:
            if cell0 in seen_all:
                continue
            comp = {cell0}
            stack = [cell0]
            while stack:
                cx, cy = stack.pop()
                for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                    nb = (cx + dx, cy + dy)
                    if nb in passable and nb not in comp:
                        comp.add(nb)
                        stack.append(nb)
            seen_all |= comp
            if len(comp) > len(biggest):
                biggest = comp
        for (x, y) in passable - biggest:
            g.map[y][x]['terrain'] = 'mountain'
            g.map[y][x]['content'] = '-'

    # ---- the base-map pipeline ----------------------------------

    def generate(self):
        """Terrain -> boundary -> spawn -> settlements. Returns the real
        town centre, or None. RNG order identical to the pre-C.1
        generate_map()."""
        g = self.g
        terrain_types = self._terrain_order

        _archetypes = g.world.map_archetypes
        # The roll is always consumed (RNG order unchanged for every
        # world). A world with a spatial spine then overrides the result
        # with its section's archetype - so the terrain reads as one
        # continuous journey, not a fresh random room each expedition.
        # The Silence has no spine: the roll stands, byte-identical.
        g.map_archetype = g.rng.choice(list(_archetypes))
        from src.sections import section_archetype_for
        _forced = section_archetype_for(g.expeditions_completed, g.world)
        if _forced is not None and _forced in _archetypes:
            g.map_archetype = _forced
        _arch = _archetypes[g.map_archetype]

        obstacle_density = min(
            OBSTACLE_DENSITY_CAP,
            max(0, g.expeditions_completed - OBSTACLE_START_LEVEL) * OBSTACLE_DENSITY_PER_LEVEL,
        )

        chunk_terrain = {}
        for cy in range(0, g.map_h, CHUNK_SIZE):
            for cx in range(0, g.map_w, CHUNK_SIZE):
                neighbor_key = None
                if (cx, cy - CHUNK_SIZE) in chunk_terrain:
                    neighbor_key = (cx, cy - CHUNK_SIZE)
                elif (cx - CHUNK_SIZE, cy) in chunk_terrain:
                    neighbor_key = (cx - CHUNK_SIZE, cy)

                if neighbor_key is not None and g.rng.random() < 0.6:
                    chunk_terrain[(cx, cy)] = chunk_terrain[neighbor_key]
                else:
                    chunk_terrain[(cx, cy)] = g.rng.choices(
                        terrain_types, weights=_arch['weights'])[0]

        for _terr, _frac in (('building', 0.22), ('water', 0.25), ('swamp', 0.15)):
            _chunks = [k for k, v in chunk_terrain.items() if v == _terr]
            _cap = max(1, int(len(chunk_terrain) * _frac))
            if len(_chunks) > _cap:
                _fallback = max(
                    ('forest', 'plain'),
                    key=lambda t: _arch['weights'][terrain_types.index(t)],
                )
                g.rng.shuffle(_chunks)
                for k in _chunks[_cap:]:
                    chunk_terrain[k] = _fallback

        chunk_zone = {}
        for cy in range(0, g.map_h, CHUNK_SIZE):
            for cx in range(0, g.map_w, CHUNK_SIZE):
                nb = None
                if (cx, cy - CHUNK_SIZE) in chunk_zone:
                    nb = (cx, cy - CHUNK_SIZE)
                elif (cx - CHUNK_SIZE, cy) in chunk_zone:
                    nb = (cx - CHUNK_SIZE, cy)
                if nb is not None and g.rng.random() < 0.55:
                    chunk_zone[(cx, cy)] = chunk_zone[nb]
                else:
                    chunk_zone[(cx, cy)] = self._zone_for_terrain(chunk_terrain[(cx, cy)])

        g.map = [
            [
                {
                    'terrain': self._pick_terrain(
                        chunk_terrain[(x - x % CHUNK_SIZE, y - y % CHUNK_SIZE)],
                        obstacle_density,
                    ),
                    'zone': chunk_zone[(x - x % CHUNK_SIZE, y - y % CHUNK_SIZE)],
                    'content': '-',
                    'explored': False,
                }
                for x in range(g.map_w)
            ]
            for y in range(g.map_h)
        ]

        self.force_boundary_ring()

        # C.3 v2: carve the box into an irregular valley before anything
        # is placed on it. v1 skips this entirely (frozen).
        if self.variant == "v2":
            self._grow_valley_mask()
        # landscape: a mountain BAND, interior mountain blobs, and one
        # connected river with bridges (MAP_REALISM_SPEC 2 + 3). Placed
        # before the settlements so a settlement can't be split by the
        # river without a bridge (ensure_reachable + the MapGraph
        # guarantee back this up).
        elif self.variant == "landscape":
            self._landscape_terrain()

        g._transit_side = None
        if self._transit_layout():
            spawn = self._transit_spawn()
        else:
            spawn = self._pick_random_walkable_tile()
        g.current_position = spawn
        g.map[spawn[1]][spawn[0]]['content'] = 'P'

        town_size = min(5, g.map_size)
        min_distance = min(
            g.map_size - 2,
            BASE_TOWN_MIN_DISTANCE + g.expeditions_completed * TOWN_DISTANCE_GROWTH_PER_LEVEL,
        )
        num_settlements = min(
            MAX_SETTLEMENTS,
            1 + g.expeditions_completed // SETTLEMENTS_PER_EXPEDITIONS,
        )

        # --- C.3.2a-5 lever A/B (docs/PHASE_C3_2_5_LEVER_MATRIX.md) ---
        # measurement-only, all default off; baseline byte-identical.
        _cap = getattr(g, "_lever_cap_town_dist", None)          # lever 3
        if _cap is not None:
            min_distance = min(min_distance, _cap)
        if getattr(g, "_lever_settlements_by_area", False):      # lever 1
            _base_area = BASE_MAP_SIZE * BASE_MAP_SIZE
            num_settlements = max(
                1, min(8, round(g.map_size * g.map_size / _base_area)))
        # -----------------------------------------------------------

        real_settlement_index = g.rng.randrange(num_settlements)

        settlement_order = [i for i in range(num_settlements) if i != real_settlement_index]
        settlement_order.append(real_settlement_index)

        town_center = None
        for i in settlement_order:
            top_left = self._pick_town_position(town_size, spawn, min_distance)
            center = self._generate_settlement(top_left, town_size, is_real=(i == real_settlement_index))
            if center is not None:
                town_center = center

        self.force_boundary_ring()

        if town_center is not None and (
            town_center[0] in (0, g.map_w - 1)
            or town_center[1] in (0, g.map_h - 1)
        ):
            tx = min(max(town_center[0], 1), g.map_w - 2)
            ty = min(max(town_center[1], 1), g.map_h - 2)
            g.map[ty][tx] = {'terrain': 'town', 'content': self._settlement_glyphs[0],
                             'explored': False}
            town_center = (tx, ty)

        g.map_archetype_blurb = _arch['blurb']
        return town_center
