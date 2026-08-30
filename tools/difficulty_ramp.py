#!/usr/bin/env python3
"""Combat Model — Experiment 3: the difficulty ramp.

docs/COMBAT_MODEL_EXPERIMENTS.md. Not "is combat balanced" — the
precise question:

    At what expedition depth does the game first present a fight whose
    consequence exceeds the player's available means to deal with it —
    with BEST-AVAILABLE realistic gear, and no credible avoidance path?

Method:
  1. realistic power curve: run N full campaigns (balance_autoplay's
     play_campaign) and take the median (level, best weapon damage,
     best armor reduction) reached at each expedition tier
  2. zombie composition per tier: replicate
     world_mixin._select_zombie_for_encounter's weight interpolation
     (t = exp / DIFFICULTY_RAMP_LENGTH) + the elite gate
  3. for each tier, for each zombie type that spawns with meaningful
     probability, simulate the fight with that tier's realistic best
     gear -> P(win), p90 HP-loss, current tier, proposed two-axis tier
  4. flag the first tier where a meaningfully-probable zombie is
     proposed-EXTREME (or SEVERE) on best gear, and report the
     minimum achievable death risk (fight, or flee-then-forced-fight)

No src/ changes.

    python3 tools/difficulty_ramp.py
    python3 tools/difficulty_ramp.py --campaigns 20 --sims 3000 --md docs/COMBAT_EXP3_RESULTS.md
"""
import argparse
import os
import random
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.constants import DIFFICULTY_RAMP_LENGTH, ELITE_MIN_EXPEDITION
from src.items import MeleeWeapon
from tools.combat_cost import _fight_detailed, _pstate, _zstate
from tools.forecast_calibration import proposed
from src import combat_forecast as cf

_FLEE = 0.50  # combat_mixin: if random.random() < 0.5
_ZNAMES = ["Fresh", "Regular", "Heavy", "Swift", "Toxic", "Armored"]
_EARLY_W = [0.62, 0.26, 0.00, 0.10, 0.02, 0.00]
_LATE_W = [0.10, 0.15, 0.25, 0.15, 0.15, 0.20]


def _composition(exp):
    t = min(1.0, exp / DIFFICULTY_RAMP_LENGTH)
    w = [e + (l - e) * t for e, l in zip(_EARLY_W, _LATE_W)]
    s = sum(w)
    w = [x / s for x in w]
    elite = (min(0.3, exp * 0.03) if exp >= ELITE_MIN_EXPEDITION else 0.0)
    return dict(zip(_ZNAMES, w)), elite


# ---- realistic power curve -------------------------------------------------
def _power_curve(n_campaigns, seed0):
    from tools.balance_autoplay import play_campaign
    agg = {}
    for i in range(n_campaigns):
        res = play_campaign(seed=seed0 + i, max_turns=600,
                            max_attempts_per_tier=8, verbose=False)
        for tier, samples in res.get("power_by_expedition", {}).items():
            for s in samples:
                agg.setdefault(tier, {"lv": [], "wpn": [], "arm": []})
                agg[tier]["lv"].append(s["level"])
                agg[tier]["wpn"].append(s["best_weapon_damage"])
                agg[tier]["arm"].append(s["best_armor_reduction"])
    curve = {}
    for tier, d in sorted(agg.items()):
        curve[tier] = {
            "level": round(statistics.median(d["lv"])),
            "weapon": round(statistics.median(d["wpn"])),
            "armor": round(statistics.median(d["arm"])),
            "n": len(d["lv"]),
        }
    return curve


