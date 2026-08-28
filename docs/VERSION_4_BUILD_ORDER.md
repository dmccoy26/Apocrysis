# Version 4 — Build Order

Organizing pass, 2026-08-28. This is the **program order** for the
escape-world redesign on the `version-4` branch. It does not add new
design — it sequences the 63 pending items in
`projects/apocrysis/version-4/.atlas/todo_list.json` into buildable
stages with their decision gates and dependencies made explicit.

Read alongside `ESCAPE_WORLD_DESIGN_ASSESSMENT.md` (the "what" and
"why"); this file is only the "in what order."

## Branch state (corrects the stale handoff note)

- `version-4` **exists**, locally and on `origin`
  (`github.com/dmccoy26/Apocrysis`). HEAD is `5c4912a` — one commit
  ahead of `version-3` (`9c835aa`), containing the design doc, commands
  reference, and README pointer.
- The working tree is at `projects/apocrysis/version-4/` (relative to
  the Atlas repo root). Sibling `version-1/`..`version-3/` directories
  are read-only single-branch clones of the older branches, for
  reference only — no work happens in them.
- All version-4 work commits to `version-4`. The earlier note saying
  "confirm/create it before pushing" is resolved — it's there.

## The two tracks

Version 4 has two mostly-independent bodies of work. Do not interleave
them arbitrarily — they have different risk profiles.

- **Track 1 — Escape-world redesign** (Stages 0–6 below). The premise
  shift. High risk, strictly ordered, gated by the slice playtest.
- **Track 2 — Current-engine cleanup** (Stage H below). Balance-harness
  realism bugs and the exploration/objective investigation pass. Mostly
  independent of Track 1, lower risk, and the harness fixes are a
  prerequisite for *trusting* any Track 1 balance data. Pull the harness
  bug fixes forward; the Q1–Q12 confirmations can happen whenever.

---

## Stage 0 — Vertical slice (BUILD THIS FIRST)

Supersedes all generator-first sequencing. Hard-coded, no procedural
generation. This is the go/no-go gate for whether the generator
(Stages 2–5) gets built at all.

| Order | ID | Item |
|---|---|---|
| 0.1 | `138c10f6` | Hard-coded 19×19 / 21×21 Dam Service Road map |
| 0.2 | `dd70ae0c` | Dam Service Road Escape Proof as real game state (4 facts / 6 evidence / 2 deductions / 1 hypothesis) |
| 0.3 | `d7a712dc` | Minimal `journal` / `remember` / `inspect`, slice-scoped only |
| 0.4 | `4f8fdc57` | Temporarily loosen survival pressure (slice-mode flag, explicitly throwaway) |
| 0.5 | `ceee7e54` | Knowledge-persists-past-object-destruction example + the gated escape action |
| 0.6 | `9f831f9d` | **Playtest against the three-situation test.** GO/NO-GO GATE. |

Do not start Stage 1 until 0.6 is done and evaluated. Read the 0.6
checklist before running it, not after.

---

## Stage 1 — Decision gates (answer before building the generator)

These are investigation/decision items with no code. They must be
resolved before the stages that depend on them. Several are "Open
Questions" the design doc deliberately left unresolved — resolve them
here, informed by what the slice playtest showed.

| ID | Decision | Blocks |
|---|---|---|
| `78921694` | Phase 0: what must the world generate so a player can *reason* to an escape? | Stage 2 (all of Phase A/B implementation) |
| `457c93a6` | Zone/district layer — semantic zone tag on top of terrain clustering | 1.x, Stage 2 loot/zombie ecology |
| `182bdc49` | The minimum information interface (what `look`/`inspect`/`journal`/`remember`/`map` must minimally provide) | `9c2db876`, `a6de97c0`, `1f2c7826` |
| `d3179782` | World-validation + information-budget invariants (`MAX_MEANINGFUL_LOCATIONS`, `MAX_EVIDENCE`, …) | `c1730862`, Stage 4 validation |
| — | Design forks from the doc still open: physical/knowledge persistence detail, zombie ecology open questions, people historical-vs-simulated, time-as-world-state, world-age/decay, escape-as-failable-arc. Resolve the ones a stage actually touches, when it touches them — not all up front. | as noted per stage |

---

## Stage 2 — Phase A + B: world geometry and player information architecture

Phase A and Phase B both ship without a premise change and are
testable standalone. Interleave them: Phase B needs *something* to
look at, Phase A produces it.

### 2A — World geometry (Phase A)

