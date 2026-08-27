#!/usr/bin/env bash
# Better replacement for a flat `python3 balance_autoplay.py --game 2000`.
#
# That command had two real problems:
#   1. `--game` isn't a real flag - it only worked because argparse
#      silently accepts unambiguous prefixes of `--games`. Harmless
#      today, but fragile (breaks the moment a second --game* flag is
#      added) and not obvious to a reader.
#   2. Every one of the 2000 games ran at the SAME level=1,
#      expeditions_completed=0 tier (the harness's defaults). Level
#      almost never climbs past 2 in a ~9-turn game, so no amount of
#      games at that one tier will ever give you a real sample at
#      level 3+ - that's why the report's level-3 dealt:taken ratio
#      was 2.17x on just 8 hits. You need games that actually START
#      higher to sample higher levels/expeditions at all.
#
# This script instead runs:
#   - a large, SEEDED baseline at the default tier (reproducible -
#     the flat command had no --seed, so re-running it gives different
#     numbers every time)
#   - a level/expedition-matched sweep across tiers, so higher levels
#     get real sample sizes instead of leftover level-ups from a
#     level-1 start
#   - a --campaign run, which is the only mode that actually answers
#     "does winning advance expeditions_completed for real" (see the
#     open todo about that) - a flat single-game batch can't answer it,
#     since play_one_game() starts every game fresh at whatever
#     --expeditions-completed you passed.
#
# Usage: tools/balance_sweep.sh [output_dir]   (default: balance_sweep_out)

set -euo pipefail
cd "$(dirname "$0")/.."

OUT="${1:-balance_sweep_out}"
mkdir -p "$OUT"
SEED=1
GAMES_PER_TIER=1000

echo "== baseline (level 1, expeditions_completed 0, seeded, reproducible) =="
python3 tools/balance_autoplay.py --games "$GAMES_PER_TIER" --seed "$SEED" \
    | tee "$OUT/baseline.txt"

# Level/expeditions_completed are independent axes in this engine (map/
# player/campaign-level split - see the harness's own docstring), but a
# sweep that raises them TOGETHER approximates "a character who has
# actually played this many expeditions", which is what you want when
# the question is "is level N vs its own tier's difficulty balanced" -
# as opposed to the flat run's implicit "level 1 forever" question.
echo
echo "== level/expedition-matched sweep =="
for tier in "1 0" "3 1" "5 3" "8 5" "12 8"; do
    set -- $tier
    level=$1
    exp=$2
    echo "--- level $level, expeditions_completed $exp ---"
    python3 tools/balance_autoplay.py --games "$GAMES_PER_TIER" \
        --level "$level" --expeditions-completed "$exp" --seed "$SEED" \
        | tee "$OUT/tier_L${level}_E${exp}.txt"
done

# Campaign mode: one persisting character playing consecutive
# expeditions for real, using the game's own save/load profile - the
# only mode that can confirm or refute "winning advances
# expeditions_completed" and "does a campaign actually reach the end".
echo
echo "== campaign mode (real progression, persisting character) =="
python3 tools/balance_autoplay.py --campaign --campaign-runs 100 --seed "$SEED" \
    | tee "$OUT/campaign.txt"

echo
echo "All reports written to $OUT/"
