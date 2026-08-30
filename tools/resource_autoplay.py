#!/usr/bin/env python3
"""Resource / attrition investigation.

The telemetry recorder (tools/telemetry.py) showed the escape model +
graded attention crossed the threshold - combat deaths ~0, EXTREME /
SEVERE all evaded - and the survivor now dies slowly of
starvation / exhaustion instead. This tool asks WHY, causally, before
anything is tuned.

Reuses the telemetry event stream and adds a resource-economy report:

  FOOD / WATER   acquired · consumed · carried · turns between finds ·
                 turns hungry / starving · starvation transitions ·
                 "available but not consumed" vs "never acquired" vs
                 "consumed too late"
  FATIGUE        gained/turn · recovery events (rest / building) ·
                 turns rested/fatigued/exhausted · transitions ·
                 does recovery keep up
  CAUSE OF DEATH combat / starvation / exhaustion / other
  BEFORE THE WALL  median state right before a starving / exhausted flip
  POLICY BEHAVIOUR when hungry -> ate / searched / travelled ;
                   when exhausted -> rested / travelled / fought
  TERRAIN COST   fatigue gained + food finds per terrain

    python3 tools/resource_autoplay.py --campaigns 20 --policy survival
    python3 tools/resource_autoplay.py --campaigns 20 --policy resource   # a trying player
"""
import argparse
import os
import statistics
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.telemetry import Recorder, run_campaign


def _med(xs):
    xs = list(xs)
    return statistics.median(xs) if xs else 0.0


