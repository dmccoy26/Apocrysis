# Structure assessment — do we need to restructure? (2026-08-29)

Asked at the start of v5, then again with "look at the entire codebase."
This version is a **code-level read**, not a file-size scan.

## Verdict

**No wholesale restructure.** The architecture is sound and the data
model is genuinely good. There are **three targeted refactors**, and all
three should happen *inside* the roadmap phase that already touches that
code — not as a preemptive pass:

| refactor | do it as | why not now |
|---|---|---|
| `worlds/` seam — world-1 content out of the engine | **Phase A step 0** (already planned) | this is the restructure that matters; it's already the plan |
| a `MechanismFamily` abstraction — consolidate the per-family `spec.get(...)` branching | **Phase A step 2** (`DiscoveryTemplate` work) | premature until `target_fact` shows exactly which seams it needs |
| split `generate_map()` into `worldgen/` | **Phase C step 0** (map-v2) | Phase C rewrites the geography half anyway; splitting then rewriting is wasted motion |

Everything else is cleanup, not restructure (§ Cleanup below).

---

## What the code actually looks like

### The data model — `knowledge.py` (215 lines) — keep as-is, it's the good part

Pure data + pure derivation. No I/O, no `src/` imports. `Fact` /
`Evidence` / `Deduction` / `Hypothesis`; states are **derived, never
stored** (`facts_known()`, `hypothesis_state()` recompute every call).
Clean serialization with a deliberate split — `to_dict`/`from_dict`
(full catalogue, for the verbatim resume save) vs
`progress_snapshot`/`restore_progress` (player progress only, because
the catalogue regenerates with the map).

This is exactly the model the roadmap wants to promote to world scope
(§3.2), and **it's already the right shape**:

- `Deduction(needs=[A, B])` already supports corroboration — §3.2's
  "two independent records that agree" needs no new type, just facts
  that use it.
- The **one** change §3.2 forces: `self.hypothesis` (singular) →
  a collection of competing hypotheses with support/confidence. That's
  a contained change to one class.

`worlds/silence/truth.py`'s `WorldFact` should be a **sibling** of these
classes, not a subclass — same file family, same derivation style.

### The generator — `escape.py` (917 lines) — data is clean, one function is at its limit

- `MECHANISMS` is **pure data** — a dict of 10 mechanism specs. Adding a
  scenario is a dict entry (this is why the overnight build could add 5).
- `Mystery` has clean `to_dict`/`from_dict` and a real **`validate()`**
  generation-time invariant gate (every load-bearing fact needs ≥2
  evidence routes; hypothesis must be confirmable; classification must
  come from the closed vocabularies). Keep this — Phase A/C make
  mysteries harder to prove solvable and this is the check that keeps up
  (until `mystery_solver.py`, roadmap §7).
- `choose_mechanism` / `story_signature` — isolated, pure, testable.
  The variety rules (A/B/C) live here cleanly.
- **`build_mystery()` is 300 lines and interleaves 5 family
  special-cases** — `_transport` (`item2`), `_deadline`
  (`deadline_turns`), `_reveal` (`reveals_route`), `power_role`,
  `controls`. Each new family threads another `if spec.get(...)` through
  site assignment **and** evidence construction **and** validation. It's
  well-commented and it works, but it's the friction point for Phase A
  (`DiscoveryTemplate` + `target_fact` add a 6th axis) and Phase C
  (geography rewrite).

### The engine — the 9-mixin god-object — leave it

`Apocrysis(PersistenceMixin, CombatMixin, WorldMixin, ObjectivesMixin,
UIMixin, ActionsMixin, KnowledgeMixin, MysteryMixin, SliceMixin)`.
~60 `self.*` attributes set in one `__init__`; no enforced boundary
between mixins (any mixin reads/writes any attribute).

- It **is** a comprehension tax and it **is** why "Atlas can't touch a
  large method here."
- But the one boundary that mattered — I/O — is **already fully
  abstracted** (`self.io.say/ask`), TUI and console are cleanly
  swappable.
- Un-mixining it means touching every mixin's `self.<x>` access for zero
  player-facing or roadmap gain, against the **frozen balance**
  (combat / hunger-thirst / encounter / loot / map growth).
