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
| 3 | 0 | 0 (blocked before hand-write) | 0 |

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
