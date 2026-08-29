# Scenario seed library — todo `66dbacb5` / `9ab1b420` follow-up

Written 2026-08-29 (overnight session). The goal is no longer *"how
many escape mechanisms do we have"* — it is **"how many meaningfully
different mysteries can the generator produce."**

A player who has done `power_station` twice should not think *"the
power-station puzzle again."* They should think *"the bridge is down
and the river is rising — how do I get out?"* That comes from
recombining a small set of trustworthy story components, not from
writing hundreds of bespoke engines.

This file is **source material**, not a build queue. Each seed is
classified so a future generator pass can pick from a matrix; each is
tagged for how much machinery it needs.

---

## The matrix

Every generated mystery is a point in this space:

| dimension | values (current pool) |
|---|---|
| **situation** | flood · fire · collapse · isolation · storm · outage · quarantine |
| **route** | road · rail · river · tunnel · airstrip · bridge · causeway · mine · cable-car |
| **discovery** | document · observation · object · signal · person · anomaly |
| **reasoning** | locate · connect · corroborate · infer · experiment · sequence · triage |
| **dependency** | key · fuel · power · repair · multi-component · none |
| **resolution** | open · repair · clear · operate · reveal · follow · ride |
| **confirmation** | traversal · environmental-change · external-response · corroboration |
| **pressure** | none · tide · fire · storm · daylight · structural · scheduled-vehicle |
| **exit type** | gap · vehicle · revealed-route · crossing |

Even at 5 values per dimension that is a combinatorial space in the
tens of thousands. We need ~a dozen well-behaved components, not
thousands of scripts.

## The acceptance test

For every seed, one question decides:

> **"What does the player have to figure out here that is different
> from the last scenario?"**

- *"Find the thing, bring it to the gate."* → **reject.** Fake variety.
- *"Work out which valve drops the valley reservoir."* → keep.
- *"Decide whether two independent records actually agree on the route."* → keep.
- *"Restore a machine that then becomes the way out."* → keep.
- *"Get across before the tide returns — and skip the optional evidence."* → keep.

## Tags

- **SHIPPED** — a mechanism for this exists in `MECHANISMS` today.
- **reuses** — buildable from machinery that exists (or lands tonight)
  with only text + roles.
- **needs: X** — requires new machinery X.
- **combo** — carries more than one dimension; needs a mechanism that
  can hold two grammars at once.
- **kid-hard** — a legitimate seed but rough for a young player
  (permadeath, tight clock, ambiguity). Flag, don't cut.

---

## The full 16-field schema

Each row in the family tables below encodes the first 11 fields as a
`class` string (`situation / route / discovery / reasoning /
dependency / resolution / confirmation / pressure / exit-type`) plus
`premise` and `tag` (= machinery-need). The remaining fields —
**story signature**, **duplicate-of**, **kid rating** — are in
§"Full-schema completion" below, keyed by seed id, so a generator pass
has all 16 without re-deriving them.

- **story signature** `(family, dependency-class, exit-type)` —
  `dependency-class ∈ {none, single-item, checklist, restore-chain,
  control-choice, corroboration}`. Two seeds with the same signature
  are the same *shape* to the player even if the mechanism names
  differ; Rule C (see `SCENARIO_EXPANSION.md` §3) dedups on this.
- **duplicate-of** — another seed id this collapses onto under the
  acceptance test, or `—`. "Pick one" pairs are flagged both ways.
- **kid rating** — `kid-ok` or `kid-hard` + the reason (permadeath
  exposure, tight clock, genuine ambiguity, deep site nesting).

---

## 1. Spatial — *where is the way out?*

| seed | premise | class | tag |
|---|---|---|---|
| `mountain_pass` | ranger foot-pass over the ridge, behind a locked forestry gate | isolation / road / document / locate / key / open / traversal / none / gap | **SHIPPED** |
| `rail_tunnel` | rail tunnel through the eastern hills, mouth caved in | isolation / rail / document / locate / repair / clear / traversal / none / gap | **SHIPPED** |
| `storm_drain` | a municipal storm drain runs to a river *outside* the valley — nobody knew it was there; the access grate is the puzzle | flood / tunnel / anomaly / locate / key / open / traversal / none / revealed-route | **reuses** — discovery is the route's *existence*, not its location; closest spatial seed to a new beat |
| `border_station` | a pre-collapse border crossing, on no current map, checkpoint overgrown in forest | isolation / road / document / locate / clear / clear / traversal / none / gap | **reuses** |
| `logging_road` | a logging camp's alternate haul road out, itself blocked by a slide | collapse / road / document / locate / clear / clear / traversal / none / gap | **reuses** — near-duplicate of `border_station`; pick one |
| `service_footbridge` | a utility company's inspection catwalk across the gorge — you have to find where it starts | isolation / bridge / observation / locate / none / follow / traversal / none / crossing | **reuses** |

