# Scenario expansion — levels of randomness, variety rules, validation

Written 2026-08-29 (overnight build, Phase 1). Companion to
`SCENARIO_SEEDS.md` (the seed inventory) and `ESCAPE_STORY_SCHEMA.md`
(the vocabularies and invariants).

This document captures **direction**, not code. It answers one
question: *when the generator picks an escape mystery, what exactly is
it choosing among, and how do we keep the choices good?*

---

## 1. The principle: authored randomness, not procedural soup

Every component the generator can pick is **human-designed and
validated**. The generator never invents prose, never assembles a
sentence from fragments, never picks a "situation" and a "route" that
haven't been checked to read together. It chooses among a pool of
known-good possibilities.

The player should feel *authored variety* — "this is a different
story" — not *procedural noise* — "this is the same three nouns
shuffled." The test for whether a new axis-value earns its place is the
acceptance test from `SCENARIO_SEEDS.md`:

> **What does the player have to figure out here that is different from
> the last scenario?**

If the answer is "nothing, it's the same reasoning with new scenery,"
the value does not go in the pool.

---

## 2. The five levels of randomness

The generator's output varies at five nested levels. Today only
level 1 (partly) and levels 3–4 are live. Levels 2 and 5 are the
post-tonight roadmap.

### Level 1 — scenario selection *(live, coarse)*

`choose_mechanism()` picks one of the `MECHANISMS` entries via a
shuffle-bag (no repeat until the pool is exhausted) with a
no-back-to-back-family rule. Each entry is a whole authored scenario:
its prose, its family, its site roles, its resolution verb.

**What's missing:** the pool is only ~9 entries and each is a fixed
point in the matrix. Two `power_station` expeditions are *identical*
apart from map layout. Level 2 fixes this.

### Level 2 — component selection *(roadmap)*

Within a chosen *family + reasoning shape*, swap interchangeable
components:

- **situation**: the same infrastructural puzzle framed as a flood, a
  wildfire, an ice storm, a chemical spill. Changes the `closed`
  prose, the abandonment flavour, sometimes the terrain paint.
- **route feature**: gate ← tunnel vs gate ← bridge vs gate ← rail
  cut. Changes `route`/`escape_desc` prose and the site label.
- **dependency object**: fuel vs a battery vs a fuse vs hydraulic
  fluid. Pure text over the same "restore a system" machinery.
- **site labels**: "the hydro station" / "the substation" / "the pump
  house" — a validated pool per role.

The rule: a component swap may change **prose, labels, and terrain
paint**. It may **not** change the reasoning the player does. If it
would, it's a new scenario (level 1), not a component (level 2).

This is the "twenty story-shapes per grammar" lever from the night
plan. It's authored: each situation × family combination is a row in a
table someone wrote and `Mystery.validate()` checks.

### Level 3 — site-layout randomness *(live)*

`build_mystery()` places the role sites onto whatever buildings the
map generator produced, subject to the pacing constraints (invariant
3d): `closed` near spawn, `route` in the middle band of the
spawn→exit run, `require`/`power`/`require2` as bounded side-trips.
The escape gap is carved at the ~65th-percentile boundary segment by
spawn distance.

Same scenario, different map → the *geography* of the investigation
changes: how far the detours are, which direction the exit lies, how
much traversal sits between beats.

### Level 4 — evidence-layout randomness *(live, thin)*

Which evidence sits at which site is currently fixed per family
(`_site_evidence` is built deterministically). The only live variation
is the experimental family's `correct_control` (a random non-obvious
pick) and the directional bearing folded into `E_obstacle_a` /
`E_route_reveal` (derived from the carved gap direction, so it varies
with level 3).

**Roadmap:** let a fact's two-or-more evidence routes land at
*different* site combinations across expeditions, so a returning
player can't pattern-match "the second clue is always at the
noticeboard."

### Level 5 — composition *(roadmap, the real prize)*

