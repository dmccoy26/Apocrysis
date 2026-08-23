import random
import re
import enum
from collections import Counter
from dataclasses import dataclass
import sys
import shutil
import os
import json

# ANSI Color Codes for Terminal Emphasis
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"
CYAN = "\033[96m"

# Real bug found live: the map's player marker ('P') got wrapped in
# health-based ANSI color codes (BOLD + GREEN/YELLOW/RED + RESET,
# see _render_map_lines() below) - invisible on screen, but `len()`
# still counts those escape-code bytes as characters. The two-column
# layout's `left_line.ljust(left_col_width)` uses raw `len()` to
# decide how much padding to add, so the ONE row containing the
# player was treated as ~13 characters "longer" than it visually is,
# and got that much LESS padding - the '|' separator (and everything
# in the right-hand panel) visibly shifted left on exactly that row,
# and only that row, matching what was reported live ("Food is out of
# place" / "What would you like to do was below No weapons in
# inventory" - whichever right-hand line happened to land on the
# player's map row that turn). `_visible_len`/`_display_ljust` pad
# based on the string with ANSI codes stripped out, so a colored cell
# no longer throws off alignment.
_ANSI_ESCAPE_RE = re.compile(r'\x1b\[[0-9;]*m')


def _visible_len(text):
    return len(_ANSI_ESCAPE_RE.sub('', text))


def _display_ljust(text, width):
    padding = width - _visible_len(text)
    return text + (' ' * padding if padding > 0 else '')

# Real bug found live: wilderness terrain ('forest'/'building'/'water'/
# 'plain', set on every non-town tile in generate_map()) only ever
# showed up as flavor text AFTER stepping onto a tile
# ("You move through dense forest.") - print_map() never rendered it,
# so every wilderness tile looked identical (.) regardless of
# terrain. This maps each real terrain type to a map symbol so it's
# visible before you walk into it. No 'mountain'/'river' terrain
# exists in generate_map()'s terrain_types - only what's actually
# generated is mapped here, rather than inventing symbols for terrain
# that was never implemented.
TERRAIN_SYMBOLS = {
    'forest': 'f',
    'water': '~',
    'building': 'b',
    'plain': '.',
}

TERRAIN_LEGEND = (
    "  f = forest   ~ = water   b = building   . = plain\n"
    "  T/H/R/S/B = town tiles (Town center/House/Road/Shop/Building)\n"
    "  P = you   Z = zombie (only shown once you've been there)"
)

class ConsumableType(enum.Enum):
    FOOD = "food"
    WATER = "water"
    MEDICINE = "medicine"
    AMMO = "ammo"

class Item:
    def __init__(self, name):
        self.name = name

class Backpack:
    def __init__(self):
        self.consumables = Counter()  # Unified storage for food, water, medicine, ammo
        self.weapons = []             # Dedicated list for Weapon objects
        self.items = []               # Generic items that aren't consumables or weapons

    def add_item(self, item):
        if isinstance(item, str):
            try:
                category = ConsumableType[item.upper()]
                self.consumables[category.value] += 1
            except KeyError:
                pass  # Gracefully ignore unrecognized strings
        elif isinstance(item, Weapon):
            self.weapons.append(item)
        else:
            self.items.append(item)

    @property
    def food(self): return self.consumables["food"]
    @food.setter
    def food(self, value): self.consumables["food"] = value

    @property
    def water(self): return self.consumables["water"]
    @water.setter
    def water(self, value): self.consumables["water"] = value

    @property
    def medicine(self): return self.consumables["medicine"]
    @medicine.setter
    def medicine(self, value): self.consumables["medicine"] = value

    @property
    def ammo(self): return self.consumables["ammo"]
    @ammo.setter
    def ammo(self, value): self.consumables["ammo"] = value




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

class RangedWeapon(Weapon):
    def __init__(self, name, damage, max_ammo, durability=20):
        super().__init__(name, damage)
        self.max_ammo = max_ammo
        self.ammo = max_ammo  # Initialize ammo count to the maximum
        self.durability = durability

    def fire(self):
        if self.ammo > 0 and self.durability > 0:
            self.ammo -= 1
            self.durability -= 1
            print(f"You fire your {self.name}. Ammo remaining: {self.ammo}/{self.max_ammo}")
            return self.damage
        else:
            if self.ammo <= 0:
                print("Out of ammo! You need to reload.")
            else:
                print(f"{self.name} is broken and cannot be used.")
            return 0

    def use(self):
        if self.ammo > 0 and self.durability > 0:
            self.ammo -= 1
            self.durability -= 1
            return self.damage
        else:
            print("Out of ammo or weapon is broken!")
            return 0

    def reload(self, ammo_count):
        self.ammo = min(ammo_count, self.max_ammo)  # Reload up to the maximum ammo count

    def __str__(self):
        return f"{self.name} (Damage: {self.damage}, Ammo: {self.ammo}/{self.max_ammo})"





class Zombie:
    loot_table = []  # Overridden per subclass below - class-level, not rebuilt per instance

    def __init__(self, name, health, attack):
        self.name = name
        self.health = health
        self.attack = attack

    def take_damage(self, damage):
        self.health -= damage

class FreshZombie(Zombie):
    loot_table = ["food", "water", "medicine"]

    def __init__(self):
        super().__init__("Fresh Zombie", 30, 5)

class RegularZombie(Zombie):
    loot_table = ["food", "water", "medicine", "weapon"]

    def __init__(self):
        super().__init__("Regular Zombie", 50, 10)

class HeavyZombie(Zombie):
    loot_table = ["food", "water", "medicine", "weapon", "ammo"]

    def __init__(self):
        super().__init__("Heavy Zombie", 100, 20)


@dataclass
class Goal:
    title: str
    description: str = ""
    completed: bool = False
    reward_type: str = "health"
    reward_amount: int = 5
    goal_type: str = ""

