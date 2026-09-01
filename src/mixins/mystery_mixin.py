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

    # ---- objective lifecycle (docs/DESIGN_SPATIAL_LANGUAGE.md) --------
    # The mystery IS the objective. "progress" = the investigation
    # advanced this turn (a fact learned, a site reached, the item
    # picked up, the way opened, the hypothesis firmed). Turns with no
    # progress accumulate; long enough without progress and the game
    # resurfaces the next step - once at REMINDER (a quiet line), again
    # at URGENT (a banner) when a real cost is also in play. Any
    # progress silently returns the state to ACTIVE.
    _OBJ_DISTRACTED_AFTER = 12
    _OBJ_REMINDER_AFTER = 20
    _OBJ_URGENT_AFTER = 34

    def _objective_sig(self):
        m = self._mystery()
        if m is None:
            return None
        k = m.knowledge
        return (len(k.found), bool(m.obstacle_open), bool(m.power_restored),
                self._mystery_has_item(), k.hypothesis_state())

    def _objective_ready_to_leave(self):
        """1d Finding F: True once every requirement is met and the
        route is confirmed - the DISCOVER/COLLECT phase is done and all
        that's left is walking to the exit. This transition used to be
        invisible; the HUD flips to ✦ ESCAPE READY on it."""
        m = self._mystery()
        if m is None or getattr(m, "escaped", False):
            return False
        if not getattr(m, "obstacle_open", False):
            return False
        k = getattr(m, "knowledge", None)
        return bool(k and k.hypothesis_state() == "confirmed")

    def _escape_ready_reassert(self):
        """P1-b (docs/PHASE_P1_COMMITMENT_INTERVENTION_SPEC.md §3.3).
        SESSION 2 N-6: `✦ ESCAPE READY` showed for 83 turns and the
        player explored and died in-map. The one-time transition beat is
        already fired by `_mystery_progress_flare` ("YOU CAN LEAVE NOW").
        This is the missing REASSERTION - deliberately NOT a turn timer:
        healthy curiosity is legitimate gameplay (the c1..c5 clues ARE
        the payload). Fires only when ready-to-leave AND survival margin
        is degrading AND the player just walked away from the exit."""
        if not hasattr(self.io, "ask_commit"):
            return                       # interactive-only, bot log clean
        m = self._mystery()
        if m is None or getattr(m, "escaped", False):
            self._ready_since = None
            return
        if not self._objective_ready_to_leave():
            self._ready_since = None
            return
        route = m.sites.get("route")
        if not route:
            return
        px, py = self.current_position
        dist = abs(route[0] - px) + abs(route[1] - py)
        prev = getattr(self, "_route_dist_prev", None)
        self._route_dist_prev = dist

        turns = getattr(self, "turns", 0)
        if getattr(self, "_ready_since", None) is None:
            # the transition banner already owns the moment the way opens;
            # start the reassert clock here, don't double up.
            self._ready_since = turns
            return

        degrading = (self.fatigue > 55
                     or self.backpack.water == 0
                     or self.health < self.max_health * 0.5)
        moved_away = prev is not None and dist > prev
        if not (degrading and moved_away):
            return
        st = self._gate_state().get("escape_reassert", {})
        if turns - st.get("turn", -10**9) < 8:
            return
        from src.nav import bearing
        b = bearing(self.current_position, route)
        self.announce_event(
            "ESCAPE REMINDER",
            "You already have what you came for. The way out is "
            + (f"to the {b}" if b else "close") + ".",
            kind="discovery", level=1)
        self._gate_state()["escape_reassert"] = {"turn": turns}

    def _objective_next_step(self):
        """A short plain-text 'what's left' line, from mystery state
        only - no tui / markup dependency."""
        m = self._mystery()
        if m is None:
            return f"find the way out of {self.world.prose.get('region_noun', 'here')}"
        known = m.knowledge.facts_known()
        labels = getattr(m, "site_labels", {})
        named = getattr(self, "_mystery_named", set())
        # 1d Finding F: everything's done - this is now a navigation
        # task, not an investigation one. Voice it that way.
        if self._objective_ready_to_leave():
            _dest = labels.get("route") or getattr(m, "mech_name", "the way out")
            return f"the way out is open - get to {_dest} and leave"
        _info = MECHANISMS.get(m.mechanism, {}).get("reveals_route")
        if not _info and "F_ROUTE" not in known and "route" not in named:
            return "work out where the other way out is"
        if m.controls and not m.obstacle_open:
            place = labels.get("require", "the controls")
            return f"work out which control clears the way, at {place}"
        if getattr(m, "power_role", None) and not m.power_restored:
            return f"get the power back on at {labels.get('power', 'the source')}"
        # 1d Finding G: multi-part requirements read as a set, not two
        # independent "got it" lines.
        _req = self._mystery_required_items()
        if len(_req) > 1 and not m.obstacle_open:
            _missing = self._mystery_missing_items()
            if _missing:
                _have = len(_req) - len(_missing)
                place = labels.get("require", "where it's kept")
                return (f"get the {_missing[0]} from {place} "
                        f"- part {_have + 1} of {len(_req)}")
        if not m.obstacle_open and not self._mystery_has_item() \
                and m.requirement_item:
            place = labels.get("require", "where it's kept")
            return f"get the {m.requirement_item} from {place}"
        if not m.obstacle_open:
            return "get past what blocks the route"
        if m.knowledge.hypothesis_state() != "confirmed":
            return "make sure this really leads out"
        mech = getattr(m, "mech_name", "the way out")
        return f"go to {mech} - it's marked on your map"

    def objective_tick(self):
        """One call per turn, from the game loop. Runs the lifecycle."""
        m = self._mystery()
        turn = getattr(self, "turns", 0)
        if m is None or getattr(m, "escaped", False):
            return
        state = getattr(self, "_obj_state", None)
        if state is None:
            self._obj_state = "active"
            self._obj_established_turn = turn
            self._obj_last_progress_turn = turn
            self._obj_sig = self._objective_sig()
            return
        if state == "complete":
            return
        sig = self._objective_sig()
        if sig != getattr(self, "_obj_sig", None):
            self._obj_sig = sig
            self._obj_last_progress_turn = turn
            if state in ("distracted", "reminder", "urgent"):
                self._obj_state = "active"   # back on track, quietly
            return
        idle = turn - self._obj_last_progress_turn
        pressure = (self.hunger < 30 or self.thirst < 30 or self.fatigue > 85)
        if state == "active" and idle >= self._OBJ_DISTRACTED_AFTER:
            self._obj_state = "distracted"          # silent - watching
        elif state == "distracted" and idle >= self._OBJ_REMINDER_AFTER:
            self._obj_state = "reminder"
            self.announce_event("still to do", self._objective_next_step(),
                                kind="reminder", level=1)
        elif state in ("distracted", "reminder") and (
                idle >= self._OBJ_URGENT_AFTER
                or (pressure and idle >= self._OBJ_REMINDER_AFTER)):
            self._obj_state = "urgent"
            _why = (f"you're low on supplies and still in "
                    f"{self.world.prose.get('region_noun', 'here')}"
                    if pressure else "you've been at this a while")
            self.announce_event("you're still not out",
                                self._objective_next_step(),
                                f"({_why} - {idle} turns since you last got anywhere)",
                                kind="reminder", level=2)

    def _objective_complete(self):
        self._obj_state = "complete"

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
                kind="danger")

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

    def _lead_loc(self, role):
        """The 'where is it' tail for a just-learned lead's announcement.
        Normal: the heading plus 'marked on your map'. Hardcore: no
        marker is placed - a bearing and a rough tile count, and the
        player searches for it (a POI marker in Hardcore is earned by
        stepping onto the tile)."""
        if not getattr(self, 'hardcore', False):
            return f"{self._mystery_heading(role)}, marked on your map"
        m = self._mystery()
        xy = m.sites.get(role) if m else None
        if not xy:
            return " somewhere out there - no fix on it"
        px, py = self.current_position
        dist = abs(xy[0] - px) + abs(xy[1] - py)
        ns = "north" if xy[1] - py < -1 else "south" if xy[1] - py > 1 else ""
        ew = "west" if xy[0] - px < -1 else "east" if xy[0] - px > 1 else ""
        b = "-".join(x for x in (ns, ew) if x)
        return f" {b}, about {dist} tiles" if b else f" close, within a few tiles"

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
                _tail = ("It's marked on your map now."
                         if not getattr(self, 'hardcore', False)
                         else f"No marker -{self._lead_loc('route')}. You'll have to find it.")
                self.announce_event(f"the route is at {m.site_labels['route']}",
                                    _tail, kind="lead")
        if 'F_POWER' in new_facts and m.site_labels.get('power'):
            _ploc = self._lead_loc('power')
            if MECHANISMS.get(m.mechanism, {}).get('reveals_route'):
                self.announce_event(
                    f"the transmitter is fed from {m.site_labels['power']}",
                    f"Get it running and the outside can guide you out. It's{_ploc}.",
                    kind="lead")
            else:
                self.announce_event(
                    f"the way out is powered from {m.site_labels['power']}",
                    f"Sort out what's wrong there - it's{_ploc}.",
                    kind="lead")
        if 'F_REQUIRE' in new_facts and m.site_labels.get('require'):
            _rloc = self._lead_loc('require')
            if m.controls:
                self.announce_event(
                    f"whatever clears the way is set from {m.site_labels['require']}",
                    f"You'll have to work out which control. It's{_rloc}.",
                    kind="lead")
            else:
                self.announce_event(
                    f"the {m.requirement_item} is kept at {m.site_labels['require']}",
                    f"It's{_rloc}.", kind="lead")

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
                        body = ("The way's been found for you - you do NOT have to "
                                "reach it yourself. Type `escape` right now and you're out.")
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
                if m.knowledge.hypothesis_state() == 'confirmed':
                    # Owner: reaching the open way out with the mystery
                    # solved IS leaving - no `escape` keystroke. That
                    # step was ceremony, not a decision. mystery_try_
                    # escape() fires the MYSTERY SOLVED / milestone /
                    # correction beats and finishes the expedition, so
                    # skip the progress flare's "type escape" banner.
                    self.mystery_try_escape()
                else:
                    self._mystery_progress_flare(_hyp_before, _facts_before)
                    self.io.say(
                        "This is the way out, and it's open - but you're "
                        "not certain yet that it leads anywhere. Better to "
                        "be sure first.")
            elif not m.escaped:
                self._mystery_progress_flare(_hyp_before, _facts_before)
                self.io.say(
                    "This is the way out. It's still blocked - clear it "
                    "and you leave straight from here.")
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
                m.power_restored_desc,
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
                self.io.say("  Work them one at a time - pull <name> and see what each does.")
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
            _rn = self.world.prose.get('region_noun', 'here')
            _obst = m.site_labels.get('obstacle', 'the system')
            self.io.say(
                f"There's nothing to force here. No way out of {_rn} "
                f"comes clear until {_obst} is back up and the "
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
                "Nothing to be done here by hand. Whatever holds this is "
                "worked from the controls, not from here.")
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
            _how = m.assemble_desc
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
        if match == m.correct_control:
            m.obstacle_open = True
            ox, oy = m.obstacle_tile
            cell = self.map[oy][ox]
            if isinstance(cell, dict):
                cell['obstacle'] = False
            self.announce_event("the way is open", m.control_correct,
                                "The route is clear - go.", kind="objective")
        else:
            if match not in m.controls_tried:
                m.controls_tried.append(match)
            self.io.say(m.control_wrong_obvious if match == m.obvious_control
                        else m.control_wrong_other)

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
            m.power_restored_desc,
            kind="objective",
        )
        _hyp_before = m.knowledge.hypothesis_state()
        _facts_before = set(m.knowledge.facts_known())
        self._mystery_after_power_restored()
        self._mystery_progress_flare(_hyp_before, _facts_before)

    def _mystery_mark_world_fact(self, fid):
        """Mark a WorldFact KNOWN and fire its milestone / ladder-
        correction banners once (the not-known -> known transition).
        Used by the finale (E.2) to establish RESP_THE_ORDER alongside
        the mystery's own world_fact_id."""
        _wi = getattr(self, 'world_investigation', None)
        if _wi is None or _wi.fact(fid) is None or _wi.is_known(fid):
            return
        _wi.mark_known(fid)
        self.__class__._world_investigation = _wi.snapshot()['status']
        _learned = list(getattr(self, '_expedition_learned', []))
        _learned.append(fid)
        self._expedition_learned = _learned
        _fact = _wi.fact(fid)
        if _fact is not None and _fact.milestone:
            self.announce_event(_fact.statement, kind="milestone")
        _rung = _wi.hypothesis_broken_by(fid)
        if _rung is not None:
            self.announce_event(_rung.statement, _rung.corrected_to,
                                kind="correction")

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
                "You follow the route it gave you and keep going."
                if MECHANISMS.get(m.mechanism, {}).get('reveals_route')
                else "You make your way back to the way out and start walking.")
            self._update_time(90)
        m.escaped = True
        self._objective_complete()   # lifecycle: COMPLETE (one beat only)
        # A.3: a resolved mystery explicitly tagged with a WorldFact
        # marks that fact KNOWN. Deliberately simple - one isolated
        # transition, so evidence/provenance logic can replace it later
        # without touching anything else. See PHASE_A3_INVESTIGATION.md.
        # E.2: the finale establishes the world's finale.also_establishes
        # facts too (World 1: the seal order + the signature at the
        # command centre) - fire their beats before the main
        # converge_fact resolution below.
        if getattr(m, 'is_finale', False) and getattr(self, 'world_investigation', None):
            _fin = self.world.finale
            for _also in (_fin.also_establishes if _fin else ()):
                self._mystery_mark_world_fact(_also)

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
        _mech_name = getattr(m, 'mech_name', 'the way out')
        if getattr(m, 'is_finale', False):
            _fin = self.world.finale
            self.announce_event(_fin.arrival_title, f"{_stmt}.", kind="solved")
            if _fin.arrival_prose:
                self.io.say("\n" + _fin.arrival_prose + "\n")
        elif MECHANISMS.get(m.mechanism, {}).get('reveals_route'):
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
        if getattr(m, 'is_finale', False):
            self._finale_choice()
        self.finish_expedition(
            reason="carried the truth out" if getattr(m, 'is_finale', False)
            else "found the way out")

    def _finale_choice(self):
        """E.3 / Phase F: the one authored binary choice at the finale
        location. Numbered prompt, never free text. Records
        campaign.ending so a relaunched completed campaign shows the
        resolved state and never re-prompts. All text is world-owned
        (world.finale)."""
        if getattr(self.__class__, "_campaign_ending", None):
            return
        _fin = self.world.finale
        _a_id, _a_line = _fin.option_a
        _b_id, _b_line = _fin.option_b
        self.announce_event(
            _fin.choice_title,
            _fin.choice_intro,
            f"  1) {_a_line}",
            f"  2) {_b_line}",
            kind="objective")
        _prompt = f"{_a_id.capitalize()}, or {_b_id}? (1 / 2): "
        pick = ""
        for _ in range(3):
            pick = (self.io.ask(_prompt) or "").strip()
            if pick in ("1", "2"):
                break
        choice = _a_id if pick == "1" else _b_id
        self.__class__._campaign_ending = choice
        from src.campaign import campaign_ending
        used = list(getattr(self.__class__, "_used_mechanisms", []) or [])
        self.io.say("\n" + campaign_ending(choice, used, self.world) + "\n")
