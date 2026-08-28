#!/usr/bin/env python3
# ============================================================
# Apocrysis - v4 vertical-slice playtest harness
# File: tools/slice_playtest.py
#
# Drives the "Dam Service Road" slice headlessly with scripted
# command sequences and captures only the game's narrative output
# (not the per-turn stats panel). Used to run the three-situation
# test from docs/ESCAPE_WORLD_DESIGN_ASSESSMENT.md ("Vertical slice
# prototype") - the go/no-go gate for building the procedural
# generator.
#
#   python3 tools/slice_playtest.py            # run all scenarios
#   python3 tools/slice_playtest.py solve      # one named scenario
# ============================================================

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.game import Apocrysis  # noqa: E402


class ScriptedIO:
    """Feeds a fixed command list; records everything say()n."""
    renders_natively = True  # suppress run_game_loop's ASCII panel

    def __init__(self, commands):
        self._commands = list(commands)
        self.log = []

    def say(self, *args, **kwargs):
        text = " ".join(str(a) for a in args) if args else ""
        self.log.append(text)

    def ask(self, prompt=""):
        if self._commands:
            return self._commands.pop(0)
        return "q"

    def ask_yes_no(self, prompt):
        return False  # never save, never pick a fight


def run(commands):
    io = ScriptedIO(commands)
    game = Apocrysis("Surveyor", slice_mode=True, io=io)
    try:
        game.run_game_loop()
    except (StopIteration, EOFError):
        pass
    return game, io


def show(title, commands):
    print("\n" + "=" * 68)
    print(title)
    print("=" * 68)
    game, io = run(commands)
    for line in io.log:
        if line.strip():
            print("  " + line)
    print("-" * 68)
    print(f"  facts known:      {sorted(game.knowledge.facts_known())}")
    print(f"  evidence found:   {sorted(game.knowledge.found)}")
    print(f"  hypothesis:       {game.knowledge.hypothesis_state()}")
    print(f"  gate open:        {game.slice_gate_open}")
    print(f"  escaped / won:    {game.slice_escaped} / {getattr(game, 'won', False)}")
    return game


# ---- command sequences -------------------------------------
# BFS-derived paths (spawn (9,17); river band y=5 x7..11; ridge boxes
# the service-road corridor so the gate at (14,12) is the sole way to
# (16,12)).
TO_FLOODED = list("nnnnnnnnnnn")               # (9,17) -> (9,6) flooded_road
FLOODED_TO_DAM = list("eeennnwww")             # (9,6) -> (9,3) dam
DAM_TO_CONTROL = list("ee")                    # (9,3) -> (11,3) control_room
CONTROL_TO_SHED = list("swwwwwssss")           # (11,3) -> (6,8) utility_shed
SHED_TO_GATE_W = list("sssseeeeeee")           # (6,8) -> (13,12), just west of the gate
FARMHOUSE = list("nnwwwwww")                   # (9,17) -> (3,15) farmhouse

SOLVE = (
    TO_FLOODED + ["remember"]                  # E1b -> F1; D1 surfaces
    + FLOODED_TO_DAM + ["search"]              # E1 (observe); nothing to search
    + DAM_TO_CONTROL + ["search", "i"]         # E5 -> valve key in inventory
    + CONTROL_TO_SHED + ["search", "journal"]  # E2, E4; review journal
    + SHED_TO_GATE_W + ["e"]                   # bump locked gate -> E3
    + ["inspect gate", "inspect key", "remember"]
    + ["og"]                                   # open gate (adjacent, have key)
    + ["e", "e", "e"]                          # through -> (16,12) beyond, E6
    + ["remember", "escape"]
)

# Situation 1: a required evidence piece not yet found. Player never
# searches the control room, so never gets the key. They reach the
# gate, know it's locked, and check what the game tells them.
S1_MISSING_EVIDENCE = (
    TO_FLOODED + FLOODED_TO_DAM + DAM_TO_CONTROL
    + CONTROL_TO_SHED + ["search"]            # E2/E4: key is "in the control room"
    + SHED_TO_GATE_W + ["e"]                  # bump gate -> E3
    + ["inspect key", "inspect gate", "remember", "og", "journal"]
)

# Situation 2: the irrelevant thread, partially chased, then recovered.
S2_IRRELEVANT = (
    FARMHOUSE + ["search", "journal", "remember"]   # diary; journal still empty
    + list("nnnnnnnnnnnn")                          # leave, head back north
    + ["remember"]
)

# Situation 3: enough evidence to form H1 (suspected) but the player
# hasn't recognised it - what do remember / inspect / journal expose?
S3_UNRECOGNISED = (
    TO_FLOODED + FLOODED_TO_DAM + DAM_TO_CONTROL
    + CONTROL_TO_SHED + ["search"]           # F1, F2, F3, F4 all established
    + SHED_TO_GATE_W + ["e"]                 # E3
    + ["remember", "inspect way out", "journal"]
)

SCENARIOS = {
    "solve": ("Full solve path", SOLVE),
    "s1": ("Situation 1 - a required evidence piece not yet found", S1_MISSING_EVIDENCE),
    "s2": ("Situation 2 - the irrelevant diary/graffiti thread", S2_IRRELEVANT),
    "s3": ("Situation 3 - hypothesis formable but unrecognised", S3_UNRECOGNISED),
}


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else None
    if which and which in SCENARIOS:
        title, cmds = SCENARIOS[which]
        show(title, cmds)
    else:
        for _key, (title, cmds) in SCENARIOS.items():
            show(title, cmds)
