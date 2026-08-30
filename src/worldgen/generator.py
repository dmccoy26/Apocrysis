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
    IMPASSABLE_TERRAIN,
    BASE_MAP_SIZE,
    BASE_TOWN_MIN_DISTANCE, TOWN_DISTANCE_GROWTH_PER_LEVEL,
    OBSTACLE_DENSITY_CAP, OBSTACLE_DENSITY_PER_LEVEL, OBSTACLE_START_LEVEL,
    CHUNK_SIZE, MAX_SETTLEMENTS, SETTLEMENTS_PER_EXPEDITIONS,
)

_ZONE_TYPES = ('rural', 'suburban', 'industrial', 'downtown', 'wilderness')


class MapGenerator:
    def __init__(self, game, variant="v1"):
        self.g = game
        self.variant = variant

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

    def _pick_random_walkable_tile(self):
        g = self.g
        margin = 3 if g.map_size >= 10 else 1
        lo, hi = margin, g.map_size - 1 - margin
        good_terrain = ('plain', 'building', 'forest')

        best = None
        for _ in range(300):
            x = g.rng.randint(0, g.map_size - 1)
            y = g.rng.randint(0, g.map_size - 1)
            terrain = g.map[y][x]['terrain']
            if terrain in IMPASSABLE_TERRAIN:
                continue
            interior = lo <= x <= hi and lo <= y <= hi
            if interior and terrain in good_terrain:
                return (x, y)
            if best is None or (interior and g.map[best[1]][best[0]]['terrain'] not in good_terrain):
                best = (x, y)
        return best if best is not None else (g.map_size // 2, g.map_size // 2)

    def _pick_town_position(self, town_size, spawn, min_distance):
        g = self.g
        max_start = max(0, g.map_size - town_size)

        def center_of(top_left):
            return (top_left[0] + town_size // 2, top_left[1] + town_size // 2)

        def distance_from_spawn(top_left):
            cx, cy = center_of(top_left)
            return abs(cx - spawn[0]) + abs(cy - spawn[1])

        for _ in range(200):
            candidate = (
                g.rng.randint(0, max_start),
                g.rng.randint(0, max_start),
            )
            if distance_from_spawn(candidate) >= min_distance:
                return candidate

        corners = [
            (0, 0), (0, max_start), (max_start, 0), (max_start, max_start),
        ]
        return max(corners, key=distance_from_spawn)

    def _generate_settlement(self, top_left, size, is_real):
        g = self.g
        town_features = ['H', 'R', 'S', 'B']
        cx = top_left[0] + size // 2
        cy = top_left[1] + size // 2
        max_dist = max(1, size // 2)

        for y in range(top_left[1], top_left[1] + size):
            for x in range(top_left[0], top_left[0] + size):
                if not (0 <= x < g.map_size and 0 <= y < g.map_size):
                    continue

                dist = abs(x - cx) + abs(y - cy)

                if dist > max_dist and g.rng.random() < 0.6:
                    continue

                is_center = is_real and (x, y) == (cx, cy)
                feature = 'T' if is_center else g.rng.choice(town_features)
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
        last = g.map_size - 1
        for i in range(g.map_size):
            for (bx, by) in ((i, 0), (i, last), (0, i), (last, i)):
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
                if not (0 <= nx < g.map_size and 0 <= ny < g.map_size):
                    continue
                if (nx, ny) in visited:
                    continue
                cell = g.map[ny][nx]
                terrain = cell.get('terrain') if isinstance(cell, dict) else None
                if terrain in IMPASSABLE_TERRAIN:
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
            if isinstance(cell, dict) and cell.get('terrain') in IMPASSABLE_TERRAIN:
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
        terrain_types = ['forest', 'building', 'water', 'plain', 'swamp']

        _archetypes = g.world.map_archetypes
        g.map_archetype = g.rng.choice(list(_archetypes))
        _arch = _archetypes[g.map_archetype]

        obstacle_density = min(
            OBSTACLE_DENSITY_CAP,
            max(0, g.expeditions_completed - OBSTACLE_START_LEVEL) * OBSTACLE_DENSITY_PER_LEVEL,
        )

        chunk_terrain = {}
        for cy in range(0, g.map_size, CHUNK_SIZE):
            for cx in range(0, g.map_size, CHUNK_SIZE):
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
        for cy in range(0, g.map_size, CHUNK_SIZE):
            for cx in range(0, g.map_size, CHUNK_SIZE):
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
                for x in range(g.map_size)
            ]
            for y in range(g.map_size)
        ]

        self.force_boundary_ring()

        # C.3 v2: carve the box into an irregular valley before anything
        # is placed on it. v1 skips this entirely (frozen).
        if self.variant == "v2":
            self._grow_valley_mask()

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
            town_center[0] in (0, g.map_size - 1)
            or town_center[1] in (0, g.map_size - 1)
        ):
            tx = min(max(town_center[0], 1), g.map_size - 2)
            ty = min(max(town_center[1], 1), g.map_size - 2)
            g.map[ty][tx] = {'terrain': 'town', 'content': 'T', 'explored': False}
            town_center = (tx, ty)

        g.map_archetype_blurb = _arch['blurb']
        return town_center
