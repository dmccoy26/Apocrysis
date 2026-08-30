#!/usr/bin/env python3
"""Combat Model — Experiment 1: the cost of a fight, not just the outcome.

docs/COMBAT_MODEL_EXPERIMENTS.md. For each (weapon, zombie, player
level, armor, condition) cell in the early-game state space, Monte-Carlo
the real round loop and report — GIVEN A WIN — the distribution of HP
lost, plus rounds-to-kill and the zombie's effective damage output.

Then show what `combat_forecast` would DISPLAY for that cell
(threat tier + weapon verdict), so the gap between "you win" and
"you're fine" is visible.

    python3 tools/combat_cost.py                 # the early-game matrix
    python3 tools/combat_cost.py --sims 5000     # tighter estimates
    python3 tools/combat_cost.py --md docs/COMBAT_EXP1_RESULTS.md

The fight simulator here is a line-for-line copy of
`combat_forecast._one_fight` instrumented to also return HP lost and
rounds. `--check` runs a drift guard against the original.
"""
import argparse
import os
import random
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.constants import STATUS_EFFECT_DAMAGE, LOOT_WEAPON_TABLE
from src.items import MeleeWeapon
from src.zombies import (FreshZombie, RegularZombie, HeavyZombie, SwiftZombie,
                         ToxicZombie, ArmoredZombie)
from src import combat_forecast as cf


