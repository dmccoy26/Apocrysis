"""World 3 - "The Deep": the competing regional hypotheses.
docs/WORLD_3_THE_DEEP.md §5B.5.

Five rungs (Silence 4 / Wake 4). Deliberately (§3.9a) the rungs do NOT
all break on milestones: rungs 1, 2 and 4 break on non-milestone facts,
because the belief bands don't align with the depth bands. Pure content
- WorldInvestigation.current_hypothesis() derives the held rung from
is_known(held_until) for any fact.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class RegionalHypothesis:
    id: str
    statement: str
    held_until: str
    corrected_to: str


REGIONAL_HYPOTHESES = (
    RegionalHypothesis(
        'DH_ACCIDENT',
        "A structural collapse killed the lower crews. Get the site working, bring out whoever's left.",
        held_until='SEAL_FROM_INSIDE',          # milestone
        corrected_to="Nothing fell on that door. It was locked from the "
                     "inside. Nobody down here was trapped by an accident.",
    ),
    RegionalHypothesis(
        'DH_EVACUATION',
        "They didn't die in the collapse - they pulled back deeper, ahead of something, and sealed the way behind them.",
        held_until='DELIBERATE_OPERATION',      # non-milestone (§3.9a)
        corrected_to="They didn't flee anywhere. The deep workings were "
                     "being run - shifts, quotas, a rota. People chose to "
                     "stay and keep them going.",
    ),
    RegionalHypothesis(
        'DH_BARRICADE',
        "They sealed themselves in - a barricade, holding a line against whatever the galleries turned into.",
        held_until='ORDERS_AFTER_SEAL',         # non-milestone (§3.9a)
        corrected_to="Operation orders, dated after the seal, issued from "
                     "below it. This isn't a line being held - it's an "
                     "operation being run.",
    ),
    RegionalHypothesis(
        'DH_COERCION',
        "The company never let them stop. Kept mining under quota - victims held down here to keep the numbers up.",
        held_until='COMMS_CUT_FROM_BELOW',      # milestone
        corrected_to="The line was cut from the deep side, by their own "
                     "hands. Nobody's forcing them. They cut themselves off "
                     "so they couldn't be ordered back up.",
    ),
    RegionalHypothesis(
        'DH_REFUSAL',
        "They refused the work and cut themselves off - hiding now, or too frightened or too far gone to come out.",
        held_until='WORKERS_MAINTAINING_IT',    # non-milestone (§3.9a)
        corrected_to="They aren't hiding behind the seal. They're holding "
                     "it shut. They have been the containment this whole "
                     "time.",
    ),
)
