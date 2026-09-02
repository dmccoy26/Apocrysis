"""World 3 - "The Deep": the mine's population.

The hostiles are the crew. This module maps a combat archetype (what
the thing does in a fight - engine-decided) to a crew identity, a
last-known situation, a presentation line and behaviour flags - the
same shape as worlds/the_wake/population.py, self-contained.

Phase F §10.2: `describe(variant, conf, hint)` uses `hint` (the set of
known milestone / fact ids) to shift how a Changed crew member reads.
Before `CHANGED_ARE_CREW`, they read as a hostile person
("A ROADHEADER OPERATOR"); after, as "one of the Changed - a roadheader
operator, once". After `CHANGED_BY_DEPTH` a passive one gets the line
that lands.

§1.5 #4: the Changed are staged by exposure/depth - recently changed in
bands I-II, far gone in III-IV, stationed in IV-V.
"""
from dataclasses import dataclass

ARCHETYPES = ("fresh", "common", "swift", "heavy", "toxic", "armored")


@dataclass(frozen=True)
class Variant:
    id: str
    archetype: str
    display: str
    line: str
    weight: float = 1.0
    band: tuple = (0, 99)
    anchor: str = ""
    flags: tuple = ()
    lean: tuple = ()
    rare: bool = False


SITUATIONS = {
    "on_shift":        ("tools", "occupational", "water"),
    "off_shift":       ("household", "personal"),
    "sealed_in":       ("spent", "damaged", "personal"),
    "went_back":       ("medical", "light", "personal"),
    "holding_ground":  ("tactical", "light", "spent"),
    "far_gone":        ("nothing", "spent", "damaged"),
}

# earlier levels = the works still half-running; deeper = the sealed
# galleries and the crews holding ground.
_STAGE_SITUATIONS = (
    (5,  ("on_shift", "off_shift")),
    (10, ("on_shift", "went_back", "sealed_in")),
    (15, ("sealed_in", "went_back", "holding_ground")),
    (99, ("holding_ground", "sealed_in", "far_gone")),
)


def situations_for_stage(expeditions_completed):
    for lim, sits in _STAGE_SITUATIONS:
        if expeditions_completed < lim:
            return sits
    return _STAGE_SITUATIONS[-1][1]


VARIANTS = (
    # --- heavy: the people who cut and moved the rock -------------
    Variant("roadheader", "heavy", "roadheader operator",
            "Cutting-machine harness still buckled on, one gauntlet gone.",
            weight=1.2, anchor="M", lean=("tools", "occupational")),
    Variant("shaftsman", "heavy", "shaft fitter",
            "A rope-access rig, scarred and half-clipped. Something metal still on the belt.",
            weight=1.0, lean=("tools", "occupational")),
    Variant("borecrew", "heavy", "bore crew",
            "Heavy drilling coveralls, a dosimeter dead on the collar.",
            weight=0.9, band=(5, 99), anchor="the_bore",
            lean=("tools", "fuel", "occupational")),

    # --- common: the ordinary crew ------------------------------
    Variant("trammer", "common", "trammer",
            "Haulage jacket, ore dust worked into every seam of it.",
            weight=1.2, anchor="R", lean=("tools", "occupational")),
    Variant("lampman", "common", "lamp-room hand",
            "A lamp-room tabard, a check tally still clipped to the pocket.",
            weight=1.1, lean=("light", "household")),
    Variant("clerk", "common", "weigh clerk",
            "A surface lanyard, a slate cracked across the screen.",
            weight=1.0, lean=("personal", "household")),
    Variant("contractor", "common", "contract miner",
            "Not company kit - a contractor's own gear. Still holding a folded pay docket.",
            weight=1.1, lean=("personal", "food")),

    # --- fresh: caught early, near the top -----------------------
    Variant("new_start", "fresh", "new start",
            "Issue overalls, barely marked, one boot unlaced. This one hadn't been down long.",
            weight=1.4, band=(0, 9), flags=("skittish",),
            anchor="upper_works", lean=("personal",)),
    Variant("day_wage", "fresh", "day-wage hand",
            "A surface jacket over pit clothes. It went fast for this one.",
            weight=1.2, band=(0, 8), lean=("food", "personal")),

    # --- swift: the ones who moved fast ------------------------
    Variant("deputy_runner", "swift", "deputy's runner",
            "Light kit, soft boots. It still moves like it knows every drift.",
            weight=1.0, band=(3, 99), lean=("water", "personal")),
    Variant("surveyor", "swift", "survey hand",
            "A survey harness, a mapping slate snapped in half.",
            weight=0.8, band=(5, 99), lean=("outdoor", "water")),

    # --- toxic: the medical station ---------------------------
    Variant("mine_medic", "toxic", "mine medic",
            "First-aid tabard and a med badge. It was with the sick when it turned.",
            weight=1.0, anchor="medical", lean=("medical", "personal")),
    Variant("orderly", "toxic", "station orderly",
            "A station tunic, gloves still on.",
            weight=0.7, anchor="medical", lean=("medical",)),

    # --- armored: the ones who held the doors -----------------
    Variant("banksman", "armored", "banksman",
            "A shaft-side duty vest, a whistle still on the lanyard. Broad across the shoulders.",
            weight=1.1, band=(2, 99), lean=("tactical", "light", "radio")),
    Variant("shift_boss", "armored", "shift boss",
            "A deputy's coat, a name bar worn illegible. It plants itself in the doorway.",
            weight=0.7, band=(5, 99), lean=("tactical", "light")),

    # --- the rare, uncomfortable tier ------------------------
    Variant("pit_boy", "swift", "pit boy",
            "A small figure in a torn work smock. A check tag still on a string at the neck.",
            weight=1.0, band=(4, 99), anchor="upper_works",
            flags=("skittish",), lean=("personal",), rare=True),
    Variant("old_hand", "common", "old hand",
            "Frail, slow, a jacket hanging off him. He barely registers you.",
            weight=1.0, band=(5, 99), flags=("passive",),
            lean=("household", "medical", "personal"), rare=True),

    # --- stripped / unknown --------------------------------
    Variant("stripped", "common", "",
            "No kit, no tag, no marks. Nothing left to say who this was.",
            weight=0.6, band=(10, 99), lean=()),
)

