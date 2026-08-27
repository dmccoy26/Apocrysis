# Auto-extracted from the original monolithic apocrysis.py during
# the src/ restructuring - see README.md for the project layout.

import copy
import random

from src.items import MeleeWeapon, RangedWeapon, format_weapon_list, format_armor_list
from src.player import PLAYER_CLASSES, STARTER_CLASS_NAME


class ActionsMixin:

    # v3 SPRINT step 4: min_level gates a real tiered progression -
    # the original 3 recipes stay at level 1 (no regression), several
    # new ones unlock at higher levels, spanning the same existing
    # ingredient types (food/water/medicine/ammo/weapon - no new
    # resource types, so Backpack needs no changes).
    crafting_recipes = {
        "steel_sword": {"ingredients": {"weapon": 1, "food": 2}, "min_level": 1, "result_name": "Steel Sword", "result": lambda: MeleeWeapon("Steel Sword", 20, 50)},
        "repair_kit": {"ingredients": {"medicine": 2, "food": 1}, "min_level": 8, "result_name": "Repair Kit", "result": None},
        "heavy_bow": {"ingredients": {"weapon": 1, "ammo": 3}, "min_level": 1, "result_name": "Heavy Bow", "result": lambda: RangedWeapon("Heavy Bow", 25, 10)},
        "combat_knife": {"ingredients": {"weapon": 1, "medicine": 1}, "min_level": 1, "result_name": "Combat Knife", "result": lambda: MeleeWeapon("Combat Knife", 15, 40)},
        "reinforced_blade": {"ingredients": {"weapon": 1, "medicine": 1, "food": 1}, "min_level": 4, "result_name": "Reinforced Blade", "result": lambda: MeleeWeapon("Reinforced Blade", 28, 60)},
        "hunting_crossbow": {"ingredients": {"weapon": 1, "ammo": 5, "food": 1}, "min_level": 6, "result_name": "Hunting Crossbow", "result": lambda: RangedWeapon("Hunting Crossbow", 30, 15)},
        "survivor_machete": {"ingredients": {"weapon": 2, "water": 2}, "min_level": 9, "result_name": "Survivor Machete", "result": lambda: MeleeWeapon("Survivor Machete", 35, 70)},
        "military_carbine": {"ingredients": {"weapon": 1, "ammo": 8, "medicine": 2}, "min_level": 13, "result_name": "Military Carbine", "result": lambda: RangedWeapon("Military Carbine", 45, 20)},
        "apex_blade": {"ingredients": {"weapon": 2, "medicine": 3, "food": 3}, "min_level": 18, "result_name": "Apex Blade", "result": lambda: MeleeWeapon("Apex Blade", 55, 100)},
    }

    def initialize_player(self):
        # v3: no class choice at game start (SPRINT plan, step 1) -
        # every new game begins as the easiest tier's representative
        # class (src/player.py's STARTER_CLASS_NAME). Stat growth
        # from there comes from leveling and tier blending
        # (combat_mixin.py's level_up()), not an initial pick.
        attrs = self.initialize_player_class(STARTER_CLASS_NAME)
        # Kept for save-file/display compatibility - no longer a
        # user choice, tracks the current tier's representative class
        # (updated by combat_mixin.py's level_up() on a tier-up).
        self.player_class = STARTER_CLASS_NAME

        self.health = attrs.health
        self.hunger = attrs.hunger
        self.thirst = attrs.thirst
        self.fatigue = attrs.fatigue
        self.strength = attrs.strength
        self.dexterity = attrs.dexterity
        self.intelligence = attrs.intelligence
        self.wisdom = attrs.wisdom
        # Real bug found live (via the new autoplay balance harness
        # running many games in one process): PLAYER_CLASSES' weapons
        # are single module-level instances, shared by every player
        # who ever rolls that starter/tier class - attrs.equipped_
        # weapon is that same object, not a fresh one. Combat mutates
        # durability/ammo in place, so without copying here, one
        # game's wear and tear on "Kitchen Knife" permanently carries
        # into every future game (or TUI win-continuation - see
        # tui.py's _game_thread()) that rolls the same class, for the
        # rest of the process's lifetime.
        self.equipped_weapon = copy.deepcopy(attrs.equipped_weapon)
        if self.equipped_weapon.name == 'Kitchen Knife':
            variant_name = self.rng.choice(['Kitchen Knife', 'Rolling Pin', 'Frying Pan', 'Screwdriver'])
            self.equipped_weapon.name = variant_name
        # RangedWeapon.__init__ already starts ammo at max_ammo - no
        # separate top-up needed here.

    def initialize_player_class(self, player_class_name):
        # No longer @staticmethod (v3 SPRINT step 6) - the fallback
        # message below needs self.io. Always called as
        # self.initialize_player_class(...) already, so this changes
        # nothing at any call site.
        if player_class_name in PLAYER_CLASSES:
            return PLAYER_CLASSES[player_class_name]
        else:
            self.io.say(f"Invalid player class '{player_class_name}' selected. Defaulting to 'gamer'.")
            return None

    def eat(self):
        if self.backpack.food > 0:
            self.backpack.food -= 1
            self.hunger = min(100, self.hunger + 5)  # Adjust value as per game mechanics
            self.health = min(100, self.health + 5)  # Health increases by 10 when eating, up to a max of 100
            self.io.say("You eat some food. Hunger increased. Health restored.")
            
            # Wisdom improves fatigue recovery rate
            fatigue_recovery = max(0, self.wisdom // 4)
            self.fatigue = max(0, self.fatigue - fatigue_recovery)
            self._check_and_complete_goals("eat")
        else:
            self.io.say("You have no food.")

    def drink(self):
        if self.backpack.water > 0:
            self.backpack.water -= 1
            self.thirst = min(100, self.thirst + 5)  # Adjust value as per game mechanics
            self.health = min(100, self.health + 5)  # Health increases by 5 when drinking, up to a max of 100
            self.io.say("You drink some water. Thirst increased. Health restored.")
            
            # Wisdom improves fatigue recovery rate
            fatigue_recovery = max(0, self.wisdom // 4)
            self.fatigue = max(0, self.fatigue - fatigue_recovery)
            self._check_and_complete_goals("drink")
        else:
            self.io.say("You have no water.")

    def use_medicine(self):
        if self.backpack.medicine > 0:
            self.backpack.medicine -= 1
            self.health = min(100, self.health + 20)  # Adjust value as per game mechanics
            self.io.say("You use medicine. Health increased.")
            
            # Wisdom improves fatigue recovery rate
            fatigue_recovery = max(0, self.wisdom // 4)
            self.fatigue = max(0, self.fatigue - fatigue_recovery)
            self._check_and_complete_goals("medicine")
        else:
            self.io.say("You have no medicine.")

    def rest(self):
        """Rest to recover fatigue. Recovery rate is based on Wisdom stat."""
        if self.fatigue <= 0:
            self.io.say("You are fully rested!")
            return
        
        recovery_rate = max(5, self.wisdom // 2)
        current_tile = self.map[self.current_position[1]][self.current_position[0]]
        current_terrain = current_tile.get('terrain') if isinstance(current_tile, dict) else None
        if current_terrain == 'building':
            recovery_rate *= 2
            self.io.say("You rest safely in a building, recovering fatigue faster.")
        recovered = min(self.fatigue, recovery_rate)
        self.fatigue -= recovered
        self.io.say(f"You rest and recover {recovered} fatigue. Current fatigue: {self.fatigue}")

    def equip_weapon(self, weapon_name):
        # Search for the weapon in the backpack's weapons list
        for weapon in self.backpack.weapons:
            if weapon.name.lower() == weapon_name.lower():
                # Check if there's already a weapon equipped
                if self.equipped_weapon:
                    # If there's already a weapon equipped, put it back in the backpack
                    self.backpack.weapons.append(self.equipped_weapon)
                    self.io.say(f"The {self.equipped_weapon.name} has been returned to the backpack.")
                # Equip the new weapon
                self.equipped_weapon = weapon
                # Remove the newly equipped weapon from the backpack
                self.backpack.weapons.remove(weapon)
                self.io.say(f"You have equipped the {weapon.name}.")
                return
        self.io.say(f"Weapon named '{weapon_name}' not found in inventory.")

    def drop_weapon(self, weapon_name):
        target = None
        in_backpack = False
        for weapon in self.backpack.weapons:
            if weapon.name.lower() == weapon_name.lower():
                target = weapon
                in_backpack = True
                break
        if target is None and self.equipped_weapon and self.equipped_weapon.name.lower() == weapon_name.lower():
            target = self.equipped_weapon

        if target is None:
            self.io.say(f"Weapon named '{weapon_name}' not found in inventory.")
            return

        salvage_note = ""
        if isinstance(target, RangedWeapon) and target.ammo > 0:
            self.backpack.ammo += target.ammo
            salvage_note = f" Salvaged {target.ammo} ammo back into your pack."
            target.ammo = 0

        if in_backpack:
            self.backpack.weapons.remove(target)
        else:
            self.equipped_weapon = None

        self.io.say(f"You drop the {target.name}.{salvage_note}")

    def equip_armor(self, armor_name):
        # Multi-piece follow-up: which slot to touch comes from the
        # piece's OWN .slot (items.py's ARMOR_SLOTS), not a slot the
        # player names separately - only the piece already occupying
        # that same slot gets swapped back to the backpack.
        for armor in self.backpack.armor:
            if armor.name.lower() == armor_name.lower():
                previous = self.equipped_armor[armor.slot]
                if previous:
                    self.backpack.armor.append(previous)
                    self.io.say(f"The {previous.name} has been returned to the backpack.")
                self.equipped_armor[armor.slot] = armor
                self.backpack.armor.remove(armor)
                self.io.say(f"You have equipped the {armor.name}.")
                return
        self.io.say(f"Armor named '{armor_name}' not found in inventory.")

    def drop_armor(self, armor_name):
        target = None
        in_backpack = False
        for armor in self.backpack.armor:
            if armor.name.lower() == armor_name.lower():
                target = armor
                in_backpack = True
                break
        if target is None:
            for slot, armor in self.equipped_armor.items():
                if armor and armor.name.lower() == armor_name.lower():
                    target = armor
                    break

        if target is None:
            self.io.say(f"Armor named '{armor_name}' not found in inventory.")
            return

        if in_backpack:
            self.backpack.armor.remove(target)
        else:
            self.equipped_armor[target.slot] = None

        self.io.say(f"You drop the {target.name}.")

    def describe_recipes(self):
        """
        v3 SPRINT step 4: the canonical, structured recipe listing -
        name, ingredients, min_level, and whether it's currently
        locked for this player. craft("list") below and the future
        TUI (step 6) both call this rather than each re-deriving
        recipe-display knowledge on their own.
        """

        return [
            {
                "key": key,
                "ingredients": dict(data["ingredients"]),
                "min_level": data.get("min_level", 1),
                "result_name": data["result_name"],
                "locked": self.level < data.get("min_level", 1),
            }
            for key, data in self.crafting_recipes.items()
        ]

    def craft(self, recipe_key):
        if recipe_key == "list":
            self.io.say("\n--- Available Crafting Recipes ---")
            for r in self.describe_recipes():
                ing_str = ", ".join(f"{v} {k}" for k, v in r["ingredients"].items())
                lock_note = f" [locked - requires level {r['min_level']}]" if r["locked"] else ""
                self.io.say(f"  {r['key']}: Requires {ing_str} -> Creates {r['result_name']}{lock_note}")
            return

        if recipe_key not in self.crafting_recipes:
            self.io.say(f"Unknown recipe: '{recipe_key}'. Type 'craft list' to see available recipes.")
            return

        recipe = self.crafting_recipes[recipe_key]

        min_level = recipe.get("min_level", 1)
        if self.level < min_level:
            self.io.say(f"'{recipe_key}' requires level {min_level} (you are level {self.level}).")
            return

        ingredients = recipe["ingredients"]

        # Check consumables
        for item_type, count in ingredients.items():
            if item_type != "weapon":
                current_count = getattr(self.backpack, item_type)
                if current_count < count:
                    self.io.say(f"Not enough {item_type} to craft. Need {count}, have {current_count}.")
                    return
        
        # Check weapon - v3 SPRINT step 4 fix: some new recipes need
        # 2 weapons (survivor_machete, apex_blade), but this only ever
        # checked "backpack isn't empty," not "has enough" - a real
        # bug the original 3 recipes (all weapon: 1) never exposed.
        weapon_count_needed = ingredients.get("weapon", 0)
        if weapon_count_needed > 0 and len(self.backpack.weapons) < weapon_count_needed:
            self.io.say(
                f"Not enough weapons to craft. Need {weapon_count_needed}, "
                f"have {len(self.backpack.weapons)}."
            )
            return

        # Consume items
        for item_type, count in ingredients.items():
            if item_type != "weapon":
                setattr(self.backpack, item_type, getattr(self.backpack, item_type) - count)
            elif item_type == "weapon":
                # Same fix - pop `count` weapons, not always just one.
                for _ in range(count):
                    removed = self.backpack.weapons.pop(0)
                    self.io.say(f"Used {removed.name} for crafting.")

        if recipe_key == 'repair_kit':
            if self.equipped_weapon:
                self.equipped_weapon.durability = self.equipped_weapon.max_durability
            for piece in self.equipped_armor.values():
                if piece:
                    piece.durability = piece.max_durability
            self.io.say('You use the repair kit to service your equipped weapon and armor - durability fully restored.')
            self._check_and_complete_goals('craft')
            return

        # Add result
        new_item = recipe["result"]()
        quality_label, quality_multiplier = self._roll_craft_quality()
        if quality_label != "Standard":
            new_item.name = f"{quality_label} {new_item.name}"
            new_item.damage = max(
                new_item.damage + 1, round(new_item.damage * quality_multiplier)
            )
            if hasattr(new_item, 'durability'):
                new_item.durability = max(
                    new_item.durability + 1,
                    round(new_item.durability * quality_multiplier),
                )
                new_item.max_durability = new_item.durability
        if not self.backpack.add_weapon(new_item):
            self.io.say(f"Crafted a {new_item.name}, but your pack is full - it was lost. Drop something first next time.")
        else:
            self.io.say(f"Crafted a {new_item.name}!")
        self._check_and_complete_goals("craft")

    def _roll_craft_quality(self):
        # Skill-based crafting quality: dexterity-scaled odds of a
        # bonus tier on top of the recipe's base result, same style as
        # combat_mixin.py's existing crit_chance/dodge_chance (both
        # `min(cap, self.dexterity / N)`). Deliberately additive only -
        # unlike a crit/dodge roll, there's no failure/waste branch
        # here; the worst outcome is just the recipe's normal result.
        masterwork_chance = min(0.3, self.dexterity / 100)
        fine_chance = 0.25  # flat band above masterwork_chance
        roll = self.rng.random()
        if roll < masterwork_chance:
            return "Masterwork", 1.3
        if roll < masterwork_chance + fine_chance:
            return "Fine", 1.15
        return "Standard", 1.0

    def auto_play(self):
        self.io.say("\nAuto-playing game...\n")
        actions = ['n', 's', 'e', 'w']
        max_steps = 100
        step_count = 0
        
        while self.health > 0 and step_count < max_steps:
            action = random.choice(actions)
            self.move_and_search(action)
            self.io.say(f"Automatically moving {action}")

            if self.hunger < 50 and self.backpack.food > 0:
                self.eat()
                self.io.say("Automatically eating to reduce hunger.")
            if self.thirst < 50 and self.backpack.water > 0:
                self.drink()
                self.io.say("Automatically drinking to reduce thirst.")

            if self.health < 75 and self.backpack.medicine > 0:
                self.use_medicine()
                self.io.say("Automatically using medicine to heal.")

            step_count += 1
            
            # Explicit stop condition based on player state changes
            if self.health <= 0:
                self.io.say("Auto-play ending due to critical health.")
                break
                
        if step_count >= max_steps:
            self.io.say(f"Auto-play ended after reaching maximum step limit ({max_steps}).")

    def view_weapon_info(self):
        if self.equipped_weapon:
            self.io.say("Equipped Weapon:")
            self.io.say(self.equipped_weapon)
        else:
            self.io.say("No weapon is currently equipped.")

        if self.backpack.weapons:
            self.io.say("\nWeapons in Inventory:")
            for line in format_weapon_list(self.backpack.weapons):
                self.io.say(line)
        else:
            self.io.say("\nNo weapons in inventory.")

    def increase_max_health(self, amount):
      self.max_health += amount
      self.health = self.max_health