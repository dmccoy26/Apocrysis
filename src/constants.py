# Auto-extracted from the original monolithic apocrysis.py during
# the src/ restructuring - see README.md for the project layout.

# ANSI Color Codes for Terminal Emphasis
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"
CYAN = "\033[96m"

# Real bug found live: wilderness terrain ('forest'/'building'/'water'/
# 'plain', set on every non-town tile in generate_map()) only ever
# showed up as flavor text AFTER stepping onto a tile
# ("You move through dense forest.") - print_map() never rendered it,
# so every wilderness tile looked identical (.) regardless of
# terrain. This maps each real terrain type to a map symbol so it's
# visible before you walk into it. No 'mountain'/'river' terrain
# exists in generate_map()'s terrain_types - only what's actually
# generated is mapped here, rather than inventing symbols for terrain
# that was never implemented.
TERRAIN_SYMBOLS = {
    'forest': 'f',
    'water': '~',
    'building': 'b',
    'plain': '.',
}

TERRAIN_LEGEND = (
    "  f = forest   ~ = water   b = building   . = plain\n"
    "  T/H/R/S/B = town tiles (Town center/House/Road/Shop/Building)\n"
    "  P = you   Z = zombie (only shown once you've been there)"
)
