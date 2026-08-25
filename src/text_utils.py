# Auto-extracted from the original monolithic apocrysis.py during
# the src/ restructuring - see README.md for the project layout.

import re


# Real bug found live: the map's player marker ('P') got wrapped in
# health-based ANSI color codes (BOLD + GREEN/YELLOW/RED + RESET,
# see _render_map_lines() below) - invisible on screen, but `len()`
# still counts those escape-code bytes as characters. The two-column
# layout's `left_line.ljust(left_col_width)` uses raw `len()` to
# decide how much padding to add, so the ONE row containing the
# player was treated as ~13 characters "longer" than it visually is,
# and got that much LESS padding - the '|' separator (and everything
# in the right-hand panel) visibly shifted left on exactly that row,
# and only that row, matching what was reported live ("Food is out of
# place" / "What would you like to do was below No weapons in
# inventory" - whichever right-hand line happened to land on the
# player's map row that turn). `_visible_len`/`_display_ljust` pad
# based on the string with ANSI codes stripped out, so a colored cell
# no longer throws off alignment.
_ANSI_ESCAPE_RE = re.compile(r'\x1b\[[0-9;]*m')


def _visible_len(text):
    return len(_ANSI_ESCAPE_RE.sub('', text))


def _display_ljust(text, width):
    padding = width - _visible_len(text)
    return text + (' ' * padding if padding > 0 else '')
