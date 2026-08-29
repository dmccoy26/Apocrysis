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

from src.escape import MECHANISMS
from src.items import Item


class MysteryMixin:

    def _mystery(self):
        return getattr(self, 'mystery', None)

    def _mystery_obstacle_ready(self):
        """Can the obstacle be opened? For a plain (spatial) mystery
        that's 'do you carry the requirement item'; for the
        infrastructural family it's 'is the dependency satisfied'
        (m.power_restored) - the item was consumed elsewhere."""
        m = self._mystery()
        if m is None:
            return False
        if m.power_role:
            return m.power_restored
        return self._mystery_has_item()

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

    def _mystery_progress_flare(self, hyp_before, facts_before):
        """Banner the investigation beats so they don't slide past in
        the scenery (playtest: "the game didn't tell me my problem had
        changed"). Call with the hypothesis state AND facts_known set
        captured BEFORE an evidence-revealing action.
          NEW LEAD       - learned where the route / the requirement is;
                           that place is now marked on the map
          OBJECTIVE ...  - the hypothesis moved (suspected / confirmed)
        """
        m = self._mystery()
        if m is None:
            return
        k = m.knowledge
        new_facts = k.facts_known() - set(facts_before)
        if 'F_ROUTE' in new_facts and m.site_labels.get('route'):
            self.announce_event(f"the route is at {m.site_labels['route']}",
                                "It's marked on your map now.", kind="lead")
        if 'F_POWER' in new_facts and m.site_labels.get('power'):
            self.announce_event(
                f"the way out is powered from {m.site_labels['power']}",
                "You'll have to sort out what's wrong there. Marked on your map.",
                kind="lead")
        if 'F_REQUIRE' in new_facts and m.site_labels.get('require'):
            self.announce_event(
                f"the {m.requirement_item} is kept at {m.site_labels['require']}",
                "It's marked on your map now.", kind="lead")

        now = k.hypothesis_state()
        if now != hyp_before and k.hypothesis is not None:
            if now == 'suspected':
                self.announce_event("a new idea about the way out",
                                    k.hypothesis.statement, kind="objective")
            elif now == 'confirmed':
                self.announce_event("escape route confirmed",
                                    k.hypothesis.statement,
                                    "Get to it and type `escape`.", kind="objective")

    def mystery_arrive(self, x, y):
        m = self._mystery()
        if m is None:
            return
        role = self._mystery_role_at(x, y)
        if role is None:
            return
        _hyp_before = m.knowledge.hypothesis_state()
        _facts_before = set(m.knowledge.facts_known())

        if role == 'escape':
            if m.obstacle_open and not m.escaped:
                self._mystery_reveal('E_confirm')
                self._mystery_progress_flare(_hyp_before, _facts_before)
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
            _pl = m.site_labels.get('power', 'where it is needed')
            _dest = "head back to it" if not m.power_role else f"take it to {_pl}"
            self.announce_event(
                f"you have the {m.requirement_item}",
                f"This is what gets you past the blocked route - {_dest}.",
                kind="objective",
            )
        # Infrastructural: applying the fix at the dependency site.
        if role == m.power_role and not m.power_restored and self._mystery_has_item():
            self.backpack.items = [it for it in self.backpack.items
                                   if getattr(it, 'name', None) != m.requirement_item]
            m.power_restored = True
            self.announce_event(
                "the generator is running",
                MECHANISMS[m.mechanism].get(
                    'power_restored_desc', "The way out has power now."),
                kind="objective",
            )
        self._mystery_progress_flare(_hyp_before, _facts_before)

    def mystery_bump_obstacle(self):
        m = self._mystery()
        if m is None:
            return
        _hyp_before = m.knowledge.hypothesis_state()
        _facts_before = set(m.knowledge.facts_known())
        m.saw_obstacle = True
        revealed = False
        for eid in m._site_evidence.get('obstacle', []):
            revealed = self._mystery_reveal(eid) or revealed
        if m.power_role and not m.power_restored and self._mystery_has_item():
            # The failed action teaches the dependency, doesn't just
            # reject: the fuel belongs somewhere else.
            self.io.say(
                f"You have the {m.requirement_item}. The gate is electrically "
                f"operated - there's nowhere to use it here.")
        elif not revealed:
            self.io.say("It's still blocked. You need the way past it first.")
        self._mystery_progress_flare(_hyp_before, _facts_before)

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
        _facts_before = set(m.knowledge.facts_known())
        any_new = False
        for eid in m._site_evidence.get(role, []):
            if self._mystery_reveal(eid):
                any_new = True
        if role == 'require' and 'E_require_b' in m.knowledge.found and not self._mystery_has_item():
            self.backpack.add_item(Item(m.requirement_item))
            self.announce_event(
                f"you have the {m.requirement_item}",
                "This is what gets you past the blocked route - head back to it.",
                kind="objective",
            )
        elif not any_new:
            self.io.say("You've already been over this place. Check `journal` for what you found.")
        self._mystery_progress_flare(_hyp_before, _facts_before)

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
        if not self._mystery_obstacle_ready():
            if m.power_role:
                self.io.say("The gate has no power. Nothing you do here changes that.")
            else:
                self.io.say(f"You can't get past it without the {m.requirement_item}.")
            return
        if not m.power_role:
            self.backpack.items = [it for it in self.backpack.items
                                   if getattr(it, 'name', None) != m.requirement_item]
        m.obstacle_open = True
        game_cell = self.map[oy][ox]
        if isinstance(game_cell, dict):
            game_cell['obstacle'] = False
        if m.power_role:
            _how = "The gate has power now. It grinds open."
        else:
            _how = (f"You come back with the {m.requirement_item}. It works."
                    if m.saw_obstacle else f"The {m.requirement_item} does it.")
        self.announce_event("the way is open", _how,
                            "The route ahead is clear - keep going.", kind="objective")

    def mystery_try_escape(self):
        m = self._mystery()
        if m is None:
            self.io.say("There's no way out from here that you know of.")
            return
        if m.escaped:
            self.io.say("You're already out.")
            return
        confirmed = m.knowledge.hypothesis_state() == 'confirmed'
        on_tile = self.current_position == m.escape_tile
        # Once you've stood at the way out and it's open, you don't have
        # to be standing on it to leave - `escape` means "go there and
        # go." Playtest: solved the whole mystery, then starved on the
        # trek back to the exit tile. The investigation is the game;
        # the walk back is not.
        if not on_tile and not (confirmed and m.obstacle_open):
            self.io.say(
                "You're not anywhere you could leave from. If there's a "
                "way out you haven't reached it yet."
            )
            return
        if not m.obstacle_open:
            self.io.say("The way is still blocked behind you.")
            return
        if not confirmed:
            self.io.say(
                "You could start walking. But you're not certain this "
                "goes anywhere - better to be sure first."
            )
            return
        if not on_tile:
            self.io.say("You make your way back to the pass and start walking.")
            self._update_time(90)
        m.escaped = True
        used = getattr(self.__class__, '_used_mechanisms', None)
        if used is None:
            used = self.__class__._used_mechanisms = []
        if m.mechanism not in used:
            used.append(m.mechanism)
        # schema invariant 3a: the next expedition avoids this family
        self.__class__._last_family = m.family
        self.io.say(
            f"\nYou found the way out - {m.knowledge.hypothesis.statement.rstrip('.')}. "
            "Not because anything told you, but because you worked out "
            "what this place was and where it had to give.\n"
        )
        self.finish_expedition(reason="found the way out")
