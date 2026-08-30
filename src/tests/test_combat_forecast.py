"""Combat information layer (docs/COMBAT_INFO_SPEC.md).

Drift guard: the forecast's estimated win-rate must track the REAL
`combat_mixin` fight loop run headless the same way. Plus tier / verdict
/ weapon-comparison sanity.
"""
import copy
import random
import unittest

from src.game import Apocrysis
from src.zombies import FreshZombie, RegularZombie, HeavyZombie, ArmoredZombie
from src.items import MeleeWeapon, RangedWeapon, Armor
from src import combat_forecast as cf


class _SilentFightIO:
    """Always fights, says nothing. No ask_combat_letter -> the encounter
    card takes the non-interactive path (plain yes/no) and never touches
    the forecast."""
    renders_natively = True

    def say(self, *a, **k):
        pass

    def ask(self, prompt=""):
        return ""

    def ask_yes_no(self, prompt):
        return True


def _make_game(weapon, armor_reductions=(), level=8, str_=18, dex=16, hp=140):
    g = Apocrysis("Fc", seed=1, io=_SilentFightIO())
    g.level = level
    g.strength, g.dexterity = str_, dex
    g.health = g.max_health = hp
    g.hunger = g.thirst = 90
    g.fatigue = 10
    g.equipped_weapon = weapon
    slots = ["head", "body", "hands", "feet"]
    g.equipped_armor = {s: None for s in slots}
    for i, red in enumerate(armor_reductions):
        g.equipped_armor[slots[i]] = Armor(f"A{i}", red, 100, slots[i])
    return g


def _real_winrate(game_template, zombie_factory, n=200):
    """Run the ACTUAL encounter_zombie fight loop n times on fresh copies
    and count how often the player is left standing."""
    wins = 0
    for _ in range(n):
        g = copy.deepcopy(game_template)
        z = zombie_factory()
        g.encounter_zombie(z)
        if g.health > 0:
            wins += 1
    return round(100 * wins / n)


class TestForecastDrift(unittest.TestCase):
    def _check(self, weapon, armor, zf, tol=14):
        g = _make_game(weapon, armor)
        predicted = cf.fight_pct(g, zf())
        actual = _real_winrate(g, zf)
        self.assertLessEqual(
            abs(predicted - actual), tol,
            f"forecast {predicted}% vs real {actual}% for {zf().name} "
            f"with {weapon.name}")

    def test_katana_vs_regular(self):
        self._check(MeleeWeapon("Steel Katana", 20, 110), (3, 6),
                    lambda: _scaled(RegularZombie, 1.4))

    def test_katana_vs_heavy(self):
        self._check(MeleeWeapon("Steel Katana", 20, 110), (3, 6),
                    lambda: _scaled(HeavyZombie, 1.2))

    def test_weak_weapon_vs_armored(self):
        self._check(MeleeWeapon("Rusty Dagger", 8, 40), (),
                    lambda: _scaled(ArmoredZombie, 1.0))

    def test_fresh_is_a_walkover(self):
        self._check(MeleeWeapon("Steel Katana", 20, 110), (3,),
                    lambda: FreshZombie())


def _scaled(cls, factor):
    z = cls()
    z.health = int(z.health * factor)
    z.attack = max(1, int(z.attack * factor))
    return z


class TestForecastShape(unittest.TestCase):
    def test_tiers_and_verdicts_monotonic(self):
        tiers = [cf.threat_tier(p) for p in (95, 70, 45, 25, 5)]
        self.assertEqual(tiers, ["LOW", "MODERATE", "HIGH", "SEVERE", "EXTREME"])

    def test_two_axis_threat_tier(self):
        # a near-certain win that is CHEAP is LOW; the same win-rate at a
        # big cost is not (COMBAT_EXP2_RESULTS.md).
        self.assertEqual(cf.threat_tier(98, cost_frac=0.10), "LOW")
        self.assertEqual(cf.threat_tier(98, cost_frac=0.30), "MODERATE")
        self.assertEqual(cf.threat_tier(98, cost_frac=0.70), "HIGH")
        # low win-rate stays a warn tier regardless of cost
        self.assertEqual(cf.threat_tier(20, cost_frac=0.10), "SEVERE")
        self.assertEqual(cf.threat_tier(3, cost_frac=None), "EXTREME")

    def test_two_axis_weapon_verdict(self):
        self.assertEqual(cf.weapon_verdict(98, cost_frac=0.05),
                         "overkill for this target")
        self.assertNotEqual(cf.weapon_verdict(98, cost_frac=0.60),
                            "overkill for this target")

    def test_stronger_weapon_never_worse(self):
        g = _make_game(MeleeWeapon("Rusty Dagger", 8, 40), (3, 6))
        g.backpack.weapons = [MeleeWeapon("Steel Katana", 20, 110)]
        z = _scaled(HeavyZombie, 1.2)
        weak = cf.fight_pct(g, z, weapon=g.equipped_weapon)
        strong = cf.fight_pct(g, z, weapon=g.backpack.weapons[0])
        self.assertGreaterEqual(strong, weak)

    def test_weapon_window_sorted_best_first(self):
        g = _make_game(MeleeWeapon("Rusty Dagger", 8, 40), (3,))
        g.backpack.weapons = [MeleeWeapon("Steel Katana", 20, 110),
                              MeleeWeapon("Iron Axe", 16, 90)]
        rows = cf.all_weapon_forecasts(g, _scaled(RegularZombie, 1.3))
        pcts = [r[1] for r in rows]
        self.assertEqual(pcts, sorted(pcts, reverse=True))

    def test_forecast_does_not_perturb_global_random(self):
        random.seed(42)
        a = [random.random() for _ in range(5)]
        random.seed(42)
        g = _make_game(MeleeWeapon("Steel Katana", 20, 110), (3, 6))
        cf.fight_pct(g, _scaled(HeavyZombie, 1.2))
        cf.all_weapon_forecasts(g, _scaled(HeavyZombie, 1.2))
        b = [random.random() for _ in range(5)]
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
