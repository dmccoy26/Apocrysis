# Auto-extracted from the original monolithic apocrysis.py during
# the src/ restructuring - see README.md for the project layout.
#
# v3 SPRINT step 2: map generation redesign - map size/town distance/
# obstacle density all scale with the player's level (self.level, set
# by game.py's __init__ before generate_map() runs - see the
# governing invariant in the sprint plan: this only ever happens at
# NEW-game creation, never a mid-game resize). Uses self.rng (a
# per-instance, seedable random.Random - game.py's __init__) instead
# of the bare random module, so map generation is reproducible in
# tests.

from collections import deque

import random

from src.constants import (
    BOLD, GREEN, RESET,
    BASE_TOWN_MIN_DISTANCE, TOWN_DISTANCE_GROWTH_PER_LEVEL,
    IMPASSABLE_TERRAIN,
    OBSTACLE_DENSITY_CAP, OBSTACLE_DENSITY_PER_LEVEL, OBSTACLE_START_LEVEL,
    TERRAIN_MOVE_MINUTES, LOOT_WEAPON_TABLE,
)
from src.items import MeleeWeapon, RangedWeapon
from src.zombies import (
    Zombie, FreshZombie, RegularZombie, HeavyZombie,
    SwiftZombie, ToxicZombie, ArmoredZombie,
)


