# Stage 0 slice — mechanical playtest (todo 9f831f9d)

2026-08-28. This is the **mechanical half** of the Stage 0 go/no-go
gate: what the built slice structurally does, run through the
three-situation test with the headless harness
(`tools/slice_playtest.py`). The **subjective half** — is it fun, does
it read as investigation or as quest-following — needs a human at the
keyboard (`python3 apocrysis.py --slice`) and is not answered here.

## What was built

- `src/slice_dam_road.py` — the authored 19×19 map and the Escape
  Proof: 4 facts, 7 evidence pieces, 2 deductions, 1 hypothesis.
- `src/mixins/slice_mixin.py` — knowledge model + `journal` /
  `remember` / `inspect` + valve-key item + locked-gate chokepoint +
  the gated escape action.
- Redundancy (design requirement): every fact has ≥2 independent
  discovery routes. F1 ← E1 *or* E1b. F2 ← E2 *or* E3 *or* E6. F3 ←
  E2 *or* E3. F4 ← E2 *or* E4 *or* E5 (E5 is also the physical key).
  The full-solve run finds all 7; a player can miss up to 3 and still
  reach a confirmed hypothesis.

## The governing test — can the player tell "unsolved" from "unimportant"?

Run each situation; the interface never labels which category the
player is in. The distinction has to be *inferable from what
`journal` / `remember` return*, not stated.

### Situation 1 — a required piece of evidence not yet found

Player reaches the gate knowing it's locked and that a key exists,
but never searched the control room, so has no key.

- `inspect key` → *"A key that opens the gate exists, kept in the dam
  control room. — Known."* (knows it exists and where; doesn't have it)
- `open gate` → *"The gate is chained and padlocked. You need the
  key — the log said it was moved to the control room."*
- Recovery: the *fiction itself* points at the control room. No quest
  marker, no "you haven't found evidence X". **Recoverable.**

### Situation 2 — the irrelevant thread, partially chased

Player goes to the farmhouse, reads the diary (Sarah, the checkpoint,
"the men there aren't ours" — deliberately compelling), then leaves.

- `journal` → *"Your journal is empty. You have not noted anything
  yet."*
- `remember` → *"So far you have a flooded road and a lot of
  questions. Nothing adds up yet."*
- The game does **not** flag the diary as a dead end — and gives the
  player nothing false to act on. They walked away with no penalty.
  **Recoverable; the fantasy "I can be curious without being
  punished" holds.**

### Situation 3 — hypothesis formable but unrecognised

Player has all 4 facts; hypothesis state is `suspected`; they haven't
acted.

- `remember` → *"You are starting to think: The south service road,
  past the locked gate, is the way out."*
- `inspect way out` → *"Suspected. You suspect: …"*
- `journal` → full evidence list + the 4 established facts.
- The interface signals *closeness* ("starting to think") without
  saying "go open the gate." The player still has to connect "a key
  exists in the control room" to "go get it." **Recoverable.**

### The distinction, side by side

|  | `journal` | `remember` |
|---|---|---|
| **Unimportant** (S2) | empty | "nothing adds up yet" |
| **Unsolved** (S3) | full: 5 evidence, 4 facts | "starting to think *X*" |

The difference is visible in the tool output; neither response names
the category. **Mechanically, the governing test passes.**

## Other mechanical checks

- **Full solve** works end to end: F1 → deductions surface via
  `remember` → hypothesis `unknown` → `suspected` → `confirmed` (only
  by physically reaching E6 past the opened gate, never a status
  message) → `escape` succeeds. Win text is slice-appropriate.
- **Escape gating**: `escape` requires position == service road
  beyond **and** gate open **and** hypothesis == confirmed. Standing
  on the tile is not enough; an unconfirmed player gets *"you're not
  sure this road goes anywhere — better to look first."*
- **Backtrack beat**: seeing the locked gate before having the key
  sets a flag; opening it later prints *"You came back. The chain
  that stopped you last time drops in the gravel."*
- **Knowledge-persists-past-destruction**: opening the gate floods
  the utility shed; re-searching it → *"the papers are pulp … "
  whatever you already read here, you still know"* — and `journal`
  still shows the maintenance log entry.
- **Gate is a true chokepoint**: BFS confirms `(16,12)` is
  unreachable from spawn with the gate tile blocked, reachable with
  it open. No walking around.
- **Survival loosened** (todo 4f8fdc57): slice-only decay of 1
  hunger/thirst per turn, no procedural encounters or loot rolls in
  slice mode. Real-game tuning untouched.
- 115 existing tests still pass.

## Fixes after the first human playthrough (2026-08-28)

The first real play surfaced four problems; all fixed in the same
Stage 0 commit range:

1. **Could not open the gate with the key.** `open gate` only worked
   from exactly one tile `(13,12)`; from `(13,11)`/`(13,13)` — normal
   approach tiles — it said "there is no gate here to open" *even
   with the key in hand*. Fixed: `open gate` now works from any tile
   adjacent to the gate (Chebyshev ≤ 1, diagonals included), **and**
   walking straight into the gate while carrying the valve key opens
   it automatically with the narrative beat.
2. **Fatigue pegged at 100 the whole game.** It climbed +5/move with
   nothing to spend it on (no combat in the slice) and just read as
   "something is wrong." Fixed: movement fatigue is disabled in slice
   mode; the player starts at 0.
3. **Nothing to find — no food, water, weapons.** The slice had
   *eliminated* survival rather than *loosened* it. Fixed: the player
   now starts provisioned (25 food / 25 water / 5 medicine) and three
   locations yield a small supply cache on `search` (shed → water,
   control room → food, farmhouse → medicine), so searching has a
   material beat, not only an evidence beat.
4. **"Where are the zombies?"** Working as intended — combat and
   scavenging are deliberately off for this test — but nothing said
   so. Fixed: the `--slice` intro now states it up front, and adds
   `(type 'escape' to leave the valley)` once the player is standing
   past the open gate with a confirmed hypothesis.

## Known rough edges (deliberately NOT fixed — "observe first")

- Stepping onto the gate tile after opening it triggers the generic
  "You enter a building. It's a safe zone." heal.
- The classic-mode command panel doesn't list the slice verbs (the
  intro text does). The headless harness suppresses the whole panel.

## What the human playtest still has to answer

The behavioral-signal checklist from the todo — none of which the
harness can judge:

- Did you notice the flooded road / locked gate / "key moved" note
  *unprompted*, or did it feel like being funnelled?
- Did `remember` feel like recalling something you knew, or like
  receiving a hint?
- Did `journal` feel like a memory aid or a quest checklist?
- Did returning to the gate with the key feel earned?
- Did you understand *why* the escape worked, not just that it did?
- Did you ever feel like you were wandering with no idea what to do?
- The gut check: **did you want to keep investigating?**

A slice that is technically solvable but whose felt experience is
"okay, I guess the game wants me to find the key" is a **warning
sign, not a pass** — even though the harness shows a clean solve.
