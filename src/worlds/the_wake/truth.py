"""World 2 - "The Wake": the authored WorldFact DAG.
docs/WORLD_2_THE_WAKE.md §4-§5.

Same shape as worlds/silence/truth.py - content only, no graph class,
no traversal. Bound to escape mechanisms by discovery.py; solving a
mechanism surfaces the fact it carries. The DAG's integrity (acyclic,
every `needs` resolves, one lead per fact) is asserted in
test_the_wake.py, the same checks World 1's truth gets.

The truth, worked backward from the ending (§4): the ship was taken
apart deliberately, by one officer, because a moving ship is a
connected ship - full power reconnects the sealed decks - so stopping
the ship WAS the quarantine. Restarting it releases everything at once.
"""
from dataclasses import dataclass

THREADS = ('ship', 'crew', 'order')

MILESTONE_IDS = frozenset({
    'SECTIONS_SEALED',              # M1  the decks are held shut on purpose
    'THE_CHANGED',                  # M2  the hostiles were the crew
    'COMMS_CUT_OUTWARD',            # M3  the silence was deliberate
    'SEALS_ARE_QUARANTINE',         # M4  the seals hold the change IN
    'ONE_AUTHORIZATION',            # M5  one officer ran the whole shutdown
    'SHUTDOWN_WAS_THE_CONTAINMENT', # M6  stopping the ship WAS the quarantine
    'WAKE_RESTART_RELEASES',        # M7  restart releases every seal at once
})


@dataclass(frozen=True)
class WorldFact:
    id: str
    thread: str
    chapter: int
    milestone: bool
    statement: str
    lead: str = ""          # 3-9 words, player voice, the checklist line
    needs: tuple = ()


