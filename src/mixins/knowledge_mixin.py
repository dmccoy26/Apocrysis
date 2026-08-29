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
            m = getattr(self, 'mystery', None)
            if m and getattr(m, 'controls', None) and 'F_REQUIRE' in known and not m.obstacle_open:
                self.io.say('The controls at ' + m.site_labels.get('require', 'the control room') + ' are the way through - you will have to try them one at a time.')
                return
            elif m and getattr(m, 'power_role', None) and not m.power_restored and self._mystery_has_item() and 'F_POWER' in known:
                self.io.say('You have got the ' + str(m.requirement_item) + '. The power for the way out comes from ' + m.site_labels.get('power', 'the power source') + ' - that is where it goes.')
                return
            elif m and getattr(m, 'power_role', None) and not m.power_restored and not self._mystery_has_item() and 'F_POWER' in known and 'F_REQUIRE' in known:
                self.io.say('The way out is dead without power from ' + m.site_labels.get('power', 'the power source') + ', and that needs the ' + str(m.requirement_item or 'part') + ' from ' + m.site_labels.get('require', 'the store') + '.')
                return
            elif m and getattr(m,'power_role',None) and m.power_restored and 'F_ROUTE' not in known:
                self.io.say('The gate has power now. You still have to find where the route comes through - keep looking.')
                return
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

    # ---- v4 command routing (generated mystery) ----

    def _v4_search(self):
        if getattr(self, 'mystery', None) is not None:
            self.mystery_search()
        else:
            self.io.say("You search around. Nothing here means anything.")

    def _v4_escape(self):
        if getattr(self, 'mystery', None) is not None:
            self.mystery_try_escape()
        else:
            self.io.say("There's no way out from here that you know of.")

    def _v4_clear(self):
        if getattr(self, 'mystery', None) is not None:
            self.mystery_clear_obstacle()
        else:
            self.io.say("There's nothing here to clear or open.")

    # ---- look --------------------------------------------

    def knowledge_look(self):
        """Describe the current tile and re-surface any 'observe'
        evidence here."""
        x, y = self.current_position
        tile = self.map[y][x]
        terrain = tile.get('terrain') if isinstance(tile, dict) else None
        cause = tile.get('abandonment') if isinstance(tile, dict) else None

        m = getattr(self, 'mystery', None)
        if m is not None:
            role = self._mystery_role_at(x, y) if hasattr(self, '_mystery_role_at') else None
            if role:
                # re-run the arrival observe pass (discover() is
                # idempotent - only new evidence prints)
                self.mystery_arrive(x, y)
                return

        if terrain == 'building':
            self.io.say("A building. Empty. " + (
                {'evacuated': "They left in a hurry.", 'barricaded': "Boarded up from inside.",
                 'burned': "Fire-damaged.", 'looted': "Already stripped.",
                 'occupied_recently': "Someone was here not long ago.", 'sealed': "Sealed from outside.",
                 'flooded': "Water damage.", 'quiet': "Just left, undisturbed."}.get(cause, "")))
        elif terrain == 'town':
            self.io.say("A settlement street. Quiet.")
        else:
            self.io.say(f"Open {terrain or 'ground'}. Nothing here that matters.")
