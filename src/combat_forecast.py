"""Combat information layer (docs/COMBAT_INFO_SPEC.md).

A PLAYER-INFORMATION layer, not a rebalance. It reads the same numbers
`combat_mixin`'s fight loop uses and Monte-Carlos a faithful copy of
that loop to estimate the fight outcome + its cost. It changes NO
combat / XP / loot math - nothing here drives the fight.

`escape_pct` delegates to `src.escape_model` - the SAME function the
real flee roll uses - so the escape number the player sees is the one
they get (docs/DESIGN_ESCAPE_MODEL.md). `threat_tier` / `weapon_verdict`
are two-axis: P(win) AND the p90/p50 HP-loss cost, so a near-certain
but near-fatal win is no longer labelled `LOW` (COMBAT_EXP2_RESULTS.md).
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
    """True on a win. Thin wrapper over `_simulate` — kept for callers
    and tests that only care about the outcome."""
    return _simulate(player, zombie, weapon, rng)[0]


def _simulate(player, zombie, weapon, rng):
    """One silent simulated fight. Mirrors combat_mixin.encounter_zombie's
    round loop: player acts, then zombie acts if alive; crit min(.25,
    dex/200) x2; dodge min(.5, dex/150); bleed 15%/3t, stun 10%/1t;
    Toxic poison 4t; Armored halves incoming; per-piece armor absorb;
    condition penalty recomputed each player turn.

    Returns `(won: bool, hp_lost: int)` — hp_lost is the HP delta from
    the start of the fight, so a caller can build the cost distribution
    (docs/COMBAT_MODEL_EXPERIMENTS.md exp 1/2)."""
    hp = player["health"]
    start_hp = hp
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
            return True, max(0, start_hp - hp)
        if hp <= 0:
            return False, max(0, start_hp - hp)
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
            return False, max(0, start_hp - hp)
    return (z_hp <= 0), max(0, start_hp - hp)


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


def fight_outcome(game, zombie, weapon="__equipped__", sims=_SIMS, rng=_RNG):
    """win % plus the HP-loss distribution *given a win*, as a fraction
    of max HP: {win_pct, p50_frac, p90_frac}. The two-axis `threat_tier`
    / `weapon_verdict` read this — `P(win)` alone is not fight severity
    (docs/COMBAT_MODEL_EXPERIMENTS.md exp 1/2)."""
    if weapon == "__equipped__":
        weapon = game.equipped_weapon
    psnap, _ = _snapshot(game, weapon)
    zsnap = _zsnap(zombie)
    mx = max(1, game.max_health)
    losses, wins = [], 0
    for _ in range(sims):
        won, lost = _simulate(psnap, zsnap, weapon, rng)
        if won:
            wins += 1
            losses.append(min(lost, mx) / mx)
    win_pct = round(100 * wins / sims)
    if losses:
        s = sorted(losses)
        p50 = s[len(s) // 2]
        p90 = s[min(len(s) - 1, int(len(s) * 0.9))]
    else:
        p50 = p90 = None
    return {"win_pct": win_pct, "p50_frac": p50, "p90_frac": p90}


def escape_pct(game, zombie, terrain=None):
    """Resolved P(escape) for the encounter card. Delegates to
    `src.escape_model` — the SAME function the real flee roll in
    `combat_mixin` uses, so the number the player sees is the number
    they get (docs/DESIGN_ESCAPE_MODEL.md, the trust constraint).
    No longer a flat 50%."""
    from src import escape_model
    return round(100 * escape_model.escape_chance_for(game, zombie, terrain))


THREAT_TIERS = ((85, "LOW"), (60, "MODERATE"), (35, "HIGH"),
                (15, "SEVERE"), (0, "EXTREME"))


def threat_tier(win_pct, cost_frac=None):
    """Two axes (COMBAT_EXP2_RESULTS.md): how likely a win, and what a
    win costs. A near-certain win that routinely near-kills you is NOT
    `LOW`. `cost_frac` is the p90 HP-loss fraction from `fight_outcome`;
    when omitted, falls back to the old P(win)-only brackets (kept so
    `threat_tier(pct)` callers and fixtures still work)."""
    if cost_frac is None:
        for floor, name in THREAT_TIERS:
            if win_pct >= floor:
                return name
        return "EXTREME"
    if win_pct < 15:
        return "EXTREME"
    if win_pct < 35:
        return "SEVERE"
    if win_pct < 65:
        return "HIGH"
    # likely win — the cost axis decides
    if cost_frac < 0.20:
        return "LOW"
    if cost_frac < 0.45:
        return "MODERATE"
    return "HIGH"


def weapon_verdict(win_pct, cost_frac=None):
    """Two axes. "overkill" now requires a near-certain win AND a cheap
    one; a likely-but-expensive win reads as "you'll win, but it'll
    cost you". `cost_frac` = p50 HP-loss fraction; omitted → old
    P(win)-only text."""
    if cost_frac is None:
        if win_pct >= 85:
            return "overkill for this target"
        if win_pct >= 60:
            return "well suited to this target"
        if win_pct >= 35:
            return "adequate, but it'll cost you"
        return "poorly suited to this target"
    if win_pct < 35:
        return "poorly suited to this target"
    if win_pct < 65:
        return "a real gamble with this weapon"
    if cost_frac < 0.15:
        return "overkill for this target"
    if cost_frac < 0.35:
        return "well suited, but it'll cost you"
    return "a likely win — but expect to be near death"


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
        oc = fight_outcome(game, zombie, weapon=w, sims=sims, rng=rng)
        out.append((w, oc["win_pct"],
                    weapon_verdict(oc["win_pct"], oc["p50_frac"])))
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
