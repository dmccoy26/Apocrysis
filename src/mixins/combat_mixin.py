# Auto-extracted from the original monolithic apocrysis.py during
# the src/ restructuring - see README.md for the project layout.

import random

from src.constants import BOLD, GREEN, RESET
from src.items import MeleeWeapon, RangedWeapon
from src.zombies import FreshZombie, RegularZombie, HeavyZombie


class CombatMixin:

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
        self.hunger = max(0, self.hunger - zombie.hunger_cost)
        self.thirst = max(0, self.thirst - zombie.thirst_cost)
        self.fatigue = min(100, self.fatigue + zombie.fatigue_cost)
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

    def take_damage(self, damage):
        """
        Reduces the player's health by the specified damage amount.
        """
        self.health -= damage
        print(f"The {self.name} takes {damage} damage. Its current health is {self.health}.")
        if self.health <= 0:
            print(f"The {self.name} has been defeated!")

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