@dataclass
class PlayerClass:
    health: int
    hunger: int
    thirst: int
    fatigue: int
    strength: int
    dexterity: int
    intelligence: int
    wisdom: int
    equipped_weapon: "Weapon" = None

    def update_status(self, health_delta=0, hunger_delta=0, thirst_delta=0):
        self.health = max(0, min(100, self.health + health_delta))
        self.hunger = max(0, min(100, self.hunger + hunger_delta))
        self.thirst = max(0, min(100, self.thirst + thirst_delta))

class Apocrysis:
    crafting_recipes = {
        "steel_sword": {"ingredients": {"weapon": 1, "food": 2}, "result": lambda: MeleeWeapon("Steel Sword", 20, 50)},
        "heavy_bow": {"ingredients": {"weapon": 1, "ammo": 3}, "result": lambda: RangedWeapon("Heavy Bow", 25, 10)},
        "combat_knife": {"ingredients": {"weapon": 1, "medicine": 1}, "result": lambda: MeleeWeapon("Combat Knife", 15, 40)}
    }

    def __init__(self, name, player_class, map_size):
        self.map_size = map_size
        self.name = name
        self.player_class = player_class
        self.health = 100
        self.max_health = 100  # Maximum health at the start
        self.backpack = Backpack()
        self.equipped_weapon = None
        self.current_position = (self.map_size // 2, self.map_size // 2)
        self.visited = set()  # Initialize visited tiles tracker
        self.visited.add(self.current_position)  # Mark the initial position as visited
        self.initialize_player(player_class)
        self.zombie_positions = set()  # Initialize as an empty set
        self.status_effects = {}  # Track active status effects (e.g., Bleeding, Stun)
        self.goals = []  # Track player goals/objectives
        self.won = False  # Win condition tracker
        
        # Day/Night Cycle Initialization
        self.time_of_day = 480  # Start at 08:00 (minutes from midnight)
        self.visibility_radius = 3
        self.is_night = False
        self.day = 1
        self._update_time()
        
        self.generate_map()
        
        # Progression System Initialization
        self.xp = 0
        self.level = 1
        self.max_xp = 100

    def _update_time(self):
        prev_hour = self.time_of_day // 60
        # Advance time by 15 minutes per action/move
        self.time_of_day = (self.time_of_day + 15) % 1440
        hour = self.time_of_day // 60
        
        # Day increments when transitioning from night (<6) to day (>=6)
        if prev_hour < 6 and hour >= 6:
            self.day += 1
            
        # Night is from 20:00 to 06:00
        if hour >= 20 or hour < 6:
            self.is_night = True
            self.visibility_radius = 1
        else:
            self.is_night = False
            self.visibility_radius = 3

    def _apply_decay(self):
        # Hunger and thirst decay faster at night
        hunger_decay = 2 + (1 if self.is_night else 0)
        thirst_decay = 2 + (1 if self.is_night else 0)
        
        self.hunger = max(0, self.hunger - hunger_decay)
        self.thirst = max(0, self.thirst - thirst_decay)

    def print_stat_changes(self, old_stats):
        current_stats = {stat: getattr(self, stat) for stat in old_stats}

        changes = []
        for stat in old_stats:
            if current_stats[stat] != old_stats[stat]:
                diff = current_stats[stat] - old_stats[stat]
                sign = "+" if diff > 0 else ""
                color = GREEN if diff > 0 else RED
                changes.append(f"{BOLD}{color}{stat.capitalize()}: {sign}{diff}{RESET}")
        
        if changes:
            print("\n" + " | ".join(changes))

    def add_goal(self, title, description="", goal_type=""):
        self.goals.append(Goal(title=title, description=description, goal_type=goal_type))
        print(f"New goal added: {title}")

    def list_goals(self):
        if not self.goals:
            print("No active goals.")
            return
        print("\n--- Active Goals ---")
        for i, g in enumerate(self.goals):
            status = "[DONE]" if g.completed else "[ACTIVE]"
            reward_desc = f"Reward: +{g.reward_amount} {g.reward_type}"
            type_desc = f"Type: {g.goal_type or 'General'}"
            print(f"{i+1}. {status} {g.title} - {g.description or 'No description'} ({reward_desc}, {type_desc})")

    def complete_goal(self, index):
        if 0 <= index < len(self.goals) and not self.goals[index].completed:
            goal = self.goals[index]
            goal.completed = True
            print(f"Goal completed: {goal.title}!")
            
            # Apply reward
            if goal.reward_type == "health":
                self.health = min(100, self.health + goal.reward_amount)
            elif goal.reward_type == "fatigue":
                self.fatigue = max(0, self.fatigue - goal.reward_amount)
            elif goal.reward_type == "food":
                self.backpack.food += goal.reward_amount
            elif goal.reward_type == "water":
                self.backpack.water += goal.reward_amount
            elif goal.reward_type == "medicine":
                self.backpack.medicine += goal.reward_amount
                
            print(f"Reward applied: +{goal.reward_amount} {goal.reward_type}")
        else:
            print("Invalid goal index or already completed.")

    def _check_and_complete_goals(self, action_type):
        for i, g in enumerate(self.goals):
            if g.completed or not getattr(g, 'goal_type', None): continue
            
            if g.goal_type == action_type:
                self.complete_goal(i)

    def run_game_loop(self):
        try:
            term_width = shutil.get_terminal_size().columns
        except Exception:
            term_width = 80
            
        left_col_width = max(40, term_width // 2 - 1)
        right_col_width = term_width - left_col_width - 3

        while self.health > 0 and not getattr(self, 'won', False):
            # Visual separator between turns to prevent text overlap from previous screens
            print("\n" + "*" * term_width)
            
            left_lines = []
            right_lines = []

            # Left Panel: Map
            # Real bug found live: this used to be its own inline copy
            # of the map-rendering logic, separate from print_map()'s
            # - a fix applied to print_map() (terrain symbols, real
            # town feature letters, the legend) never showed up here,
            # since this is the rendering actually used every turn;
            # print_map() itself was only ever reached via the
            # explicit 'm'/'map' command. Sharing one method closes
            # that gap for good, not just for this one fix.
            left_lines.extend(self._render_map_lines())
            left_lines.extend(TERRAIN_LEGEND.split("\n"))

            # Right Panel: Stats & Inventory
            hour = self.time_of_day // 60
            minute = self.time_of_day % 60
            time_str = f"{hour:02d}:{minute:02d}"
            day_night = "Night" if self.is_night else "Day"
            
            right_lines.append(f"Time: {time_str} ({day_night})")
            right_lines.append("--- Player Stats ---")
            stats_list = [
                ("Day", self.day),
                ("Health", f"{self.health}/{self.max_health}"),
                ("Hunger", self.hunger),
                ("Thirst", self.thirst),
                ("Fatigue", self.fatigue),
                ("Strength", self.strength),
                ("Dexterity", self.dexterity),
                ("Intelligence", self.intelligence),
                ("Wisdom", self.wisdom),
                ("Level", self.level),
                ("XP", f"{self.xp}/{self.max_xp}"),
            ]
            for label, value in stats_list:
                right_lines.append(f"{label:<12} : {value}")
            
            if self.equipped_weapon:
                right_lines.append(f"{'Equipped Weapon':<12} : {self.equipped_weapon.name}")
            else:
                right_lines.append("Equipped Weapon : None")

            right_lines.append("")
            right_lines.append("--- Inventory ---")
            inv_list = [
                ("Food", self.backpack.food),
                ("Water", self.backpack.water),
                ("Medicine", self.backpack.medicine),
                ("Ammo", self.backpack.ammo),
            ]
            for label, value in inv_list:
                right_lines.append(f"{label:<12} : {value}")

            # Consolidated weapons section to fix positioning and overlap issues
            right_lines.append("--- Weapons ---")
            if self.equipped_weapon:
                right_lines.append(f"Equipped: {self.equipped_weapon}")
            
            if self.backpack.weapons:
                right_lines.append("Inventory:")
                for weapon in self.backpack.weapons:
                    right_lines.append(str(weapon))
            else:
                right_lines.append("No weapons in inventory.")

            # Commands
            cmd_list = ["n (north)", "s (south)", "e (east)", "w (west)", "m (map)", "i (inventory)", "st (stats)", "h (help)", "x (exit game)", "q (quit)", "sv (save)", "ds (delete save)"]
            cmd_list.append("go [title] (add goal)")
            cmd_list.append("goals (list goals)")
            cmd_list.append("complete [idx] (finish goal)")
            
            if self.backpack.weapons:
                cmd_list.append("eq [weapon name] (equip)")
            if isinstance(self.equipped_weapon, RangedWeapon):
                cmd_list.append(f"reload ({self.equipped_weapon.name})")
            
            cmd_list.append("cr [recipe] (craft) (type 'cr list' for recipes)")
            
            current_tile = self.map[self.current_position[1]][self.current_position[0]]
            if isinstance(current_tile, (FreshZombie, RegularZombie, HeavyZombie)):
                cmd_list.append("f (fight)")
            if self.backpack.food > 0:
                cmd_list.append("ea (eat)")
            if self.backpack.water > 0:
                cmd_list.append("dr (drink)")
            if self.backpack.medicine > 0:
                cmd_list.append("med (medicine)")

            right_lines.append("")
            right_lines.append("What would you like to do?")
            for c in cmd_list:
                right_lines.append(f"  {c}")

            # Render side-by-side with dynamic column widths to minimize spacing
            max_left_len = max((_visible_len(line) for line in left_lines), default=0)
            max_right_len = max((_visible_len(line) for line in right_lines), default=0)

            left_col_width = max_left_len + 2
            right_col_width = max_right_len

            max_rows = max(len(left_lines), len(right_lines))
            for i in range(max_rows):
                left_line = left_lines[i] if i < len(left_lines) else ""
                right_line = right_lines[i] if i < len(right_lines) else ""

                print(f"{_display_ljust(left_line, left_col_width)} | {_display_ljust(right_line, right_col_width)}")

            command = input("> ").lower()
            
            direction_aliases = {"north": "n", "south": "s", "east": "e", "west": "w"}
            command = direction_aliases.get(command, command)

            old_stats = {
                "health": self.health,
                "hunger": self.hunger,
                "thirst": self.thirst,
                "fatigue": self.fatigue,
                "strength": self.strength,
                "dexterity": self.dexterity,
                "intelligence": self.intelligence,
                "wisdom": self.wisdom,
                "level": self.level,
                "xp": self.xp,
            }

            dispatch_map = {
                'exit': lambda: print("Exiting game..."),
                'n': lambda: self.move_and_search('n'),
                's': lambda: self.move_and_search('s'),
                'e': lambda: self.move_and_search('e'),
                'w': lambda: self.move_and_search('w'),
                'm': self.print_map,
                'i': self.display_inventory,
                'st': self.stats,
                'h': self.print_help,
                '?': self.print_help,
                'q': lambda: print("Exiting game..."),
                'quit': lambda: print("Exiting game..."),
                'x': lambda: print("Exiting game..."),
                'exit game': lambda: print("Exiting game..."),
                'eat': self.eat,
                'ea': self.eat,
                'drink': self.drink,
                'dr': self.drink,
                'medicine': self.use_medicine,
                'med': self.use_medicine,
                'rest': self.rest,
                'r': self.rest,
                'auto': self.auto_play,
                'a': self.auto_play,
                'fight': lambda: self.encounter_zombie(),
                'f': lambda: self.encounter_zombie(),
                'save': lambda: self.save_game(input("Enter save slot name (e.g., 'Slot1'): ") + ".json"),
                'sv': lambda: self.save_game(input("Enter save slot name (e.g., 'Slot1'): ") + ".json"),
                'ds': lambda: self.delete_save(input("Enter save slot name to delete: ") + ".json"),
                'delete save': lambda: self.delete_save(input("Enter save slot name to delete: ") + ".json"),
                'go': lambda: self.add_goal(input("Goal title: "), goal_type=input("Goal type (eat/drink/medicine/craft/kill/reach_town): ").lower()),
                'goals': self.list_goals,
                'complete': lambda: self.complete_goal(int(input("Goal index (1-based): ")) - 1),
            }

            if command in ('q', 'quit'):
                save_choice = input("Do you want to save? (y/n): ").lower()
                if save_choice == 'y':
                    self.save_game(input("Enter save slot name (e.g., 'Slot1'): ") + ".json")
                print("\n" + "*" * term_width)
                self.quit = True
                break
            elif command in ('exit', 'x', 'exit game'):
                print("\n" + "*" * term_width)
                dispatch_map[command]()
                self.quit = True
                break
            
            action = dispatch_map.get(command)
            if action:
                print("\n" + "*" * term_width)
                action()
            elif command.startswith(('equip', 'eq')):
                parts = command.split()
                if len(parts) > 1:
                    self.equip_weapon(' '.join(parts[1:]))
                else:
                    print("Missing weapon name for equip.")
            elif command.startswith(('reload', 'rl')):
                parts = command.split()
                weapon_name = ' '.join(parts[1:]) if len(parts) > 1 else None
                
                target_weapon = self.equipped_weapon
                if weapon_name:
                    candidates = list(self.backpack.weapons)
                    if self.equipped_weapon:
                        candidates.append(self.equipped_weapon)
                    for w in candidates:
                        if isinstance(w, RangedWeapon) and w.name.lower() == weapon_name.lower():
                            target_weapon = w
                            break
                
                if target_weapon and isinstance(target_weapon, RangedWeapon):
                    ammo_input = input(f"How much ammo to reload {target_weapon.name} with? ")
                    try:
                        amount = int(ammo_input)
                        target_weapon.reload(amount)
                    except ValueError:
                        print("Invalid ammo count.")
                else:
                    print("No valid ranged weapon found to reload.")
            elif command.startswith(('craft', 'cr')):
                parts = command.split()
                if len(parts) > 1:
                    self.craft(parts[1])
                else:
                    print("Usage: craft [recipe_name] (type 'craft list' for recipes)")
            else:
                if command.startswith(('eat', 'ea')) and self.backpack.food <= 0:
                    print("No food in inventory to eat.")
                elif command.startswith(('drink', 'dr')) and self.backpack.water <= 0:
                    print("No water in inventory to drink.")
                elif command.startswith(('medicine', 'med')) and self.backpack.medicine <= 0:
                    print("No medicine in inventory to use.")
                else:
                    print(f"Unknown command: '{command}'. Type 'help' for available commands.")

            self.print_stat_changes(old_stats)

    def initialize_player(self, player_class):
        attrs = self.initialize_player_class(player_class)
        if attrs is None:
            attrs = self.initialize_player_class("gamer")

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

    @staticmethod
    def initialize_player_class(player_class_name):
        player_classes = {
            "husband": PlayerClass(100, 90, 90, 5, 12, 10, 10, 10, MeleeWeapon("Kitchen Knife", 6, 80)),
            "grandpa": PlayerClass(90, 85, 85, 10, 8, 7, 14, 16, MeleeWeapon("Walking Cane", 4, 100)),
            "gamer": PlayerClass(95, 95, 95, 0, 10, 12, 13, 8, MeleeWeapon("Switchblade", 7, 60)),
            "office worker": PlayerClass(100, 90, 90, 5, 9, 9, 11, 11, MeleeWeapon("Letter Opener", 4, 50)),
            "engineer": PlayerClass(95, 90, 90, 5, 11, 12, 16, 12, RangedWeapon("Pipe Gun", 12, 8)),
            "student": PlayerClass(100, 100, 100, 0, 10, 11, 12, 9, MeleeWeapon("Baseball Bat", 8, 70)),
            "teacher": PlayerClass(100, 95, 95, 0, 9, 10, 14, 13, MeleeWeapon("Chalk Eraser", 3, 40)),
            "chef": PlayerClass(105, 85, 85, 5, 14, 12, 10, 9, MeleeWeapon("Chef's Knife", 10, 60)),
            "artist": PlayerClass(95, 90, 90, 5, 8, 13, 15, 12, MeleeWeapon('Palette Knife', 5, 45)),
            "prepper": PlayerClass(110, 80, 80, 0, 13, 11, 12, 13, RangedWeapon("Hunting Rifle", 18, 6)),
            "survivalist": PlayerClass(115, 75, 75, 5, 14, 10, 11, 14, MeleeWeapon("Hatchet", 12, 90)),
            "army ranger": PlayerClass(110, 85, 85, 0, 13, 15, 10, 8, RangedWeapon("Assault Rifle", 20, 10)),
            "medic": PlayerClass(100, 95, 95, 0, 7, 9, 16, 15, MeleeWeapon("Scalpel", 5, 80)),
            "hunter": PlayerClass(105, 80, 80, 5, 12, 14, 13, 12, RangedWeapon("Compound Bow", 16, 12)),
            "farmer": PlayerClass(110, 90, 90, 5, 15, 8, 9, 10, MeleeWeapon("Pitchfork", 11, 70)),
            "mechanic": PlayerClass(100, 90, 90, 5, 12, 13, 14, 11, RangedWeapon("Wrench Gun", 14, 8)),
            "pro gamer": PlayerClass(120, 100, 100, 0, 15, 16, 16, 15, MeleeWeapon("Fixed Blade Knife", 10, 100)),
            "scavenger": PlayerClass(90, 110, 110, 5, 8, 12, 14, 10, MeleeWeapon("Crowbar", 7, 100)),
            "soldier": PlayerClass(115, 85, 85, 0, 14, 13, 11, 9, RangedWeapon("Pistol", 15, 12)),
            "police officer": PlayerClass(110, 90, 90, 0, 12, 14, 12, 11, RangedWeapon("Service Revolver", 16, 8)),
            "doctor": PlayerClass(105, 95, 95, 0, 8, 10, 17, 16, MeleeWeapon("Surgical Scissors", 6, 70)),
            "scientist": PlayerClass(95, 90, 90, 5, 7, 11, 18, 14, MeleeWeapon("Lab Pipette", 3, 30)),
        }
        
        if player_class_name in player_classes:
            return player_classes[player_class_name]
        else:
            print(f"Invalid player class '{player_class_name}' selected. Defaulting to 'gamer'.")
            return None

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

    def encounter_zombie(self, current_tile=None):
        # Use passed tile if available and valid, otherwise generate a random one
        if current_tile and isinstance(current_tile, (FreshZombie, RegularZombie, HeavyZombie)):
            zombie = current_tile
        else:
            zombie = self._select_zombie_for_encounter()
            
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
            # Process status effects at start of turn
            if self.status_effects.get("Stun", 0) > 0:
                print(f"You are stunned! Turn skipped.")
                self.status_effects["Stun"] -= 1
            elif self.equipped_weapon:
                damage = self.equipped_weapon.use() + max(0, self.strength // 3)
                
                # Critical hit chance scaled by dexterity
                crit_chance = min(0.25, self.dexterity / 200)
                if random.random() < crit_chance:
                    damage *= 2
                    print("Critical Hit!")
                    
                zombie.take_damage(damage)
                print(f"The {zombie.name} takes {damage} damage.")
            else:
                print("You have no weapon equipped and attempt to fight with your hands!")
                zombie.take_damage(2)  # Minimal damage when unarmed
                print("You deal 2 damage with your bare hands.")

            # Process status effects (e.g., Bleeding)
            for effect, turns in list(self.status_effects.items()):
                if effect == "Bleeding":
                    bleed_dmg = 2
                    self.health -= bleed_dmg
                    print(f"You are bleeding! Lost {bleed_dmg} health.")
                    self.status_effects[effect] -= 1

            # Check if the zombie has been defeated
            if zombie.health <= 0:
                print(f"The {zombie.name} has been defeated!")
                self.award_xp(25)
                self.handle_loot(zombie.loot_table)
                self._check_and_complete_goals("kill")
                return

            # Zombie's turn to attack if it is still alive
            if zombie.health > 0:
                dodge_chance = min(0.5, self.dexterity / 150)
                if random.random() < dodge_chance:
                    print(f"You deftly dodged the {zombie.name}'s attack!")
                else:
                    self.take_damage(zombie.attack)
                    
                    # Chance to inflict status effect
                    status_roll = random.random()
                    if status_roll < 0.15 and "Bleeding" not in self.status_effects:
                        self.status_effects["Bleeding"] = 3
                        print("You are bleeding! You will take damage each turn.")
                    elif status_roll < 0.25 and "Stun" not in self.status_effects:
                        self.status_effects["Stun"] = 1
                        print("You have been stunned!")

            # Check for critical health condition for fleeing chance
            if 0 < self.health <= self.max_health * 0.1:
                print("You are critically wounded!")
                if random.random() < 0.1:  # 10% chance to flee successfully
                    print("In a desperate move, you managed to flee from the zombie.")
                    return
                else:
                    print("Unable to flee, you brace yourself for the zombie's attack.")

        if self.health <= 0:
            print("You are critically wounded and unable to continue the fight!")

    def award_xp(self, amount):
        if amount <= 0: return
        self.xp += amount
        while self.xp >= self.max_xp:
            self.xp -= self.max_xp
            self.level_up()
            self.max_xp = int(self.max_xp * 1.5)

    def level_up(self):
        self.level += 1
        self.strength += 1
        self.dexterity += 1
        self.intelligence += 1
        self.wisdom += 1
        self.max_health += 5
        self.health = min(100, self.health + 10)
        print(f"{BOLD}{GREEN}Level Up! You are now level {self.level}.{RESET}")

    def save_game(self, filename="apocrysis_save.json"):
        data = {
            "name": self.name,
            "health": self.health,
            "hunger": self.hunger,
            "thirst": self.thirst,
            "fatigue": self.fatigue,
            "strength": self.strength,
            "dexterity": self.dexterity,
            "intelligence": self.intelligence,
            "wisdom": self.wisdom,
            "level": self.level,
            "xp": self.xp,
            "max_xp": self.max_xp,
            "current_position": list(self.current_position),
            "time_of_day": self.time_of_day,
            "visited": [list(pos) for pos in self.visited],
            "backpack_food": self.backpack.food,
            "backpack_water": self.backpack.water,
            "backpack_medicine": self.backpack.medicine,
            "backpack_ammo": self.backpack.ammo,
            "weapons": [],
            "equipped_weapon": None,
            "goals": [{"title": g.title, "description": g.description, "completed": g.completed, "reward_type": g.reward_type, "reward_amount": g.reward_amount, "goal_type": getattr(g, 'goal_type', "")} for g in self.goals],
            "status_effects": self.status_effects
        }

        for w in self.backpack.weapons:
            data["weapons"].append({
                "name": w.name,
                "damage": w.damage,
                "type": type(w).__name__,
                "durability": getattr(w, 'durability', None),
                "ammo": getattr(w, 'ammo', None),
                "max_ammo": getattr(w, 'max_ammo', None)
            })

        if self.equipped_weapon:
            data["equipped_weapon"] = {
                "name": self.equipped_weapon.name,
                "damage": self.equipped_weapon.damage,
                "type": type(self.equipped_weapon).__name__,
                "durability": getattr(self.equipped_weapon, 'durability', None),
                "ammo": getattr(self.equipped_weapon, 'ammo', None),
                "max_ammo": getattr(self.equipped_weapon, 'max_ammo', None)
            }

        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Game saved to {filename}.")

    def delete_save(self, filename="apocrysis_save.json"):
        if os.path.exists(filename):
            os.remove(filename)
            print(f"Saved game deleted from {filename}.")
        else:
            print("No saved game found to delete.")

    @classmethod
    def load_game(cls, filename="apocrysis_save.json"):
        if not os.path.exists(filename):
            return None
            
        with open(filename, 'r') as f:
            data = json.load(f)
            
        player = cls(data.get("name", "SavedPlayer"), "gamer", 25)

        player.health = data.get("health", 100)
        player.hunger = data.get("hunger", 95)
        player.thirst = data.get("thirst", 95)
        player.fatigue = data.get("fatigue", 0)
        player.strength = data.get("strength", 10)
        player.dexterity = data.get("dexterity", 12)
        player.intelligence = data.get("intelligence", 13)
        player.wisdom = data.get("wisdom", 8)
        player.level = data.get("level", 1)
        player.xp = data.get("xp", 0)
        player.max_xp = data.get("max_xp", 100)
        
        player.current_position = tuple(data.get("current_position", [12, 12]))
        player.time_of_day = data.get("time_of_day", 480)
        player.visited = set(tuple(pos) for pos in data.get("visited", []))
        
        player.backpack.food = data.get("backpack_food", 0)
        player.backpack.water = data.get("backpack_water", 0)
        player.backpack.medicine = data.get("backpack_medicine", 0)
        player.backpack.ammo = data.get("backpack_ammo", 0)
        
        for w_data in data.get("weapons", []):
            if w_data.get("type") == "MeleeWeapon":
                w = MeleeWeapon(w_data.get("name"), w_data.get("damage"), w_data.get("durability", 10))
            else:
                w = RangedWeapon(w_data.get("name"), w_data.get("damage"), w_data.get("max_ammo", 5))
                w.ammo = w_data.get("ammo")
            player.backpack.weapons.append(w)
            
        eq_w_data = data.get("equipped_weapon")
        if eq_w_data and eq_w_data.get("name"):
            if eq_w_data.get("type") == "MeleeWeapon":
                player.equipped_weapon = MeleeWeapon(eq_w_data.get("name"), eq_w_data.get("damage"), eq_w_data.get("durability", 10))
            else:
                player.equipped_weapon = RangedWeapon(eq_w_data.get("name"), eq_w_data.get("damage"), eq_w_data.get("max_ammo", 5))
                player.equipped_weapon.ammo = eq_w_data.get("ammo")
                
        for g_data in data.get("goals", []):
            player.goals.append(Goal(
                title=g_data["title"],
                description=g_data.get("description", ""),
                completed=g_data.get("completed", False),
                reward_type=g_data.get("reward_type", "health"),
                reward_amount=g_data.get("reward_amount", 5),
                goal_type=g_data.get("goal_type", "")
            ))

        player.status_effects = data.get("status_effects", {})
                
        return player

    def _render_map_lines(self):
        # Shared by print_map() (the standalone 'm'/'map' command) and
        # run_game_loop()'s per-turn left panel - a single source of
        # truth so a rendering fix here can never again land in one
        # call site and silently not exist in the other (see the
        # comment at run_game_loop()'s own left-panel block for what
        # that gap actually looked like live).
        border = '*' * (len(self.map[0]) + 2)
        lines = [border]

        for y, row in enumerate(self.map):
            line = '*'
            for x, tile in enumerate(row):
                dist = abs(x - self.current_position[0]) + abs(y - self.current_position[1])
                in_range = dist <= self.visibility_radius
                if (x, y) == self.current_position:
                    health_pct = self.health / max(1, self.max_health) * 100
                    if health_pct > 75:
                        color = GREEN
                    elif health_pct > 40:
                        color = YELLOW
                    else:
                        color = RED
                    char = f"{BOLD}{color}P{RESET}"
                elif isinstance(tile, dict):
                    if tile.get('terrain') == 'town':
                        # Real bug found live: this used to hardcode
                        # 'T' for EVERY town tile no matter which
                        # feature (House/Road/Shop/Building/Town
                        # center) generate_map() actually assigned to
                        # it - town_features' letters were stored in
                        # tile['content'] but never rendered, so the
                        # whole town always looked like a uniform
                        # block of 'T's. Showing the real feature
                        # letter is what "what does TTT mean" was
                        # actually asking about.
                        char = tile.get('content') or 'T'
                    elif in_range:
                        # Show real terrain (forest/water/building/
                        # plain), not a blanket '-' - see
                        # TERRAIN_SYMBOLS above.
                        char = TERRAIN_SYMBOLS.get(tile.get('terrain'), '.')
                    elif (x, y) in self.visited:
                        char = '.'
                    else:
                        char = ' '
                elif isinstance(tile, (FreshZombie, RegularZombie, HeavyZombie)):
                    char = 'Z' if in_range and (x, y) in self.visited else ' '
                else:
                    char = '.' if in_range and (x, y) in self.visited else ' '
                line += char
            line += '*'
            lines.append(line)

        lines.append(border)
        return lines

    def print_map(self):
        for line in self._render_map_lines():
            print(line)
        print(TERRAIN_LEGEND)

    def handle_loot(self, loot_table):
        # Intelligence increases number of items found from loot tables
        extra_items = max(0, self.intelligence // 25)
        k = min(4, random.randint(1, 3) + extra_items)
        dropped_loot = random.choices(loot_table, k=k)  # Randomly choose items from loot table
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

    def print_help(self):
        print("\n--- Help ---")
        print("Available commands:")
        print("  n (north), s (south), e (east), w (west) - Move")
        print("  m (map)                                 - Display the current map")
        print("  i (inventory)                           - Show your backpack contents")
        print("  st (stats)                              - View player statistics")
        print("  f (fight)                               - Fight the zombie on your current tile")
        print("  eq [name] (equip)                       - Equip a weapon from your inventory")
        if self.backpack.food > 0:
            print("  ea (eat)                                - Consume food to reduce hunger and restore health")
        if self.backpack.water > 0:
            print("  dr (drink)                              - Consume water to reduce thirst and restore health")
        if self.backpack.medicine > 0:
            print("  med (medicine)                          - Use medicine to restore health")
        print("  cr [name] (craft)                       - Combine items into upgraded gear (type 'cr list' for recipes)")
        print("  r (rest)                                - Rest to recover fatigue (rate based on Wisdom)")
        print("  a (auto)                                - Automatically play for a short duration")
        print("  q, x, quit                              - Quit the game")
        print("  h, ? (help)                             - Show this message\n")

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
            
            # Wisdom improves fatigue recovery rate
            fatigue_recovery = max(0, self.wisdom // 4)
            self.fatigue = max(0, self.fatigue - fatigue_recovery)
            self._check_and_complete_goals("eat")
        else:
            print("You have no food.")

    def drink(self):
        if self.backpack.water > 0:
            self.backpack.water -= 1
            self.thirst = min(100, self.thirst + 5)  # Adjust value as per game mechanics
            self.health = min(100, self.health + 5)  # Health increases by 5 when drinking, up to a max of 100
            print("You drink some water. Thirst increased. Health restored.")
            
            # Wisdom improves fatigue recovery rate
            fatigue_recovery = max(0, self.wisdom // 4)
            self.fatigue = max(0, self.fatigue - fatigue_recovery)
            self._check_and_complete_goals("drink")
        else:
            print("You have no water.")

    def use_medicine(self):
        if self.backpack.medicine > 0:
            self.backpack.medicine -= 1
            self.health = min(100, self.health + 20)  # Adjust value as per game mechanics
            print("You use medicine. Health increased.")
            
            # Wisdom improves fatigue recovery rate
            fatigue_recovery = max(0, self.wisdom // 4)
            self.fatigue = max(0, self.fatigue - fatigue_recovery)
            self._check_and_complete_goals("medicine")
        else:
            print("You have no medicine.")

    def rest(self):
        """Rest to recover fatigue. Recovery rate is based on Wisdom stat."""
        if self.fatigue <= 0:
            print("You are fully rested!")
            return
        
        recovery_rate = max(5, self.wisdom // 2)
        recovered = min(self.fatigue, recovery_rate)
        self.fatigue -= recovered
        print(f"You rest and recover {recovered} fatigue. Current fatigue: {self.fatigue}")

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

    def craft(self, recipe_key):
        if recipe_key == "list":
            print("\n--- Available Crafting Recipes ---")
            for key, data in self.crafting_recipes.items():
                ing_str = ", ".join([f"{v} {k}" for k, v in data["ingredients"].items()])
                result_name = data["result"]().name
                print(f"  {key}: Requires {ing_str} -> Creates {result_name}")
            return

        if recipe_key not in self.crafting_recipes:
            print(f"Unknown recipe: '{recipe_key}'. Type 'craft list' to see available recipes.")
            return
            
        recipe = self.crafting_recipes[recipe_key]
        ingredients = recipe["ingredients"]
        
        # Check consumables
        for item_type, count in ingredients.items():
            if item_type != "weapon":
                current_count = getattr(self.backpack, item_type)
                if current_count < count:
                    print(f"Not enough {item_type} to craft. Need {count}, have {current_count}.")
                    return
        
        # Check weapon
        if ingredients.get("weapon", 0) > 0 and len(self.backpack.weapons) == 0:
            print("No weapons in inventory to combine.")
            return
            
        # Consume items
        for item_type, count in ingredients.items():
            if item_type != "weapon":
                setattr(self.backpack, item_type, getattr(self.backpack, item_type) - count)
            elif item_type == "weapon" and self.backpack.weapons:
                removed = self.backpack.weapons.pop(0)
                print(f"Used {removed.name} for crafting.")
                
        # Add result
        new_item = recipe["result"]()
        self.backpack.weapons.append(new_item)
        print(f"Crafted a {new_item.name}!")
        self._check_and_complete_goals("craft")

    def auto_play(self):
        print("\nAuto-playing game...\n")
        actions = ['n', 's', 'e', 'w']
        max_steps = 100
        step_count = 0
        
        while self.health > 0 and step_count < max_steps:
            action = random.choice(actions)
            self.move_and_search(action)
            print(f"Automatically moving {action}")

            if self.hunger < 50 and self.backpack.food > 0:
                self.eat()
                print("Automatically eating to reduce hunger.")
            if self.thirst < 50 and self.backpack.water > 0:
                self.drink()
                print("Automatically drinking to reduce thirst.")

            if self.health < 75 and self.backpack.medicine > 0:
                self.use_medicine()
                print("Automatically using medicine to heal.")

            step_count += 1
            
            # Explicit stop condition based on player state changes
            if self.health <= 0:
                print("Auto-play ending due to critical health.")
                break
                
        if step_count >= max_steps:
            print(f"Auto-play ended after reaching maximum step limit ({max_steps}).")

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
        Reduces the player's health by the specified damage amount.
        """
        self.health -= damage
        print(f"The {self.name} takes {damage} damage. Its current health is {self.health}.")
        if self.health <= 0:
            print(f"The {self.name} has been defeated!")

    def increase_max_health(self, amount):
      self.max_health += amount
      self.health = self.max_health


def main():
    while True:
        player = None
        # List available save files for convenience
        try:
            save_files = [f for f in os.listdir(".") if f.endswith(".json")]
        except OSError:
            save_files = []
            
        if save_files:
            print("Available save files:", ", ".join(save_files))
        load_choice = input("Load saved game? (y/n): ").lower()
        if load_choice == 'y':
            filename = input("Enter save file name (e.g., 'apocrysis_save.json'): ")
            player = Apocrysis.load_game(filename)
        
        if player is None:
            name = input("Enter your name: ")
            
            class_list = [
                "husband", "grandpa", "gamer", "office worker", "engineer", 
                "student", "teacher", "chef", "artist", "prepper", 
                "survivalist", "army ranger", "medic", "hunter", "farmer", 
                "mechanic", "pro gamer", "scavenger", "soldier", "police officer", 
                "doctor", "scientist"
            ]
            
            print("\nAvailable Classes:")
            for i, cls in enumerate(class_list, 1):
                print(f"{i}. {cls}")
                
            while True:
                selection = input("Choose your class (number or name): ").strip().lower()
                if not selection:
                    continue
                    
                try:
                    idx = int(selection)
                    if 1 <= idx <= len(class_list):
                        player_class = class_list[idx - 1]
                        break
                    else:
                        print(f"Please enter a number between 1 and {len(class_list)}.")
                except ValueError:
                    if selection in class_list:
                        player_class = selection
                        break
                    else:
                        print("Invalid selection. Please try again.")

            map_size = 25
            while True:
                try:
                    map_size_input = input(f"Enter the size of the game board (default {map_size}): ")
                    if not map_size_input.strip():
                        break
                    new_map_size = int(map_size_input)
                    if new_map_size <= 0 or new_map_size > 50:
                        raise ValueError
                    map_size = new_map_size
                    break
                except ValueError:
                    print("Invalid input. Please enter a positive integer for the game board size (max 50).")

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
        print(f"{player.name}, a once unassuming person with a knack for survival and a heart brimming ")
        print("with resilience, found himself cast into the heart of this apocalyptic nightmare. While the world around him ")
        print(f"succumbed to despair and ruin, {player.name}'s resolve to endure, to fight, and to carve out a semblance of hope amid ")
        print("the desolation became the beacon that guided his every step. As society crumbled and the vestiges of humanity ")
        print(f"dwindled, {player.name}'s journey through this dystopian world became a testament to the indomitable spirit of those who ")
        print("refuse to be extinguished, even in the darkest of times.")
        print(" ")
        player.run_game_loop()

        if getattr(player, 'quit', False) or player.health <= 0 or getattr(player, 'won', False):
            print("Thanks for playing!")
            break

def run_tests():
    print("Running tests for apocrysis.py...")
    
    # Test Backpack
    bp = Backpack()
    assert bp.food == 0 and bp.water == 0 and bp.medicine == 0 and bp.ammo == 0
    assert len(bp.weapons) == 0
    
    bp.add_item("food")
    assert bp.food == 1
    bp.add_item("water")
    assert bp.water == 1
    bp.add_item("medicine")
    assert bp.medicine == 1
    bp.add_item("ammo")
    assert bp.ammo == 1
    
    # Test MeleeWeapon
    mw = MeleeWeapon("Sword", 10, 5)
    assert mw.damage == 10 and mw.durability == 5
    dmg = mw.use()
    assert dmg == 10 and mw.durability == 4
    for _ in range(4):
        mw.use()
    assert mw.durability == 0
    dmg = mw.use()
    assert dmg == 0
    
    # Test RangedWeapon
    rw = RangedWeapon("Gun", 15, 3)
    assert rw.ammo == 3 and rw.max_ammo == 3 and rw.durability == 20
    dmg = rw.use()
    assert dmg == 15 and rw.ammo == 2 and rw.durability == 19
    dmg = rw.use()
    assert dmg == 15 and rw.ammo == 1 and rw.durability == 18
    dmg = rw.use()
    assert dmg == 15 and rw.ammo == 0 and rw.durability == 17
    dmg = rw.use()
    assert dmg == 0
    
    rw.reload(5)
    assert rw.ammo == 3 # capped at max_ammo
    
    # Test Zombies
    fz = FreshZombie()
    assert fz.name == "Fresh Zombie" and fz.health == 30
    fz.take_damage(10)
    assert fz.health == 20
    
    rz = RegularZombie()
    assert rz.name == "Regular Zombie" and rz.health == 50
    
    hz = HeavyZombie()
    assert hz.name == "Heavy Zombie" and hz.health == 100
    
    # Test PlayerClass & Apocrysis initialization
    pc = PlayerClass(100, 100, 100, 0, 10, 10, 10, 10, MeleeWeapon("Knife", 5, 10))
    assert pc.health == 100
    
    # Test Apocrysis map size and player setup
    ap = Apocrysis("TestPlayer", "gamer", 10)
    assert ap.map_size == 10
    assert len(ap.map) == 10
    assert ap.player_class is not None
    assert ap.health > 0
    assert hasattr(ap, 'status_effects')
    
    # NEW TEST: Battle, Inventory Management, and Stat Modifications
    print("\nRunning advanced feature tests...")
    
    # Test stat modifications (eat/drink/medicine)
    ap_stats = Apocrysis("StatTest", "gamer", 5)
    initial_health = ap_stats.health
    
    ap_stats.backpack.food += 10
    ap_stats.eat()
    assert ap_stats.hunger > 0, "Hunger should increase after eating"
    assert ap_stats.health == min(100, initial_health + 5), "Health should increase by 5 after eating"
    
    ap_stats.backpack.water += 10
    ap_stats.drink()
    assert ap_stats.thirst > 0, "Thirst should increase after drinking"
    assert ap_stats.health == min(100, initial_health + 10), "Health should increase by another 5 after drinking"
    
    ap_stats.backpack.medicine += 1
    current_health = ap_stats.health
    ap_stats.use_medicine()
    assert ap_stats.health == min(100, current_health + 20), "Health should increase by 20 after using medicine"
    
    # Test weapon equipping and battle logic
    ap_battle = Apocrysis("BattleTest", "engineer", 5)
    # Engineer starts with a crossbow. Add a melee weapon to test equip swap.
    ap_battle.backpack.weapons.append(MeleeWeapon("Axe", 8, 50))
    
    assert len(ap_battle.backpack.weapons) == 1, "Backpack should contain the added Axe"
    assert isinstance(ap_battle.equipped_weapon, RangedWeapon), "Engineer should start equipped with a ranged weapon"
    
    # Equip the axe
    ap_battle.equip_weapon("axe")
    assert ap_battle.equipped_weapon.name.lower() == "axe", "Equipped weapon should be Axe after command"
    assert len(ap_battle.backpack.weapons) == 1, "Crossbow should return to backpack when equipping new weapon"
    
    # Deal one attack round with the newly equipped axe. Not
    # ap_battle.battle(...) - that method was removed as dead code
    # (encounter_zombie() is the real, only combat path now), and
    # encounter_zombie() itself calls input() for the fight/flee
    # prompt, which would hang a non-interactive test run.
    test_zombie = FreshZombie()
    initial_z_health = test_zombie.health
    damage = ap_battle.equipped_weapon.use() + max(0, ap_battle.strength // 3)
    test_zombie.take_damage(damage)
    assert test_zombie.health < initial_z_health, "Zombie health should decrease after taking weapon damage"
    assert 0 <= ap_battle.health <= 100, "Player health must remain within valid bounds"
    
    print("All tests passed!")

if __name__ == "__main__":
    if "--test" in sys.argv:
        run_tests()
    else:
        main()