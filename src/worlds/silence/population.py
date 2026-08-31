"""World 1 - "The Silence": the valley's population.

The infected are the people who lived here. This module maps a combat
archetype (what the thing does in a fight - decided elsewhere) to a
plausible *identity*, a *last-known situation*, a presentation line,
and behaviour flags. Pure data + selection - no imports from
src.mixins / src.game, no RNG of its own (callers pass one). See
docs/ZOMBIE_IDENTITY_PASS.md.

Layering:  identity -> situation -> presentation -> loot -> archetype
The player sees `INFECTED - former mechanic` + a line; the threat card
reads from the archetype and is untouched.
"""
from dataclasses import dataclass

ARCHETYPES = ("fresh", "common", "swift", "heavy", "toxic", "armored")

# ---- last-known situations -----------------------------------------
# id -> loot categories this situation leans toward. The loot roll
# blends these with the identity's own occupational lean (population
# .loot_pool()).
SITUATIONS = {
    "ordinary":        ("food", "household", "personal"),
    "working":         ("tools", "occupational", "water"),
    "at_home":         ("household", "personal", "medical"),
    "passing_through": ("water", "outdoor"),
    "responding":      ("light", "tools", "radio", "medical"),
    "leaving":         ("food", "water", "light", "personal"),
    "last_stand":      ("spent", "damaged", "nothing"),
}

# Which situations are plausible at each collapse stage, keyed by
# expeditions_completed (0-indexed). Earlier = normal life, later = the
# evacuation and its failure.
_STAGE_SITUATIONS = (
    (3,  ("ordinary", "working", "at_home")),
    (6,  ("working", "ordinary", "responding", "passing_through")),
    (9,  ("responding", "working", "leaving")),
    (12, ("responding", "leaving", "working")),
    (15, ("leaving", "responding", "last_stand")),
    (99, ("last_stand", "leaving", "at_home")),
)


def situations_for_stage(expeditions_completed):
    for lim, sits in _STAGE_SITUATIONS:
        if expeditions_completed < lim:
            return sits
    return _STAGE_SITUATIONS[-1][1]


# ---- the roster ---------------------------------------------------
@dataclass(frozen=True)
class Variant:
    id: str
    archetype: str
    display: str            # "former mechanic"  (shown after INFECTED -)
    line: str               # the presentation sentence
    weight: float = 1.0
    band: tuple = (0, 99)   # (min_exp, max_exp) this identity appears in
    anchor: str = ""        # building content tag it clusters near ('' anywhere)
    flags: tuple = ()       # 'passive' | 'skittish'
    lean: tuple = ()        # occupational loot categories
    rare: bool = False      # the uncomfortable tier - very low weight


VARIANTS = (
    # --- heavy: manual trades -------------------------------------
    Variant("farmhand", "heavy", "farmhand",
            "Mud-caked overalls, rubber boots worn through at one heel.",
            weight=1.4, band=(0, 12), lean=("food", "tools")),
    Variant("logger", "heavy", "logging worker",
            "A heavy canvas jacket, still intact. One arm hangs wrong.",
            weight=1.0, lean=("tools", "occupational")),
    Variant("mechanic", "heavy", "mechanic",
            "Grease-stained coveralls. Something metallic still hangs from the belt.",
            weight=1.1, anchor="R", lean=("tools", "occupational")),
    Variant("construction", "heavy", "construction worker",
            "High-visibility vest, a hard hat knocked askew.",
            weight=1.0, band=(2, 99), lean=("tools", "occupational")),
    Variant("groundcrew", "heavy", "ground crew",
            "A maintenance vest, ear defenders around the neck.",
            weight=0.7, band=(6, 99), anchor="airfield",
            lean=("tools", "fuel", "occupational")),

    # --- common: the ordinary valley ----------------------------
    Variant("shopworker", "common", "shop worker",
            "An apron, a plastic name tag, one hand still gripping a ring of keys.",
            weight=1.3, band=(0, 12), anchor="S", lean=("food", "household")),
    Variant("clerk", "common", "office worker",
            "Slacks and a lanyard; one shoe is missing.",
            weight=1.0, band=(0, 10), lean=("personal", "household")),
    Variant("gardener", "common", "gardener",
            "A sun hat, and one gardening glove still on.",
            weight=0.9, band=(0, 12), lean=("food", "tools")),
    Variant("trucker", "common", "delivery driver",
            "A company shirt, a cap, a lanyard with a fleet number.",
            weight=1.0, band=(3, 99), anchor="road",
            lean=("food", "water", "outdoor", "fuel")),
    Variant("radiotech", "common", "radio technician",
            "A tool bag, a headset hanging around the neck.",
            weight=0.7, band=(6, 99), anchor="radio_station",
            lean=("radio", "tools", "occupational")),
    Variant("parent", "common", "parent",
            "Still clutching a torn grocery sack.",
            weight=1.1, band=(0, 99), lean=("food", "personal")),

    # --- fresh: caught mid-ordinary ----------------------------
    Variant("pajamas", "fresh", "resident",
            "Nightclothes and one slipper. This one turned at home.",
            weight=1.2, band=(0, 8), flags=("skittish",),
            lean=("household", "personal")),
    Variant("earlyturn", "fresh", "resident",
            "Ordinary clothes, barely marked. It happened fast for this one.",
            weight=1.4, band=(0, 6), lean=("food", "personal")),

    # --- swift: fast people -----------------------------------
    Variant("hunter", "swift", "hunter",
            "Camouflage and worn boots. It moves over rough ground like it knows how.",
            weight=1.0, band=(5, 99), lean=("ammo", "outdoor", "food")),
    Variant("runner", "swift", "trail runner",
            "Running gear, still fast, still light on its feet.",
            weight=0.8, band=(3, 99), lean=("water", "outdoor")),
    Variant("hiker", "swift", "hiker",
            "A daypack, a trekking pole snapped in half. Came in from outside.",
            weight=0.9, band=(4, 99), anchor="wilderness",
            lean=("water", "outdoor", "food")),

    # --- toxic: the clinic ----------------------------------
    Variant("nurse", "toxic", "nurse",
            "Scrubs and a hospital badge. It was near the sick when it turned.",
            weight=1.0, anchor="clinic", lean=("medical", "personal")),
    Variant("clinicworker", "toxic", "clinic worker",
            "A staff lanyard, gloves still on.",
            weight=0.7, anchor="clinic", lean=("medical",)),

    # --- armored: the response ----------------------------------
    Variant("patrol", "armored", "highway patrol officer",
            "A duty vest and radio, still recognisable. The holster is empty.",
            weight=1.0, band=(3, 99), lean=("tactical", "light", "radio")),
    Variant("deputy", "armored", "sheriff's deputy",
            "A tan uniform, a name bar you can't quite read.",
            weight=0.7, band=(4, 99), lean=("tactical", "light")),

    # --- the rare, uncomfortable tier -----------------------
    Variant("child", "swift", "schoolchild",
            "A small figure. The remains of a torn school uniform. A plastic name tag, still clipped on.",
            weight=1.0, band=(3, 99), anchor="school",
            flags=("skittish",), lean=("personal",), rare=True),
    Variant("elderly", "common", "elderly resident",
            "Frail, slow, a cardigan buttoned wrong. It barely reacts to you.",
            weight=1.0, band=(3, 99), flags=("passive",),
            lean=("household", "medical", "personal"), rare=True),

    # --- stripped / unknown - the honest home of "Elite" -------
    Variant("stripped", "common", "",
            "No clothing, no marks. Nothing left to say who this was.",
            weight=0.6, band=(8, 99), lean=()),
)

