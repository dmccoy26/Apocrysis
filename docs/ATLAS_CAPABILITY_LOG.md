# Atlas capability log — Apocrysis v5

Purpose: track what Atlas can and cannot do as it works the Phase A
todo list. Every `atlas request` / `atlas todo` attempt on this repo
gets a row, whatever the outcome. This is the running answer to "can
Atlas manage and program this upgrade?"

Prior baseline (v4 session, 2026-08-28, memory `apocrysis_v5_stage0`):
Atlas's generation pipeline was **0-for-5** here — new-file creation,
one-function rewrites, and even two-key dict-literal edits all came
back "no parseable output" or diffed against a stale index and would
have silently reverted uncommitted work. That was `qwen3.6-35b-a3b`
then `qwen2.5-coder-32b-instruct`, before the `--create` coherence
fixes (Atlas commits `3e4fe5c` / `e6b0b5c`). This run re-tests from
that baseline.

## Operating protocol (this run)

1. **Committed clean tree before every `atlas request`.** `git status`
   clean; if a bad proposal reverts to the index it reverts to nothing
   lost.
2. **Fresh `atlas scan` immediately before each request** — the
   stale-index data-loss mode (memory `atlas_stale_index_dataloss`)
   needs a stale index; deny it one.
3. **`atlas review <id>` every diff before `atlas approve`.** Read the
   whole diff. Reject anything that touches files outside the ask or
   rewrites a region wholesale.
4. **Both test suites green before the commit:** `python3 apocrysis.py
   --test` AND `../../../.venv/bin/pytest -q .`
5. **One attempt logged per row below** — request text, workflow id,
   outcome, what Claude had to do instead.
6. Claude hand-writes anything Atlas fails twice. The point is to
   ship Phase A, not to force Atlas through a wall.

## Scoreboard

| attempts | Atlas shipped | Claude hand-wrote (after fail or not routed) | Atlas-only (no rework) |
|---|---|---|---|
| 22 | 6 (`base.py` v1, `worlds/__init__.py`, `game.py` param, `truth.py`, `world_investigation.py`, `campaign.py` milestones) | ~31 | 6 |

> Phase-A-era scoreboard; see **Cumulative (Phase A + B + C)** below for
> the whole-project picture (9 of ~69 files, +C.1 `reachable.py` and
> `survivor_knowledge.py`). Nothing has been routed to Atlas since.

**Atlas can now (2 for 2 each):** a self-contained new file given
verbatim (dataclass / constant table / a class of short methods, up to
~60 lines) · a small precise unambiguous edit to a file under ~350
lines. **Everything else** — larger-file edits, multi-file, cross-module
imports, procedural test modules, renames — has been Claude's. Every
architectural decision in Phase A has been Claude's.

## RESOLVED (2026-08-29) — `atlas scan` was broken; fixed this session

`atlas scan` now works (fix committed to Atlas `zork`:
`scripts/atlas.py` scan branch re-imports `RepositoryScanner` locally —
a later branch in `main()` shadowed the module import, leaving the name
function-local and unbound). The EI store rebuilt (45 KB → 790 KB, 103
files). Remaining Atlas-tooling gaps below are **not** staleness.

## Still open — `atlas rename` can't rename constants

