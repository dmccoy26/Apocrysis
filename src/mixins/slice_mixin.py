# ============================================================
# Apocrysis - "Dam Service Road" vertical-slice engine glue
# File: src/mixins/slice_mixin.py
#
# The behaviour half of the v4 vertical slice. The authored content
# lives in src/slice_dam_road.py; this mixin wires it into the
# existing game: a fixed map, an evidence/knowledge model, the
# journal/remember/inspect commands, and the gated escape action.
#
# Scoped deliberately to the slice - this is NOT the Phase B command
# architecture or the Phase C knowledge model. It exists to find out
# whether the investigation loop is fun before either gets built.
# See "Vertical slice prototype" in
# docs/ESCAPE_WORLD_DESIGN_ASSESSMENT.md.
# ============================================================

from src.items import Item
from src import slice_dam_road as S


class SliceMixin:
    # ---- setup -------------------------------------------------

    def slice_setup(self):
        """Build the fixed slice world and its knowledge state.

        Called from world_mixin.generate_map() when self.slice_mode is
        True, in place of procedural generation.
        """
        self.map_size = S.SLICE_MAP_SIZE
        self.map = S.build_slice_map()
        self.current_position = S.SLICE_SPAWN
        self.map[S.SLICE_SPAWN[1]][S.SLICE_SPAWN[0]]['content'] = 'P'

        # Knowledge state - in-memory only for the slice. Persisting
        # it across save/load and death is Phase 2C (todo e3a1e201),
        # deliberately out of scope here.
        self.slice_evidence_found = {}      # evidence id -> evidence dict
        self.slice_locations_seen = set()   # location keys arrived at
        self.slice_gate_open = False
        self.slice_saw_gate_locked = False  # for the backtrack beat
        self.slice_shed_flooded = False     # physical-destruction demo
        self.slice_escaped = False

    # ---- knowledge derivations (pure, computed on demand) ------

    def _slice_facts_known(self):
        known = set()
        for ev in self.slice_evidence_found.values():
            for fid in ev['supports']:
                known.add(fid)
        return known

    def _slice_deductions_available(self):
        known = self._slice_facts_known()
        return [d for d in S.SLICE_DEDUCTIONS if set(d['needs']) <= known]

    def _slice_hypothesis_state(self):
        if S.SLICE_HYPOTHESIS['confirmed_by'] in self.slice_evidence_found:
            return 'confirmed'
        available = {d['id'] for d in self._slice_deductions_available()}
        if set(S.SLICE_HYPOTHESIS['suspected_when']) <= available:
            return 'suspected'
        return 'unknown'

    def _slice_has_key(self):
        return any(
            getattr(it, 'name', None) == S.SLICE_KEY_ITEM
            for it in self.backpack.items
        )

    # ---- recording evidence -----------------------------------

    def _slice_record(self, ev):
        """Record one evidence entry, printing it the first time only."""
        if ev['id'] in self.slice_evidence_found:
            return False
        self.slice_evidence_found[ev['id']] = ev
        self.io.say(ev['text'])
        return True

    # ---- arrival (called from move_and_search) ----------------

    def slice_arrive(self, x, y):
        key = S.slice_location_at(x, y)
        if key is None:
            return
        loc = S.SLICE_LOCATIONS[key]

        first_time = key not in self.slice_locations_seen
        self.slice_locations_seen.add(key)
        if first_time:
            self.io.say(loc['blurb'])

        # Auto-revealed ('observe') evidence at this location.
        for ev in S.evidence_at(key, method='observe'):
            # E6 (road continues past the gate) only registers once the
            # gate is actually open and you are standing beyond it.
            if ev['id'] == S.SLICE_HYPOTHESIS['confirmed_by'] and not self.slice_gate_open:
                continue
            self._slice_record(ev)

        if first_time and S.evidence_at(key, method='search'):
            self.io.say("(There may be more here if you `search`.)")

    def slice_bump_gate(self):
        """Walked into the locked gate. Records the gate as observed
        evidence (E3) and the backtrack flag, without moving."""
        self.slice_saw_gate_locked = True
        for ev in S.evidence_at(S.SLICE_GATE_LOCATION, method='observe'):
            if not self._slice_record(ev):
                self.io.say("The gate is still locked. You still need the key.")

    def _slice_adjacent_to(self, location_key):
        lx, ly = S.SLICE_LOCATIONS[location_key]['coord']
        px, py = self.current_position
        return abs(px - lx) + abs(py - ly) <= 1

    # ---- commands --------------------------------------------

    def slice_search(self):
        key = S.slice_location_at(*self.current_position)
        if key is None:
            self.io.say("You search the area but find nothing worth noting.")
            return
        loc = S.SLICE_LOCATIONS[key]

        # Irrelevant leads: real text, no evidence, no mechanical hook.
        if key in S.SLICE_IRRELEVANT:
            self.io.say(S.SLICE_IRRELEVANT[key])

        searchable = S.evidence_at(key, method='search')
        if not searchable and key not in S.SLICE_IRRELEVANT:
            self.io.say(f"You search {loc['name']}. Nothing new.")
            return

        # Physical-destruction demo: once the reservoir has risen, the
        # shed's paper record is gone - but anything already read stays
        # in the journal.
        if key == 'utility_shed' and self.slice_shed_flooded:
            self.io.say(
                "The shed floor is under a foot of reservoir water. The "
                "clipboard and the papers on the wall are pulp. Whatever "
                "you already read here, you still know - but there is "
                "nothing left to read."
            )
            return

        found_new = False
        for ev in searchable:
            if self._slice_record(ev):
                found_new = True

        # Searching the control room and finding the key evidence hands
        # over the actual key item.
        if (key == 'control_room'
                and S.SLICE_KEY_EVIDENCE in self.slice_evidence_found
                and not self._slice_has_key()):
            self.backpack.add_item(Item(S.SLICE_KEY_ITEM))
            self.io.say(f"You take the {S.SLICE_KEY_ITEM}.")
        elif not found_new and key not in S.SLICE_IRRELEVANT:
            self.io.say("Nothing else here.")

    def slice_journal(self):
        """Raw evidence found + facts it establishes. A memory aid, not
        a checklist - it shows only what you have actually seen."""
        if not self.slice_evidence_found:
            self.io.say("Your journal is empty. You have not noted anything yet.")
            return
        self.io.say("== JOURNAL ==")
        self.io.say("Things you have found:")
        for ev in S.SLICE_EVIDENCE:
            if ev['id'] in self.slice_evidence_found:
                self.io.say(f"  - {ev['text']}")
        known = self._slice_facts_known()
        if known:
            self.io.say("")
            self.io.say("What that tells you:")
            for fid, text in S.SLICE_FACTS.items():
                if fid in known:
                    self.io.say(f"  - {text}")

    def slice_remember(self):
        """A short synthesised read of where your understanding stands -
        prose, not a table. Recalling what you know, not a hint."""
        known = self._slice_facts_known()
        if not known:
            self.io.say(
                "You think it over. So far you have a flooded road and a "
                "lot of questions. Nothing adds up yet."
            )
            return

        parts = []
        deductions = self._slice_deductions_available()
        for d in deductions:
            parts.append(d['text'])

        state = self._slice_hypothesis_state()
        if state == 'confirmed':
            parts.append(
                "You have seen it with your own eyes: " + S.SLICE_HYPOTHESIS['text']
            )
        elif state == 'suspected':
            parts.append("You are starting to think: " + S.SLICE_HYPOTHESIS['text'])

        if not parts:
            self.io.say(
                "You go over what you know. It is real, but it does not "
                "point anywhere yet. Keep looking."
            )
            return
        self.io.say("You think it through:")
        for p in parts:
            self.io.say(f"  {p}")

    _INSPECT_TARGETS = {
        'road': 'F1', 'highway': 'F1', 'water': 'F1', 'flood': 'F1',
        'service road': 'F2', 'other road': 'F2', 'bypass': 'F2',
        'gate': 'F3', 'lock': 'F3',
        'key': 'F4', 'valve key': 'F4',
    }

    def slice_inspect(self, target):
        """Observed / Known / Suspected / Unknown for one thing."""
        target = (target or "").strip().lower()
        if not target:
            self.io.say("Inspect what? Try: road, service road, gate, key, way out.")
            return

        if target in ('way out', 'escape', 'exit', 'hypothesis'):
            state = self._slice_hypothesis_state()
            label = {'confirmed': 'Known', 'suspected': 'Suspected',
                     'unknown': 'Unknown'}[state]
            self.io.say(f"The way out - {label}.")
            if state == 'confirmed':
                self.io.say(f"  {S.SLICE_HYPOTHESIS['text']}")
            elif state == 'suspected':
                self.io.say(f"  You suspect: {S.SLICE_HYPOTHESIS['text']}")
            else:
                self.io.say("  You have no idea how to get out of here yet.")
            return

        fid = None
        for phrase, f in self._INSPECT_TARGETS.items():
            if phrase in target:
                fid = f
                break
        if fid is None:
            self.io.say(f"You do not have anything on '{target}'.")
            return

        known = self._slice_facts_known()
        supporting = [e for e in S.SLICE_EVIDENCE
                      if fid in e['supports'] and e['id'] in self.slice_evidence_found]
        if fid in known:
            self.io.say(f"{S.SLICE_FACTS[fid]} - Known.")
            for e in supporting:
                self.io.say(f"  (from: {e['text']})")
        elif supporting:
            self.io.say(f"{S.SLICE_FACTS[fid]} - Suspected.")
        else:
            self.io.say("Unknown - you have not found anything about that.")

    # ---- gate / escape --------------------------------------

    def slice_open_gate(self):
        if not self._slice_adjacent_to(S.SLICE_GATE_LOCATION):
            self.io.say("There is no gate here to open.")
            return
        if self.slice_gate_open:
            self.io.say("The gate is already open.")
            return
        if not self._slice_has_key():
            self.io.say(
                "The gate is chained and padlocked. You need the key - the "
                "log said it was moved to the control room."
            )
            return

        # Consume the key; distinct beat if this is a return trip.
        self.backpack.items = [
            it for it in self.backpack.items
            if getattr(it, 'name', None) != S.SLICE_KEY_ITEM
        ]
        self.slice_gate_open = True
        if self.slice_saw_gate_locked:
            self.io.say(
                "You came back. The valve key turns in the padlock and the "
                "chain that stopped you last time drops into the gravel. The "
                "gate swings in."
            )
        else:
            self.io.say(
                "The valve key fits the padlock. The chain drops and the "
                "gate swings in."
            )
        # The reservoir is still rising - reaching the gate takes long
        # enough that the shed record is lost behind you.
        self.slice_shed_flooded = True

    def slice_try_escape(self):
        if self.slice_escaped:
            self.io.say("You are already out.")
            return
        key = S.slice_location_at(*self.current_position)
        if key != S.SLICE_ESCAPE_LOCATION:
            self.io.say(
                "You are not anywhere you could leave from. If there is a "
                "way out of this valley you have not reached it yet."
            )
            return
        if not self.slice_gate_open:
            self.io.say("The service gate is still locked behind you.")
            return
        if self._slice_hypothesis_state() != 'confirmed':
            self.io.say(
                "You could start walking. But you are not sure this road "
                "goes anywhere - better to look first."
            )
            return
        self.slice_escaped = True
        self.won = True
        self.io.say(
            "\nYou walk up the service road. The roar of the spillway "
            "falls away behind you. Over the ridge the road keeps going, "
            "and so do you.\n"
            "You worked out the way out of a place that had no marked "
            "exit - a flooded road, another road, a locked gate, a key "
            "someone had moved. You put it together yourself.\n"
            "SLICE COMPLETE."
        )
