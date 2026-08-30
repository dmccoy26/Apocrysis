# Audit status — what isn't written yet (World 1, version-5)

*Reconciled 2026-08-30, `HEAD a26678b`. 347 tests green, `--mapgen v1`
byte-identical. The full 25-expedition World-1 arc is playable start to
finish.*

The earlier "what isn't written yet" audit was taken **before** the
design-pass implementation (escape model / two-axis forecast / L0–L3
attention) and before the B→F investigation loop (objective lifecycle,
attention lifecycle, investigation strip, landmark spotting, fatigue
decision, navigation). Roughly half of what it listed as "0 code" is
now shipped. This doc is the corrected picture.

Read it as three separate things, not one backlog:

1. **Genuinely unfinished implementation** — the core experience is not
   yet complete without these.
2. **Deliberately deferred decisions** — measured, parked on purpose,
   not evidence the core is incomplete.
3. **The Phase C/D world-generation layer** — a separate layer, kept
   behind the human playtest on purpose.

---

## Current state, one paragraph

The core World-1 game is implemented. The remaining immediate work is
finishing the investigation / spatial presentation, removing legacy
dead systems, and validating the complete experience with a human
playthrough. The larger world-generation and balance roadmap comes
afterward — and should not be allowed to obscure whether World 1 as it
stands today is fun and understandable.

---

## Next gate

The next implementation gate is **not** balance or world generation. It
is **human comprehension and agency**.

The player must be able to:

1. understand the current investigation,
2. identify what evidence remains,
3. understand what action can advance it,
4. understand spatial threats and opportunities,
5. make meaningful combat / escape / resource decisions,
6. complete the World-1 arc **without** requiring knowledge of the
   underlying map markers or bot-specific behaviour.

Once that gate is exercised by a human playthrough, **reopen only the
problems that playthrough demonstrates.** That is the stopping rule.

Items 1a–1c below exist to make the gate passable; 1d is the gate
itself. Everything in sections 2–4 stays closed until a human run
produces evidence against it.

---

## 1 — Genuinely unfinished implementation

### 1a. Finish the investigation UI