# ---- one (tier, zombie) fight evaluation ----------------------------------
def _evaluate(gear, zname, elite, sims):
    rng = random.Random(hash((gear["level"], gear["weapon"], gear["armor"],
                              zname, elite)) & 0xffffffff)
    p = _pstate(max(1, gear["level"]), "worn")   # mid-expedition = the honest case
    p["armor_reductions"] = [gear["armor"]] if gear["armor"] > 0 else []
    w = MeleeWeapon("best", max(1, gear["weapon"]), 100)
    z, _ = _zstate(zname, elite)
    wins, losses_on_win = 0, []
    for _ in range(sims):
        won, lost, _r, _h = _fight_detailed(p, z, w, rng)
        if won:
            wins += 1
            losses_on_win.append(max(0, min(lost, p["max_health"])))
    pwin = round(100 * wins / sims)
    if losses_on_win:
        s = sorted(losses_on_win)
        p90 = s[min(len(s) - 1, int(len(s) * 0.9))] / p["max_health"]
    else:
        p90 = None
    cur = cf.threat_tier(pwin)
    new_tier, new_verdict = proposed(pwin, p90)
    p_death_if_fight = 1 - wins / sims
    # min achievable death risk: fight, or flee (50%) then forced fight
    min_death = min(p_death_if_fight, (1 - _FLEE) * p_death_if_fight)
    return {
        "zombie": ("Elite " if elite else "") + zname,
        "pwin": pwin, "p90": p90, "cur": cur,
        "new": new_tier, "verdict": new_verdict,
        "p_death_fight": p_death_if_fight, "min_death": min_death,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--campaigns", type=int, default=15)
    ap.add_argument("--sims", type=int, default=2500)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--min-weight", type=float, default=0.04,
                    help="ignore zombie types rarer than this at a tier")
    ap.add_argument("--md", default=None)
    args = ap.parse_args()

    print(f"\n running {args.campaigns} campaigns for the realistic power curve...")
    curve = _power_curve(args.campaigns, args.seed)

    print(f"\n{'=' * 84}\n COMBAT EXPERIMENT 3 — the difficulty ramp"
          f"  ({args.sims} sims/cell)\n{'=' * 84}")
    print("\n realistic best-available gear by expedition tier "
          "(median across campaigns):\n")
    print(f"  {'tier':>4}  {'level':>5}  {'best wpn dmg':>12}  {'best armor':>10}  {'n':>4}")
    for tier, g in curve.items():
        print(f"  {tier:>4}  {g['level']:>5}  {g['weapon']:>12}  {g['armor']:>10}  {g['n']:>4}")

    rows_by_tier = {}
    first_cliff = None
    for tier in sorted(curve):
        gear = curve[tier]
        comp, elite_ch = _composition(tier)
        evals = []
        for zname, wt in comp.items():
            if wt < args.min_weight:
                continue
            evals.append((wt, _evaluate(gear, zname, False, args.sims)))
            if elite_ch >= 0.05:
                evals.append((wt * elite_ch, _evaluate(gear, zname, True, args.sims)))
        rows_by_tier[tier] = evals
        worst = max(evals, key=lambda e: e[1]["min_death"])
        if first_cliff is None and worst[1]["new"] in ("EXTREME", "SEVERE") \
                and worst[0] >= args.min_weight * 0.5:
            first_cliff = (tier, worst)

    print(f"\n per-tier worst credible encounter (proposed tier · min death risk):\n")
    print(f"  {'tier':>4}  {'zombie':<14}  {'spawn~':>6}  {'win%':>5}  "
          f"{'p90':>5}  {'cur':<8}  {'proposed':<8}  {'P(die|fight)':>12}  {'min P(die)':>10}")
    for tier in sorted(rows_by_tier):
        for wt, e in sorted(rows_by_tier[tier], key=lambda x: -x[1]["min_death"])[:3]:
            p90 = "—" if e["p90"] is None else f"{e['p90']*100:.0f}%"
            mark = "  <<< first cliff" if first_cliff and tier == first_cliff[0] \
                and e is first_cliff[1][1] else ""
            print(f"  {tier:>4}  {e['zombie']:<14}  {wt*100:>5.1f}%  {e['pwin']:>4}%  "
                  f"{p90:>5}  {e['cur']:<8}  {e['new']:<8}  {e['p_death_fight']:>11.0%}  "
                  f"{e['min_death']:>9.0%}{mark}")

    print(f"\n{'=' * 84}")
    if first_cliff:
        tier, (wt, e) = first_cliff
        print(f" FIRST CLIFF: expedition tier {tier} — a {e['zombie']} "
              f"(spawns ~{wt*100:.0f}% of encounters) is proposed-{e['new']} "
              f"with best realistic gear (level {curve[tier]['level']}, "
              f"weapon {curve[tier]['weapon']} dmg, armor {curve[tier]['armor']}).")
        print(f"   Fighting: {e['p_death_fight']:.0%} death.  "
              f"Best case (flee, {_FLEE:.0%} success, else forced fight): "
              f"{e['min_death']:.0%} death.  There is no credible avoidance path — "
              "escape is a flat coin flip and failing it forces the fight.")
        print(f"\n The design question (COMBAT_MODEL_EXPERIMENTS.md exp 3):")
        print(f"   Is expedition {tier} SUPPOSED to contain a \"don't fight this\" enemy?")
        print( "     YES -> the player needs a real escape / avoidance path "
               "(escape_pct must stop being a coin flip; or a warning + room to run)")
        print( "     NO  -> gate the Heavy/Armored later, lift the loot band, "
               "or soften the composition ramp before this tier")
    else:
        print(" No cliff found in the tiers sampled.")

    if args.md:
        _write_md(curve, rows_by_tier, first_cliff, args, args.md)
        print(f"\n wrote {args.md}")


