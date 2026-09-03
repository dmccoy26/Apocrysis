"""World 3 - "The Deep": the authored WorldFact DAG.
docs/WORLD_3_THE_DEEP.md §5B.4 + the Phase-6 integration pass.

Content only. Bound to carriers - a mix of escape mechanisms
(discovery.py), authored scene / contact beats (world.py, contacts.py),
a combat beat (combat_beat.py) and a campaign_state check (facility.py)
- so different evidence modalities interact. Integrity is asserted in
test_the_deep.py.

The truth, worked backward from the ending (§1.5): the seam is an
energy deposit that changes the people who work it, dose by depth and
hours at the face. The company established the curve and kept the cages
running. The deep crews put it together, downed tools, sealed the last
galleries and cut the line from the deep side so no one could order
them back. They have been the containment ever since. Restoring the
site to reach the survivors rebuilds the exact road the seam travels up.

Integration merges (§5B.4 allows collapsing the institution branch):
COMPANY_CORRELATION -> QUOTAS_CONTINUED (one managed-harm fact);
CASE_TIMING -> ORE_IS_SOURCE (ORLA presents the whole convergence).
Authored order follows the 25-level schedule so next_target() hands the
mystery levels the right facts; the beat-carried facts are listed in
manifest.BEAT_CARRIED_FACTS so a generated mystery never grabs them.
"""
from dataclasses import dataclass

THREADS = ('facility', 'order', 'seam')

MILESTONE_IDS = frozenset({
    'SEAL_FROM_INSIDE',            # M1  the descent was shut from the inside
    'CHANGED_HAVE_STRUCTURE',      # M2  the Changed hold ground - stationed
    'COMPANY_KNEW',               # M3  the company established the harm, kept mining
    'COMMS_CUT_FROM_BELOW',        # M4  the site was cut off from the deep side
    'ORE_IS_SOURCE',              # M5  this seam is where the region's change began
    'RESTART_REOPENS_THE_ROUTE',   # C1  restoring the site rebuilds the seam's road up
    'THE_STANCES',                # C2  the lucid survivors do not agree
})


@dataclass(frozen=True)
class WorldFact:
    id: str
    thread: str
    chapter: int
    milestone: bool
    statement: str
    lead: str = ""
    needs: tuple = ()


