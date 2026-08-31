"""World 2 - "The Wake": the finale. docs/WORLD_2_THE_WAKE.md §2-§3.

The finale *shape* is engine-owned (converge the investigation -> a
bespoke last expedition -> a binary choice at a location). This fills
it in. The mechanism is `power_station` - the reactor restart IS an
infrastructural dependency chain - so the site labels below map onto
that grammar's roles.
"""
from src.worlds.base import WorldFinale

FINALE = WorldFinale(
    converge_fact="WAKE_THE_CHOICE",
    # the FIN-chapter chain lands at the finale site - the last
    # hypothesis rung (WH_CONTAINED, broken by WAKE_RESTART_RELEASES)
    # falls exactly as the player reaches the decision. Order matters:
    # SHUTDOWN first (WAKE_RESTART_RELEASES needs it). A fact already
    # surfaced normally is a no-op here.
    also_establishes=("SHUTDOWN_WAS_THE_CONTAINMENT",
                      "SURVIVORS_ON_A_CLOCK",
                      "WAKE_RESTART_RELEASES"),
    escape_kind="reactor",
    site_labels={
        "power": "main engineering control",
        "route": "the reactor gallery",
        "obstacle": "the blast door to the core",
        "require": "the coolant-loop override",
        "closed": "the dead pressure doors",
    },
    arrival_title="main engineering control",
    arrival_prose=(
        "Main engineering is quiet, the reactor cold in its gallery. The "
        "officer's terminal is still logged in, the shutdown order open on "
        "it with the signature and the date. The blast door to the core "
        "stands ready to run either way. There is nothing left to work out - "
        "only to decide."
    ),
    choice_title="THE CORE IS COLD AND THE SURVIVORS ARE ON A CLOCK",
    choice_intro="The reactor can be brought back, or left dead.",
    option_a=(
        "restart",
        "RESTART - bring the reactor up. The survivors get systems, air, and a "
        "way off the ship. Full power reconnects the network, every deck-seal "
        "releases at once, and whatever is behind them comes back with the lights.",
    ),
    option_b=(
        "shutdown",
        "SHUT DOWN - leave the reactor cold. The seals hold and the changed "
        "stay contained. The survivors keep only what their failing section "
        "still gives them, and the truth of this ship leaves only with you.",
    ),
    question="Restart the reactor - saving the few who are awake at the cost of "
             "releasing what the ship was stopped to contain - or leave it dead.",
    endings={
        "restart": (
            "You run the start sequence. The reactor catches, the network "
            "floods back deck by deck, and all through the ship the standing "
            "seals lift at once - a long rolling boom of blast doors clearing "
            "their housings. The survivors' section comes alive around them. "
            "You make the pod bay ahead of what's coming up the spine.",
            "The awake are off the ship, or on their way. Everything the "
            "officer stopped this ship to hold is loose in it now, and the "
            "ship is under power and pointed somewhere. Whatever that costs, "
            "further out, you won't be there to see it. You chose the people "
            "you had met.",
        ),
        "shutdown": (
            "You close the shutdown order without countersigning a restart, "
            "and you leave the reactor cold. On your way out you pass the "
            "survivors' section. Nobody says anything. They know what a dead "
            "reactor means for them.",
            "The seals hold. The changed stay where they were put, in the "
            "dark, under a ship that will not move again. The people who were "
            "still breathing when you found them run out of air on their own "
            "clock. You carry the whole of it off alone, in a single pod, "
            "with no one on the other end to tell. Maybe that was the harder "
            "thing to do. Maybe it was only the one that keeps it buried.",
        ),
    },
)
