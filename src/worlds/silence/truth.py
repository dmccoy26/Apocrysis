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
    'DIS_ORGANISED',                 # M1  the exodus was organised
    'DEAD_REGIONAL_CRISIS',          # M2  it was handled as regional
    'DEAD_INFECTION_PREDATES_EVAC',  # M4  infection predates the evac
    'RESP_COMMS_CUT_DELIBERATE',     # M3  comms were switched off, not lost
    'RESP_SEAL_SCHEDULED',           # M5  the corridors closed on a schedule
    'RESP_ONE_COMMAND',              # M6  one command opened and sealed them
    'RESP_A_POST_TRANSMITS',         # M8  a station never stopped transmitting
    'RESP_PEOPLE_ALIVE',             # M9  there are living people in the valley
    'RESP_THE_ORDER',                # M10 the seal was signed before the first corridor
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

    # CH3 - THE EVACUATION (thread: response). Where did the corridors
    # lead, and did everyone reach them?
    WorldFact('RESP_CORRIDORS_LED_OUT', 'response', 3, False,
              "The signed corridors ran to reception centres beyond the valley rim. People who reached them did get out.",
              needs=('DIS_ORGANISED',)),
    WorldFact('RESP_NOT_ALL_REACHED', 'response', 3, False,
              "Not everyone made the corridors. The marshalling-yard manifests stop mid-count, the same day across every yard.",
              needs=('RESP_CORRIDORS_LED_OUT',)),
    WorldFact('RESP_COMMS_CUT_DELIBERATE', 'response', 3, True,
              "The valley's communications were not knocked out. They were switched off, from the outside, on a timestamp.",
              needs=('RESP_NOT_ALL_REACHED',)),
    WorldFact('RESP_CORDON_HELD_OUTSIDE', 'response', 3, False,
              "The cordon line was manned from the far side the whole time. The people inside were told to wait for transport that had already been recalled.",
              needs=('RESP_COMMS_CUT_DELIBERATE',)),

    # CH4 - THE RESPONSE (thread: response). Who ordered the seal, and
    # when was it decided?
    WorldFact('RESP_PROTOCOL_SEVEN', 'response', 4, False,
              "The operation had a name: Protocol Seven. The evacuation and the seal were one plan in two phases, written together.",
              needs=('RESP_CORDON_HELD_OUTSIDE',)),
    WorldFact('RESP_SEAL_SCHEDULED', 'response', 4, True,
              "The corridors were set to close on a fixed date from the moment Protocol Seven activated - not when they were 'overrun'. They closed on time, with people still inside.",
              needs=('RESP_PROTOCOL_SEVEN', 'RESP_NOT_ALL_REACHED')),
    WorldFact('RESP_ONE_COMMAND', 'response', 4, True,
              "The order to open the corridors and the order to seal them carry the same signature. One regional command ran both the rescue and the abandonment.",
              needs=('RESP_SEAL_SCHEDULED',)),
    WorldFact('RESP_CONTAINMENT_WORKED', 'response', 4, False,
              "From outside the line, Protocol Seven is filed as a success: the outbreak never left the region. The whole cost of that was kept inside the valley.",
              needs=('RESP_ONE_COMMAND', 'DEAD_REGIONAL_CRISIS')),

    # CH5 - THE LAST SIGNAL (thread: response). Is anyone still alive?
    WorldFact('RESP_STILL_MONITORED', 'response', 5, False,
              "The cordon frequency is still monitored from outside. Someone has been listening to the valley the entire time.",
              needs=('RESP_COMMS_CUT_DELIBERATE',)),
    WorldFact('RESP_A_POST_TRANSMITS', 'response', 5, True,
              "One station inside the valley never stopped transmitting - a low automatic carrier out of the regional command centre.",
              needs=('RESP_STILL_MONITORED',)),
    WorldFact('RESP_CONSOLIDATION_HELD', 'response', 5, False,
              "A consolidation point on the last corridor never emptied. The people sent there were told to keep walking; instead they stopped and dug in.",
              needs=('RESP_SEAL_SCHEDULED',)),
    WorldFact('RESP_PEOPLE_ALIVE', 'response', 5, True,
              "There are living people in the valley - the ones who held the consolidation point. Not infected. Still waiting.",
              needs=('RESP_CONSOLIDATION_HELD', 'RESP_A_POST_TRANSMITS')),

    # FIN - THE TRUTH (thread: response). The regional command centre.
    WorldFact('RESP_THE_ORDER', 'response', 6, True,
              "The regional command centre holds the seal order and the signature that authorised leaving the valley full. It was signed before the first corridor opened.",
              needs=('RESP_ONE_COMMAND', 'RESP_A_POST_TRANSMITS')),
    WorldFact('RESP_THE_CHOICE', 'response', 6, False,
              "The command centre's transmitter still reaches past the cordon. The truth of Protocol Seven can be sent out - or the people who held the line can be left their silence.",
              needs=('RESP_THE_ORDER', 'RESP_PEOPLE_ALIVE')),
)