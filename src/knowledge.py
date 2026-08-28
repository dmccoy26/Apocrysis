# ============================================================
# Apocrysis - the player knowledge model (v4 Phase B / Stage 2C)
# File: src/knowledge.py
#
# The four-object mystery model from
# docs/PHASE0_KNOWLEDGE_MODEL.md, generalised out of the Stage 0
# slice (src/slice_dam_road.py + SliceMixin, which proved the shape).
#
#   Evidence is DISCOVERED by the player.
#   Facts / Deductions / the Hypothesis state are DERIVED from what
#   evidence has been discovered - never set directly. State
#   transitions are automatic, never a player command (design doc,
#   "Knowledge state").
#
# Pure data + pure derivation. No imports from src/, no I/O. The
# generator (Stage 4) populates the collections per-expedition; in
# Phase B, find_loot()'s "clue" outcome adds standalone facts via
# add_clue().
# ============================================================

# The four states a piece of knowledge can be in.
OBSERVED = "Observed"      # seen raw, no meaning attached yet
KNOWN = "Known"            # a fact established by >=1 piece of evidence
SUSPECTED = "Suspected"    # a hypothesis with incomplete support
CONFIRMED = "Confirmed"    # a hypothesis established by sufficient evidence

# Hypothesis-state strings (distinct from the fact states above).
HYP_UNKNOWN = "unknown"
HYP_SUSPECTED = "suspected"
HYP_CONFIRMED = "confirmed"


class Fact:
    def __init__(self, id, statement):
        self.id = id
        self.statement = statement


class Evidence:
    def __init__(self, id, text, supports=(), location=None, method="observe"):
        self.id = id
        self.text = text
        self.supports = list(supports)      # fact ids this evidence establishes
        self.location = location            # location id where it physically is
        self.method = method                # "observe" (auto on arrival) | "search"


class Deduction:
    def __init__(self, id, text, needs=()):
        self.id = id
        self.text = text
        self.needs = list(needs)            # fact ids that must all be Known


class Hypothesis:
    def __init__(self, id, statement, suspected_when=(), confirmed_by=None):
        self.id = id
        self.statement = statement
        self.suspected_when = list(suspected_when)   # deduction ids
        self.confirmed_by = confirmed_by             # evidence id


