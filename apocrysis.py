# ============================================================
# Apocrysis
# File: apocrysis.py
#
# Thin entry point - the game itself lives under src/. See
# README.md for the project layout.
#
# v3 SPRINT step 6: the textual TUI is the default interactive
# experience now - `--classic` keeps the original print-loop
# (src/cli.py's main(), via io_console.py's ConsoleIO) as an explicit
# fallback. `--test` is unaffected either way - it never touches I/O
# beyond bare print(), and run_tests() always uses the classic path.
# ============================================================

import argparse

from src.cli import main, main_tui, run_tests


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--test", action="store_true", help="Run tests")
    group.add_argument("--classic", action="store_true", help="Run classic print-loop mode")
    parser.add_argument("--log", action="store_true",
                        help="(deprecated - logging is on by default now; kept so old commands still work)")
    parser.add_argument("--no-log", dest="no_log", action="store_true",
                        help="Don't auto-write a play log for this session (still toggleable in game with `log`)")
    parser.add_argument("--mapgen", choices=("v1", "v2"), default="v1",
                        help="Map generator: v1 (default, rectangular) or v2 "
                             "(Phase C.3 experiment - irregular valley)")
    args = parser.parse_args()

    from src.game import Apocrysis
    Apocrysis._default_mapgen = args.mapgen

    # Logging is on by default for interactive play (feel-tests /
    # playtests need the transcript); --no-log opts out.
    start_log = not args.no_log

    if args.test:
        run_tests()
    elif args.classic:
        main(start_log=start_log)
    else:
        main_tui(start_log=start_log)