# Phase B — the roguelite inheritance loop (spec)

**Reviewed and locked 2026-08-29.** Builds on the frozen Phase A spine
(`PHASE_A_COMPLETE.md`). Does not modify it.

## The one sentence

> **Survivor Knowledge describes persistent *understanding*, not
> persistent *capability*.** A new survivor does not inherit the
> previous survivor's physical competence, equipment, resources,
> statistics, or progression. They inherit what the campaign has
> learned and the ability to recognise situations the campaign has
> already encountered.

## Load-bearing invariants (write into every relevant test)

1. **Death may replace the survivor record, but must never reconstruct
   or mutate the campaign record.**
2. `expeditions_completed` **is campaign depth, not survivor progress.**
   A survivor dies at depth 8 → the campaign is still at depth 8 → the
   next survivor begins at depth 8, at level 1.
3. **`SurvivorLore.effect` is documentation / UI text only.** It is
   never parsed or interpreted by the engine. **The learned *id* is the
   only executable interface** — engine systems do `if
   survivor_knowledge.has("BLUE_SIGNS"):`, nothing more. No `effect`
   vocabulary, no mini rules engine.
4. **Nothing in Survivor Knowledge may modify** survivor stats,
   equipment, XP, health, damage, durability, loot quantity, or
   encounter probabilities. It only changes what information is
   *surfaced* and *when*.
5. Persistence *serialises* state. The **game lifecycle** decides when a
   survivor is replaced — `save_profile()` never contains
   death-detection logic.

## The player question Phase B answers

> If my survivor dies, what does the next survivor actually inherit
> besides a percentage bar?

Answer: **the campaign's understanding of the world**, plus **3–5 small,
legible pieces of survivor lore** — each of which makes one thing about
an expedition *easier to read*, never stronger.

## The split Phase B makes explicit

```
CAMPAIGN  (persists across deaths - "what has been figured out")
 ├── World Investigation        (already Phase A - profile-persisted)
 ├── Survivor Knowledge         (NEW - B.2)
 ├── depth reached              (expeditions_completed, as "how far in")
 └── variety rings              (_used_mechanisms / _recent_* - already persisted)

SURVIVOR  (resets on death - "who is carrying it now")
 ├── name / identity
 ├── level / xp / stats
 ├── gear / backpack
 └── health / hunger / thirst / fatigue / current map
```

Phase A already put World Investigation on the campaign side. Phase B
formalises the boundary and moves Survivor Knowledge onto it.

## B.1 — the death → new-survivor transition

### Today

`cli.py`'s loop: on a non-hardcore death, `save_profile` keeps
*everything* (level, gear, investigation) and the next `Apocrysis` gets
it all back — death is a soft "knocked out". On a hardcore death,
`delete_profile()` wipes *everything*, investigation included.

Neither is the roguelite loop the roadmap wants.

### Phase B — the lifecycle

