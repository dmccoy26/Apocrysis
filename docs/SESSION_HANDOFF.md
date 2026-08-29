# Session handoff — Apocrysis v5

Last updated **2026-08-29** (overnight build complete — all 5 phases
shipped — then a long roadmap/direction session). **Read this first in
a fresh session.**

---

## >> DIRECTION (2026-08-29, v5 — Phase A started)

- Renamed to **v5** (branch + dir). `origin/version-4` kept as a frozen marker.
- **§10 decision pass LOCKED** — `docs/PHASE_A_DECISIONS.md`. World truth
  **A "The Cordon"**; build behind a thin **`World` seam** now; **world 1
  fact-DAG-only**; CH1+CH2 first.
- **Phase A todo list**: `docs/PHASE_A_TODO.md` (11 items). Not yet
  queued in Atlas — the last `todo add` mis-bound targets via `--file`;
  re-add per-file with no batch `--file`.
- **Atlas capability run**: `docs/ATLAS_CAPABILITY_LOG.md`. Owner wants
  every `atlas request` on this repo tracked vs the v4 0-for-5 baseline.
  4 attempts logged; fixed an `atlas scan` crash in Atlas itself.
- **Structure**: `docs/STRUCTURE_ASSESSMENT.md` — no big restructure;
  `worlds/` seam (A.0) + `worldgen/` split (C.0) are the only two, both
  in the roadmap. Cheap wins pending: split `test_apocrysis.py`; delete
  the slice scaffolding (needs owner sign-off).
- **Next**: decide test-split / slice-deletion, then Phase A step 0 (the
  seam) — likely hand-written, letting Atlas attempt each piece first.

---

## >> DIRECTION (2026-08-29, session continued) — read these two first

The project's direction has moved past "more mechanisms." Two new docs:

