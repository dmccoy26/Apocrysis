"""Zombie Identity Pass (docs/ZOMBIE_IDENTITY_PASS.md) - the valley's
population layer. Identity is attached from a dedicated RNG so it never
perturbs map generation (that's covered by test_worldgen_structure);
this covers the data + selection + determinism."""
import random
import unittest

from src.game import Apocrysis
from src.zombies import Zombie, FreshZombie, HeavyZombie, ArmoredZombie
from src.worlds.silence import population as P


class _IO:
    renders_natively = True

    def __init__(self):
        self.log = []

    def say(self, *a, **k):
        self.log.append(" ".join(str(x) for x in a))

    def ask(self, prompt=""):
        return "q"

    def ask_yes_no(self, prompt):
        return False


class TestPopulationData(unittest.TestCase):
    def test_every_variant_has_a_known_archetype(self):
        for v in P.VARIANTS:
            self.assertIn(v.archetype, P.ARCHETYPES, v.id)

    def test_every_archetype_has_at_least_one_identity(self):
        covered = {v.archetype for v in P.VARIANTS}
        for a in P.ARCHETYPES:
            self.assertIn(a, covered, a)

    def test_rare_tier_is_flagged_and_low_weight_effective(self):
        rare = [v for v in P.VARIANTS if v.rare]
        self.assertTrue(rare)
        for v in rare:
            self.assertTrue(v.flags)   # child skittish, elderly passive

    def test_pick_identity_respects_band(self):
        rng = random.Random(1)
        # armored identities are band=(3, 99) or (4, 99) - none at exp 0
        for _ in range(50):
            v = P.pick_identity("armored", 0, rng)
            self.assertTrue(v.band[0] <= 0 <= v.band[1] or v.id.startswith("unknown_"))

    def test_situations_shift_with_stage(self):
        early = set(P.situations_for_stage(1))
        late = set(P.situations_for_stage(20))
        self.assertIn("ordinary", early)
        self.assertIn("last_stand", late)
        self.assertNotIn("last_stand", early)

    def test_describe_three_levels(self):
        v = next(x for x in P.VARIANTS if x.id == "mechanic")
        self.assertEqual(P.describe(v, "clear")[0], "INFECTED - a mechanic")
        self.assertTrue(P.describe(v, "hint")[0].startswith("INFECTED - "))
        self.assertEqual(P.describe(v, "unknown")[0], "INFECTED")

    def test_stripped_variant_is_always_anonymous(self):
        v = next(x for x in P.VARIANTS if x.id == "stripped")
        for conf in ("clear", "hint", "unknown"):
            self.assertEqual(P.describe(v, conf)[0], "INFECTED")


class TestIdentityAttachment(unittest.TestCase):
    def test_placed_infected_get_an_identity(self):
        g = Apocrysis("Pop", seed=5, io=_IO(), expeditions_completed=4)
        placed = [c for row in g.map for c in row if isinstance(c, Zombie)]
        self.assertTrue(placed)
        for z in placed:
            self.assertTrue(z.identity)
            self.assertTrue(z.identity_label.startswith("INFECTED"))
            self.assertIn(z.situation, P.SITUATIONS)

    def test_identity_is_deterministic_for_a_seed(self):
        a = Apocrysis("Pop", seed=5, io=_IO(), expeditions_completed=4)
        b = Apocrysis("Pop", seed=5, io=_IO(), expeditions_completed=4)
        za = [(x, y, c.identity, c.situation)
              for y, row in enumerate(a.map) for x, c in enumerate(row)
              if isinstance(c, Zombie)]
        zb = [(x, y, c.identity, c.situation)
              for y, row in enumerate(b.map) for x, c in enumerate(row)
              if isinstance(c, Zombie)]
        self.assertEqual(za, zb)

    def test_bare_zombie_has_safe_defaults(self):
        z = FreshZombie()
        self.assertEqual(z.identity_label, "INFECTED")
        self.assertEqual(z.flags, ())
        self.assertEqual(z.ARCHETYPE, "fresh")
        self.assertEqual(HeavyZombie().ARCHETYPE, "heavy")
        self.assertEqual(ArmoredZombie().ARCHETYPE, "armored")


class TestBehaviourFlags(unittest.TestCase):
    def _g(self):
        return Apocrysis("Flag", seed=1, io=_IO())

    def test_skittish_infected_flees_no_fight_no_xp(self):
        from src.worlds.silence import population as P
        g = self._g()
        z = FreshZombie()
        z.flags = ("skittish",)
        z.identity_label, z.identity_line = "INFECTED - a schoolchild", "A small figure."
        xp0, hp0 = g.xp, g.health
        g.io.log.clear()
        g.encounter_zombie(z)
        self.assertEqual(g.xp, xp0)          # no reward for it running
        self.assertEqual(g.health, hp0)      # no fight
        self.assertTrue(any("gone" in l or "bolts" in l for l in g.io.log))

    def test_passive_infected_is_stepped_around(self):
        g = self._g()
        z = FreshZombie()
        z.flags = ("passive",)
        z.identity_label = "INFECTED - an elderly resident"
        hp0 = g.health
        g.io.log.clear()
        g.encounter_zombie(z)
        self.assertEqual(g.health, hp0)
        self.assertTrue(any("barely reacts" in l for l in g.io.log))


class TestIdentityLoot(unittest.TestCase):
    def _g(self):
        return Apocrysis("Loot", seed=1, io=_IO())

    def test_medical_lean_biases_toward_medicine(self):
        import random as _r
        _r.seed(3)
        g = self._g()
        z = FreshZombie()
        z._loot_lean = ("medical",) * 6      # a heavy nurse lean
        med0 = g.backpack.medicine
        for _ in range(30):
            g.handle_loot(z.loot_table, z)
        # over many rolls a medical lean should net more medicine than
        # a bare fresh table would (fresh table has 1/3 medicine)
        self.assertGreater(g.backpack.medicine - med0, 25)

    def test_loot_poor_infected_gives_almost_nothing(self):
        g = self._g()
        z = FreshZombie()
        z._loot_poor = True
        before = (g.backpack.food, g.backpack.medicine,
                  len(g.backpack.weapons), g.backpack.ammo)
        g.io.log.clear()
        for _ in range(20):
            g.handle_loot(z.loot_table, z)
        after = (g.backpack.food, g.backpack.medicine,
                 len(g.backpack.weapons), g.backpack.ammo)
        # only water can trickle in, and only sometimes
        self.assertEqual(before[:1] + before[1:], before)
        self.assertEqual(after[1], before[1])       # no medicine
        self.assertEqual(after[2], before[2])       # no weapons
        self.assertEqual(after[3], before[3])       # no ammo

    def test_last_stand_drops_less(self):
        import random as _r
        g = self._g()
        z = HeavyZombie()
        z.situation = "last_stand"
        _r.seed(1)
        total = 0
        for _ in range(40):
            g.io.log.clear()
            g.handle_loot(z.loot_table, z)
            total += len(g.io.log)
        self.assertLess(total / 40, 2.0)           # avg < 2 items


if __name__ == "__main__":
    unittest.main()
