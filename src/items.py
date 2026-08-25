# Auto-extracted from the original monolithic apocrysis.py during
# the src/ restructuring - see README.md for the project layout.

import enum
from collections import Counter


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
                print(f"'{item}' is not a recognized item and was not added.")
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
        self.max_durability = durability

    def use(self):
        if self.durability > 0:
            self.durability -= 1
            return self.damage
        else:
            print(f"{self.name} is broken and cannot be used.")
            return 0  # Return 0 damage if the weapon is broken

    def __str__(self):
        # Real gap found live: Weapon's own __str__ (inherited here
        # before this override existed) showed damage only - a
        # player had no way to compare two melee weapons' durability
        # without reading source. i (inventory)/eq's weapon listing
        # both call str() on each weapon, so this one change surfaces
        # it everywhere weapons are already displayed.
        return f"{self.name} - Damage: {self.damage}, Durability: {self.durability}/{self.max_durability}"

class RangedWeapon(Weapon):
    def __init__(self, name, damage, max_ammo, durability=20):
        super().__init__(name, damage)
        self.max_ammo = max_ammo
        self.ammo = max_ammo  # Initialize ammo count to the maximum
        self.durability = durability
        self.max_durability = durability

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
        self.durability = self.max_durability  # Reloading also services the weapon

    def __str__(self):
        return (
            f"{self.name} (Damage: {self.damage}, "
            f"Ammo: {self.ammo}/{self.max_ammo}, "
            f"Durability: {self.durability}/{self.max_durability})"
        )