- **`docs/APOCRYSIS_ROADMAP.md`** — the buildable plan. Apocrysis gets
  a *world-investigation spine*: one authored question ("what happened
  to the region?") that every procedural expedition answers a piece of.
  Phased A–E. **Phase A question: the smallest version of the story
  engine that makes "The Silence" feel like a story.** Open decisions
  in §10 — nothing is being built yet; the world truth isn't picked
  (`docs/WORLD_TRUTH_CANDIDATES.md`, three candidates, A/B/C).
- **`docs/APOCRYSIS_STORY_ENGINE.md`** — the far-horizon brainstorm
  (Story Ledger, death model, the "Trace" causal-model principle, the
  eight story-engine primitives). Ambitious on purpose; kept separate
  so it can't masquerade as a near-term requirement. World 1's causal
  history is **frozen and hand-authored** — no runtime simulation.

The overnight scenario/mechanism work below is done and feeds the
roadmap (`SCENARIO_SEEDS.md` / `SCENARIO_EXPANSION.md` = the discovery
grammar).

---

## Overnight build 2026-08-29 — DONE (all 5 phases, `NIGHT_BUILD_PLAN.md`)

Autonomous build. Goal was *make Apocrysis produce many
different-feeling escape stories from a small set of mechanisms.*
**All 5 phases shipped and pushed** to `origin/version-5`. Working tree
clean. **164 tests + 100 subtests** green (both runners). 10-mechanism
bot run at the bottom. `git stash` mined + dropped. Atlas confirmed
unusable for this repo (two more rejected proposals — see Phase 2).

The nightly commits: `f4f241e` (Phase 1) · `18ad92b` (Phase 2) ·
`c8231f2` (Phase 3) · `05e736e` (Phase 4) · `748c40a` (Phase 5) ·
`8c72330` (handoff + 10k numbers).

**Progress:**
- [x] **Phase 1 — scenario library.** `SCENARIO_SEEDS.md` brought to the
  full 16-field schema (~49 seeds; story signature / duplicate-of / kid
  rating added, signature census). `SCENARIO_EXPANSION.md` written (5
  levels of randomness, variety rules A/B/C with the signature formula,
  the 5 validation categories, directional-truth spec, build-priority
  sequence). Doc-only, no code. Committed.

- [x] **Phase 2 — transportation (`airfield_plane`).** Hand-written
  (Atlas tried the MECHANISMS entry twice, both proposals diffed
  against a stale index and would have reverted the require2 work —
  rejected, entry hand-written; also rejected one stale
  `mystery_apply_fix` workflow left over from a prior session).
  `Mystery.requirement_items` (order-free checklist) + validate +
  save/load round-trip; `build_mystery` places the plane nearest the
  gap and a `require2` field-store side-trip, adds `E_require2_a/b`;
  `_mystery_has_all_items` / `_mystery_missing_items` on the mixin,
  obstacle opens on the full checklist, `mystery_bump_obstacle` /
  `mystery_clear_obstacle` name the missing part(s) and use
  `assemble_desc`; a transportation branch in `_objective_steps`
  (one line per part with its own ✓/▸ + heading). Bot: visits
  `require2`; `--force-mechanism` flag + a per-mechanism campaign-goal
  table (`mystery_solved` = Escape Proof reached even if the bot then
  died) + `mystery_solved` metric. Forced 100-game: 86% solved / 85%
  survived / median 41, 10/10 deaths zombie combat. Unforced 300-game:
  85.3% survival, 0 timeouts, 44/44 deaths zombie combat,
  `airfield_plane` 92.6% solved. 154 tests + 40 subtests green.
  Committed.

- [x] **Phase 3 — time-pressure (`tidal_causeway`).** Hand-written.
  `docs/MECHANISM_TIME_PRESSURE.md` written. New `triage` word in
  `REASONING_PATTERNS`. `Mystery.deadline` / `tide_recovery` / `crossed`
  + save/load round-trip. `build_mystery`: route site nearest the gap,
  obstacle **open at build** (tide is out), `require_ev`/`require_fact`
  spec keys so an item-less mechanism doesn't say "you find the None
  here". Mixin: `_mystery_arm_deadline` (fires when `F_ROUTE` lands —
  diegetic), `_mystery_tide_tick` (per-turn from `move_and_search`
  after decay: banners at 10/5/2, soft-fail flood at 0 → `tide_recovery`
  countdown → reopen + reset), bump/escape/obstacle-ready all respect
  `crossed`. TUI: time-pressure `_objective_steps` branch + a
  `the tide turns in ~N` / `causeway flooded — ~N to low tide` WARNINGS
  line. Bot: triages by skipping the tide-board site. Hand sim (15
  seeds): focused player wins every time, dawdling floods then recovers,
  save/load preserves the clock. Forced 100-game: 86% survived / 88%
  solved / median 20, 12/12 deaths zombie combat, 2 timeouts (flooded-
  tile path loop, rare). Unforced 300-game: 90% survival, 0 timeouts,
  30/30 deaths zombie combat. 158 tests + 40 subtests green. Committed.

- [x] **Phase 4 — directional-truth audit.** `_assert_directional_truth`
  in `escape.py`, run in `build_mystery` before `validate()`. Any
  compass word the *generator* injected into evidence must agree with
  the spawn→gap vector; authored MECHANISMS scenery (`the eastern
  hills`, control names like `the west intake`) is flattened out and
  gets a pass. Plus a positive check that the two bearing-injected
  clues (`E_obstacle_a` tail, `E_route_reveal`) carry the right
  direction — a derivation-refactor guard. All 10 mechanisms clean
  across 200 seeds. +2 tests (60-seed sweep, catches-a-lie). 160 tests
  + 100 subtests green. Committed.

- [x] **Phase 5 — variety rules B + C.** `escape.py`: `story_signature()`
  (`family|dependency-class|exit-type` string) + `choose_mechanism` now
  takes `recent_mechanisms` / `recent_signatures` and applies Rule A
  (no back-to-back family), B (not one of the last 2 mechanisms), C
  (not one of the last 2 signatures) — each only when it leaves a
  candidate. `Apocrysis._recent_mechanisms` / `_recent_signatures`
  class rings (length 2), updated on escape next to `_last_family`,
  persisted through the profile like `73ff535`. Over a simulated 400-
  expedition campaign, A-B-A mechanism repeats dropped 10 → 0. +4
  tests. 164 tests + 100 subtests green. Unforced 300-game bot: 87.7%
  survival, 0 timeouts, 100% combat deaths, and a visibly more even
  mechanism spread. Committed.

