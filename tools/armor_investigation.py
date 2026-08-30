#!/usr/bin/env python3
"""Phase-2, item 7 — the armor find/acquire/equip investigation.

docs/DESIGN_ESCAPE_MODEL.md §3. The question is narrow:

  Why does a T0-4 survivor have essentially zero effective armor
  despite T0 armor being technically available?

Separates three rates, so the answer is causal, not "ARMOR_TABLE is
probably the culprit":

  A. AVAILABILITY  - how often a loot roll can even become armor
                     (analytical: the find_loot weighted pool + zone
                     bias + the intelligence>10 -> weapon override)
  B. ACQUISITION   - how often the survivor actually obtains a piece,
                     per expedition tier (campaign simulation)
  C. EQUIPPING     - of what's owned, how much is worn
                     (campaign simulation; the bot already equips
                     upgrades, so this isolates whether that's the gap)

Then the effective-armor curve vs the Exp-3 target, plus the
regression anchor: T2 Armored + best plausible early armor -> P(win)
must stay ~0%.

No src/ changes.

    python3 tools/armor_investigation.py
    python3 tools/armor_investigation.py --campaigns 30 --md docs/ARMOR_INVESTIGATION_RESULTS.md
"""
import argparse
import os
import re
import statistics
import sys
import tempfile
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.constants import ARMOR_TABLE, CAMPAIGN_LENGTH
from src.game import Apocrysis
from tools.balance_autoplay import BotIO, _OBTAINED_ARMOR_RE

_LOOT_BASE = ["food", "water", "medicine", "ammo", "weapon", "armor"]
_ZONE_LOOT_BIAS = {
    'rural':      {'armor': 0.5}, 'suburban': {'armor': 0.9},
    'industrial': {'armor': 1.6}, 'downtown': {'armor': 1.2},
    'wilderness': {'armor': 0.5},
}
_ALL_ZONES = list(_ZONE_LOOT_BIAS)


# ============================================================
# A. AVAILABILITY  (analytical — replicates find_loot's roll)
# ============================================================
def availability(tier, zone, intelligence, has_map=True, has_flash=True,
                 has_waders=True):
    """P(a successful loot roll resolves to armor) at this tier/zone."""
    pool = list(_LOOT_BASE)
    if not has_map:
        pool.append("map")
    if not has_flash:
        pool.append("flashlight")
    if not has_waders:
        pool.append("waders")
    zbias = _ZONE_LOOT_BIAS.get(zone, {})
    weighted = []
    for lt in pool:
        weighted.extend([lt] * max(1, round(zbias.get(lt, 1.0) * 4)))
    p_armor_pick = weighted.count("armor") / len(weighted)
    # the intelligence>10 override: p = int/100 chance the pick is
    # forcibly rewritten to "weapon"
    p_override = (intelligence / 100) if intelligence > 10 else 0.0
    return p_armor_pick * (1 - p_override)


def reduction_distribution(tier):
    """Given an armor drop at `tier`, the reduction you get (uniform
    over eligible ARMOR_TABLE names — find_loot uses rng.choice)."""
    eligible = [s["reduction"] for s in ARMOR_TABLE.values()
                if s.get("min_expedition", 0) <= tier]
    n = len(eligible)
    return {
        "eligible_pieces": n,
        "mean_reduction": statistics.mean(eligible),
        "p_reduction_1": eligible.count(1) / n,
        "p_reduction_ge3": sum(1 for r in eligible if r >= 3) / n,
        "best_reduction": max(eligible),
    }


