# Auto-extracted from the original monolithic apocrysis.py during
# the src/ restructuring - see README.md for the project layout.

import random
import shutil

from src.constants import BOLD, GREEN, RED, RESET, YELLOW, TERRAIN_LEGEND, TERRAIN_SYMBOLS
from src.items import RangedWeapon
from src.text_utils import _visible_len, _display_ljust
from src.zombies import FreshZombie, RegularZombie, HeavyZombie


class UIMixin:

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

            # Tasks Section (Dynamic Objectives)
            active_tasks = [t for t in self.tasks if not t.completed]
            if active_tasks:
                right_lines.append("")
                right_lines.append("--- Active Tasks ---")
                for i, task in enumerate(active_tasks):
                    reward_info = f"+{task.reward_amount} {task.reward_type}"
                    right_lines.append(f"  [{i+1}] {task.title} ({reward_info})")

            # Commands
            cmd_list = ["n (north)", "s (south)", "e (east)", "w (west)", "m (map)", "i (inventory)", "st (stats)", "h (help)", "x (exit game)", "q (quit)", "sv (save)", "ds (delete save)"]
            cmd_list.append("go [title] (add goal)")
            cmd_list.append("goals (list goals)")
            cmd_list.append("complete [idx] (finish goal)")
            cmd_list.append("ts (tasks)")
            cmd_list.append("ct [idx] (complete task)")
            
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

            # Track action for automatic goal completion
            self.last_action = self._map_command_to_action(command)

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
                'ds': self._prompt_delete_save,
                'delete save': self._prompt_delete_save,
                'go': lambda: self.add_goal(input("Goal title: "), goal_type=input("Goal type (eat/drink/medicine/craft/kill/reach_town): ").lower()),
                'goals': self.list_goals,
                'complete': self._prompt_complete_goal,
                'ts': self.list_tasks,
                'ct': self._prompt_complete_task,
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
                print(f"Unknown command: '{command}'. Type 'help' for available commands.")

            self.print_stat_changes(old_stats)
            # Automatically check and complete goals based on the performed action
            self._auto_check_goals()
            
            # Generate new dynamic tasks periodically or when conditions change
            if random.random() < 0.1:  # 10% chance per turn to evaluate task generation
                self._generate_dynamic_tasks()

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
        print("  ts                                      - View active tasks")
        print("  ct [idx]                                - Complete a task by index")
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

    def _map_command_to_action(self, command):
        if command in ('eat', 'ea'): return 'eat'
        if command in ('drink', 'dr'): return 'drink'
        if command.startswith(('craft', 'cr')): return 'craft'
        if command in ('fight', 'f'): return 'kill'
        if command == 'm': return 'map'
        if command in ('n', 's', 'e', 'w'): return 'move'
        if command in ('rest', 'r'): return 'rest'
        if command.startswith(('equip', 'eq')): return 'equip'
        if command.startswith('reload'): return 'reload'
        return ''