## 2. Infrastructural — *what dependency makes it work?*

| seed | premise | class | tag |
|---|---|---|---|
| `power_station` | tunnel gate is electric and dead; gate ← hydro station ← generator ← fuel | outage / tunnel / anomaly / infer / power / repair / environmental-change / none / gap | **SHIPPED** |
| `service_route` | dam service road gate, key in the control room | flood / road / observation / locate / key / open / traversal / none / gap | **SHIPPED** (light — really a fetch) |
| `rail_switch` | the line out is fine, but the junction is thrown the wrong way *and* the switch motor is dead: switch ← control box ← battery | isolation / rail / document / infer / power / operate / traversal / none / gap | **needs: a small experiment inside a dependency** — you restore power to the switch, then still have to set it right (which way?), a 2-state pull. Bridges infra ↔ experimental. |
| `lift_bridge` | a counterweight bascule bridge, raised and stuck; the winch needs hydraulic pressure ← pump ← power | flood / bridge / observation / infer / power / operate / environmental-change / none / crossing | **needs: escape_kind=crossing** (leave from the far side of a bridge, not a mountain gap) |
| `tunnel_vent` | the road tunnel is intact but the ventilation fans failed — the air's bad, you can't walk it until they run again: fans ← control room ← fuse | collapse / tunnel / observation / infer / repair / repair / environmental-change / none / gap | **reuses** power_station machinery almost exactly (restore a system → obstacle clears) |
| `elevator_shaft` | a mine cage lift down to a level that connects through; the lift needs power AND the brake released | collapse / mine / object / connect / multi-component / operate / traversal / none / revealed-route | **combo** — infra + a 2-item checklist (transportation machinery) |

## 3. Experimental — *what if my interpretation is wrong?*

| seed | premise | class | tag |
|---|---|---|---|
| `dam_valves` | the low road is under the reservoir; a bank of dam controls; the obvious one is never right | flood / road / anomaly / experiment / operate / operate / environmental-change / none / revealed-route | **SHIPPED** |
| `rail_junction_puzzle` | evidence says the old maintenance spur runs beyond the junction; three switch positions, you try them and watch where the line goes | isolation / rail / document / experiment / operate / operate / traversal / none / gap | **reuses** `controls` machinery — swap "pull a valve" for "throw a switch", consequence text tells you where the line went |
| `mine_junction` | first shaft is **not** the escape — it leads to an underground junction where you determine which of three tunnels actually reaches through; maps are incomplete, no lying evidence | collapse / mine / document / experiment / follow / follow / traversal / none / revealed-route | **needs: a second layer of sites** — reach junction, then the "which tunnel" experiment happens there. Deeper than `dam_valves`. **kid-hard.** |
| `sluice_bank` | three sluices; one floods the valley worse, one does nothing, one drops the road — with a *misleading* maintenance label ("Sluice 3 → lower spillway") that's out of date | flood / road / document / experiment / operate / operate / environmental-change / none / revealed-route | **reuses** `dam_valves` — the twist is a document that lies-by-being-stale, not by being false |

## 4. Informational — *what can I learn that I couldn't see?*

| seed | premise | class | tag |
|---|---|---|---|
| `radio_tower` | broadcast tower's transmitter is dead; fuel the generator, a voice answers and reads you a road that was never on any map | isolation / airstrip / signal / infer / repair / reveal / external-response / none / revealed-route | **SHIPPED** |
| `fire_lookout` | a lookout tower with a heliograph / signal lamp; repair it, flash the ridge, a response identifies an evacuation trail not visible from the ground | fire / road / signal / infer / repair / reveal / external-response / none / revealed-route | **reuses** `reveals_route` machinery — swap radio for a signal lamp, "a voice" for "a returning flash" |
| `smoke_sighting` | you see smoke beyond the western ridge at dusk; reaching a vantage point (the water tower) confirms it's a settlement with a working road | isolation / road / observation / locate / none / follow / corroboration / daylight / revealed-route | **needs: an observation-confirms mechanic** — no machine, the "restore" step is *getting to a place you can see from* |
| `beacon_bearing` | an emergency beacon is transmitting on a loop; a handheld set at the ranger station gives you a *direction* — signal strength rises as you head the right way | isolation / road / signal / locate / none / follow / external-response / none / revealed-route | **needs: directional-by-information** — the objective panel updates "the signal's stronger to the NE" as you move; a real new toy |
| `night_lights` | after dark, lights appear on a far hillside — someone's got power; by day you can't tell which of three settlements it was | outage / road / observation / corroborate / none / follow / corroboration / daylight / revealed-route | **combo** — informational + directional + a daylight/night pressure twist |

