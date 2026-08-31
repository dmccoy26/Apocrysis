# Auto-extracted from the original monolithic apocrysis.py during
# the src/ restructuring - see README.md for the project layout.

class Zombie:
    loot_table = []  # Overridden per subclass below - class-level, not rebuilt per instance
    ARCHETYPE = "common"

    def __init__(self, name, health, attack):
        self.name = name           # internal archetype string ("Swift Zombie")
        self.health = health
        self.attack = attack
        # Zombie Identity Pass (docs/ZOMBIE_IDENTITY_PASS.md) - attached
        # by world_mixin._attach_infected() from a dedicated RNG so it
        # never perturbs map generation. Safe defaults for an
        # un-attached instance (tests, bare construction).
        self.identity = ""
        self.identity_label = "INFECTED"
        self.identity_line = ""
        self.situation = ""
        self.flags = ()
        self._loot_lean = ()
        self._loot_poor = False

    def take_damage(self, damage):
        self.health -= damage

class FreshZombie(Zombie):
    loot_table = ["food", "water", "medicine"]
    ARCHETYPE = 'fresh'

    def __init__(self):
        super().__init__("Fresh Zombie", 30, 5)
        self.hunger_cost = 2
        self.thirst_cost = 2
        self.fatigue_cost = 5

class RegularZombie(Zombie):
    loot_table = ["food", "water", "medicine", "weapon"]
    ARCHETYPE = 'common'

    def __init__(self):
        super().__init__("Regular Zombie", 50, 10)
        self.hunger_cost = 4
        self.thirst_cost = 4
        self.fatigue_cost = 10

class HeavyZombie(Zombie):
    loot_table = ["food", "water", "medicine", "weapon", "ammo"]
    ARCHETYPE = 'heavy'

    def __init__(self):
        super().__init__("Heavy Zombie", 100, 20)
        self.hunger_cost = 8
        self.thirst_cost = 8
        self.fatigue_cost = 20


# v3 SPRINT step 3: more zombie variety beyond Fresh/Regular/Heavy.

class SwiftZombie(Zombie):
    loot_table = ["food", "ammo"]
    ARCHETYPE = 'swift'

    def __init__(self):
        super().__init__("Swift Zombie", 25, 15)
        self.hunger_cost = 3
        self.thirst_cost = 3
        self.fatigue_cost = 8


class ToxicZombie(Zombie):
    # Its bite inflicts "Poison" (combat_mixin.py's encounter_zombie(),
    # constants.py's STATUS_EFFECT_DAMAGE) - 3 damage/turn for 4
    # turns, guaranteed on hit rather than a chance roll like
    # Bleeding/Stun, matching its name being the whole point of
    # fighting one.
    loot_table = ["medicine", "weapon"]
    ARCHETYPE = 'toxic'

    def __init__(self):
        super().__init__("Toxic Zombie", 40, 8)
        self.hunger_cost = 5
        self.thirst_cost = 5
        self.fatigue_cost = 12


class ArmoredZombie(Zombie):
    loot_table = ["weapon", "ammo", "medicine"]
    ARCHETYPE = 'armored'
    damage_reduction = 0.5

    def __init__(self):
        super().__init__("Armored Zombie", 120, 15)
        self.hunger_cost = 10
        self.thirst_cost = 10
        self.fatigue_cost = 25

    def take_damage(self, damage):
        super().take_damage(damage * (1 - self.damage_reduction))


# --- escape model (docs/DESIGN_ESCAPE_MODEL.md) ---------------------
# How hard a given zombie is to *disengage* from — the dominant input
# to src.escape_model. "slow" is what makes "evade the Armored" a real
# strategy; "fast" is why a Swift is dangerous to run from, not just to
# fight. Keyed by the base subclass name (Elite variants share it).
SPEED_CLASS = {
    "Fresh Zombie": "normal",
    "Regular Zombie": "normal",
    "Toxic Zombie": "normal",
    "Heavy Zombie": "slow",
    "Armored Zombie": "slow",
    "Swift Zombie": "fast",
}


def speed_class_of(zombie):
    base = zombie.name.replace("Elite ", "", 1)
    return SPEED_CLASS.get(base, "normal")


