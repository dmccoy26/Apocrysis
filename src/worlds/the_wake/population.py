"""World 2 - "The Wake": the ship's population.

The hostiles are the crew. This module maps a combat archetype (what
the thing does in a fight - engine-decided) to a crew identity, a
last-known situation, a presentation line and behaviour flags - the
same shape as worlds/silence/population.py, self-contained so the two
worlds don't couple.

Phase F §10.2: `describe(variant, conf, hint)` uses `hint` (the set of
known milestone ids) to shift how a changed crew member reads. Before
the player has established `THE_CHANGED`, they read as a hostile human
("A SECURITY OFFICER"); after, as "one of the changed - security,
once". After `CHANGE_IS_STAGED` a passive one gets the line that lands.
"""
from dataclasses import dataclass

ARCHETYPES = ("fresh", "common", "swift", "heavy", "toxic", "armored")


@dataclass(frozen=True)
class Variant:
    id: str
    archetype: str
    display: str            # "security officer"  (shown after the label -)
    line: str               # the presentation sentence
    weight: float = 1.0
    band: tuple = (0, 99)   # (min_exp, max_exp) this identity appears in
    anchor: str = ""        # building content tag it clusters near
    flags: tuple = ()       # 'passive' | 'skittish'
    lean: tuple = ()        # occupational loot categories
    rare: bool = False


# id -> loot categories this situation leans toward.
SITUATIONS = {
    "on_shift":       ("tools", "occupational", "water"),
    "off_duty":       ("household", "personal"),
    "sealed_in":      ("spent", "damaged", "personal"),
    "went_back":      ("medical", "light", "personal"),
    "holding_a_door": ("tactical", "light", "spent"),
    "already_turning":("nothing", "spent", "damaged"),
}

# earlier expeditions = the ship still half-running; later = the seals
# and the last stand behind the barricade.
_STAGE_SITUATIONS = (
    (4,  ("on_shift", "off_duty")),
    (9,  ("on_shift", "went_back", "sealed_in")),
    (13, ("sealed_in", "went_back", "holding_a_door")),
    (99, ("holding_a_door", "sealed_in", "already_turning")),
)


def situations_for_stage(expeditions_completed):
    for lim, sits in _STAGE_SITUATIONS:
        if expeditions_completed < lim:
            return sits
    return _STAGE_SITUATIONS[-1][1]


