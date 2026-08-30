#!/usr/bin/env python3
"""Phase-2 harness — the escape model.

docs/DESIGN_ESCAPE_MODEL.md. Defines ONE candidate `escape_probability`
and evaluates it against the completion gate:

  R1–R6 fixtures · monotonicity matrix (§4a) · bounded influence (§4b)
  · intrinsic/availability/resolved split (§4) · statistical trust (§5)

Discipline: the model is defined first (the constants block below),
then evaluated. A failing fixture means revise the MODEL, not nudge a
coefficient until R6 goes green.

This is the experiment. When the gate passes, the same function moves
into `combat_mixin` as the single source of truth the flee roll and
`combat_forecast.escape_pct` both call.

    python3 tools/escape_model.py
    python3 tools/escape_model.py --md docs/ESCAPE_MODEL_RESULTS.md
"""
import argparse
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ====================================================================
# THE MODEL  (define once; do not tune to pass)
# ====================================================================

# Dominant factor: zombie speed class. Survivor state is secondary
# (bounded influence, §4b).
_SPEED_BASE = {"slow": 0.88, "normal": 0.55, "fast": 0.24}

_SPEED_CLASS = {
    "Fresh": "normal", "Regular": "normal", "Toxic": "normal",
    "Heavy": "slow", "Armored": "slow",
    "Swift": "fast",
}

# Dexterity: neutral at 10; ±0.012 per point, capped so it can't flip
# the speed relationship on its own.
_DEX_PER_POINT = 0.012
_DEX_CAP = 0.12

# Fatigue / low HP: a tired or wounded survivor doesn't outrun things.
def _fatigue_mod(fatigue):
    if fatigue > 80:
        return -0.15
    if fatigue > 50:
        return -0.08
    return 0.0

def _hp_mod(hp_frac):
    if hp_frac < 0.25:
        return -0.15
    if hp_frac < 0.50:
        return -0.08
    return 0.0

_INTRINSIC_FLOOR, _INTRINSIC_CEIL = 0.05, 0.97

# Terrain: intrinsic escape is "can I outrun it"; availability is
# "is there anywhere to run". Kept separate (§ intrinsic/contextual).
_TERRAIN_AVAIL = {
    "open": 1.00,       # plain, road
    "reduced": 0.60,    # forest, settlement street, swamp, water
    "confined": 0.22,   # inside a building
}
_TERRAIN_OF = {
    "plain": "open", "road": "open",
    "forest": "reduced", "town": "reduced", "swamp": "reduced", "water": "reduced",
    "building": "confined",
}
_RESOLVED_FLOOR, _RESOLVED_CEIL = 0.02, 0.97


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


def _availability(terrain):
    """Accepts an availability class ('open'/'reduced'/'confined') or a
    raw terrain name ('plain'/'forest'/'building'/…)."""
    if terrain in _TERRAIN_AVAIL:
        return _TERRAIN_AVAIL[terrain]
    return _TERRAIN_AVAIL[_TERRAIN_OF.get(terrain, "reduced")]


def escape_probability(speed_class, dexterity, fatigue, hp_frac, terrain):
    """Returns {intrinsic, availability, resolved}. `resolved` is what
    the flee roll compares against and what the card shows."""
    base = _SPEED_BASE[speed_class]
    dex = _clamp((dexterity - 10) * _DEX_PER_POINT, -_DEX_CAP, _DEX_CAP)
    intrinsic = _clamp(base + dex + _fatigue_mod(fatigue) + _hp_mod(hp_frac),
                       _INTRINSIC_FLOOR, _INTRINSIC_CEIL)
    avail = _availability(terrain)
    resolved = _clamp(intrinsic * avail, _RESOLVED_FLOOR, _RESOLVED_CEIL)
    return {"intrinsic": intrinsic, "availability": avail, "resolved": resolved}


# ====================================================================
# EVALUATION
# ====================================================================

def _p(zombie, dex, fatigue, hp_frac, terrain):
    return escape_probability(_SPEED_CLASS[zombie], dex, fatigue, hp_frac, terrain)


# L3 survivor ≈ dex 12 (dev/_pstate model). "healthy rested" / "worn".
_L3_DEX = 12


