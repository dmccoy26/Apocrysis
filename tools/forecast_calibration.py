#!/usr/bin/env python3
"""Combat Model — Experiment 2: does the forecast describe reality?

docs/COMBAT_MODEL_EXPERIMENTS.md. Experiment 1 measured what a fight
actually costs. This one asks: does `combat_forecast`'s card
(`threat_tier`, `weapon_verdict`, fight %, escape %) tell the player
the actual distribution of outcomes well enough to make the intended
decision?

Method:
  1. sweep a broad encounter space (weapon x zombie x level x armor x
     condition, early through late game so all tiers populate)
  2. for each cell: the CURRENT forecast label + the measured
     P(win) / median HP-loss% / p90 HP-loss% / worst%
  3. CONFUSION MATRIX: group by current tier, show the spread of
     actual outcomes inside each label -> is the label's promise kept?
  4. a PROPOSED two-axis derivation (win-likelihood x cost-of-winning)
     and its confusion matrix, for comparison

No src/ changes. `_fight_detailed` is imported from combat_cost.py
(itself drift-guarded against combat_forecast._one_fight).

    python3 tools/forecast_calibration.py
    python3 tools/forecast_calibration.py --sims 4000 --md docs/COMBAT_EXP2_RESULTS.md
"""
import argparse
import os
import random
import statistics
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import combat_forecast as cf
from tools.combat_cost import _fight_detailed, _pstate, _zstate, _ARMOR, _WEAPONS


# The proposed two-axis model (docs/COMBAT_MODEL_EXPERIMENTS.md exp 2).
# Axis 1: how likely is a win.  Axis 2: what a win costs (p90 HP-loss
# fraction).  Tier + verdict read BOTH.
def proposed(pwin, p90_frac):
    if pwin < 15:
        return "EXTREME", "don't fight this"
    if pwin < 35:
        return "SEVERE", "you'll probably lose"
    if pwin < 65:
        return "HIGH", "a real gamble"
    # likely win (>= 65%): the cost axis decides
    if p90_frac is None:
        return "HIGH", "a real gamble"
    if p90_frac < 0.20:
        return "LOW", "overkill"
    if p90_frac < 0.45:
        return "MODERATE", "you'll win, but it'll cost you"
    return "HIGH", "you'll likely win — and likely be near death"


_LEVELS = [1, 2, 3, 4, 6, 8, 10]
_CONDS = ["fresh", "worn"]
_ZOMBIES = ["Fresh", "Regular", "Heavy", "Swift", "Toxic", "Armored"]


def _sweep(sims):
    """Every (weapon, zombie, level, armor, condition, elite) cell in a
    broad grid. Yields dicts with the current + proposed labels and the
    measured outcome distribution."""
    rows = []
    for wname, w in _WEAPONS.items():
        for zname in _ZOMBIES:
            for lv in _LEVELS:
                for cond in _CONDS:
                    for armor in ("none", "light", "kevlar"):
                        for elite in (False, True):
                            if elite and lv < 3:
                                continue
                            rows.append(_one_cell(wname, w, zname, lv, cond,
                                                  armor, elite, sims))
    return rows