- **Don't.** The `worlds/` seam adds the *next* real boundary the right
  way — a passed-in object, not a mixin — and that's the pattern to
  extend later if the itch persists.

### `world_mixin.py` (1137 lines) — the one file that's genuinely overloaded

Six lifecycles in one mixin: (1) map generation — `generate_map()`
**278 lines**, (2) settlement generation, (3) zone tagging, (4)
reachability/pathfinding (`_bfs_reachable`, `_carve_path`,
`_ensure_reachable`, `_force_boundary_ring`), (5) zombie selection
(**frozen balance**), (6) per-turn runtime — `move_and_search()`
**~220 lines**, `find_loot()`.

Generation (1–4) and runtime (5–6) are different lifecycles and the
natural fault line. **Roadmap Phase C rewrites 1, 2, 4 and part of 6**
(connectivity-graph generator, irregular masks, `_carve_escape_pass`
rewrite, graph-native pacing). Split into `src/worldgen/` as **the first
commit of Phase C**; don't pull it forward.

### The per-family branching is spread across two files — this is the real smell

`spec.get('deadline_turns')` / `spec.get('controls')` /
`spec.get('power_role')` are checked ad-hoc in **both** `escape.py`
(`build_mystery`) **and** `mystery_mixin.py` (`_mystery_obstacle_ready`
and friends). There is no "mechanism family" object — a family is just a
convention about which dict keys are present.

A `MechanismFamily` strategy (`assign_sites`, `build_evidence`,
`obstacle_ready`, `on_resolve`) would consolidate ~5 scattered
conditionals into one place per family, and it's the natural home for
`DiscoveryTemplate` (Phase A step 2). **Do it there**, when the
`target_fact` path shows which methods the strategy actually needs —
not as a speculative refactor now.

### Persistence — `persistence_mixin.py` (555 lines) — clean, extend it don't touch it

Deliberate split: `save_game`/`load_game` (full playthrough snapshot for
exact resume) vs `save_profile`/`apply_profile` (identity + progression
that carries into a fresh map). The class-var + profile round-trip
pattern (`_used_mechanisms`, `_recent_signatures`, `last_family`) is the
**established way to add cross-expedition persistent state** — Phase A's
World Investigation slots straight into `save_profile`'s dict and an
`apply_profile` restore line. No structural change needed.

---

## Cleanup (not restructure) — safe, worth doing, needs your OK

1. **Delete the slice scaffolding** — `src/slice_dam_road.py` (307),
   `src/mixins/slice_mixin.py` (225), `tools/slice_playtest.py` (137),
   the `slice_mode`/`SliceMixin` hooks in `game.py` and `_apply_decay`.
   Memory + the code's own comments: "throwaway experimental
   scaffolding, not a game mode." It proved the knowledge-model shape
   (now in `knowledge.py`); it's done. ~700 lines of branching sitting
   in code Phase A edits. **Confirm nothing still runs it.**
2. **Split `test_apocrysis.py`** (1990 lines) → `test_combat.py`,
   `test_world.py`, `test_persistence.py`, `test_campaign.py`. Pure
   move; `pytest` proves equivalence. Every Phase A item adds tests —
   better into a focused file.
3. **`expeditions_completed` does four jobs** — map sizing, obstacle
   density, zombie-difficulty interpolation, campaign framing. The
   roadmap wants chapter / World-Investigation state to drive framing
   and (later) sizing. The Phase A vocab rename is the first cut; keep
   the storage name, add `chapter_for_expedition()`.

## Do NOT

- Un-mixin the `Apocrysis` class.
- Pre-split `world_mixin` / `build_mystery` ahead of the phase that
  rewrites them.
- Change `knowledge.py`'s shape beyond singular→plural hypothesis.
- Route any of this through Atlas — `ATLAS_CAPABILITY_LOG.md` shows it
  can't do multi-file structural work here yet.

## One-line answer

> The bones are good — `knowledge.py` especially. The structure is
> adequate for Phases A–B as-is. Three refactors are on the path
> (`worlds/` seam, `MechanismFamily`, `worldgen/` split); each belongs
> to a roadmap phase that already opens that file. No preemptive
> restructure.
