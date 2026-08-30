"""World 1 - "The Silence": the competing regional hypotheses
(docs/PHASE_E_SPEC.md E.1).

The player's read of what happened to the region is earned and wrong,
disproved in stages (WORLD_TRUTH_CANDIDATES.md candidate A - the
wrong-assumptions ladder). Each rung is a belief the player holds until
a specific milestone WorldFact disproves it. Content only: no state, no
logic - WorldInvestigation.current_hypothesis() derives the current
rung from milestone-known state.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class RegionalHypothesis:
    id: str
    statement: str        # the belief, in the survivor's own voice
    held_until: str       # milestone WorldFact id whose discovery breaks it
    corrected_to: str     # the one line that replaces it when it falls


REGIONAL_HYPOTHESES = (
    RegionalHypothesis(
        'RH_KILLED',
        "Everyone here was killed by the infected. This is a graveyard.",
        held_until='DIS_ORGANISED',
        corrected_to="They weren't killed. They left - along prepared routes, "
                     "in order. This was an evacuation.",
    ),
    RegionalHypothesis(
        'RH_EVACUATED',
        "The valley was evacuated. Everyone got out.",
        held_until='RESP_SEAL_SCHEDULED',
        corrected_to="Not everyone. The corridors closed on a fixed date, with "
                     "people still inside, told help was coming.",
    ),
    RegionalHypothesis(
        'RH_RESCUE_RAN_OUT',
        "The people who ran the evacuation did what they could and ran out of "
        "time. The seal was a last resort.",
        held_until='RESP_ONE_COMMAND',
        corrected_to="The same command that opened the corridors ordered them "
                     "sealed. One body ran both the rescue and the abandonment.",
    ),
    RegionalHypothesis(
        'RH_BETRAYED_AT_END',
        "It was a real rescue that was betrayed at the end - someone lost their "
        "nerve and sealed the line.",
        held_until='RESP_THE_ORDER',
        corrected_to="The seal was signed before the first corridor opened. "
                     "Rescue and abandonment were never two things. They were "
                     "one plan, Protocol Seven, written together.",
    ),
)
