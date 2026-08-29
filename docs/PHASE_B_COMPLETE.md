# Phase B — complete (freeze / checkpoint)

Tag: `v5-phase-b-complete`. 240 tests + 100 subtests green from a clean
tree. Builds on the frozen Phase A spine; does not touch it. **Phase B
is now frozen too** — modify only for a bug.

## What Phase B established

> A survivor dies. The next one starts weak, with a new name — but
> knows what the last one figured out about the world, carries a
> concrete survival lesson, and is dropped at the depth the campaign
> reached. Dying costs the run, not the campaign.

```
                 CAMPAIGN  (one profile file's "campaign" record - survives every death)
                  ├── World Investigation      (Phase A)
                  ├── Survivor Knowledge       (learned SurvivorLore ids)
                  ├── expeditions_completed     = DEPTH, not survivor progress
                  ├── variety rings             (used_mechanisms / recent_*)
                  └── survivors_lost
                          │
   survivor dies ─────────┤ (non-hardcore)         hardcore death ─▶ delete everything
                          ▼
                 a fresh SURVIVOR  (the "survivor" record - replaced wholesale)
                  ├── new name (name pool, numbered on wrap)
                  ├── level 1, xp 0, starter stats + gear, full health
                  └── dropped at the campaign's depth
                          │
                          ▼
                 next expedition targets world_investigation.next_target()
```

## The invariants (all have tests)

1. **Death may replace the survivor record; it never reconstructs or
   mutates the campaign record.** (`test_campaign_record_is_byte_identical_across_the_death`)
2. **`expeditions_completed` is campaign depth, not survivor progress.**
   Die at depth N → heir at depth N, level 1.
   (`test_depth_is_not_survivor_progress`, `TestPhaseBExitCondition`)
3. **`SurvivorLore.effect` is doc / UI text only.** The engine reads
   exactly `survivor_knowledge.has(<id>)`. No `effect` vocabulary is
   parsed. (`test_effect_is_never_interpreted_by_the_engine`)
4. **Nothing in Survivor Knowledge changes stats / gear / xp / health /
   damage / durability / loot / encounter probabilities.** It only
   changes what information is surfaced and when.
   (`TestLegibilityNotPower` — 3 ids × identical-game diff)
5. **The game lifecycle, not `save_profile`, decides when a survivor is
   replaced.** `save_profile` only serialises;
   `Apocrysis.persist_new_survivor(...)` is the lifecycle op.

## The 3 shipped SurvivorLore ("The Cordon")

| id | learned by | effect (all legibility, not power) |
|---|---|---|
| `BLUE_SIGNS` | solving an `evac_corridor` mystery | the `route` site is map-marked from turn 1 of an `evac_corridor` expedition — you still walk to it |
| `COMMAND_FREQUENCY` | solving a `radio_tower` mystery | the broadcast-log evidence (`E_route_a`) surfaces on arrival instead of on `search` — one fewer search step in `radio_tower`, same site, same solve |
| `RESERVOIR_CONTROLS` | solving a `dam_valves` mystery | the control-room evidence **names** the governing control instead of "but which?" — control count and the open condition are unchanged; you still operate and revise |

Held for a later balance pass: `INFECTED_AND_NOISE`,
`CORRIDOR_CHECKPOINTS` (they cross into simulation rules / a mystery's
state machine). Hard cap 5.

Balance: `evac_corridor` 92% / `radio_tower` 89% / `dam_valves` 84% bot
survival — all in the frozen band. The bot navigates via `m.sites`
directly, so BLUE_SIGNS' map-marking has no bot effect; the other two
are text-only.

## As built (deviations / notes)

- **Profile file format changed** to `{"campaign": {...}, "survivor":
  {...}}`. `load_profile` normalises a legacy flat Phase-A profile into
  it by field name (`_CAMPAIGN_KEYS`). `apply_profile` flattens
  internally (`_profile_flat`) so its field restore is shape-agnostic.
  Existing persistence tests were updated to read the nested paths.
- **The profile file is now the *campaign's* identity**, keyed by the
  founder's name (`campaign_file` in `cli.py`). The survivor's display
  name (`player.name`) changes independently as survivors die.
- **`has_flashlight` is now survivor-level** — a death loses the
  flashlight (it's gear). Intentional; noted in case it surprises.
- **The TUI does not loop into new survivors** the way `cli.py` does
  (it runs one game per `app.run()`), but its `_save_or_delete_profile`
  now writes campaign + fresh survivor on a non-hardcore death, so the
  next launch inherits correctly.
- **`_used_mechanisms` / `prize_for_next_game`** still have the
  read-in-`__init__`-restored-after quirk (Phase A note) — untouched,
  cosmetic only.

## Atlas (Phase B)

1 of ~12 files (`survivor_knowledge.py`, verbatim). `lore.py` rejected
(import-then-use). Everything else — the profile split, the lifecycle,
the per-lore hooks, the tests — hand-written. `ATLAS_CAPABILITY_LOG.md`
has the cumulative tally (8 of ~55 files over Phases A+B, all leaf).
Filed `atlas-self` `46ee8a52`.

## Doc status

`PHASE_B_SPEC.md` (locked + as-built section) → `PHASE_B_COMPLETE.md`
(this). `PHASE_A_COMPLETE.md` unchanged and still authoritative for the
spine.

## Next

Phase C (map-v2 + `worldgen/` split) is the big geography rewrite —
`APOCRYSIS_ROADMAP.md` §5 / §9. Or A.0.1 (parked encounters), or a
native modal investigation screen, or optional-evidence / valley-file
(roadmap Phase B.3, deferred out of B). Spec to be written and reviewed
first, as always.