# --------------------------------------------------------------------
# Instrumented copy of combat_forecast._one_fight — keep in sync; the
# --check drift guard asserts the win/loss verdict still matches.
# --------------------------------------------------------------------
def _fight_detailed(player, zombie, weapon, rng):
    hp = player["health"]
    hunger = max(0, player["hunger"] - zombie.get("hunger_cost", 0))
    thirst = max(0, player["thirst"] - zombie.get("thirst_cost", 0))
    fatigue = min(100, player["fatigue"] + zombie.get("fatigue_cost", 0))
    strv, dexv = player["strength"], player["dexterity"]
    armor = list(player["armor_reductions"])

    z_hp = zombie["health"]
    z_atk = zombie["attack"]
    z_reduce = zombie.get("damage_reduction", 0.0)
    z_toxic = zombie.get("toxic", False)

    wdmg = cf._usable_damage(weapon)
    dur = getattr(weapon, "durability", None)

    crit = min(0.25, dexv / 200)
    dodge = min(0.5, dexv / 150)
    effects = {}
    start_hp = hp
    z_hits = 0

    rounds = 0
    for _ in range(60):
        rounds += 1
        if effects.get("Stun", 0) > 0:
            effects["Stun"] -= 1
        else:
            live = wdmg
            if dur is not None and dur <= 0:
                live = 0
            if live > 0:
                cp = cf._cond_penalty(hp, hunger, thirst, fatigue)
                dmg = round((live + max(0, strv // 3)) * cp)
                if rng.random() < crit:
                    dmg *= 2
                if dur is not None:
                    dur -= 1
            else:
                dmg = round(2 * cf._cond_penalty(hp, hunger, thirst, fatigue))
            z_hp -= dmg * (1 - z_reduce)
        for eff in list(effects):
            d = STATUS_EFFECT_DAMAGE.get(eff)
            if d:
                hp -= d
            effects[eff] -= 1
            if effects[eff] <= 0:
                del effects[eff]
        if z_hp <= 0:
            return True, start_hp - hp, rounds, z_hits
        if hp <= 0:
            return False, start_hp - hp, rounds, z_hits
        if rng.random() >= dodge:
            z_hits += 1
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
            return False, start_hp - hp, rounds, z_hits
    return z_hp <= 0, start_hp - hp, rounds, z_hits


# --------------------------------------------------------------------
def _pstate(level, condition):
    """Model a survivor at campaign `level`. Real play adds +1 str/dex
    and +5 max-HP per level gained (see run 7 level-ups). Condition:
    'fresh' = rested/fed, 'worn' = mid-expedition."""
    bump = level - 1
    max_hp = 100 + 5 * bump
    h, t, f = (90, 90, 10) if condition == "fresh" else (40, 40, 60)
    return {
        "health": max_hp, "max_health": max_hp,
        "hunger": h, "thirst": t, "fatigue": f,
        "strength": 12 + bump, "dexterity": 10 + bump,
        "armor_reductions": [],
    }


_ZCLASS = {
    "Fresh": FreshZombie, "Regular": RegularZombie, "Heavy": HeavyZombie,
    "Swift": SwiftZombie, "Toxic": ToxicZombie, "Armored": ArmoredZombie,
}


def _zstate(name, elite=False):
    z = _ZCLASS[name]()
    mult = 1.5 if elite else 1.0
    return {
        "health": int(z.health * mult),
        "attack": max(1, int(z.attack * mult)),
        "hunger_cost": z.hunger_cost, "thirst_cost": z.thirst_cost,
        "fatigue_cost": z.fatigue_cost,
        "damage_reduction": getattr(type(z), "damage_reduction", 0.0),
        "toxic": name == "Toxic",
    }, z.attack * mult


_ARMOR = {
    "none": [],
    "light": [2],          # Padded Vest
    "kevlar": [4],         # Kevlar Vest (exp 3+)
}

_WEAPONS = {
    "Starter (6)": MeleeWeapon("Starter", 6, 80),
    "Rusty Dagger (8)": MeleeWeapon("Rusty Dagger", 8, 40),
    "Chipped Sword (12)": MeleeWeapon("Chipped Sword", 12, 50),
    "Iron Axe (16)": MeleeWeapon("Iron Axe", 16, 90),
}


def cell(weapon, zname, level, armor, condition, sims, elite=False):
    rng = random.Random((hash((weapon, zname, level, armor, condition, elite)) & 0xffffffff))
    p = _pstate(level, condition)
    p["armor_reductions"] = list(_ARMOR[armor])
    z, zdps = _zstate(zname, elite)
    w = _WEAPONS[weapon]
    wins, losses = [], 0
    for _ in range(sims):
        won, lost, rounds, zhits = _fight_detailed(p, z, w, rng)
        if won:
            wins.append((max(0, lost), rounds, zhits))
        else:
            losses += 1
    n = sims
    pwin = round(100 * len(wins) / n)
    if wins:
        loss = sorted(x[0] for x in wins)
        rr = sorted(x[1] for x in wins)
        mean_loss = statistics.mean(loss)
        p50 = loss[len(loss) // 2]
        p90 = loss[min(len(loss) - 1, int(len(loss) * 0.9))]
        mx = loss[-1]
        r50 = rr[len(rr) // 2]
    else:
        mean_loss = p50 = p90 = mx = r50 = None
    frac = (lambda v: None if v is None else round(100 * v / p["max_health"]))
    return {
        "pwin": pwin,
        "tier": cf.threat_tier(pwin),
        "verdict": cf.weapon_verdict(pwin).replace(" for this target", "")
                                          .replace(" to this target", ""),
        "mean_loss": None if mean_loss is None else round(mean_loss),
        "p50": p50, "p90": p90, "max": mx,
        "p90_frac": frac(p90), "max_frac": frac(mx),
        "rounds": r50,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sims", type=int, default=3000)
    ap.add_argument("--md", default=None, help="also write a markdown report here")
    ap.add_argument("--check", action="store_true",
                    help="drift guard vs combat_forecast._one_fight, then exit")
    args = ap.parse_args()

    if args.check:
        _drift_check()
        return

    rows = []
    # early-game matrix: the weapons/levels/zombies a player actually
    # meets in expeditions 0-4.
    plan = [
        # (weapon, zombie, level, armor, condition, elite)
        ("Starter (6)",        "Fresh",   1, "none", "fresh", False),
        ("Starter (6)",        "Regular", 1, "none", "fresh", False),   # run 7 case A
        ("Starter (6)",        "Regular", 1, "none", "worn",  False),
        ("Starter (6)",        "Swift",   1, "none", "fresh", False),
        ("Starter (6)",        "Toxic",   2, "none", "fresh", False),
        ("Rusty Dagger (8)",   "Regular", 2, "none", "fresh", False),
        ("Chipped Sword (12)", "Regular", 2, "none", "fresh", False),
        ("Chipped Sword (12)", "Regular", 3, "light","worn",  False),
        ("Chipped Sword (12)", "Heavy",   3, "none", "worn",  False),   # run 7 case B
        ("Chipped Sword (12)", "Heavy",   3, "light","fresh", False),
        ("Chipped Sword (12)", "Armored", 3, "none", "fresh", False),
        ("Iron Axe (16)",      "Heavy",   4, "kevlar","fresh",False),
        ("Iron Axe (16)",      "Armored", 4, "kevlar","fresh",False),
        ("Iron Axe (16)",      "Heavy",   4, "kevlar","fresh",True),
    ]
    for w, z, lv, ar, cond, el in plan:
        r = cell(w, z, lv, ar, cond, args.sims, el)
        r.update(weapon=w, zombie=("Elite " + z) if el else z, level=lv,
                 armor=ar, cond=cond)
        rows.append(r)

    _print_table(rows, args.sims)
    if args.md:
        _write_md(rows, args.sims, args.md)
        print(f"\nwrote {args.md}")


def _fmt_row(r):
    return (f"  {r['weapon']:<18} {r['zombie']:<14} L{r['level']} "
            f"{r['armor']:<7}{r['cond']:<6} | "
            f"win {r['pwin']:>3}%  {r['tier']:<8} \"{r['verdict']}\"  | "
            f"loss µ{str(r['mean_loss']):>3} p50 {str(r['p50']):>3} "
            f"p90 {str(r['p90']):>3} ({r['p90_frac']}%) "
            f"max {str(r['max']):>3} ({r['max_frac']}%)  {r['rounds']}r")


def _print_table(rows, sims):
    print(f"\n{'=' * 78}\n COMBAT EXPERIMENT 1 — cost of a fight  ({sims} sims/cell)\n{'=' * 78}")
    print(" cell (weapon / zombie / level / armor / condition)")
    print("   | forecast DISPLAY (tier + verdict)")
    print("   | HP LOSS given a win: mean, p50, p90 (% max-HP), worst, median rounds\n")
    for r in rows:
        print(_fmt_row(r))
    print(f"\n{'=' * 78}")
    print(" Read: any row where the tier is LOW/MODERATE or the verdict is")
    print(' "overkill/well suited" but p90 loss is > ~40% max-HP is the forecast')
    print(" saying \"you're fine\" about a fight that routinely isn't.")


def _write_md(rows, sims, path):
    L = []
    L.append("# Combat Experiment 1 — the cost of a fight\n")
    L.append(f"Generated by `tools/combat_cost.py` ({sims} sims/cell). "
             "See `docs/COMBAT_MODEL_EXPERIMENTS.md` for the question.\n")
    L.append("**HP loss is measured GIVEN A WIN.** `p90 %` / `max %` are "
             "fractions of the survivor's max HP. The forecast columns are "
             "what `combat_forecast` would put on the encounter card for "
             "that cell.\n")
    L.append("| weapon | zombie | lvl | armor | cond | win% | tier | verdict | "
             "loss µ | p50 | p90 | p90 % | worst | worst % | rnds |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        L.append(f"| {r['weapon']} | {r['zombie']} | {r['level']} | {r['armor']} "
                 f"| {r['cond']} | {r['pwin']} | {r['tier']} | {r['verdict']} "
                 f"| {r['mean_loss']} | {r['p50']} | {r['p90']} | {r['p90_frac']} "
                 f"| {r['max']} | {r['max_frac']} | {r['rounds']} |")
    L.append("")
    L.append("## The two run-7 cases\n")
    a = next(r for r in rows if r['weapon'].startswith('Starter') and r['zombie'] == 'Regular' and r['cond'] == 'fresh')
    b = next(r for r in rows if r['weapon'].startswith('Chipped') and r['zombie'] == 'Heavy' and r['cond'] == 'worn')
    L.append(f"- **Case A** (exp 1 t5 — Starter vs Regular, L1, fresh, no armor): "
             f"card shows **{a['tier']} / \"{a['verdict']}\" / Fight ~{a['pwin']}%**. "
             f"Actual: p90 loss **{a['p90']} HP ({a['p90_frac']}% of max)**, "
             f"worst **{a['max']} ({a['max_frac']}%)**. "
             f"The card says trivial; the p90 says half-dead.")
    L.append(f"- **Case B** (exp 3 t9 — Chipped Sword vs Heavy, L3, worn, no armor): "
             f"card shows **{b['tier']} / \"{b['verdict']}\" / Fight ~{b['pwin']}%**. "
             f"Actual win rate {b['pwin']}% — the card is honest here; this is a "
             f"model / ramp problem, not a communication one.")
    L.append("")
    L.append("## What this says for the attention spec\n")
    L.append("`threat_tier` and `weapon_verdict` are pure functions of `P(win)`. "
             "Every row above where a LOW/MODERATE tier sits next to a p90 loss "
             "over ~40% max-HP is a cell where the attention level (which the "
             "spec derives from the forecast) would be set too low. The fix is "
             "in `combat_forecast`, not the attention renderer — "
             "`threat_tier = f(P(win), expected_HP_loss_fraction, worst_case_HP)`.")
    with open(path, "w") as f:
        f.write("\n".join(L) + "\n")


def _drift_check():
    """The instrumented copy must agree with combat_forecast._one_fight
    on the win/loss verdict for paired RNG streams."""
    mism = 0
    trials = 400
    for i in range(trials):
        p = _pstate(random.choice([1, 2, 3, 4]), random.choice(["fresh", "worn"]))
        p["armor_reductions"] = random.choice(list(_ARMOR.values()))
        zname = random.choice(list(_ZCLASS))
        z, _ = _zstate(zname, random.random() < 0.3)
        w = random.choice(list(_WEAPONS.values()))
        r1 = random.Random(i)
        r2 = random.Random(i)
        got = _fight_detailed(p, z, w, r1)[0]
        want = cf._one_fight(p, z, w, r2)
        if got != want:
            mism += 1
    if mism:
        print(f"DRIFT: {mism}/{trials} verdict mismatches — _fight_detailed has "
              "diverged from combat_forecast._one_fight")
        sys.exit(1)
    print(f"drift check OK — {trials}/{trials} verdicts match combat_forecast._one_fight")


if __name__ == "__main__":
    main()