# ============================================================
# B + C. ACQUISITION + EQUIPPING  (campaign simulation)
# ============================================================
class _ArmorBotIO(BotIO):
    """BotIO + per-expedition armor bookkeeping."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.armor_found_this_exp = []      # reductions

    def say(self, *args, **kwargs):
        super().say(*args, **kwargs)
        text = " ".join(str(x) for x in args)
        for line in text.splitlines():
            m = _OBTAINED_ARMOR_RE.match(line.strip())
            if m:
                name = m.group(1)
                spec = ARMOR_TABLE.get(name)
                if spec:
                    self.armor_found_this_exp.append(spec["reduction"])


def _equipped_reduction(player):
    return sum(a.damage_reduction for a in player.equipped_armor.values()
               if a and getattr(a, "durability", 1) > 0)


def _owned_reduction(player):
    eq = _equipped_reduction(player)
    pack = sum(a.damage_reduction for a in player.backpack.armor)
    return eq + pack


def run_campaigns(n, seed0, max_turns=600, max_attempts=8):
    """Per-expedition-tier: armor found / owned / equipped, across n
    campaigns. Mirrors balance_autoplay.play_campaign's profile
    carry-forward."""
    by_tier = defaultdict(lambda: {"found": [], "owned": [], "equipped": [],
                                   "slots": [], "int": []})
    for c in range(n):
        Apocrysis._used_mechanisms = []
        profile = None
        level = 1
        exp = 0
        attempts = defaultdict(int)
        with tempfile.TemporaryDirectory() as tmp:
            pf = os.path.join(tmp, "p.json")
            while exp < CAMPAIGN_LENGTH:
                attempts[exp] += 1
                if attempts[exp] > max_attempts:
                    break
                io = _ArmorBotIO(max_turns=max_turns, verbose=False)
                player = Apocrysis("ArmorBot", level=level,
                                   expeditions_completed=exp,
                                   seed=(seed0 + c * 100 + sum(attempts.values())),
                                   io=io)
                if profile is not None:
                    player.apply_profile(profile)
                io.player = player
                player.run_game_loop()

                t = by_tier[exp]
                t["found"].append(sum(io.armor_found_this_exp))
                t["owned"].append(_owned_reduction(player))
                t["equipped"].append(_equipped_reduction(player))
                t["slots"].append(sum(1 for a in player.equipped_armor.values() if a))
                t["int"].append(player.intelligence)

                level = player.level
                if player.won:
                    exp = player.expeditions_completed
                    player.save_profile(pf)
                    profile = Apocrysis.load_profile(pf)
                elif player.health <= 0:
                    # death keeps gear, retries the tier (non-hardcore)
                    player.save_profile(pf)
                    profile = Apocrysis.load_profile(pf)
                # timeout: same
    return by_tier


# ============================================================
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--campaigns", type=int, default=20)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--md", default=None)
    args = ap.parse_args()

    print(f"\n{'=' * 80}\n ARMOR INVESTIGATION — find / acquire / equip\n{'=' * 80}")

    # ---- A. availability ----
    print("\n A. AVAILABILITY — P(a successful loot roll → armor)\n")
    print(f"   {'tier':>4}  " + "  ".join(f"{z[:5]:>7}" for z in _ALL_ZONES)
          + "   (int 10 / int 16)")
    for tier in (0, 1, 2, 3, 4, 6, 8):
        lo = [availability(tier, z, 10) for z in _ALL_ZONES]
        hi = [availability(tier, z, 16) for z in _ALL_ZONES]
        print(f"   {tier:>4}  " + "  ".join(f"{v:>6.1%}" for v in lo)
              + f"   rural {lo[0]:.1%} / {hi[0]:.1%}")
    print("\n   reduction you get GIVEN an armor drop (uniform over eligible):\n")
    print(f"   {'tier':>4}  {'#pieces':>7}  {'mean red':>8}  {'P(red=1)':>8}  {'P(red≥3)':>8}  {'best':>4}")
    for tier in (0, 1, 2, 3, 4, 6, 8):
        d = reduction_distribution(tier)
        print(f"   {tier:>4}  {d['eligible_pieces']:>7}  {d['mean_reduction']:>8.2f}  "
              f"{d['p_reduction_1']:>7.0%}  {d['p_reduction_ge3']:>7.0%}  {d['best_reduction']:>4}")

    # ---- B + C. acquisition + equipping ----
    print(f"\n B + C. ACQUISITION + EQUIPPING — {args.campaigns} campaigns\n")
    by_tier = run_campaigns(args.campaigns, args.seed)
    print(f"   {'tier':>4}  {'n':>4}  {'reduction found':>15}  {'owned (med)':>11}  "
          f"{'equipped (med)':>13}  {'slots (med)':>11}  {'int (med)':>9}")
    rows = []
    for tier in sorted(by_tier):
        t = by_tier[tier]
        if not t["found"]:
            continue
        fnd = statistics.median(t["found"])
        own = statistics.median(t["owned"])
        eqp = statistics.median(t["equipped"])
        slt = statistics.median(t["slots"])
        it = statistics.median(t["int"])
        rows.append((tier, len(t["found"]), fnd, own, eqp, slt, it))
        print(f"   {tier:>4}  {len(t['found']):>4}  {fnd:>15.1f}  {own:>11.1f}  "
              f"{eqp:>13.1f}  {slt:>11.1f}  {it:>9.0f}")

    # ---- diagnosis ----
    print(f"\n{'=' * 80}\n DIAGNOSIS\n{'=' * 80}")
    _diagnose(rows)

    if args.md:
        _write_md(rows, args.md, args.campaigns)
        print(f"\n wrote {args.md}")


def _diagnose(rows):
    if not rows:
        print("  (no data)")
        return
    early = [r for r in rows if r[0] <= 4]
    med_found = statistics.median([r[2] for r in early]) if early else 0
    med_eq = statistics.median([r[4] for r in early]) if early else 0
    med_own = statistics.median([r[3] for r in early]) if early else 0
    gap_equip = med_own - med_eq
    a_rural = availability(2, "rural", 12)
    print(f"  A (availability): a loot roll at T2 in a rural zone becomes armor "
          f"~{a_rural:.1%} of the time — armor is the RAREST of ~6 loot types "
          f"there (bias 0.5×), and the int>10 rule converts more rolls to weapons.")
    print(f"  B (acquisition):  early tiers find a median of {med_found:.1f} total "
          f"reduction-points of armor per expedition.")
    print(f"  C (equipping):    of {med_own:.1f} owned reduction, {med_eq:.1f} is "
          f"worn — equip gap {gap_equip:.1f} "
          + ("(negligible — the bot equips what it finds; NOT the bottleneck)"
             if gap_equip < 1.0 else "(SIGNIFICANT — armor sits unequipped)"))
    print()
    if med_found < 2.0:
        print("  → PRIMARY BOTTLENECK: ACQUISITION. The pieces barely drop. Even "
              "with perfect equipping the early survivor can't assemble a "
              "loadout. The lever is find_loot's armor weight / the zone bias / "
              "the int>10->weapon override — NOT the ARMOR_TABLE min_expedition "
              "bands (T0 armor is already available, it just doesn't appear).")
    elif gap_equip >= 1.0:
        print("  → PRIMARY BOTTLENECK: EQUIPPING. Pieces are found but not worn.")
    else:
        print("  → armor is found and worn but the reductions are too small — "
              "the ARMOR_TABLE numbers or the reduction distribution is the lever.")


def _write_md(rows, path, n):
    L = [f"# Armor investigation — find / acquire / equip\n",
         f"`tools/armor_investigation.py` · {n} campaigns. See "
         "`docs/DESIGN_ESCAPE_MODEL.md` §3.\n",
         "## A. Availability (analytical)\n",
         "P(a successful `find_loot` roll resolves to armor), by tier and zone. "
         "Armor competes with 5 other base loot types; the rural/wilderness "
         "zones (early farmland maps) bias armor to **0.5×**, and "
         "`intelligence > 10` rewrites a further `int/100` of rolls to "
         "`weapon`.\n",
         "| tier | rural | suburban | industrial | downtown | wilderness |",
         "|---|---|---|---|---|---|"]
    for tier in (0, 1, 2, 3, 4, 6, 8):
        vs = [availability(tier, z, 12) for z in _ALL_ZONES]
        L.append(f"| {tier} | " + " | ".join(f"{v:.1%}" for v in vs) + " |")
    L.append("\n**Reduction given a drop** (uniform over eligible `ARMOR_TABLE`):\n")
    L.append("| tier | eligible pieces | mean reduction | P(reduction = 1) | P(reduction ≥ 3) | best |")
    L.append("|---|---|---|---|---|---|")
    for tier in (0, 1, 2, 3, 4, 6, 8):
        d = reduction_distribution(tier)
        L.append(f"| {tier} | {d['eligible_pieces']} | {d['mean_reduction']:.2f} "
                 f"| {d['p_reduction_1']:.0%} | {d['p_reduction_ge3']:.0%} | {d['best_reduction']} |")
    L.append("\n## B + C. Acquisition + equipping (simulated)\n")
    L.append("| tier | n | reduction found / exp (med) | owned (med) | equipped (med) | slots (med) | int (med) |")
    L.append("|---|---|---|---|---|---|---|")
    for tier, nn, fnd, own, eqp, slt, it in rows:
        L.append(f"| {tier} | {nn} | {fnd:.1f} | {own:.1f} | {eqp:.1f} | {slt:.1f} | {it:.0f} |")
    L.append("\n## Diagnosis\n")
    import io as _io, contextlib
    buf = _io.StringIO()
    with contextlib.redirect_stdout(buf):
        _diagnose(rows)
    L.append("```\n" + buf.getvalue().strip() + "\n```\n")
    L.append("## Design constraint (from `DESIGN_ESCAPE_MODEL.md` / the DDR)\n")
    L.append("Whatever the fix, it must **not** make early armor strong enough "
             "to solve the T2 Armored. The target stays: T0–1 little armor / T2 "
             "Armored → evade / T3–5 armor makes a **Heavy** survivable / T6+ "
             "Armored becomes a costly *possible* fight. Regression anchor: "
             "`T2 Armored + best plausible early armor → P(win) ~0%` "
             "(check with `tools/difficulty_ramp.py`).")
    with open(path, "w") as f:
        f.write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