## 5. Corroborative — *can I trust this route?*

| seed | premise | class | tag |
|---|---|---|---|
| `two_maps_agree` | a ranger map shows an old trail west; a *geological survey* map independently shows an access road west — the journal establishes the route only once **both** are found | isolation / road / document / corroborate / none / follow / corroboration / none / gap | **needs: a "corroboration" fact-gate** — `F_ROUTE` doesn't land on either map alone, only on the deduction that they agree |
| `survey_route` | partial notes in one geologists' camp, the missing pages in another; combine → the completed survey shows a pass | collapse / road / document / corroborate / connect / follow / corroboration / none / revealed-route | **needs: same gate as `two_maps_agree`** + assembling a document from parts (sequential flavour) |
| `two_witnesses` | two separate survivor logs, different hands, both mention "the emergency station past the north ridge" — one alone could be a rumour, two is a lead | isolation / road / document / corroborate / none / follow / corroboration / none / revealed-route | **reuses** the corroboration gate once it exists |
| `label_vs_thing` | a maintenance log says "Valve 3 controls the lower spillway"; you find three valves physically stamped 1/2/3 — the document + the physical evidence corroborate which one to pull | flood / road / document / corroborate / experiment / operate / corroboration / none / revealed-route | **combo** — corroborative + experimental; the corroboration *reduces* the experiment from 3 tries to 1 |

## 6. Sequential — *a route assembled from several places*

| seed | premise | class | tag |
|---|---|---|---|
| `ranger_network` | station A points to station B points to station C, which holds the trail-network map out | isolation / road / document / sequence / none / follow / traversal / none / revealed-route | **needs: N ordered sites** — each site's evidence names the next; the route only completes at the last |
| `survivor_caches` | three roadside caches: "don't use the highway" → "the quarry road's still open" → "the gate has a manual release" | isolation / road / object / sequence / key / open / traversal / none / gap | **needs: ordered sites** (same machinery); ends in a normal spatial resolution |
| `emergency_relay` | radio station → relay tower → ranger post → the ranger post has the extraction coordinates | isolation / road / signal / sequence / repair / reveal / external-response / none / revealed-route | **combo** — sequential + informational (restore the relay chain, *then* the response) |

## 7. Directional — *which way, and can I trust the clue?*

| seed | premise | class | tag |
|---|---|---|---|
| `river_leads_out` | "the river runs toward the old highway" — follow the watercourse, it exits the valley where the map says a bridge once was | flood / river / observation / locate / none / follow / traversal / none / crossing | **reuses** — the route *is* a terrain feature; follow it |
| `sunset_firebreak` | "at sundown the light picks out the firebreak on the eastern slope" — only visible at dusk, from the right spot | fire / road / observation / locate / none / follow / traversal / daylight / revealed-route | **needs: time-of-day-gated visibility** on a site marker |
| `ridge_bearing` | "the pass lies beyond the highest ridge" — the objective points you at the tallest boundary segment; the actual gap is there | isolation / road / document / locate / none / follow / traversal / none / gap | **reuses** — but see the **directional-truth guarantee** below |

> **Directional-truth guarantee (build-time invariant, this session).**
> Any compass word in generated evidence — "toward the {bearing}
> edge", "stronger to the NE" — must agree with the vector to the site
> it names. A build-time assertion catches "every clue says north, the
> gap is southwest." That's broken trust, not difficulty.

## 8. Environmental — *the world changes when I solve it*

