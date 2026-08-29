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

| attempts | Atlas shipped | Claude hand-wrote after Atlas failed | Atlas-only (no rework) |
|---|---|---|---|
| 9 | 2 (`base.py`, `worlds/__init__.py`) | 5 (rename ×2, `world.py`, seam bundle, constants shim) | 2 |

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