| Order | ID | Item | File |
|---|---|---|---|
| 2A.1 | `aa461cec` | Bound map size to a gameplay ceiling (~25–33, revisit `MAP_GROWTH_PER_LEVEL` too) | `src/constants.py` |
| 2A.2 | `6c9f672a` | Mountain-boundary Phase 1: force outer ring to `mountain` | `src/mixins/world_mixin.py` |
| 2A.3 | `98ab82c7` | Organic settlements: seed-and-grow footprint instead of fixed box | `src/mixins/world_mixin.py` |
| 2A.4 | `7ecd39cc` | Buildings as landmarks: one-time message when a building enters visibility | `src/mixins/world_mixin.py` |
| 2A.5 | `b31aac00` | Randomize player classification at spawn (reverses an earlier decision — see doc) | `src/mixins/actions_mixin.py` |

### 2B — Current-engine persistence findings (Phase A/C-adjacent, concrete bugs)

| Order | ID | Item |
|---|---|---|
| 2B.1 | `93edaf83` | Defeated zombies are never cleared from the map — fix |
| 2B.2 | `6c9a4ca6` | Dropped items are deleted, not placed in the world — fix |
| 2B.3 | `7db3c4b5` | Variable location abandonment states (generated *cause*, not a bool flag) |

### 2C — Player information architecture (Phase B), after `182bdc49`

| Order | ID | Item |
|---|---|---|
| 2C.1 | `f6d126f9` | Knowledge/discovery core data model — `clue` outcome + persisted fact collection + Observed/Known/Suspected/Confirmed |
| 2C.2 | `e3a1e201` | Persist the new discovery state in BOTH serialization paths (`save_profile`/`apply_profile` + JSON) |
| 2C.3 | `478c2cf9` | Discover-before-understand mechanic (significance deferred until later evidence) |
| 2C.4 | `9c2db876` | `look` and `inspect` commands |
| 2C.5 | `a6de97c0` | `journal` and `remember` commands (raw evidence vs. current interpretation, kept distinct) |
| 2C.6 | `1f2c7826` | Map as a knowledge surface — progressive annotation over `print_map()` |
| 2C.7 | `2977a8a1` | Loot progression bands — restructure `LOOT_WEAPON_TABLE`/`ARMOR_TABLE` `min_expedition` banding |

### 2D — Zone-dependent ecology (Phase B/C-adjacent), after `457c93a6`

| Order | ID | Item |
|---|---|---|
| 2D.1 | `1255e24e` | Zone-aware zombie ecology — `_select_zombie_for_encounter()` keyed to zone |
| 2D.2 | `a9c8c83e` | Contextual per-location-type loot tables — `find_loot()` keyed to building type |

---

## Stage 3 — Phase B½: automated investigation harness

Starts **alongside** Stage 4, not after. Depends on 2C's command
interface existing (at least a first version) and on `d3179782`'s
invariants.

| Order | ID | Item |
|---|---|---|
| 3.1 | `9b336876` | Investigation-aware bot policy using the real command interface + player-available info only |
| 3.2 | `7f6d4331` | Mystery/solvability telemetry in the Metrics struct |
| 3.3 | `c1730862` | Per-expedition information-budget reporting against the `MAX_*` invariants |

Prerequisite: the harness realism bugs in Stage H (`7dc71b94`,
`75016734`, `f81aa556`) should be fixed before 3.1 — a bot that cheats
by reading `player.map` directly can't honestly test solvability.

---

## Stage 4 — Phase C: world logic and the escape-mechanism generator

Depends on Stages 2 and 3. Test continuously against Stage 3's harness.

| Order | ID | Item | Note |
|---|---|---|---|
| 4.1 | `10855536` | Escape Proof data structure + backward causal-chain validation | **MUST land before/alongside 4.2, not after** |
| 4.2 | `53ec9e53` | Escape mechanism as a generation seed (selection before terrain/settlement) | depends on `78921694` |
| 4.3 | `44c1449a` | People / organizations / relationship evidence layer | depends on zone/district + contextual loot; resolve the historical-vs-simulated fork first |
| 4.4 | `403bf871` | Town Center: win-trigger → information-rich location | the central premise change; depends on Phase B landed |
| 4.5 | `ddd8ce16` | New escape-discovery win condition (which `known_facts` set = "knows how to escape") | depends on 4.4 |
| 4.6 | `0b052554` | Mountain-boundary Phase 3: a pass/tunnel through the ring = the real escape route | depends on 4.5 |
| 4.7 | `d3179782` | World validation + failure-mode handling (implementation, once the invariants from Stage 1 are set) | investigate as Phase C generation-order changes land |

---

## Stage 5 — Phase D/E: campaign narrative

Depends on Stage 4.

