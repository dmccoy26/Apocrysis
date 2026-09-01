# Map-9/World-2 postmortem (2026-09): the encounter card already
# computes win% + the HP-loss cost of winning (combat_forecast's Monte
# Carlo), but only ever spoke a cost sentence for the fp>=65 "you'll
# win, but it'll cost you" case - a 22%-to-win fight got a bare number
# and "poorly suited", no translation of what that number MEANS. The
# fix is pure communication: no stun/escape/damage/weapon number moves.
#
# Bands mirror src.combat_forecast.THREAT_TIERS (15/35/65) so the cost
# sentence never disagrees with the "Threat: X" line already on the
# same card.

import unittest
from unittest.mock import patch

from src.game import Apocrysis
from src.zombies import HeavyZombie


class _IO:
    """Interactive stand-in: records everything said, scripts the
    combat-letter answer (always 'e' here - we're only reading the
    card, never running the fight loop)."""
    renders_natively = True

    def __init__(self):
        self.said = []

    def say(self, *a, **k):
        self.said.append(" ".join(str(x) for x in a))

    def ask(self, prompt=""):
        return ""

    def ask_yes_no(self, prompt):
        return True

    def ask_combat_letter(self):
        return "e"

    @property
    def text(self):
        return "\n".join(self.said)


def _game():
    with patch("builtins.print"):
        g = Apocrysis("T", map_size=12, seed=1)
    g.io = _IO()
    return g


def _forecast(escape_pct=19):
    return patch.multiple(
        "src.combat_forecast",
        escape_pct=lambda *a, **k: escape_pct,
        better_weapon=lambda *a, **k: None,
    )


_FATAL = "likely to be fatal"
_BADLY_HURT = "likely to leave you badly hurt"
_SIGNIFICANT = "probably cost you significant health"
_NEAR_DEATH = "near death by the end"
_ALL = (_FATAL, _BADLY_HURT, _SIGNIFICANT, _NEAR_DEATH)


def _card(fp, p90):
    g = _game()
    with _forecast():
        g._encounter_card(HeavyZombie(), None,
                          {"win_pct": fp, "p50_frac": p90, "p90_frac": p90})
    return g.io.text


class TestCombatCostMessage(unittest.TestCase):

    def test_below_15_reads_as_fatal(self):
        text = _card(fp=5, p90=0.9)
        self.assertIn(_FATAL, text)
        for other in _ALL:
            if other != _FATAL:
                self.assertNotIn(other, text)

    def test_map9_regression_22pct_reads_as_badly_hurt(self):
        """The exact encounter from the Map-9/World-2 death: Fire Axe
        vs a SEVERE-tier Changed, ~22% to win. The card must now say
        so in plain language, not just print the two numbers."""
        text = _card(fp=22, p90=0.8)
        self.assertIn("Threat:  SEVERE", text)
        self.assertIn(_BADLY_HURT, text)
        for other in _ALL:
            if other != _BADLY_HURT:
                self.assertNotIn(other, text)

    def test_35_to_65_reads_as_significant_cost(self):
        text = _card(fp=50, p90=0.6)
        self.assertIn(_SIGNIFICANT, text)
        for other in _ALL:
            if other != _SIGNIFICANT:
                self.assertNotIn(other, text)

    def test_likely_win_but_costly_keeps_the_existing_message(self):
        text = _card(fp=80, p90=0.5)
        self.assertIn(_NEAR_DEATH, text)
        for other in _ALL:
            if other != _NEAR_DEATH:
                self.assertNotIn(other, text)

    def test_likely_and_cheap_win_gets_no_cost_sentence(self):
        text = _card(fp=90, p90=0.1)
        for s in _ALL:
            self.assertNotIn(s, text)

    def test_bands_align_with_the_threat_tier_already_on_the_card(self):
        """The sentence must never contradict the Threat: line - same
        14/35/65 breakpoints as combat_forecast.THREAT_TIERS."""
        from src import combat_forecast as cf
        for fp, expect in ((10, "EXTREME"), (20, "SEVERE"), (50, "HIGH")):
            text = _card(fp=fp, p90=0.8)
            tier = cf.threat_tier(fp, 0.8)
            self.assertEqual(tier, expect)
            self.assertIn(f"Threat:  {expect}", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
