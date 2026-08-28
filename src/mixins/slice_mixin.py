# ============================================================
# Apocrysis - "Dam Service Road" vertical-slice engine glue
# File: src/mixins/slice_mixin.py
#
# The behaviour half of the v4 vertical slice. Authored content lives
# in src/slice_dam_road.py; the knowledge model and the
# journal/remember/inspect/look commands are now the shared Phase B
# machinery (src/knowledge.py + KnowledgeMixin). This mixin only
# does the slice-specific glue: the fixed map, translating the
# authored content into a Knowledge object, location arrival, the
# valve key, the gate chokepoint + backtrack beat, and the gated
# escape action.
# ============================================================

from src.items import Item
from src.knowledge import Knowledge, Fact, Evidence, Deduction, Hypothesis
from src import slice_dam_road as S


class SliceMixin:
    # ---- setup -------------------------------------------------

    def slice_setup(self):
        """Build the fixed slice world and load its knowledge model.

        Called from world_mixin.generate_map() when self.slice_mode is
        True, in place of procedural generation.
        """
        self.map_size = S.SLICE_MAP_SIZE
        self.map = S.build_slice_map()
        self.current_position = S.SLICE_SPAWN
        self.map[S.SLICE_SPAWN[1]][S.SLICE_SPAWN[0]]['content'] = 'P'

        # Translate the authored content into the shared knowledge
        # model (what the generator will produce procedurally later).
        k = Knowledge()
        for fid, statement in S.SLICE_FACTS.items():
            k.add_fact(Fact(fid, statement))
        for ev in S.SLICE_EVIDENCE:
            k.add_evidence(Evidence(ev['id'], ev['text'], supports=ev['supports'],
                                    location=ev['location'], method=ev['method']))
        for d in S.SLICE_DEDUCTIONS:
            k.add_deduction(Deduction(d['id'], d['text'], needs=d['needs']))
        h = S.SLICE_HYPOTHESIS
        k.set_hypothesis(Hypothesis(h['id'], h['text'],
                                    suspected_when=h['suspected_when'],
                                    confirmed_by=h['confirmed_by']))
        self.knowledge = k

        # Slice-specific state.
        self.slice_locations_seen = set()
        self.slice_gate_open = False
        self.slice_saw_gate_locked = False
        self.slice_shed_flooded = False
        self.slice_escaped = False
        self.slice_supplies_taken = set()

    # ---- helpers --------------------------------------------

    def _slice_has_key(self):
        return any(getattr(it, 'name', None) == S.SLICE_KEY_ITEM
                   for it in self.backpack.items)

    def _slice_discover(self, evidence_id):
        """Discover one evidence item, printing its text the first time."""
        if self.knowledge.discover(evidence_id):
            self.io.say(self.knowledge.evidence[evidence_id].text)
            return True
        return False

    def _slice_adjacent_to(self, location_key):
        lx, ly = S.SLICE_LOCATIONS[location_key]['coord']
        px, py = self.current_position
        return max(abs(px - lx), abs(py - ly)) <= 1

    # ---- look (used by KnowledgeMixin.knowledge_look) --------

    def _look_here(self):
        key = S.slice_location_at(*self.current_position)
        if key is None:
            self.io.say("Open ground. Nothing here but the way you're going.")
            return
        self.io.say(S.SLICE_LOCATIONS[key]['blurb'])
        self._slice_examine(key)

    # ---- arrival (called from world_mixin.move_and_search) --

    def slice_arrive(self, x, y):
        key = S.slice_location_at(x, y)
        if key is None:
            return
        first_time = key not in self.slice_locations_seen
        self.slice_locations_seen.add(key)
        if first_time:
            self.io.say(S.SLICE_LOCATIONS[key]['blurb'])
        self._slice_examine(key)

        if (key == S.SLICE_ESCAPE_LOCATION and self.slice_gate_open
                and not self.slice_escaped
                and self.knowledge.hypothesis_state() == 'confirmed'):
            self.io.say("(Type `escape` to leave the valley.)")

    def _slice_examine(self, key):
        """Everything you'd get from being at this location and going
        through it - observed AND searched evidence, supply caches, the
        irrelevant-thread text, the physical-destruction beat. Runs on
        arrival (no separate `search` step) and is idempotent."""
        # supply cache, once
        if key in S.SLICE_SUPPLIES and key not in self.slice_supplies_taken:
            self.slice_supplies_taken.add(key)
            kind, amount, text = S.SLICE_SUPPLIES[key]
            setattr(self.backpack, kind, getattr(self.backpack, kind) + amount)
            self.io.say(f"{text} (+{amount} {kind})")

        # physical-destruction demo: the shed record is gone after the
        # flood, but the journal keeps what was already read
        if key == 'utility_shed' and self.slice_shed_flooded:
            if any(e['id'] in self.knowledge.found for e in S.evidence_at('utility_shed')):
                self.io.say(
                    "The shed is under a foot of reservoir water now. The "
                    "clipboard and the papers are pulp. What you already "
                    "read here you still know - check `journal` - but "
                    "there's nothing left to read."
                )
                return

        if key in S.SLICE_IRRELEVANT:
            self.io.say(S.SLICE_IRRELEVANT[key])

        for ev in S.evidence_at(key):
            if ev['id'] == S.SLICE_HYPOTHESIS['confirmed_by'] and not self.slice_gate_open:
                continue
            self._slice_discover(ev['id'])

        if (key == 'control_room'
                and S.SLICE_KEY_EVIDENCE in self.knowledge.found
                and not self._slice_has_key()):
            self.backpack.add_item(Item(S.SLICE_KEY_ITEM))
            self.io.say(f"You take the {S.SLICE_KEY_ITEM}.")

    def slice_bump_gate(self):
        """Walked into the locked gate without the key."""
        self.slice_saw_gate_locked = True
        for ev in S.evidence_at(S.SLICE_GATE_LOCATION, method='observe'):
            if not self._slice_discover(ev['id']):
                self.io.say("The gate is still locked. You still need the key.")

    # ---- commands (slice-specific) --------------------------

    def slice_search(self):
        """`search` still works, but you get the same thing just by
        being here - it's not a required step."""
        key = S.slice_location_at(*self.current_position)
        if key is None:
            self.io.say("You look around properly. Nothing here worth noting.")
            return
        before = len(self.knowledge.found)
        self._slice_examine(key)
        if len(self.knowledge.found) == before and key not in S.SLICE_IRRELEVANT:
            self.io.say("You've been over this place. Check `journal` for what you found.")

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

        self.backpack.items = [it for it in self.backpack.items
                               if getattr(it, 'name', None) != S.SLICE_KEY_ITEM]
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
        self.io.say("The service road is open ahead of you. Head east.")
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
        if self.knowledge.hypothesis_state() != 'confirmed':
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