def fixtures():
    R1 = _p("Armored", _L3_DEX, 10, 1.00, "open")
    R2w = _p("Armored", _L3_DEX, 60, 0.40, "open")     # wounded+fatigued
    R2x = _p("Armored", _L3_DEX, 90, 0.20, "open")     # extreme
    R3 = _p("Swift", _L3_DEX, 10, 1.00, "open")
    R4 = _p("Armored", _L3_DEX, 10, 1.00, "confined")
    R5lo = _p("Regular", 4, 30, 1.0, "open")
    R5hi = _p("Regular", 20, 30, 1.0, "open")
    rows = []
    rows.append(("R1  Armored·healthy·rested·open",
                 R1, R1["resolved"] >= 0.75, "resolved ≥ 0.75 (reliably high)"))
    rows.append(("R2  Armored·wounded+fatigued·open",
                 R2w, R2w["resolved"] < R1["resolved"] - 0.08 and R2w["resolved"] > 0.5,
                 "materially below R1, still > 0.5 (best option)"))
    rows.append(("R2x Armored·extreme(20%HP,90fat)·open",
                 R2x, R2x["resolved"] < R2w["resolved"],
                 "below R2 (state keeps mattering)"))
    rows.append(("R3  Swift·healthy·rested·open",
                 R3, R3["resolved"] < R1["resolved"] - 0.20,
                 "materially below the Armored (fast = hard to disengage)"))
    rows.append(("R4  Armored·confined",
                 R4, R4["resolved"] < 0.35 and R4["availability"] < 1.0,
                 "constrained — availability < 1, resolved low"))
    rows.append(("R5  Dexterity 4 vs 20 (Regular·open)",
                 {"lo": R5lo["resolved"], "hi": R5hi["resolved"]},
                 R5hi["resolved"] > R5lo["resolved"],
                 "escape ↑ with Dex"))
    rows.append(("R6  \"don't fight\" is a strategy not a coin flip",
                 R1, R1["resolved"] >= 0.70,
                 "R1 resolved materially above 0.50 (ideally 0.75–0.90)"))
    return rows


_BASELINE = dict(dex=_L3_DEX, fatigue=30, hp_frac=1.0, terrain="open", zombie="Regular")


def monotonicity():
    b = _BASELINE
    def r(**kw):
        a = {**b, **kw}
        return _p(a["zombie"], a["dex"], a["fatigue"], a["hp_frac"], a["terrain"])["resolved"]
    checks = [
        ("zombie speed  Swift → Regular → Armored",
         [r(zombie="Swift"), r(zombie="Regular"), r(zombie="Armored")]),
        ("Dexterity      4 → 12 → 20",
         [r(dex=4), r(dex=12), r(dex=20)]),
        ("fatigue        90 → 30 → 0   (rested = higher escape)",
         [r(fatigue=90), r(fatigue=30), r(fatigue=0)]),
        ("HP fraction    0.2 → 0.6 → 1.0",
         [r(hp_frac=0.2), r(hp_frac=0.6), r(hp_frac=1.0)]),
        ("terrain avail  confined → reduced → open",
         [r(terrain="building"), r(terrain="forest"), r(terrain="plain")]),
    ]
    out = []
    for label, vals in checks:
        ok = all(vals[i] <= vals[i + 1] + 1e-9 for i in range(len(vals) - 1))
        out.append((label, vals, ok))
    return out


def bounded_influence():
    # slow zombie, worst plausible survivor state, open ground
    slow_worst = escape_probability("slow", 3, 90, 0.15, "open")["resolved"]
    # fast zombie, best plausible survivor state, open ground
    fast_best = escape_probability("fast", 25, 0, 1.0, "open")["resolved"]
    return slow_worst, fast_best, slow_worst > fast_best


def trust_check(trials=200000):
    """The flee roll IS `random() < resolved`. Confirm empirically."""
    rng = random.Random(12345)
    worst = 0.0
    for zc in ("slow", "normal", "fast"):
        for terr in ("open", "reduced", "confined"):
            p = escape_probability(zc, 12, 30, 1.0, terr)["resolved"]
            hits = sum(1 for _ in range(trials) if rng.random() < p)
            emp = hits / trials
            worst = max(worst, abs(emp - p))
    return worst


def _fmt_pr(pr):
    if "resolved" in pr:
        return (f"intrinsic {pr['intrinsic']:.2f}  × avail {pr['availability']:.2f}  "
                f"→ resolved {pr['resolved']:.2f}")
    return f"lo {pr['lo']:.2f}  hi {pr['hi']:.2f}"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--md", default=None)
    args = ap.parse_args()

    fx = fixtures()
    mono = monotonicity()
    sw, fb, bounded_ok = bounded_influence()
    trust_err = trust_check()

    print(f"\n{'=' * 78}\n ESCAPE MODEL — Phase-2 harness\n{'=' * 78}")
    print("\n MODEL: resolved = clamp(intrinsic × terrain_availability)")
    print("   intrinsic = speed_base + dex_mod + fatigue_mod + hp_mod")
    print(f"   speed_base  slow {_SPEED_BASE['slow']}  normal {_SPEED_BASE['normal']}  "
          f"fast {_SPEED_BASE['fast']}")
    print(f"   dex ±{_DEX_PER_POINT}/pt cap ±{_DEX_CAP} · fatigue -0.08/-0.15 · "
          f"hp -0.08/-0.15")
    print(f"   terrain  open {_TERRAIN_AVAIL['open']}  reduced {_TERRAIN_AVAIL['reduced']}  "
          f"confined {_TERRAIN_AVAIL['confined']}")

    print(f"\n R1–R6 fixtures:\n")
    all_ok = True
    for label, pr, ok, why in fx:
        all_ok &= ok
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
        print(f"         {_fmt_pr(pr)}   ({why})")

    print(f"\n §4a monotonicity matrix:\n")
    for label, vals, ok in mono:
        all_ok &= ok
        print(f"  [{'PASS' if ok else 'FAIL'}] {label:<48}  "
              + " → ".join(f"{v:.2f}" for v in vals))

    print(f"\n §4b bounded influence:  slow/worst-state {sw:.2f}  >  "
          f"fast/best-state {fb:.2f}   [{'PASS' if bounded_ok else 'FAIL'}]")
    all_ok &= bounded_ok

    print(f"\n §5 trust — empirical flee rate vs predicted, worst |Δ| over "
          f"9 cells: {trust_err:.4f}   [{'PASS' if trust_err < 0.01 else 'FAIL'}]")
    all_ok &= trust_err < 0.01

    print(f"\n{'=' * 78}\n GATE (items 1–6): {'PASS' if all_ok else 'FAIL'}   "
          "(item 7 — armor progression — is a separate difficulty_ramp check)\n{'=' * 78}"
          .replace("{'=' * 78}", "=" * 78))

    if args.md:
        _write_md(fx, mono, (sw, fb, bounded_ok), trust_err, all_ok, args.md)
        print(f" wrote {args.md}")