VARIANTS = (
    # --- heavy: the people who moved the ship's mass ---------------
    Variant("cargo", "heavy", "cargo hand",
            "Loader's rig still buckled on, one glove gone.",
            weight=1.2, anchor="R", lean=("tools", "occupational")),
    Variant("structural", "heavy", "structural tech",
            "A hardsuit, scarred and half-sealed. Something metal still clipped to the belt.",
            weight=1.0, lean=("tools", "occupational")),
    Variant("reactor_hand", "heavy", "reactor hand",
            "Heavy shielding coveralls, a dosimeter dead on the collar.",
            weight=0.9, band=(4, 99), anchor="engineering",
            lean=("tools", "fuel", "occupational")),

    # --- common: the ordinary crew --------------------------------
    Variant("hydroponics", "common", "hydroponics tech",
            "Grow-bay apron, soil still under the nails.",
            weight=1.2, anchor="S", lean=("food", "water")),
    Variant("galley", "common", "galley hand",
            "A serving tunic, a ration card clipped to the pocket.",
            weight=1.1, lean=("food", "household")),
    Variant("clerk", "common", "logistics clerk",
            "A deck lanyard, a slate cracked across the screen.",
            weight=1.0, lean=("personal", "household")),
    Variant("colonist", "common", "colonist",
            "Civilian clothes - a passenger, not crew. Still holding a folded transfer slip.",
            weight=1.1, lean=("personal", "food")),

    # --- fresh: caught before they were properly awake -----------
    Variant("cryo_early", "fresh", "early riser",
            "A cryo gown and one sock. This one was barely out of the pod.",
            weight=1.4, band=(0, 8), flags=("skittish",),
            anchor="cryo", lean=("personal",)),
    Variant("just_woke", "fresh", "crew member",
            "A duty jumpsuit, barely marked. It went fast for this one.",
            weight=1.2, band=(0, 7), lean=("food", "personal")),

    # --- swift: the ones who moved fast ------------------------
    Variant("runner_crew", "swift", "courier",
            "Light rig, soft boots. It still moves like it knows the decks.",
            weight=1.0, band=(3, 99), lean=("water", "personal")),
    Variant("scout", "swift", "survey tech",
            "A field harness, a mapping slate snapped in half.",
            weight=0.8, band=(4, 99), lean=("outdoor", "water")),

    # --- toxic: medical --------------------------------------
    Variant("medic", "toxic", "medic",
            "Scrubs and a med badge. It was with the sick when it turned.",
            weight=1.0, anchor="medical", lean=("medical", "personal")),
    Variant("orderly", "toxic", "orderly",
            "A ward tunic, gloves still on.",
            weight=0.7, anchor="medical", lean=("medical",)),

    # --- armored: security ----------------------------------
    Variant("security", "armored", "security officer",
            "A duty vest and sidearm rig, still recognisable. The holster is empty.",
            weight=1.1, band=(2, 99), lean=("tactical", "light", "radio")),
    Variant("marshal", "armored", "deck marshal",
            "A section marshal's coat, a name bar worn illegible.",
            weight=0.7, band=(4, 99), lean=("tactical", "light")),

    # --- the rare, uncomfortable tier -----------------------
    Variant("ship_child", "swift", "colony child",
            "A small figure in a torn schooling smock. A pod tag still clipped at the collar.",
            weight=1.0, band=(3, 99), anchor="cryo",
            flags=("skittish",), lean=("personal",), rare=True),
    Variant("elder_colonist", "common", "elderly colonist",
            "Frail, slow, a blanket still around the shoulders. It barely registers you.",
            weight=1.0, band=(4, 99), flags=("passive",),
            lean=("household", "medical", "personal"), rare=True),

    # --- stripped / unknown --------------------------------
    Variant("stripped", "common", "",
            "No uniform, no ID, no marks. Nothing left to say who this was.",
            weight=0.6, band=(7, 99), lean=()),
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
    """'clear' | 'hint' | 'unknown' - later stages strip identity away
    faster, as the changed get further from what they were."""
    t = min(1.0, expeditions_completed / 18)
    r = rng.random()
    if r < 0.15 + 0.50 * t:
        return "unknown" if r < 0.05 + 0.35 * t else "hint"
    return "clear"


_VAGUE = {"heavy": "someone in a work rig", "common": "crew",
          "swift": "someone quick", "toxic": "someone from medical",
          "armored": "someone in a duty vest", "fresh": "someone barely dressed"}


def _a(noun):
    return ("an " if noun[:1].lower() in "aeiou" else "a ") + noun


def describe(variant, conf, hint=None):
    """(label, line) for the encounter banner. Phase F §10.2: the
    meaning of the encounter changes with the investigation.

    hint = the set/tuple of known milestone ids.
      before THE_CHANGED : reads as a hostile human  ("A SECURITY OFFICER")
      after  THE_CHANGED : reads as one of the changed ("ONE OF THE CHANGED - SECURITY, ONCE")
      after CHANGE_IS_STAGED + a passive one : the line that lands
    """
    hint = set(hint or ())
    known_changed = "THE_CHANGED" in hint
    staged = "CHANGE_IS_STAGED" in hint

    if not variant.display or conf == "unknown":
        if known_changed:
            return "ONE OF THE CHANGED", "Too far gone to tell what it was. Crew, once."
        return "SOMEONE IN THE DARK", "You can't make out who - only that it's coming at you."

    disp = variant.display
    if conf == "hint":
        disp = _VAGUE.get(variant.archetype, "crew")

    if not known_changed:
        # a hostile human, not yet understood as anything else
        return disp.upper(), variant.line

    label = f"ONE OF THE CHANGED - {disp}, once"
    line = variant.line
    if staged and "passive" in variant.flags:
        line = variant.line + " It looks at your face like it's trying to place you."
    return label.upper(), line


def loot_pool(variant, situation):
    return tuple(variant.lean) + SITUATIONS.get(situation, ())
