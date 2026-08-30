# ============================================================
# Apocrysis - the investigation loop for procedurally generated
# mysteries (v4 Phase C / Stage 4)
# File: src/mixins/mystery_mixin.py
#
# The engine glue for src/escape.py's generated mysteries. Site
# arrival surfaces 'observe' evidence; `search` surfaces 'search'
# evidence and hands over the
# requirement item; `clear` opens the obstacle; `escape` wins if the
# hypothesis is confirmed and the obstacle is open.
# ============================================================

from src.escape import MECHANISMS
from src.items import Item


def _and_list(names):
    """['a', 'b'] -> 'the a and the b'; ['a'] -> 'the a'."""
    xs = [f"the {n}" for n in names]
    if len(xs) <= 1:
        return xs[0] if xs else ""
    return ", ".join(xs[:-1]) + (" and " if len(xs) == 2 else ", and ") + xs[-1]


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
        if MECHANISMS.get(m.mechanism, {}).get('deadline_turns'):
            # time-pressure: the tide state is the gate. Once you've
            # crossed, a later flood can't shut you back in.
            return m.obstacle_open or m.crossed
        if m.controls:
            return m.obstacle_open
        if m.power_role:
            return m.power_restored
        # transportation: a checklist - the machine runs once you're
        # carrying every part. Single-item mechanisms fall through the
        # same call (one-entry list).
        return self._mystery_has_all_items()

    def _mystery_required_items(self):
        """Every item this mechanism's obstacle needs. A list of one for
        the single-item families; two (or more) for transportation."""
        m = self._mystery()
        if m is None:
            return []
        return list(m.requirement_items) or (
            [m.requirement_item] if m.requirement_item else [])

    def _mystery_missing_items(self):
        have = {getattr(it, 'name', None) for it in self.backpack.items}
        return [n for n in self._mystery_required_items() if n not in have]

    def _mystery_has_all_items(self):
        req = self._mystery_required_items()
        return bool(req) and not self._mystery_missing_items()

    # ---- time-pressure family (tidal_causeway) --------------------

    def _mystery_arm_deadline(self):
        """Start the tide clock the turn the player learns the causeway
        exists (F_ROUTE known) - diegetic, not from spawn."""
        m = self._mystery()
        if m is None:
            return
        spec = MECHANISMS.get(m.mechanism, {})
        if not spec.get('deadline_turns') or m.deadline is not None or m.crossed:
            return
        m.deadline = spec['deadline_turns']
        self.announce_event(
            "the tide is going out",
            f"The causeway is clear now, but not for long - you've got "
            f"roughly {m.deadline} turns before the water's back over it. "
            "Don't stop for anything you don't need.",
            kind="lead")

    def _mystery_tide_tick(self):
        """Per-turn, from world_mixin.move_and_search right after decay.
        Runs the tide state machine for a tidal_causeway mystery; a
        no-op for everything else."""
        m = self._mystery()
        if m is None or m.escaped or m.crossed:
            return
        spec = MECHANISMS.get(m.mechanism, {})
        if not spec.get('deadline_turns'):
            return
        if m.tide_recovery > 0:
            # flooded - counting down to the next low tide
            m.tide_recovery -= 1
            if m.tide_recovery in (10, 5):
                self.io.say(f"The causeway's still under - about {m.tide_recovery} turns to low water.")
            if m.tide_recovery <= 0:
                m.tide_recovery = 0
                m.obstacle_open = True
                m.deadline = spec['deadline_turns']
                ox, oy = m.obstacle_tile
                cell = self.map[oy][ox]
                if isinstance(cell, dict):
                    cell['obstacle'] = False
                self.announce_event(
                    "THE TIDE IS OUT AGAIN",
                    "The water's pulled back off the causeway. Go now - "
                    f"you've got another {m.deadline} turns or so.",
                    kind="objective")
            return
        if m.deadline is None:
            return
        m.deadline -= 1
        if m.deadline == 10:
            self.io.say("The tide's on the turn - maybe 10 turns before the causeway floods.")
        elif m.deadline == 5:
            self.announce_event("the water's coming up",
                                "Five turns, give or take, before the causeway goes under.",
                                kind="warn")
        elif m.deadline == 2:
            self.announce_event("the causeway's about to flood",
                                "Two turns. If you're not across, you wait for the next tide.",
                                kind="warn")
        elif m.deadline <= 0:
            m.deadline = None
            m.obstacle_open = False
            m.tide_recovery = spec.get('flood_recovery', 24)
            ox, oy = m.obstacle_tile
            cell = self.map[oy][ox]
            if isinstance(cell, dict):
                cell['obstacle'] = True
            self.announce_event(
                "THE TIDE HAS TURNED",
                "The causeway's under water - no crossing it now. The next "
                f"low tide is roughly {m.tide_recovery} turns off, after dark. "
                "Find somewhere to wait it out.",
                kind="warn")

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

    def _mystery_heading(self, role):
        """Compass hint from the player to a mystery site - "it's
        marked on your map" isn't enough for a kid who can't read the
        ASCII map (playtest)."""
        m = self._mystery()
        xy = m.sites.get(role) if m else None
        if not xy:
            return ""
        px, py = self.current_position
        dx, dy = xy[0] - px, xy[1] - py
        ns = "north" if dy < -1 else "south" if dy > 1 else ""
        ew = "west" if dx < -1 else "east" if dx > 1 else ""
        d = "-".join(x for x in (ns, ew) if x)
        return f" ({d} of you)" if d else " (close by)"

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
            self._mystery_arm_deadline()
            if MECHANISMS.get(m.mechanism, {}).get('reveals_route'):
                # informational: F_ROUTE and 'confirmed' land in the same
                # beat here - the "YOU CAN LEAVE NOW" banner below says
                # everything, so don't double up.
                pass
            elif m.site_labels.get('route'):
                self.announce_event(f"the route is at {m.site_labels['route']}",
                                    "It's marked on your map now.", kind="lead")
        if 'F_POWER' in new_facts and m.site_labels.get('power'):
            _pdir = self._mystery_heading('power')
            if MECHANISMS.get(m.mechanism, {}).get('reveals_route'):
                self.announce_event(
                    f"the transmitter is fed from {m.site_labels['power']}",
                    f"Get it running and the outside can guide you out. It's{_pdir}, marked on your map.",
                    kind="lead")
            else:
                self.announce_event(
                    f"the way out is powered from {m.site_labels['power']}",
                    f"Sort out what's wrong there - it's{_pdir}, marked on your map.",
                    kind="lead")
        if 'F_REQUIRE' in new_facts and m.site_labels.get('require'):
            _rdir = self._mystery_heading('require')
            if m.controls:
                self.announce_event(
                    f"whatever clears the way is set from {m.site_labels['require']}",
                    f"You'll have to work out which control. It's{_rdir}, marked on your map.",
                    kind="lead")
            else:
                self.announce_event(
                    f"the {m.requirement_item} is kept at {m.site_labels['require']}",
                    f"It's{_rdir}, marked on your map.", kind="lead")

        now = k.hypothesis_state()
        if now != hyp_before and k.hypothesis is not None:
            if now == 'suspected':
                self.announce_event("a new idea about the way out",
                                    k.hypothesis.statement, kind="objective")
            elif now == 'confirmed':
                if m.obstacle_open:
                    # `escape` works from wherever you are now. A kid
                    # walked to the map marker and died one tile short
                    # (playtest) - say it loud, say you don't travel.
                    if MECHANISMS.get(m.mechanism, {}).get('reveals_route'):
                        body = ("The voice has you - you do NOT have to reach the ridge "
                                "yourself. Type `escape` right now and you're out.")
                    else:
                        body = ("The way's open and you know it leads out. Type `escape` "
                                "from here - no need to walk back to it.")
                    self.announce_event("YOU CAN LEAVE NOW",
                                        k.hypothesis.statement, body, kind="objective")
                else:
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
                if MECHANISMS.get(m.mechanism, {}).get('deadline_turns'):
                    # stood on the far side with the causeway open - the
                    # tide can't strand you now; stop the clock.
                    m.crossed = True
                    m.deadline = None
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
            if m.requirement_items:
                # transportation: name the machine, not "back to it" -
                # and mention the other part if it's still outstanding.
                _still = [n for n in self._mystery_required_items()
                          if n != m.requirement_item and n in self._mystery_missing_items()]
                _dest = (f"take it to {m.site_labels.get('route', 'the machine')}"
                         + (f" - you still need the {_still[0]} too" if _still else ""))
            self.announce_event(
                f"you have the {m.requirement_item}",
                f"This is what gets you past the blocked route - {_dest}.",
                kind="objective",
            )
        # transportation: the second parallel part, at the require2 site.
        if (role == 'require2' and 'E_require2_b' in m.knowledge.found
                and not m.obstacle_open):
            _item2 = self._mystery_required_items()[-1]
            if _item2 in self._mystery_missing_items():
                self.backpack.add_item(Item(_item2))
                _still = [n for n in self._mystery_missing_items() if n != _item2]
                _tail = (f" - you still need the {_still[0]}" if _still
                         else " - that's everything the plane needs")
                self.announce_event(
                    f"you have the {_item2}",
                    f"Take it to {m.site_labels.get('route', 'the machine')}{_tail}.",
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
                # transportation: same for the second store, once its
                # part is in the pack or already fitted.
                if (eid == 'E_require2_b' and m.requirement_items
                        and self._mystery_required_items()[-1] not in self._mystery_missing_items()):
                    continue
                self.io.say(f"  {m.knowledge.evidence[eid].text}")
            if role in ('require', 'require2') and m.requirement_items:
                _left = [] if m.obstacle_open else self._mystery_missing_items()
                self.io.say("  Nothing more to take here."
                            if not _left else
                            "  Nothing more here - you still need " + _and_list(_left) + ".")
            elif role == 'require' and _fix_done and m.requirement_item:
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
        elif m.requirement_items and not m.obstacle_open:
            _miss = self._mystery_missing_items()
            if _miss:
                self.io.say(
                    "You climb up and try the starter. Nothing. It still needs "
                    + _and_list(_miss) + " before it'll run.")
            else:
                self.io.say("You've got everything it needs - fit it and go.")
        elif MECHANISMS.get(m.mechanism, {}).get('deadline_turns') and not m.obstacle_open:
            self.io.say(
                "The causeway's under water - chest-deep and still coming up. "
                f"The next low tide is about {max(m.tide_recovery, 1)} turns off. "
                "Nothing to do here but wait it out somewhere safe.")
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
            elif m.requirement_items:
                _miss = self._mystery_missing_items()
                self.io.say("The plane still needs " + _and_list(_miss) + "."
                            if _miss else "The plane still won't start.")
            else:
                self.io.say(f"You can't get past it without the {m.requirement_item}.")
            return
        if not m.power_role:
            _consume = set(self._mystery_required_items()) or {m.requirement_item}
            self.backpack.items = [it for it in self.backpack.items
                                   if getattr(it, 'name', None) not in _consume]
        m.obstacle_open = True
        game_cell = self.map[oy][ox]
        if isinstance(game_cell, dict):
            game_cell['obstacle'] = False
        if m.power_role:
            _how = "The gate has power now. It grinds open."
        elif m.requirement_items:
            _how = MECHANISMS.get(m.mechanism, {}).get(
                'assemble_desc', "You fit the parts. The machine is ready.")
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
        _open = m.obstacle_open or m.crossed
        # Once you've stood at the way out and it's open, you don't have
        # to be standing on it to leave - `escape` means "go there and
        # go." Playtest: solved the whole mystery, then starved on the
        # trek back to the exit tile. The investigation is the game;
        # the walk back is not.
        if not on_tile and not (confirmed and _open):
            self.io.say(
                "You're not anywhere you could leave from. If there's a "
                "way out you haven't reached it yet."
            )
            return
        if not _open:
            self.io.say(
                "The causeway's under water - wait for the tide."
                if MECHANISMS.get(m.mechanism, {}).get('deadline_turns')
                else "The way is still blocked behind you.")
            return
        if not confirmed:
            self.io.say(
                "You could start walking. But you're not certain this "
                "goes anywhere - better to be sure first."
            )
            return
        if not on_tile:
            self.io.say(
                "You follow the directions off the ridge and keep going."
                if MECHANISMS.get(m.mechanism, {}).get('reveals_route')
                else "You make your way back to the pass and start walking.")
            self._update_time(90)
        m.escaped = True
        # A.3: a resolved mystery explicitly tagged with a WorldFact
        # marks that fact KNOWN. Deliberately simple - one isolated
        # transition, so evidence/provenance logic can replace it later
        # without touching anything else. See PHASE_A3_INVESTIGATION.md.
        _milestone_line = None
        _correction = None
        if getattr(m, 'world_fact_id', None) and getattr(self, 'world_investigation', None):
            _wi = self.world_investigation
            _fid = m.world_fact_id
            _was_known = _wi.is_known(_fid)
            _wi.mark_known(_fid)
            self.__class__._world_investigation = _wi.snapshot()['status']
            if not _was_known:
                # E.1: discovering this fact may break a rung of the
                # regional wrong-assumptions ladder - the "you had it
                # wrong" beat. Fires once (a fact flips not-known->known
                # once, campaign-wide).
                _rung = _wi.hypothesis_broken_by(_fid)
                if _rung is not None:
                    _correction = _rung
                # A.5.2: what this expedition changed, for the retrospective
                _learned = list(getattr(self, '_expedition_learned', []))
                _learned.append(_fid)
                self._expedition_learned = _learned
                # A.4.4: milestone banner - fires exactly once, on the
                # not-KNOWN -> KNOWN transition of a milestone=True fact.
                # Announced AFTER the "found the way out" texture below
                # (A.5.3), so the beats read solved -> texture -> milestone.
                _fact = _wi.fact(_fid)
                if _fact is not None and _fact.milestone:
                    _milestone_line = _fact.statement
        used = getattr(self.__class__, '_used_mechanisms', None)
        if used is None:
            used = self.__class__._used_mechanisms = []
        if m.mechanism not in used:
            used.append(m.mechanism)
        # schema invariant 3a: the next expedition avoids this family
        self.__class__._last_family = m.family
        # variety rules B + C: keep the last 2 mechanisms and the last 2
        # story signatures so the generator can steer away from them.
        from src.escape import story_signature
        _rm = list(getattr(self.__class__, '_recent_mechanisms', []) or [])
        _rm.append(m.mechanism)
        self.__class__._recent_mechanisms = _rm[-2:]
        _rs = list(getattr(self.__class__, '_recent_signatures', []) or [])
        _rs.append(story_signature(m.mechanism))
        self.__class__._recent_signatures = _rs[-2:]
        _stmt = m.knowledge.hypothesis.statement.rstrip('.')
        # A.5.3: the signpost beat - MYSTERY SOLVED - then the texture
        # prose, then (if any) the milestone. One coherent hierarchy.
        _mech_name = MECHANISMS.get(m.mechanism, {}).get('name', 'the way out')
        self.announce_event(_mech_name, f"{_stmt}.", kind="solved")
        if MECHANISMS.get(m.mechanism, {}).get('reveals_route'):
            self.io.say(
                f"\nYou found the way out - {_stmt}. You worked out that "
                "someone was still listening, brought the tower back, and "
                "the voice on the other end brought you a road.\n")
        else:
            self.io.say(
                f"\nYou found the way out - {_stmt}. "
                "Not because anything told you, but because you worked out "
                "what this place was and where it had to give.\n")
        if _milestone_line is not None:
            self.announce_event(_milestone_line, kind="milestone")
        if _correction is not None:
            # E.1: the reframe - what you were sure of, and what it
            # actually was.
            self.announce_event(_correction.statement,
                                _correction.corrected_to, kind="correction")
        # B.2: solving this mechanism may teach a Survivor Knowledge
        # lesson that carries to the next survivor. learn() is True only
        # the first time - one banner ever, campaign-wide.
        _lore_id = self.world.lore_triggers.get(m.mechanism)
        if _lore_id and getattr(self, 'survivor_knowledge', None) is not None:
            if self.survivor_knowledge.learn(_lore_id):
                self.__class__._survivor_knowledge = self.survivor_knowledge.snapshot()
                _lo = {lo.id: lo for lo in self.world.survivor_lore}.get(_lore_id)
                if _lo is not None:
                    self.announce_event(_lo.blurb, _lo.effect, kind="lore")
                    _ll = list(getattr(self, '_expedition_lore_learned', []))
                    _ll.append(_lore_id)
                    self._expedition_lore_learned = _ll
        self.finish_expedition(reason="found the way out")
