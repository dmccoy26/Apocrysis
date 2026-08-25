# Auto-extracted from the original monolithic apocrysis.py during
# the src/ restructuring - see README.md for the project layout.

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
        self.hunger_cost = 2
        self.thirst_cost = 2
        self.fatigue_cost = 5

class RegularZombie(Zombie):
    loot_table = ["food", "water", "medicine", "weapon"]

    def __init__(self):
        super().__init__("Regular Zombie", 50, 10)
        self.hunger_cost = 4
        self.thirst_cost = 4
        self.fatigue_cost = 10

class HeavyZombie(Zombie):
    loot_table = ["food", "water", "medicine", "weapon", "ammo"]

    def __init__(self):
        super().__init__("Heavy Zombie", 100, 20)
        self.hunger_cost = 8
        self.thirst_cost = 8
        self.fatigue_cost = 20


