# Session handoff — Apocrysis v4

Last updated **2026-08-29** (late — end of the kid-playtest session,
start of the overnight scenario-expansion build). **Read this first in
a fresh session.**

---

## >> START HERE — 2026-08-29 overnight build

**The plan for tonight is `docs/NIGHT_BUILD_PLAN.md`** (mirrored from
the rev-3 artifact). One-line version: *make Apocrysis produce many
different-feeling escape stories from a small set of mechanisms* — not
"add two more puzzle types."

**Progress (overnight 2026-08-29, autonomous build):**
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

Phases, in order:

1. **Scenario library** (first-class, not filler). **DONE** — see above.
2. **Transportation** — `airfield_plane`, two parallel `requirement_items`
   (a checklist, vs infra's serial chain). Spec: `docs/MECHANISM_TRANSPORTATION.md`.
3. **Time-pressure** — `tidal_causeway`, diegetic `deadline` from when
   `F_ROUTE` lands, escalating tide banners, **soft failure** (route
   reopens next low tide). Spec: write `docs/MECHANISM_TIME_PRESSURE.md`.
4. **Directional-truth audit** — build-time assertion: any compass word
   in generated evidence must match the vector to the site it names.
5. **Variety rules B + C** *(if runway)* — recent-scenario history +
   story-signature dedup, persisted like the family history.

**Forks resolved:** two-item assembly · soft failure · leave
`boat_crossing` alone.

**FROZEN (do not touch):** combat numbers · hunger/thirst decay ·
encounter rate · loot rate · map growth · a hard movement cap at 0/0.
No fetch reskins. No engine rewrite. No assist mode.

**`git stash@{0}`** — a rough first pass at the transportation code
(`requirement_items` field + `validate` + `build_mystery` site
placement). Predates the rev-3 design; `git stash show -p stash@{0}` to
mine it or `git stash drop` and rebuild from the doc.

**Atlas can't edit this repo** — failed the `airfield_plane` MECHANISMS
entry tonight (hung, killed). Every code change this session and last
was hand-written. Route only tiny `MECHANISMS` dict entries + library
classification through Atlas; hand-write everything else.

---

## Where things are

- **Working tree:** `projects/apocrysis/version-4/` (only v4 copy;
  `version-1..3/` are read-only clones).
- **Branch:** `version-4`, pushed to `github.com/dmccoy26/Apocrysis`.
  HEAD: `252db78` (or later).
- **Run:** `python3 apocrysis.py` (TUI) · `--classic` · `--slice`
  (tutorial) · `--test` · `--log` (session transcript).
- **Tests:** `python3 apocrysis.py --test` (unittest) **and**
  `.venv/bin/python -m pytest -q` from the Atlas repo root — **151
  pass + 40 subtests** (2026-08-29). Run both; the unittest runner
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
- **`src/escape.py`** — `MECHANISMS` (7 escape mechanisms, each with a
  story-family **classification**; see below), `choose_mechanism`
  (shuffle-bag + no back-to-back family), `build_mystery(game)`
  (assigns role sites to building tiles, carves one gap in the
  mountain ring, builds + `validate()`s the proof). `Mystery` carries
  `family/discovery/reasoning/resolution/confirmation`, plus
  `power_role`/`power_restored` (infrastructural) and
  `controls`/`correct_control` (experimental).
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

**7 mechanisms, by family:**

| mechanism | family | player question |
|---|---|---|
| mountain_pass, rail_tunnel | spatial | where is the route? |
| service_route | infrastructural | (light — still a fetch) |
| boat_crossing | transportation | (light) |
| evac_corridor | sequential | (light) |
| **power_station** | **infrastructural** | what dependency makes this work? (gate ← hydro ← fuel; fuel applied at the generator, not the gate) |
| **dam_valves** | **experimental** | which of these controls is it? (the obvious one is never right; pulling it says why) |

`power_station` (`docs/MECHANISM_INFRASTRUCTURAL.md`) and `dam_valves`
(`docs/MECHANISM_EXPERIMENTAL.md`) are the two genuinely-different
grammars built so far.

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
map-marked in the same beat. All 7 mechanisms.

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
(deferred — not in transportation v1); (c) tonight's build — see
**>> START HERE** at the top.

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
design-doc paste, never reconciled; most items are done or garbage
fragments. Ignore it; don't `atlas todo next`. Real open work:

- **Tonight:** `17f2a0ca` transportation · `5761c63f` time-pressure ·
  `66dbacb5` scenario library (see **>> START HERE**).
- Post-tonight machinery (seeded in `SCENARIO_SEEDS.md`, ranked): the
  corroboration gate, region mutation, `escape_kind=vehicle`.
- Minor/cosmetic: power-site `!` clears after `power_restored` ·
  `9779d49f` NEW DISCOVERY banner · `c359b1bb` bigger map render.
- **Not doing:** `6cffc528` / `e2850fa5` Tier-1 fetch reskins — cut.
  `461878aa` campaign narrative — needs a design conversation first.

## Atlas — does not work here

`qwen2.5-coder-32b-instruct` (local). **Failed every non-trivial task
against this repo** — 6+ times, two models, down to "add two keys to a
dict". `escape.py` / `tui.py` / `mystery_mixin.py` / `ui_mixin.py` /
`game.py` all exceed its context, so it emits whole-file rewrites and
self-rejects, or hangs on a big dict literal. **Every code change this
session and last was hand-written.**

Only attempt Atlas for: a tiny `MECHANISMS` dict entry, an isolated
data addition, scenario-library classification. Route those through
`atlas request → review → approve`, inspect the diff, reject a
rewrite. Hand-write everything in `build_mystery`, the mixins, the TUI,
save/load, turn hooks.

## Session history (for context; detail in git log + Claude memory)

Playtest-driven, 2026-08-28, ~40 commits on `version-4`:
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

**Read for tonight:** `NIGHT_BUILD_PLAN.md` (the plan) ·
`SCENARIO_SEEDS.md` (~45-seed library, first draft) ·
`SCENARIO_EXPANSION.md` (levels-of-randomness / variety-rules
direction) · `MECHANISM_TRANSPORTATION.md` (airfield_plane spec).

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