WORLD_FACTS = (
    # ---- BAND I  THE WORKS  (chapter 1) ------------------------------
    WorldFact('DESCENT_BLOCKED', 'facility', 1, False,
              "The cage only runs three levels down. Below that the shaft's dark and the lower crews aren't answering.",
              lead="why the lower crews went quiet"),
    WorldFact('SEAL_FROM_INSIDE', 'facility', 1, True,
              "The deep-access blast door is locked - and the bar is thrown on my side. Nothing collapsed onto it. Someone shut it, standing where I'm standing.",
              lead="what actually blocked the descent",
              needs=('DESCENT_BLOCKED',)),
    WorldFact('WORK_CONTINUED_BELOW', 'facility', 1, False,
              "Past the seal: tools left mid-task, shift notes, a cold meal - all dated days after the surface wrote the site off. People kept working down here.",
              lead="whether anyone worked on past the seal",
              needs=('SEAL_FROM_INSIDE',)),
    WorldFact('DELIBERATE_OPERATION', 'facility', 1, False,
              "Shift boards, quotas, a maintenance rota. The deep workings weren't people hiding - they were being run, to a schedule, by people who chose to stay.",
              lead="hiding, or still working",
              needs=('WORK_CONTINUED_BELOW',)),
    WorldFact('ORE_HAS_VALUE', 'seam', 1, False,
              "The seam isn't ordinary rock. It's an energy deposit - rich, and exactly what the failing grid up top is starving for. There was a real reason to dig.",
              lead="what they were mining",
              needs=('WORK_CONTINUED_BELOW',)),

    # ---- BAND II  THE WORKING LEVELS  (chapter 2) -------------------
    WorldFact('CHANGED_ARE_CREW', 'facility', 2, False,
              "The things in the workings wear crew coveralls, carry crew tags, wore their boots down the same way I wore mine. These were the people I came for.",
              lead="what the things in the workings are",
              needs=('DESCENT_BLOCKED',)),
    WorldFact('CHANGED_HAVE_STRUCTURE', 'facility', 2, True,
              "They don't wander. They hold ground - doorways, junctions, the gallery heads. Two worked me from opposite sides like they'd rehearsed it. They're stationed.",
              lead="are the Changed organised",
              needs=('CHANGED_ARE_CREW',)),
    WorldFact('CHANGED_BY_DEPTH', 'facility', 2, False,
              "The deeper I go the further gone they are. Near the top they still flinch from a light. At the face they don't register me at all.",
              lead="do the Changed get worse with depth",
              needs=('CHANGED_ARE_CREW',)),
    WorldFact('ANOMALY_REPORTS', 'order', 2, False,
              "The medical station's logs run back years: tremors, blackouts, men walking into walls - every line worse the more hours they'd spent below.",
              lead="did anyone record the sickness",
              needs=('CHANGED_ARE_CREW',)),

    # ---- BAND III  THE DEEP WORKINGS  (chapter 3) -----------------
    WorldFact('EXTRACTION_EXPOSURE', 'seam', 3, False,
              "Cross the sick list against the rosters and it's exact: dose by depth, dose by hours at the face. The richest ore and the fastest change are the same place.",
              lead="what was making the crews sick",
              needs=('CHANGED_BY_DEPTH', 'ANOMALY_REPORTS')),
    WorldFact('ORDERS_AFTER_SEAL', 'facility', 3, False,
              "There are operation orders logged from levels that had supposedly gone dark - dated after the deep door closed. Someone below the seal was still issuing them.",
              lead="who gave orders after the seal",
              needs=('SEAL_FROM_INSIDE', 'DELIBERATE_OPERATION')),
    WorldFact('QUOTAS_CONTINUED', 'order', 3, False,
              "The occupational records don't just log the symptoms - they model them, exposure in and severity out. And the extraction targets logged next to that curve never once came down. A managed-harm programme, run alongside the numbers.",
              lead="did the company connect it, did production slow",
              needs=('ANOMALY_REPORTS',)),
    WorldFact('COMPANY_KNEW', 'order', 3, True,
              "They weren't a company that didn't know. They established exactly what the seam did to people, wrote it down, and kept the cages running. They costed it.",
              lead="did the company understand the harm",
              needs=('QUOTAS_CONTINUED', 'EXTRACTION_EXPOSURE')),

    # ---- BAND IV  THE SEALED GALLERIES  (chapter 4) --------------
    WorldFact('COMMS_CUT_FROM_BELOW', 'order', 4, True,
              "The external line wasn't cut at the surface. The break is at a junction hundreds of metres down, and the tool marks are on the deep side. They cut themselves off.",
              lead="who cut the site off from outside",
              needs=('ORDERS_AFTER_SEAL',)),
    WorldFact('WORKERS_CHOSE_ISOLATION', 'facility', 4, False,
              "The deep crews put the pattern together, downed tools, sealed the last galleries behind them and pulled the line so nobody could order them back. Whether that was a refuge or a containment is the thing the accounts disagree on.",
              lead="why the deep crews sealed themselves in",
              needs=('COMMS_CUT_FROM_BELOW',)),
    WorldFact('WORKERS_MAINTAINING_IT', 'facility', 4, False,
              "It's not a relic left running. People are down here now keeping it sealed - the lucid ones by choice, the stationed Changed because holding that ground is the last thing they know how to do.",
              lead="is anyone still holding the seal",
              needs=('CHANGED_HAVE_STRUCTURE',)),
    WorldFact('CONTAINMENT_INFRASTRUCTURE', 'facility', 4, False,
              "The doors, the vent splits, the way the power's carved up below the seal - it isn't damage and it isn't neglect. It's a system, built and kept up, to hold one thing shut. That settles what the seal is for.",
              lead="what the deep layout actually is",
              needs=('COMMS_CUT_FROM_BELOW', 'WORKERS_MAINTAINING_IT')),

    # ---- BAND V  THE SEAL  (chapter 5) --------------------------
    WorldFact('ORE_IS_SOURCE', 'seam', 5, True,
              "Exposure records, the shipment manifests and the first cases up the line, the ore that went up the shaft - it converges. This seam is where the region's change began, and it rode the ore and the crews out. I've been climbing down toward the source the whole way.",
              lead="where the region's outbreak started",
              needs=('EXTRACTION_EXPOSURE', 'WORKERS_CHOSE_ISOLATION')),
    WorldFact('SURVIVORS_ON_A_CLOCK', 'order', 5, False,
              "The still-lucid ones are holed up on one dead-end circuit - scavenged power, rationed air and water. Every gauge in the room is falling. They can't hold much longer without the site's systems back.",
              lead="how long the lucid survivors have",
              needs=('WORKERS_MAINTAINING_IT',)),
    WorldFact('RESTART_REOPENS_THE_ROUTE', 'seam', 5, True,
              "Every system I brought back - power, vents, lifts, haulage - is a piece of the extraction line. Finish it and I don't just reach the survivors. I rebuild the exact road the seam travels up.",
              lead="what restoring the site actually does",
              needs=('CONTAINMENT_INFRASTRUCTURE', 'ORE_IS_SOURCE')),
    WorldFact('THE_STANCES', 'order', 5, True,
              "The ones who can still talk don't agree. One wants the doors open and everyone out. One says the seal stays shut whatever it costs them. One says they can't make the call any more - it's mine now.",
              lead="what the survivors want done",
              needs=('WORKERS_MAINTAINING_IT', 'SURVIVORS_ON_A_CLOCK')),
    WorldFact('THE_CHOICE', 'order', 5, False,
              "The line can be finished - the survivors get out and the seam goes up to whoever's been trying to reach this place - or the deep comes down for good, and everyone still holding it goes with it.",
              lead="the decision at the seal",
              needs=('RESTART_REOPENS_THE_ROUTE', 'SURVIVORS_ON_A_CLOCK', 'THE_STANCES')),

    # ---- TEXTURE  (milestone False, off the critical path) -------
    WorldFact('SOMEONE_IS_COMING', 'order', 5, False,
              "Since the collapse something's been working the site from outside - sinking a bypass, testing the old vents. Not a rescue. Someone wants back in the moment the route is viable.",
              lead="who's been trying to reach the site",
              needs=('SURVIVORS_ON_A_CLOCK',)),
)
