"""§F.11: the fiction of MOVING through a world - entry lines, the
"can't cross" lines, the crossing beat, distant sightings, the HUD
location label + travel-drag note.

The engine reads this off `world.terrain.prose`; a world that authors
none gets GENERIC below - deliberately bland and world-NEUTRAL (it
never claims forest, water, hull, deck). The test for whether a line
belongs here: could it be false in a different world?
"""

# semantic slot -> event -> line. `{pct}` / `{k}` are .format()ed.
GENERIC = {
    "enter": {
        "shelter": "You get inside. It's safer here.",
        "slow": "The going is slow through here.",
        "dense": "You work your way through. It's slow.",
    },
    "reenter": {
        "shelter": "Back inside - safe for now.",
        "slow": "More of the same. Slow going.",
    },
    "hazard": {
        "slow": "The cold gets into you. You lost some health.",
    },
    "barrier": {
        "edge_first": "The way is closed off here - solid, and no way "
                      "through that you can see anywhere along it.",
        "edge": "Closed off. No way through.",
        "interior": "You can't get through here.",
    },
    "crossing": {
        "blocked": "You can't get across here.",
        "title": "THE CROSSING",
        "prompt": "Try for the other side?  ~{pct}% you make it clean.",
        "prompt_body": "Fail and you're back on this side - a hard knock, "
                       "and you may lose something loose from your pack.",
        "ask": "Go for it?",
        "ok": "You make it across, shaken but over.",
        "fail": "It throws you back where you started.",
        "loss": "You lost some {k} in the crossing.",
    },
    "spot": {
        "shelter": "Something built, standing on its own further out.",
        "settlement": "Signs of a place ahead - somewhere people were.",
    },
    # HUD "where you are" labels, by terrain role. Missing role ->
    # world.prose["place_name_fallback"].
    "label": {"settlement": "SETTLEMENT"},
    # tui travel-drag note, by terrain role.
    "hud_slow": {},
}


def tp(world, group, key, default=""):
    """One line from `world`'s terrain prose, falling back to GENERIC."""
    prose = getattr(getattr(world, "terrain", None), "prose", None) or {}
    got = prose.get(group, {}).get(key)
    if got is not None:
        return got
    return GENERIC.get(group, {}).get(key, default)