_BY_ARCH = {}
for _v in VARIANTS:
    _BY_ARCH.setdefault(_v.archetype, []).append(_v)

_FALLBACK = {a: Variant(f"unknown_{a}", a, "", "You can't tell what this was.")
             for a in ARCHETYPES}


def _band_ok(v, exp):
    return v.band[0] <= exp <= v.band[1]


def pick_identity(archetype, expeditions_completed, rng, anchor=None):
    """A Variant for this archetype, plausible at this depth.

    `anchor` (a building content tag / zone) is a *soft* bias: an
    anchored identity is ~3x more likely on its anchor and ~1/3 as
    likely off it, but can still appear anywhere. `rng` is a
    caller-supplied random.Random - never the map RNG."""
    pool = [v for v in _BY_ARCH.get(archetype, [])
            if _band_ok(v, expeditions_completed)]
    if not pool:
        return _FALLBACK.get(archetype, _FALLBACK["common"])

    def _w(v):
        base = 0.12 if v.rare else 1.0
        if v.anchor:
            base *= 3.0 if v.anchor == anchor else 0.35
        return v.weight * base

    return rng.choices(pool, weights=[_w(v) for v in pool])[0]


def pick_situation(variant, expeditions_completed, rng):
    return rng.choice(situations_for_stage(expeditions_completed))


def confidence(expeditions_completed, rng):
    """'clear' | 'hint' | 'unknown' - later stages strip identity away."""
    t = min(1.0, expeditions_completed / 18)
    r = rng.random()
    if r < 0.15 + 0.45 * t:
        return "unknown" if r < 0.05 + 0.30 * t else "hint"
    return "clear"


def describe(variant, conf):
    """(label, line) for the encounter banner.

    clear   -> INFECTED - former mechanic  + full line
    hint    -> INFECTED - a worker          + a hedged line
    unknown -> INFECTED                     + "no way to tell"
    """
    if not variant.display or conf == "unknown":
        return "INFECTED", "Whatever this person was, there's no way to tell any more."
    if conf == "hint":
        # collapse a specific trade to a vague one
        vague = _VAGUE.get(variant.archetype, "someone")
        return f"INFECTED - {vague}", variant.line
    return f"INFECTED - {_a(variant.display)}", variant.line


_VAGUE = {"heavy": "a worker", "common": "a local", "swift": "someone quick",
          "toxic": "someone from the clinic", "armored": "someone in uniform",
          "fresh": "a resident"}


def loot_pool(variant, situation):
    """The blended loot-category lean for this infected: occupational +
    situational. Empty -> the caller falls back to a generic roll."""
    return tuple(variant.lean) + SITUATIONS.get(situation, ())


def _a(noun):
    return ("an " if noun[:1].lower() in "aeiou" else "a ") + noun
