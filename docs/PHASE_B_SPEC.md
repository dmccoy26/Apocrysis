# Phase B — the roguelite inheritance loop (spec, for review)

**Draft — review before implementation.** Builds on the frozen Phase A
spine (`PHASE_A_COMPLETE.md`). Does not modify it.

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

### Phase B

A death (in the campaign mode — see "modes" below):

1. **The survivor is gone.** Framing: `EXPEDITION ENDED — <name> did not
   make it back.` (the A.5 retrospective already leads with this) →
   then `A NEW SURVIVOR TAKES UP THE SEARCH.`
2. **The campaign stands.** World Investigation, Survivor Knowledge,
   depth, and variety rings all persist.
3. **The new survivor** starts at level 1 with starter gear, a new
   generated name (or a short pool / "the next survivor"), full health.
   `expeditions_completed` (depth) is **kept** — the new survivor is
   dropped at the chapter the campaign has reached, not back at map 1.
4. The next expedition targets `next_target()` exactly as before —
   nothing about the investigation changed.

### Persistence change

Split the single profile file into two logical records inside the same
file (no new file, no new abstraction):

```json
{
  "campaign": { "world_investigation": {...}, "survivor_knowledge": [...],
                "expeditions_completed": 7, "used_mechanisms": [...], ... },
  "survivor": { "name": "...", "level": 3, "xp": ..., "stats": {...},
                "weapons": [...], "armor": [...], ... }
}
```

- `save_profile` writes both. `apply_profile` restores both.
- **On death**: `save_profile` writes `campaign` as-is and writes a
  **fresh** `survivor` block (level 1, starter gear, new name).
- Back-compat: a flat legacy profile (Phase A shape) loads as
  `campaign` + `survivor` by field. One migration branch in
  `load_profile`, same pattern as the existing legacy-single-slot
  handling.

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
    learned_when: str      # human-readable trigger, for the docs only
    blurb: str             # player-facing, one line - what you now know
    effect: str            # player-facing, one line - what it changes
```

A small authored list in `worlds/silence/` (like `truth.py` /
`discovery.py`). The **campaign** tracks which ids are learned (a set,
profile-persisted). `SurvivorKnowledge` (engine, like
`WorldInvestigation`) interprets it.

### The 3–5 for "The Cordon"

Each must be **legibility, not power** (hard rule — roadmap §10):

| id | learned when | what you know | what it changes |
|---|---|---|---|
| `BLUE_SIGNS` | solve an `evac_corridor` mystery | Protocol Seven marked its routes with blue signs | evacuation-corridor / signed-route sites show on the map from the start of an expedition (you still have to reach them) |
| `INFECTED_AND_NOISE` | survive an encounter triggered near a running machine | the infected come toward sustained noise | a one-line warning when you start an action that makes noise near unexplored ground |
| `COMMAND_FREQUENCY` | solve a `radio_tower` mystery | regional command held one emergency frequency | a `radio_tower` mystery skips the "find the frequency" search step — the transmitter briefing names it |
| `RESERVOIR_CONTROLS` | solve a `dam_valves` mystery | the valley reservoir is set from the control room, never the sluice | a `dam_valves` mystery's control-room evidence rules out the obvious-wrong control up front |
| `CORRIDOR_CHECKPOINTS` | solve any mystery whose `closed` fact is a checkpoint | the corridors out were all checkpointed the same way | the "the usual way out is closed" beat is pre-known — F_CLOSED starts as observed, one less thing to establish |

Pick **3** to ship first (`BLUE_SIGNS`, `COMMAND_FREQUENCY`,
`RESERVOIR_CONTROLS` — all "skip a step you've done before"), hold 2 in
reserve. Hard cap at 5; every entry reviewed for power creep against
`balance_autoplay.py` before it ships.

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

- death → new survivor: level resets to 1, gear resets to starter,
  name changes, **investigation + survivor knowledge + depth persist**
- a legacy (Phase A flat) profile migrates to campaign/survivor split
- earning a `SurvivorLore` id: the trigger fires it once, it persists
  through a death, `announce_event(kind="lore")` fires once
- each lore effect does what it says (blue signs visible from turn 1;
  `COMMAND_FREQUENCY` removes the frequency-search step; etc.) — one
  test per shipped entry
- **power check**: a lore-loaded campaign's bot win-rate is within the
  frozen-balance band (extend `balance_autoplay.py` or a targeted test)
- hardcore death still wipes everything (unchanged)

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
