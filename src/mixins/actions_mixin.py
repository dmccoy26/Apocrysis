# Auto-extracted from the original monolithic apocrysis.py during
# the src/ restructuring - see README.md for the project layout.

import random

from src.items import MeleeWeapon, RangedWeapon
from src.player import PLAYER_CLASSES


class ActionsMixin:

    crafting_recipes = {
        "steel_sword": {"ingredients": {"weapon": 1, "food": 2}, "result": lambda: MeleeWeapon("Steel Sword", 20, 50)},
        "heavy_bow": {"ingredients": {"weapon": 1, "ammo": 3}, "result": lambda: RangedWeapon("Heavy Bow", 25, 10)},
        "combat_knife": {"ingredients": {"weapon": 1, "medicine": 1}, "result": lambda: MeleeWeapon("Combat Knife", 15, 40)}
    }

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
        if player_class_name in PLAYER_CLASSES:
            return PLAYER_CLASSES[player_class_name]
        else:
            print(f"Invalid player class '{player_class_name}' selected. Defaulting to 'gamer'.")
            return None

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

    def increase_max_health(self, amount):
      self.max_health += amount
      self.health = self.max_health

