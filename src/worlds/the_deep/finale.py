"""World 3 - "The Deep": the finale. docs/WORLD_3_THE_DEEP.md §5B.9.

Same shape as the Wake's: converge the investigation -> a bespoke last
descent -> a binary choice at a location. The mechanism is
`power_station` - finishing the extraction line IS an infrastructural
dependency chain - so the site labels map onto that grammar's roles.

Kill-test 0: `also_establishes` carries the Band IV-V tail that §5B is
spec'd to deliver through `WorldContact` (kill-test B) and the
`campaign_state` check (kill-test A). Order is dependency-valid. Those
facts also have mechanism routes in discovery.py; a fact already
surfaced is a no-op here. Kill-tests A/B trim this list.
"""
from src.worlds.base import WorldFinale

# §5.3 draft prose - the wording pass (§5B.11) still applies. The
# cruelty holds: the retrospective must not tell the player which bet
# paid off.
LEAD_A = (
    "You finish the last of the line - power to the lifts, the vents split "
    "back the way they run, the haulage turning over. The decline door "
    "runs up. Down at the enclave the gauges stop falling. You take the "
    "ones who can still be moved up the haulage road, and behind them the "
    "first loaded skip of the seam goes up the shaft to meet whoever's "
    "been sinking a bypass to reach it."
)
BODY_A = (
    "The survivors who could be moved are out, or on their way. The seam "
    "is going up to hands that wanted it badly enough to dig for it, and "
    "the road it travels is open all the way. Whatever that costs, further "
    "out, you won't be there to see it. You chose the people in front of "
    "you, and a chance, over the door."
)
LEAD_B = (
    "You bring the bore down instead - drop the charges on the face, weld "
    "the deep doors, cut the lift ropes behind you as you climb. The last "
    "thing you hear from below is the galleries closing on themselves. The "
    "ones who were holding the seal are on the wrong side of it now, the "
    "lucid with the rest."
)
BODY_B = (
    "The seam stays below for good, and so does everyone who stayed to "
    "hold it. The change that started here doesn't get its road back. The "
    "people who put the pattern together and gave up the surface to keep "
    "it shut are sealed in with the thing they were containing, and no one "
    "outside this rock will ever have their names. You carried the whole "
    "of it out alone. Maybe that was the harder thing to do. Maybe it was "
    "only the one that keeps it buried."
)

FINALE = WorldFinale(
    converge_fact="THE_CHOICE",
    also_establishes=(
        "CONTAINMENT_INFRASTRUCTURE",
        "WORKERS_MAINTAINING_IT",
        "ORE_IS_SOURCE",
        "SURVIVORS_ON_A_CLOCK",
        "RESTART_REOPENS_THE_ROUTE",
        "THE_STANCES",
        "SOMEONE_IS_COMING",
    ),
    escape_kind="power_station",
    site_labels={
        "power": "main extraction control",
        "route": "the haulage road up",
        "obstacle": "the seal across the bore",
        "require": "the last of the extraction line",
        "closed": "the bore face",
    },
    arrival_title="main extraction control",
    arrival_prose=(
        "Main extraction control, the bore cold beyond it, the seal doors "
        "standing ready to run either way. The last of the line is here to "
        "be finished or not. There is nothing left to work out - only to "
        "decide."
    ),
    choice_title="THE BORE IS COLD AND THE SURVIVORS ARE ON A CLOCK",
    choice_intro="The line can be finished, or the deep brought down.",
    option_a=(
        "bring_up",
        "BRING IT UP - finish the extraction line. The survivors who can "
        "still be moved get a route out; the seam goes up with them, to "
        "whoever has been trying to reach this place. You choose the people "
        "in front of you, and a chance, over the door.",
    ),
    option_b=(
        "seal_it",
        "SEAL IT - bring the bore down, weld the deep doors, cut the lifts. "
        "The seam stays below for good, and so does everyone still holding "
        "it - the lucid ones included.",
    ),
    question="Finish the line - the survivors out, the seam up to whoever's "
             "been trying to reach it - or bring the deep down for good.",
    endings={
        "bring_up": (LEAD_A, BODY_A),
        "seal_it": (LEAD_B, BODY_B),
    },
)
