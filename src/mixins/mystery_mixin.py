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
        """Can the obstacle be opened by walking into it?
          spatial        - do you carry the requirement item
          infrastructural - is the dependency satisfied (m.power_restored)
          experimental   - never here; it opens from the control room
                           via `pull` (m.obstacle_open mirrors that)"""
        m = self._mystery()
        if m is None:
            return False
        if m.controls:
            return m.obstacle_open
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

    def _mystery_after_power_restored(self):
        """Informational family (reveals_route): restoring the system
        doesn't open a gate - it produces a response that names a route
        the player could not have found. F_ROUTE lands here, via
        E_route_reveal; there is no physical obstacle to clear, so
        obstacle_open flips too. The `★` banner is fired by
        _mystery_progress_flare seeing F_ROUTE newly known."""
        m = self._mystery()
        if m is None:
            return
        if MECHANISMS.get(m.mechanism, {}).get('reveals_route'):
            self._mystery_reveal('E_route_reveal')
            m.obstacle_open = True

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
        if 'F_ROUTE' in new_facts:
            if MECHANISMS.get(m.mechanism, {}).get('reveals_route'):
                # informational: the response named a route that was
                # never on the map. It's the way out now - and there is
                # nothing left to clear.
                self.announce_event(
                    "the way out",
                    "The voice on the channel talked you onto it - it's marked on your map now.",
                    kind="objective")
            elif m.site_labels.get('route'):
                self.announce_event(f"the route is at {m.site_labels['route']}",
                                    "It's marked on your map now.", kind="lead")
        if 'F_POWER' in new_facts and m.site_labels.get('power'):
            if MECHANISMS.get(m.mechanism, {}).get('reveals_route'):
                self.announce_event(
                    f"the transmitter is fed from {m.site_labels['power']}",
                    "Get it running and the outside can guide you out. Marked on your map.",
                    kind="lead")
            else:
                self.announce_event(
                    f"the way out is powered from {m.site_labels['power']}",
                    "You'll have to sort out what's wrong there. Marked on your map.",
                    kind="lead")
        if 'F_REQUIRE' in new_facts and m.site_labels.get('require'):
            if m.controls:
                self.announce_event(
                    f"whatever clears the way is set from {m.site_labels['require']}",
                    "You'll have to work out which control. Marked on your map.",
                    kind="lead")
            else:
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
        if (role == 'require' and m.requirement_item and 'E_require_b' in m.knowledge.found
                and not self._mystery_has_item()
                and not m.obstacle_open and not m.power_restored):
            # ...but not once the fix is already done - revisiting the
            # depot shouldn't re-hand a jerrycan you already used.
            self.backpack.add_item(Item(m.requirement_item))
            _pl = m.site_labels.get('power', 'where it is needed')
            _dest = "head back to it" if not m.power_role else f"take it to {_pl}"
            self.announce_event(
                f"you have the {m.requirement_item}",
                f"This is what gets you past the blocked route - {_dest}.",
                kind="objective",
            )
        # Infrastructural: applying the fix at the dependency site.
        power_restore_fired = False
        if role == m.power_role and not m.power_restored and self._mystery_has_item():
            self.backpack.items = [it for it in self.backpack.items
                                   if getattr(it, 'name', None) != m.requirement_item]
            m.power_restored = True
            power_restore_fired = True
            self.announce_event(
                "the generator is running",
                MECHANISMS[m.mechanism].get(
                    'power_restored_desc', "The way out has power now."),
                kind="objective",
            )
            self._mystery_after_power_restored()
        self._mystery_progress_flare(_hyp_before, _facts_before)

        if not any_new and not power_restore_fired and role in m.sites and role != 'escape':
            label = m.site_labels.get(role)
            if label:
                self.io.say(f"{label.capitalize()}.")
            _fix_done = m.obstacle_open or m.power_restored
            for eid in m._site_evidence.get(role, []):
                if eid not in m.knowledge.found:
                    continue
                # "You find the jerrycan here" reads wrong once you've
                # taken it and used it - skip that one line on revisit.
                if eid == 'E_require_b' and _fix_done and m.requirement_item:
                    continue
                self.io.say(f"  {m.knowledge.evidence[eid].text}")
            if role == 'require' and _fix_done and m.requirement_item:
                self.io.say("  Nothing more to take here - you've already got what this place had.")
            if m.controls and role == 'require' and not m.obstacle_open:
                self.io.say("  Work them one at a time - pull <name> and watch the reservoir.")
            elif m.power_role and role == 'power' and not m.power_restored and not self._mystery_has_item():
                self.io.say(f"  The generator needs the {m.requirement_item} - it is kept at {m.site_labels.get('require', 'the store')}.")

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
        _reveals = MECHANISMS.get(m.mechanism, {}).get('reveals_route')
        if _reveals and not m.power_restored:
            self.io.say(
                "There's nothing to force here. No way out of the valley "
                "comes clear until the transmitter is back up and the "
                "outside answers."
                + (f" The {m.requirement_item} goes to {m.site_labels.get('power', 'the generator')}."
                   if self._mystery_has_item() else ""))
        elif m.power_role and not m.power_restored and self._mystery_has_item():
            # The failed action teaches the dependency, doesn't just
            # reject: the fuel belongs somewhere else.
            self.io.say(
                f"You have the {m.requirement_item}. The gate is electrically "
                f"operated - there's nowhere to use it here.")
        elif m.controls and not m.obstacle_open:
            self.io.say(
                "Too deep to wade, and nothing to move here. Whatever holds "
                "this water back is set from the control room, not here.")
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
        if (role == 'require' and m.requirement_item and 'E_require_b' in m.knowledge.found
                and not self._mystery_has_item()
                and not m.obstacle_open and not m.power_restored):
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

    def mystery_pull_control(self, arg):
        """Experimental family: `pull <control>` at the control room.
        The evidence never lied - the player's reading of it did. The
        obvious control is wrong and says WHY; the player revises and
        tries again. The right one opens the obstacle from here."""
        m = self._mystery()
        if m is None or not m.controls:
            self.io.say("There's nothing here to pull.")
            return
        role = self._mystery_role_at(*self.current_position)
        if role != 'require':
            self.io.say("The controls for that are back at the control room.")
            return
        arg = (arg or "").strip().lower()
        match = next((c for c in m.controls
                      if arg and (arg in c.lower() or c.lower() in arg)), None)
        if match is None:
            self.io.say("The controls here: " + ", ".join(m.controls)
                        + ".  (try `pull <name>`)")
            return
        if m.obstacle_open:
            self.io.say("The water's already down. No need to touch anything else.")
            return
        spec = MECHANISMS[m.mechanism]
        if match == m.correct_control:
            m.obstacle_open = True
            ox, oy = m.obstacle_tile
            cell = self.map[oy][ox]
            if isinstance(cell, dict):
                cell['obstacle'] = False
            self.announce_event("the way is open", spec['control_correct'],
                                "The lower road is clear - go.", kind="objective")
        else:
            if match not in m.controls_tried:
                m.controls_tried.append(match)
            key = ('control_wrong_obvious' if match == spec.get('obvious_control')
                   else 'control_wrong_other')
            self.io.say(spec[key])

    def mystery_apply_fix(self, arg):
        """Infrastructural family: an explicit verb (`use fuel` / `fill
        generator` / `refuel`) for applying the requirement item at the
        power site. Arriving there with the item already does this
        automatically (mystery_arrive); this is the same effect for a
        player who reaches for a verb instead, and a forward pointer if
        it's already done."""
        m = self._mystery()
        if m is None or not getattr(m, 'power_role', None):
            self.io.say("Nothing here to do that with.")
            return
        role = self._mystery_role_at(*self.current_position)
        _reveals = MECHANISMS.get(m.mechanism, {}).get('reveals_route')
        if m.power_restored:
            self.io.say("The transmitter's already up - the outside told you where to go. Follow it."
                        if _reveals
                        else "The generator is already running. The way out "
                             "has power - now reach the route.")
            return
        if role != m.power_role:
            self.io.say("Nowhere to use that here. It goes to "
                        + m.site_labels.get('power', 'the power source') + ".")
            return
        if not self._mystery_has_item():
            self.io.say("You have nothing to run it on.")
            return
        self.backpack.items = [it for it in self.backpack.items
                               if getattr(it, 'name', None) != m.requirement_item]
        m.power_restored = True
        self.announce_event(
            "the generator is running",
            MECHANISMS[m.mechanism].get(
                'power_restored_desc', "The way out has power now."),
            kind="objective",
        )
        _hyp_before = m.knowledge.hypothesis_state()
        _facts_before = set(m.knowledge.facts_known())
        self._mystery_after_power_restored()
        self._mystery_progress_flare(_hyp_before, _facts_before)

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
