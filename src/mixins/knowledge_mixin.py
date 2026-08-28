# ============================================================
# Apocrysis - knowledge interface commands (v4 Phase B / Stage 2C)
# File: src/mixins/knowledge_mixin.py
#
# The player-facing side of src/knowledge.py: `journal`, `remember`,
# `inspect`, `look`. Generalised out of SliceMixin's slice-scoped
# versions (which proved the shape in Stage 0).
#
# Principle (design doc, "Player cognition & information
# architecture"): the player must never be required to remember
# something the interface can preserve. `journal` is the durable
# record; `remember` synthesises current understanding as prose;
# `inspect` reports one thing's Observed/Known/Suspected/Unknown
# state. None of these promote knowledge - transitions are automatic.
# ============================================================

from src.knowledge import (
    Knowledge, KNOWN, OBSERVED,
    HYP_CONFIRMED, HYP_SUSPECTED,
)


class KnowledgeMixin:

    def ensure_knowledge(self):
        if not hasattr(self, 'knowledge') or self.knowledge is None:
            self.knowledge = Knowledge()
        return self.knowledge

    # ---- journal --------------------------------------------

    def knowledge_journal(self):
        k = self.ensure_knowledge()
        if k.is_empty():
            self.io.say("Your journal is empty. You haven't noted anything yet.")
            return
        self.io.say("== JOURNAL ==")
        self.io.say("Things you've found:")
        for eid, ev in k.evidence.items():
            if eid in k.found:
                self.io.say(f"  - {ev.text}")
        known = k.facts_known()
        if known:
            self.io.say("")
            self.io.say("What that tells you:")
            for fid, fact in k.facts.items():
                if fid in known:
                    self.io.say(f"  - {fact.statement}")
        observed = [f for f in k.facts.values() if k.fact_state(f.id) == OBSERVED]
        if observed:
            self.io.say("")
            self.io.say("Things you've seen but don't understand yet:")
            for fact in observed:
                self.io.say(f"  - {fact.statement}")

    # ---- remember ------------------------------------------

    def knowledge_remember(self):
        """Prose synthesis of current understanding - recalling what
        you know, not receiving a hint."""
        k = self.ensure_knowledge()
        known = k.facts_known()
        if not known:
            self.io.say(
                "You think it over. You have a few scraps and a lot of "
                "questions. Nothing adds up yet."
            )
            return

        parts = [d.text for d in k.deductions_available()]
        state = k.hypothesis_state()
        if k.hypothesis is not None:
            if state == HYP_CONFIRMED:
                parts.append("You've seen it for yourself: " + k.hypothesis.statement)
            elif state == HYP_SUSPECTED:
                parts.append("You're starting to think: " + k.hypothesis.statement)

        if not parts:
            # Facts known but nothing connects them yet.
            self.io.say("You go over what you know:")
            for fid in known:
                self.io.say(f"  {k.facts[fid].statement}")
            self.io.say("It's real, but it doesn't point anywhere yet.")
            return

        self.io.say("You think it through:")
        for p in parts:
            self.io.say(f"  {p}")

    # ---- inspect ------------------------------------------

    def knowledge_inspect(self, target):
        k = self.ensure_knowledge()
        target = (target or "").strip().lower()
        if not target:
            self.io.say("Inspect what? Name something you've come across.")
            return

        # The hypothesis / "the way out".
        if k.hypothesis is not None and (
            target in ("way out", "escape", "exit", "hypothesis")
            or target in k.hypothesis.statement.lower()
        ):
            state = k.hypothesis_state()
            label = {HYP_CONFIRMED: "Known", HYP_SUSPECTED: "Suspected"}.get(state, "Unknown")
            self.io.say(f"The way out - {label}.")
            if state == HYP_CONFIRMED:
                self.io.say(f"  {k.hypothesis.statement}")
            elif state == HYP_SUSPECTED:
                self.io.say(f"  You suspect: {k.hypothesis.statement}")
            else:
                self.io.say("  You've no idea how to get out of here yet.")
            return

        matches = [f for f in k.facts.values() if target in f.statement.lower()]
        if not matches:
            self.io.say(f"You've got nothing on '{target}'.")
            return
        for fact in matches:
            state = k.fact_state(fact.id)
            if state == KNOWN:
                self.io.say(f"{fact.statement} - Known.")
                for ev in k.evidence_for(fact.id):
                    self.io.say(f"  (from: {ev.text})")
            elif state == OBSERVED:
                self.io.say(f"{fact.statement} - Observed, but you don't know what it means yet.")
            else:
                self.io.say(f"{fact.statement} - Unknown.")

    # ---- look --------------------------------------------

    def knowledge_look(self):
        """Describe the current tile and what's visible from it. In the
        real game this is where 'observe'-method evidence is surfaced;
        subclasses/mixins that own location content override or extend
        _look_here()."""
        if hasattr(self, '_look_here'):
            self._look_here()
            return
        tile = self.map[self.current_position[1]][self.current_position[0]]
        terrain = tile.get('terrain') if isinstance(tile, dict) else None
        self.io.say(f"You take stock of your surroundings ({terrain or 'open ground'}).")
