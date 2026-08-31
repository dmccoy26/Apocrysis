"""P1 - Commitment & Intervention Pass.

docs/PHASE_P1_COMMITMENT_INTERVENTION_SPEC.md §6.1. These assert the
experiment's shape: gates fire at the specified thresholds, resolve on
the specified defaults, never touch the bot, and the corrective ones
actually perform the action.
"""

import unittest
from unittest.mock import patch

from src import combat_forecast as cf
from src.game import Apocrysis
from src.items import MeleeWeapon, RangedWeapon
from src.zombies import RegularZombie, HeavyZombie


class _GateIO:
    """Interactive stand-in: records banners, scripts ask_* answers."""
    renders_natively = True

    def __init__(self, combat_letter="f", commit="__default__"):
        self.said = []
        self._letter = combat_letter
        self._commit = commit
        self.commit_prompts = []

    def say(self, *a, **k):
        self.said.append(" ".join(str(x) for x in a))

    def ask(self, prompt=""):
        return ""

    def ask_yes_no(self, prompt):
        return True

    def ask_combat_letter(self):
        return self._letter

    def ask_commit(self, prompt, default="cancel"):
        self.commit_prompts.append(prompt)
        if self._commit == "__default__":
            return default
        return self._commit

    @property
    def text(self):
        return "\n".join(self.said)


def _game(io=None, **kw):
    with patch("builtins.print"):
        g = Apocrysis("T", map_size=12, seed=1, **kw)
    if io is not None:
        g.io = io
    return g


def _forecast(win_pct, escape_pct=40):
    """Patch context: pin the encounter card's numbers."""
    return patch.multiple(
        "src.combat_forecast",
        fight_outcome=lambda *a, **k: {"win_pct": win_pct, "p50_frac": 0.5,
                                      "p90_frac": 0.8},
        escape_pct=lambda *a, **k: escape_pct,
        better_weapon=lambda *a, **k: None,
    )


class TestP1aCombatOverride(unittest.TestCase):

    def test_gate_fires_below_10pct_and_y_means_fight(self):
        io = _GateIO(combat_letter="f", commit="proceed")
        g = _game(io)
        z = HeavyZombie()
        with _forecast(3):
            verdict = g._encounter_card(z, None, {"win_pct": 3, "p50_frac": 0.5,
                                                  "p90_frac": 0.9})
        self.assertEqual(verdict, "fight")
        self.assertTrue(any("EXTREME THREAT" in p or "EXTREME THREAT" in t
                            for p in io.commit_prompts for t in [io.text]))
        self.assertIn("EXTREME THREAT", io.text)

    def test_gate_default_cancels_to_escape(self):
        io = _GateIO(combat_letter="f", commit="__default__")   # bare Enter
        g = _game(io)
        with _forecast(0):
            verdict = g._encounter_card(HeavyZombie(), None,
                                        {"win_pct": 0, "p50_frac": 0.6,
                                         "p90_frac": 1.0})
        self.assertEqual(verdict, "escape")

    def test_no_gate_at_or_above_10pct(self):
        io = _GateIO(combat_letter="f")
        g = _game(io)
        with _forecast(35):
            verdict = g._encounter_card(RegularZombie(), None,
                                        {"win_pct": 35, "p50_frac": 0.3,
                                         "p90_frac": 0.5})
        self.assertEqual(verdict, "fight")
        self.assertEqual(io.commit_prompts, [])
        self.assertNotIn("EXTREME THREAT", io.text)

    def test_bot_io_never_sees_the_gate(self):
        class Botish:
            renders_natively = False
            def say(self, *a, **k): pass
            def ask(self, p=""): return ""
            def ask_yes_no(self, p): return True
            def ask_combat_letter(self): return "f"
        g = _game(Botish())
        with _forecast(1):
            verdict = g._encounter_card(HeavyZombie(), None,
                                        {"win_pct": 1, "p50_frac": 0.6,
                                         "p90_frac": 1.0})
        self.assertEqual(verdict, "fight")     # "skip" falls through to fight

    def test_escape_line_is_speed_class_honest(self):
        io = _GateIO(combat_letter="e")
        g = _game(io)
        with _forecast(30):
            g._encounter_card(HeavyZombie(), None, {"win_pct": 30, "p50_frac": 0.4,
                                                    "p90_frac": 0.7})
        self.assertIn("break contact", io.text)          # slow: not catastrophic
        io2 = _GateIO(combat_letter="e")
        g2 = _game(io2)
        from src.zombies import SwiftZombie
        with _forecast(30):
            g2._encounter_card(SwiftZombie(), None, {"win_pct": 30, "p50_frac": 0.4,
                                                     "p90_frac": 0.7})
        self.assertIn("in the fight", io2.text)          # fast: still dangerous


