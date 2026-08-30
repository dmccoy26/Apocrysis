"""Per-run record for a perception-bounded autoplay game.

The objective-related fields come in received/actionable pairs so a
failure reads unambiguously:

    objective_text_seen        — the game told the player there is a goal
    objective_destination_named — …and named what / where it is
    direction_text_seen        — a bearing word was shown ("south-west")
    direction_operational      — …and the player had a frame to act on it
    landmark_named             — a landmark was named in text
    landmark_visible           — …and that landmark is on the rendered map
    map_marker_present         — the map/ESCAPE panel shows a destination mark

`objective_reached` / `turns_to_objective` are outcome facts filled in
by the runner after the game — analysis, not something a policy used.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict


@dataclass
class RunRecord:
    seed: int | None = None
    chapter: int | None = None
    policy: str = ""
    nav_phrasing: str = "cardinal"   # what phrasing the game shipped this run

    outcome: str | None = None       # won | died | timeout
    turns: int = 0
    final_level: int = 1
    final_day: int = 1
    death_cause: str | None = None

    # --- comprehension: received vs actionable -------------------------
    objective_text_seen: bool = False
    objective_destination_named: bool = False
    direction_text_seen: bool = False
    direction_operational: bool = False
    landmark_named: bool = False
    landmark_visible: bool = False
    map_marker_present: bool = False

    # --- objective pursuit (outcome facts, set by the runner) ----------
    objective_reached: bool = False
    turns_to_objective: int | None = None
    turns_pursuing: int = 0          # turns the policy moved toward a lead
    turns_wandering: int = 0         # turns it did not

    # --- investigation ------------------------------------------------
    hypothesis_formed: bool = False
    hypothesis_corrections_seen: int = 0
    facts_found: int = 0
    facts_available: int = 0
    mystery_solved: bool = False

    # --- movement shape ---------------------------------------------
    tiles_visited: int = 0
    revisit_ratio: float = 0.0       # 1 - unique/steps
    max_distance_from_spawn: int = 0

    # --- survival economy (light; balance_autoplay is the real lab) ---
    min_health: int = 0
    final_food: int = 0
    final_water: int = 0
    fatigue_pinned_turns: int = 0    # turns at fatigue >= 95
    zombie_encounters: int = 0
    combat_deaths: int = 0

    notes: list = field(default_factory=list)

    # ------------------------------------------------------------------
    def observe(self, per):
        """Fold one turn's Perception into the running comprehension
        flags. Called every turn by the runner."""
        panel_txt = " ".join(per.escape_panel).lower()
        log_txt = " ".join(per.log).lower()
        blob = panel_txt + " " + log_txt
        # guidance context only: the ESCAPE panel + objective/discovery
        # flares. Ambient scenery ("you move through the mountain
        # forest") must not count as the game *guiding* you to a
        # landmark.
        guidance = panel_txt + " " + " ".join(
            t.lower() for c, t in per.flares
            if c in ("objective", "discovery", "story"))

        if per.escape_panel or "objective updated" in blob or "new lead" in blob:
            self.objective_text_seen = True

        # a named destination = the panel/stream refers to a specific
        # place, not the generic "the way out" / "a way toward another
        # route". The mystery site_labels are proper-noun-ish
        # ("the generator shed", "the ranger depot", "the town centre").
        _GENERIC = ("the way out", "a way toward another route",
                    "another route", "the controls")
        for ln in per.escape_panel:
            low = ln.lower()
            if "head for" in low or "found " in low:
                rest = low.split("head for")[-1] if "head for" in low else low
                if not any(g in rest for g in _GENERIC) and "the " in rest:
                    self.objective_destination_named = True

        if per.spatial_relation:
            self.direction_text_seen = True
            if per.reference_frame:
                self.direction_operational = True

        # landmark: a physical feature named in the guidance text AND
        # present as a glyph the player can see. Until the
        # spatial-language pass there are no landmark strings, so this
        # stays False — which is exactly the finding.
        # a landmark *cue* = "head toward / you can see / make for" a
        # named feature. Mechanism names ("the old mountain pass") and
        # ambient terrain do not count — until the spatial-language
        # pass adds real landmark guidance this stays ~0, which IS the
        # finding.
        _CUE = ("head toward", "head for the", "make for the",
                "you can see the", "toward the")
        _FEATURE = (("water tower", "T"), ("tower", "T"), ("bridge", "="),
                    ("church", "C"), ("silo", "T"))
        if any(c in guidance for c in _CUE):
            for word, glyphs in _FEATURE:
                if word in guidance:
                    self.landmark_named = True
                    if per.glyph_positions(glyphs):
                        self.landmark_visible = True

        if per.glyph_positions("!+"):
            self.map_marker_present = True

        for cls, _txt in per.flares:
            if cls == "story" and "had it wrong" in _txt.lower():
                self.hypothesis_corrections_seen += 1
        if any("you think" in l.lower() or "you know" in l.lower()
               for l in per.escape_panel + per.investigation):
            self.hypothesis_formed = True

        if per.hud["fatigue"] >= 95:
            self.fatigue_pinned_turns += 1
        if per.encounter is not None:
            self.zombie_encounters += 1

    def to_json(self) -> str:
        return json.dumps(asdict(self), default=str)
