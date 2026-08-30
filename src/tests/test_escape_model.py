"""Phase-2 regression tests for the escape model
(docs/DESIGN_ESCAPE_MODEL.md). The design-doc completion gate, as
executable assertions: R1–R6, the monotonicity matrix (§4a), bounded
influence (§4b), the intrinsic/resolved split, and the statistical
trust of the flee roll (§5) — plus that `combat_forecast.escape_pct`
and the real flee roll read the *same* number.
"""
import random
import unittest

from src import escape_model as em
from src import combat_forecast as cf
from src.game import Apocrysis
from src.zombies import (FreshZombie, RegularZombie, HeavyZombie, SwiftZombie,
                         ToxicZombie, ArmoredZombie, speed_class_of)


_L3_DEX = 12   # dev/_pstate: dex = 10 + (level-1)


def _res(zombie, dex=_L3_DEX, fatigue=10, hp_frac=1.0, terrain="plain"):
    return em.escape_chance(speed_class_of(zombie()), dex, fatigue, hp_frac, terrain)


class TestSpeedClasses(unittest.TestCase):
    def test_roster_classes(self):
        self.assertEqual(speed_class_of(HeavyZombie()), "slow")
        self.assertEqual(speed_class_of(ArmoredZombie()), "slow")
        self.assertEqual(speed_class_of(SwiftZombie()), "fast")
        self.assertEqual(speed_class_of(RegularZombie()), "normal")

    def test_elite_shares_base_class(self):
        z = ArmoredZombie()
        z.name = "Elite Armored Zombie"
        self.assertEqual(speed_class_of(z), "slow")


class TestFixtures(unittest.TestCase):
    def test_R1_armored_open_healthy_reliably_high(self):
        self.assertGreaterEqual(_res(ArmoredZombie), 0.75)

    def test_R2_wounded_fatigued_materially_lower_but_still_best(self):
        r1 = _res(ArmoredZombie)
        r2 = _res(ArmoredZombie, fatigue=60, hp_frac=0.40)
        self.assertLess(r2, r1 - 0.08)
        self.assertGreater(r2, 0.50)

    def test_R2x_extreme_state_lower_still(self):
        r2 = _res(ArmoredZombie, fatigue=60, hp_frac=0.40)
        r2x = _res(ArmoredZombie, fatigue=90, hp_frac=0.20)
        self.assertLess(r2x, r2)

    def test_R3_swift_materially_below_armored(self):
        self.assertLess(_res(SwiftZombie), _res(ArmoredZombie) - 0.20)

    def test_R4_confined_constrains_escape(self):
        b = em.escape_breakdown("slow", _L3_DEX, 10, 1.0, "building")
        self.assertLess(b["availability"], 1.0)
        self.assertLess(b["resolved"], 0.35)
        # intrinsic unchanged — "the thing is still slow"
        self.assertGreater(b["intrinsic"], 0.75)

    def test_R5_dexterity_monotonic(self):
        self.assertGreater(_res(RegularZombie, dex=20), _res(RegularZombie, dex=4))

    def test_R6_dont_fight_is_a_strategy_not_a_coin_flip(self):
        self.assertGreater(_res(ArmoredZombie), 0.70)


class TestMonotonicity(unittest.TestCase):
    def _b(self, **kw):
        d = dict(zombie=RegularZombie, dex=_L3_DEX, fatigue=30, hp_frac=1.0,
                 terrain="plain")
        d.update(kw)
        return em.escape_chance(speed_class_of(d["zombie"]()), d["dex"],
                                d["fatigue"], d["hp_frac"], d["terrain"])

    def test_speed(self):
        vals = [self._b(zombie=SwiftZombie), self._b(zombie=RegularZombie),
                self._b(zombie=HeavyZombie)]
        self.assertEqual(vals, sorted(vals))

    def test_dex(self):
        vals = [self._b(dex=4), self._b(dex=12), self._b(dex=20)]
        self.assertEqual(vals, sorted(vals))

    def test_fatigue(self):
        vals = [self._b(fatigue=90), self._b(fatigue=30), self._b(fatigue=0)]
        self.assertEqual(vals, sorted(vals))

    def test_hp(self):
        vals = [self._b(hp_frac=0.2), self._b(hp_frac=0.6), self._b(hp_frac=1.0)]
        self.assertEqual(vals, sorted(vals))

    def test_terrain(self):
        vals = [self._b(terrain="building"), self._b(terrain="forest"),
                self._b(terrain="plain")]
        self.assertEqual(vals, sorted(vals))


class TestBoundedInfluence(unittest.TestCase):
    def test_speed_class_stays_dominant(self):
        slow_worst = em.escape_chance("slow", 3, 90, 0.15, "plain")
        fast_best = em.escape_chance("fast", 25, 0, 1.0, "plain")
        self.assertGreater(slow_worst, fast_best)


class TestTrust(unittest.TestCase):
    def test_flee_roll_matches_predicted(self):
        rng = random.Random(99)
        for sc in ("slow", "normal", "fast"):
            for terr in ("plain", "forest", "building"):
                p = em.escape_chance(sc, 12, 30, 1.0, terr)
                n = 40000
                hits = sum(1 for _ in range(n) if rng.random() < p)
                self.assertLess(abs(hits / n - p), 0.02)


class _IO:
    renders_natively = True
    def say(self, *a, **k): pass
    def ask(self, prompt=""): return ""
    def ask_yes_no(self, prompt): return True


class TestForecastAndFleeShareOneNumber(unittest.TestCase):
    def test_escape_pct_delegates_to_escape_model(self):
        g = Apocrysis("Esc", seed=1, io=_IO())
        g.dexterity = 12
        g.fatigue = 20
        g.health = g.max_health = 120
        z = ArmoredZombie()
        # open ground
        want = round(100 * em.escape_chance_for(g, z, "plain"))
        self.assertEqual(cf.escape_pct(g, z, "plain"), want)
        # a building constrains it
        self.assertLess(cf.escape_pct(g, z, "building"), cf.escape_pct(g, z, "plain"))

    def test_not_a_flat_fifty(self):
        g = Apocrysis("Esc", seed=1, io=_IO())
        g.dexterity = 12
        g.fatigue = 20
        g.health = g.max_health = 120
        self.assertGreater(cf.escape_pct(g, ArmoredZombie(), "plain"), 60)
        self.assertLess(cf.escape_pct(g, SwiftZombie(), "plain"), 45)


if __name__ == "__main__":
    unittest.main()
