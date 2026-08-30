#!/usr/bin/env python3
"""Fatigue investigation.

The re-run (RESOURCE_MODEL_RESULTS.md) closed food as a nav artifact
and left fatigue as the one survival lever: exhausted ~40% of turns,
29% of deaths, recovery loses to decay, and the policy never rests.
Before touching `rest()` we separate:

  A. is the fatigue model mathematically unsustainable?
  B. does a naive player just not rest?
  C. is resting even economically worth it (it costs a turn of
     hunger/thirst + objective time)?
  D. does the player get the information to make that call?

Part 1 - analytical: the recovery-vs-decay math across Wisdom.
Part 2 - simulation: `objective` (never rests) vs `objective_rest`
         (rests when exhausted) - exhausted turn-share, rest count,
         the hunger cost of resting, cause of death, wins, length.

    python3 tools/fatigue_autoplay.py --campaigns 10
"""
import argparse
import os
import statistics
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.telemetry import Recorder, run_campaign


# ---- Part 1: the fatigue arithmetic (from src/mixins/world_mixin.py) ----
def _fatigue_math():
    L = ["=" * 66, " FATIGUE ARITHMETIC (per src/mixins/world_mixin.py)", "=" * 66]
    L.append("   plain / forest move        + 5   fatigue")
    L.append("   water / swamp move          +15   (move +5, terrain +10)")
    L.append("   building ENTRY             - (wisdom//4 + 5)   [free, no turn]")
    L.append("   `rest` command             - max(5, wisdom//2)   (x2 inside a building)")
    L.append("                              + costs a turn: -2 hunger, -2 thirst,")
    L.append("                                + the objective time")
    L.append("")
    L.append(f"   {'wisdom':>6}  {'move gain':>10}  {'building entry':>15}  "
             f"{'rest (open)':>12}  {'rest (bldg)':>12}  {'net rest vs 1 move':>18}")
    for w in (10, 12, 15, 20):
        move = 5
        entry = -(w // 4 + 5)
        rest_o = -max(5, w // 2)
        rest_b = 2 * rest_o
        net = rest_o + move   # fatigue after resting then taking one move
        L.append(f"   {w:>6}  {move:>+10}  {entry:>+15}  {rest_o:>+12}  {rest_b:>+12}  "
                 f"{net:>+18}")
    L.append("")
    L.append("   READ: at wisdom 10 a rest gives back exactly what one move takes")
    L.append("   (-5 vs +5) and costs a turn of decay - so on the open map rest")
    L.append("   is NET-ZERO fatigue for a positive hunger cost. The only")
    L.append("   free net-positive recovery is walking into a building (-7).")
    L.append("   That is why `objective` (sweeps buildings) got exhausted 65% ->")
    L.append("   40% WITHOUT ever resting.")
    return "\n".join(L)


# ---- Part 2: the sim comparison ----
def _sim_report(events, label):
    turns = [e for e in events if e["event"] == "turn"]
    res = [e for e in events if e["event"] == "resource"]
    trans = [e for e in events if e["event"] == "state_transition"]
    combats = [e for e in events if e["event"] == "combat"]
    ends = [e for e in events if e["event"] == "expedition_end"]
    key = lambda e: (e["campaign"], e["run"])
    by_run = defaultdict(list)
    for e in turns:
        by_run[key(e)].append(e)
    for v in by_run.values():
        v.sort(key=lambda e: e["turn"])

    L = [f"\n --- {label} ---"]
    oc = Counter(e["outcome"] for e in ends)
    L.append("   outcomes: " + "  ".join(f"{k} {v}" for k, v in oc.most_common()))
    tpe = [len(v) for v in by_run.values()]
    L.append(f"   turns/expedition (median): {statistics.median(tpe):.0f}" if tpe else "")

    fb = Counter(e["fatigue_band"] for e in turns)
    ftot = sum(fb.values()) or 1
    L.append("   fatigue band: "
             + "  ".join(f"{b} {100*fb[b]//ftot}%"
                         for b in ("rested", "fatigued", "exhausted")))
    rests = [e for e in res if e["kind"] == "fatigue" and e["op"] == "rest"]
    blds = [e for e in res if e["kind"] == "fatigue" and e["op"] == "building_recover"]
    L.append(f"   explicit rests: {len(rests)}   building-recover events: {len(blds)}")
    ft = Counter((e["frm"], e["to"]) for e in trans if e["axis"] == "fatigue")
    up = sum(n for (a, b), n in ft.items() if (a, b) in
             (("exhausted", "fatigued"), ("fatigued", "rested")))
    down = sum(n for (a, b), n in ft.items() if (a, b) in
               (("rested", "fatigued"), ("fatigued", "exhausted")))
    L.append(f"   fatigue transitions  recovery {up}  vs  decline {down}")

    # cause of death
    died = [e for e in ends if e["outcome"] == "died"]
    causes = Counter()
    for e in died:
        rt = by_run.get(key(e), [])[-3:]
        cd = any(c["outcome"] == "death" for c in combats if key(c) == key(e))
        st = any(t["hunger_band"] == "starving" for t in rt)
        ex = any(t["fatigue_band"] == "exhausted" for t in rt)
        causes["combat" if cd else "starv+exh" if (st and ex) else "starvation"
               if st else "exhaustion" if ex else "other"] += 1
    if died:
        L.append("   deaths: " + "  ".join(f"{k} {v}" for k, v in causes.most_common()))

    # the hunger cost of resting: hunger delta across the turns where a
    # rest fired
    rest_turns = {(e["campaign"], e["run"], e["turn"]) for e in rests}
    hunger_cost = []
    for run in by_run.values():
        for a, b in zip(run, run[1:]):
            if (a["campaign"], a["run"], a["turn"]) in rest_turns:
                hunger_cost.append(a["hunger"] - b["hunger"])
    if hunger_cost:
        L.append(f"   hunger lost per rest (median): "
                 f"{statistics.median(hunger_cost):.0f}")

    # combat while exhausted vs not
    exh_c = [c for c in combats if c.get("fatigue_band") == "exhausted"]
    ok_c = [c for c in combats if c.get("fatigue_band") != "exhausted"]
    def _loss(cs):
        v = [c["dmg_taken"] for c in cs if c["decision"] == "fight" or c["forced_fight"]]
        return statistics.mean(v) if v else 0
    L.append(f"   combat HP lost: exhausted {_loss(exh_c):.0f}  "
             f"vs rested/fatigued {_loss(ok_c):.0f}   "
             f"(n {len(exh_c)} / {len(ok_c)})")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--campaigns", type=int, default=8)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--md", default=None)
    args = ap.parse_args()

    parts = [_fatigue_math()]
    parts.append("\n" + "=" * 66 + "\n SIM: does resting help?  (objective vs objective_rest)\n"
                 + "=" * 66)
    for pol in ("objective", "objective_rest"):
        rec = Recorder()
        for c in range(args.campaigns):
            rec.campaign = c + 1
            run_campaign(rec, pol, args.seed + c * 1000)
        parts.append(_sim_report(rec.events, pol))
        print(f"  {pol}: {len(rec.events)} events")

    parts.append("\n" + "=" * 66)
    parts.append(" Q4 (surfacing): there is NO fatigue equivalent of game._hp_warnings")
    parts.append("   - fatigue is never announced as a standing condition. A naive")
    parts.append("   player (and the `objective` policy) has no prompt to rest.")
    parts.append("=" * 66)

    out = "\n".join(parts)
    print("\n" + out)
    if args.md:
        with open(args.md, "w") as f:
            f.write("# Fatigue investigation\n\n`tools/fatigue_autoplay.py`.\n\n```\n"
                    + out + "\n```\n")
        print(f"\n wrote {args.md}")


if __name__ == "__main__":
    main()