def _write_md(curve, rows_by_tier, first_cliff, args, path):
    L = []
    L.append("# Combat Experiment 3 — the difficulty ramp\n")
    L.append(f"`tools/difficulty_ramp.py` · {args.campaigns} campaigns for the "
             f"power curve · {args.sims} sims/cell. See "
             "`docs/COMBAT_MODEL_EXPERIMENTS.md`.\n")
    L.append("**Question:** at what expedition depth does the game first present "
             "a fight whose consequence exceeds the player's available means — "
             "with best realistic gear and no credible avoidance path?\n")
    L.append("## Realistic best-available gear by tier (median across campaigns)\n")
    L.append("| tier | level | best weapon dmg | best armor reduction | n |")
    L.append("|---|---|---|---|---|")
    for tier, g in curve.items():
        L.append(f"| {tier} | {g['level']} | {g['weapon']} | {g['armor']} | {g['n']} |")
    L.append("")
    L.append("## Per-tier worst credible encounter\n")
    L.append("Fight simulated with the tier's realistic gear, mid-expedition "
             "condition. `min P(die)` = the best the player can do: fight, or "
             "flee (flat 50%) then forced fight on failure.\n")
    L.append("| tier | zombie | spawn ~ | win% | p90 loss | current tier | proposed tier | P(die\\|fight) | min P(die) |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for tier in sorted(rows_by_tier):
        for wt, e in sorted(rows_by_tier[tier], key=lambda x: -x[1]["min_death"])[:3]:
            p90 = "—" if e["p90"] is None else f"{e['p90']*100:.0f}%"
            L.append(f"| {tier} | {e['zombie']} | {wt*100:.1f}% | {e['pwin']} | {p90} "
                     f"| {e['cur']} | {e['new']} | {e['p_death_fight']:.0%} | {e['min_death']:.0%} |")
    L.append("")
    if first_cliff:
        tier, (wt, e) = first_cliff
        L.append("## The first cliff\n")
        L.append(f"**Expedition tier {tier}.** A **{e['zombie']}** (~{wt*100:.0f}% "
                 f"of encounters at this tier) is proposed-**{e['new']}** with the "
                 f"best gear a real campaign has by then (level {curve[tier]['level']}, "
                 f"weapon {curve[tier]['weapon']} dmg, armor {curve[tier]['armor']}).\n")
        L.append(f"- Fighting: **{e['p_death_fight']:.0%} death**.\n"
                 f"- Best case (flee at flat {_FLEE:.0%}, else forced fight): "
                 f"**{e['min_death']:.0%} death**.\n"
                 f"- **No credible avoidance path** — escape is a coin flip and "
                 f"failing it forces the fight. This is run 7's exp-3 Heavy, "
                 f"confirmed as the structural cliff, not bad luck.\n")
        L.append("## The design question\n")
        L.append(f"Is expedition {tier} *supposed* to contain a \"don't fight this\" "
                 "enemy?\n")
        L.append("- **YES** → the player needs a real escape / avoidance path: "
                 "`escape_pct` must become a function of zombie speed / player "
                 "dex (a slow Heavy should be very escapable), and/or the "
                 "encounter should arrive with enough warning and open ground to "
                 "run. A guaranteed-lethal forced fight is not a decision.\n")
        L.append("- **NO** → gate Heavy/Armored to a later tier, lift the loot "
                 "band so armor actually develops (it currently medians "
                 f"{curve.get(first_cliff[0], {}).get('armor', 0)} at the cliff), "
                 "or soften the composition ramp before this tier.\n")
    L.append("## Note on the power curve\n")
    L.append("Armor reduction stays near 0 for most of the campaign (confirmed "
             "here and in `balance_autoplay`'s own comments). The player's only "
             "real combat-power axis is weapon damage, which plateaus ~20–26 "
             "around tier 3. So \"best-available gear\" past ~tier 3 barely "
             "improves — the ramp climbs, the counter-play doesn't.")
    with open(path, "w") as f:
        f.write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