**10,000-game bot run (`--games 10000 --seed 1`), all 10 mechanisms:**
87.0% won (8704), 1277 died (**1277/1277 zombie combat**), 19 timeout
(0.19% — flooded-causeway path loop + normal bot dead-ends, pre-existing
class). Per-mechanism survived / solved / median turns: radio_tower
86.6 / 95.9 / 28 · tidal_causeway 88.0 / 88.7 / 21 · evac_corridor
89.8 / 90.5 / 26 · dam_valves 89.2 / 90.1 / 26 · power_station 86.5 /
86.8 / 29 · boat_crossing 87.7 / 88.7 / 29 · airfield_plane 81.8 /
82.7 / 40 (longest — two-store detour) · service_route 87.1 / 87.5 /
29 · rail_tunnel 86.0 / 87.5 / 26 · mountain_pass 87.1 / 87.6 / 25.
Even mechanism spread (886–1119 each) from variety rules B+C. **Frozen
balance held** — every death is the survival layer, no new failure
mode. `tools/balance_autoplay.py --force-mechanism <name>` pins one
family; the per-mechanism table prints on any run.

**FROZEN (do not touch — held through all 5 phases, confirmed by the
10k bot run):** combat numbers · hunger/thirst decay · encounter rate ·
loot rate · map growth · a hard movement cap at 0/0. No fetch reskins.
No assist mode.

**Atlas can't edit this repo** — tried the `airfield_plane` MECHANISMS
entry twice via `atlas request --file`; both proposals diffed against a
stale index and would have reverted the `require2` work. Rejected both
+ one stale leftover `mystery_apply_fix` workflow. Every line this
session was hand-written. Also: 5 todos filed into Atlas's own
`atlas-self` workspace todo list to fix the failure modes
(`0c03efc9` patch scope-containment · `430be5ca` confidence vs scope ·
`2f67f707` stale-workflow detection · `90229f32` file disambiguation ·
`2222271b` span-scoped generation). Roadmap-relevant Atlas capability:
none for this repo — hand-write everything.

---

## Where things are

- **Working tree:** `projects/apocrysis/version-5/` (only v5 copy;
  `version-1..3/` are read-only clones).
- **Branch:** `version-5`, pushed to `github.com/dmccoy26/Apocrysis`.
  HEAD: `babc7c3` (2026-08-29 end of session) or later.
- **Run:** `python3 apocrysis.py` (TUI) · `--classic` · `--slice`
  (tutorial) · `--test` · `--log` (session transcript).
- **Tests:** `python3 apocrysis.py --test` (unittest) **and**
  `.venv/bin/python -m pytest -q` from the Atlas repo root — **164
  pass + 100 subtests** (2026-08-29, post-overnight-build). Run both; the unittest runner
  misses async-TUI thread-context bugs that pytest catches.
- **Harnesses:** `tools/balance_autoplay.py` (v4-aware bot + full
  report), `tools/mystery_solver.py`, `tools/slice_playtest.py`.
- **Playtest harness:** `tools/playtest_three.py <mechanism>|shuffle` —
  forces a mechanism (bypasses `choose_mechanism`); for the blind
  gate. Normal play is `apocrysis.py`.

## What v4 is

An investigation game. Every expedition, `build_mystery()`
(`src/escape.py`) generates an escape mystery onto the map; you win by
reconstructing the "Escape Proof" (the four-state knowledge model) and
taking the route — not by reaching a Town Center. Playable end to end,
~86–88% bot survival, median ~44-turn wins.

## Key architecture

- **`src/knowledge.py`** — the four-object model (Fact / Evidence /
  Deduction / Hypothesis). States (Observed/Known/Suspected/Confirmed)
  are *derived* from discovered evidence; transitions automatic.