| Order | ID | Item |
|---|---|---|
| 5.1 | `55df661d` | Campaign-as-chapters — narrative framing text per expedition tier |
| 5.2 | `20c9c192` | Real campaign-victory payoff (needs the knowledge layer to have content to reveal) |
| 5.3 | `87dc4cf0` | Deprecate/replace the goal/task system (`go`/`goals`/`complete`/`ts`/`ct`) with the knowledge interaction model |
| 5.4 | `a59a2da5` | Balance-sweep extension for full escape-world campaigns (lower priority) |

**Not phase-gated — slot in any time after 2A.2:**

| ID | Item |
|---|---|
| `ef3e9bf6` | Mountain-boundary Phase 2 — organic/irregular ring instead of uniform 1-tile width |

---

## Stage 6 — Follow-up

| ID | Item |
|---|---|
| `cc49e8e8` | Rewrite `README.md` as a player-facing document once the direction has landed |

---

## Stage H — Track 2: current-engine cleanup (mostly parallel to Track 1)

### H1 — Balance-harness realism bugs (pull forward — Stage 3 depends on these)

| Order | ID | Item |
|---|---|---|
| H1.1 | `7dc71b94` | Bug A (dominant): `_find_town_center()` scans `player.map` directly, no fog-of-war — bot knows the goal instantly |
| H1.2 | `75016734` | Bug B: `_bfs_path()` routes using full-map terrain knowledge |
| H1.3 | `f81aa556` | Bug C: `_step_is_legal()` / `_random_legal_step()` read `player.map` directly for terrain legality |
| H1.4 | `cee4cb36` | Investigation D: combat policy always fights, never flees |

### H2 — Balance-harness protocol & reporting

| ID | Item |
|---|---|
| `2fbb435a` | H: establish two labeled balance-test protocols (combat stress test vs. full campaign) |
| `5de4d6fd` | E: per-expedition-tier survival breakdown in the non-campaign report |
| `d04cd313` | F: per-run player-progression snapshot |
| `3fcea5fe` | G: exploration-specific metrics (buildings entered/searched, settlements found, tiles seen) |

### H3 — Exploration/objective investigation pass (Q1–Q12)

`4b0fafcc` (Q6 — decoy vs. objective settlement, `self.settlement_explored`
is a single global bool) is flagged **THE CORE FIX** and overlaps
directly with Stage 4.4 (Town Center role change) — do it as part of
Stage 4, not here.

`8f9ec034` (Q3 — what a found map reveals now that there are multiple
settlements) is a real change and pairs with 2C.6.

The rest (`121c7b10` Q1, `fb492c15` Q2, `54340f22` Q4, `3b6975b0` Q5,
`20d5281b` Q7, `803192db` Q8, `063f5c8c` Q9, `322ce1e4` Q10,
`8ade9640` Q11, `972de29e` Q12) are mostly "proposed answer is already
true in the current code — confirm and document." Low effort, do in one
sitting whenever; they inform Stage 1's Phase 0 investigation.

`ec98648a` — tune endgame difficulty ramp (expeditions 7–9; only 27%
of campaigns complete all 10). Independent balance tuning; do after H1
(so the harness data is trustworthy).

---

## One-screen summary

```
Stage 0  Vertical slice ............... 138c10f6 dd70ae0c d7a712dc 4f8fdc57 ceee7e54 9f831f9d
         └─ 9f831f9d is the GO/NO-GO gate
Stage 1  Decision gates .............. 78921694 457c93a6 182bdc49 d3179782  (+ open design forks)
Stage 2  Phase A + B ................. 2A: aa461cec 6c9f672a 98ab82c7 7ecd39cc b31aac00
                                       2B: 93edaf83 6c9a4ca6 7db3c4b5
                                       2C: f6d126f9 e3a1e201 478c2cf9 9c2db876 a6de97c0 1f2c7826 2977a8a1
                                       2D: 1255e24e a9c8c83e
Stage 3  Phase B½ harness ............ 9b336876 7f6d4331 c1730862   (needs H1 first)
Stage 4  Phase C generator .......... 10855536 53ec9e53 44c1449a 403bf871 ddd8ce16 0b052554 d3179782
                                       (+ 4b0fafcc / Q6 folded in here)
Stage 5  Phase D/E campaign ......... 55df661d 20c9c192 87dc4cf0 a59a2da5   (ef3e9bf6 anytime)
Stage 6  Follow-up .................. cc49e8e8

Track 2 (parallel):
Stage H1 harness bugs .............. 7dc71b94 75016734 f81aa556 cee4cb36   (pull forward)
Stage H2 harness reporting ......... 2fbb435a 5de4d6fd d04cd313 3fcea5fe
Stage H3 Q-pass ................... 8f9ec034 + (Q1,Q2,Q4,Q5,Q7-Q12 confirmations) + ec98648a
```
