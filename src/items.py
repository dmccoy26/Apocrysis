# Auto-extracted from the original monolithic apocrysis.py during
# the src/ restructuring - see README.md for the project layout.

import enum
from collections import Counter


def _format_item_list(items, slot_tag=None):
    """Collapse a *contiguous run* of identical items onto one line with
    an "xN" suffix - a long haul of looted duplicates would otherwise
    repeat the same line once per item and swamp the inventory display.
    Runs must be contiguous so the slot numbers stay honest.

    `slot_tag` ("" for weapons, "W" for armor) prefixes each line with
    the 1-based slot number(s) the run covers, so a player can `eq 3` /
    `wr W2` exactly what they see."""
    items = list(items)
    lines = []
    i = 0
    while i < len(items):
        key = str(items[i])
        j = i
        while j < len(items) and str(items[j]) == key:
            j += 1
        n = j - i
        body = f"{key} x{n}" if n > 1 else key
        if slot_tag is not None:
            tag = (f"{slot_tag}{i + 1}" if n == 1
                   else f"{slot_tag}{i + 1}-{slot_tag}{j}")
            body = f"[{tag}] {body}"
        lines.append(body)
        i = j
    return lines


def format_weapon_list(weapons):
    return _format_item_list(weapons, slot_tag="")


def format_armor_list(armor_pieces):
    return _format_item_list(armor_pieces, slot_tag="W")


class ConsumableType(enum.Enum):
    FOOD = "food"
    WATER = "water"
    MEDICINE = "medicine"
    AMMO = "ammo"

class Item:
    def __init__(self, name):
        self.name = name

class Backpack:
    MAX_FOOD = 50
    MAX_WATER = 50
    MAX_MEDICINE = 50
    MAX_AMMO = 99
    MAX_WEAPONS = 12
    MAX_ARMOR = 6

    def __init__(self):
        self.consumables = Counter()  # Unified storage for food, water, medicine, ammo
        self.weapons = []             # Dedicated list for Weapon objects
        self.armor = []               # Dedicated list for Armor objects (equipment-slot investigation)
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
        elif isinstance(item, Armor):
            self.armor.append(item)
        else:
            self.items.append(item)

    def add_weapon(self, weapon):
        if len(self.weapons) < self.MAX_WEAPONS:
            self.weapons.append(weapon)
            return True
        return False

    def add_armor(self, armor):
        if len(self.armor) < self.MAX_ARMOR:
            self.armor.append(armor)
            return True
        return False

    @property
    def food(self): return self.consumables["food"]
    @food.setter
    def food(self, value): self.consumables["food"] = min(value, self.MAX_FOOD)

    @property
    def water(self): return self.consumables["water"]
    @water.setter
    def water(self, value): self.consumables["water"] = min(value, self.MAX_WATER)

    @property
    def medicine(self): return self.consumables["medicine"]
    @medicine.setter
    def medicine(self, value): self.consumables["medicine"] = min(value, self.MAX_MEDICINE)

    @property
    def ammo(self): return self.consumables["ammo"]
    @ammo.setter
    def ammo(self, value): self.consumables["ammo"] = min(value, self.MAX_AMMO)




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

    def use(self, io=None):
        if self.durability > 0:
            self.durability -= 1
            return self.damage
        else:
            (io.say(f"{self.name} is broken and cannot be used.") if io is not None else None)
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

    def fire(self, io=None):
        if self.ammo > 0 and self.durability > 0:
            self.ammo -= 1
            self.durability -= 1
            (io.say(f"You fire your {self.name}. Ammo remaining: {self.ammo}/{self.max_ammo}") if io is not None else None)
            return self.damage
        else:
            if self.ammo <= 0:
                (io.say("Out of ammo! You need to reload.") if io is not None else None)
            else:
                (io.say(f"{self.name} is broken and cannot be used.") if io is not None else None)
            return 0

    def use(self, io=None):
        if self.ammo > 0 and self.durability > 0:
            self.ammo -= 1
            self.durability -= 1
            return self.damage
        else:
            (io.say("Out of ammo or weapon is broken!") if io is not None else None)
            return 0

    def reload(self, available_ammo):
        # Tops off toward max_ammo, drawing at most `available_ammo`
        # from the caller's ammo pool - never invents ammo the pool
        # doesn't have. Returns how much was actually drawn, so the
        # caller (ui_mixin.py) can debit backpack.ammo by exactly
        # that amount instead of assuming the full request went
        # through.
        needed = self.max_ammo - self.ammo
        used = max(0, min(needed, available_ammo))
        self.ammo += used
        self.durability = self.max_durability  # Reloading also services the weapon
        return used

    def __str__(self):
        return (
            f"{self.name} (Damage: {self.damage}, "
            f"Ammo: {self.ammo}/{self.max_ammo}, "
            f"Durability: {self.durability}/{self.max_durability})"
        )


ARMOR_SLOTS = ("head", "body", "hands", "feet")


class Armor(Item):
    """
    Equipment-slot investigation, multi-piece follow-up: one Armor
    instance occupies exactly one of ARMOR_SLOTS (equipped_armor on
    Apocrysis is now a dict of all four, not a single object/None).
    """

    def __init__(self, name, damage_reduction, durability, slot):
        super().__init__(name)
        if slot not in ARMOR_SLOTS:
            raise ValueError(f"Unknown armor slot: {slot!r}")
        self.damage_reduction = damage_reduction
        self.durability = durability
        self.max_durability = durability
        self.slot = slot

    def absorb(self, incoming_damage):
        """
        Reduces incoming damage by damage_reduction, degrading
        durability by 1 per hit absorbed. Broken armor (durability<=0)
        absorbs nothing - matches MeleeWeapon.use()'s "broken tool
        does nothing" pattern rather than blocking combat.
        """
        if self.durability <= 0:
            return incoming_damage
        self.durability -= 1
        return max(0, incoming_damage - self.damage_reduction)

    def __str__(self):
        return f"{self.name} [{self.slot}] - Reduction: {self.damage_reduction}, Durability: {self.durability}/{self.max_durability}"