| seed | premise | class | tag |
|---|---|---|---|
| `drain_tunnel` | a flooded road tunnel; a pump house upstream, restore it, the tunnel drains — **new passable tiles appear** | flood / tunnel / observation / infer / operate / reveal / environmental-change / none / revealed-route | **needs: region mutation** — a set of tiles flips impassable→passable on solve. The `★ THE WATER IS RECEDING` beat. |
| `dam_spillway` | redirect the reservoir through a spillway → a lower valley road is *exposed* (this is `dam_valves` but the payoff is new tiles, not one obstacle tile) | flood / road / document / infer / operate / reveal / environmental-change / none / revealed-route | **needs: region mutation**; can share the hook with `drain_tunnel` |
| `firebreak_race` | an old firebreak to an access road; you have to *clear* a section of it, and the fire is advancing — the escape boundary moves as the fire does | fire / road / observation / locate / clear / clear / traversal / fire / revealed-route | **combo** — environmental + time-pressure; the pressure source is the fire, not a tide |
| `sprinkler_system` | a fire blocks the route; the orchard's irrigation system, restarted, wets a corridor through it | fire / road / anomaly / infer / operate / clear / environmental-change / none / gap | **reuses** power_station-style restore, but the "obstacle" is fire and clearing it is the environmental change |

## 9. Time-pressure — *what must I finish before it changes?*

| seed | premise | class | tag |
|---|---|---|---|
| `tidal_causeway` | a stone causeway to a headland with a footbridge beyond; walkable only at low tide; reading the tide table starts an ~18-24 turn clock | isolation / causeway / document / triage / none / follow / traversal / tide / crossing | **needs: deadline machinery** — building tonight |
| `storm_road` | the mountain road out is passable now, but a storm front is coming; when it hits, the road washes/ices over | storm / road / observation / triage / none / follow / traversal / storm / gap | **reuses** deadline machinery once it exists — swap "the tide turns" for "the storm hits" |
| `scheduled_train` | a maintenance train runs the line out **once** — you have to be at the platform when it passes | isolation / rail / document / triage / none / ride / traversal / scheduled-vehicle / vehicle | **combo** — time-pressure + transportation; miss the window, wait for tomorrow's pass (soft failure) |
| `rescue_window` | a rescue helicopter will put down at the old sports field at a stated time; be there, cleared and confirmed, or it leaves | isolation / airstrip / signal / triage / repair / reveal / external-response / scheduled-vehicle / vehicle | **combo** — informational (restore contact → get the time) + time-pressure + transportation. **kid-hard.** |
| `collapsing_mine` | the mine route through is open but the timbers are going — every few turns a section further back seals; you can't dawdle or backtrack | collapse / mine / observation / triage / none / follow / traversal / structural / revealed-route | **needs: deadline + a no-backtrack twist**. **kid-hard.** |

## 10. Transportation — *what can I restore and ride/fly away in?*

The exit is a machine, at a location, needing one or more things.

### Air
| seed | premise | needs | tag |
|---|---|---|---|
| `airfield_plane` | crop-duster: fit the propeller (hangar) + fuel it (field store), fly out | **requirement_items** (2 parallel) | building tonight |
| `bush_plane` | STOL plane on a short strip: battery + fuel + a fallen tree cleared off the runway | 3-item checklist + a clear step | **needs: 3 items**; stretch |
| `rescue_helicopter` | see `rescue_window` above | combo | kid-hard |

### Ground
| seed | premise | needs | tag |
|---|---|---|---|
| `snowplow` | the mountain road is blocked by drifts; a plow at the depot needs keys + diesel, then it opens the road for you | 2-item + the plow *clears the route* (environmental-ish) | **reuses** transportation machinery + a clear-on-operate |
| `service_bulldozer` | a dozer at the quarry, needs a battery; drive it at the landslide, it clears | 1-item + operate-clears | **reuses** — single item, so almost free once `escape_kind`/operate exists |
| `utility_truck` | a works truck at the yard: battery + fuel; drive the service route out | 2-item, `escape_kind=vehicle` | **needs: escape_kind=vehicle** (leave from the truck, no gap) |
| `handcar` | a rail handcar in a maintenance shed; find it, and set the junction right to reach the outside line | 1-item (the car) + a switch-setting (experimental) | **combo** — transportation + experimental |

### Water
| seed | premise | needs | tag |
|---|---|---|---|
| `boat_crossing` | fuel a boat at the marina, motor out | 1-item | **SHIPPED** — leave it alone |
| `ferry` | a cable ferry across the reservoir; restore its winch motor, operate it across | 1-item + operate | **reuses** |
| `rescue_boat` | a launch on a davit at the rescue station; find fuel, lower it, cast off | 1-item, `escape_kind=vehicle` | **needs: escape_kind=vehicle** |