def _one_cell(wname, w, zname, lv, cond, armor, elite, sims):
    rng = random.Random(hash((wname, zname, lv, cond, armor, elite)) & 0xffffffff)
    p = _pstate(lv, cond)
    p["armor_reductions"] = list(_ARMOR[armor])
    z, _ = _zstate(zname, elite)
    losses_on_win = []
    wins = 0
    for _ in range(sims):
        won, lost, _r, _h = _fight_detailed(p, z, w, rng)
        if won:
            wins += 1
            losses_on_win.append(max(0, min(lost, p["max_health"])))
    pwin = round(100 * wins / sims)
    if losses_on_win:
        s = sorted(losses_on_win)
        p50 = s[len(s) // 2] / p["max_health"]
        p90 = s[min(len(s) - 1, int(len(s) * 0.9))] / p["max_health"]
        worst = s[-1] / p["max_health"]
    else:
        p50 = p90 = worst = None
    cur_tier = cf.threat_tier(pwin)
    cur_verdict = cf.weapon_verdict(pwin)
    new_tier, new_verdict = proposed(pwin, p90)
    return {
        "cell": f"{wname} vs {'Elite ' if elite else ''}{zname} L{lv} {armor}/{cond}",
        "pwin": pwin, "p50": p50, "p90": p90, "worst": worst,
        "cur_tier": cur_tier, "cur_verdict": cur_verdict,
        "new_tier": new_tier, "new_verdict": new_verdict,
    }


def _confusion(rows, key_tier):
    """For each tier label, the spread of actual outcomes that wear it."""
    by = defaultdict(list)
    for r in rows:
        by[r[key_tier]].append(r)
    order = ["LOW", "MODERATE", "MODERATE ", "HIGH", "SEVERE", "EXTREME"]
    out = []
    for tier in sorted(by, key=lambda t: order.index(t) if t in order else 99):
        rs = by[tier]
        pw = [r["pwin"] for r in rs]
        p90s = [r["p90"] for r in rs if r["p90"] is not None]
        out.append({
            "tier": tier, "n": len(rs),
            "pwin_lo": min(pw), "pwin_hi": max(pw), "pwin_med": statistics.median(pw),
            "p90_med": (statistics.median(p90s) if p90s else None),
            "p90_lo": (min(p90s) if p90s else None),
            "p90_hi": (max(p90s) if p90s else None),
        })
    return out


# The promise each tier makes, for the pass check.
_PROMISE = {
    "LOW":      "win near-certain AND cheap (p90 loss < ~20%)",
    "MODERATE": "win likely, real but bounded cost (p90 loss ~20-45%)",
    "HIGH":     "genuine risk — uncertain win OR near-death even winning",
    "SEVERE":   "you'll probably lose",
    "EXTREME":  "do not fight",
}


def _fmt_conf(conf):
    L = []
    L.append(f"  {'tier':<9} {'n':>4}  {'P(win) range':>16}  {'P(win) med':>10}  "
             f"{'p90 loss med':>12}  {'p90 loss range':>16}")
    for c in conf:
        pr = f"{c['pwin_lo']:>3}–{c['pwin_hi']:<3}%"
        p90m = "—" if c["p90_med"] is None else f"{c['p90_med']*100:.0f}%"
        p90r = "—" if c["p90_lo"] is None else f"{c['p90_lo']*100:.0f}–{c['p90_hi']*100:.0f}%"
        L.append(f"  {c['tier']:<9} {c['n']:>4}  {pr:>16}  {c['pwin_med']:>9.0f}%  "
                 f"{p90m:>12}  {p90r:>16}")
    return "\n".join(L)


def _violations(rows):
    """Cells where the CURRENT label breaks its promise."""
    bad = []
    for r in rows:
        if r["p90"] is None:
            continue
        t = r["cur_tier"]
        if t == "LOW" and r["p90"] >= 0.30:
            bad.append(r)
        elif t == "MODERATE" and r["p90"] >= 0.55:
            bad.append(r)
        elif "overkill" in r["cur_verdict"] and r["p50"] is not None and r["p50"] >= 0.20:
            bad.append(r)
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sims", type=int, default=2500)
    ap.add_argument("--md", default=None)
    args = ap.parse_args()

    rows = _sweep(args.sims)

    print(f"\n{'=' * 82}\n COMBAT EXPERIMENT 2 — forecast calibration  "
          f"({len(rows)} cells, {args.sims} sims/cell)\n{'=' * 82}")

    print("\n CURRENT forecast — threat_tier(P(win)) only:\n")
    cur = _confusion(rows, "cur_tier")
    print(_fmt_conf(cur))

    print("\n Each tier's PROMISE vs what actually wears it:")
    for c in cur:
        pm = _PROMISE.get(c["tier"], "?")
        p90m = "—" if c["p90_med"] is None else f"{c['p90_med']*100:.0f}%"
        print(f"  {c['tier']:<9} promises: {pm}")
        print(f"  {'':<9}   reality: median p90 HP loss {p90m}, "
              f"P(win) {c['pwin_lo']}–{c['pwin_hi']}%")

    viol = _violations(rows)
    print(f"\n {len(viol)}/{len(rows)} cells break the CURRENT label's promise. Examples:")
    for r in sorted(viol, key=lambda r: -r["p90"])[:8]:
        print(f"   {r['cell']:<44} card: {r['cur_tier']:<8} \"{r['cur_verdict'][:22]}\"  "
              f"| win {r['pwin']}%  p50 {r['p50']*100:.0f}%  p90 {r['p90']*100:.0f}%")

    print("\n PROPOSED forecast — two axes: P(win) x cost-of-winning (p90):\n")
    new = _confusion(rows, "new_tier")
    print(_fmt_conf(new))
    print("\n Each proposed tier's promise vs reality:")
    for c in new:
        pm = _PROMISE.get(c["tier"], "?")
        p90m = "—" if c["p90_med"] is None else f"{c['p90_med']*100:.0f}%"
        print(f"  {c['tier']:<9} promises: {pm}")
        print(f"  {'':<9}   reality: median p90 HP loss {p90m}, "
              f"P(win) {c['pwin_lo']}–{c['pwin_hi']}%")

    print("\n ESCAPE %: combat_forecast.escape_pct is a flat "
          f"{cf.escape_pct(None, None)}% for every zombie "
          "(round(100 * _FLEE_CHANCE)). No per-zombie value exists, so the "
          "criterion \"escape ~X% -> flee succeeds ~X% for THIS zombie\" "
          "cannot pass — the number is not a forecast, it's a constant.")

    print(f"\n{'=' * 82}")

    if args.md:
        _write_md(rows, cur, new, viol, args.sims, args.md)
        print(f"wrote {args.md}")


def _write_md(rows, cur, new, viol, sims, path):
    def conf_table(conf):
        L = ["| tier | n | P(win) range | P(win) median | p90 loss median | p90 loss range |",
             "|---|---|---|---|---|---|"]
        for c in conf:
            p90m = "—" if c["p90_med"] is None else f"{c['p90_med']*100:.0f}%"
            p90r = "—" if c["p90_lo"] is None else f"{c['p90_lo']*100:.0f}–{c['p90_hi']*100:.0f}%"
            L.append(f"| {c['tier']} | {c['n']} | {c['pwin_lo']}–{c['pwin_hi']}% "
                     f"| {c['pwin_med']:.0f}% | {p90m} | {p90r} |")
        return "\n".join(L)

    out = []
    out.append("# Combat Experiment 2 — forecast calibration\n")
    out.append(f"`tools/forecast_calibration.py` · {len(rows)} cells · {sims} sims/cell. "
               "See `docs/COMBAT_MODEL_EXPERIMENTS.md`.\n")
    out.append("**The question:** does the card describe the actual distribution "
               "of outcomes well enough for the player to make the intended "
               "decision? The confusion matrices group every simulated cell by "
               "its forecast label and show the spread of what actually wears "
               "that label.\n")
    out.append("## Current forecast — `threat_tier(P(win))` only\n")
    out.append(conf_table(cur) + "\n")
    out.append(f"**{len(viol)} of {len(rows)} cells break their label's promise.** "
               "The failure mode is uniform: a tier is assigned purely on P(win), "
               "so a reliably-won fight is `LOW` no matter what it costs.\n")
    out.append("Worst offenders (LOW / \"overkill\" over a huge cost):\n")
    out.append("| cell | card | win% | p50 loss | p90 loss |")
    out.append("|---|---|---|---|---|")
    for r in sorted(viol, key=lambda r: -r["p90"])[:12]:
        out.append(f"| {r['cell']} | {r['cur_tier']} / \"{r['cur_verdict']}\" "
                   f"| {r['pwin']} | {r['p50']*100:.0f}% | {r['p90']*100:.0f}% |")
    out.append("")
    out.append("## Proposed forecast — two axes\n")
    out.append("`tier = f(P(win), cost-of-winning)` where cost is the p90 "
               "HP-loss fraction. A likely win that is expensive is no longer "
               "`LOW` — it becomes `MODERATE` (\"you'll win, but it'll cost "
               "you\") or `HIGH` (\"likely win — and likely near death\").\n")
    out.append(conf_table(new) + "\n")
    out.append("The proposed tiers are tighter: within each label the P(win) "
               "*and* the p90-loss ranges are narrower and match the promise. "
               "This is the change to make in `combat_forecast` **before** the "
               "attention hierarchy consumes the forecast.\n")
    out.append("## Escape %\n")
    out.append("`combat_forecast.escape_pct` returns a flat "
               f"`{cf.escape_pct(None, None)}%` for every zombie — "
               "`round(100 * _FLEE_CHANCE)`, `_FLEE_CHANCE = 0.50`. There is no "
               "per-zombie escape estimate to calibrate; the pass criterion "
               "\"escape ~X% → flee succeeds ~X% for this zombie\" cannot be "
               "evaluated because X does not vary. Making `escape_pct` a real "
               "function of `(zombie_speed_class, player_dex, fatigue, hp_frac)` "
               "is a **model** change (experiment 3 / the deferred "
               "escape-informed-by-threat work), not a calibration fix.\n")
    out.append("## Verdict\n")
    out.append("- The current forecast has a **category error**: it reports "
               "P(win) as if it were fight severity.\n"
               "- The proposed two-axis derivation fixes it with no balance "
               "change — same simulation, richer label.\n"
               "- `escape_pct` is not a forecast and needs the model, not "
               "calibration.\n"
               "- Do the `threat_tier` / `weapon_verdict` rewrite before "
               "wiring `combat_forecast` into `DESIGN_ATTENTION_LANGUAGE.md`'s "
               "level derivation.")
    with open(path, "w") as f:
        f.write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