The **game lifecycle** (`cli.py` / `tui.py`'s loop), not `save_profile`,
owns the replacement:

```
current survivor dies
        ↓
capture campaign state   (read the campaign record off the dying game)
        ↓
discard survivor state
        ↓
construct new survivor   (level 1, starter gear, new identity)
        ↓
combine campaign + new survivor
        ↓
persist                  (save_profile just serialises the combined state)
        ↓
start next expedition    (at campaign depth, targeting next_target())
```

Framing (the A.5 retrospective already leads with `EXPEDITION ENDED —
<name> did not make it back.`) → then `A NEW SURVIVOR TAKES UP THE
SEARCH.`

### Persistence — one file, two logical records

```json
{
  "campaign": { "world_investigation": {...}, "survivor_knowledge": [...],
                "expeditions_completed": 8, "used_mechanisms": [...],
                "last_family": ..., "recent_mechanisms": [...],
                "recent_signatures": [...], "hardcore": false },
  "survivor": { "name": "...", "player_class": "...", "level": 3,
                "xp": ..., "max_xp": ..., "strength": ..., ...,
                "weapons": [...], "equipped_weapon": ...,
                "armor": [...], "equipped_armor": {...},
                "backpack_food": ..., ..., "has_flashlight": ... }
}
```

- `save_profile` writes both records from current state. `apply_profile`
  restores both.
- **`save_profile` has no death logic.** The lifecycle constructs a
  fresh survivor before the save; `save_profile` just serialises
  whatever survivor is on the game object.
- Back-compat: a flat legacy profile (Phase A shape — all keys at top
  level) is loaded into the campaign/survivor records by field name.
  One migration branch in `load_profile`, mirroring the existing
  legacy-single-slot handling.
- **`campaign` is written verbatim from what was read** — no field of
  it is recomputed on a death (invariant 1).

### Modes

- Keep **hardcore** meaning what it means (permanent — `delete_profile`
  on death, campaign included). Hardcore is "one survivor, one shot".
- The default (non-hardcore) becomes the **campaign / roguelite** loop
  above: survivors are mortal, the campaign isn't.
- (No third mode. The old "soft knocked-out" behaviour goes away — it
  was never intentional design, just what fell out.)

## B.2 — Survivor Knowledge (3–5 entries)

### Shape

```python
@dataclass(frozen=True)
class SurvivorLore:
    id: str
    learned_when: str      # doc-only: human-readable trigger description
    blurb: str             # player-facing: what you now know (one line)
    effect: str            # DOC/UI TEXT ONLY - never parsed by the engine
```

`id`, `learned_when`, `blurb`, `effect` are all **data**. The engine
reads exactly one thing: `survivor_knowledge.has(<id>)`. `effect` is a
string shown to the player and written in this doc; it has no runtime
meaning. (Invariant 3.)

A small authored list in `worlds/silence/lore.py` (like `truth.py` /
`discovery.py`). The **campaign** tracks which ids are learned (a set,
profile-persisted). `SurvivorKnowledge` (engine, sibling of
`WorldInvestigation`) holds the learned set and answers `has()`.

### The 3 shipped for "The Cordon"

Every entry is **legibility, not power** (invariant 4). Two more
(`INFECTED_AND_NOISE`, `CORRIDOR_CHECKPOINTS`) were considered and
**held** — they cross from "I figured something out about this world"
into altering the simulation's rules or a mystery's state machine; a
later balance pass can revisit them.

| id | learned when | blurb (what you know) | effect (surfaced info) |
|---|---|---|---|
| `BLUE_SIGNS` | solve an `evac_corridor` mystery | Protocol Seven marked its routes with blue signs | the signed-route / corridor site is shown on the map from the start of an expedition — you still have to reach it |
| `COMMAND_FREQUENCY` | solve a `radio_tower` mystery | regional command held one emergency frequency | in a `radio_tower` mystery the transmitter briefing names the frequency up front, instead of it being a `search` step |
| `RESERVOIR_CONTROLS` | solve a `dam_valves` mystery | the valley reservoir is governed from the control room, not the sluice | in a `dam_valves` mystery the control-room evidence **identifies which control governs the reservoir** — you still operate it yourself, revise as normal; you're just not told which one blind |

**`RESERVOIR_CONTROLS` is informational** (per review): it surfaces
*which control* earlier, it does **not** reduce the number of actions or
evidence items required, and it must not touch `dam_valves`'s revise
loop. Test asserts the same control count / obstacle-open condition.

**`COMMAND_FREQUENCY`** does remove one `search` evidence item from the
`radio_tower` chain — an explicit, mystery-specific shortcut. Test
asserts it changes *only* the radio-tower evidence set and nothing
about combat / resources / completion probability.

Hard cap at 5; every entry power-checked against `balance_autoplay.py`
before it ships.

### Earning

A `SurvivorLore` id is marked learned when its trigger fires (in
`mystery_try_escape` / the encounter path — 1–2 lines each, guarded,
next to the existing A.3 hook). It persists on the campaign side, so a
new survivor has it.

### Surfacing

- when first learned: `announce_event(<blurb>, <effect>, kind="lore")`
  — a 4th `announce_event` kind, below `milestone`, above `discovery`
- the `wi` screen gains a short `WHAT SURVIVORS HAVE LEARNED` footer
  (blurbs only)
- the A.5 retrospective's `WHAT YOU LEARNED` includes a newly-earned
  lore line

## Out of scope for Phase B

- optional evidence / per-region "valley file" (roadmap B.3) — a
  separate later pass; it's world-history flavour, not the inheritance
  loop
- the Survivor Network as a *mechanic* (a roster of past survivors you
  can draw on) — the framing line is enough for B; the mechanic is
  post-E
- any `knowledge.py` change, any `WorldFact` change, `MechanismFamily`,
  map-v2, A.0.1
- CH3+ world facts (Phase E)

## Tests

- **death → new survivor**: level → 1, xp → 0, gear → starter, health →
  max, name changes; **investigation + survivor knowledge + depth +
  variety rings persist unchanged**
- **campaign record is byte-identical across a death** (invariant 1) —
  serialise campaign before + after, `assertEqual`
- **depth ≠ survivor** (invariant 2) — die at depth N, new survivor's
  first expedition is depth N and level 1
- a legacy (Phase A flat) profile migrates to the campaign/survivor
  split and round-trips
- earning a `SurvivorLore` id: trigger fires it once, persists through
  a death, `announce_event(kind="lore")` fires once
- one behavioural test per shipped entry (blue-sign site visible from
  turn 1; `COMMAND_FREQUENCY` drops exactly one radio-tower `search`
  item; `RESERVOIR_CONTROLS` surfaces the correct control and leaves
  the control count + open condition unchanged)
- **the negative / "legibility not power" test** (invariant 4): for
  each shipped id, build two otherwise-identical games (same seed, same
  mechanism) — one with the id learned, one without — and assert
  **equal**: starting stats, starting gear, `max_health`, per-hit
  damage for the starter weapon, loot-table identity, and
  `_select_zombie_for_encounter`'s output over a fixed RNG. Only the
  mystery's evidence/site presentation may differ.
- hardcore death still `delete_profile()`s everything (unchanged)

## Build order

1. B.1a — the campaign/survivor profile split + legacy migration
2. B.1b — the death → new-survivor transition + framing
3. B.2a — `SurvivorLore` list + `SurvivorKnowledge` + campaign persistence
4. B.2b — the 3 shipped entries' triggers + effects, one at a time,
   each behind its own test + balance check
5. B.2c — surfacing (`kind="lore"`, `wi` footer, retrospective line)

Both suites green after each step. Atlas gets the leaf files
(`SurvivorLore` list, `SurvivorKnowledge` class) first, per protocol;
the rest is large-file wiring — hand-written, logged.

## Exit condition

> A survivor dies. The next one starts weak, with a new name — but
> knows what the last one figured out about the world, carries a
> couple of concrete survival lessons that make specific expeditions
> read more clearly, and is dropped at the depth the campaign reached.
> Dying costs the run, not the campaign.

---

## As built (2026-08-29) — see `PHASE_B_COMPLETE.md`

Shipped as specced. **240 tests + 100 subtests green.** Build order
followed (B.1a profile split → B.1b lifecycle → B.2a lore data +
interpreter → B.2b the 3 entries one at a time, each with its own test
+ balance check → B.2c surfacing → exit-condition test).

Notable as-built points (full list in `PHASE_B_COMPLETE.md`):
- profile file is now `{campaign, survivor}`; `load_profile` migrates
  legacy flat profiles; `apply_profile` flattens internally.
- the profile file keys on the *campaign* (founder's name); the
  survivor display name changes independently.
- `COMMAND_FREQUENCY` removes exactly one `radio_tower` `search` step
  (`E_route_a` → `observe`); `RESERVOIR_CONTROLS` is purely
  informational (rewrites `E_require_b.text`, touches nothing else).
- `INFECTED_AND_NOISE` / `CORRIDOR_CHECKPOINTS` remain un-shipped.
- Atlas shipped 1 of ~12 files (`survivor_knowledge.py`).