WORLD_FACTS = (
    # ---- CH1  THE WAKE  (thread: ship) -------------------------------
    WorldFact('WAKE_ALONE', 'ship', 1, False,
              "You came out of cryo alone and out of sequence - your pod cycled early, on a manual command, not the scheduled wake.",
              lead="why you woke early"),
    WorldFact('POWER_PARTITIONED', 'ship', 1, False,
              "The ship's power network isn't down - it's carved into isolated islands. Each section runs on its own, cut off from the rest by design.",
              lead="whether the power actually failed",
              needs=('WAKE_ALONE',)),
    WorldFact('NAV_ON_HOLD', 'ship', 1, False,
              "Navigation isn't broken. It's executing a hold command, and the ship has drifted to a stop against it. Someone told it to stop.",
              lead="why the ship stopped",
              needs=('POWER_PARTITIONED',)),
    WorldFact('SECTIONS_SEALED', 'ship', 1, True,
              "Whole decks are held shut - not by damage, but by standing blast-door commands that never lifted. The ship was closed up section by section, on purpose.",
              lead="why the decks are shut",
              needs=('POWER_PARTITIONED',)),

    # ---- CH2  THE CREW  (thread: crew) -------------------------------
    WorldFact('SURVIVORS_FEW', 'crew', 2, False,
              "A handful of people are awake, holding one section behind a barricade. The manifest lists hundreds. The rest are unaccounted for.",
              lead="how many are left"),
    WorldFact('THE_CHANGED', 'crew', 2, True,
              "The things in the dark corridors wear crew uniforms and carry crew IDs. They are the people who were aboard.",
              lead="what the hostiles are",
              needs=('SURVIVORS_FEW',)),
    WorldFact('CHANGE_IS_STAGED', 'crew', 2, False,
              "The changed differ by how far it has run, not by kind - a few still lucid and failing slowly, most long past that.",
              lead="how far the change has run",
              needs=('THE_CHANGED',)),
    WorldFact('CHANGE_BEGAN_IN_CRYO', 'crew', 2, False,
              "The earliest cases all came out of one cryo bank. The change started in the pods, before the crew were properly awake.",
              lead="where the change started",
              needs=('THE_CHANGED',)),

    # ---- CH3  THE ISOLATION  (thread: order) -----------------------
    WorldFact('SEAL_CODE_IS_MEDICAL', 'order', 3, False,
              "Every deck-seal command carries a Medical department authorization code.",
              lead="where the seal commands came from",
              needs=('SECTIONS_SEALED',)),
    WorldFact('MEDICAL_DENIES_IT', 'order', 3, False,
              "Medical's own console logs have no record of issuing any seal. The authorization code was used - the console it belongs to never was.",
              lead="whether Medical actually did it",
              needs=('SEAL_CODE_IS_MEDICAL',)),
    WorldFact('COMMS_CUT_OUTWARD', 'order', 3, True,
              "External communications weren't lost. They were switched off from the bridge, aimed outward, on a timestamp. Nothing has gone out or come in since.",
              lead="why no one called for help",
              needs=('NAV_ON_HOLD',)),
    WorldFact('SEALS_ARE_QUARANTINE', 'order', 3, True,
              "The decks weren't sealed to protect the people inside them. They were sealed to keep what's inside from reaching the rest of the ship.",
              lead="what the seals were for",
              needs=('MEDICAL_DENIES_IT', 'THE_CHANGED')),

    # ---- CH4  THE ORDER  (thread: order) ---------------------------
    WorldFact('ONE_AUTHORIZATION', 'order', 4, True,
              "The nav hold, the comms blackout and every deck seal share one authorization signature. One officer took the ship apart, alone.",
              lead="who ran the shutdown",
              needs=('COMMS_CUT_OUTWARD', 'SEALS_ARE_QUARANTINE')),
    WorldFact('THE_OFFICERS_LOG', 'order', 4, False,
              "The officer left a record. They had already worked out that the change could not be stopped - only contained - and that containing it meant stranding the ship with everyone still aboard.",
              lead="why the officer did it",
              needs=('ONE_AUTHORIZATION',)),
    WorldFact('SHUTDOWN_WAS_THE_CONTAINMENT', 'order', 4, True,
              "A moving ship needs full power, and full power reconnects the sealed decks. Stopping the ship wasn't a symptom of the crisis - stopping the ship WAS the quarantine.",
              lead="why stopping the ship mattered",
              needs=('THE_OFFICERS_LOG',)),
    WorldFact('CONTAINMENT_FILED_CLEAN', 'order', 4, False,
              "In any record that ever leaves this hull, the ship is logged lost with all hands. The whole cost of the containment was written to stay aboard.",
              lead="how it reads from outside",
              needs=('SHUTDOWN_WAS_THE_CONTAINMENT',)),
    # off the critical path (nothing needs it); placed last of the
    # non-finale facts so next_target only surfaces it late. §12.2.
    WorldFact('WAKE_YOU_BEFORE', 'crew', 4, False,
              "A note, scrawled and left where you'd find it: 'you were up before. i watched you go back in the pod. you don't remember, do you.' Nothing else on it. The hand is shaking.",
              lead="the note that says you've been awake",
              needs=('THE_CHANGED',)),

    # ---- FIN  THE REACTOR  (thread: order) -------------------------
    WorldFact('SURVIVORS_ON_A_CLOCK', 'order', 5, False,
              "The awake survivors' section is failing on its own island of power - air, water, heat all counting down. They cannot hold much longer without the ship's systems back.",
              lead="how long the survivors have",
              needs=('SURVIVORS_FEW', 'SHUTDOWN_WAS_THE_CONTAINMENT')),
    WorldFact('WAKE_RESTART_RELEASES', 'order', 5, True,
              "Restarting the reactor reconnects the whole network - which lifts every standing deck-seal at once. Whatever is behind those doors comes back with the lights.",
              lead="what restarting actually does",
              needs=('SHUTDOWN_WAS_THE_CONTAINMENT',)),
    WorldFact('WAKE_THE_CHOICE', 'order', 5, False,
              "The reactor can be brought back - the survivors get their systems and a way off - or left cold, the seals held, the survivors left with what little their section still gives them.",
              lead="what the reactor decision is",
              needs=('WAKE_RESTART_RELEASES', 'SURVIVORS_ON_A_CLOCK')),
)
