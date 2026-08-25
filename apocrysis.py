# ============================================================
# Apocrysis
# File: apocrysis.py
#
# Thin entry point - the game itself lives under src/. See
# README.md for the project layout.
# ============================================================

import sys

from src.cli import main, run_tests


if __name__ == "__main__":
    if "--test" in sys.argv:
        run_tests()
    else:
        main()
