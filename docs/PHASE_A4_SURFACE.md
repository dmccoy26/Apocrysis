# Phase A.4 — surfacing the investigation

Authored before implementation. Builds on A.1/A.2/A.3.

## The responsibility split (the architecture's spine now)

| owns | responsibility |
|---|---|
| `WorldFact` (truth.py) | what is true |
| `WorldInvestigation` | what the player has discovered about it, and `next_target()` |
| **UI** (ui_mixin/tui) | how that state is shown — asks `WorldInvestigation`, never re-derives the DAG |
| **campaign.py** | how investigation progress reframes the run — asks `WorldInvestigation` |
| **mystery system** (escape.py) | how one investigation opportunity is generated |

**No component reconstructs the DAG rules.** No second "current fact"
state — `next_target()` is the answer.

## A.4.1 — the World Investigation screen

- new top-level action `w` (and `investigation`) from the `>` prompt,
  free in `_free` like `m`/`i`/`st`
- `ui_mixin.world_investigation_screen()` renders, per thread:
  - a title + question (from `game.world.prose["thread_titles"]` —
    world content, in the seam; **never** the raw `thread` id)
  - a progress bar / `known/total`
  - each fact: `✓ <statement>` if KNOWN, `· <statement>` if SUSPECTED,
    `? <statement>` if UNKNOWN
  - `milestones_known()` count as a headline number
- classic-mode text version (this IS classic — `io.say` lines); the TUI
  gets the same via `io.say` for now (a native panel is later)
- **no schema vocab leak**: the player sees thread *titles* and fact
  *statements* only, never `disappearance` / `F_CLOSED` / `chapter`
- snapshot-style test on the rendered string

`world.prose["thread_titles"]` (add to `worlds/silence/world.py`):
```python
"thread_titles": {
    "disappearance": ("THE SILENCE", "Where did the people go?"),
    "dead":          ("THE INFECTED", "What are they, and where did they start?"),
    "response":      ("THE RESPONSE", "Who ordered it?"),   # no CH1/CH2 facts yet
},
```

## A.4.2 — investigation-driven mystery targeting

`world_mixin.generate_map()` currently: `self.mystery = build_mystery(self)`.

Change to:
```python
self.mystery = build_mystery(self, target_fact=self.world_investigation.next_target())
```

`next_target()` returns `None` once every CH1/CH2 fact is KNOWN →
`build_mystery` takes the ordinary random path (already handled in A.2).
So an "ordinary mystery" still happens legitimately — when the authored
DAG is exhausted, or (future) when a phase wants a non-targeted run.

**Verify before accepting** (a sim, in the test):
- run ~6 expeditions, marking each target KNOWN on "success"
- assert the targets come in DAG order: `DIS_FEW_REMAINS`,
  `DIS_MOVED_TOGETHER`, `DIS_ROUTES_PREPARED`, `DIS_ORGANISED`, then a
  CH2 root
- assert **no back-to-back identical story family** across the run
  (the invariant the roadmap protects)

### The variety-vs-targeting tension (must be handled, not ignored)

`build_mystery`'s `target_fact` path does `rng.choice(routes).mechanism`
— it bypasses `choose_mechanism`'s A/B/C anti-repetition. Consecutive
targets can collide: in `discovery.py` today `DIS_ROUTES_PREPARED` and
`DIS_ORGANISED` both bind only to `evac_corridor` → back-to-back same
mechanism **and** family.

Fix, minimal:
1. give the colliding facts a **second** `DiscoveryTemplate` route
   (a different mechanism of a plausible-enough theme), and
2. in `build_mystery`'s target branch, pick the route whose mechanism's
   family is **not** `game.__class__._last_family` when such a route
   exists (fall back to `rng.choice` otherwise). One `if`, no
   `MechanismFamily`.

`discovery.py` after: every fact has ≥1 route; the four that would
collide in authored order get a 2nd.

## A.4.3 — chapter intros keyed to progress

`campaign.chapter_intro(expeditions_completed, milestones_known=0)`:
- if `milestones_known > 0`: index `_CHAPTERS` by a
  milestone→line mapping (3 milestones in CH1/CH2 → the first few
  lines), so replaying after a death doesn't reset the framing
- else: fall back to `expeditions_completed` (today's behaviour)
- `cli.py` passes `len(player.world_investigation.milestones_known())`
- **no save-format change**; `chapter_intro` stays pure

## A.4.4 — milestone banner

In `mystery_try_escape`, where A.3 already calls `mark_known`:
```python
fid = m.world_fact_id
was_known = self.world_investigation.is_known(fid)
self.world_investigation.mark_known(fid)
type(self)._world_investigation = self.world_investigation.snapshot()["status"]
if not was_known:
    fact = <the WorldFact for fid>
    if fact and fact.milestone:
        self.announce_event(<milestone title>, <one line>, kind="milestone")
```
- `announce_event` gains a `kind="milestone"` branch — visually
  distinct from `"discovery"` (bigger rule, its own label e.g.
  `A PIECE FALLS INTO PLACE`)
- fires **exactly once**, on the `not KNOWN → KNOWN` transition of a
  `milestone=True` fact
- ordinary `NEW DISCOVERY` announcements are untouched
- classic + TUI both go through `announce_event` → both covered
- the milestone's player-facing line: the fact's own `statement`
  (that's the authored player-facing text) — **not** a schema string

`WorldInvestigation` needs a tiny read helper: `fact(fid)` returning the
`WorldFact` or None (so the mixin doesn't reach into `_facts`).

## Guardrails (Atlas)

No `MechanismFamily`, no `knowledge.py` change, no DB, no native TUI
panel, no encounter extraction (A.0.1 stays parked), no new persistent
state (`next_target()` + the profile status map are enough). Route each
piece to Atlas first; on the known walls (large files: `ui_mixin` 843,
`world_mixin` 1130, `mystery_mixin` 664; multi-file; cross-import) log
and hand-write. `campaign.py` (55 lines) and `discovery.py` are the
realistic Atlas candidates.

## Order

1. A.4.1 screen  2. A.4.2 targeting + variety fix  3. A.4.3 chapter
intros  4. A.4.4 milestone banner. Both suites green after each.
