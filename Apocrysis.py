import random

class Item:
    def __init__(self, name):
        self.name = name

class Backpack:
    def __init__(self):
        self.items = []  # Now this will only store general items, not categorized
        self.food = 0
        self.water = 0
        self.medicine = 0
        self.ammo = 0
        self.weapons = []

    def add_item(self, item):
        if isinstance(item, str):  # Simplified for demonstration; consider enhancing for real application
            if item == "food":
                self.food += 1
            elif item == "water":
                self.water += 1
            elif item == "medicine":
                self.medicine += 1
            elif item == "ammo":
                self.ammo += 1
        elif isinstance(item, Weapon):
            self.weapons.append(item)
        else:
            self.items.append(item)


class Weapon(Item):
    def __init__(self, name, damage):
        super().__init__(name)
        self.damage = damage

    def __str__(self):
        return f"{self.name} - Damage: {self.damage}"

class MeleeWeapon(Weapon):
    def __init__(self, name, damage, durability):
        super().__init__(name, damage)
        self.durability = durability

    def use(self):
        if self.durability > 0:
            self.durability -= 1
            return self.damage
        else:
            print(f"{self.name} is broken and cannot be used.")
            return 0  # Return 0 damage if the weapon is broken

class RangedWeapon:
    def __init__(self, name, damage, max_ammo):
        self.name = name
        self.damage = damage
        self.max_ammo = max_ammo
        self.ammo = max_ammo  # Initialize ammo count to the maximum

    def fire(self):
        if self.ammo > 0:
            self.ammo -= 1
            print(f"You fire your {self.name}. Ammo remaining: {self.ammo}/{self.max_ammo}")
            # Implement damage logic or any other functionality here
        else:
            print("Out of ammo! You need to reload.")

    def reload(self, ammo_count):
        self.ammo = min(ammo_count, self.max_ammo)  # Reload up to the maximum ammo count

    def __str__(self):
        return f"{self.name} (Damage: {self.damage}, Ammo: {self.ammo}/{self.max_ammo})"



class Zombie:
    def __init__(self, name, health, attack):
        self.name = name
        self.health = health
        self.attack = attack
        #self.loot_table = []

    def take_damage(self, damage):
        self.health -= damage

class FreshZombie(Zombie):
    def __init__(self):
        super().__init__("Fresh Zombie", 30, 5)
        self.loot_table = ["food", "water", "medicine"]

class RegularZombie(Zombie):
    def __init__(self):
        super().__init__("Regular Zombie", 50, 10)
        self.loot_table = ["food", "water", "medicine", "weapon"]

class HeavyZombie(Zombie):
    def __init__(self):
        super().__init__("Heavy Zombie", 100, 20)
        self.loot_table = ["food", "water", "medicine", "weapon", "ammo"]


class PlayerClass:
    def __init__(self, health, hunger, thirst, fatigue, strength, dexterity, intelligence, wisdom, equipped_weapon):
        self.health = health
        self.hunger = hunger
        self.thirst = thirst
        self.fatigue = fatigue
        self.strength = strength
        self.dexterity = dexterity
        self.intelligence = intelligence
        self.wisdom = wisdom
        self.equipped_weapon = equipped_weapon