---

## Full-schema completion — signature · duplicate-of · kid rating

| seed | story signature | duplicate-of | kid rating |
|---|---|---|---|
| `mountain_pass` | spatial · single-item · gap | — | kid-ok |
| `rail_tunnel` | spatial · single-item · gap | — | kid-ok |
| `storm_drain` | spatial · single-item · revealed-route | — | kid-ok |
| `border_station` | spatial · none · gap | `logging_road` | kid-ok |
| `logging_road` | spatial · none · gap | `border_station` (pick one) | kid-ok |
| `service_footbridge` | spatial · none · crossing | — | kid-ok |
| `power_station` | infrastructural · restore-chain · gap | — | kid-ok |
| `service_route` | infrastructural · single-item · gap | `mountain_pass` (fetch) | kid-ok |
| `rail_switch` | infrastructural · restore-chain+control-choice · gap | — | kid-hard (2-stage: restore *then* a which-way pull) |
| `lift_bridge` | infrastructural · restore-chain · crossing | — | kid-ok |
| `tunnel_vent` | infrastructural · restore-chain · gap | `power_station` (near-dup, share hook) | kid-ok |
| `elevator_shaft` | infrastructural · checklist · revealed-route | — | kid-hard (two subsystems + nesting) |
| `dam_valves` | experimental · control-choice · revealed-route | — | kid-hard (genuine ambiguity — solved on 2nd try in playtest) |
| `rail_junction_puzzle` | experimental · control-choice · gap | `dam_valves` | kid-hard (same ambiguity) |
| `mine_junction` | experimental · control-choice · revealed-route | — | kid-hard (deep site nesting + ambiguity) |
| `sluice_bank` | experimental · control-choice · revealed-route | `dam_valves` (stale-label twist) | kid-hard |
| `radio_tower` | informational · restore-chain · revealed-route | — | kid-ok (solved by every kid; deaths were survival-layer) |
| `fire_lookout` | informational · restore-chain · revealed-route | `radio_tower` (lamp for radio) | kid-ok |
| `smoke_sighting` | informational · none · revealed-route | — | kid-ok |
| `beacon_bearing` | directional · none · revealed-route | — | kid-hard (warmer/colder navigation, no map marker) |
| `night_lights` | informational · none · revealed-route | `smoke_sighting` + day/night twist | kid-hard (day/night gate) |
| `two_maps_agree` | corroborative · corroboration · gap | — | kid-hard (must reason "do these agree", not "find X") |
| `survey_route` | corroborative · corroboration · revealed-route | `two_maps_agree` + doc-assembly | kid-hard |
| `two_witnesses` | corroborative · corroboration · revealed-route | `two_maps_agree` | kid-hard |
| `label_vs_thing` | corroborative · corroboration+control-choice · revealed-route | — | kid-hard (combo) |
| `ranger_network` | sequential · none · revealed-route | — | kid-ok (linear, each site points to the next) |
| `survivor_caches` | sequential · single-item · gap | `ranger_network` (same machinery) | kid-ok |
| `emergency_relay` | sequential · restore-chain · revealed-route | — | kid-hard (chain + response) |
| `river_leads_out` | directional · none · crossing | — | kid-ok (follow the water) |
| `sunset_firebreak` | directional · none · revealed-route | — | kid-hard (time-of-day visibility) |
| `ridge_bearing` | spatial · none · gap | `mountain_pass` (thin) | kid-ok |
| `drain_tunnel` | environmental · restore-chain · revealed-route | — | kid-ok |
| `dam_spillway` | environmental · control-choice · revealed-route | `drain_tunnel` (share region-mutation hook) | kid-hard |
| `firebreak_race` | environmental · none · revealed-route | — | kid-hard (advancing fire = moving deadline) |
| `sprinkler_system` | environmental · restore-chain · gap | `power_station` (restore→clear) | kid-ok |
| `tidal_causeway` | time-pressure · none · crossing | — | kid-hard (clock + triage; soft failure softens it) |
| `storm_road` | time-pressure · none · gap | `tidal_causeway` (same deadline machinery) | kid-hard |
| `scheduled_train` | time-pressure · single-item · vehicle | — | kid-hard (window + vehicle) |
| `rescue_window` | time-pressure · restore-chain · vehicle | — | kid-hard (restore→time→be-there) |
| `collapsing_mine` | time-pressure · none · revealed-route | — | kid-hard (clock + no-backtrack) |
| `airfield_plane` | transportation · checklist · gap | — | kid-ok (two items, order-free, machine tells you what's missing) |
| `bush_plane` | transportation · checklist(3) · gap | `airfield_plane` (more items) | kid-hard (3 items + clear step) |
| `snowplow` | transportation · checklist · gap | — | kid-ok |
| `service_bulldozer` | transportation · single-item · gap | — | kid-ok |
| `utility_truck` | transportation · checklist · vehicle | — | kid-ok |
| `handcar` | transportation · single-item+control-choice · gap | — | kid-hard (combo) |
| `boat_crossing` | transportation · single-item · crossing | — | kid-ok |
| `ferry` | transportation · single-item · crossing | `boat_crossing` | kid-ok |
| `rescue_boat` | transportation · single-item · vehicle | `boat_crossing` + escape_kind | kid-ok |

**Signature census** (what the pool actually covers today vs after
tonight):

- `* · single-item · gap` — 4 seeds (`mountain_pass`, `rail_tunnel`,
  `service_route`, `survivor_caches`). Over-represented; Rule C should
  bias against a third in a row.
- `infrastructural · restore-chain · *` — 6 seeds. The workhorse; keep
  it but vary the situation (level 2).
- `experimental · control-choice · *` — 5 seeds, all kid-hard.
- `* · corroboration · *` — 4 seeds, all blocked on the gate.
- `transportation · checklist · *` — 4 seeds, unlocked by tonight's
  `requirement_items`.
- `time-pressure · * · *` — 5 seeds, unlocked by tonight's `deadline`.

---

## Combinations — the ones worth the machinery

These are stories, not puzzles. Each needs a mechanism that can carry
**two dimensions at once**. That's the next real generator capability
after tonight.

### "The flooded railway"
> signal (a rail signal still cycling) → corroborate (two maintenance
> logs agree the line reaches outside) → infrastructure (the switch
> needs power) → transportation (a maintenance loco takes you out) →
> time-pressure (the water's rising).

Five dimensions. Needs: corroboration gate + `escape_kind=vehicle` +
deadline + `rail_switch`-style experiment. The payoff is enormous —
it reads as an adventure, not a mechanic.

### "The burning dam"
> observe smoke → find the dam → the road below is flooded → find the
> control room → infer which sluice → experiment → water recedes → the
> road appears → the fire reaches the valley → escape.

Environmental (region mutation) + experimental + time-pressure (fire).
Needs: region mutation + `firebreak_race`-style advancing pressure.

### "The last train"
> `scheduled_train` — you have N turns, the train passes the junction
> once, and the junction is thrown wrong. Set it, be on the platform.

Transportation + time-pressure + a switch experiment. Soft failure:
miss it, the *next* day's train.

---

## Build priority (post-tonight)

Ranked by *new-question-per-unit-machinery*:

1. **Deadline machinery** (`tidal_causeway`) — unlocks `storm_road`,
   half of every combo. Building tonight.
2. **`requirement_items`** (`airfield_plane`) — unlocks the whole
   ground/water transportation column with text only. Building tonight.
3. **Corroboration gate** (`two_maps_agree`) — unlocks 4 seeds, and
   it's the one that makes the Evidence→Deduction→Hypothesis model
   *earn its keep*. Small, self-contained. **Top candidate for
   Phase 5.**
4. **Region mutation** (`drain_tunnel`) — the `★ THE WATER IS RECEDING`
   experience. Unlocks the environmental column. Medium — a tile-set
   flip hook. Phase 5 stretch.
5. **`escape_kind=vehicle`** — cosmetic-ish (leave from the machine,
   not a gap) but it's what makes `utility_truck` / `rescue_boat` read
   right. Low risk, do it with region mutation.
6. **N ordered sites** (`ranger_network`) — sequential family. Distinct
   but lower value; the "several buildings matter" benefit is real but
   the puzzle is thin.
7. **Directional-by-information** (`beacon_bearing`) — a genuinely new
   toy (a live warmer/colder signal) but needs objective-panel and
   movement-hook work. Later.

## What this replaces

The seven Tier-1 fetch reskins (`e2850fa5`) are **cut**. Every one of
them is "find the thing, bring it to the gate" with new scenery —
exactly what the acceptance test rejects. Where a reskin idea had a
real different question (`storm_drain`'s "didn't know it existed",
`quarry` → `service_bulldozer`'s operate-a-machine), it survives here
as a proper seed instead.
