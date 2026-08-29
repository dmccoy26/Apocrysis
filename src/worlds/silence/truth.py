"""World 1 - 'The Silence': the authored WorldFact DAG (docs/PHASE_A1_TRUTH.md).

WorldFact is the world's authored truth - what is actually true here -
and is deliberately NOT a subclass of knowledge.Fact (which is what the
*player* has learned). They are bound later by DiscoveryTemplate (A.2),
never by inheritance. This file is content only: no graph class, no
traversal, no solver, no runtime state. Imported by nothing yet except
its test.
"""
from dataclasses import dataclass

THREADS = ('disappearance', 'dead', 'response')

MILESTONE_IDS = frozenset({
    'DIS_ORGANISED',                 # M1
    'DEAD_REGIONAL_CRISIS',          # M2
    'DEAD_INFECTION_PREDATES_EVAC',  # M4
})

@dataclass(frozen=True)
class WorldFact:
    id: str
    thread: str
    chapter: int
    milestone: bool
    statement: str
    needs: tuple = ()

WORLD_FACTS = (
    # CH1 - THE SILENCE (thread: disappearance). No cross-chapter needs.
    WorldFact('DIS_FEW_REMAINS', 'disappearance', 1, False,
              "Far fewer remains than a die-off would leave. Most people left; they did not fall."),
    WorldFact('DIS_MOVED_TOGETHER', 'disappearance', 1, False,
              "The people who left moved along a handful of specific routes, the same direction, over a few days.",
              needs=('DIS_FEW_REMAINS',)),
    WorldFact('DIS_ROUTES_PREPARED', 'disappearance', 1, False,
              "Those routes were prepared before the exodus - signed corridors, marshalling yards, supply caches.",
              needs=('DIS_MOVED_TOGETHER',)),
    WorldFact('DIS_ORGANISED', 'disappearance', 1, True,
              "The exodus was an organised evacuation, directed by some authority - not a panicked flight.",
              needs=('DIS_ROUTES_PREPARED',)),
    # CH2 - THE INFECTED (thread: dead). May need CH1 facts.
    WorldFact('DEAD_WERE_LOCALS', 'dead', 2, False,
              "The infected wear the valley's own clothes and carry its own papers. They are the people who lived here."),
    WorldFact('DEAD_STAGES_DIFFER', 'dead', 2, False,
              "The infected differ by how far the disease has run, not by kind - some lucid and failing slowly, others long past that.",
              needs=('DEAD_WERE_LOCALS',)),
    WorldFact('DEAD_CONTAINED_FIRST', 'dead', 2, False,
              "There was a contained outbreak before the exodus - a quarantine site with early cases already inside it.",
              needs=('DEAD_WERE_LOCALS',)),
    WorldFact('DEAD_REGIONAL_CRISIS', 'dead', 2, True,
              "The crisis was handled as regional: reception centres outside a cordon around the valley. The wider world did not end.",
              needs=('DIS_ORGANISED',)),
    WorldFact('DEAD_INFECTION_PREDATES_EVAC', 'dead', 2, True,
              "The infection was known and present before the evacuation began. The evacuation was a response to it - not the other way round.",
              needs=('DEAD_CONTAINED_FIRST', 'DIS_ORGANISED')),
)