"""World Investigation - which authored WorldFacts this campaign has
established. Operates on a WorldFact DAG passed in; pure data +
derivation, no I/O, no imports from src. Persists across death / new
expedition via the profile round-trip (persistence_mixin). See
docs/PHASE_A3_INVESTIGATION.md.
"""

KNOWN = 'known'
SUSPECTED = 'suspected'
UNKNOWN = 'unknown'


class WorldInvestigation:
    def __init__(self, facts):
        # dict preserves authored order -> next_target() is DAG-ordered
        self._facts = {f.id: f for f in facts}
        self._status = {}  # fid -> KNOWN | SUSPECTED ; absent means UNKNOWN

    def fact(self, fid):
        return self._facts.get(fid)

    def all_facts(self):
        """Every WorldFact, in authored order. Read-only view for
        presentation code - which must not re-derive DAG rules itself."""
        return list(self._facts.values())

    def status(self, fid):
        return self._status.get(fid, UNKNOWN)

    def is_known(self, fid):
        return self._status.get(fid) == KNOWN

    def mark_known(self, fid):
        if fid in self._facts:
            self._status[fid] = KNOWN

    def mark_suspected(self, fid):
        if fid in self._facts and self._status.get(fid) != KNOWN:
            self._status[fid] = SUSPECTED

    def eligible(self):
        return [f for f in self._facts.values()
                if self.status(f.id) == UNKNOWN
                and all(self.is_known(dep) for dep in f.needs)]

    def next_target(self):
        e = self.eligible()
        return e[0].id if e else None

    def thread_progress(self):
        out = {}
        for f in self._facts.values():
            known, total = out.get(f.thread, (0, 0))
            out[f.thread] = (known + (1 if self.is_known(f.id) else 0), total + 1)
        return out

    def milestones_known(self):
        return [fid for fid, f in self._facts.items()
                if f.milestone and self.is_known(fid)]

    def snapshot(self):
        return {'status': dict(self._status)}

    def restore(self, snap):
        if snap:
            self._status = dict(snap.get('status', {}))