`atlas rename CAMPAIGN_LENGTH EXPEDITIONS_PER_CAMPAIGN` still fails with
`no Definition named 'CAMPAIGN_LENGTH' in the indexed store` even with a
fresh index. The Definition store tracks callables, not module-level
`NAME = value` assignments. So an **atomic repo-wide constant rename has
no Atlas path**: `atlas rename` won't see it, and per-file `atlas
request` can only touch one file at a time (breaking importers →
rollback). Filed in `atlas-self` (`1ba1bf47`).

## Phase A.0 seam creation (2026-08-29) — partial success

Model: `qwen2.5-coder-32b-instruct`. Index fresh (scan fixed).

| # | ask | route | workflow | outcome | notes |
|---|---|---|---|---|---|
| 5 | create all 5 seam files at once | `atlas request --file ×5 --create --force --run-tests` | (bundled, id unknown) | **REJECTED — "No repair implementation found"** | ~7 min of `full_file` generation; debug.log shows the model returning 14–44-char completions (empty/refusal) for most files. The `--create` **coherence** fixes (`3e4fe5c`/`e6b0b5c`) fixed bundling/feed-forward; they did **not** make the local model able to author 5 new files in one workflow. |
| 6 | create **one** file `src/worlds/base.py` (frozen dataclass, 15 lines) | `atlas request --file … --create --force` | `f8200b43` | **SHIPPED** ✓ | Exact, verbatim. Auto-committed `73d8ed2`. First genuine Atlas authoring success on this repo. |
| 7 | create **one** file `src/worlds/__init__.py` (1-line docstring) | same | `f00581a3` | **SHIPPED** ✓ | Exact. Auto-committed `3a49bd6`. |
| 8 | create **one** file `src/worlds/silence/world.py` (imports + `World(...)` call with imported constants) | same | `03388152` | **REJECTED-WRONG** | Model produced a **`dict` literal with `None` values** instead of `World(...)`, and **dropped both `import` lines**. It "simplified" a constructor-call-with-imports into a bare dict. Hand-written. |

### Boundary, sharpened

- **Single new file, self-contained (a dataclass, a constant, a
  docstring): Atlas can do it now.** New since v4.
- **Single new file that must `import` and then *call* something with
  the imported names: still fails** — the model flattens it to a
  literal. `world.py`, `silence/__init__.py`, `test_worlds.py`
  hand-written.
- **Multi-file `--create` (>2 files): fails outright** on this repo +
  model.

Net Phase A.0: `base.py` + `worlds/__init__.py` by Atlas; the 3 files
with real wiring by hand. Filed `atlas-self`: `--create` multi-file
generation + the import-then-construct failure mode.

| 9 | step 3 — turn `constants.py` into a re-export shim (delete 3 table defs + their comment blocks, add one `from … import` line) | `atlas request --file src/constants.py` | — | **TIMED OUT (>2 min)** | `debug.log`: repeated ~90 s full-file regeneration passes, never converged. Same large-data-block failure mode memory flagged in v4 (a `MECHANISMS` dict block "HUNG the model ~30 min"). A localized *edit* that forces the model to re-emit a data table it's deleting still triggers whole-file regeneration. Hand-written. |

### Sharpened once more

Atlas can't yet do a single-file edit whose surrounding context
contains a large literal (here: `MAP_ARCHETYPES`, ~6 lines of nested
dict) — it regenerates the whole file and never converges. Even though
the *edit* only removes lines. Same root cause as the v4 `MECHANISMS`
hang. Added to `atlas-self` `dbc93715`.

## Phase A.0 step 5 (2026-08-29) — engine reads `self.world`

| # | ask | route | workflow | outcome | notes |
|---|---|---|---|---|---|
| 10 | 4-file bundle (`game.py` + `world_mixin` + `ui_mixin` + `tui.py`), each a small precise edit | `atlas request --file ×4` | — | **TIMED OUT** at 2 min; only a `game.py` workflow materialised | huge bundled prompt (`prompt_chars` 58 637), `patch` mode, never finished the other 3 |
| 11 | `game.py` alone: add `world=None` param + `self.world = world if world is not None else SILENCE` + import | (the workflow from #10) `32ac8acf` | `32ac8acf` | **SHIPPED** ✓ | **Correct on the first try** — exact param placement, exact `if world is not None` form, import in the right block. Auto-committed `aa033a2`. Best Atlas result of the session: a real semantic edit to a 340-line existing engine file. |
| 12 | `world_mixin.py` alone: `MAP_ARCHETYPES` → `self.world.map_archetypes` (3 lines in `generate_map`) | `atlas request --file …` | (rejected) | **REJECTED — failed validation** | 1130-line file. Ran ~2 min in the background then Atlas's own validation killed the generated change. Hand-written. |
| — | `ui_mixin.py` (842 lines), `tui.py` (900 lines) | not routed | — | **HAND** | two Atlas failures already this step; both files are past the size where Atlas has ever succeeded here. Hand-written. |

### The real capability picture after A.0

**Atlas (32B coder) on this repo, ranked by what works:**

1. ✅ **Small, self-contained new file** (bare `@dataclass`, a docstring module) — reliable.
2. ✅ **Small, precise edit to a mid-size existing file** (`game.py`, 340 lines: add a param + one line + one import) — worked first try. *This is new since v4.*
3. ❌ **Edit to a large file** (>~800 lines) — rejected or times out.
4. ❌ **Edit near a large literal** — full-file regen, never converges.
5. ❌ **New file needing import-then-construct** — drops imports, emits a stub.
6. ❌ **Any multi-file bundle** (`--create` or plain `--file ×N`) — rejected or times out.

Net A.0: **2 of ~9 files by Atlas** (`base.py`, `worlds/__init__.py`,
`game.py` param). The seam's actual wiring — hand-written. The
experiment answered its question: Atlas moved its boundary a little
(#2 is real progress) but "decompose and execute a constrained
multi-file architectural change" is still out of reach.

## Phase A.1 (2026-08-29) — the `WorldFact` DAG

| # | ask | route | workflow | outcome | notes |
|---|---|---|---|---|---|
| 13 | create `src/worlds/silence/truth.py` — self-contained, ~57 lines, `WorldFact` dataclass + 9 `WorldFact(...)` constructor calls with multi-line string args | `atlas request --file … --create --force` | `49e4da00` | **SHIPPED** ✓ | Near-verbatim. **Biggest self-contained new file Atlas has produced correctly here** — and it *improved* the spec: dropped the unused `field` from `from dataclasses import …`. Auto-committed `6331d4c`. |
| 14 | create `src/tests/test_world_truth.py` — ~70 lines, 9 test methods incl. a 3-colour DFS cycle detector | `atlas request --file … --create --force` | — | **REJECTED** ("generate fewer files at once") | The DFS logic + 9 methods exceeded what the model emits in one file. Hand-written. |

### Boundary, updated

Self-contained new file: Atlas now handles **~60 lines including a
repetitive constructor-call block** (`truth.py`), not just a bare
dataclass. But a new file that's ~70 lines of **non-repetitive
procedural logic** (`test_world_truth.py`) still fails. Roughly:
Atlas can type out *structured data* it's given; it can't yet author
*algorithm* at that length. Appended to `atlas-self` `dbc93715`.

## Phase A.2 (2026-08-29) — `DiscoveryTemplate` + `target_fact`

| # | ask | route | workflow | outcome | notes |
|---|---|---|---|---|---|
| 15 | create `src/worlds/silence/discovery.py` — `from src.worlds.base import DiscoveryTemplate` + a 9-entry dict of `DiscoveryTemplate(...)` | `atlas request --file … --create --force` | `333b4b23` | **REJECTED-WRONG** | The `DISCOVERY_TEMPLATES` dict was **perfect**. But Atlas **redefined `DiscoveryTemplate` locally** (plain class, `.name` not `.world_fact_id`) instead of importing it from `base.py`. Exact `dbc93715` failure — the model stubs a cross-module dependency rather than importing it. Hand-written. |
| 16 | `src/worlds/base.py` — add `DiscoveryTemplate` dataclass + a `discovery_templates` field to `World` (16-line file) | not routed | — | **HAND** | wanted to keep `base.py` + `discovery.py` + `world.py` as one coherent change; #15 showed Atlas can't do the import anyway |
| 17 | `src/escape.py` — `Mystery.world_fact_id` + `build_mystery(target_fact=…)` branch (917-line file) | `atlas request --file src/escape.py` | — | **KILLED** (did not converge in ~4 min, killed) | 917 lines — same wall as `world_mixin` (#12). Hand-written. |
| 18 | `src/tests/test_discovery.py` — 9 tests incl. BFS reachability + anti-injection | not routed | — | **HAND** | procedural, past the `test_world_truth` line boundary |

Net A.2: **0 of 5 files by Atlas** — the one it could have done
(`discovery.py`, structured data) it botched on the import. The rest
are large-file or procedural, both known walls.

## Phase A.3 (2026-08-29) — World Investigation state

| # | ask | route | workflow | outcome | notes |
|---|---|---|---|---|---|
| 19 | create `src/world_investigation.py` — a **full class**, ~58 lines, self-contained (no `src` imports), with procedural methods (`eligible`/`thread_progress`/`milestones_known` = list comprehensions with conditions) | `atlas request --file … --create --force` | `c5f9c529` | **SHIPPED verbatim** ✓ | **The most procedural file Atlas has produced correctly here.** Bigger and more logic-heavy than `test_world_truth.py` (#14, rejected). Distinguishing factor: one coherent class of short methods, given verbatim, vs a test module of 9 independent methods + a DFS. Auto-committed `96c9580`. |
| 20–24 | `worlds/base.py` field, `worlds/silence/world.py` import+arg, `game.py` class-var + ctor lines, `mystery_mixin.py` (664 ln) 2-line hook, `persistence_mixin.py` (555 ln) round-trip | **not routed** | — | **HAND** | `base`+`world` are the cross-module-import shape (#8, #15 both failed); `mystery_mixin`/`persistence_mixin` are past the ~800-line-ish edit wall (#12, #17). Routing them would only re-confirm known gaps and cost ~15 min. Hooks are 2–6 precise lines each. |
| 25 | `test_world_investigation.py` — 10 tests, tempfile profile round-trip, resolution-hook driving | not routed | — | **HAND** | procedural, past #14's line boundary |

Net A.3: **1 of 7 files by Atlas** — but it's the substantive one
(`WorldInvestigation` itself). The wiring is small and hand-written.

## Phase A.4 (2026-08-29) — surfacing the investigation

| # | ask | route | workflow | outcome | notes |
|---|---|---|---|---|---|
| 26 | `campaign.chapter_intro` — add a `milestones_known=0` param, key the chapter line to it (advance-only), keep the header string (55-line file) | `atlas request --file src/campaign.py` | `1aaf5024` | **SHIPPED verbatim** ✓ | Exact diff, first try, all safety checks green. Auto-committed `0a07781`. **2nd clean small-file *edit* success** (after `game.py` param). |
| 27 | `ui_mixin.world_investigation_screen()` + command wiring (843 ln) | not routed | — | **HAND** | past the edit wall |
| 28 | `world_mixin.generate_map()` `target_fact` wiring (1130 ln) | not routed | — | **HAND** | past the edit wall |
| 29 | `escape.py` variety-aware target pick (920 ln) | not routed | — | **HAND** | past the edit wall (#12, #17 already confirmed) |
| 30 | `discovery.py` 2nd routes, `world_investigation.py` `fact()` helper, `world.py` `thread_titles`, `mystery_mixin` banner hook, `ui_mixin` `announce_event` milestone branch, `cli.py` caller, 3 test files | not routed | — | **HAND** | cross-import / large-file / procedural — all known walls |

Net A.4: **1 of ~11 files by Atlas** (`campaign.py`). But it's a real
data point — small, self-contained *edits* to files under ~350 lines
now work reliably (2 for 2).

## Phase A.5 (2026-08-29) — coherence pass

**Nothing routed to Atlas.** Every A.5 change was to `ui_mixin.py`
(870 ln), `mystery_mixin.py` (690), `tui.py` (920), or a mid-function
6-line edit to `cli.py` — all past or at the edit wall, none a
self-contained new file. The `campaign.py`-style opportunity did not
recur. All hand-written. This is itself a data point: **a
presentation/coherence pass on an existing codebase gives Atlas (at
this capability level) essentially no surface** — the work is
distributed small edits across large files, which is exactly what it
can't do.

## Phase A end state — Atlas final tally

**6 files shipped by Atlas** over A.0–A.5 (~40 files touched total):

| file | kind |
|---|---|
| `src/worlds/base.py` (v1) | new, self-contained dataclass |
| `src/worlds/__init__.py` | new, one-line |
| `src/worlds/silence/truth.py` | new, self-contained, 9 constructor calls |
| `src/world_investigation.py` | new, self-contained, a class of 11 short methods |
| `src/game.py` (world param) | small precise edit, 340-line file |
| `src/campaign.py` (milestones) | small precise edit, 55-line file |

**Everything else — the seam wiring, every large-file edit, every
multi-file change, every cross-import module, every test file, the
rename — was Claude's. Every architectural decision was Claude's.**

The capability gained since v4 (`0-for-5`) is real: Atlas can now be a
reliable typist for a fully-specified, self-contained leaf file or a
small unambiguous edit to a small file. It is not yet a participant in
architecture or in changes that span the existing codebase.

## 9 `atlas-self` capability todos filed this session

`dbc93715` (multi-file + import-construct + procedural-length) ·
`f7ee975b` (data-block edit non-convergence) · `c4b89284` (large-file
edit) · `1ba1bf47` (constant rename) · `89efb2fc` (new-file length
boundary) · `434396fb` (import-stub, 3 repros) · `9fd6b2b0` (positive:
class-of-methods > test-module) · `e25bed2b` (positive: small-file edit
sizing) · plus the scan-crash fix already committed (`e749bcd`).

## Running tally (A.0 + A.1 + A.2 + A.3)

**Atlas shipped, no rework — 5 files:** `worlds/base.py` (v1),
`worlds/__init__.py`, `game.py` (world param), `worlds/silence/truth.py`,
`src/world_investigation.py`.

The pattern is now clear and stable:

| Atlas CAN | Atlas CANNOT |
|---|---|
| a self-contained new file — dataclass, constant table, or a whole class of short methods, up to ~60 lines, **given verbatim** | a new file that must `import` a project symbol and use it (stubs it locally — 3 repros) |
| a small, precise, unambiguous edit to a ≤~350-line file (`game.py` param) | any edit to a ~550+ line file (rejected or non-convergent) |
| | any multi-file bundle |
| | procedural logic (a test module) past ~45–50 lines |
| | a module-level constant rename |

All of Phase A's **architecture and wiring** has been Claude's. Atlas
has been a competent typist for the isolated, fully-specified leaf
files.

## Phase B (2026-08-29) — the roguelite inheritance loop

| # | ask | route | outcome | notes |
|---|---|---|---|---|
| 31 | `src/survivor_knowledge.py` — a small class (`has`/`learn`/`snapshot`/`restore`), self-contained | `atlas request --create --force` | **SHIPPED verbatim** ✓ (`b0fa752`) | 7th leaf file. Same shape as `world_investigation.py`. |
| 32 | `src/worlds/silence/lore.py` — `from src.worlds.base import SurvivorLore` + a 3-entry list | `atlas request --create --force` | **REJECTED** | The import-then-use shape again (`dbc93715`, 4th repro). Hand-written. |
| 33–40 | the campaign/survivor profile split (`persistence_mixin` 570 ln), the death lifecycle (`cli.py` mid-loop + `tui.py`), `SurvivorLore` dataclass, all 3 lore triggers + effects (`escape.py` 940 ln, `mystery_mixin` 700, `ui_mixin` 900), surfacing, ~30 tests | not routed | **HAND** | all large-file edits / cross-module / mid-function restructure / procedural |

Net Phase B: **1 of ~12 files by Atlas** (`survivor_knowledge.py`).
Same story as Phase A — the leaf class, yes; the profile-format change,
the lifecycle restructure, the per-lore engine hooks, no.

## Phase C (2026-08-29) — geography (C.1 + C.2 + C.4)

| # | ask | route | outcome |
|---|---|---|---|
| 41 | `src/worldgen/reachable.py` — pure BFS + `shortest_path`, ~45 lines | `atlas request --create --force` | **SHIPPED verbatim** ✓ (9th leaf file) |
| 42 | `src/worldgen/graph.py` — `from src.worldgen.reachable import …` + `MapGraph` class | `atlas request --create --force` | **REJECTED** (import-then-use + length; 5th repro) |
| 43+ | `worldgen/generator.py` (330-line verbatim move), the `generate_map` rewrite (258→55 lines) + 10 helper deletions, the `MapGraph` wiring, the structural suite | not routed | **HAND** — large-file / multi-file / mechanical-move |

| 44 | C.3: `MapGenerator._grow_valley_mask` (irregular-valley v2), `tools/geo_compare.py` (v1-vs-v2 distribution harness), the `mapgen=` plumbing, v2 structural tests | not routed | **HAND** — engine wiring + a generation algorithm + a metrics harness; all past the walls |

Net Phase C: **1 of ~9 files by Atlas** (`reachable.py`). C.3's
irregular-valley experiment (reversible, behind `mapgen="v1"|"v2"`) is
hand-written and awaits the owner's human feel-test.

## Phase C.3.1 + post-experiment fixes (2026-08-29) — feel-test prep

Three hand-written changes while getting the C.3 build ready for the
owner's five-expedition feel-test. None routed to Atlas.

| # | ask | route | outcome |
|---|---|---|---|
| 45 | C.3.1 — guarantee a mystery on v2 maps (regenerate the base map until `build_mystery` succeeds); `world_mixin.generate_map()` retry loop, v2 only | not routed | **HAND** — edit inside `generate_map` (720-line file, mid-function control flow); known edit wall |
| 46 | auto-write the play log by default + carry one transcript across expeditions | not routed | **HAND** — 3-file change (`apocrysis.py`, `cli.py` loop, `tui.py` post-win rebuild); multi-file + large-file |
| 47 | sanitise the survivor name on entry (`clean_display_name`) — stray `\`/`[` corrupted the Rich HUD, the play log and the profile slug; + `rich.markup.escape` in the HUD; + `hardcore` flag read through `_profile_flat` | not routed | **HAND** — new helper is ~10 lines and self-contained (Atlas-shaped), but it ships with edits to `cli.py`, `tui.py` and a test file; routing just the helper would strand the wiring |

Net C.3.1: **0 of 4 files by Atlas.** #47's helper is the only
Atlas-sized piece and it couldn't stand alone.

## Phase C.3.2 (2026-08-29) — navigation affordances

| # | ask | route | outcome |
|---|---|---|---|
| 48 | `src/nav.py` — `bearing()` + `heading_is_honest()`, ~72 lines, pure, no imports; + `test_nav.py` (11 tests) | not routed | **HAND** — ~72 lines is just over the reliable line, and `heading_is_honest` is real branching logic (axis-set contradiction test) not a data literal or a dataclass; the paired test file is procedural. A borderline call — could have been *attempted* — but the index-staleness risk plus the logic density made hand-writing the safer path for a load-bearing helper. |
| 49 | C.3.2 piece 0: `tui.py` `_objective_steps` — make the route heading graph-honest (~15-line change: extract `_route_heading`, delegate `heading()` to it, 2 module imports) | `atlas request --file src/tui.py` | **REJECTED-UNPARSEABLE** (3 attempts, no parseable patch) — the whole-file-load ceiling, exactly as predicted (`tui.py` ~980 lines). Note it did *not* hit `exceed_context_size_error` this time (post scan-fix), it just produced nothing parseable 3×. Filed `atlas-self` `9ecc7f2b`. Hand-written + `test_route_heading.py` (5 tests). |

Net C.3.2 so far: **0 of 2.** The recurring wall: every non-trivial
Apocrysis file that matters (`tui.py`, `escape.py`, `world_mixin.py`,
`game.py`, `ui_mixin.py`, `mystery_mixin.py`) is past the size where
Atlas can load it to edit, and the edits that land are cross-file.

## Cumulative (Phase A + B + C) — Atlas shipped 9 of ~70 files touched

9 self-contained new leaf files; every architecture / large-file /
multi-file / cross-import / mechanical-move change hand-written.

**The stable finding across three full phases:** Atlas (32B local coder) can
type a fully-specified, self-contained file up to ~60 lines, or make a
small unambiguous edit to a file under ~350 lines. It cannot do
architecture, multi-file changes, large-file edits, cross-module-import
new files, mid-function restructures, or procedural test modules.
Every design decision and every load-bearing change across both phases
has been Claude's.

## Running tally after A.0 + A.1 + A.2

**Atlas shipped, no rework:** `worlds/base.py` (v1), `worlds/__init__.py`,
`game.py` world param, `worlds/silence/truth.py` — **4 files**, all
either a small self-contained new file or a small precise edit to a
mid-size file.

**Everything else hand-written** — every large-file edit, every
multi-file change, every new file needing a cross-module import, every
piece of procedural logic over ~45 lines, and the `CAMPAIGN_LENGTH`
rename. ~15 files.

The capability gained since v4 is real but narrow: *small, local,
self-contained*. The architectural work of Phase A has been Claude's.

## Original blocker writeup (for the record)

## BLOCKER (2026-08-29) — `atlas scan` is broken, index is a week stale

`atlas scan` (and `atlas --json scan`) crash every time:

```
Atlas hit an unexpected error: cannot access local variable
'RepositoryScanner' where it is not associated with a value
```

`atlas doctor` reports all-green regardless. The Engineering
Intelligence store on disk is from **2026-08-23** (`file_map.json`
2026-08-18) — it predates the entire overnight build. Consequences:

- **`atlas rename` is unusable** — `no Definition named 'CAMPAIGN_LENGTH'
  in the indexed store` (the symbol isn't in the stale index).
- **`atlas request` scoping is blind** — it can't see current structure,
  so it can't reliably target the right file (see attempt 1).
- **The stale-index data-loss mode (memory `atlas_stale_index_dataloss`)
  is live and un-mitigable** — a proposal that diffs against the Aug-23
  index would revert three weeks of work. Only mitigation available:
  work on a committed clean tree so a revert = last commit, and reject
  any diff whose context lines don't match the working tree.

Until `atlas scan` is fixed (it's a bug in the Atlas CLI on the `zork`
branch), Atlas cannot safely author changes on this repo. Filing a
fix-Atlas todo in the `atlas-self` workspace.

## Log

| # | date | ask | route | workflow | outcome | notes |
|---|---|---|---|---|---|---|
| 1 | 08-29 | vocab rename pt.1 — rename `CAMPAIGN_LENGTH` across ~10 files | `atlas todo do 077a94f1` (list added with `--file docs/PHASE_A_TODO.md`) | a650f393 | **REJECTED-SCOPE** | `--file` on `todo add` pins every item's target to that one file. Atlas "did" the rename by string-replacing the constant name *inside the todo doc's own prose*, producing "rename `EXPEDITIONS_PER_CAMPAIGN` to `EXPEDITIONS_PER_CAMPAIGN`". Confidence **1.0**, all 8 safety checks green. Classic confidence-vs-scope failure. My config error (wrong `--file` semantics) + Atlas's — it should not have accepted a target that can't contain the change. |
| 2 | 08-29 | same rename, scoped to just `src/constants.py` | `atlas request --file src/constants.py` | 700934ba | **REJECTED (correct diff, un-approvable)** | Diff was exactly right and minimal — `CAMPAIGN_LENGTH` → `EXPEDITIONS_PER_CAMPAIGN` on the definition line, comment kept. But approving one file alone breaks ~10 importers → both suites fail → Atlas's own verify gate would roll it back. Confirms the rename must be atomic; Atlas's one-file-at-a-time model can't do atomic multi-file. |
| 3 | 08-29 | same rename via the purpose-built symbol tool | `atlas rename CAMPAIGN_LENGTH EXPEDITIONS_PER_CAMPAIGN` (dry-run) | — | **BLOCKED** | `no Definition named 'CAMPAIGN_LENGTH' in the indexed store`. First thought stale index; see #4. |
| 3.5 | 08-29 | unblock the tooling | fixed `atlas scan` in Atlas itself (`zork`), reran it | — | **FIXED** | scan crashed on an unbound `RepositoryScanner`; one-line local re-import. Index rebuilt 45 KB → 790 KB. Not a capability of Atlas-on-apocrysis, but it's what stood between here and one. |
| 4 | 08-29 | retry #3 with a fresh index | `atlas rename ... --run-tests` | — | **BLOCKED (tool limitation)** | Still `no Definition named 'CAMPAIGN_LENGTH'`. `atlas rename` indexes callables, not `NAME = value` constants. No Atlas path to an atomic multi-file constant rename. Filed `atlas-self` `1ba1bf47`. |

### Takeaway so far

The v4 baseline finding still stands, and the cause is now precise:
**Atlas's authoring on this repo is gated by the Engineering
Intelligence index, and that index is stale and un-refreshable because
`atlas scan` has a bug.** The 32B coder model produced a *correct*
minimal diff in attempt 2 — the model is not the bottleneck this time.
The tooling around it is.

### Outcome vocabulary

- **SHIPPED** — proposal approved, tests green, committed as-is.
- **SHIPPED+FIXUP** — approved but needed a small hand follow-up.
- **REJECTED-UNPARSEABLE** — no parseable diff produced.
- **REJECTED-SCOPE** — diff touched files / regions outside the ask.
- **REJECTED-STALE** — diff was against a stale index; would have
  reverted real work.
- **REJECTED-WRONG** — parseable, in scope, but incorrect; tests failed
  or logic was wrong.
- **HAND** — not routed to Atlas (too large / known-out-of-reach), or
  Atlas failed twice and Claude wrote it.