- **`src/escape.py`** — `MECHANISMS` (**10** escape mechanisms, each
  with a story-family **classification**; see below), `choose_mechanism`
  (shuffle-bag + variety rules A/B/C: no back-to-back family, no recent
  mechanism, no recent `story_signature`), `build_mystery(game)`
  (assigns role sites, carves one gap in the mountain ring, builds +
  `validate()`s the proof, runs `_assert_directional_truth`). `Mystery`
  carries `family/discovery/reasoning/resolution/confirmation`, plus
  `power_role`/`power_restored` (infrastructural),
  `controls`/`correct_control` (experimental),
  `requirement_items`/`assemble_desc` (transportation), and
  `deadline`/`tide_recovery`/`crossed` (time-pressure).
- **`src/mixins/mystery_mixin.py`** — the investigation loop.
  `mystery_arrive` auto-discovers all evidence at a site;
  `_mystery_obstacle_ready()` gates the obstacle (spatial: carry the
  item · infrastructural: `power_restored` · experimental:
  `obstacle_open`, set by `pull`); `mystery_pull_control` is the
  experimental verb; `_mystery_progress_flare` fires the `★` banners.
- **`src/tui.py`** — MOVE/TYPE roguelike input, the panels,
  `_objective_steps` (the bottom-right OBJECTIVES checklist,
  **generated from the mystery**), `_status_block` (OBJECTIVES +
  WARNINGS).
- `src/mixins/ui_mixin.py` — `announce_event` (the `═══` banners:
  `kind=lead/discovery/objective/warn`), `_action_bar`,
  `_render_map_lines` + `_mystery_site_mark` (the `!` markers),
  `print_help`.
- `src/mixins/slice_mixin.py` — the hand-authored tutorial.
- `src/campaign.py`, `src/playlog.py`. Win finalisation:
  `world_mixin.finish_expedition()`.

## The escape-story matrix (the current work)

Docs: `ESCAPE_STORY_LIBRARY.md` (10 families + ~24 scenarios),
`ESCAPE_STORY_SCHEMA.md` (v1 — vocabularies, `Mystery` fields,
invariants, §4 = which primitives generalise vs need extending),
`PLAYER_UNDERSTANDING.md` (the UX rules — read this).

**10 mechanisms, by family:**

| mechanism | family | player question |
|---|---|---|
| mountain_pass, rail_tunnel | spatial | where is the route? |
| service_route | infrastructural | (light — still a fetch) |
| boat_crossing | transportation | (light) |
| evac_corridor | sequential | (light) |
| **power_station** | **infrastructural** | what dependency makes this work? (gate ← hydro ← fuel; fuel applied at the generator, not the gate) |
| **dam_valves** | **experimental** | which of these controls is it? (the obvious one is never right; pulling it says why) |
| **radio_tower** | **informational** | what can I learn that I couldn't see? (fuel the transmitter; a voice reads you a road that was never on the map) |
| **airfield_plane** | **transportation** | the way out is a machine — what does it need? (propeller + avgas, a two-box checklist, fetched in any order) |
| **tidal_causeway** | **time_pressure** | what must I finish before it changes? (cross before the tide; soft failure — wait out the flood, go on the next low tide) |

Six genuinely-different grammars now: `power_station`
(`MECHANISM_INFRASTRUCTURAL.md`), `dam_valves`
(`MECHANISM_EXPERIMENTAL.md`), `radio_tower`
(`MECHANISM_INFORMATIONAL.md`), `airfield_plane`
(`MECHANISM_TRANSPORTATION.md`), `tidal_causeway`
(`MECHANISM_TIME_PRESSURE.md`), plus spatial. Variety rules A+B+C keep
consecutive expeditions from repeating a family, a mechanism, or a
story shape (`SCENARIO_EXPANSION.md` §3).

## >> THE THREE-MYSTERY PLAYTEST (`69d78812` / `9ae794b9`): **PASSED 2026-08-28**

Three families played blind by a human, over two rounds (round 1
exposed an action-affordance gap, 5 fixes landed, round 2 confirmed):

- **A `mountain_pass` (spatial):** WON clean, no mechanic confusion.
- **B `power_station` (infrastructural):** WON.
- **C `dam_valves` (experimental):** solved via `pull` after the recap.

