# Auto-extracted from the original monolithic apocrysis.py during
# the src/ restructuring - see README.md for the project layout.

from dataclasses import dataclass

from src.items import MeleeWeapon, RangedWeapon


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


def _power_score(player_class):
    return (
        player_class.health
        + player_class.strength * 2
        + player_class.dexterity * 2
        + player_class.intelligence
        + player_class.wisdom
        - player_class.fatigue * 3
    )


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


# SPRINT v3: level-based progression (no class choice at game start -
# see src/mixins/actions_mixin.py's initialize_player()). Classes
# collapse into 5 difficulty tiers, derived programmatically from
# PLAYER_CLASSES's own stats rather than hand-ranked, so a future
# edit to PLAYER_CLASSES doesn't need a parallel manual re-ranking.
#
# CLASS_TIERS is an ordered list of tiers, each a list of class-name
# strings sorted ascending by _power_score within the tier (easiest
# tier first). Each tier's REPRESENTATIVE (used by level_up()'s tier
# blend, combat_mixin.py) is deterministically the STRONGEST class in
# that tier's slice - its last element, since the slice itself is
# sorted ascending - not an arbitrary first element.

_TIER_COUNT = 5


def _split_into_tiers(sorted_names, tier_count=_TIER_COUNT):
    tiers = []
    n = len(sorted_names)
    base, extra = divmod(n, tier_count)
    index = 0
    for i in range(tier_count):
        size = base + (1 if i < extra else 0)
        tiers.append(sorted_names[index:index + size])
        index += size
    return tiers


_SORTED_CLASS_NAMES = sorted(
    PLAYER_CLASSES,
    key=lambda name: _power_score(PLAYER_CLASSES[name]),
)

# AUDIT FINDING (level 9->10 tier transition): Simulating level_up() calls 1->20 reveals that the level-10 tier blend is the only one of the 5 tier crossings with any negative raw-stat delta. The level 9->10 transition nets strength -2 and dexterity -2 even after normal per-level +1/+1 growth (level 9: str 20/dex 21 -> level 10: str 18/dex 19), because the level-10 tier representative ('teacher') has lower strength/dexterity than level-5's ('mechanic'). However, the FULL capability impact is milder than the raw stat delta suggests: melee damage bonus (strength // 3) is UNCHANGED (20//3 == 18//3 == 6), dodge chance drops from 0.140 to 0.127 and crit chance from 0.105 to 0.095 (both dex/divisor-based, real but small), while max_health (+5), fatigue recovery, and rest recovery all improve at the same transition. Net verdict: real but narrow regression (dodge/crit only, ~1 percentage point each), not the across-the-board power loss the raw -3/-3 representative-class delta implied. This audit is what should inform any fix to the level-10 tier blend, rather than fixing it blind.
CLASS_TIERS = _split_into_tiers(_SORTED_CLASS_NAMES)

TIER_LEVEL_THRESHOLDS = [1, 5, 10, 15, 20]


def tier_representative(tier_index):
    return CLASS_TIERS[tier_index][-1]


STARTER_CLASS_NAME = tier_representative(0)