class Knowledge:
    """One expedition's mystery, plus the player's progress through it."""

    def __init__(self):
        self.facts = {}          # id -> Fact
        self.evidence = {}       # id -> Evidence  (the full catalogue)
        self.deductions = {}     # id -> Deduction
        self.hypothesis = None   # Hypothesis | None
        self.found = set()       # evidence ids the player has discovered
        self._observed = set()   # fact ids seen raw, no evidence yet
        self._auto_seq = 0       # for add_clue() ids

    # ---- generation-side population --------------------------

    def add_fact(self, fact):
        self.facts[fact.id] = fact

    def add_evidence(self, evidence):
        self.evidence[evidence.id] = evidence

    def add_deduction(self, deduction):
        self.deductions[deduction.id] = deduction

    def set_hypothesis(self, hypothesis):
        self.hypothesis = hypothesis

    def add_clue(self, statement, evidence_text=None):
        """Phase B convenience: a standalone flavour fact with one
        piece of directly-supporting evidence, already discovered.
        Returns the fact id."""
        self._auto_seq += 1
        fid = f"c{self._auto_seq}"
        self.add_fact(Fact(fid, statement))
        self.add_evidence(Evidence(fid, evidence_text or statement, supports=[fid]))
        self.found.add(fid)
        return fid

    # ---- discovery ------------------------------------------

    def discover(self, evidence_id):
        """Record one evidence item as found. True if newly found."""
        if evidence_id in self.found or evidence_id not in self.evidence:
            return False
        self.found.add(evidence_id)
        # Any fact this now establishes is no longer merely "observed".
        for fid in self.evidence[evidence_id].supports:
            self._observed.discard(fid)
        return True

    def observe_fact(self, fact_id):
        """Raw sighting of something whose meaning isn't clear yet
        (discover-before-understand). No effect once the fact is Known."""
        if fact_id in self.facts and fact_id not in self.facts_known():
            self._observed.add(fact_id)

    # ---- derivation (never stored, always computed) ---------

    def facts_known(self):
        known = set()
        for eid in self.found:
            ev = self.evidence.get(eid)
            if ev:
                known.update(ev.supports)
        return known & set(self.facts)

    def fact_state(self, fact_id):
        if fact_id in self.facts_known():
            return KNOWN
        if fact_id in self._observed:
            return OBSERVED
        return None

    def deductions_available(self):
        known = self.facts_known()
        return [d for d in self.deductions.values() if set(d.needs) <= known]

    def hypothesis_state(self):
        if self.hypothesis is None:
            return HYP_UNKNOWN
        if self.hypothesis.confirmed_by in self.found:
            return HYP_CONFIRMED
        available = {d.id for d in self.deductions_available()}
        if self.hypothesis.suspected_when and set(self.hypothesis.suspected_when) <= available:
            return HYP_SUSPECTED
        return HYP_UNKNOWN

    def evidence_for(self, fact_id, found_only=True):
        src = self.found if found_only else set(self.evidence)
        return [self.evidence[e] for e in self.evidence
                if fact_id in self.evidence[e].supports and e in src]

    def is_empty(self):
        return not self.found and not self._observed

    # ---- persistence ---------------------------------------

    def progress_snapshot(self):
        """Just the mutable player-progress part - the catalogue
        (facts/evidence/deductions/hypothesis) is regenerated with the
        map, so only what the player has done needs saving."""
        return {"found": sorted(self.found), "observed": sorted(self._observed)}

    def restore_progress(self, snapshot):
        if not snapshot:
            return
        self.found = set(snapshot.get("found", []))
        self._observed = set(snapshot.get("observed", []))

    def to_dict(self):
        """Full serialisation - catalogue AND progress - for the
        named-slot save (save_game), where the map is restored verbatim
        and generate_map() is not re-run, so the mystery cannot be
        regenerated."""
        return {
            "facts": [{"id": f.id, "statement": f.statement}
                      for f in self.facts.values()],
            "evidence": [{"id": e.id, "text": e.text, "supports": e.supports,
                          "location": e.location, "method": e.method}
                         for e in self.evidence.values()],
            "deductions": [{"id": d.id, "text": d.text, "needs": d.needs}
                           for d in self.deductions.values()],
            "hypothesis": None if self.hypothesis is None else {
                "id": self.hypothesis.id, "statement": self.hypothesis.statement,
                "suspected_when": self.hypothesis.suspected_when,
                "confirmed_by": self.hypothesis.confirmed_by,
            },
            "found": sorted(self.found),
            "observed": sorted(self._observed),
            "auto_seq": self._auto_seq,
        }

    @classmethod
    def from_dict(cls, data):
        k = cls()
        if not data:
            return k
        for f in data.get("facts", []):
            k.add_fact(Fact(f["id"], f["statement"]))
        for e in data.get("evidence", []):
            k.add_evidence(Evidence(e["id"], e["text"], supports=e.get("supports", ()),
                                    location=e.get("location"),
                                    method=e.get("method", "observe")))
        for d in data.get("deductions", []):
            k.add_deduction(Deduction(d["id"], d["text"], needs=d.get("needs", ())))
        h = data.get("hypothesis")
        if h:
            k.set_hypothesis(Hypothesis(h["id"], h["statement"],
                                        suspected_when=h.get("suspected_when", ()),
                                        confirmed_by=h.get("confirmed_by")))
        k.found = set(data.get("found", []))
        k._observed = set(data.get("observed", []))
        k._auto_seq = data.get("auto_seq", 0)
        return k
