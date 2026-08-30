#!/usr/bin/env python3
"""Perception-bounded autoplay — the measuring instrument.

Runs the real game through `PerceivedBotIO`: the bot decides only from
what a player can see (HUD, fogged map grid, the say() stream, the
ESCAPE panel). See docs/AUTOPLAY_STRATEGY.md.

    python3 tools/tui_autoplay.py --policy explorer --chapter 3 --games 50
    python3 tools/tui_autoplay.py --policy survival --games 100 --json out/s.jsonl
    python3 tools/tui_autoplay.py --policy random --seed 1 --games 1 --verbose

Instrument phase: policies are `random` / `survival` / `explorer` only.
The `objective` / `humanlike` policies and the cardinal-vs-landmark
A/B come after the spatial-language design pass — this tool exists to
measure that redesign, not to pre-empt it.
"""
import argparse
import json
import os
import statistics
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.autoplay.runner import run_one


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--policy", default="explorer",
                    choices=["random", "survival", "explorer"])
    ap.add_argument("--chapter", type=int, default=None,
                    help="1-6: drop in at the start of that chapter "
                         "(synthetic state, like --dev). Omit for a "
                         "fresh expedition-1 start.")
    ap.add_argument("--games", type=int, default=20)
    ap.add_argument("--seed", type=int, default=1,
                    help="base seed; game N uses seed+N")
    ap.add_argument("--max-turns", type=int, default=600)
    ap.add_argument("--nav-phrasing", default="cardinal",
                    help="label only — records which spatial-language "
                         "build the game shipped this run (for the A/B "
                         "once the redesign exists)")
    ap.add_argument("--json", default=None,
                    help="append one RunRecord per line to this file")
    ap.add_argument("--verbose", action="store_true",
                    help="print each game's record as it finishes")
    args = ap.parse_args()

    records = []
    jf = open(args.json, "a") if args.json else None
    try:
        for i in range(args.games):
            seed = None if args.seed is None else args.seed + i
            rec = run_one(seed, args.chapter, args.policy,
                          max_turns=args.max_turns,
                          nav_phrasing=args.nav_phrasing)
            records.append(rec)
            if jf:
                jf.write(rec.to_json() + "\n")
                jf.flush()
            if args.verbose:
                print(f"[{i+1}/{args.games}] seed={seed} {rec.outcome:7s} "
                      f"turns={rec.turns:3d} obj_reached={rec.objective_reached} "
                      f"dir_seen={rec.direction_text_seen} "
                      f"dir_ok={rec.direction_operational} "
                      f"dest_named={rec.objective_destination_named} "
                      f"marker={rec.map_marker_present} "
                      f"facts={rec.facts_found}/{rec.facts_available}")
    finally:
        if jf:
            jf.close()

    _summary(records, args)


def _pct(xs):
    xs = list(xs)
    return 100.0 * sum(bool(x) for x in xs) / len(xs) if xs else 0.0


def _summary(records, args):
    n = len(records)
    if not n:
        return
    outcomes = Counter(r.outcome for r in records)
    turns = [r.turns for r in records]
    reached = [r for r in records if r.objective_reached]
    tto = [r.turns_to_objective for r in reached if r.turns_to_objective]

    print("\n" + "=" * 60)
    print(f" perceived autoplay — policy={args.policy} "
          f"chapter={args.chapter} games={n} phrasing={args.nav_phrasing}")
    print("=" * 60)
    print(f" outcomes            : "
          + "  ".join(f"{k} {v}" for k, v in outcomes.most_common()))
    print(f" turns               : median {statistics.median(turns):.0f}  "
          f"min {min(turns)}  max {max(turns)}")
    print()
    print(" — comprehension: received  →  actionable —")
    print(f"   objective told      : {_pct(r.objective_text_seen for r in records):5.1f}%"
          f"   → destination named : {_pct(r.objective_destination_named for r in records):5.1f}%")
    print(f"   direction shown     : {_pct(r.direction_text_seen for r in records):5.1f}%"
          f"   → operational       : {_pct(r.direction_operational for r in records):5.1f}%")
    print(f"   landmark named      : {_pct(r.landmark_named for r in records):5.1f}%"
          f"   → landmark visible  : {_pct(r.landmark_visible for r in records):5.1f}%")
    print(f"   map marker present  : {_pct(r.map_marker_present for r in records):5.1f}%")
    print()
    print(f" objective reached    : {_pct(r.objective_reached for r in records):5.1f}%"
          + (f"   (median {statistics.median(tto):.0f} turns to it)" if tto else ""))
    print(f" mystery solved       : {_pct(r.mystery_solved for r in records):5.1f}%")
    print(f" hypothesis formed    : {_pct(r.hypothesis_formed for r in records):5.1f}%"
          f"   corrections seen (total): {sum(r.hypothesis_corrections_seen for r in records)}")
    _ff = [r.facts_found for r in records]
    _fa = [r.facts_available for r in records if r.facts_available]
    if _fa:
        print(f" facts found          : median {statistics.median(_ff):.1f}"
              f" of {statistics.median(_fa):.0f} available")
    print()
    print(f" revisit ratio        : median {statistics.median(r.revisit_ratio for r in records):.2f}")
    print(f" turns pursuing/wander : "
          f"{sum(r.turns_pursuing for r in records)} / {sum(r.turns_wandering for r in records)}")
    print(f" fatigue-pinned turns  : median {statistics.median(r.fatigue_pinned_turns for r in records):.0f}"
          f"   (of median {statistics.median(turns):.0f})")
    print(f" zombie encounters    : median {statistics.median(r.zombie_encounters for r in records):.0f}")
    print("=" * 60)


if __name__ == "__main__":
    main()