Each reads as a different *kind* of problem — the objective panel
alone distinguishes them (`got the forestry gate key` / `restored
power at the hydro station` / `worked out which control clears the
way`). **Apocrysis generates different problems, not different
scenery.** Tier-2 families are unblocked: `ea1d52be` informational,
`17f2a0ca` transportation, `5761c63f` time-pressure.

Balance is **FROZEN** (Atlas decision recorded) — do NOT tune combat
or resources off the bot. This playtest replaced another sweep.

**Harness ready:** `python3 tools/playtest_three.py shuffle` runs one
blind mystery; do it 3×. `A`/`B`/`C` force spatial/infrastructural/
experimental. Answer sheet + facilitator key:
`docs/PLAYTEST_three_mystery_ANSWERS.md`.

### Playtest round 1 (2026-08-28) — 2 of 3 runs, both non-spatial

Runs: B `power_station` (infra), C `dam_valves` (experimental). Both
players could *name the kind of problem* (comprehension ~passing) but
**could not execute the resolution action**, and died of attrition
while confused. One root cause: the two non-spatial families are the
only ones needing an explicit player action at a site (walk fuel back
to the power site / `pull` a control), and the game never signalled
that — every other interaction is passive (arrive = discovered).
Compounded by: revisiting a mystery site printed **nothing** (place
already named, evidence already revealed → dead silence, reads as
"empty"); and `t`/think hit a dead-end "doesn't point anywhere yet"
even with the next step fully determined.

**Fixes landed (all pushed, 145 tests + 40 subtests green):**
- `ae1a812` — revisiting a mystery site now reprints a terse recap
  (label + found evidence + action hint: `pull <name>` at the control
  room, "generator needs the {item} from {place}" at the hydro site).
- `8353a0d` — `t` synthesises the next step for infra/experimental
  instead of the dead-end line.
- `a4a9e8c` — objective panel `▸` hot line reads as an instruction
  (`▸ get the jerrycan of fuel to the hydro station`, `▸ try the
  controls one at a time - pull each`) not a past-tense achievement.

### Playtest round 2 (2026-08-28) — fixes confirmed

- **C `dam_valves`:** player read the revisit recap, typed `pull
  intake`, opened the way. **First experimental solve.** Died later to
  a zombie on the walk out (survival layer, frozen) — investigation
  bar PASSED.
- **B `power_station`:** **WON** (turn 60). Recap sent them for the
  jerrycan; walking back onto the hydro tile auto-restored power. But
  they didn't believe it worked — ~20 turns typing `fill generator` /
  `use fuel` / `pull gate` / `inspect panel`, and `t` still
  dead-ended (power on but route not yet found). Marginal pass.

Two more fixes for the B friction (pushed, 145+40 green):
- `6e18632` — `t` 4th case: power restored + route unknown → "the
  gate has power now, you still have to find where the route comes
  through."
- `55a6a65` — explicit `use`/`fill`/`refuel`/`pour`/`apply` verb at
  the power site (`mystery_apply_fix`): applies the fix like
  auto-on-arrival, or points forward if already done.

### Round 3 — A `mountain_pass` (spatial): **WON** turn 120

Clean. Got the key, objective panel tracked it, walked to the gate →
opened → confirmed → escaped. No mechanic confusion. 120 turns is a
big 18×18 map + wandering, not stuck-ness. **Gate passed.**

### Input rework (`893d0e1`)

MOVE/TYPE modes removed. The command box is always focused; arrow keys
move (priority bindings), everything else is typed + Enter. No more
wasd remap, no mode toggle/hint, `on_key` gone. Bare Enter at `>` is a
silent no-op. Numbered equip restored: `1`..`N` = weapon from `i`,
`W1`/`W2` = armor, straight from the `>` prompt.

### Eat/drink is a meal now (`01425cb`)

Playtest: "spent half the game eating." `eat`/`drink` consumed one
ration (+5) per turn vs −2/turn decay → constant nibbling. Now one
action eats up to 6 rations (+5 each, capped by the deficit), same
rations-per-point economy. Lake drink +4 → +15. Balance bot (400
games, seed 7): survival 85.5%→84.5% (noise; still 100% combat deaths,
zero starvation), median completion 46→42 turns. Frozen-balance line
held — economy unchanged, only the action tax removed.

