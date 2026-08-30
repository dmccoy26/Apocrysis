"""Combat information layer (docs/COMBAT_INFO_SPEC.md).

A PLAYER-INFORMATION layer, not a rebalance. It reads the same numbers
`combat_mixin`'s fight loop uses and Monte-Carlos a faithful copy of
that loop to estimate fight / escape odds. It changes NO combat, escape,
XP or loot math - nothing here is called by the fight itself.
"""
import random as _random

from src.constants import STATUS_EFFECT_DAMAGE
from src.items import RangedWeapon

_SIMS = 300
_FLEE_CHANCE = 0.50          # combat_mixin: `if random.random() < 0.5`

# A private stream - the forecast must NEVER perturb the global `random`
# the real combat loop draws from.
_RNG = _random.Random()

# One line the survivor could plausibly infer - bulk, speed, armour -
# never a stat readout. Keyed by the base subclass name.
DANGER_NOTE = {
    "Fresh Zombie":   "Recently turned. Slow, clumsy, still soft.",
    "Regular Zombie": "Turned a while ago. Tougher, hits harder.",
    "Heavy Zombie":   "Huge and swollen. Enormous reach of health, slow swings.",
    "Swift Zombie":   "Fast and wiry. Gets inside your guard before you swing.",
    "Toxic Zombie":   "Weeping sores. Its bite festers - you'll keep bleeding.",
    "Armored Zombie": "Wrapped in scavenged plate. Half your hits barely land.",
}


def _base_name(zombie):
    return zombie.name.replace("Elite ", "", 1)


def danger_note(zombie):
    note = DANGER_NOTE.get(_base_name(zombie), "An infected. Dangerous up close.")
    if zombie.name.startswith("Elite "):
        note += " This one is an Elite - bigger, stronger than its kind."
    return note


def _usable_damage(weapon):
    if weapon is None or getattr(weapon, "durability", 1) <= 0:
        return 0
    if isinstance(weapon, RangedWeapon) and weapon.ammo <= 0:
        return 0
    return weapon.damage


def _cond_penalty(health, hunger, thirst, fatigue):
    p = 0.0
    if health < 25:
        p += 0.2
    elif health < 50:
        p += 0.1
    if hunger < 20 or thirst < 20:
        p += 0.2
    elif hunger < 40 or thirst < 40:
        p += 0.1
    if fatigue > 80:
        p += 0.2
    elif fatigue > 50:
        p += 0.1
    return max(0.5, 1.0 - p)


