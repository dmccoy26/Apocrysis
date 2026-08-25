# Auto-extracted from the original monolithic apocrysis.py during
# the src/ restructuring - see README.md for the project layout.

from dataclasses import dataclass

from src.items import MeleeWeapon, RangedWeapon, Weapon


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


PLAYER_CLASSES = {
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
