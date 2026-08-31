"""G6 (Phase G, §8): a small set of player-global preferences, held in
`.apocrysis/settings.json` (NOT per-campaign - these are "how do I want
to experience the game", not "which game am I playing").

Every entry is a bool or a two-value enum the game reads at expedition
start or per-render. Deliberately tiny; do not grow it here - panel
width / layout presets / colour themes / keybindings are G.1-G.4.
"""
import json
import os

from src import runtime_paths

DEFAULTS = {
    "play_log": False,        # auto-start the play-log transcript
    "combat_card": "full",    # "full" | "terse" - the fight/escape % card
    "command_hints": True,     # the ACTIONS panel
    "hud_density": "full",     # "full" | "compact" - CONDITIONS/WARNINGS
}

ENUMS = {
    "combat_card": ("full", "terse"),
    "hud_density": ("full", "compact"),
}

# Human labels for SettingsScreen.
LABELS = {
    "play_log": "Play log",
    "combat_card": "Combat card",
    "command_hints": "Command hints",
    "hud_density": "HUD density",
}
ORDER = ("play_log", "combat_card", "command_hints", "hud_density")


def _path():
    return os.path.join(str(runtime_paths.home()), "settings.json")


def load():
    """The stored settings merged over DEFAULTS. Tolerant: a missing /
    unreadable / partial file just yields defaults for what's missing,
    and a value of the wrong type or an out-of-range enum is ignored."""
    out = dict(DEFAULTS)
    try:
        with open(_path()) as f:
            raw = json.load(f)
    except (OSError, ValueError):
        return out
    if not isinstance(raw, dict):
        return out
    for k, default in DEFAULTS.items():
        if k not in raw:
            continue
        v = raw[k]
        if k in ENUMS:
            if v in ENUMS[k]:
                out[k] = v
        elif isinstance(v, bool):
            out[k] = v
    return out


def save(values):
    """Write `values` (only the known keys, defaults filling any gap)
    and return the cleaned dict. Creates the runtime root if needed."""
    clean = {}
    for k, default in DEFAULTS.items():
        v = values.get(k, default)
        if k in ENUMS and v not in ENUMS[k]:
            v = default
        if k not in ENUMS and not isinstance(v, bool):
            v = default
        clean[k] = v
    p = _path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(clean, f, indent=2)
    return clean


def toggled(values, key):
    """Return a copy of `values` with `key` flipped - bool inverted, an
    enum advanced to its other value."""
    out = dict(values)
    if key in ENUMS:
        a, b = ENUMS[key]
        out[key] = b if values.get(key, DEFAULTS[key]) == a else a
    else:
        out[key] = not values.get(key, DEFAULTS[key])
    return out


def display(values, key):
    """The on-screen value token for `key`."""
    v = values.get(key, DEFAULTS[key])
    if key in ENUMS:
        return str(v).upper()
    return "ON" if v else "OFF"
