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

import sys

from src.cli import main, main_tui, run_tests


if __name__ == "__main__":
    if "--test" in sys.argv:
        run_tests()
    elif "--classic" in sys.argv:
        main()
    else:
        main_tui()