Combine two grammars in one mystery: infrastructural + time-pressure
("restore the pump before the water rises"), corroborative +
experimental ("the stale label narrows three valves to one"),
sequential + informational ("relay the chain, then the voice
answers"). See `SCENARIO_SEEDS.md` §Combinations.

Needs a `Mystery` that can hold two reasoning shapes at once and a
generator that knows which pairs are coherent. This is the capability
that follows the tonight-built primitives.

---

## 3. Variety rules

Three rules keep consecutive expeditions feeling different. Rule A is
live; B and C are Phase 5 tonight (or the next night).

- **Rule A — no back-to-back family** *(live, `choose_mechanism`,
  persisted since `73ff535`)*. `spatial → spatial` can't happen while
  another family is available.

- **Rule B — recent-scenario history** *(Phase 5)*. A short ring of
  the last N *mechanisms* (not just families), persisted alongside
  `_used_mechanisms`. Stops `power_station → dam_valves →
  power_station` — different families, same two scenarios on rotation.

- **Rule C — story-signature dedup** *(Phase 5)*. A signature computed
  from the matrix classification — `spatial · single-item · gate`,
  `infrastructural · restore-system · gate`, `transportation ·
  checklist · gap`. `key→gate`, `fuel→gate`, `battery→gate` all
  reduce to the same signature, so the generator recognises them as
  the same *shape* even across different mechanism names and steers
  away from repeating it. This is what makes level 2 (component swaps)
  safe: swapping fuel for a battery doesn't fool the dedup.

Signature formula (draft):

```
signature = (family, dependency_class, exit_type)
  dependency_class ∈ {none, single-item, checklist, restore-chain,
                      control-choice, corroboration}
  exit_type        ∈ {gap, vehicle, revealed-route, crossing}
```

Persist the last 2–3 signatures. On generation, drop any candidate
whose signature is in the recent set unless that empties the pool.

---

## 4. Expanded validation

`Mystery.validate()` today checks **structural** validity (every fact
has ≥2 evidence routes, the hypothesis is confirmable, the
classification is in-vocabulary, obstacle/escape tiles exist). The
expansion adds four more categories. Each is a build-time assertion —
a broken mystery is a generation bug caught before the player sees it,
same contract as `_ensure_reachable`.

### 4a. Structural validity *(live)*

- ≥2 independent evidence routes per load-bearing fact.
- Hypothesis `confirmed_by` names a real evidence id.
- Obstacle tile and escape tile both set.
- `power_role` / `controls` / `requirement_items` consistent with the
  family.
- Classification axes all drawn from the closed vocabularies.

### 4b. Evidence validity *(live, partial → expand)*

- Every evidence `location` role exists in `m.sites` (or is a known
  sentinel like `_deferred`).
- No evidence names a route/site the player can't yet know about
  (the `reveals_route` leak guard — currently a hand-coded drop of
  `E_route_b`; generalise to "no evidence at an early site may name
  the mechanism by name for a `reveals_route` mystery").
- Every `search`-method evidence sits at a site the player can reach
  before the obstacle is open.

### 4c. Geographic validity *(live — the pacing invariant)*

- Every site and the escape tile reachable from spawn (with the
  obstacle open). Carve an approach for any that isn't.
- Invariant 3d: critical-path sites carry momentum toward the exit;
  side sites detour but bounded (`_detour(p) <= map_size * 0.5`).
- **New (Phase 4):** directional truth — any compass word in
  generated evidence must agree with the vector from spawn (or from
  the site it's read at) to the site it names. See §5.

### 4d. Story validity *(new)*

- No vocab leak: the rendered prose (evidence text, banners,
  objective lines) never contains `family` / `escape_kind` /
  `reasoning:` / a raw pattern name. A build-time scan of the
  generated strings against the vocabulary token lists.
- The `closed` situation and the `route` feature read together: a
  water `closed` ("the reservoir came up over the road") pairs with a
  water-adjacent route, not "the airstrip is flooded but fine."
  Enforced by only pairing situation × route from an authored table
  (level 2).
- Confirmation matches the family: `traversal` families end on
  `E_confirm` at the escape tile; `external_response` /
  `environmental` families end on their own evidence and don't force
  a post-solution trek.

### 4e. Variety validity *(new — Phase 5)*

- The chosen mechanism's signature is not in the recent-signature
  ring (Rule C).
- The mechanism is not in the recent-mechanism ring (Rule B).
- The family ≠ last family (Rule A, live).

---

## 5. Directional-truth guarantee (Phase 4, this session)

A build-time assertion in `build_mystery()` after the bearing is
computed:

> For every piece of generated evidence containing a compass word
> (`north`, `south`, `east`, `west`, or a hyphenated pair), the word
> must match the sign of the vector from the point where that evidence
> is read to the site or tile the sentence is about.

Today the only compass words the generator emits are:

- `E_obstacle_a` — "It's out toward the {bearing} edge of the
  valley." → must match spawn→escape_tile vector.
- `E_route_reveal` — "an emergency access road up the {bearing}
  ridge" → must match spawn→escape_tile vector.
- Objective-panel `heading()` / `_compass()` — computed live from the
  player's position, so always true by construction.

Both generated cases derive `{bearing}` from `escape_tile - spawn`
directly, so they're correct *today*. The assertion is a **regression
guard** for level 2 (when a component swap might hard-code a direction
into `closed`/`route` prose) and for any future authored clue that
names a direction. If a mechanism's prose says "the pass lies beyond
the eastern ridge" and the gap carved west, `validate()` raises.

Implementation: `_compass_words(text)` returns the set of cardinal
tokens in a string; for each evidence whose text has any, resolve the
site it references (by role label match, or default to `escape_tile`)
and assert `sign(dx)`/`sign(dy)` agree. A scenario may be *hard*; it
may not *lie*.

---

## 6. Build-priority ranking (unit: new-question-per-machinery)

Carried forward from `SCENARIO_SEEDS.md` §Build priority, re-stated as
the expansion sequence:

| # | capability | unlocks | size | when |
|---|---|---|---|---|
| 1 | deadline machinery | `tidal_causeway`, `storm_road`, ½ of every combo | S | tonight (Phase 3) |
| 2 | `requirement_items` (checklist) | whole ground/water transportation column (text only) | S | tonight (Phase 2) |
| 3 | directional-truth assertion | trust guard for levels 2+ | XS | tonight (Phase 4) |
| 4 | Rules B + C (signature dedup) | safe component swaps | S | tonight Phase 5 / next |
| 5 | corroboration fact-gate | `two_maps_agree` +3 seeds; makes E→D→H earn its keep | S | next night |
| 6 | region mutation (tile-set flip) | environmental column, the `★ WATER RECEDING` beat | M | next |
| 7 | `escape_kind = vehicle` | `utility_truck`, `rescue_boat` read right | S | with #6 |
| 8 | N ordered sites | sequential family | M | later |
| 9 | component tables (level 2) | 20 shapes per grammar | M | the big one, after #5–7 |
| 10 | composition (level 5) | the combos — "the flooded railway" | L | the prize |

---

## 7. What "done" looks like for the expansion (not tonight)

The engine holds ~a dozen validated components. `build_mystery()`
picks: a family (Rule A/B/C), a reasoning shape, a situation, a route
feature, a dependency object, site labels — all from authored pools —
then lays them onto the map (levels 3–4) and validates all five
categories (§4). A player runs ten expeditions and meets ten
recognisably different problems, and the diff that added the tenth was
a table row, not a new mixin.
