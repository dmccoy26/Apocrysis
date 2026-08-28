# ============================================================
# Apocrysis - the investigation loop for procedurally generated
# mysteries (v4 Phase C / Stage 4)
# File: src/mixins/mystery_mixin.py
#
# The engine glue for src/escape.py's generated mysteries - the
# non-slice equivalent of SliceMixin. Site arrival surfaces 'observe'
# evidence; `search` surfaces 'search' evidence and hands over the
# requirement item; `clear` opens the obstacle; `escape` wins if the
# hypothesis is confirmed and the obstacle is open.
# ============================================================

from src.items import Item


class MysteryMixin:

    def _mystery(self):
        return getattr(self, 'mystery', None)

    def _mystery_role_at(self, x, y):
        m = self._mystery()
        if m is None:
            return None
        for role, xy in m.sites.items():
            if xy == (x, y):
                return role
        if m.escape_tile == (x, y):
            return 'escape'
        return None

    def _mystery_has_item(self):
        m = self._mystery()
        return m is not None and any(
            getattr(it, 'name', None) == m.requirement_item
            for it in self.backpack.items
        )

    def _mystery_reveal(self, evidence_id):
        m = self._mystery()
        if m and m.knowledge.discover(evidence_id):
            self.io.say(m.knowledge.evidence[evidence_id].text)
            return True
        return False

    # ---- arrival (from world_mixin.move_and_search) ----------

    def _mystery_hyp_flare(self, before_state):
        """Emphasise a hypothesis state change (unknown -> suspected ->
        confirmed) instead of letting it slide past in the scenery.
        Call with the state captured BEFORE an evidence-revealing action."""
        m = self._mystery()
        if m is None:
            return
        now = m.knowledge.hypothesis_state()
        if now == before_state or m.knowledge.hypothesis is None:
            return
        if now == 'suspected':
            self.announce_event("A new idea about the way out.",
                                m.knowledge.hypothesis.statement)
        elif now == 'confirmed':
            self.announce_event("Escape route confirmed.",
                                m.knowledge.hypothesis.statement,
                                "Get to it and type `escape`.")

    def mystery_arrive(self, x, y):
        m = self._mystery()
        if m is None:
            return
        role = self._mystery_role_at(x, y)
        if role is None:
            return
        _hyp_before = m.knowledge.hypothesis_state()

        if role == 'escape':
            if m.obstacle_open and not m.escaped:
                self._mystery_reveal('E_confirm')
                self._mystery_hyp_flare(_hyp_before)
                if m.knowledge.hypothesis_state() == 'confirmed':
                    self.io.say("(Type `escape` to leave.)")
            return

        # Name the place - the evidence chain refers to these names
        # ("the fuel is in the harbourmaster's shed"), so recognising
        # one on arrival is how the player connects a clue to a
        # destination without searching every building.
        label = m.site_labels.get(role)
        if label and role not in getattr(self, '_mystery_named', set()):
            named = getattr(self, '_mystery_named', None)
            if named is None:
                named = self._mystery_named = set()
            named.add(role)
            self.io.say(f"This is {label}.")

        # Arriving at a meaningful location IS the investigation. Both
        # observed and searched evidence surface now - no separate
        # `search` step (it was ceremony, not a decision). The require
        # site also hands over the requirement item.
        any_new = False
        for eid in m._site_evidence.get(role, []):
            if self._mystery_reveal(eid):
                any_new = True
        if role == 'require' and 'E_require_b' in m.knowledge.found and not self._mystery_has_item():
            self.backpack.add_item(Item(m.requirement_item))
            self.announce_event(
                f"You have the {m.requirement_item}.",
                "This is what gets you past the blocked route. Head back to it.",
            )
        self._mystery_hyp_flare(_hyp_before)

    def mystery_bump_obstacle(self):
        m = self._mystery()
        if m is None:
            return
        _hyp_before = m.knowledge.hypothesis_state()
        m.saw_obstacle = True
        revealed = False
        for eid in m._site_evidence.get('obstacle', []):
            revealed = self._mystery_reveal(eid) or revealed
        if not revealed:
            self.io.say("It's still blocked. You need the way past it first.")
        self._mystery_hyp_flare(_hyp_before)

    # ---- commands ------------------------------------------

    def mystery_search(self):
        """`search` still exists for a deliberate second look, but at a
        mystery site everything already surfaced on arrival - so this
        mostly just confirms there's nothing more, or picks up the
        requirement item if arrival somehow missed it."""
        m = self._mystery()
        if m is None:
            self.io.say("You look around properly. Nothing here that means anything.")
            return
        role = self._mystery_role_at(*self.current_position)
        if role is None or role == 'escape':
            self.io.say("You look around properly. Nothing here that means anything.")
            return

        _hyp_before = m.knowledge.hypothesis_state()
        any_new = False
        for eid in m._site_evidence.get(role, []):
            if self._mystery_reveal(eid):
                any_new = True
        if role == 'require' and 'E_require_b' in m.knowledge.found and not self._mystery_has_item():
            self.backpack.add_item(Item(m.requirement_item))
            self.announce_event(
                f"You have the {m.requirement_item}.",
                "This is what gets you past the blocked route. Head back to it.",
            )
        elif not any_new:
            self.io.say("You've already been over this place. Check `journal` for what you found.")
        self._mystery_hyp_flare(_hyp_before)

    def mystery_clear_obstacle(self):
        m = self._mystery()
        if m is None:
            self.io.say("There's nothing here to clear.")
            return
        ox, oy = m.obstacle_tile
        px, py = self.current_position
        if max(abs(px - ox), abs(py - oy)) > 1:
            self.io.say("There's nothing here to clear or open.")
            return
        if m.obstacle_open:
            self.io.say("It's already open.")
            return
        if not self._mystery_has_item():
            self.io.say(f"You can't get past it without the {m.requirement_item}.")
            return
        self.backpack.items = [it for it in self.backpack.items
                               if getattr(it, 'name', None) != m.requirement_item]
        m.obstacle_open = True
        game_cell = self.map[oy][ox]
        if isinstance(game_cell, dict):
            game_cell['obstacle'] = False
        _how = (f"You come back with the {m.requirement_item}. It works."
                if m.saw_obstacle else f"The {m.requirement_item} does it.")
        self.announce_event("The way is open.", _how, "The route ahead is clear - keep going.")

    def mystery_try_escape(self):
        m = self._mystery()
        if m is None:
            self.io.say("There's no way out from here that you know of.")
            return
        if m.escaped:
            self.io.say("You're already out.")
            return
        if self.current_position != m.escape_tile:
            self.io.say(
                "You're not anywhere you could leave from. If there's a "
                "way out you haven't reached it yet."
            )
            return
        if not m.obstacle_open:
            self.io.say("The way is still blocked behind you.")
            return
        if m.knowledge.hypothesis_state() != 'confirmed':
            self.io.say(
                "You could start walking. But you're not certain this "
                "goes anywhere - better to be sure first."
            )
            return
        m.escaped = True
        used = getattr(self.__class__, '_used_mechanisms', None)
        if used is None:
            used = self.__class__._used_mechanisms = []
        if m.mechanism not in used:
            used.append(m.mechanism)
        self.io.say(
            f"\nYou found the way out - {m.knowledge.hypothesis.statement.rstrip('.')}. "
            "Not because anything told you, but because you worked out "
            "what this place was and where it had to give.\n"
        )
        self.finish_expedition(reason="found the way out")
