#!/usr/bin/env python3
# ============================================================
# playtest_three.py  --  the three-mystery blind comprehension test
# (phase gate 69d78812 / 9ae794b9)
#
# Forces build_mystery() to use ONE named mechanism for this run so a
# human can play one generated mystery of each story family, blind,
# and fill in docs/PLAYER_UNDERSTANDING.md.  Dev harness only - it
# monkeypatches src.escape.choose_mechanism and touches nothing in
# the game itself.
#
#   python3 tools/playtest_three.py A     # spatial        (mountain_pass)
#   python3 tools/playtest_three.py B     # infrastructural (power_station)
#   python3 tools/playtest_three.py C     # experimental    (dam_valves)
#
#   python3 tools/playtest_three.py --list
#   python3 tools/playtest_three.py rail_tunnel      # any mechanism by name
#
# --log is ON by default (writes the session transcript); pass
# --no-log to suppress.  The three blind runs for the phase gate are
# A, B, C in some shuffled order the player shouldn't know.
# ============================================================

import argparse
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import escape

# The blind test wants three genuinely different grammars, one per
# family.  These are the three that are built end to end.
SLOTS = {
    "A": "mountain_pass",   # spatial        - "where is the route?"
    "B": "power_station",   # infrastructural - "what powers this?"
    "C": "dam_valves",      # experimental    - "which control is it?"
}


def _force(mechanism):
    if mechanism not in escape.MECHANISMS:
        sys.exit(f"unknown mechanism {mechanism!r}; --list to see them")

    def choose_mechanism(rng, already_used, last_family=None):
        return mechanism

    escape.choose_mechanism = choose_mechanism
    # build_mystery reads the module global by name, so the patch above
    # is enough; clear the class-level bookkeeping too for tidiness.
    try:
        from src.game import Apocrysis
        Apocrysis._used_mechanisms = []
        Apocrysis._last_family = None
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", nargs="?", help="A|B|C, a mechanism name, or 'shuffle'")
    ap.add_argument("--list", action="store_true", help="list mechanisms + families and exit")
    ap.add_argument("--no-log", action="store_true", help="don't write a session transcript")
    args = ap.parse_args()

    if args.list or not args.target:
        for name, spec in escape.MECHANISMS.items():
            slot = next((k for k, v in SLOTS.items() if v == name), " ")
            print(f"  [{slot}] {name:<16} {spec.get('family')}")
        if not args.target:
            print("\npass A, B, or C  (or a mechanism name, or 'shuffle')")
        return

    if args.target == "shuffle":
        slot = random.choice(list(SLOTS))
        mechanism = SLOTS[slot]
        # deliberately DON'T print which slot - that's the point
        print("Starting a blind run. Play it, then fill in the answer sheet.\n")
    else:
        mechanism = SLOTS.get(args.target.upper(), args.target)
        fam = escape.MECHANISMS.get(mechanism, {}).get("family", "?")
        print(f"Forcing mechanism: {mechanism}  (family: {fam})\n")

    _force(mechanism)

    from src.cli import main_tui
    main_tui(start_log=not args.no_log)


if __name__ == "__main__":
    main()