class WorldMixin:

    # --------------------------------------------------
    # Map Generation
    # --------------------------------------------------

    def generate_map(self):
        terrain_types = ['forest', 'building', 'water', 'plain']

        obstacle_density = min(
            OBSTACLE_DENSITY_CAP,
            max(0, self.level - OBSTACLE_START_LEVEL) * OBSTACLE_DENSITY_PER_LEVEL,
        )

        self.map = [
            [
                {
                    'terrain': self._pick_terrain(terrain_types, obstacle_density),
                    'content': '-',
                    'explored': False,
                }
                for _ in range(self.map_size)
            ]
            for _ in range(self.map_size)
        ]

        # Random player spawn (v3 #6) - was always the map center.
        spawn = self._pick_random_walkable_tile()
        self.current_position = spawn
        self.map[spawn[1]][spawn[0]]['content'] = 'P'

        # Town placement, distance-scaled from spawn and level (#5).
        town_size = min(5, self.map_size)
        min_distance = min(
            self.map_size - 2,
            BASE_TOWN_MIN_DISTANCE + (self.level - 1) * TOWN_DISTANCE_GROWTH_PER_LEVEL,
        )
        town_top_left = self._pick_town_position(town_size, spawn, min_distance)
        town_center = (
            town_top_left[0] + town_size // 2,
            town_top_left[1] + town_size // 2,
        )

        # Exactly one town center (#2 - the multiple-'T' bug fix):
        # every OTHER town tile draws from H/R/S/B only.
        town_features = ['H', 'R', 'S', 'B']
        for y in range(town_top_left[1], town_top_left[1] + town_size):
            for x in range(town_top_left[0], town_top_left[0] + town_size):
                feature = 'T' if (x, y) == town_center else self.rng.choice(town_features)
                self.map[y][x] = {'terrain': 'town', 'content': feature, 'explored': False}

        # Connectivity guarantee (#7) - a "harder" map with more
        # obstacles must never generate an unreachable town.
        self._ensure_reachable(spawn, town_center)

        # Zombie placement (10% of tiles) - unchanged shape, now via
        # self.rng and skipping impassable/town/spawn tiles.
        total_tiles = self.map_size ** 2
        num_zombies = int(total_tiles * 0.10)

        placed_zombies = 0
        attempts = 0
        max_attempts = max(200, num_zombies * 20)

        while placed_zombies < num_zombies and attempts < max_attempts:
            attempts += 1
            x = self.rng.randint(0, self.map_size - 1)
            y = self.rng.randint(0, self.map_size - 1)
            cell = self.map[y][x]
            if (
                isinstance(cell, dict)
                and cell.get('terrain') not in IMPASSABLE_TERRAIN
                and cell.get('terrain') != 'town'
                and (x, y) != spawn
            ):
                self.map[y][x] = self._select_zombie_for_encounter()
                placed_zombies += 1

        return self.map

    def _pick_terrain(self, terrain_types, obstacle_density):
        if obstacle_density > 0 and self.rng.random() < obstacle_density:
            return self.rng.choice(['mountain', 'river'])
        return self.rng.choice(terrain_types)

    def _pick_random_walkable_tile(self):
        while True:
            x = self.rng.randint(0, self.map_size - 1)
            y = self.rng.randint(0, self.map_size - 1)
            if self.map[y][x]['terrain'] not in IMPASSABLE_TERRAIN:
                return (x, y)

    def _pick_town_position(self, town_size, spawn, min_distance):
        max_start = max(0, self.map_size - town_size)

        def center_of(top_left):
            return (top_left[0] + town_size // 2, top_left[1] + town_size // 2)

        def distance_from_spawn(top_left):
            cx, cy = center_of(top_left)
            return abs(cx - spawn[0]) + abs(cy - spawn[1])

        for _ in range(200):
            candidate = (
                self.rng.randint(0, max_start),
                self.rng.randint(0, max_start),
            )
            if distance_from_spawn(candidate) >= min_distance:
                return candidate

        # Map too small to satisfy min_distance anywhere - fall back
        # to whichever map corner is genuinely farthest from spawn,
        # not another random guess.
        corners = [
            (0, 0), (0, max_start), (max_start, 0), (max_start, max_start),
        ]
        return max(corners, key=distance_from_spawn)

    def _bfs_reachable(self, start, goal):
        if start == goal:
            return True

        visited = {start}
        queue = deque([start])

        while queue:
            x, y = queue.popleft()
            for dx, dy in ((0, -1), (0, 1), (1, 0), (-1, 0)):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < self.map_size and 0 <= ny < self.map_size):
                    continue
                if (nx, ny) in visited:
                    continue
                cell = self.map[ny][nx]
                terrain = cell.get('terrain') if isinstance(cell, dict) else None
                if terrain in IMPASSABLE_TERRAIN:
                    continue
                if (nx, ny) == goal:
                    return True
                visited.add((nx, ny))
                queue.append((nx, ny))

        return False

    def _carve_path(self, spawn, town_center):
        # Walks an L-shaped route (x-leg then y-leg) between spawn and
        # town_center, clearing only the obstacle cells it crosses -
        # explicitly never touching the spawn or town-center tiles
        # themselves, even though neither would ever be impassable by
        # construction (spawn is chosen walkable; town tiles are never
        # 'mountain'/'river').
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
            cell = self.map[py][px]
            if isinstance(cell, dict) and cell.get('terrain') in IMPASSABLE_TERRAIN:
                cell['terrain'] = 'plain'

    def _ensure_reachable(self, spawn, town_center):
        if self._bfs_reachable(spawn, town_center):
            return

        self._carve_path(spawn, town_center)

        if not self._bfs_reachable(spawn, town_center):
            # Treated as a real generation bug (per the sprint plan's
            # governing invariant), not a map silently shipped
            # unreachable - the L-carve should always connect a
            # straight route, so reaching this means something else
            # is wrong.
            raise RuntimeError(
                "generate_map(): spawn-to-town-center reachability "
                "could not be guaranteed after carving a path"
            )

    # v3 SPRINT step 3: base (health, attack) per zombie type, at
    # difficulty_factor == 1.0 - scaled below the same way every type
    # already was, just table-driven instead of one elif per type
    # (6 types would otherwise mean 6 near-identical branches).
    _ZOMBIE_BASE_STATS = {
        FreshZombie: (30, 5),
        RegularZombie: (50, 10),
        HeavyZombie: (100, 20),
        SwiftZombie: (25, 15),
        ToxicZombie: (40, 8),
        ArmoredZombie: (120, 15),
    }

    def _select_zombie_for_encounter(self):
        # Difficulty scaling based on day count
        difficulty_factor = max(1.0, self.day * 0.2)

        # Adjust weights towards harder/more varied zombies as days
        # progress - Fresh/Regular/Heavy, Swift, Toxic, Armored.
        if self.day <= 5:
            weights = [0.55, 0.20, 0.03, 0.15, 0.05, 0.02]
        elif self.day <= 15:
            weights = [0.25, 0.25, 0.10, 0.20, 0.15, 0.05]
        else:
            weights = [0.10, 0.15, 0.25, 0.15, 0.15, 0.20]

        zombie_classes = list(self._ZOMBIE_BASE_STATS.keys())
        zombie_class = self.rng.choices(zombie_classes, weights=weights)[0]
        choice = zombie_class()

        base_health, base_attack = self._ZOMBIE_BASE_STATS[zombie_class]
        choice.health = int(base_health * difficulty_factor)
        choice.attack = max(1, int(base_attack * difficulty_factor))

        return choice

    # --------------------------------------------------
    # Movement
    # --------------------------------------------------

    def move_and_search(self, direction):
        directions = {"n": (0, -1), "s": (0, 1), "e": (1, 0), "w": (-1, 0)}
        dx, dy = directions.get(direction, (0, 0))
        new_x, new_y = self.current_position[0] + dx, self.current_position[1] + dy

        if not (0 <= new_x < self.map_size and 0 <= new_y < self.map_size):
            self.io.say("Can't move in that direction.")
            return

        destination = self.map[new_y][new_x]
        dest_terrain = destination.get('terrain') if isinstance(destination, dict) else None

        # Impassable terrain (v3 #7) - blocks movement instead of
        # being walked onto.
        if dest_terrain in ('mountain', 'river'):
            label = "mountain" if dest_terrain == 'mountain' else "river"
            self.io.say(f"You can't cross the {label} here.")
            return

        # Update the current position
        self.current_position = (new_x, new_y)
        self.visited.add(self.current_position)  # Mark the new position as visited

        # Per-move time cost is now terrain-dependent (v3 #11) rather
        # than a flat 15 minutes - see constants.py's
        # TERRAIN_MOVE_MINUTES.
        move_cost = TERRAIN_MOVE_MINUTES.get(dest_terrain, 15)
        self._update_time(move_cost)
        self._apply_decay()

        # Fatigue increases with movement
        self.fatigue = min(100, self.fatigue + 5)

        self.io.say(f"Moved {direction}.")

        # Check tile contents for placed zombies
        current_tile = self.map[self.current_position[1]][self.current_position[0]]

        if isinstance(current_tile, dict) and current_tile.get('content') == 'T':
            self.won = True
            self.io.say(f"\n{BOLD}{GREEN}You have reached the Town Center! The survivors welcome you home. You WIN!{RESET}\n")
            self.io.say(f"{BOLD}A grateful stash of supplies awaits you when you start your next game!{RESET}\n")
            # self.__class__, not a direct Apocrysis reference -
            # importing Apocrysis here would be circular (game.py
            # imports WorldMixin from this module). Equivalent at
            # runtime since self is always an Apocrysis instance.
            self.__class__.prize_for_next_game = True
            self._check_and_complete_goals("reach_town")
            return

        # Apply terrain-specific effects
        if isinstance(current_tile, dict):
            terrain = current_tile.get('terrain')

            if terrain == 'building':
                self.io.say("You enter a building. It's a safe zone.")
                heal_amount = self.rng.randint(5, 10)
                self.health = min(100, max(0, self.health + heal_amount))
                fatigue_recovery = max(0, self.wisdom // 4)
                self.fatigue = max(0, self.fatigue - fatigue_recovery - 5)
                self.io.say(f"Restored {heal_amount} health and recovered some fatigue.")

            elif terrain == 'water':
                self.io.say("You wade through water. Movement is difficult.")
                self.fatigue = min(100, self.fatigue + 10) # Extra fatigue penalty for slow movement
                if self.rng.random() < 0.2:
                    self.health -= 5
                    self.io.say("The cold water chills you. You lost some health.")

            elif terrain == 'forest':
                self.io.say("You move through dense forest.")

        encounter_chance = 0.5 if self.is_night else 0.3

        # Forest increases encounter rate
        if isinstance(current_tile, dict) and current_tile.get('terrain') == 'forest':
            encounter_chance = min(1.0, encounter_chance * 1.5)

        if isinstance(current_tile, Zombie):
            self.encounter_zombie(current_tile)
        elif self.rng.random() < encounter_chance:  # Chance encounter when moving around the map
            self.encounter_zombie()
        else:
            self.find_loot()

    def find_loot(self):
        # Intelligence increases chance of finding loot and better items
        find_chance = min(1.0, 0.2 + self.intelligence / 250)
        if random.random() < find_chance:
            loot_type = random.choice(["food", "water", "medicine", "ammo", "weapon"])

            # Higher intelligence increases chance of finding weapons over consumables
            if self.intelligence > 10 and random.random() < (self.intelligence / 100):
                loot_type = "weapon"

            self.io.say(f"You found {loot_type}!")
            self.award_xp(10)

            if loot_type == "weapon":
                # Real stat variance per name, and the correct weapon
                # type (melee vs ranged) - see LOOT_WEAPON_TABLE's own
                # comment in constants.py for the bug this replaced.
                new_weapon_name = random.choice(list(LOOT_WEAPON_TABLE.keys()))
                spec = LOOT_WEAPON_TABLE[new_weapon_name]
                if spec["type"] == "ranged":
                    new_weapon = RangedWeapon(
                        new_weapon_name, spec["damage"],
                        spec["max_ammo"], spec["durability"],
                    )
                else:
                    new_weapon = MeleeWeapon(
                        new_weapon_name, spec["damage"], spec["durability"],
                    )
                self.backpack.weapons.append(new_weapon)
                self.io.say(f"You obtained a {new_weapon.name}.")
            elif loot_type == "food":
                # Increase food in the backpack
                self.backpack.food += 1
                self.io.say("You found some food. Food stock increased.")
            elif loot_type == "water":
                # Increase water in the backpack
                self.backpack.water += 1
                self.io.say("You found some water. Water stock increased.")
            elif loot_type == "medicine":
                # Increase medicine in the backpack
                self.backpack.medicine += 1
                self.io.say("You found some medicine. Medicine stock increased.")
            elif loot_type == "ammo":
                # Increase ammo in the backpack to support ranged crafting recipes
                self.backpack.ammo += random.randint(1, 3)
                self.io.say("You found some ammo! Ammo stock increased.")