def _write_md(fx, mono, bi, trust_err, all_ok, path):
    sw, fb, bounded_ok = bi
    L = ["# Escape model — Phase-2 harness results\n",
         "`tools/escape_model.py`. See `docs/DESIGN_ESCAPE_MODEL.md`.\n",
         "## The model (one source of truth)\n",
         "```\n"
         "resolved = clamp(intrinsic × terrain_availability, 0.02, 0.97)\n"
         "intrinsic = speed_base + dex_mod + fatigue_mod + hp_mod   (clamped 0.05–0.97)\n\n"
         f"speed_base    slow {_SPEED_BASE['slow']}   normal {_SPEED_BASE['normal']}   fast {_SPEED_BASE['fast']}\n"
         f"dex_mod       (dex-10) × {_DEX_PER_POINT}, capped ±{_DEX_CAP}\n"
         "fatigue_mod   0 / -0.08 (>50) / -0.15 (>80)\n"
         "hp_mod        0 / -0.08 (<0.5) / -0.15 (<0.25)\n"
         f"terrain       open {_TERRAIN_AVAIL['open']}   reduced {_TERRAIN_AVAIL['reduced']}   confined {_TERRAIN_AVAIL['confined']}\n"
         "```\n",
         "The flee roll is `random() < resolved`; `combat_forecast.escape_pct` "
         "is `round(100 * resolved)` on the same inputs. Never two formulas.\n",
         "## R1–R6\n",
         "| fixture | intrinsic | avail | resolved | pass | requirement |",
         "|---|---|---|---|---|---|"]
    for label, pr, ok, why in fx:
        if "resolved" in pr:
            L.append(f"| {label} | {pr['intrinsic']:.2f} | {pr['availability']:.2f} "
                     f"| {pr['resolved']:.2f} | {'✅' if ok else '❌'} | {why} |")
        else:
            L.append(f"| {label} | — | — | lo {pr['lo']:.2f} / hi {pr['hi']:.2f} "
                     f"| {'✅' if ok else '❌'} | {why} |")
    L.append("\n## §4a Monotonicity matrix\n")
    L.append("| variable (low → baseline → high) | values | pass |")
    L.append("|---|---|---|")
    for label, vals, ok in mono:
        L.append(f"| {label} | {' → '.join(f'{v:.2f}' for v in vals)} | {'✅' if ok else '❌'} |")
    L.append(f"\n## §4b Bounded influence\n")
    L.append(f"`escape(slow, worst survivor state, open)` = **{sw:.2f}**  >  "
             f"`escape(fast, best survivor state, open)` = **{fb:.2f}**  → "
             f"{'✅ zombie speed stays the dominant factor' if bounded_ok else '❌ state can invert speed'}\n")
    L.append(f"## §5 Trust\n")
    L.append(f"Worst |empirical − predicted| flee rate over 9 (speed × terrain) "
             f"cells, 200k trials each: **{trust_err:.4f}** "
             f"{'✅' if trust_err < 0.01 else '❌'} — the roll and the forecast "
             f"read the same number.\n")
    L.append(f"## Gate\n")
    L.append(f"Items 1–6: **{'PASS' if all_ok else 'FAIL'}**. Item 7 (armor "
             "progression moved earlier, Armored still ~0% fight at T2) is a "
             "separate `tools/difficulty_ramp.py` check — pending the "
             "`ARMOR_TABLE` band change.\n")
    L.append("## What moves to `combat_mixin` when the gate is green\n")
    L.append("- `escape_probability(player, zombie, terrain)` — exactly this "
             "function, as the single source of truth\n"
             "- zombie `speed_class` on the roster (`src/zombies.py`)\n"
             "- the flee roll becomes `random() < escape_probability(...).resolved`\n"
             "- `combat_forecast.escape_pct` becomes `round(100 * ...resolved)`")
    with open(path, "w") as f:
        f.write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