_BY_ARCH = {}
for _v in VARIANTS:
    _BY_ARCH.setdefault(_v.archetype, []).append(_v)

_FALLBACK = {a: Variant(f"unknown_{a}", a, "", "You can't tell what this was.")
             for a in ARCHETYPES}


def _band_ok(v, exp):
    return v.band[0] <= exp <= v.band[1]


def pick_identity(archetype, expeditions_completed, rng, anchor=None):
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
    """'clear' | 'hint' | 'unknown' - deeper levels strip identity away
    faster, as the Changed get further from what they were."""
    t = min(1.0, expeditions_completed / 18)
    r = rng.random()
    if r < 0.15 + 0.50 * t:
        return "unknown" if r < 0.05 + 0.35 * t else "hint"
    return "clear"


_VAGUE = {"heavy": "someone in a cutting rig", "common": "a miner",
          "swift": "someone quick", "toxic": "someone from the station",
          "armored": "someone in a duty vest", "fresh": "someone barely kitted"}


def _a(noun):
    return ("an " if noun[:1].lower() in "aeiou" else "a ") + noun


def describe(variant, conf, hint=None):
    """(label, line) for the encounter banner. Phase F §10.2: the
    meaning of the encounter changes with the investigation.

      before CHANGED_ARE_CREW : reads as a hostile person
      after  CHANGED_ARE_CREW : reads as one of the Changed ("... , once")
      after CHANGED_BY_DEPTH + a passive one : the line that lands
    """
    hint = set(hint or ())
    known_crew = "CHANGED_ARE_CREW" in hint
    staged = "CHANGED_BY_DEPTH" in hint

    if not variant.display or conf == "unknown":
        if known_crew:
            return "ONE OF THE CHANGED", "Too far gone to tell what it was. Crew, once."
        return "SOMETHING IN THE DARK", "You can't make out who - only that it's coming at you."

    disp = variant.display
    if conf == "hint":
        disp = _VAGUE.get(variant.archetype, "a miner")

    if not known_crew:
        return disp.upper(), variant.line

    label = f"ONE OF THE CHANGED - {disp}, once"
    line = variant.line
    if staged and "passive" in variant.flags:
        line = variant.line + " It looks at your face like it's trying to place you."
    return label.upper(), line


def loot_pool(variant, situation):
    return tuple(variant.lean) + SITUATIONS.get(situation, ())
