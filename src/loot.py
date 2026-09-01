"""Loot GRAMMAR (Phase F §F.10). The engine reads a world's equipment
vocabulary through here; a world that authors none falls back to The
Silence's tables. No world-specific branching - `world` in, table out.

The bands / min_expedition gating / melee-vs-ranged split / ingredient
costs all stay in the callers (world_mixin.find_loot, combat_mixin's
drop, actions_mixin.craft, persistence_mixin._apply_heir_advantage).
"""
from src.items import MeleeWeapon, RangedWeapon
from src.worlds.silence.loot import (
    WEAPONS as _DEF_WEAPONS,
    ARMOR as _DEF_ARMOR,
    CRAFTING as _DEF_CRAFTING,
    STARTER as _DEF_STARTER,
)


def _loot(world):
    return getattr(world, "loot", None)


def weapon_table(world=None):
    return _loot(world).weapons if getattr(_loot(world), "weapons", None) else _DEF_WEAPONS


def armor_table(world=None):
    return _loot(world).armor if getattr(_loot(world), "armor", None) else _DEF_ARMOR


def starter_spec(world=None):
    return _loot(world).starter if getattr(_loot(world), "starter", None) else _DEF_STARTER


def build_weapon(name, spec):
    """spec is a weapon_table entry."""
    if spec.get("type") == "ranged":
        return RangedWeapon(name, spec["damage"], spec["max_ammo"],
                            spec["durability"])
    return MeleeWeapon(name, spec["damage"], spec["durability"])


def _build_craft_result(res):
    if res is None:
        return None
    if res["kind"] == "ranged":
        return RangedWeapon(res["name"], res["damage"], res["max_ammo"])
    return MeleeWeapon(res["name"], res["damage"], res["durability"])


def craft_recipes(world=None):
    """The recipe dict actions_mixin.craft() expects: each entry keeps
    `ingredients` / `min_level` from the (engine-owned) grammar, and
    gets `result` as a zero-arg builder + `result_name`, hydrated from
    the world's data spec."""
    src = _loot(world).crafting if getattr(_loot(world), "crafting", None) else _DEF_CRAFTING
    out = {}
    for key, spec in src.items():
        res = spec.get("result")
        out[key] = {
            "ingredients": spec["ingredients"],
            "min_level": spec.get("min_level", 1),
            "result_name": (res["name"] if res else spec.get("result_name")),
            "result": (lambda res=res: _build_craft_result(res)),
        }
    return out
