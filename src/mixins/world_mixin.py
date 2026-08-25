# Auto-extracted from the original monolithic apocrysis.py during
# the src/ restructuring - see README.md for the project layout.

import random

from src.constants import BOLD, GREEN, RESET
from src.items import MeleeWeapon
from src.zombies import FreshZombie, RegularZombie, HeavyZombie


class WorldMixin:

    def generate_map(self):
        terrain_types = ['forest', 'building', 'water', 'plain']
        # Initialize the map with random terrain
        self.map = [[{'terrain': random.choice(terrain_types), 'content': '-', 'explored': False} for _ in
                     range(self.map_size)] for _ in range(self.map_size)]
        
        center = self.map_size // 2
        # Place the player in the center
        self.current_position = (center, center)
        self.map[center][center]['content'] = 'P'

        # Consolidated zombie placement: calculate total zombies based on 10% of map tiles
        total_tiles = self.map_size ** 2
        num_zombies = int(total_tiles * 0.10)
        
        placed_zombies = 0
        while placed_zombies < num_zombies:
            x = random.randint(0, self.map_size - 1)
            y = random.randint(0, self.map_size - 1)
            if isinstance(self.map[y][x], dict):  # Consistent row-major indexing [y][x]
                zombie_type = self._select_zombie_for_encounter()
                self.map[y][x] = zombie_type
                placed_zombies += 1

        # Define town size and features
        town_size = min(5, self.map_size)  # Example size of the town (5x5), clamped to small maps
        town_features = ['H', 'R', 'S', 'B', 'T']  # Example features (House, Road, Shop, Building, Town center)

        max_start = max(0, self.map_size - town_size)
        town_start_x = random.randint(0, max_start)
        town_start_y = random.randint(0, max_start)

        # Place the town on the map
        for y in range(town_start_y, town_start_y + town_size):
            for x in range(town_start_x, town_start_x + town_size):
                feature = random.choice(town_features)
                self.map[y][x] = {'terrain': 'town', 'content': feature, 'explored': False}

        return self.map

    def _select_zombie_for_encounter(self):
        # Difficulty scaling based on day count
        difficulty_factor = max(1.0, self.day * 0.2)
        
        # Adjust weights towards harder zombies as days progress
        if self.day <= 5:
            weights = [0.7, 0.25, 0.05]
        elif self.day <= 15:
            weights = [0.4, 0.4, 0.2]
        else:
            weights = [0.2, 0.3, 0.5]
            
        choice = random.choices([FreshZombie(), RegularZombie(), HeavyZombie()], weights=weights)[0]
        
        # Scale stats based on day difficulty
        if isinstance(choice, FreshZombie):
            choice.health = int(30 * difficulty_factor)
            choice.attack = max(1, int(5 * difficulty_factor))
        elif isinstance(choice, RegularZombie):
            choice.health = int(50 * difficulty_factor)
            choice.attack = max(1, int(10 * difficulty_factor))
        elif isinstance(choice, HeavyZombie):
            choice.health = int(100 * difficulty_factor)
            choice.attack = max(1, int(20 * difficulty_factor))
            
        return choice

    def move_and_search(self, direction):
        directions = {"n": (0, -1), "s": (0, 1), "e": (1, 0), "w": (-1, 0)}
        dx, dy = directions.get(direction, (0, 0))
        new_x, new_y = self.current_position[0] + dx, self.current_position[1] + dy

        if 0 <= new_x < self.map_size and 0 <= new_y < self.map_size:
            # Update the current position
            self.current_position = (new_x, new_y)
            self.visited.add(self.current_position)  # Mark the new position as visited
            
            # Advance time cycle and apply decay
            self._update_time()
            self._apply_decay()
            
            # Fatigue increases with movement
            self.fatigue = min(100, self.fatigue + 5)
            
            print(f"Moved {direction}.")
            
            # Check tile contents for placed zombies
            current_tile = self.map[self.current_position[1]][self.current_position[0]]
            
            if isinstance(current_tile, dict) and current_tile.get('content') == 'T':
                self.won = True
                print(f"\n{BOLD}{GREEN}You have reached the Town Center! The survivors welcome you home. You WIN!{RESET}\n")
                print(f"{BOLD}A grateful stash of supplies awaits you when you start your next game!{RESET}\n")
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
                    print("You enter a building. It's a safe zone.")
                    heal_amount = random.randint(5, 10)
                    self.health = min(100, max(0, self.health + heal_amount))
                    fatigue_recovery = max(0, self.wisdom // 4)
                    self.fatigue = max(0, self.fatigue - fatigue_recovery - 5)
                    print(f"Restored {heal_amount} health and recovered some fatigue.")
                    
                elif terrain == 'water':
                    print("You wade through water. Movement is difficult.")
                    self.fatigue = min(100, self.fatigue + 10) # Extra fatigue penalty for slow movement
                    if random.random() < 0.2:
                        self.health -= 5
                        print("The cold water chills you. You lost some health.")
                        
                elif terrain == 'forest':
                    print("You move through dense forest.")

            encounter_chance = 0.5 if self.is_night else 0.3
            
            # Forest increases encounter rate
            if isinstance(current_tile, dict) and current_tile.get('terrain') == 'forest':
                encounter_chance = min(1.0, encounter_chance * 1.5)
                
            if isinstance(current_tile, (FreshZombie, RegularZombie, HeavyZombie)):
                self.encounter_zombie(current_tile)
            elif random.random() < encounter_chance:  # Chance encounter when moving around the map
                self.encounter_zombie()
            else:
                self.find_loot()
        else:
            print("Can't move in that direction.")

    def find_loot(self):
        # Intelligence increases chance of finding loot and better items
        find_chance = min(1.0, 0.2 + self.intelligence / 250)
        if random.random() < find_chance:
            loot_type = random.choice(["food", "water", "medicine", "ammo", "weapon"])
            
            # Higher intelligence increases chance of finding weapons over consumables
            if self.intelligence > 10 and random.random() < (self.intelligence / 100):
                loot_type = "weapon"
                
            print(f"You found {loot_type}!")
            self.award_xp(10)

            if loot_type == "weapon":
                # Parameterized weapon names for randomized loot generation
                possible_weapon_names = [
                    "Rusty Dagger", "Iron Axe", "Broken Rifle", 
                    "Steel Katana", "Leather Bow", "Chipped Sword"
                ]
                new_weapon_name = random.choice(possible_weapon_names)
                new_weapon = MeleeWeapon(new_weapon_name, 10, 100)
                self.backpack.weapons.append(new_weapon)
                print(f"You obtained a {new_weapon.name}.")
            elif loot_type == "food":
                # Increase food in the backpack
                self.backpack.food += 1
                print("You found some food. Food stock increased.")
            elif loot_type == "water":
                # Increase water in the backpack
                self.backpack.water += 1
                print("You found some water. Water stock increased.")
            elif loot_type == "medicine":
                # Increase medicine in the backpack
                self.backpack.medicine += 1
                print("You found some medicine. Medicine stock increased.")
            elif loot_type == "ammo":
                # Increase ammo in the backpack to support ranged crafting recipes
                self.backpack.ammo += random.randint(1, 3)
                print("You found some ammo! Ammo stock increased.")

