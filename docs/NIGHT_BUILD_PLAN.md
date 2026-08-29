# Night build plan — 2026-08-29 (rev 3, final)

Artifact mirror: https://claude.ai/code/artifact/04705944-5bda-4f0b-aeb3-7db7840d58c4

## The goal

**Make Apocrysis produce many different-feeling escape stories from a
small set of mechanisms.** Not "add two more puzzle types." Six good
grammars with twenty story-shapes each feels much larger than twenty
isolated mechanics.

After tonight the engine has: spatial · infrastructural · experimental ·
informational (all shipped) + transportation + time-pressure. The next
gains come from *combining* those, guided by the seed library.

### The ten questions a player should meet

| # | question | family | status |
|---|---|---|---|
| 1 | Where is the actual way out? | spatial | shipped |
| 2 | What dependency makes this work? | infrastructural | shipped |
| 3 | What if my interpretation is wrong? | experimental | shipped |
| 4 | What can I learn that I couldn't see? | informational | shipped |
| 5 | Can I trust this route — does independent evidence agree? | corroborative | seeded |
| 6 | How do I assemble the route from several pieces? | sequential | seeded |
| 7 | Which direction does the evidence actually point? | directional | audited tonight |
| 8 | What can I change in the world to open a way out? | environmental | seeded |
| 9 | What can I restore and ride away in? | transportation | **tonight** |
| 10 | What must I finish before the environment changes? | time-pressure | **tonight** |

## Phases (in order)

### 1 — Scenario library (first-class)

- `docs/SCENARIO_SEEDS.md` — bring the ~45-seed first draft to the full
  **16-field schema** per seed: id · premise · situation · route ·
  discovery · reasoning · dependency · resolution · confirmation ·
  pressure · exit-type · machinery-need · **story signature** ·
  duplicate-of · kid rating (kid-ok / kid-hard + why).
- `docs/SCENARIO_EXPANSION.md` — capture the direction: the 5 levels of
  randomness (scenario / component / site-layout / evidence-layout /
  composition), variety rules A/B/C, the expanded validation
  (structural / evidence / geographic / story / variety validity), and
  the "authored randomness not procedural soup" principle.
- Not an implementation backlog — a design inventory. Per seed: *can
  the current engine support this, and if not, what's the smallest
  missing capability?* A seed needing "new machinery X" is a candidate
  for a future night, not a reason to build X now.
- Build-priority ranking: machinery that unlocks **several** genuinely
  different scenarios wins (corroboration gate → 4 seeds; region
  mutation → 4; vehicle-exit → 5) over one-offs.
- Combinations section for multi-grammar stories ("the flooded
  railway", "the burning dam") — the long-term prize.

### 2 — Transportation (`airfield_plane`)

Spec: `docs/MECHANISM_TRANSPORTATION.md`. Player question: *"the way
out is a machine — what does it need before it'll run?"*

Distinct grammar: **two parallel requirement items** (a checklist),
versus infra's *serial* dependency chain.

New machinery:
- `Mystery.requirement_items: list` beside the single
  `requirement_item` (untouched for the other 8 mechanisms).
- A `require2` site with its own item + evidence (both routes support
  `F_REQUIRE`).
- `_mystery_has_all_items` / `_mystery_missing_items`; obstacle opens
  when the checklist is complete.
- Transportation branch in `_objective_steps` (list each item with its
  own ✓/▸ + compass heading) and in `mystery_bump_obstacle` ("you're
  missing the propeller" / "the engine catches").
- Both fields round-trip `to_dict` / `from_dict`.
- **No `escape_kind` in v1** — the plane sits adjacent to the carved
  gap; you cover the last tile. `escape_kind=vehicle` is deferred.

Fallback (only if `requirement_items` destabilises save/load):
single-item + the vehicle fiction. Never a half-broken list.

Done when: forced 100-game bot solve (combat-only deaths), end-to-end
sim passes, committed.

### 3 — Time-pressure (`tidal_causeway`)

Spec: write `docs/MECHANISM_TIME_PRESSURE.md`. Player question: *"what
must I finish before the clock runs out — and what can I skip?"*

Distinct reasoning: **triage**.

New machinery:
- `Mystery.deadline` — turns remaining, set when `F_ROUTE` lands
  (diegetic — starts when the player *knows*). `None` for every other
  family. Round-trips save/load.
- Per-turn tick in `world_mixin.move_and_search`, right after
  `_apply_decay()`. Decrement; escalating tide banners at 10 / 5 / 2
  turns left.
- Visible timer: an objective-panel line ("the tide turns in ~6
  turns") + a HUD warning. Tide-language, never "deadline: 0".
- **Soft failure**: at 0 the causeway floods and the route shuts, then
  re-opens at the next low tide (~24 turns later). Lose time and
  daylight, not the run.

Done when: a forced bot run *and* a hand sim both show it's winnable
with focused play and lost with dawdling; banners read right;
committed. Expect forced `tidal_causeway` bot survival below 85% —
that's the family working, **report it, don't tune it**. Held line:
the aggregate unforced number stays in noise (1-in-9 of expeditions).

### 4 — Directional-truth audit

Build-time assertion: any compass word in generated evidence
("north-west ridge", "stronger to the east") must agree with the
vector to the site it names. Fix any mechanism that contradicts its
own geometry. A scenario may be hard; it may not lie.

### 5 — Variety rules B + C  *(only if genuine runway)*

- **Rule B** — a short recent-*scenario* history so
  `power_station → dam_valves → power_station` can't happen just
  because the families differ.
- **Rule C** — a **story signature** computed from the matrix
  classification (`spatial · single-item · gate`), so `key→gate`,
  `fuel→gate`, `battery→gate` register as the same shape and the
  generator steers away from repeating it.
- Persist both alongside `_used_mechanisms` / `_last_family` in the
  profile (same pattern as `73ff535`).

## Guardrails

- **Balance FROZEN** — no combat / hunger-thirst / encounter-rate /
  loot-rate / map-growth changes, and no hard movement cap at 0/0.
  Attrition stays the consequence; watch real player reach first.
- **Invariant 3d** — critical paths lead toward the exit; no unrelated
  post-solution trek.
- **Directional truth** — enforced (phase 4).
- **No vocab leak** — the player never sees `family` / `escape_kind` /
  `reasoning: triage`. Prose only.
- **Authored randomness** — every pool component is human-designed and
  validated; the generator chooses among good possibilities, never
  invents nonsense.
- **Green before commit** — both suites + `validate()` across ≥8 seeds
  + save/load round-trip. Commit + push per phase.
- **Bot sanity per family** — 300-game unforced within ~3pt of ~85.8%,
  ~100% combat deaths; forced 100-game confirms the bot can solve it.

## Forks (resolved)

1. Transportation: **two-item assembly**.
2. Time-pressure: **soft failure**.
3. `boat_crossing`: **leave it untouched**.

## Not tonight

Fetch reskins (cut) · the generalised component generator · the
corroboration-gate / region-mutation / vehicle-exit machinery (seeded,
not built) · campaign-reward design · assist mode.

## Success by morning

- **Code:** transportation + time-pressure work; the 8 existing
  mechanisms still work; both suites green; save/load correct;
  directional clues trustworthy.
- **Content:** 30–50 seeds fully classified; duplicates identified by
  signature; future machinery documented; combos catalogued;
  `SCENARIO_EXPANSION.md` written.
- **Experience:** a player runs several expeditions and reasonably
  meets different places, clues, reasoning, dependencies, resolutions,
  pressures, and ways of leaving — without mechanical chaos.

Not success: "we added two mechanisms." Success: the game got
materially bigger and the engine didn't get more brittle.
