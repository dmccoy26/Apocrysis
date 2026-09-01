"""The Wake's equipment vocabulary (Phase F §F.10).

A stopped colony ship: what its crew carried and what an engineer
scavenges is maintenance and rescue gear, not valley weapons. The stat
values are IDENTICAL to The Silence's, band for band - the balance
contract is untouched; only the fiction changes. (No "ceramic-edged
maintenance blade" reskins - these are things a ship's people would
actually have had to hand.)
"""
from src.worlds.base import WorldLoot

WEAPONS = {
    # melee
    "Utility Knife": {"type": "melee", "damage": 8, "durability": 40, "min_expedition": 0},
    "Pry Bar": {"type": "melee", "damage": 12, "durability": 50, "min_expedition": 0},
    "Fire Axe": {"type": "melee", "damage": 16, "durability": 90, "min_expedition": 4},
    "Breaching Bar": {"type": "melee", "damage": 20, "durability": 110, "min_expedition": 6},
    # ranged
    "Bolt Driver": {"type": "ranged", "damage": 10, "max_ammo": 5, "durability": 15, "min_expedition": 0},
    "Speargun": {"type": "ranged", "damage": 14, "max_ammo": 8, "durability": 45, "min_expedition": 2},
}

ARMOR = {
    "Hard Hat": {"slot": "head", "reduction": 1, "durability": 20, "min_expedition": 0},
    "EVA Helmet": {"slot": "head", "reduction": 3, "durability": 50, "min_expedition": 4},
    "Padded Jacket": {"slot": "body", "reduction": 2, "durability": 30, "min_expedition": 0},
    "Impact Vest": {"slot": "body", "reduction": 4, "durability": 70, "min_expedition": 3},
    "Salvage Rig": {"slot": "body", "reduction": 6, "durability": 100, "min_expedition": 6},
    "Work Gloves": {"slot": "hands", "reduction": 1, "durability": 25, "min_expedition": 0},
    "Insulated Gauntlets": {"slot": "hands", "reduction": 2, "durability": 50, "min_expedition": 3},
    "Deck Shoes": {"slot": "feet", "reduction": 1, "durability": 25, "min_expedition": 0},
    "Steel-Toe Boots": {"slot": "feet", "reduction": 2, "durability": 50, "min_expedition": 3},
}

CRAFTING = {
    "steel_sword": {"ingredients": {"weapon": 1, "food": 2}, "min_level": 1,
                    "result": {"kind": "melee", "name": "Plasma Cutter", "damage": 20, "durability": 50}},
    "repair_kit": {"ingredients": {"medicine": 2, "food": 1}, "min_level": 8,
                   "result": None, "result_name": "Service Kit"},
    "heavy_bow": {"ingredients": {"weapon": 1, "ammo": 3}, "min_level": 1,
                  "result": {"kind": "ranged", "name": "Modified Speargun", "damage": 25, "max_ammo": 10}},
    "combat_knife": {"ingredients": {"weapon": 1, "medicine": 1}, "min_level": 1,
                     "result": {"kind": "melee", "name": "Bench Knife", "damage": 15, "durability": 40}},
    "reinforced_blade": {"ingredients": {"weapon": 1, "medicine": 1, "food": 1}, "min_level": 4,
                         "result": {"kind": "melee", "name": "Reinforced Pry Bar", "damage": 28, "durability": 60}},
    "hunting_crossbow": {"ingredients": {"weapon": 1, "ammo": 5, "food": 1}, "min_level": 6,
                         "result": {"kind": "ranged", "name": "Rail Harpoon", "damage": 30, "max_ammo": 15}},
    "survivor_machete": {"ingredients": {"weapon": 2, "water": 2}, "min_level": 9,
                         "result": {"kind": "melee", "name": "Cut-Down Halligan", "damage": 35, "durability": 70}},
    "military_carbine": {"ingredients": {"weapon": 1, "ammo": 8, "medicine": 2}, "min_level": 13,
                         "result": {"kind": "ranged", "name": "Bolt Rifle", "damage": 45, "max_ammo": 20}},
    "apex_blade": {"ingredients": {"weapon": 2, "medicine": 3, "food": 3}, "min_level": 18,
                   "result": {"kind": "melee", "name": "Control Rod", "damage": 55, "durability": 100}},
}

STARTER = {
    "name": "Multitool", "damage": 6, "durability": 80,
    "variants": ("Multitool", "Torque Wrench", "Handframe Hook", "Deck Iron"),
}

THE_WAKE_LOOT = WorldLoot(weapons=WEAPONS, armor=ARMOR,
                          crafting=CRAFTING, starter=STARTER)
