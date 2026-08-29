# Phase A — complete (freeze / checkpoint)

Tag: `v5-phase-a-complete`. 215 tests + 100 subtests green from a clean
tree. **The Phase A spine is frozen** — do not modify it unless a bug
appears. Phase B builds on it; it does not rework it.

## What Phase A established

The player loop:

```
WORLD  (worlds/silence/, passed into the engine)
   │
WORLD FACTS  (worlds/silence/truth.py - authored WorldFact DAG, CH1+CH2)
   │
INVESTIGATION STATE  (world_investigation.py - per-fact KNOWN/SUSPECTED/UNKNOWN)
   │
NEXT TARGET  (WorldInvestigation.next_target() - first UNKNOWN whose needs are met)
   │
MYSTERY  (escape.build_mystery(target_fact=...) - DiscoveryTemplate picks the mechanism)
   │
DISCOVERY  (the player solves the escape mystery by its own evidence)
   │
MILESTONE  (if the fact is milestone=True: "A PIECE FALLS INTO PLACE")
   │
PERSISTENT KNOWLEDGE  (profile round-trip - survives death)
   │
NEXT EXPEDITION  (a new survivor, the investigation stands, next_target advances)
```

## The load-bearing invariants (do not break these)

1. **World investigation is campaign-level knowledge, not
   survivor-level knowledge.** A survivor dies; their understanding of
   the world does not. `WorldInvestigation` state lives in the profile,
   never the expedition save. Player level / gear / health / current
   map are survivor-level and reset on death.

2. **`WorldFact` is authored truth; it is not `knowledge.Fact`.**
   Separate classes, separate jobs — "what is true" vs "what the player
   has evidenced". They meet only through `DiscoveryTemplate`, never by
   inheritance.

3. **`WorldFact.needs` is declarative.** It means "these truths
   logically support this truth" — *not* "the player must have solved
   these first". `WorldInvestigation` interprets the DAG; the facts
   know nothing about gameplay.

4. **The `WorldFact` statement is never injected into a mystery.** A
   `DiscoveryTemplate` routes a fact to a mechanism; the mystery is
   still solved by its own evidence. `Mystery.world_fact_id` is a tag,
   read by nothing during the build. (Test:
   `test_worldfact_statement_is_never_injected`.)

5. **No component re-derives the DAG rules.** UI, `campaign.py`, and
   the mystery scheduler ask `WorldInvestigation`. There is no second
   "current investigation fact" state — `next_target()` is the answer.

6. **The `World` boundary is data-only.** `worlds/*` imports nothing
   from `src.mixins` / `src.game` (test:
   `test_world_layer_has_no_engine_imports`). The engine reads
   `game.world`; a different `World` changes rendered behaviour with no
   engine change (test: `TestDummyWorldActuallyRenders`).

7. **No schema vocabulary reaches the player.** Never `disappearance`,
   `F_CLOSED`, `chapter=`, `thread`, `milestone=`. The player sees
   thread *titles* (`world.prose["thread_titles"]`) and fact
   *statements* only.

8. **The frozen balance stays frozen.** Combat / hunger-thirst /
   encounter / loot / map growth are untouched by all of Phase A.

## As-built notes (deviations / fixes worth knowing)

- **`w` is west-movement**, so the investigation screen is `wi` /
  `investigation`, not `w` (the roadmap §8's `w` predates that clash).
- **`MechanismFamily` was never built.** A.2 found the minimal
  `target_fact` path doesn't need it; A.4's variety-vs-targeting fix is
  one `if` in `build_mystery`, not a strategy object. If a later phase
  needs it, that's where it goes.
- **`apply_profile` ordering fix (A.5):** `generate_map()` targets
  `next_target()` inside `__init__`, which runs *before* the caller's
  `apply_profile()`. So `cli.py` and `tui.py` now seed
  `Apocrysis._world_investigation` from the profile *before*
  constructing — same pattern already used for `expeditions_completed`.
  Without this, a returning survivor's first expedition mis-targets
  `DIS_FEW_REMAINS`.
- **`_used_mechanisms` has the same latent ordering quirk** (read in
  `__init__`, restored by `apply_profile`) but its consequence is
  cosmetic (one possible mechanism repeat on reload), so it was left
  alone. Noted here in case it ever matters.
- **Encounter extraction (A.0.1) is parked** — `_select_zombie_for_
  encounter` tangles algorithm + roster + weights; not a literal lift;
  the seam works without it.

## Atlas capability baseline (Phase A)

See `ATLAS_CAPABILITY_LOG.md` for the full log. Summary: Atlas shipped
**6 of ~40 files** — 4 self-contained new leaf files + 2 small edits to
small files. Everything architectural, every large-file edit, every
multi-file change, every cross-import module, every test file, and the
one rename were hand-written by Claude. Every architectural decision
was Claude's.

**Nine `atlas-self` capability todos** filed as the baseline for future
Atlas work: `dbc93715`, `f7ee975b`, `c4b89284`, `1ba1bf47`, `89efb2fc`,
`434396fb`, `9fd6b2b0`, `e25bed2b`, `7762e330`. One Atlas bug fixed and
committed to `zork` this session: `e749bcd` (`atlas scan` crash).

## Doc status

| doc | status |
|---|---|
| `APOCRYSIS_ROADMAP.md` | live — the plan |
| `PHASE_A_DECISIONS.md` | locked |
| `PHASE_A0_SEAM.md` … `PHASE_A5_COHERENCE.md` | as-built, historical record of each phase |
| `PHASE_A_TODO.md` | **superseded** by the per-phase docs above |
| `ATLAS_CAPABILITY_LOG.md` | live — carries forward into Phase B |
| `SESSION_HANDOFF.md` | live — current state |

## Next

Phase B — the roguelite inheritance loop. *Not* Phase C (geography
rewrite). *Not* the native modal investigation screen (A.5's strip is
enough to prove the concept). Spec to be written and reviewed before
implementation.