### Requirement lead moved to the route site (`ee84647`)

Playtest (spatial): learned "locked gate" at the noticeboard, trekked
to the gate, *then* got told "key's at the ranger station" — wasted
trip + backtrack, objective panel couldn't warn. `E_require_a` moved
`location='obstacle'` → `location='route'`, so the route site
(noticeboard / marina / tunnel mouth) now gives the whole briefing at
once (route + obstacle + where the key/item/controls are), both places
map-marked in the same beat. All mechanisms.

### Informational family — `radio_tower` (`ea1d52be`, DONE)

The third genuinely-different grammar. The way out isn't a place you
find — a broadcast log says the channel is monitored from outside; the
tower's transmitter is dead; fuel the generator and **a voice answers
and reads you an emergency access road that was never on the map**.
Reuses the whole `power_station` machinery + one `reveals_route` flag:
`F_ROUTE` withheld from every early site, lands only via
`E_route_reveal` on `power_restored`; escape-tile marker gated on
`F_ROUTE`; objective-panel header stops leaking the route name until
then. Doc: `MECHANISM_INFORMATIONAL.md`. Full end-to-end sim passes.
**Bot: ~82.5% aggregate (4 seeds) vs ~85.8% baseline — ~3pt drop,
still 100% combat deaths, no new failure mode. `radio_tower` solo
~77%** (more traversal). Needs a human blind playtest like the other
three got — `python3 tools/playtest_three.py radio_tower`.

**Playtest 1 (radio_tower):** mechanic worked end to end — found the
log, fueled the generator, got the voice/route reveal, objective panel
tracked it all. Died on the SW trek to the far-corner escape gap on a
21×21 map (out of water, Armored Zombie) — the same "solved it, died
getting out" pattern as every other playtest this session (5/5). Fixed
`b??????` — revisiting the require site (walked back down past the
depot) re-handed the jerrycan and re-fired "take it to the generator
shed"; now guarded on the fix being done, recap says "nothing more to
take here." Applies to all fetch families.

Known v1 limitations: the "broadcast tower" obstacle site sits at the
escape gap (schema `escape_kind` not built), so a player with the
found-map could guess the ridge area before the response — but can't
confirm or use it. Objective step "found what blocks the route" is
generic (no physical block for informational).

### Traversal pacing — levers A + B (DONE)

Invariant 3d (`ESCAPE_STORY_SCHEMA.md` / `PACING_MYSTERY_TO_EXIT.md`):
the critical path must carry geographic momentum toward the exit; no
unrelated post-solution trek. **A** (`c816232`) — informational: the
radio response confirms the hypothesis, `escape` from anywhere. **B**
(`build_mystery` + `_carve_escape_pass`) — sites placed along the
spawn->exit run, gap at ~65th-percentile distance. Bot: survival held
~85% / 100% combat deaths, **median expedition 43 -> 27 turns**. The
radio_tower -3pt is erased. Combat/resources still FROZEN.

### New-player legibility (kid playtests, 2026-08-28 night)

Son (age ~kid) played 3 radio_tower runs. All 3: understood/solved the
mystery, died anyway. Fixes:
- `5778432` — "YOU CAN LEAVE NOW" banner + objective hot line the moment
  `escape` works from anywhere (he solved it, walked to the marker,
  died one tile short).
- `4012664` — compass headings: objective `▸ go to the ranger depot
  (west)` and lead banners "it's (west of you), marked on your map"
  ("marked on your map" alone means nothing to a kid).
- `d572268` — nudges: `⚠ GETTING HUNGRY / type eat` when low + have
  supplies (re-arms >45); `(your Kitchen Knife barely scratches them -
  search buildings for a heavier weapon)` once/expedition when stuck
  with a <10-dmg weapon and nothing better. UI only, bot unaffected.
- `ea4e48d` — combat: empty ranged weapon never recommended as a swap
  and does no phantom str//3 damage (falls back to a 2-dmg club).
- `73ff535` — `_used_mechanisms`/`_last_family` now save/load through
  the profile (no-back-to-back-family survives quit/relaunch); hunger/
  thirst warnings escalate <=30 -> <=10 -> 0, one shot per tier,
  re-arm >45. NO movement cap - starvation stays HP attrition, just
  made legible.