class Apocrysis:

    def __init__(self, name, player_class, map_size):
        self.map_size = map_size
        self.name = name
        self.player_class = player_class
        self.health = 100
        self.max_health = 100  # Maximum health at the start
        self.backpack = Backpack()
        self.equipped_weapon = None
        self.current_position = (self.map_size // 2, self.map_size // 2)
        self.map = [[None for _ in range(self.map_size)] for _ in range(self.map_size)]
        self.visited = set()  # Initialize visited tiles tracker
        self.visited.add(self.current_position)  # Mark the initial position as visited
        self.initialize_player(player_class)
        self.zombie_positions = set()  # Initialize as an empty set
        self.place_zombies()


    def run_game_loop(self):
        while self.health > 0:
            self.print_map()
            self.stats()
            self.display_inventory()
            self.view_weapon_info()

            print("\nWhat would you like to do?")
            command = input(
                "Enter command (n/s/e/w, map, inventory, stats, eat, drink, medicine, equip [weapon name], exit): ").lower()

            if command == 'exit':
                print("Exiting game...")
                break
            elif command in ['n', 's', 'e', 'w']:
                self.move_and_search(command)
            elif command == 'map':
                self.print_map()
            elif command == 'inventory':
                self.display_inventory()
            elif command == 'stats':
                self.stats()
            elif command == 'eat':
                self.eat()
            elif command == 'drink':
                self.drink()
            elif command == 'medicine':
                self.use_medicine()
            elif command.startswith('equip '):
                weapon_name = command[6:]
                self.equip_weapon(weapon_name)
            elif command == 'auto':
                self.auto_play()  # Trigger the auto play functionality
            else:
                print("Unknown command.")

    def initialize_player(self, player_class):
        class_attributes = {
            "gamer": PlayerClass(100, 100, 100, 0, 10, 10, 10, 10, MeleeWeapon("Folding Pocket Knife", 5, 100)),
            "pro gamer": PlayerClass(120, 100, 100, 0, 15, 15, 15, 15, MeleeWeapon("Fixed Blade Knife", 10, 100)),
            "scavenger": PlayerClass(90, 110, 110, 5, 8, 12, 14, 10, MeleeWeapon("Crowbar", 7, 100)),
            "medic": PlayerClass(100, 100, 100, 0, 7, 9, 16, 15, MeleeWeapon("Scalpel", 5, 100)),
            "engineer": PlayerClass(95, 100, 100, 10, 10, 11, 18, 12, RangedWeapon("Homemade Crossbow", 15, 10)),
            "ranger": PlayerClass(110, 90, 90, 0, 12, 15, 10, 8, RangedWeapon("Bow", 12, 20)),
            "survivalist": PlayerClass(120, 85, 85, 5, 14, 8, 12, 14, MeleeWeapon("Hatchet", 10, 100)),
        }

        # Fetch the PlayerClass object for the chosen class, default to 'gamer' if not found
        attrs = class_attributes.get(player_class, class_attributes["gamer"])

        self.health = attrs.health
        self.hunger = attrs.hunger
        self.thirst = attrs.thirst
        self.fatigue = attrs.fatigue
        self.strength = attrs.strength
        self.dexterity = attrs.dexterity
        self.intelligence = attrs.intelligence
        self.wisdom = attrs.wisdom
        self.equipped_weapon = attrs.equipped_weapon

        # Add starting ammo for player classes with ranged weapons
        if isinstance(self.equipped_weapon, RangedWeapon):
            # Add 5 ammo to start with
            self.equipped_weapon.reload(5)  # Adjust the number as needed

    def initialize_player_class(player_class_name):
        if player_class_name in player_classes:
            player_class = player_classes[player_class_name]
            # You can now use player_class attributes and equipped_weapon
            # For example, assigning them to a player object
            return player_class
        else:
            print("Invalid player class selected.")
            return None

    def place_zombies(self):
        zombie_percentage = 0.10  # 10% of the map tiles will have zombies
        total_tiles = self.map_size ** 2
        num_zombies = int(total_tiles * zombie_percentage)

        placed_zombies = 0
        while placed_zombies < num_zombies:
            x = random.randint(0, self.map_size - 1)
            y = random.randint(0, self.map_size - 1)
            if self.map[y][x] is None:  # Check if the tile is empty before placing a zombie
                zombie_type = random.choice([FreshZombie(), RegularZombie(), HeavyZombie()])
                self.map[y][x] = zombie_type
                placed_zombies += 1

    def generate_map(self):
        terrain_types = ['forest', 'building', 'water', 'plain']
        # Initialize the map with random terrain
        self.map = [[{'terrain': random.choice(terrain_types), 'content': '-', 'explored': False} for _ in
                     range(self.map_size)] for _ in range(self.map_size)]
        center = self.map_size // 2
        # Place the player in the center
        self.current_position = (center, center)
        self.map[center][center]['content'] = 'P'
        # Place zombies randomly
        for _ in range(8):
            x, y = random.randint(0, self.map_size - 1), random.randint(0, self.map_size - 1)
            self.map[x][y]['content'] = 'Z'

        # Define town size and features
        town_size = 5  # Example size of the town (5x5)
        town_features = ['H', 'R', 'S', 'B', 'T']  # Example features (House, Road, Shop, Building, Town center)

        # Calculate start coordinates for the town in the northeast corner
        town_start_x = self.map_size - town_size
        town_start_y = 0  # Starting at the top row for the northern part

        # Place the town on the map
        for y in range(town_start_y, town_start_y + town_size):
            for x in range(town_start_x, town_start_x + town_size):
                # Assign a specific town feature to each tile in the town area
                feature = random.choice(town_features)
                self.map[y][x] = {'terrain': 'town', 'content': feature, 'explored': False}

        return self.map

    def move_and_search(self, direction):
        directions = {"n": (0, -1), "s": (0, 1), "e": (1, 0), "w": (-1, 0)}
        dx, dy = directions.get(direction, (0, 0))
        new_x, new_y = self.current_position[0] + dx, self.current_position[1] + dy

        if 0 <= new_x < self.map_size and 0 <= new_y < self.map_size:
            # Clear the current position if needed (depends on your map setup)
            # Update the current position
            self.current_position = (new_x, new_y)
            self.visited.add(self.current_position)  # Mark the new position as visited
            print(f"Moved {direction}.")
            self.check_tile_contents()  # Use the updated current_position within the method
        else:
            print("Can't move in that direction.")

    def check_tile_contents(self):
        current_tile = self.map[self.current_position[1]][self.current_position[0]]
        if isinstance(current_tile, (FreshZombie, RegularZombie, HeavyZombie)):
            # Here, you handle the encounter with the zombie
            print("Encountered a zombie!")
            self.encounter_zombie(current_tile)  # Assuming you have a method to handle zombie encounters
        else:
            # Assuming you have a find_loot method or similar logic for when the player lands on an empty tile
            self.find_loot()

    def find_loot(self):
        # Simplified loot finding logic with a 50% chance to find something
        if random.random() < 0.5:
            loot_type = random.choice(["food", "water", "medicine", "weapon"])
            print(f"You found {loot_type}!")

            if loot_type == "weapon":
                # Adjust the weapon creation to match the MeleeWeapon constructor with durability
                # Assuming durability is relevant for MeleeWeapon and is set here as an example
                new_weapon = MeleeWeapon("Found Sword", 10, 100)  # Adjusted to remove the durability argument
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
            # This structure allows for easy expansion to include more loot types and detailed handling for each.

    def explore_tile(self, position):
        x, y = position
        self.map[x][y]['explored'] = True
        print("Explored the tile.")

    def check_encounter(self):
        # Correct indexing for accessing the map's row first, then column
        x, y = self.current_position
        tile = self.map[y][x]  # Note the reversal to y, x for row, column access

        if tile['content'] == 'Z':
            self.encounter_zombie()
        # Optionally, you can add more conditions here for different encounters
        # Example:
        elif tile['content'] == 'L':
            self.find_loot()

    def encounter_zombie(self, current_tile=None):
        # Randomly select a zombie type for the encounter
        zombie = random.choice([FreshZombie(), RegularZombie(), HeavyZombie()])
        print(f"Encountered a {zombie.name}! What will you do?")

        # Prompt player for action
        action = input("Do you want to fight or flee? (fight/flee): ").lower()
        if action == "flee":
            # Implement fleeing logic with a certain chance of success
            if random.random() < 0.5:  # Assuming a 50% success rate for fleeing
                print("Successfully fled from the zombie.")
                return  # Exit the method to avoid the fight
            else:
                print("Failed to flee! You have to fight the zombie.")

        print(f"Preparing for battle against the {zombie.name}...")
        while self.health > 0 and zombie.health > 0:
            # Player's turn to attack
            if self.equipped_weapon:
                print(f"You attack the {zombie.name} with your {self.equipped_weapon.name}.")
                damage = self.equipped_weapon.damage
                zombie.take_damage(damage)
                print(f"The {zombie.name} takes {damage} damage.")
            else:
                print("You have no weapon equipped and attempt to fight with your hands!")
                zombie.take_damage(2)  # Minimal damage when unarmed
                print("You deal 2 damage with your bare hands.")

            # Check if the zombie has been defeated
            if zombie.health <= 0:
                print(f"The {zombie.name} has been defeated!")
                self.handle_loot(zombie.loot_table)
                return

            # Zombie's turn to attack if it is still alive
            if zombie.health > 0:
                self.take_damage(zombie.attack)

            # Check for critical health condition for fleeing chance
            if self.health <= self.max_health * 0.1:
                print("You are critically wounded!")
                if random.random() < 0.1:  # 10% chance to flee successfully
                    print("In a desperate move, you managed to flee from the zombie.")
                    return
                else:
                    print("Unable to flee, you brace yourself for the zombie's attack.")

        if self.health <= 0:
            print("You are critically wounded and unable to continue the fight!")
            # Implement game over or severe consequence logic here

    def print_map(self):
        # Print top border
        print('*' * (len(self.map[0]) + 2))

        for y, row in enumerate(self.map):
            # Print left border
            print('*', end='')
            for x, tile in enumerate(row):
                char = ' '  # Default character for empty space
                if (x, y) == self.current_position:
                    char = 'P'  # Player's position
                elif isinstance(tile, dict):
                    if 'terrain' in tile and tile['terrain'] == 'town':
                        # Handle town features, display 'T' for town tiles
                        char = 'T'
                    elif (x, y) in self.visited:
                        if 'content' in tile:
                            if tile['content'] == 'P':
                                char = 'P'  # Player's position, if revisited
                            elif tile['content'] == 'Z':
                                char = 'Z'  # Zombie's position, shown only if visited and has 'Z'
                elif isinstance(tile, FreshZombie) and (x, y) in self.visited:
                    char = 'Z'  # Assuming 'Z' for zombies, shown only if visited
                print(char, end='')
            # Print right border
            print('*')

        # Print bottom border
        print('*' * (len(self.map[0]) + 2))

    def stats(self):
        print(f"Health: {self.health}, Hunger: {self.hunger}, Thirst: {self.thirst}")

    def handle_loot(self, loot_table):
        dropped_loot = random.choices(loot_table, k=random.randint(1, 3))  # Randomly choose 1 to 3 items from loot table
        for item in dropped_loot:
            if item == "food":
                self.backpack.food += 1
                print("You found some food!")
            elif item == "water":
                self.backpack.water += 1
                print("You found some water!")
            elif item == "medicine":
                self.backpack.medicine += 1
                print("You found some medicine!")
            elif item == "weapon":
                # Corrected instantiation of MeleeWeapon and RangedWeapon
                weapon = random.choice([
                    MeleeWeapon("Sword", 15, 25),
                    RangedWeapon("Gun", 20, 5)  # Assuming the last number is the ammunition count
                ])

                self.backpack.weapons.append(weapon)
                print(f"You found a {weapon.name}!")
            elif item == "ammo":
                self.backpack.ammo += random.randint(1, 10)
                print("You found some ammo!")

    def display_inventory(self):
        print("\n--- Inventory ---")
        print(f"Food: {self.backpack.food}")
        print(f"Water: {self.backpack.water}")
        print(f"Medicine: {self.backpack.medicine}")
        print(f"Ammo: {self.backpack.ammo}")  # If applicable
        print("Weapons:")
        for weapon in self.backpack.weapons:
            print(f"- {weapon.name}")
        # Display other inventory items as needed

    def stats(self):
        print("\n--- Player Stats ---")
        print(f"Health: {self.health}")
        print(f"Hunger: {self.hunger}")
        print(f"Thirst: {self.thirst}")
        print(f"Fatigue: {self.fatigue}")
        print(f"Strength: {self.strength}")
        print(f"Dexterity: {self.dexterity}")
        print(f"Intelligence: {self.intelligence}")
        print(f"Wisdom: {self.wisdom}")
        if self.equipped_weapon:
            print(f"Equipped Weapon: {self.equipped_weapon.name}")
        else:
            print("Equipped Weapon: None")

    def eat(self):
        if self.backpack.food > 0:
            self.backpack.food -= 1
            self.hunger = min(100, self.hunger + 5)  # Adjust value as per game mechanics
            self.health = min(100, self.health + 5)  # Health increases by 10 when eating, up to a max of 100
            print("You eat some food. Hunger increased. Health restored.")
        else:
            print("You have no food.")

    def drink(self):
        if self.backpack.water > 0:
            self.backpack.water -= 1
            self.thirst = min(100, self.thirst + 5)  # Adjust value as per game mechanics
            self.health = min(100, self.health + 5)  # Health increases by 5 when drinking, up to a max of 100
            print("You drink some water. Thirst increased. Health restored.")
        else:
            print("You have no water.")

    def use_medicine(self):
        if self.backpack.medicine > 0:
            self.backpack.medicine -= 1
            self.health = min(100, self.health + 20)  # Adjust value as per game mechanics
            print("You use medicine. Health increased.")
        else:
            print("You have no medicine.")

    def equip_weapon(self, weapon_name):
        # Search for the weapon in the backpack's weapons list
        for weapon in self.backpack.weapons:
            if weapon.name.lower() == weapon_name.lower():
                # Check if there's already a weapon equipped
                if self.equipped_weapon:
                    # If there's already a weapon equipped, put it back in the backpack
                    self.backpack.weapons.append(self.equipped_weapon)
                    print(f"The {self.equipped_weapon.name} has been returned to the backpack.")
                # Equip the new weapon
                self.equipped_weapon = weapon
                # Remove the newly equipped weapon from the backpack
                self.backpack.weapons.remove(weapon)
                print(f"You have equipped the {weapon.name}.")
                return
        print(f"Weapon named '{weapon_name}' not found in inventory.")

    def auto_play(self):
        print("\nAuto-playing game...\n")
        actions = ['n', 's', 'e', 'w']
        while self.health > 0:
            # Simulate random movement
            action = random.choice(actions)
            self.move_and_search(action)
            print(f"Automatically moving {action}")

            # Randomly decide to eat or drink if necessary
            if self.hunger < 50 and self.backpack.food > 0:
                self.eat()
                print("Automatically eating to reduce hunger.")
            if self.thirst < 50 and self.backpack.water > 0:
                self.drink()
                print("Automatically drinking to reduce thirst.")

            # Randomly use medicine
            if self.health < 75 and self.backpack.medicine > 0:
                self.use_medicine()
                print("Automatically using medicine to heal.")

            # Implement other auto actions like fighting or fleeing from zombies

            # Check for end conditions or keep the loop running for a set number of iterations
            # For demonstration, let's add a condition to stop after a few iterations
            if random.random() < 0.1:  # 10% chance to stop auto-playing
                print("Auto-play ending...")
                break

    def view_weapon_info(self):
        if self.equipped_weapon:
            print("Equipped Weapon:")
            print(self.equipped_weapon)
        else:
            print("No weapon is currently equipped.")

        if self.backpack.weapons:
            print("\nWeapons in Inventory:")
            for weapon in self.backpack.weapons:
                print(weapon)
        else:
            print("\nNo weapons in inventory.")

    def take_damage(self, damage):
        """
        Reduces the zombie's health by the specified damage amount.
        """
        self.health -= damage
        print(f"The {self.name} takes {damage} damage. Its current health is {self.health}.")
        if self.health <= 0:
            print(f"The {self.name} has been defeated!")

    def increase_max_health(self, amount):
      self.max_health += amount
      self.health = self.max_health

    def battle(self, zombie):
        while self.health > 0 and zombie.health > 0:
            # Player's turn to attack
            if self.health <= 0:
                print("You have died. Game over.")
                break

            if self.equipped_weapon and isinstance(self.equipped_weapon, RangedWeapon):
                if self.equipped_weapon.ammo > 0:
                    damage = self.equipped_weapon.use()  # Use the equipped weapon
                    if damage > 0:
                        print(f"You attack the {zombie.name} with your {self.equipped_weapon.name}.")
                        print(
                            f"You fire your {self.equipped_weapon.name}. Ammo remaining: {self.equipped_weapon.ammo}/{self.equipped_weapon.max_ammo}")
                        zombie.take_damage(damage)
                        print(f"The {zombie.name} takes {damage} damage.")
                    else:
                        print("You cannot attack with a broken weapon.")
                else:
                    print("You have no ammo left for your ranged weapon!")
            elif self.equipped_weapon:
                damage = self.equipped_weapon.use()  # Use the equipped weapon
                if damage > 0:
                    print(f"You attack the {zombie.name} with your {self.equipped_weapon.name}.")
                    print(
                        f"You fire your {self.equipped_weapon.name}. Ammo remaining: {self.equipped_weapon.ammo}/{self.equipped_weapon.max_ammo}")
                    zombie.take_damage(damage)
                    print(f"The {zombie.name} takes {damage} damage.")
                else:
                    print("You cannot attack with a broken weapon.")
            else:
                print("You have no weapon equipped and attempt to fight with your hands!")
                zombie.take_damage(2)  # Minimal damage when unarmed
                print("You deal 2 damage with your bare hands.")

            # Check if the zombie has been defeated
            if zombie.health <= 0:
                print(f"The {zombie.name} has been defeated!")
                self.handle_loot(zombie.loot_table)
                break

            # Zombie's turn to attack
            print(f"The {zombie.name} attacks you back, dealing {zombie.attack} damage.")
            self.take_damage(zombie.attack)
            print(f"You took {zombie.attack} damage. Your current health is {self.health}.")

            # Check for critical health condition for fleeing chance
            if self.health <= self.max_health * 0.1:
                print("You are critically wounded!")
                if random.random() < 0.1:  # 10% chance to flee successfully
                    print("In a desperate move, you managed to flee from the zombie.")
                    break
                else:
                    print("Unable to flee, you brace yourself for the zombie's attack.")

            # Subtract ammo used from inventory
            if self.equipped_weapon and isinstance(self.equipped_weapon, RangedWeapon):
                self.equipped_weapon.ammo -= 1


def main():
    name = input("Enter your name: ")
    player_class = input("Choose your class (gamer, pro gamer, scavenger, medic, engineer, ranger, survivalist): ").lower()

    # Initialize map_size with a default or invalid value
    map_size = -1

    # Use a loop to keep asking for input until a valid integer is provided
    while map_size <= 0:
        try:
            map_size_input = input("Enter the size of the game board (a positive integer): ")
            map_size = int(map_size_input)
            if map_size <= 0:
                raise ValueError  # Ensure the entered integer is positive
        except ValueError:
            print("Invalid input. Please enter a positive integer for the game board size.")
            # The loop will continue until a valid input is received

    player = Apocrysis(name, player_class, map_size)
    print(" ")
    print(" ")
    print("In the twilight years of the 21st century, the world as we knew it teetered on the brink of an abyss, ")
    print("brought to its knees by a catastrophic blend of environmental disasters, political turmoil, and ")
    print("unchecked scientific experimentation. Amidst this chaos, a virulent pathogen, born from the reckless ")
    print("ambition of a clandestine biotech firm, was unleashed upon an unsuspecting populace. The outbreak was ")
    print("swift and merciless, ravaging cities, decimating communities, and transforming the afflicted into ")
    print("voracious, undead beings. ")
    print(" ")
    print(f"{name}, a once unassuming person with a knack for survival and a heart brimming ")
    print("with resilience, found himself cast into the heart of this apocalyptic nightmare. While the world around him ")
    print(f"succumbed to despair and ruin, {name}'s resolve to endure, to fight, and to carve out a semblance of hope amid ")
    print("the desolation became the beacon that guided his every step. As society crumbled and the vestiges of humanity ")
    print(f"dwindled, {name}'s journey through this dystopian world became a testament to the indomitable spirit of those who ")
    print("refuse to be extinguished, even in the darkest of times.")
    print(" ")
    player.run_game_loop()

if __name__ == "__main__":
    main()


