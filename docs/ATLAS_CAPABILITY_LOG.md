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
| 0 | 0 | 0 | 0 |

## Log

| # | date | todo / ask | files | workflow id | model | outcome | notes |
|---|---|---|---|---|---|---|---|
| — | — | _(first entry lands when the vocab-rename todo is submitted)_ | | | | | |

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
