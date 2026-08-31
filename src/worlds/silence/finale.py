"""World 1 - "The Silence": the finale. Content only.

Phase F: the finale *shape* stays in the engine (converge the
investigation -> a bespoke last expedition -> a binary choice at a
location). This is the content that fills that shape - moved out of
mystery_mixin's hardcoded strings and campaign.ENDINGS.
"""
from src.worlds.base import WorldFinale

FINALE = WorldFinale(
    converge_fact="RESP_THE_CHOICE",
    also_establishes=("RESP_THE_ORDER",),
    escape_kind="checkpoint",
    site_labels={
        "route": "the antenna mast",
        "power": "the regional command centre",
        "require": "the compound fuel store",
        "require2": "the motor pool",
        "closed": "the checkpoint gate",
    },
    arrival_title="the regional command centre",
    arrival_prose=(
        "The command centre is quiet and the transmitter is warm. The "
        "order is on the desk where it was left, with the signature and "
        "the date. Outside the compound the checkpoint gate stands open, "
        "and the road past it is clear. There is nothing left to work out."
    ),
    choice_title="THE TRANSMITTER STILL REACHES OUT",
    choice_intro="The command centre's antenna can still send past the cordon.",
    option_a=(
        "broadcast",
        "BROADCAST - send the seal order and the signature out. The truth "
        "of Protocol Seven leaves the valley. The people who held the line "
        "lose their silence.",
    ),
    option_b=(
        "protect",
        "PROTECT  - walk out without transmitting. Protocol Seven stays "
        "filed a success. The settlement keeps its silence and its chance.",
    ),
    question="Broadcast the truth of Protocol Seven past the cordon, or "
             "protect the silence of the people who held the line?",
    endings={
        "broadcast": (
            "You bring the command centre's transmitter up and send it all "
            "out past the cordon - the seal order, the signature, the date it "
            "was written. A voice answers, eventually. Flat. It acknowledges "
            "receipt and nothing else.",
            "Protocol Seven is on record now, outside the line, where it "
            "can't be filed as a success. What that changes, you won't be "
            "here to see. The people who held the consolidation point have "
            "lost their silence - the cordon knows exactly where they are. "
            "You told the truth, and it cost them.",
        ),
        "protect": (
            "You stand in the command centre with the order in your hand and "
            "the transmitter warm, and you switch it off. You walk out past "
            "the empty checkpoint without sending anything.",
            "Protocol Seven stays a success on someone's ledger. The people "
            "who held the line keep their silence and their chance. The truth "
            "of what was done here leaves the valley only with you - one "
            "survivor, carrying it, unheard. Maybe that was the kinder thing. "
            "Maybe it was just the safer one.",
        ),
    },
)
