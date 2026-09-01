"""The Silence's equipment vocabulary (Phase F §F.10).

This is also the engine's fallback loot (src/loot.py) for any world
that doesn't author its own - so the tables here must stay exactly what
constants.LOOT_WEAPON_TABLE / ARMOR_TABLE and actions_mixin's crafting
recipes were before the seam, values AND key order (the loot RNG picks
by index).
"""
from src.worlds.base import WorldLoot

# Real bug found live (kept for the record): world_mixin.find_loot()
# used to build every looted weapon as MeleeWeapon(name, 10, 100)
# regardless of the name - a "Rusty Dagger" and a "Steel Katana" were
# mechanically identical, and "Broken Rifle"/"Leather Bow" were melee
# instances that could never reload. Real stat variance + correct type.
WEAPONS = {
    "Rusty Dagger": {"type": "melee", "damage": 8, "durability": 40, "min_expedition": 0},
    "Chipped Sword": {"type": "melee", "damage": 12, "durability": 50, "min_expedition": 0},
    "Iron Axe": {"type": "melee", "damage": 16, "durability": 90, "min_expedition": 4},
    "Steel Katana": {"type": "melee", "damage": 20, "durability": 110, "min_expedition": 6},
    "Broken Rifle": {"type": "ranged", "damage": 10, "max_ammo": 5, "durability": 15, "min_expedition": 0},
    "Leather Bow": {"type": "ranged", "damage": 14, "max_ammo": 8, "durability": 45, "min_expedition": 2},
}

# Equipment-slot investigation: four slots (head/body/hands/feet), each
# banded by expeditions_completed the same way WEAPONS is. Per-slot
# reductions kept modest (a full loadout at max expedition sums to 13).
ARMOR = {
    "Bandana": {"slot": "head", "reduction": 1, "durability": 20, "min_expedition": 0},
    "Combat Helmet": {"slot": "head", "reduction": 3, "durability": 50, "min_expedition": 4},
    "Padded Vest": {"slot": "body", "reduction": 2, "durability": 30, "min_expedition": 0},
    "Kevlar Vest": {"slot": "body", "reduction": 4, "durability": 70, "min_expedition": 3},
    "Riot Armor": {"slot": "body", "reduction": 6, "durability": 100, "min_expedition": 6},
    "Work Gloves": {"slot": "hands", "reduction": 1, "durability": 25, "min_expedition": 0},
    "Reinforced Gauntlets": {"slot": "hands", "reduction": 2, "durability": 50, "min_expedition": 3},
    "Sneakers": {"slot": "feet", "reduction": 1, "durability": 25, "min_expedition": 0},
    "Steel-Toe Boots": {"slot": "feet", "reduction": 2, "durability": 50, "min_expedition": 3},
}

# Crafting: the ingredient costs + level gates are the GRAMMAR (engine,
# actions_mixin.craft); only `result` is world vocabulary. `result`
# None = a utility recipe (repair kit). Keys are shared across worlds.
CRAFTING = {
    "steel_sword": {"ingredients": {"weapon": 1, "food": 2}, "min_level": 1,
                    "result": {"kind": "melee", "name": "Steel Sword", "damage": 20, "durability": 50}},
    "repair_kit": {"ingredients": {"medicine": 2, "food": 1}, "min_level": 8,
                   "result": None, "result_name": "Repair Kit"},
    "heavy_bow": {"ingredients": {"weapon": 1, "ammo": 3}, "min_level": 1,
                  "result": {"kind": "ranged", "name": "Heavy Bow", "damage": 25, "max_ammo": 10}},
    "combat_knife": {"ingredients": {"weapon": 1, "medicine": 1}, "min_level": 1,
                     "result": {"kind": "melee", "name": "Combat Knife", "damage": 15, "durability": 40}},
    "reinforced_blade": {"ingredients": {"weapon": 1, "medicine": 1, "food": 1}, "min_level": 4,
                         "result": {"kind": "melee", "name": "Reinforced Blade", "damage": 28, "durability": 60}},
    "hunting_crossbow": {"ingredients": {"weapon": 1, "ammo": 5, "food": 1}, "min_level": 6,
                         "result": {"kind": "ranged", "name": "Hunting Crossbow", "damage": 30, "max_ammo": 15}},
    "survivor_machete": {"ingredients": {"weapon": 2, "water": 2}, "min_level": 9,
                         "result": {"kind": "melee", "name": "Survivor Machete", "damage": 35, "durability": 70}},
    "military_carbine": {"ingredients": {"weapon": 1, "ammo": 8, "medicine": 2}, "min_level": 13,
                         "result": {"kind": "ranged", "name": "Military Carbine", "damage": 45, "max_ammo": 20}},
    "apex_blade": {"ingredients": {"weapon": 2, "medicine": 3, "food": 3}, "min_level": 18,
                   "result": {"kind": "melee", "name": "Apex Blade", "damage": 55, "durability": 100}},
}

# The weapon a fresh survivor comes in with. Historically the tier-0
# class weapon (MeleeWeapon("Kitchen Knife", 6, 80)) with a random
# household variant.
STARTER = {
    "name": "Kitchen Knife", "damage": 6, "durability": 80,
    "variants": ("Kitchen Knife", "Rolling Pin", "Frying Pan", "Screwdriver"),
}

SILENCE_LOOT = WorldLoot(weapons=WEAPONS, armor=ARMOR,
                         crafting=CRAFTING, starter=STARTER)