def resource_report(events):
    turns = [e for e in events if e["event"] == "turn"]
    res = [e for e in events if e["event"] == "resource"]
    trans = [e for e in events if e["event"] == "state_transition"]
    combats = [e for e in events if e["event"] == "combat"]
    exp_end = [e for e in events if e["event"] == "expedition_end"]

    key = lambda e: (e["campaign"], e["run"])
    by_run_turns = defaultdict(list)
    for e in turns:
        by_run_turns[key(e)].append(e)
    for v in by_run_turns.values():
        v.sort(key=lambda e: e["turn"])

    L = ["=" * 66, " RESOURCE / ATTRITION REPORT", "=" * 66]
    L.append(f" expeditions: {len(exp_end)}   turns: {len(turns)}")
    oc = Counter(e["outcome"] for e in exp_end)
    L.append(" outcomes: " + "  ".join(f"{k} {v}" for k, v in oc.most_common()))

    # ---------- cause of death ----------
    L.append("\n CAUSE OF DEATH (expeditions that ended 'died')")
    died = [e for e in exp_end if e["outcome"] == "died"]
    causes = Counter()
    for e in died:
        rt = by_run_turns.get(key(e), [])
        last = rt[-3:] if rt else []
        combat_death = any(c["outcome"] == "death" for c in combats
                           if key(c) == key(e))
        starving = any(t["hunger_band"] == "starving" for t in last)
        exhausted = any(t["fatigue_band"] == "exhausted" for t in last)
        if combat_death:
            causes["combat"] += 1
        elif starving and exhausted:
            causes["starvation+exhaustion"] += 1
        elif starving:
            causes["starvation"] += 1
        elif exhausted:
            causes["exhaustion"] += 1
        else:
            causes["other"] += 1
    tot = sum(causes.values()) or 1
    for c, n in causes.most_common():
        L.append(f"   {c:<24} {n:>3}  ({100*n//tot}%)")

    # ---------- food / water economy ----------
    for kind, band_key, low, worse in (("food", "hunger_band", "hungry", "starving"),
                                       ("water", "hunger_band", None, None)):
        acq = [e for e in res if e["kind"] == kind and e["op"] == "found"]
        con = [e for e in res if e["kind"] == kind and e["op"] == "consumed"]
        acq_units = sum(e["qty"] or 4 for e in acq)   # unquantified find ~= 4
        con_units = sum(e["qty"] or 0 for e in con)
        L.append(f"\n {kind.upper()}")
        L.append(f"   finds: {len(acq)}   (~{acq_units} units)   "
                 f"consume actions: {len(con)}   (~{con_units} units)")
        # turns between finds
        gaps = []
        for rt in by_run_turns.values():
            fturns = sorted(e["turn"] for e in acq if key(e) in {key(rt[0])} if rt)
        allf = defaultdict(list)
        for e in acq:
            allf[key(e)].append(e["turn"])
        for k, ts in allf.items():
            ts.sort()
            gaps += [b - a for a, b in zip(ts, ts[1:])]
        L.append(f"   turns between finds (median): {_med(gaps):.0f}")
        # carried at end
        carried = [t[kind if kind != "water" else "water"] for t in turns]
        L.append(f"   carried (median across all turns): {_med(carried):.0f}")

    # hunger/thirst band share + transitions
    hb = Counter(t["hunger_band"] for t in turns)
    hb_tot = sum(hb.values()) or 1
    L.append(f"\n   hunger band turn-share: "
             + "  ".join(f"{b} {100*hb[b]//hb_tot}%" for b in ("fed", "hungry", "starving")))
    st = Counter((e["frm"], e["to"]) for e in trans if e["axis"] == "hunger")
    L.append("   hunger transitions: "
             + ", ".join(f"{a}→{b} ×{n}" for (a, b), n in st.most_common()))
    warns = [e for e in res if e["op"] == "warned"]
    dmg = [e for e in res if e["op"] == "damage"]
    L.append(f"   'GETTING HUNGRY/THIRSTY' warnings: {len(warns)}   "
             f"'wearing you down' (HP damage) turns: {len(dmg)}")

    # "available but not consumed" — turns spent starving with food in the pack
    starv_with_food = sum(1 for t in turns
                          if t["hunger_band"] == "starving" and t["food"] > 0)
    starv_no_food = sum(1 for t in turns
                        if t["hunger_band"] == "starving" and t["food"] == 0)
    L.append(f"\n   STARVING with food in the pack:  {starv_with_food} turns   "
             f"(the bug: food available, not eaten in time)")
    L.append(f"   STARVING with an empty pack:     {starv_no_food} turns   "
             f"(the bug: food never acquired / economy too tight)")

    # ---------- fatigue economy ----------
    L.append("\n FATIGUE")
    fb = Counter(t["fatigue_band"] for t in turns)
    fb_tot = sum(fb.values()) or 1
    L.append("   band turn-share: "
             + "  ".join(f"{b} {100*fb[b]//fb_tot}%"
                         for b in ("rested", "fatigued", "exhausted")))
    # gained per turn (positive deltas between consecutive turns, same run)
    gains = []
    for rt in by_run_turns.values():
        for a, b in zip(rt, rt[1:]):
            d = b["fatigue"] - a["fatigue"]
            if d > 0:
                gains.append(d)
    rests = [e for e in res if e["kind"] == "fatigue" and e["op"] == "rest"]
    blds = [e for e in res if e["kind"] == "fatigue" and e["op"] == "building_recover"]
    L.append(f"   gained/turn (median of positive moves): {_med(gains):.1f}")
    L.append(f"   explicit rests: {len(rests)}   (median recovered {_med(e['qty'] for e in rests):.0f})"
             if rests else "   explicit rests: 0  (the policy / a naive player never rests)")
    L.append(f"   building fatigue-recovery events: {len(blds)}")
    ft = Counter((e["frm"], e["to"]) for e in trans if e["axis"] == "fatigue")
    L.append("   transitions: " + ", ".join(f"{a}→{b} ×{n}" for (a, b), n in ft.most_common()))
    recov_up = sum(n for (a, b), n in ft.items()
                   if ("exhausted", "fatigued") == (a, b) or ("fatigued", "rested") == (a, b))
    decl = sum(n for (a, b), n in ft.items()
               if ("rested", "fatigued") == (a, b) or ("fatigued", "exhausted") == (a, b))
    L.append(f"   recovery transitions {recov_up}  vs  decline transitions {decl}  "
             + ("-> recovery keeps up" if recov_up >= decl else "-> recovery LOSES to decay"))

    # ---------- before the wall ----------
    L.append("\n BEFORE THE FLIP (state on the turn just before a bad transition)")
    for axis, to in (("hunger", "starving"), ("fatigue", "exhausted")):
        pre = []
        for e in trans:
            if e["axis"] == axis and e["to"] == to:
                rt = by_run_turns.get(key(e), [])
                cand = [t for t in rt if t["turn"] == e["turn_from"]]
                if cand:
                    pre.append(cand[0])
        if pre:
            if axis == "hunger":
                L.append(f"   -> starving: median food carried {_med(t['food'] for t in pre):.0f}, "
                         f"terrain {Counter(t['terrain'] for t in pre).most_common(1)[0][0]}")
            else:
                L.append(f"   -> exhausted: median fatigue {_med(t['fatigue'] for t in pre):.0f}, "
                         f"terrain {Counter(t['terrain'] for t in pre).most_common(2)}")

    # ---------- policy behaviour ----------
    L.append("\n POLICY BEHAVIOUR")
    hungry_turns = [t for t in turns if t["hunger_band"] in ("hungry", "starving")]
    acts = Counter(t["action"] for t in hungry_turns)
    ht = len(hungry_turns) or 1
    L.append(f"   when hungry/starving ({len(hungry_turns)} turns): "
             f"ate {100*acts.get('eat', 0)//ht}%  searched {100*acts.get('search', 0)//ht}%  "
             f"moved {100*sum(acts.get(d, 0) for d in 'nsew')//ht}%")
    exh_turns = [t for t in turns if t["fatigue_band"] == "exhausted"]
    ea = Counter(t["action"] for t in exh_turns)
    et = len(exh_turns) or 1
    L.append(f"   when exhausted ({len(exh_turns)} turns): "
             f"rested {100*ea.get('rest', 0)//et}%  "
             f"moved {100*sum(ea.get(d, 0) for d in 'nsew')//et}%  "
             f"other {100*(et - ea.get('rest', 0) - sum(ea.get(d, 0) for d in 'nsew'))//et}%")

    # ---------- terrain cost ----------
    L.append("\n TERRAIN COST")
    tturns = Counter(t["terrain"] for t in turns)
    tgain = defaultdict(list)
    for rt in by_run_turns.values():
        for a, b in zip(rt, rt[1:]):
            d = b["fatigue"] - a["fatigue"]
            if d > 0:
                tgain[a["terrain"]].append(d)
    tfood = Counter()
    # attribute a find to the terrain of the same turn
    tmap = {(e["campaign"], e["run"], e["turn"]): e["terrain"] for e in turns}
    for e in res:
        if e["op"] == "found" and e["kind"] in ("food", "water"):
            tfood[tmap.get((e["campaign"], e["run"], e["turn"]), "?")] += 1
    L.append(f"   {'terrain':<12} {'turns':>6} {'fatigue/turn':>13} {'food+water finds':>17}")
    for t, n in tturns.most_common():
        L.append(f"   {t:<12} {n:>6} {_med(tgain.get(t, [])):>13.1f} {tfood.get(t, 0):>17}")

    L.append("=" * 66)
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--campaigns", type=int, default=15)
    ap.add_argument("--policy", default="survival",
                    choices=["random", "survival", "explorer", "resource", "objective"])
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--jsonl", default=None)
    ap.add_argument("--md", default=None)
    args = ap.parse_args()

    rec = Recorder(args.jsonl)
    try:
        for c in range(args.campaigns):
            rec.campaign = c + 1
            run_campaign(rec, args.policy, args.seed + c * 1000)
            print(f"  campaign {c+1}/{args.campaigns} ({len(rec.events)} events)")
    finally:
        rec.close()

    rpt = resource_report(rec.events)
    print("\n" + rpt)
    if args.md:
        with open(args.md, "w") as f:
            f.write(f"# Resource / attrition — {args.policy} policy, "
                    f"{args.campaigns} campaigns\n\n"
                    "`tools/resource_autoplay.py`. See docs/TELEMETRY.md for the "
                    "event stream this is derived from.\n\n```\n" + rpt + "\n```\n")
        print(f"\n wrote {args.md}")


if __name__ == "__main__":
    main()