`tui._investigation_strip()` (B3) now shows the milestone count,
per-thread progress bars, a `▸` on the thread this expedition advances,
the thread question ("this run: …"), and the working theory ("you
think: …"). The *mystery* has an OBJECTIVES checklist under it.

Still missing, for the **world-investigation thread** itself:

- a **per-lead checklist** — which specific leads on the active thread
  are known, which are still out there
- a **current / hot next step** — the single most useful thing to look
  for now
- a clear read of **what this expedition can advance** vs what it
  can't

Target shape (presentation is not the point — the four questions are):

```text
INVESTIGATION
▸ Who ordered it, and why?

LEADS
✓ damaged relay
✓ evacuation record
○ witness at the mill
○ radio transmission

NEXT
→ Search the mill

THIS RUN
Can advance: witness at the mill
```

The player must be able to answer: **what do I know? what am I
missing? what should I do next? can this expedition make progress?**
This is the last unclosed piece of the run-6 discovery problem
(`DEV_PLAYTEST.md`, `NAV_INVESTIGATION_RESULTS.md`).

### 1b. Finish spatial language

Shipped: `world_mixin._spot_leads()` names a mystery site the first
time its `!` marker enters visibility; F marks the entry point from
turn 1 with an opening beat + bearing; the ESCAPE-panel hot step
climbs an approach ladder.

Still missing:

- **named physical landmarks at mystery sites** — the world places no
  "you can see the water tower — the pass cuts through it" feature.
  `_spot_landmarks` stays generic; approach-ladder rung 2 (line of
  sight to a *named world feature*, not a marker) is unbuilt.
- the world should communicate **what the player sees**, not merely
  expose a map marker.

Instead of `! MYSTERY SITE`, the player should encounter something
like:

> A rusted water tower rises beyond the trees. Something about it
> matches the description in your notes.

The marker can still exist — but the **world description becomes the
primary information, with the marker as support.**

`DESIGN_SPATIAL_LANGUAGE.md`.

### 1c. Clean up the legacy zombie systems

Unchanged since the audit — no commits touched either.

- **Dynamic Tasks** (`objectives_mixin._generate_dynamic_tasks`, fires
  ~10 %/turn) render in the HUD and accumulate forever. `complete_task()`
  has a full reward switch (xp / health / fatigue / food / water /
  medicine) that is **only reachable via the interactive `ct [idx]`
  command** — nothing auto-completes a task, so the reward path is dead
  in normal play.
- **Goals** — `commands.md` says the goal/task checklist was "removed
  in v4". It wasn't: 6 fixed goals are still seeded every expedition
  and auto-checked "for save-file compatibility", under a UI that no
  longer surfaces them.

Make this an **architectural decision, not another investigation.**
The question: **are Tasks and Goals part of version-5's actual player
model?** If no, remove them. If yes, finish them properly (Tasks need
auto-completion so the reward path fires). What version-5 must not
ship is three overlapping objective systems —

```text
Goals
Tasks
Investigation objectives
```

— when the game has clearly converged on the investigation objective
as the meaningful player-facing system. This is the oldest untouched
debt in the repo.

### 1d. Human playtest of the full arc

Not implementation, but the missing **validation milestone**. The bots
navigate symbols, not language, so they have reached their useful
ceiling: `story_playthrough.py` completes the arc (23/23 world facts,
9/9 milestones, both endings) but only by retrying — 76 % expedition
death rate, expedition 24 needs ~30 bot attempts. A human run is the
only evidence for whether the whole experience actually works.

**Then stop coding.** Play the straight-through 25-expedition campaign
— not a bot, not a regression test, not a balance sim. Record what
surprises, confuses, or frustrates:

- "I don't know where I'm supposed to go."
- "I know where I'm supposed to go but not how."
- "I didn't realise that was important."
- "I don't understand why this encounter is dangerous."
- "I have no idea what I should do this turn."
- "I keep doing this because the game isn't telling me anything better."
- "This is tedious." / "This is great."

Those observations are worth more right now than reopening any parked
model.

---

## 2 — Deliberately deferred (parked, not lost)

Do **not** fold these into a "finish everything" sprint. Each is
measured and parked on purpose.

| item | source | why parked |
|---|---|---|
| Difficulty-ramp retuning (zombie bands, elite gating, `DIFFICULTY_RAMP_LENGTH`) | `COMBAT_EXP3_RESULTS.md` | curve frozen; decouple from arc length done, retune waits for the human playtest |
| Failed-escape sub-decision (forced full fight vs "one free hit / lose ground") | `DDR_ARMORED_ZOMBIE.md` | not decided; still a forced full fight |
| Dangerous-enemy reward bonus ("a hard fight should pay") | `COMBAT_INFO_SPEC.md` | 0 code, explicitly deferred |
| Late-game loot accumulation (4 guns by exp 4; inheritance compounds past ~exp 10) | `RESOURCE_MODEL_RESULTS.md` | untuned; needs the human playtest to confirm it's actually a problem |
| Two-axis forecast on the bot path | — | `balance_autoplay` still sees old single-arg `threat_tier`; byte-identity constraint |
| Armor accumulation still slow late; "guaranteed early vest" / `ARMOR_TABLE` change | `ARMOR_INVESTIGATION_RESULTS.md` | acquisition fix shipped; further tuning measured, not applied |

**Answered, not open:** early food density. The resource investigation
showed food was a *navigation artifact* — with a bot that navigates
well, starvation went 47 % → 7 % of turns. Do **not** tune food because
the old audit said it was thin. That is the evidence-driven result the
project is built on.

---

## 3 — Phase C/D world-generation layer (keep behind the human playtest)

A separate layer. Do not let it obscure whether World 1 as implemented
is fun and understandable.

| item | state |
|---|---|
| `DIS_FEW_REMAINS` → only `mountain_pass` | known bug — expedition 1 is mechanically identical every campaign (first WorldFact binds to one mechanism) |
| Dedicated finale map archetype | E.2 reuses the normal generator + a fixed target + relabels; no bespoke command-centre geography |
| NPC arrival / consolidation-point scene | 0 code |
| Phase D — world conditions / region mutation / weather | 0 % |
| `escape_kind` behaviour | field with two values, no gameplay behind the non-default |
| B.3 optional-evidence valley file | skipped |
| `landscape` mapgen default flip | built behind `--mapgen landscape`; needs a feel-test at depth 4 + 10 before it's default |
| Nav pieces 1 / 4 (C.3.2) | parked |

---

## 4 — Tooling / instrument gaps (validation, not core)

| gap | state |
|---|---|
| `objective` policy building-sweep strategy | still the ceiling — `unique-tile ratio ~0.03`, oscillates between searched structures; can't measure objective completion |
| Text-navigating bot / cardinal-vs-landmark A/B | inconclusive — the marker-navigating policy is phrasing-blind; needs a language-aware bot or a human |
| `humanlike` policy (drops the objective after N distracted turns) | named in `AUTOPLAY_STRATEGY.md`, never built |
| Human-session telemetry sink | `tools/telemetry.py` runs on bot campaigns only; a `--log` session produces no event trace |
| `combat_cost.py` / `forecast_calibration.py` `_fight_detailed` duplication | could now import `combat_forecast._simulate` |

**Shipped since the audit:** `tools/telemetry.py` (black-box event
stream), `tools/{resource,nav,fatigue}_autoplay.py`,
`tools/autoplay/policies.py` objective policies,
`tools/story_playthrough.py` (+ `--runs` batch stats). All 16 CLI
tools now respond to `--help`.

---

## What the design pass + B→F loop actually closed

For the record — these were "0 code" in the old audit and are now
shipped:

- **Objective lifecycle** (B1) — `mystery_mixin.objective_tick()`,
  states none→active→distracted→reminder→urgent→complete, thresholds
  12 / 20 / 34 + resource-pressure, plain-text next-step nudges,
  `_objective_complete()`. Wired at end-of-turn. The run-6 "objective
  loses behavioural priority" fix.
- **Attention lifecycle** (B2 + D) — `_supply_warnings` / `_hp_warnings`
  / `_fatigue_warnings` in `game.py`: one-shot-per-tier escalation,
  re-arm at a clearance threshold, `✓` completion line on recovery.
- **Attention grading for non-combat channels** (B2) — `_KIND_ALIAS`
  is now `(class, prefix, default_level)`; every semantic channel has a
  default level. `_LEVEL_BY_CLASS` deleted.
- **Escape model** — `src/escape_model.py`, one `escape_chance()` the
  flee roll and `combat_forecast.escape_pct` both call. No more flat
  50 %. Zombie speed classes.
- **Two-axis forecast** — `threat_tier` / `weapon_verdict` take a cost
  fraction; L0–L3 encounter grading by forecast + HP.
- **Interaction inference** — `_auto_equip_best` on expedition start;
  no encounter fires on a won move; reaching the solved escape tile
  ends the expedition with no keystroke.
- **Fatigue** (C + D) — `rest` recovery `max(5, wisdom//2)` (net-zero
  vs a move) → `max(12, wisdom)`; `_fatigue_warnings` surfaces rest as
  an affordance; building-entry recovery kept. `objective_rest`
  exhausted 20 % → 4 %.
- **Navigation** (B4 + F) — `_spot_leads()` names a mystery site on
  first sight; the `closed` entry point is marked from turn 1 with an
  opening beat. `objective` bot deaths 31 → 18, wins 11 → 21.

---

## Bottom line

**Immediate:** finish the investigation UI (1a) and spatial language
(1b), resolve the legacy Tasks/Goals systems (1c), then run a human
playtest of the full arc (1d).

**After the human playtest:** the Phase C/D world-generation layer
(section 3) and the parked balance decisions (section 2) — reopened
only where the playtest produces evidence against them.

Apocrysis is not primarily suffering from missing mechanics. It is
approaching the more interesting question: **does the player actually
understand the machinery that's been built?** The Next gate above is
how we find out.
