"""The player-facing dressing of the day/night cycle.

The engine keeps the *mechanic* (game._update_time): four internal phase
roles - "dawn" / "day" / "dusk" / "night" - drive visibility, encounter
chance and hunger/thirst decay, keyed to the role name and nothing else.
What those roles are *called* on the HUD, and the glyph shown, is the
world's to say: a valley has a sun; a ship adrift between stars keeps a
clock and a lighting schedule but no sky.

The engine reads this off `world.prose["day_cycle"]`:

    "day_cycle": {
        "labels": {"day": "ship day", "night": "ship night",
                   "dawn": "lights up", "dusk": "lights down"},
        "glyphs": {"day": "○", "night": "●", "dawn": "◔", "dusk": "◕"},
    }

Either sub-key may be partial or absent; anything unspecified falls back
to GENERIC below, which is deliberately the historical valley/default
wording so The Silence stays byte-identical. Callers case the label
themselves (.upper() on the panels, .title() in classic mode), so the
values here are lowercase.
"""

_LABELS = {"dawn": "dawn", "day": "day", "dusk": "dusk", "night": "night"}
_GLYPHS = {"day": "☀", "night": "☾", "dusk": "◐", "dawn": "☼"}
_COLORS = {"day": "yellow", "night": "blue", "dusk": "#d08a3c", "dawn": "#d08a3c"}


def _cycle(world):
    return (getattr(world, "prose", None) or {}).get("day_cycle", {}) or {}


def phase_label(world, phase):
    """Lowercase display name for an internal phase role."""
    return _cycle(world).get("labels", {}).get(phase) or _LABELS.get(phase, phase)


def phase_glyph(world, phase):
    return _cycle(world).get("glyphs", {}).get(phase) or _GLYPHS.get(phase, "·")


def phase_color(world, phase):
    return _cycle(world).get("colors", {}).get(phase) or _COLORS.get(phase, "grey50")
