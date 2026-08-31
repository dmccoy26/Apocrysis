"""World 2 - "The Wake": the competing regional hypotheses.
docs/WORLD_2_THE_WAKE.md §6.

Four rungs (vs World 1's four - same count, different shape). The
player's read of what happened is earned and wrong, disproved in stages.
Each `held_until` is a milestone WorldFact whose discovery breaks the
rung. Pure content - WorldInvestigation.current_hypothesis() derives
the held rung from milestone state.
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
        'WH_CATASTROPHE',
        "The ship suffered a systems failure. Fix the systems, fix the ship, wake the rest of the crew.",
        held_until='SECTIONS_SEALED',
        corrected_to="The ship didn't fail. Someone took it apart - deck by "
                     "deck, deliberately - and left it that way.",
    ),
    RegionalHypothesis(
        'WH_SURVIVORS_DID_IT',
        "The people who are left did this. They cut the ship down and sealed themselves in to survive whatever came aboard.",
        held_until='SEALS_ARE_QUARANTINE',
        corrected_to="It isn't a barricade. It's a quarantine. The crew didn't "
                     "hide from an enemy - the crew became one.",
    ),
    RegionalHypothesis(
        'WH_PANIC',
        "Someone panicked when the change started and locked the whole ship down. A desperate, badly-made call.",
        held_until='SHUTDOWN_WAS_THE_CONTAINMENT',
        corrected_to="It wasn't panic. One officer worked out the only thing "
                     "that would hold it, and did it deliberately - knowing it "
                     "stranded everyone still aboard.",
    ),
    RegionalHypothesis(
        'WH_CONTAINED',
        "The containment worked. The change is sealed away for good. The survivors just need the ship back.",
        held_until='WAKE_RESTART_RELEASES',
        corrected_to="The containment only holds while the ship is dead. "
                     "Bringing it back undoes all of it, at once.",
    ),
)
