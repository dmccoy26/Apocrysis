# Phase A.5 — coherence / presentation pass

A **small** pass. Make the Phase A spine *feel* intentional before
Phase B. No new architecture. No `MechanismFamily`. No A.0.1.

## Exit condition

> A player can complete an expedition, understand what they learned,
> see that knowledge persist after death, inspect their accumulated
> investigation, and immediately understand what the next expedition is
> about — without ever seeing engine/schema terminology.

## A.5.1 — investigation is present in the interface, not just on demand

The TUI already parses `io.say` ANSI into Rich styling, so the `wi`
detail view is not raw-escape garbage — it's styled text in the log.
The real gap: investigation progress isn't *visible* unless you ask.

**Add a compact investigation strip to the OBJECTIVES panel**
(`tui._status_block`, a pure function) — always visible:

```
THE APOCRYSIS   ◆ 2
  THE SILENCE    ███░  2/4
  THE INFECTED   ░░░░  0/5
```

- milestone count + per-thread bar + `known/total`
- thread *titles* only (`world.prose["thread_titles"]`), never ids
- sits above the WARNINGS block; omitted entirely if the investigation
  is empty (no `world_facts`) so nothing changes for a bare test world

`wi` stays the full detail view. A full modal takeover is **not** in
A.5 — noted as optional further polish.

## A.5.2 — the expedition-end retrospective

`_render_end_screen` currently prints a stats box on win **and** death.
Add, after the box, a short **what-changed** section — describing the
*transition this expedition caused*, not re-listing the whole screen:

```
EXPEDITION ENDED — Jess did not make it back.        (death)
EXPEDITION 4 — you got clear.                        (win)

  THE SILENCE   2 / 4 understood
    ✓ you learned: the exodus was organised          (only if won + milestone/fact)

  The next survivor can look into:
    the evacuation had prepared routes                (next_target()'s statement)
```

- track `self._expedition_learned` — fids marked KNOWN this run (set in
  the resolution hook; empty on a death or an untagged run)
- "the next survivor can look into" = `world_investigation.next_target()`
  → that fact's `statement` (the authored player-facing text)
- if the investigation is empty / exhausted, the section is omitted
- no schema strings

## A.5.3 — one coherent vocabulary, three tiers

The player already meets three beats. Make them read as a hierarchy,
understated, in the right order when solving a milestone mystery:

```
  (during play)   NEW DISCOVERY — <fact statement>          cyan, "*"
  (on escape)     MYSTERY SOLVED — <mechanism name>          green, "◆"
  (just after)    A PIECE FALLS INTO PLACE — <milestone>     yellow, "◆◆"
```

Changes:
- `mystery_try_escape`: the escape moment becomes an
  `announce_event(<mechanism name>, kind="solved")` beat **before** the
  existing "You found the way out…" prose (keep the prose — it's the
  texture; the banner is the signpost)
- the A.4.4 milestone banner moves to fire **after** that prose, so the
  order is solved → texture → "and a piece falls into place"
- `announce_event` gains `kind="solved"` (green, `◆`, label
  `MYSTERY SOLVED`)
- `NEW DISCOVERY` wording/behaviour unchanged

## A.5.4 — one end-to-end lifecycle test

`test_world_investigation.py` — a single test walking the whole feature:

```
fresh campaign, investigation empty
  → expedition 1 targets DIS_FEW_REMAINS
  → solve it            → DIS_FEW_REMAINS KNOWN, no milestone banner
  → expedition 2 targets DIS_MOVED_TOGETHER   (DAG advanced)
  → solve it
  → expedition 3 targets DIS_ROUTES_PREPARED
  → solve it
  → expedition 4 targets DIS_ORGANISED
  → solve it           → milestone banner fires once
  → chapter_intro framing index is >= the milestone count
  → DEATH (new Apocrysis, apply the profile)
  → all four facts still KNOWN
  → chapter_intro framing does NOT regress
  → next expedition targets a CH2 root, not a re-run of CH1
```

## Routing

`tui._status_block` edit (pure function, but `tui.py` is 900 lines) —
route once, expect the wall, hand-write. `_render_end_screen` (ui_mixin
843 ln) — hand-write. `mystery_mixin` (670 ln) — hand-write.
`announce_event` `kind="solved"` — hand-write. The lifecycle test —
hand-write. Log each; append to `atlas-self`.

## Not in A.5

Native modal investigation screen · `MechanismFamily` · A.0.1 encounters
· any `knowledge.py` change · Phase B survivor loop.

---

## As built (2026-08-29) — commits `fc66818` (design) / `af05903` (impl)

All four items landed as specced. 215 tests + 100 subtests green.

- **A.5.1** — `tui._investigation_strip(p)` (new pure function) folded
  into `_status_block`. Milestone count + per-thread 4-char bar +
  `known/total`. Omitted entirely when `world.world_facts` is empty.
- **A.5.2** — `ui_mixin._render_investigation_retrospective(won)`,
  called at the end of `_render_end_screen`. Win → `WHAT YOU LEARNED`
  (from `self._expedition_learned`, set in the resolution hook) +
  thread progress. Death → `THE INVESTIGATION STANDS`. Both →
  `THE NEXT SURVIVOR CAN LOOK INTO` = `next_target()`'s `statement`.
- **A.5.3** — `announce_event` gained `kind="solved"` (green `◆`,
  `MYSTERY SOLVED —`). `mystery_try_escape` now fires, in order:
  `MYSTERY SOLVED` banner → the "You found the way out …" prose →
  (if milestone) `A PIECE FALLS INTO PLACE`. The milestone announcement
  was moved after the prose via a deferred `_milestone_line` local.
- **A.5.4** — `TestFullLifecycle.test_campaign_lifecycle_through_a_death`
  in `test_world_investigation.py`.

### The ordering fix (found by A.5.4, not in the original spec)

`generate_map()` calls `build_mystery(target_fact=next_target())` from
inside `Apocrysis.__init__`. The caller applies the profile *after*
construction (`cli.py` line ~103, `tui.py` line ~679), so on a fresh
process a returning survivor's `world_investigation` was still empty
when the first mystery was targeted → it always picked
`DIS_FEW_REMAINS` regardless of campaign progress.

**Fix:** `cli.py` and `tui.py` set `Apocrysis._world_investigation =
profile["world_investigation"]` *before* `Apocrysis(...)`. `apply_profile`
still restores it afterward (idempotent). `_used_mechanisms` has the
same shape of quirk but only a cosmetic consequence, so it was left as
is. Recorded in `PHASE_A_COMPLETE.md` § As-built.
