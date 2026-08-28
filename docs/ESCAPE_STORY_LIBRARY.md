# Escape story library — candidate scenarios & the archetype matrix

Source: playtest-driven brainstorm, 2026-08-28. The five current
`MECHANISMS` (mountain_pass, rail_tunnel, service_route, boat_crossing,
evac_corridor) all reduce to **find obstacle → find requirement item →
use item → walk through a gap**. After ~3 expeditions a player learns
"v4 grammar = find the thing that gets me through the mountain." This
doc is the backlog for breaking that.

## The goal: not 30 mechanisms, a component matrix

Turn escape "mechanisms" into **story archetypes with interchangeable
components**, and deliberately ensure the generator can produce
different *kinds of reasoning*:

- **spatial** — where is it, physically
- **directional** — which way, relative to spawn / the boundary
- **corroborative** — two documents must agree before you trust a route
- **infrastructural** — a dependency chain (gate ← power ← generator ← fuel)
- **environmental** — solving it changes the world (drain water, clear fire)
- **informational** — a clue changes what you can *perceive*, not where to go
- **sequential** — a route assembled from several locations
- **experimental** — a wrong-but-reasonable reading, revised via consequences

### Component pools

| Category | Components |
|---|---|
| Transportation | boat · train · helicopter · cable car · vehicle · aircraft |
| Infrastructure | dam · power station · railway · quarry · mine · construction site |
| Natural routes | pass · cave · river · canyon · firebreak · logging trail |
| Emergency systems | evacuation route · radio beacon · ranger network · emergency airstrip · rescue station |
| Environmental intervention | clear obstruction · restore power · drain water · repair bridge · excavate tunnel · operate machinery |

`radio beacon + ranger station + mountain trail` should feel like a
completely different story from `boat + marina + navigation chart`.

## Tier 1 — fit the current engine shape (obstacle + item + gap)

Text + role additions to `MECHANISMS`, minimal new machinery:

1. **Flooded highway** — washed-out highway; road maintenance depot has a portable bridge; assemble it at the works yard. (infrastructural)
2. **Logging road** — main road ends at a slide; a logging operation's alternate route; camp → route maps → equipment shed → blocked logging road. (spatial, wilderness)
3. **Landslide detour** — landslide blocks the valley; road crew had a secondary route, itself blocked by debris; find the equipment, clear it. (spatial)
4. **Quarry haul road** — quarry abandoned after a slide; survey map shows an old haul road out; blocked by equipment; a dozer still works but needs a battery/fuel. (environmental-lite: operate machinery)
5. **Construction project** — half-built highway that actually reaches past the mountain; equipment scattered; find plans + equipment + fuel + access road; clear the unfinished section. (infrastructural)
6. **Border station** — valley once had a border crossing, no obvious road; checkpoint docs → overgrown checkpoint hidden in forest → clear it, follow the road. (bureaucratic/spatial)
7. **Storm drain** — heavy rain reveals an old drainage system connecting to a river outside; entrance inaccessible until you find the right access point. (spatial, "didn't know it existed")

## Tier 2 — environmental intervention (the world changes on solve)

Needs: a tile/region state flip on completion, not just `obstacle_open`.

8. **Dam spillway** — dam control room → maintenance schematics → locked service access → valve controls → redirect the water → a road through the lower valley is *exposed* (new passable tiles appear). (environmental)
9. **Power station** — the road tunnel's gate is electric and dead; gate → power dependency → hydro station → fuel/fuse → restored power → gate opens. Dependency chain, not a key. (infrastructural)
10. **Forest fire firebreak** — a fire blocks one side; player thinks "escape the fire"; evidence reveals an old firebreak leading to an access road; the escape boundary *moves* as the fire does. (environmental, directional)

## Tier 3 — informational (the clue changes what you can perceive)

Needs: a "restore a system → receive a response → the response reveals
a route that was not visible before" beat. The clue is not a location.

11. **Radio tower** — emergency broadcast tower; log says the valley's channel is still monitored from outside; dead generator → generator shed → fuel → transmission restored → response confirms outside contact → follow a marked emergency access road that only appears after contact.
12. **Fire lookout** — logbook: "smoke beyond the western ridge"; the lookout has a signaling system; repair it → a response identifies an evacuation trail not visible from the ground.
13. **Radio beacon** — an old beacon is transmitting; follow signal strength (a directional-by-information mechanic) to a hidden emergency station → coordinates for an extraction point.

## Tier 4 — the weird ones (new reasoning shapes)

14. **The mine junction** — abandoned mine, multiple shafts; survey docs say one connects through the mountain; entrance collapsed, need mining equipment; **the first shaft is not the escape** — it leads to an underground junction where the player determines which tunnel is the real route. Ambiguity without lying evidence. (experimental)
15. **Dam control puzzle** — several valves control different dam sections; the player finds the wrong one first; evidence doesn't lie, the player misunderstands which system controls the road; they experiment, observe consequences, revise. Directly exercises Observation → Interpretation → Hypothesis → Action → Result → Revision. (experimental)
16. **The stranger's cache** — a survivor left caches around the valley; each holds one line of a route ("don't take the highway" → "the old service trail starts behind the quarry" → "the gate has a manual release"). Distributed narrative; no survivor to find. (sequential)
17. **Ranger network** — several ranger stations, each with part of the trail network; one log: "if the eastern station is unreachable, use the old western trail." Following the network reveals the exit. Makes *several* locations meaningful without making *every* building meaningful. (sequential, corroborative)
18. **Survey route** — a geological team mapped a mountain route; their camp has partial notes, another camp the missing pages; combine → the completed map reveals a pass. Pure information escape, no machine. (corroborative)
19. **Avalanche tunnel** — the tunnel is buried and not initially visible; map + survey notes + terrain observation reveal where it *should* be; you excavate it. The investigation discovers the route's *existence*, not just its location. (informational + environmental)
20. **The train that isn't there** — a timetable shows a train that should have passed through; a railway signal still works; following the rail leads to a maintenance junction; the real escape is an old service tunnel. The train clue is a *misleading interpretation*, not false evidence. (experimental)

## Tier 5 — transportation restoration (mental model shift: "restore transport" not "find a path")

21. **Damaged helicopter** — at an emergency landing site; can't fly; damaged rotor → maintenance records → parts at a facility → fuel elsewhere → repair → escape by air.
22. **Emergency airstrip** — runway intact, plane isn't; evidence reveals the plane was moved to a hangar; find, repair, refuel. Mechanically like the boat, feels completely different.
23. **Cable crossing** — old aerial cable system across a canyon; platform + cable exist, motor is broken; maintenance shed → replacement belt → fuel/power → operating instructions → ride across. Spatially unlike a tunnel or road.

## Tier 6 — time as pressure (not hunger)

24. **The dam is about to fail** — you're racing to reach an evacuation route before the dam becomes dangerous; rising water / failed monitoring / emergency route / locked emergency gate; figure out which route is still viable. Introduces *time* as story pressure.

## Also captured

The reservoir (boat + infrastructure + underwater maintenance route
converge), prison convoy route (secure transport road, credentials →
gate), hidden border station (dup of #6).