**Kid result (2026-08-29):** BlueNoodle (hardcore) won 3 expeditions
after the fixes, then died to an Armored Zombie on map 3 — permadeath,
character gone. Each death was survival-layer (starving, weak weapon),
not mystery confusion. Follow-ups shipped:
- `cde361a` — HUD + end screen show **map level** (`expeditions_completed
  + 1` and the map size). Dad's tracking how far the kid gets.
- `aa73a64` — route-step objective line is now `▸ head for the way out
  (SW)` with a compass bearing, not the directionless `▸ found a way
  toward another route` (a kid did the whole fuel chain then couldn't
  find the tunnel).

**Confirmed by the kid playtests, don't rebuild:** the escalating
warnings all fire correctly and a 7-year-old ignores every one of
them. That's the answer to "does this game need an assist mode" —
maybe, but the user said **no assist mode**. The game stays as-is;
he dies a lot and has fun.

**Still open:** (a) cosmetic: power site keeps its `!` after
`power_restored`; (b) `m.escape_kind` for transportation/environmental
(deferred — roadmap Phase D); (c) the roadmap — see **DIRECTION** at
the top.

## Design rules (settled — don't relitigate)

1. **Four panels answer four questions:** Map=WHERE · Journal=WHAT I
   LEARNED · Think=WHAT I BELIEVE · Objectives=WHAT NEXT. If the player
   must *remember* a fact to operate the game, the UI remembers it for
   them. Investigation hard, interface easy.
2. **Most text is ambient; important info interrupts** via a `═══`
   banner (`★ NEW LEAD` / `★ NEW DISCOVERY` / `★ OBJECTIVE UPDATED` /
   `⚠`). Don't make repeated text more interesting — make it recede.
3. **Objective + banners say WHAT STATE / WHY, never HOW.** "Find the
   ranger station" — not "go to 11,4, take the red key, return."
4. **The schema is for us; the story is for the player.** `family:
   experimental` / `reasoning: revise` NEVER reaches the player.
5. **No back-to-back story family** across consecutive expeditions.
6. Earlier settled: `search` is optional (arrival auto-discovers); a
   found map reveals the whole valley; named places not generic
   buildings; `rest` costs 45 min; goal/task system removed.

## Open todos

The `atlas todo list` for this workspace is **stale** — a months-old
design-doc paste, never reconciled. Ignore it; don't `atlas todo next`.
Real open work:

- **THE BIG ONE:** `docs/APOCRYSIS_ROADMAP.md` — the world-investigation
  spine. Not started. Blocked on a §10 decision pass (see DIRECTION at
  the top). ~8 forks to lock: world truth A/B/C, game-vs-engine + the
  `World` seam, campaign scope, causal-model depth for world 1,
  region-stability window, what carries on death (`STORY_ENGINE §1D` is
  the candidate answer), the ending shape, the vocabulary rename.
- Cheap-to-reserve-now for the roadmap (fold into Phase A schema):
  `WorldSecret`, evidence provenance + epistemic status, `faction`
  tags, `deadline`-as-story-clock.
- Post-roadmap machinery (still seeded in `SCENARIO_SEEDS.md`): the
  corroboration gate (top pick — makes `Deduction` load-bearing),
  region mutation, `escape_kind=vehicle`.
- Minor/cosmetic: power-site `!` clears after `power_restored` ·
  `9779d49f` NEW DISCOVERY banner · `c359b1bb` bigger map render ·
  2 bot timeouts on flooded-causeway path loops (0.19% of 10k, benign).
- **Cut:** `6cffc528` / `e2850fa5` Tier-1 fetch reskins. `461878aa`
  campaign narrative — **subsumed by `APOCRYSIS_ROADMAP.md`.**

## Atlas — does not work here

`qwen2.5-coder-32b-instruct` (local). **Failed every non-trivial task
against this repo** — 6+ times, two models, down to "add two keys to a
dict". `escape.py` / `tui.py` / `mystery_mixin.py` / `ui_mixin.py` /
`game.py` all exceed its context, so it emits whole-file rewrites and
self-rejects, or hangs on a big dict literal. **Every code change this
session and last was hand-written.**

