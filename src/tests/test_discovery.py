"""Phase A.2 - DiscoveryTemplate + build_mystery(target_fact=...).

The binding is a routing table: a WorldFact selects which escape
mechanism carries it. The mystery is still solved by its own evidence,
and the WorldFact statement is never injected. See
docs/PHASE_A2_DISCOVERY.md.
"""
import unittest

from src.game import Apocrysis
from src.escape import MECHANISMS, build_mystery, Mystery
from src.worlds.silence import SILENCE
from src.worlds.silence.truth import WORLD_FACTS


class _IO:
    renders_natively = True

    def __init__(self):
        self.log = []

    def say(self, *a, **k):
        self.log.append(" ".join(str(x) for x in a))

    def ask(self, prompt=""):
        return ""

    def ask_yes_no(self, prompt):
        return False


_BY_ID = {f.id: f for f in WORLD_FACTS}


class TestDiscoveryTemplates(unittest.TestCase):
    def test_every_template_names_a_real_mechanism(self):
        for fid, routes in SILENCE.discovery_templates.items():
            for t in routes:
                self.assertIn(t.mechanism, MECHANISMS,
                              f"{fid} -> unknown mechanism {t.mechanism}")

    def test_every_ch1_ch2_fact_has_a_route(self):
        for f in WORLD_FACTS:
            self.assertIn(f.id, SILENCE.discovery_templates,
                          f"{f.id} has no DiscoveryTemplate")

    def test_template_world_fact_id_matches_its_key(self):
        for fid, routes in SILENCE.discovery_templates.items():
            for t in routes:
                self.assertEqual(t.world_fact_id, fid)


class TestBuildMysteryTargetFact(unittest.TestCase):
    def _game(self, seed=1):
        return Apocrysis("Disc", seed=seed, io=_IO())

    def test_target_fact_selects_the_bound_mechanism(self):
        g = self._game()
        m = build_mystery(g, target_fact="DIS_ORGANISED")
        self.assertEqual(m.world_fact_id, "DIS_ORGANISED")
        self.assertEqual(m.mechanism, "evac_corridor")

    def test_targeted_mystery_is_still_valid_and_reachable(self):
        from collections import deque

        g = self._game(seed=4)
        m = build_mystery(g, target_fact="DEAD_CONTAINED_FIRST")
        m.validate()  # raises on a broken mystery

        # escape tile reachable from spawn over non-impassable terrain
        start = g.current_position
        seen, q = {start}, deque([start])
        n = g.map_size
        while q:
            x, y = q.popleft()
            for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < n and 0 <= ny < n and (nx, ny) not in seen:
                    c = g.map[ny][nx]
                    if isinstance(c, dict) and c.get("terrain") not in ("mountain", "river"):
                        seen.add((nx, ny))
                        q.append((nx, ny))
        self.assertIn(m.escape_tile, seen)

    def test_worldfact_statement_is_never_injected(self):
        g = self._game(seed=7)
        fid = "DIS_ORGANISED"
        m = build_mystery(g, target_fact=fid)
        statement = _BY_ID[fid].statement
        k = m.knowledge
        blobs = (
            [f.statement for f in k.facts.values()]
            + [e.text for e in k.evidence.values()]
            + [d.text for d in k.deductions.values()]
            + ([k.hypothesis.statement] if k.hypothesis else [])
        )
        for text in blobs:
            self.assertNotIn(statement, text)
        # also: no unique 6-word run of the statement leaks in
        words = statement.split()
        if len(words) >= 6:
            needle = " ".join(words[:6])
            for text in blobs:
                self.assertNotIn(needle, text)

    def test_no_target_fact_is_the_unchanged_random_path(self):
        g = self._game(seed=2)
        m = build_mystery(g)
        self.assertIsNone(m.world_fact_id)
        self.assertIn(m.mechanism, MECHANISMS)

    def test_unknown_target_fact_falls_back_gracefully(self):
        g = self._game(seed=3)
        m = build_mystery(g, target_fact="NOPE_NOT_A_FACT")
        self.assertIsNone(m.world_fact_id)
        self.assertIn(m.mechanism, MECHANISMS)
        m.validate()

    def test_world_fact_id_round_trips(self):
        g = self._game(seed=5)
        m = build_mystery(g, target_fact="DEAD_REGIONAL_CRISIS")
        again = Mystery.from_dict(m.to_dict())
        self.assertEqual(again.world_fact_id, "DEAD_REGIONAL_CRISIS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
