"""World 2 - "The Wake": the FICTION of each escape mechanism, on a ship.
docs/WORLD_2_THE_WAKE.md §7, §10.1.

The GRAMMAR (family / discovery logic / placement / RNG) is engine-owned
(escape.MECHANISMS). This is only what a `power_station` / `dam_valves`
/ ... looks, sounds and reads like aboard a stopped colony ship. The
recurring problem: the direct route between one section and the next
has been severed - open to vacuum, sealed, or unpowered - and there is
another way through if you can work the ship.

Only the 8 mechanisms in manifest.supported_mechanisms are authored.
"""

MECHANISM_PROSE = {
    # spatial: a locked way, find the access ---------------------------
    "mountain_pass": {
        "name": "the ladderway",
        "closed": "The main lift trunk is dead - the car stuck between decks, its doors standing half open onto nothing. Nothing moves between sections that way.",
        "route": "A maintenance ladderway runs the full height of the ship, past every deck. It's the long way, but it's a way.",
        "obstacle": "The ladderway hatch onto the connecting deck is maglocked, and the lock has power when nothing else nearby does.",
        "require": "A deck officer's access card would drop the maglock. There's a duty locker in the crew section.",
        "item": "deck officer's access card",
        "obstacle_desc": "A maglocked hatch seals the ladderway where it passes the connecting deck.",
        "escape_desc": "The hatch releases. The ladderway carries on down past the sealed decks and lets you out into the next section.",
        "roles": {"closed": "the dead lift trunk", "route": "the ladderway hatch",
                  "obstacle": "the maglocked hatch", "require": "the duty locker"},
        "landmark": "A maintenance ladderway runs straight up through an open deck, rung after rung into the dark",
    },
    # spatial: a collapsed passage, clear it --------------------------
    "rail_tunnel": {
        "name": "the cargo rail",
        "closed": "The connecting passage between this section and the next is buckled shut - the deck above came down into it.",
        "route": "A cargo rail line runs the spine of the ship, flatbed to flatbed, all the way out to the shuttle bay.",
        "obstacle": "A section of the rail tunnel has collapsed. A structural bulkhead is down across the track - not impassable, but not walkable either.",
        "require": "The rail maintenance bay stocks the cutting gear for exactly this.",
        "item": "cutting torch",
        "obstacle_desc": "A fallen bulkhead blocks the rail tunnel. You'd need something to cut through it.",
        "escape_desc": "Past the cut the rail tunnel runs straight and level, a cold draught coming the other way, and opens into the next section.",
        "roles": {"closed": "the buckled passage", "route": "the rail maintenance bay",
                  "obstacle": "the collapsed rail tunnel", "require": "the cutting-gear store"},
        "landmark": "A cargo rail runs dead straight down the spine of the ship toward a distant bay",
    },
    # infrastructural, light: a locked access panel + key ------------
    "service_route": {
        "name": "the maintenance crawlway",
        "closed": "The connecting passage ahead is open to vacuum - the pressure door on the far side is simply gone.",
        "route": "A maintenance crawlway runs behind the compartments of this section, pressurised its whole length, and comes out past the breach.",
        "obstacle": "The crawlway is closed off partway by a locked engineering access panel.",
        "require": "The panel key is on the board in the section engineer's office.",
        "item": "engineering access key",
        "obstacle_desc": "A locked engineering access panel seals the maintenance crawlway.",
        "escape_desc": "The panel swings back. The crawlway carries on behind the compartments and lets you out on the far side, still in air.",
        "roles": {"closed": "the breached passage", "route": "the crawlway hatch",
                  "obstacle": "the locked access panel", "require": "the section engineer's office"},
        "landmark": "A maintenance crawlway runs behind the compartment wall, its hatch stencilled with a deck number",
    },
    # sequential: a marked route through a checkpoint ----------------
    "evac_corridor": {
        "name": "the evacuation route",
        "closed": "The direct way through is a debris field - a compartment wall failed and took the passage with it.",
        "route": "A marked evacuation route runs from here toward the muster bay - the deck stencils and the arrows are all still lit.",
        "obstacle": "The route is blocked where it crosses into the next section - an internal security checkpoint, its shutter down, never raised again.",
        "require": "The section security post holds the checkpoint override.",
        "item": "checkpoint override key",
        "obstacle_desc": "A security checkpoint shutter closes the evacuation route where it leaves the section.",
        "escape_desc": "The shutter grinds up. Past it the evacuation route runs clear and straight, the arrows still lit, carrying you out toward the bay.",
        "roles": {"closed": "the collapsed passage", "route": "an evacuation stencil",
                  "obstacle": "the security checkpoint", "require": "the section security post"},
        "landmark": "Evacuation stencils and lit arrows run along the deck, all pointing the same way",
    },
    # infrastructural: restore power to a dead door -----------------
    "power_station": {
        "name": "the spine door",
        "closed": "Every route between sections runs through a pressure door, and every pressure door on this deck is dead.",
        "route": "One pressure door - the one onto the connecting spine - still has a working control. It just has no power.",
        "obstacle": "The spine door's control panel is dark. The section it draws from is one of the sealed ones, and nothing is crossing that line.",
        "require": "A charged power cell is racked in the parts store.",
        "item": "charged power cell",
        "obstacle_desc": "The spine door's control panel is unlit. A conduit leaves it heading aft, toward the switching compartment.",
        "escape_desc": "The door runs back into its housing. The connecting spine is open, level and lit, straight through to the next section.",
        "roles": {"closed": "the dead pressure doors", "route": "the spine door",
                  "obstacle": "the spine door panel", "require": "the parts store",
                  "power": "the switching compartment"},
        "power_fact": "The spine door's power comes off the section bus in the switching compartment aft.",
        "power_obstacle_ev": "The spine door's panel is dead. A heavy conduit runs from it aft down the passage - the power's fed from somewhere else, and none is arriving.",
        "power_site_ev": "The section power bus stands here, cabled forward to the spine door. This is what feeds it.",
        "generator_ev": "The bus is intact, but its supply cell reads flat. It won't carry a load without a charge.",
        "power_restored_desc": "The cell seats and the bus takes the load. Forward down the passage, the spine door's panel lights up.",
        "landmark": "A dead pressure door stands across the passage, a heavy conduit running back from it into the wall",
    },
    # experimental: which override lifts THIS seal -----------------
    "dam_valves": {
        "name": "the lower deck",
        "closed": "The direct connection to the next section is through a deck that's been sealed - a blast door, floor to overhead.",
        "route": "The deck below this one runs straight through into the next section. It's clear - but the deck above it is the sealed one, and the seal holds both.",
        "obstacle": "The blast-door seal is set from a bank of section overrides in the deck control room. The switch labels don't match the wiring any more.",
        "require": "The deck control room - a row of override switches, and someone has peeled half the labels off.",
        "item": None,
        "obstacle_desc": "The blast-door seal runs the full height of the deck. There is no forcing it - it's set from the control room.",
        "escape_desc": "You drop through the lifted seal onto the lower deck and follow it straight through, out into the next section.",
        "roles": {"closed": "the sealed deck", "route": "the lower deck",
                  "obstacle": "the blast-door seal", "require": "the deck control room"},
        "controls": ["the section override", "the deck isolation switch", "the manual blast-door release"],
        "obvious_control": "the section override",
        "controls_prompt": "One of them lifts this deck's seal - but the labels have been swapped.",
        "controls_lore": "lifts this deck's seal",
        "control_wrong_obvious": "The section override throws, and a fault light comes up across the far side of the room. That one isolates the wrong deck entirely - it does nothing to this seal.",
        "control_wrong_other": "Something heavy shifts in the wall, then stops. The blast door drops a hand's width and holds. This one only takes part of the load.",
        "control_correct": "The switch throws and stays. The blast door cracks, then runs all the way up into its housing. The lower deck is open.",
        "landmark": "A row of override switches stands in a dark control room, half the labels peeled away",
    },
    # informational: bring the routing system up, it finds a way ---
    "radio_tower": {
        "name": "the routed passage",
        "closed": "Every marked route between sections is blocked, and the ship's deck plans are out of date - sections renumbered, passages that aren't where the schematic says.",
        "route": "A damage-control log, left open on the console: the ship's routing system still holds a live map of every open passage. If the console it runs on had power.",
        "obstacle": "The damage-control console is dead. Its panels are dark - no power reaching it at all.",
        "require": "A charged supply cell is stored in the equipment bay.",
        "item": "charged supply cell",
        "obstacle_desc": "The damage-control station is silent, every panel unlit.",
        "escape_desc": "The service passage runs exactly where the routing system put it, through a section the deck plans have as solid wall, and out into the next. This is the way through.",
        "roles": {"closed": "the outdated deck plans", "route": "the damage-control log",
                  "obstacle": "the damage-control console", "require": "the equipment bay",
                  "power": "the supply trunk"},
        "power_fact": "The routing system can still work you a way through - but only with the damage-control console running.",
        "power_obstacle_ev": "The console is dead. A supply line runs from it back to a trunk compartment - the power comes from there, and nothing is coming through.",
        "power_site_ev": "A supply trunk feeds the damage-control console from this compartment, cabled straight through the wall to it.",
        "generator_ev": "The trunk's supply cell is flat. It will not carry the console without a charge.",
        "power_restored_desc": "The cell seats. The damage-control console wakes, runs a check, and starts drawing a route across its screen.",
        "f_obstacle": "There is no route to see yet - not until the routing system is running and it works one out.",
        "d_route": "The way through isn't on the deck plans - it's whatever the routing system hands you once the console is up.",
        "route_reveal_ev": "The console finishes its check and lights a path: a service passage running {bearing}, through a section the schematics have as solid structure. It's on your map now.",
        "landmark": "A wall of dark damage-control panels stands in a control station, one screen flickering",
    },
    # transportation: a lifepod that needs two parts --------------
    "airfield_plane": {
        "name": "the lifepod",
        "closed": "Every connecting passage off this deck is either sealed or open to vacuum. There's no walking out of here.",
        "route": "A lifepod sits cradled in a launch tube two decks down - single-seat, but rated, fuelled, and the tube's clear all the way to the hull.",
        "obstacle": "The pod won't arm. Its power cell is pulled and its nav module is locked out - no launch without both.",
        "require": "The pod's power cell is on a charger in the pod bay.",
        "item": "pod power cell",
        "require2": "The nav module unlock key is held in the deck officer's safe.",
        "item2": "nav unlock key",
        "obstacle_desc": "The lifepod sits safed in its tube - no cell in the bay, no nav key, no launch.",
        "escape_desc": "The cell's seated and the nav's keyed. You strap in, the tube blows its cover, and the pod kicks clear of the hull. This is the way out.",
        "roles": {"closed": "the sealed deck", "route": "the launch tube",
                  "obstacle": "the safed lifepod", "require": "the pod bay",
                  "require2": "the deck officer's safe"},
        "assemble_desc": "You seat the power cell, key the nav module live, and the pod runs its arming sequence - green across the board. It's ready to launch.",
        "landmark": "A lifepod sits in an open launch tube, its hatch cracked and its cradle lights dead",
    },
}
