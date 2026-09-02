"""World 3 - "The Deep": the FICTION of each escape mechanism, in a mine.
docs/WORLD_3_THE_DEEP.md §5B.10.

The GRAMMAR (family / discovery logic / placement / RNG) is engine-owned
(escape.MECHANISMS). This is only what a `power_station` / `dam_valves`
/ ... looks, sounds and reads like down a deep working. The recurring
problem: the way down to the next level has been severed - a fall,
flooded, unpowered, or welded shut - and there is another way down if
you can work the mine.

Only the 8 mechanisms in manifest.supported_mechanisms are authored.
"""

MECHANISM_PROSE = {
    # spatial: a locked way, find the access -------------------------
    "mountain_pass": {
        "name": "the man-way",
        "closed": "The cage won't run past this level - the hoist rope's off its sheave and the shaft below stands dark. Nothing rides down that way.",
        "route": "A man-way ladder runs the wall of the shaft, stage after stage, all the way to the bottom levels. It's the long way, but it's a way.",
        "obstacle": "The man-way gate onto the level below is chained and padlocked, and the lock is new.",
        "require": "A shift boss keeps the man-way keys. There's a key press in the deputy's office.",
        "item": "man-way gate key",
        "obstacle_desc": "A chained gate seals the man-way where it passes onto the next level.",
        "escape_desc": "The chain drops. The man-way carries on down past the sealed levels and lets you out into the next working.",
        "roles": {"closed": "the dead shaft", "route": "the man-way gate",
                  "obstacle": "the chained gate", "require": "the deputy's office"},
        "landmark": "A man-way ladder climbs the shaft wall, stage after stage into the dark",
    },
    # spatial: a collapsed passage, clear it ------------------------
    "rail_tunnel": {
        "name": "the haulage drift",
        "closed": "The drift onto the next level is blocked - the back came down across it, floor to roof.",
        "route": "A haulage drift runs the length of the workings, tub track on tub track, out to the ore pass.",
        "obstacle": "A stretch of the haulage drift has fallen. A steel set is down across the track - not solid, but not walkable either.",
        "require": "The fitting shop stocks the cutting gear for exactly this.",
        "item": "cutting torch",
        "obstacle_desc": "A fallen steel set blocks the haulage drift. You'd need something to cut through it.",
        "escape_desc": "Past the cut the haulage drift runs straight and level, a cold draught coming up it, and opens onto the next level.",
        "roles": {"closed": "the fallen drift", "route": "the fitting shop",
                  "obstacle": "the collapsed haulage drift", "require": "the cutting-gear store"},
        "landmark": "A haulage drift runs dead straight along the tub track toward a distant ore pass",
    },
    # infrastructural, light: a locked access panel + key ----------
    "service_route": {
        "name": "the maintenance crawlway",
        "closed": "The drift down to the next level is flooded to the roof - the pumps that kept it clear have stopped.",
        "route": "A maintenance crawlway runs behind the pump stations of this level, above the water the whole way, and comes out past the flooded ground.",
        "obstacle": "The crawlway is closed off partway by a locked service panel.",
        "require": "The panel key is on the board in the level fitter's cabin.",
        "item": "service panel key",
        "obstacle_desc": "A locked service panel seals the maintenance crawlway.",
        "escape_desc": "The panel swings back. The crawlway carries on behind the pump stations and lets you out on the far side, on dry ground.",
        "roles": {"closed": "the flooded drift", "route": "the crawlway hatch",
                  "obstacle": "the locked service panel", "require": "the fitter's cabin"},
        "landmark": "A maintenance crawlway runs behind the pump-station wall, its hatch stencilled with a level number",
    },
    # sequential: a marked route through a checkpoint -------------
    "evac_corridor": {
        "name": "the escapeway",
        "closed": "The direct way down is gone - a rib failed and took the drift with it.",
        "route": "A marked escapeway runs from here toward the refuge station - the reflectors and the arrows are all still up.",
        "obstacle": "The escapeway is blocked where it drops to the next level - a self-closing fire door, dropped and never lifted.",
        "require": "The refuge station holds the door override.",
        "item": "fire-door override key",
        "obstacle_desc": "A dropped fire door closes the escapeway where it leaves the level.",
        "escape_desc": "The door lifts. Past it the escapeway runs clear and straight, the reflectors still catching your lamp, carrying you down to the next station.",
        "roles": {"closed": "the collapsed drift", "route": "an escapeway reflector",
                  "obstacle": "the dropped fire door", "require": "the refuge station"},
        "landmark": "Escapeway reflectors and painted arrows run along the drift, all pointing the same way",
    },
    # infrastructural: restore power to a dead door --------------
    "power_station": {
        "name": "the level door",
        "closed": "Every way down from this level runs through a powered door, and every powered door here is dead.",
        "route": "One door - the airlock onto the decline - still has a working control. It just has no power.",
        "obstacle": "The decline door's panel is dark. The circuit it draws from is one of the cut ones, and nothing is crossing that line.",
        "require": "A charged battery pack is racked in the store.",
        "item": "charged battery pack",
        "obstacle_desc": "The decline door's panel is unlit. A cable leaves it heading inbye, toward the switch room.",
        "escape_desc": "The door runs back into the wall. The decline is open, graded and lit, straight down to the next level.",
        "roles": {"closed": "the dead powered doors", "route": "the decline door",
                  "obstacle": "the decline door panel", "require": "the store",
                  "power": "the switch room"},
        "power_fact": "The decline door's power comes off the level circuit in the switch room inbye.",
        "power_obstacle_ev": "The decline door's panel is dead. A heavy cable runs from it inbye down the drift - the power's fed from somewhere else, and none is arriving.",
        "power_site_ev": "The level distribution board stands here, cabled outbye to the decline door. This is what feeds it.",
        "generator_ev": "The board is intact, but its battery bank reads flat. It won't carry a load without a charge.",
        "power_restored_desc": "The pack seats and the board takes the load. Outbye down the drift, the decline door's panel lights up.",
        "landmark": "A dead powered door stands across the drift, a heavy cable running back from it into the wall",
    },
    # experimental: which override lifts THIS seal -------------
    "dam_valves": {
        "name": "the level below",
        "closed": "The direct way on is through a level that's been sealed - a bulkhead door, floor to roof.",
        "route": "The level below this one runs straight through toward the next working. It's clear - but the level above it is the sealed one, and the seal holds both.",
        "obstacle": "The bulkhead seal is set from a bank of level overrides in the control cabin. The switch labels don't match the wiring any more.",
        "require": "The control cabin - a row of override switches, and someone has peeled half the labels off.",
        "item": None,
        "obstacle_desc": "The bulkhead seal runs the full height of the level. There is no forcing it - it's set from the control cabin.",
        "escape_desc": "You drop through the lifted seal onto the level below and follow it straight on, out toward the next working.",
        "roles": {"closed": "the sealed level", "route": "the level below",
                  "obstacle": "the bulkhead seal", "require": "the control cabin"},
        "controls": ["the level override", "the section isolation switch", "the manual bulkhead release"],
        "obvious_control": "the level override",
        "controls_prompt": "One of them lifts this level's seal - but the labels have been swapped.",
        "controls_lore": "lifts this level's seal",
        "control_wrong_obvious": "The level override throws, and a fault light comes up across the far side of the cabin. That one isolates the wrong level entirely - it does nothing to this seal.",
        "control_wrong_other": "Something heavy shifts in the wall, then stops. The bulkhead drops a hand's width and holds. This one only takes part of the load.",
        "control_correct": "The switch throws and stays. The bulkhead cracks, then runs all the way up into its housing. The level below is open.",
        "landmark": "A row of override switches stands in a dark control cabin, half the labels peeled away",
    },
    # informational: bring the routing system up, it finds a way -
    "radio_tower": {
        "name": "the routed drift",
        "closed": "Every marked way down is blocked, and the working plans are out of date - levels renumbered, drifts that aren't where the plan says.",
        "route": "A survey log, left open on the terminal: the mine's plan system still holds a live map of every open drift. If the terminal it runs on had power.",
        "obstacle": "The survey terminal is dead. Its screens are dark - no power reaching it at all.",
        "require": "A charged battery pack is stored in the lamp room.",
        "item": "charged battery pack",
        "obstacle_desc": "The survey station is silent, every screen unlit.",
        "escape_desc": "The service drift runs exactly where the plan system put it, through ground the working plans have as solid rock, and out onto the next level. This is the way down.",
        "roles": {"closed": "the outdated working plans", "route": "the survey log",
                  "obstacle": "the survey terminal", "require": "the lamp room",
                  "power": "the supply cable"},
        "power_fact": "The plan system can still work you a way down - but only with the survey terminal running.",
        "power_obstacle_ev": "The terminal is dead. A supply line runs from it back to a battery cabinet - the power comes from there, and nothing is coming through.",
        "power_site_ev": "A battery cabinet feeds the survey terminal from here, cabled straight through the wall to it.",
        "generator_ev": "The cabinet's battery pack is flat. It will not carry the terminal without a charge.",
        "power_restored_desc": "The pack seats. The survey terminal wakes, runs a check, and starts drawing a route across its screen.",
        "f_obstacle": "There is no route to see yet - not until the plan system is running and it works one out.",
        "d_route": "The way down isn't on the working plans - it's whatever the plan system hands you once the terminal is up.",
        "route_reveal_ev": "The terminal finishes its check and lights a path: a service drift running {bearing}, through ground the plans have as solid rock. It's on your map now.",
        "landmark": "A wall of dark survey screens stands in a control station, one of them flickering",
    },
    # transportation: a cage that needs two parts --------------
    "airfield_plane": {
        "name": "the auxiliary cage",
        "closed": "Every drift off this level is either sealed or flooded. There's no walking on from here.",
        "route": "An auxiliary cage sits in a service shaft two levels down - a maintenance skip, but rated, and the shaft's clear all the way to the bottom.",
        "obstacle": "The cage won't run. Its winder battery is pulled and its brake interlock is locked out - no descent without both.",
        "require": "The cage's winder battery is on a charger in the winder house.",
        "item": "winder battery",
        "require2": "The brake interlock key is held in the deputy's safe.",
        "item2": "brake interlock key",
        "obstacle_desc": "The auxiliary cage sits chocked in its shaft - no battery in the winder, no interlock key, no descent.",
        "escape_desc": "The battery's in and the brake's keyed. You pull the gate, the winder takes up, and the cage runs you down the service shaft. This is the way on.",
        "roles": {"closed": "the sealed level", "route": "the service shaft",
                  "obstacle": "the chocked cage", "require": "the winder house",
                  "require2": "the deputy's safe"},
        "assemble_desc": "You seat the winder battery, key the brake interlock live, and the cage runs its check - green across the board. It's ready to run.",
        "landmark": "An auxiliary cage sits in an open service shaft, its gate chocked back and its lights dead",
    },
}