def _one_fight(player, zombie, weapon, rng):
    """One silent simulated fight. Mirrors combat_mixin.encounter_zombie's
    round loop: player acts, then zombie acts if alive; crit min(.25,
    dex/200) x2; dodge min(.5, dex/150); bleed 15%/3t, stun 10%/1t;
    Toxic poison 4t; Armored halves incoming; per-piece armor absorb;
    condition penalty recomputed each player turn. Returns True on win."""
    hp = player["health"]
    max_hp = player["max_health"]
    hunger = max(0, player["hunger"] - zombie.get("hunger_cost", 0))
    thirst = max(0, player["thirst"] - zombie.get("thirst_cost", 0))
    fatigue = min(100, player["fatigue"] + zombie.get("fatigue_cost", 0))
    strv, dexv = player["strength"], player["dexterity"]
    armor = list(player["armor_reductions"])       # per-piece, degrade 1/hit

    z_hp = zombie["health"]
    z_atk = zombie["attack"]
    z_reduce = zombie.get("damage_reduction", 0.0)   # ArmoredZombie
    z_toxic = zombie.get("toxic", False)

    wdmg = _usable_damage(weapon)
    ammo = getattr(weapon, "ammo", None) if isinstance(weapon, RangedWeapon) else None
    dur = getattr(weapon, "durability", None)

    crit = min(0.25, dexv / 200)
    dodge = min(0.5, dexv / 150)
    effects = {}

    for _ in range(60):                              # hard round cap
        # --- player turn ---
        if effects.get("Stun", 0) > 0:
            effects["Stun"] -= 1
        else:
            if ammo is not None:
                live = wdmg if ammo > 0 else 0
                if ammo > 0:
                    ammo -= 1
            else:
                live = wdmg
            if dur is not None and dur <= 0:
                live = 0
            if live > 0:
                cp = _cond_penalty(hp, hunger, thirst, fatigue)
                dmg = round((live + max(0, strv // 3)) * cp)
                if rng.random() < crit:
                    dmg *= 2
                if dur is not None:
                    dur -= 1
            else:
                dmg = round(2 * _cond_penalty(hp, hunger, thirst, fatigue))
            z_hp -= dmg * (1 - z_reduce)
        for eff in list(effects):
            d = STATUS_EFFECT_DAMAGE.get(eff)
            if d:
                hp -= d
            effects[eff] -= 1
            if effects[eff] <= 0:
                del effects[eff]
        if z_hp <= 0:
            return True
        if hp <= 0:
            return False
        # --- zombie turn ---
        if rng.random() >= dodge:
            incoming = z_atk
            for i, red in enumerate(armor):
                if red > 0:
                    incoming = max(0, incoming - red)
                    armor[i] -= 1
            hp -= incoming
            if z_toxic:
                effects["Poison"] = 4
            else:
                roll = rng.random()
                if roll < 0.15 and "Bleeding" not in effects:
                    effects["Bleeding"] = 3
                elif roll < 0.25 and "Stun" not in effects:
                    effects["Stun"] = 1
        if hp <= 0:
            return False
    return z_hp <= 0


def _snapshot(game, weapon):
    return {
        "health": game.health, "max_health": game.max_health,
        "hunger": game.hunger, "thirst": game.thirst, "fatigue": game.fatigue,
        "strength": game.strength, "dexterity": game.dexterity,
        "armor_reductions": [p.damage_reduction for p in game.equipped_armor.values()
                             if p and getattr(p, "durability", 1) > 0],
    }, weapon


def _zsnap(zombie):
    from src.zombies import ToxicZombie
    return {
        "health": zombie.health, "attack": zombie.attack,
        "hunger_cost": getattr(zombie, "hunger_cost", 0),
        "thirst_cost": getattr(zombie, "thirst_cost", 0),
        "fatigue_cost": getattr(zombie, "fatigue_cost", 0),
        "damage_reduction": getattr(type(zombie), "damage_reduction", 0.0),
        "toxic": isinstance(zombie, ToxicZombie),
    }


def fight_pct(game, zombie, weapon="__equipped__", sims=_SIMS, rng=_RNG):
    """Estimated % the player wins the fight with `weapon` (default: the
    equipped one). Monte Carlo over the real round loop."""
    if weapon == "__equipped__":
        weapon = game.equipped_weapon
    psnap, _ = _snapshot(game, weapon)
    zsnap = _zsnap(zombie)
    wins = sum(_one_fight(psnap, zsnap, weapon, rng) for _ in range(sims))
    return round(100 * wins / sims)


def escape_pct(game, zombie):
    return round(100 * _FLEE_CHANCE)


THREAT_TIERS = ((85, "LOW"), (60, "MODERATE"), (35, "HIGH"),
                (15, "SEVERE"), (0, "EXTREME"))


def threat_tier(win_pct):
    for floor, name in THREAT_TIERS:
        if win_pct >= floor:
            return name
    return "EXTREME"


def weapon_verdict(win_pct):
    if win_pct >= 85:
        return "overkill for this target"
    if win_pct >= 60:
        return "well suited to this target"
    if win_pct >= 35:
        return "adequate, but it'll cost you"
    return "poorly suited to this target"


def all_weapon_forecasts(game, zombie, sims=_SIMS, rng=_RNG):
    """(weapon, fight_pct, verdict) for the equipped weapon + every
    backpack weapon, best fight % first. For the [w] stats window."""
    seen, weapons = set(), []
    for w in [game.equipped_weapon] + list(game.backpack.weapons):
        if w is None or id(w) in seen:
            continue
        seen.add(id(w))
        weapons.append(w)
    out = []
    for w in weapons:
        pct = fight_pct(game, zombie, weapon=w, sims=sims, rng=rng)
        out.append((w, pct, weapon_verdict(pct)))
    out.sort(key=lambda t: t[1], reverse=True)
    return out


def better_weapon(game, zombie, sims=_SIMS, rng=_RNG):
    """The best backpack weapon if it beats the equipped weapon's fight %
    by >= 15 points, else None."""
    cur = fight_pct(game, zombie, sims=sims, rng=rng)
    best = None
    for w, pct, _ in all_weapon_forecasts(game, zombie, sims=sims, rng=rng):
        if w is game.equipped_weapon:
            continue
        if pct >= cur + 15 and (best is None or pct > best[1]):
            best = (w, pct)
    return best