**2026-08-29 update:** tried once more for the `airfield_plane`
`MECHANISMS` entry — the smallest possible task — via `atlas request
--file src/escape.py`. It produced a proposal, but the diff was built
against a stale scan index and would have **silently reverted
uncommitted hand-written work** (deleted new `E_require2_a/b` evidence,
rolled back a loop), with every safety check green and confidence 1.0.
Rejected. **Do not route anything through Atlas for this repo** —
including "tiny" dict entries. Hand-write everything. (Fix todos filed
into the `atlas-self` workspace — see the overnight section above.)

## Session history (for context; detail in git log + Claude memory)

**2026-08-29** — overnight build: 5 phases (`f4f241e`..`748c40a`) taking
the mechanism count 7 → 10 (transportation, time-pressure) + the
directional-truth audit + variety rules B/C + the scenario library to
full schema. Then a long direction session: `APOCRYSIS_ROADMAP.md`
(world-investigation spine), `WORLD_TRUTH_CANDIDATES.md`, a big
brainstorm expansion, split into roadmap (plan) + `APOCRYSIS_STORY_ENGINE.md`
(vision). 5 Atlas-self-improvement todos filed. No Phase-A code yet.

Playtest-driven, 2026-08-28, ~40 commits on `version-5`:
`341ceca`..`325ed26` (playlog crashes, map declutter, growth,
archetypes, front-loaded-mystery fix, weapon nudge) →
`c1d1fad`..`e4eaa09` (event emphasis, weapon-break auto-swap, loot to
ground, building cap, revisit de-dup, escape bearing, marina water) →
`f4d42bc`..`d47ac3a` (the v4.1 UI pass: action bar, HUD blocks,
victory screen, STATUS block, water caps, escape-from-afar,
drink-from-water, starvation drain) → `49a0904`..`36cc08e` (roguelike
input, numbered inventory, mystery-generated objectives, named-place
markers) → `b89cb7a`..`8c0d3d4` (escape story schema v1,
PLAYER_UNDERSTANDING, typed banners) → `ce54c4a`..`d5a517b`
(power_station + dam_valves — the first two different grammars).

## Design docs

**Direction (read first):** `APOCRYSIS_ROADMAP.md` (the buildable
plan — world-investigation spine, Phases A–E, §10 open decisions) ·
`APOCRYSIS_STORY_ENGINE.md` (the far-horizon brainstorm — Story Ledger,
death model, Trace principle, eight primitives) ·
`WORLD_TRUTH_CANDIDATES.md` (world 1 truth — 3 candidates A/B/C,
spoiler-gated).

**Overnight-build inputs (done, feed the roadmap):**
`NIGHT_BUILD_PLAN.md` (superseded) · `SCENARIO_SEEDS.md` (~49-seed
library, full 16-field schema) · `SCENARIO_EXPANSION.md` (5 levels of
randomness / variety rules / validation) · `MECHANISM_TRANSPORTATION.md`
· `MECHANISM_TIME_PRESSURE.md`.

**Standing:** `ESCAPE_STORY_SCHEMA.md` (families, patterns, invariants
incl. **3d mystery-to-exit continuity** and **no vocab leak**) ·
`PLAYER_UNDERSTANDING.md` (the UX rules) · `PACING_MYSTERY_TO_EXIT.md`
(levers A + B, done) · `MECHANISM_INFORMATIONAL.md` /
`MECHANISM_INFRASTRUCTURAL.md` / `MECHANISM_EXPERIMENTAL.md` ·
`ESCAPE_STORY_LIBRARY.md` · `BALANCE_BASELINE_2026-08-28.md` (the
frozen numbers).

**Background:** `ESCAPE_WORLD_DESIGN_ASSESSMENT.md` ·
`VERSION_4_BUILD_ORDER.md` · `PHASE0_KNOWLEDGE_MODEL.md` ·
`V3_ASSUMPTION_AUDIT.md` · `SLICE_PLAYTEST_MECHANICAL.md`.
