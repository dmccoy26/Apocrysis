"""The honest perception boundary.

`Perception` holds exactly what a player can see on their screen this
turn. A policy is handed a `Perception` and decides from it alone — it
never touches `player.map` (unfogged), `mystery.sites`,
`mystery.escape_tile`, the RNG, or zombie internal stats.

`build_perception(player, log_lines)` assembles one from:
  - public HUD attributes (health/hunger/thirst/… — the same numbers
    the TUI stat panel formats)
  - `player.perceived_map_grid()` (the fogged glyph grid — engine side)
  - `log_lines`: the ANSI-stripped say() output since the last command
  - the ESCAPE panel + investigation strip (via `src.tui`), markup
    stripped

Nothing here reaches for a coordinate the player hasn't been shown. If
the game says "south-west" with no reference frame, that string is all
the `Perception` carries — see `spatial_relation` / `reference_frame`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_MARKUP = re.compile(r"\[/?[a-zA-Z#][a-zA-Z0-9#_ ]*\]")

# announce_event() glyph -> semantic class (docs/ATTENTION_SYSTEM_SPEC).
_FLARE_GLYPHS = {
    "‼": "danger",     # ‼
    "◈": "story",      # ◈
    "◆": "objective",  # ◆
    "⚠": "warning",    # ⚠
    "✦": "discovery",  # ✦
    "✓": "success",    # ✓
    "•": "info",       # •
}

_BEARINGS = ("north-east", "north-west", "south-east", "south-west",
             "north", "south", "east", "west")

_CARDINAL_KEY = {
    "north": "n", "south": "s", "east": "e", "west": "w",
}


def strip(s: str) -> str:
    """Drop ANSI colour and Rich markup — leave the text a player reads."""
    return _MARKUP.sub("", _ANSI.sub("", s)).rstrip()


@dataclass
class Perception:
    """One turn's worth of what the screen shows. Read-only for policies."""

    turn: int
    hud: dict                       # health, max_health, hunger, thirst,
                                    #   fatigue, food, water, medicine, ammo,
                                    #   level, day, phase, biome,
                                    #   equipped_weapon, has_flashlight
    grid: list                      # grid[y][x] plain glyphs (fogged)
    player_xy: tuple                # (x, y) — you are 'P' on the grid
    size: int
    log: list = field(default_factory=list)          # say() lines this turn
    flares: list = field(default_factory=list)        # [(class, text)]
    escape_panel: list = field(default_factory=list)  # plain checklist lines
    investigation: list = field(default_factory=list) # plain WI strip lines
    encounter: dict | None = None    # {name, threat, fight_pct, escape_pct,
                                     #  weapon_verdict} while a combat card
                                     #  is on screen; else None

    # ---- spatial language actually presented (received, not resolved) ----
    spatial_relation: str | None = None   # e.g. "south-west" — a bearing word
    reference_frame: str | None = None    # "arrow-keys" if a n/s/e/w frame is
                                          #   available to map a bearing to a
                                          #   key; None if the game gave none

    # ---- convenience views over the grid (still player-visible only) ----
    def legal_moves(self) -> list:
        """Directions that don't walk into a wall the player can SEE.
        An unseen tile (' ') is assumed walkable — the player would try
        it. Impassable-but-visible ('^' mountain, '=' river) is out."""
        x, y = self.player_xy
        blocked = {"^", "="}
        out = []
        for d, (dx, dy) in (("n", (0, -1)), ("s", (0, 1)),
                            ("e", (1, 0)), ("w", (-1, 0))):
            nx, ny = x + dx, y + dy
            if not (0 <= nx < self.size and 0 <= ny < self.size):
                continue
            if self.grid[ny][nx] in blocked:
                continue
            out.append(d)
        return out

    def glyph_positions(self, glyphs) -> list:
        """Every (x, y) whose visible glyph is in `glyphs` — e.g. the
        mystery-lead markers ('!', '+') or a zombie ('Z'). Used by a
        landmark-following policy; still only reads the rendered grid."""
        want = set(glyphs)
        hits = []
        for y, row in enumerate(self.grid):
            for x, g in enumerate(row):
                if g in want:
                    hits.append((x, y))
        return hits

    def unseen_frontier(self) -> list:
        """Visited-or-visible tiles that border an unseen (' ') tile —
        where an explorer would head to reveal more map."""
        out = []
        for y, row in enumerate(self.grid):
            for x, g in enumerate(row):
                if g == " " or g in {"^", "="}:
                    continue
                for dx, dy in ((0, -1), (0, 1), (1, 0), (-1, 0)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.size and 0 <= ny < self.size \
                            and self.grid[ny][nx] == " ":
                        out.append((x, y))
                        break
        return out


def _parse_flares(lines):
    out = []
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        cls = _FLARE_GLYPHS.get(s[:1])
        if cls:
            out.append((cls, s[1:].strip()))
    return out


def _parse_encounter(lines):
    """The combat card (src/io_console.ask_combat_letter / the TUI
    version). Lines look like:
        ‼ ZOMBIE — ELITE ARMORED ZOMBIE
          Threat:  EXTREME
          With your Steel Katana (20 dmg):   Fight ~0%    Escape ~50%
    """
    blob = "\n".join(lines)
    if "Threat:" not in blob:
        return None
    name = None
    m = re.search(r"ZOMBIE\s+[—-]\s+(.+)", blob)
    if m:
        name = m.group(1).strip().title()
    threat = None
    m = re.search(r"Threat:\s+([A-Z]+)", blob)
    if m:
        threat = m.group(1)
    fight = escape = None
    m = re.search(r"Fight ~(\d+)%", blob)
    if m:
        fight = int(m.group(1))
    m = re.search(r"Escape ~(\d+)%", blob)
    if m:
        escape = int(m.group(1))
    verdict = None
    for key in ("overkill", "poorly suited", "adequate", "well matched",
                "barely enough"):
        if key in blob:
            verdict = key
            break
    return {"name": name, "threat": threat, "fight_pct": fight,
            "escape_pct": escape, "weapon_verdict": verdict}


def _spatial_relation(lines, panel):
    """The bearing word the game most recently put in front of the
    player (story stream or ESCAPE panel), or None. We record the
    STRING; we do not resolve it to a vector."""
    for src in (list(reversed(lines)), list(reversed(panel))):
        for ln in src:
            low = ln.lower()
            for b in _BEARINGS:
                if b in low:
                    return b
    return None


def _escape_panel(player):
    """The ESCAPE checklist + investigation strip, markup stripped.
    Imported from src.tui so it is literally the panel the player sees.
    Empty on a no-mystery map."""
    try:
        from src import tui
    except Exception:
        return [], []
    m = getattr(player, "mystery", None)
    k = getattr(player, "knowledge", None) or getattr(m, "knowledge", None)
    strip_lines = lambda seq: [strip(s) for s in seq if strip(s)]
    panel = []
    wi = []
    try:
        if hasattr(tui, "_investigation_strip"):
            wi = strip_lines(tui._investigation_strip(player) or [])
    except Exception:
        wi = []
    try:
        if m is not None and k is not None:
            panel = strip_lines(tui._objective_steps(player, m, k) or [])
    except Exception:
        panel = []
    return panel, wi


def _reference_frame(player):
    """Does the game currently give the player a way to turn a bearing
    word into a movement key?

    Today: movement is n/s/e/w keys with an on-screen legend
    ("↑ Move north …"), and the map is NOT oriented/labelled and has no
    compass rose. That legend is a *key* mapping, not a spatial
    reference frame for the map — a player still cannot tell which way
    is north on the terrain. So for the map-reading sense that the
    spatial-language work cares about, there is no frame: return None.

    This function is the single place the spatial-language redesign
    flips to "arrow-keys" / "compass" / "oriented-map" once it ships —
    the received/actionable split in metrics keys off it.
    """
    return None


def build_perception(player, log_lines, turn):
    lines = [strip(l) for l in log_lines]
    grid_info = player.perceived_map_grid()
    bp = player.backpack
    hud = {
        "health": player.health,
        "max_health": player.max_health,
        "hunger": player.hunger,
        "thirst": player.thirst,
        "fatigue": player.fatigue,
        "food": bp.food,
        "water": bp.water,
        "medicine": bp.medicine,
        "ammo": bp.ammo,
        "level": player.level,
        "day": player.day,
        "phase": getattr(player, "day_phase",
                         "night" if player.is_night else "day"),
        "biome": getattr(player, "biome", None) or getattr(
            player, "current_biome", None),
        "equipped_weapon": getattr(player.equipped_weapon, "name", None),
        "has_flashlight": getattr(player, "has_flashlight", False),
    }
    panel, wi = _escape_panel(player)
    return Perception(
        turn=turn,
        hud=hud,
        grid=grid_info["grid"],
        player_xy=grid_info["player"],
        size=grid_info["size"],
        log=lines,
        flares=_parse_flares(lines),
        escape_panel=panel,
        investigation=wi,
        encounter=_parse_encounter(lines),
        spatial_relation=_spatial_relation(lines, panel),
        reference_frame=_reference_frame(player),
    )