class TestP1cWeaponEmpty(unittest.TestCase):

    def test_gate_offers_the_spare_and_equips_on_proceed(self):
        io = _GateIO(commit="proceed")
        g = _game(io)
        g.equipped_weapon = RangedWeapon("Dry Gun", 10, 6, 50)
        g.equipped_weapon.ammo = 0
        g.backpack.ammo = 0
        g.backpack.weapons = [MeleeWeapon("Axe", 14, 40)]
        g._intervention_gates()
        self.assertIn("YOUR WEAPON IS EMPTY", io.text)
        self.assertEqual(g.equipped_weapon.name, "Axe")

    def test_no_gate_when_reload_is_possible(self):
        io = _GateIO(commit="proceed")
        g = _game(io)
        g.equipped_weapon = RangedWeapon("Gun", 10, 6, 50)
        g.equipped_weapon.ammo = 0
        g.backpack.ammo = 12                      # _ammo_warnings owns this
        g.backpack.weapons = [MeleeWeapon("Axe", 14, 40)]
        g._intervention_gates()
        self.assertNotIn("YOUR WEAPON IS EMPTY", io.text)

    def test_no_gate_without_a_usable_spare(self):
        io = _GateIO(commit="proceed")
        g = _game(io)
        g.equipped_weapon = RangedWeapon("Gun", 10, 6, 50)
        g.equipped_weapon.ammo = 0
        g.backpack.ammo = 0
        g.backpack.weapons = []
        g._intervention_gates()
        self.assertEqual(io.commit_prompts, [])


class TestP1dCriticalHP(unittest.TestCase):

    def test_gate_fires_at_20pct_with_medicine_and_heals(self):
        io = _GateIO(commit="proceed")
        g = _game(io)
        g.health = int(g.max_health * 0.18)
        g.backpack.medicine = 2
        before = g.health
        g._intervention_gates()
        self.assertIn("CRITICALLY HURT", io.text)
        self.assertGreater(g.health, before)
        self.assertEqual(g.backpack.medicine, 1)

    def test_no_gate_without_medicine(self):
        io = _GateIO(commit="proceed")
        g = _game(io)
        g.health = int(g.max_health * 0.15)
        g.backpack.medicine = 0
        g._intervention_gates()
        self.assertEqual(io.commit_prompts, [])

    def test_one_shot_then_rearms_over_55pct(self):
        io = _GateIO(commit="cancel")            # decline the heal
        g = _game(io)
        g.backpack.medicine = 3
        g.health = int(g.max_health * 0.15)
        g._intervention_gates()
        g._intervention_gates()                  # still critical - must not re-fire
        self.assertEqual(len(io.commit_prompts), 1)
        g.health = int(g.max_health * 0.60)      # recovered
        g._intervention_gates()                  # re-arm
        g.health = int(g.max_health * 0.15)
        g._intervention_gates()                  # fires again
        self.assertEqual(len(io.commit_prompts), 2)


class TestP1bEscapeReassert(unittest.TestCase):

    def _ready_game(self, io):
        g = _game(io)

        class _M:
            escaped = False
            sites = {"route": (0, 0)}
        g.mystery = _M()
        g._objective_ready_to_leave = lambda: True
        return g

    def test_healthy_player_gets_no_reminder(self):
        io = _GateIO()
        g = self._ready_game(io)
        g.turns = 1
        g.current_position = (5, 5)
        g._escape_ready_reassert()               # arms the clock
        g.turns = 40
        g.fatigue = 10
        g.backpack.water = 20
        g.health = g.max_health
        g.current_position = (8, 8)              # moved away
        g._escape_ready_reassert()
        self.assertNotIn("ESCAPE REMINDER", io.text)

    def test_worn_and_walking_away_gets_a_reminder(self):
        io = _GateIO()
        g = self._ready_game(io)
        g.turns = 1
        g.current_position = (3, 3)
        g._escape_ready_reassert()               # arms, sets _route_dist_prev=6
        g.turns = 30
        g.fatigue = 70
        g.current_position = (6, 6)              # dist 12 > 6 : moved away
        g._escape_ready_reassert()
        self.assertIn("ESCAPE REMINDER", io.text)

    def test_reminder_respects_cooldown(self):
        io = _GateIO()
        g = self._ready_game(io)
        g.turns = 1
        g.current_position = (3, 3)
        g._escape_ready_reassert()
        g.fatigue = 70
        g.turns = 30
        g.current_position = (6, 6)
        g._escape_ready_reassert()              # fires
        g.turns = 33
        g.current_position = (9, 9)
        g._escape_ready_reassert()              # <8 turns later - quiet
        self.assertEqual(io.text.count("ESCAPE REMINDER"), 1)


class TestCommitGatePrimitive(unittest.TestCase):

    def test_console_ask_commit_default_on_bare_enter(self):
        from src.io_console import ConsoleIO
        io = ConsoleIO()
        with patch("builtins.input", return_value=""):
            self.assertEqual(io.ask_commit("x", "proceed"), "proceed")
            self.assertEqual(io.ask_commit("x", "cancel"), "cancel")
        with patch("builtins.input", return_value="y"):
            self.assertEqual(io.ask_commit("x", "cancel"), "proceed")
        with patch("builtins.input", return_value="n"):
            self.assertEqual(io.ask_commit("x", "proceed"), "cancel")

    def test_skip_when_io_has_no_ask_commit(self):
        class Plain:
            def say(self, *a, **k): pass
        g = _game()
        g.io = Plain()
        self.assertEqual(g.commit_gate("k", "T", "b", default="cancel"), "skip")

    def test_once_repeat_and_rearm(self):
        io = _GateIO(commit="proceed")
        g = _game(io)
        self.assertEqual(g.commit_gate("k", "T", "b"), "proceed")
        self.assertEqual(g.commit_gate("k", "T", "b"), "skip")   # one-shot
        g.gate_rearm("k")
        self.assertEqual(g.commit_gate("k", "T", "b"), "proceed")


if __name__ == "__main__":
    unittest.main()
