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
    BOLD, GREEN, RESET, CAMPAIGN_LENGTH,
    BASE_TOWN_MIN_DISTANCE, TOWN_DISTANCE_GROWTH_PER_LEVEL,
    IMPASSABLE_TERRAIN,
    OBSTACLE_DENSITY_CAP, OBSTACLE_DENSITY_PER_LEVEL, OBSTACLE_START_LEVEL,
    MAX_DAY_DIFFICULTY_FACTOR, ELITE_MIN_EXPEDITION, ELITE_STAT_MULTIPLIER,
    TERRAIN_MOVE_MINUTES, LOOT_WEAPON_TABLE, ARMOR_TABLE,
    CHUNK_SIZE, MAX_SETTLEMENTS, SETTLEMENTS_PER_EXPEDITIONS,
)
from src.items import MeleeWeapon, RangedWeapon, Armor
from src.zombies import (
    Zombie, FreshZombie, RegularZombie, HeavyZombie,
    SwiftZombie, ToxicZombie, ArmoredZombie,
)


class WorldMixin:

    # --------------------------------------------------
    # Map Generation
    # --------------------------------------------------

    """Tier 6-9 expedition design summary (closes open questions):
    - Contiguous terrain biomes via chunk clustering instead of per-tile rolls.
    - Slow/exhausting swamp terrain type, with waders mitigating water/swamp slowdown.
    - Location-aware resting in buildings (heals/fatigue recovery).
    - repair_kit crafting recipe (level 8+) for sustained gear upkeep.
    - Diagnosed real cause of the tier 6-9 wall: weapon/armor power plateaus while zombie composition keeps escalating (see _select_zombie_for_encounter()).

    Explicitly out of scope for this pass: per-settlement discovery so decoy settlements genuinely differ from the real objective (currently settlement_explored is one global flag set by entering ANY settlement). That remains a separate, not-yet-implemented change.
    """
    def generate_map(self):
        terrain_types = ['forest', 'building', 'water', 'plain', 'swamp']

        obstacle_density = min(
            OBSTACLE_DENSITY_CAP,
            max(0, self.expeditions_completed - OBSTACLE_START_LEVEL) * OBSTACLE_DENSITY_PER_LEVEL,
        )

        # Chunk-based terrain generation investigation: one base
        # terrain rolls per CHUNK_SIZE x CHUNK_SIZE block instead of
        # independently per tile, so forests/plains/etc form
        # contiguous regions instead of a checkerboard of unrelated
        # single-tile rolls. Obstacle terrain (mountain/river) is
        # still an overlay rolled per-tile inside any chunk via
        # _pick_terrain() - it represents a hazard cutting across a
        # region, not a region type of its own.
        chunk_terrain = {}
        for cy in range(0, self.map_size, CHUNK_SIZE):
            for cx in range(0, self.map_size, CHUNK_SIZE):
                # spawn-local terrain variety was requested as a separate feature 
                # (a lighter, spawn-scoped version of biome clustering, giving each game's opening moves a recognizable local context - forest edge, riverside, near buildings, etc.) but is already satisfied by this same clustering logic - since spawn is picked from the already-clustered map, its immediate neighborhood naturally inherits whatever biome it landed in. Verified empirically across 5 seeds: 4/5 showed a single dominant terrain type filling the spawn's 5x5 neighborhood, each a different terrain. No separate spawn-context mechanism was needed.
                neighbor_key = None
                if (cx, cy - CHUNK_SIZE) in chunk_terrain:
                    neighbor_key = (cx, cy - CHUNK_SIZE)
                elif (cx - CHUNK_SIZE, cy) in chunk_terrain:
                    neighbor_key = (cx - CHUNK_SIZE, cy)

                if neighbor_key is not None and self.rng.random() < 0.6:
                    chunk_terrain[(cx, cy)] = chunk_terrain[neighbor_key]
                else:
                    chunk_terrain[(cx, cy)] = self.rng.choice(terrain_types)

        self.map = [
            [
                {
                    'terrain': self._pick_terrain(
                        chunk_terrain[(x - x % CHUNK_SIZE, y - y % CHUNK_SIZE)],
                        obstacle_density,
                    ),
                    'content': '-',
                    'explored': False,
                }
                for x in range(self.map_size)
            ]
            for y in range(self.map_size)
        ]

        # Random player spawn (v3 #6) - was always the map center.
        spawn = self._pick_random_walkable_tile()
        self.current_position = spawn
        self.map[spawn[1]][spawn[0]]['content'] = 'P'

        # Multiple-settlements investigation: 1-MAX_SETTLEMENTS
        # populated areas, more as expeditions_completed grows.
        # Exactly one (chosen at random, not always the first placed)
        # gets the real Town Center - the rest are decoys with no
        # win-triggering tile, just loot/exploration opportunities
        # (organic-settlement investigation covers each one's own
        # shape/district structure - see _generate_settlement()).
        # Known limitation: settlements are placed independently, each
        # only checked against SPAWN distance - with 2-3 on a small
        # map they can end up adjacent or slightly overlapping. Not a
        # correctness requirement the way spawn-to-real-Town-Center
        # reachability below is, so left as-is rather than adding a
        # full non-overlap placement search.
        town_size = min(5, self.map_size)
        min_distance = min(
            self.map_size - 2,
            BASE_TOWN_MIN_DISTANCE + self.expeditions_completed * TOWN_DISTANCE_GROWTH_PER_LEVEL,
        )
        num_settlements = min(
            MAX_SETTLEMENTS,
            1 + self.expeditions_completed // SETTLEMENTS_PER_EXPEDITIONS,
        )
        real_settlement_index = self.rng.randrange(num_settlements)

        # Real bug found live: with the real settlement placed in loop
        # order (not necessarily last), an overlapping DECOY placed
        # afterward could straight-up overwrite its 'T' tile with an
        # H/R/S/B letter, silently deleting the only win tile on the
        # map. Placing every decoy first and the real settlement last
        # guarantees its tiles (including 'T') always win any overlap.
        settlement_order = [i for i in range(num_settlements) if i != real_settlement_index]
        settlement_order.append(real_settlement_index)

        town_center = None
        for i in settlement_order:
            top_left = self._pick_town_position(town_size, spawn, min_distance)
            center = self._generate_settlement(top_left, town_size, is_real=(i == real_settlement_index))
            if center is not None:
                town_center = center

        # Connectivity guarantee (#7) - a "harder" map with more
        # obstacles must never generate an unreachable REAL Town
        # Center. Decoy settlements are best-effort only (see the
        # known-limitation note above) - never carved for.
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
                and (x, y) != spawn and abs(x - spawn[0]) + abs(y - spawn[1]) > 1
            ):
                self.map[y][x] = self._select_zombie_for_encounter()
                placed_zombies += 1

        return self.map

    def _generate_settlement(self, top_left, size, is_real):
        """
        Organic-settlement investigation: fills a size x size bounding
        box with an irregular (diamond-ish, not solid-square)
        boundary and per-tile district tags based on distance from
        the settlement's own center. Returns the town-center
        coordinate if is_real (the only settlement that gets a real
        'T' tile), else None.
        """
        town_features = ['H', 'R', 'S', 'B']
        cx = top_left[0] + size // 2
        cy = top_left[1] + size // 2
        max_dist = max(1, size // 2)

        for y in range(top_left[1], top_left[1] + size):
            for x in range(top_left[0], top_left[0] + size):
                if not (0 <= x < self.map_size and 0 <= y < self.map_size):
                    continue

                dist = abs(x - cx) + abs(y - cy)

                # Irregular boundary: tiles outside the inscribed
                # diamond (the box's own corners) have a real chance
                # to stay whatever background terrain was already
                # there, instead of every bounding-box tile becoming
                # part of the settlement - breaks up the solid-square
                # silhouette without touching the box's own size.
                if dist > max_dist and self.rng.random() < 0.6:
                    continue

                is_center = is_real and (x, y) == (cx, cy)
                feature = 'T' if is_center else self.rng.choice(town_features)
                district = (
                    "downtown" if dist <= max_dist // 2
                    else "commercial" if dist <= max_dist
                    else "residential"
                )
                self.map[y][x] = {
                    'terrain': 'town', 'content': feature,
                    'explored': False, 'district': district,
                }

        return (cx, cy) if is_real else None

    def _pick_terrain(self, base_terrain, obstacle_density):
        if obstacle_density > 0 and self.rng.random() < obstacle_density:
            return self.rng.choice(['mountain', 'river'])
        return base_terrain

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

    # Campaign-difficulty diagnosis (resolves open question of WHY the 
    # campaign difficulty curve breaks at tiers 6-9): a 15-campaign run 
    # (tools/balance_autoplay.py --campaign, seed 11, 30-attempt cap) with 
    # the newer failure-reason and player-power-vs-expedition-power telemetry 
    # shows 100% of every failed attempt at EVERY expedition tier (0 through 9) 
    # is 'died: zombie combat' - zero timeouts, zero environmental deaths. So 
    # the tier 6-9 wall is not a navigation/exploration/pacing problem, it's 
    # purely a combat-power problem. The real cause: best weapon damage plateaus 
    # around 20-26 starting at roughly expedition tier 3 and never grows further 
    # through tier 9 (LOOT_WEAPON_TABLE's highest-damage entries and the crafting 
    # system's higher-tier recipes require levels the player rarely reaches within 
    # a single campaign - final level averages only ~8.5-9), and best armor reduction 
    # stays near 0-1 for almost the entire campaign (armor essentially never develops 
    # meaningfully). Meanwhile zombie composition/elite chance (this function, via the 
    # t = expeditions_completed / CAMPAIGN_LENGTH interpolation) keeps escalating all 
    # way through tier 9. So player combat power flatlines around tier 3-5 while the 
    # difficulty curve keeps climbing for 5 more tiers - that gap is the wall, not 
    # exploration or player level stalling out.
    def _select_zombie_for_encounter(self):
        # Combat difficulty scaling investigation: composition (which
        # zombie types can appear, and whether an elite variant rolls)
        # is now the primary difficulty lever, keyed to
        # expeditions_completed (the same map-level axis that already
        # drives map size/obstacle density) - not raw player level,
        # and not an unbounded flat stat multiplier. A player who
        # grinds one map indefinitely no longer faces ever-scarier
        # zombies from that alone; finishing expeditions is what
        # brings in tougher composition.
        # Continuous interpolation between the early (t=0) and late
        # (t=1, reached at CAMPAIGN_LENGTH) weight vectors, replacing
        # the three hard brackets this used to jump between - see the
        # campaign-simulation finding above for why a hard jump was a
        # real problem, not just a style preference.
        t = min(1.0, self.expeditions_completed / CAMPAIGN_LENGTH)
        early_weights = [0.55, 0.20, 0.03, 0.15, 0.05, 0.02]
        late_weights = [0.10, 0.15, 0.25, 0.15, 0.15, 0.20]
        weights = [
            early + (late - early) * t
            for early, late in zip(early_weights, late_weights)
        ]

        zombie_classes = list(self._ZOMBIE_BASE_STATS.keys())
        zombie_class = self.rng.choices(zombie_classes, weights=weights)[0]
        choice = zombie_class()

        # Day still gives a mild in-run ramp - capped now (was
        # unbounded: day * 0.2, ~3x by day 15) so it's a secondary
        # effect rather than the main way zombies get tougher.
        difficulty_factor = min(MAX_DAY_DIFFICULTY_FACTOR, max(1.0, self.day * 0.1))

        # Elite variant: same subclass, boosted stats - gated behind
        # expeditions_completed so they don't show up before the
        # player's had any chance to gear up. This is the "harder
        # without inflating every zombie forever" lever: elites are a
        # composition choice (this roll), not a universal multiplier.
        is_elite = (
            self.expeditions_completed >= ELITE_MIN_EXPEDITION
            and self.rng.random() < min(0.3, self.expeditions_completed * 0.03)
        )
        if is_elite:
            difficulty_factor *= ELITE_STAT_MULTIPLIER
            choice.name = f"Elite {choice.name}"

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
        move_cost = 15 if (self.has_waders and dest_terrain in ('water', 'swamp')) else TERRAIN_MOVE_MINUTES.get(dest_terrain, 15)
        self._update_time(move_cost)
        self._apply_decay()

        # Fatigue increases with movement
        self.fatigue = min(100, self.fatigue + 5)

        self.io.say(f"Moved {direction}.")

        # Check tile contents for placed zombies
        current_tile = self.map[self.current_position[1]][self.current_position[0]]

        if (
            isinstance(current_tile, dict)
            and current_tile.get('content') == 'T'
            and not self.settlement_explored
        ):
            # Objective-driven win condition investigation: the Town
            # Center alone no longer wins - the player must have
            # already set foot in this (or any) settlement's other
            # tiles first (below), so reaching it is confirmation of
            # exploring, not the entire objective.
            self.io.say(
                "The Town Center looks quiet - too quiet. You should "
                "search the settlement's buildings and streets before "
                "assuming it's safe to call this home."
            )
            return

        if isinstance(current_tile, dict) and current_tile.get('content') == 'T':
            self.won = True
            self.expeditions_completed += 1
            if self.expeditions_completed >= CAMPAIGN_LENGTH:
                self.io.say(f"\n{BOLD}{GREEN}You have reached the Town Center after {self.expeditions_completed} expeditions - the outbreak is finally contained. CAMPAIGN COMPLETE!{RESET}\n")
                self.io.say(f"{BOLD}A hero's stash of supplies awaits you when you start your next game!{RESET}\n")
                self.io.say(f"{BOLD}Your story in this outbreak ends here.{RESET}\n")
                self.__class__.prize_for_next_game = True
                self.backpack.food += 10
                self.backpack.water += 10
                self.backpack.medicine += 5
                self.backpack.ammo += 20
            else:
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

            if terrain == 'town' and current_tile.get('content') != 'T':
                # Objective-driven win condition / organic-settlement
                # investigations: stepping into any non-Town-Center
                # settlement tile satisfies the exploration gate above
                # (any settlement, decoy or real - see generate_map()'s
                # own known-limitation note on this simplification),
                # and surfaces the tile's district (the actual ask
                # behind the organic-settlement investigation: "I'm
                # entering the residential district", not a uniform
                # block of letters).
                if not self.settlement_explored:
                    self.settlement_explored = True
                    self.io.say("You've found a settlement - it's worth exploring before moving on.")
                district = current_tile.get('district')
                if district:
                    self.io.say(f"You're in the {district} district.")

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

        if self.current_position in self.tile_event_cooldowns and self.day < self.tile_event_cooldowns[self.current_position]:
            return

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

        self.tile_event_cooldowns[self.current_position] = self.day + 3

    def find_loot(self):
        current_tile = self.map[self.current_position[1]][self.current_position[0]]
        terrain = current_tile.get('terrain') if isinstance(current_tile, dict) else None
        content = current_tile.get('content') if isinstance(current_tile, dict) else None
        if terrain != 'building' and content not in ('H', 'R', 'S', 'B', 'T'):
            return

        # Intelligence increases chance of finding loot and better items
        find_chance = min(1.0, 0.2 + self.intelligence / 250)
        if self.rng.random() < find_chance:
            loot_types = ["food", "water", "medicine", "ammo", "weapon", "armor"]
            # Only a live possibility until it's actually been found -
            # once town_known is True there's nothing left to reveal,
            # so it drops out of the pool instead of wasting a roll.
            # Same pattern for the flashlight (day/night granularity
            # investigation) - once owned, it drops out too.
            if not self.town_known:
                loot_types.append("map")
            if not self.has_flashlight:
                loot_types.append("flashlight")
            if not self.has_waders:
                loot_types.append('waders')
            loot_type = self.rng.choice(loot_types)

            # Higher intelligence increases chance of finding weapons over consumables
            if self.intelligence > 10 and self.rng.random() < (self.intelligence / 100):
                loot_type = "weapon"

            self.io.say(f"You found {loot_type}!")
            self.award_xp(10)

            if loot_type == "weapon":
                # Real stat variance per name, and the correct weapon
                # type (melee vs ranged) - see LOOT_WEAPON_TABLE's own
                # comment in constants.py for the bug this replaced.
                eligible_weapons = {
                    name: spec for name, spec in LOOT_WEAPON_TABLE.items()
                    if spec.get('min_expedition', 0) <= self.expeditions_completed
                }
                new_weapon_name = self.rng.choice(list(eligible_weapons.keys()))
                spec = eligible_weapons[new_weapon_name]
                if spec["type"] == "ranged":
                    new_weapon = RangedWeapon(
                        new_weapon_name, spec["damage"],
                        spec["max_ammo"], spec["durability"],
                    )
                else:
                    new_weapon = MeleeWeapon(
                        new_weapon_name, spec["damage"], spec["durability"],
                    )
                if self.backpack.add_weapon(new_weapon):
                    self.io.say(f"You obtained a {new_weapon.name}.")
                else:
                    self.io.say("You found a weapon but your pack is full - drop something first.")
            elif loot_type == "armor":
                # Equipment-slot investigation: same expedition-banding
                # pattern as weapons above.
                eligible_armor = {
                    name: spec for name, spec in ARMOR_TABLE.items()
                    if spec.get('min_expedition', 0) <= self.expeditions_completed
                }
                new_armor_name = self.rng.choice(list(eligible_armor.keys()))
                spec = eligible_armor[new_armor_name]
                new_armor = Armor(new_armor_name, spec["reduction"], spec["durability"], spec["slot"])
                if self.backpack.add_armor(new_armor):
                    self.io.say(f"You obtained {new_armor.name}.")
                else:
                    self.io.say("You found armor but your pack is full - drop something first.")
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
                self.backpack.ammo += self.rng.randint(1, 3)
                self.io.say("You found some ammo! Ammo stock increased.")
            elif loot_type == "map":
                self.town_known = True
                self.io.say(
                    "You found a weathered survivor's map! The Town "
                    "Center's location is now revealed."
                )
            elif loot_type == "flashlight":
                self.has_flashlight = True
                self._update_time(0)  # refresh visibility_radius immediately, without advancing time
                self.io.say(
                    "You found a working flashlight! Visibility at "
                    "dawn, dusk, and night is now much better."
                )
            elif loot_type == 'waders':
                self.has_waders = True
                self.io.say(
                    'You found a sturdy pair of waders! Water and swamp '
                    'terrain no longer slow you down as much.'
                )