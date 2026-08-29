"""Survivor Knowledge - the concrete lessons this campaign's survivors
have figured out. Campaign-level (survives death), persisted via the
profile round-trip. The engine asks exactly one question: has(<id>).
See docs/PHASE_B_SPEC.md.
"""

class SurvivorKnowledge:
    def __init__(self, learned=None):
        self._learned = set(learned or ())

    def has(self, lore_id):
        return lore_id in self._learned

    def learn(self, lore_id):
        """Returns True if this is newly learned (for the one-time banner)."""
        if lore_id in self._learned:
            return False
        self._learned.add(lore_id)
        return True

    def learned_ids(self):
        return sorted(self._learned)

    def snapshot(self):
        return sorted(self._learned)

    def restore(self, ids):
        self._learned = set(ids or ())