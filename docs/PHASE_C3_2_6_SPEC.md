# C.3.2a-6 — Scaled Investigation Structure (experiment spec)

**Owner-set 2026-08-30, after Gate 8 was falsified.** This is the next
controlled experiment in the C.3.2a-5 line. **Measurement only — no
generator change ships, baseline stays byte-identical, stop at the
review gate.** Do **not** combine this with a survival-envelope change.

---

## 1. Why this experiment

Gate 8 (`SCALE_REPORT.md § Gate 8`) established a **fixed-content
ceiling**:

> Rearranging a *fixed* number of required story nodes inside a
> 5×-larger world — even with a relational escape-gap ceiling and a
> settlement density floor — restores viability only through campaign
> depth ~4–6. Past that, the world keeps growing while the required
> story structure stays constant, and the required circuit outgrows the
> survival budget no matter how the nodes are arranged.

C.3.2a-5 asked *"can the existing story occupy the larger world
better?"* Gate 8 answered *"only up to the point the fixed story runs
out."* C.3.2a-6 asks the next logical question:

> **What happens if the story itself grows with the world?**

## 2. The hypothesis

> **As playable geography grows, the required investigation acquires
> additional genuine story-bearing intermediate structure proportional
> to that growth — and this restores `ratio p90 < 1` at the supported
> depths *without* artificially shrinking the meaningful geography
> (i.e. without the "nicer shirt" / spawn-cluster failure).**

The experiment must distinguish two outcomes that look identical in the
headline ratio:

```
  more required nodes  →  more meaningful geography      (hypothesis holds)
  more required nodes  →  more checkpoints, same         (hypothesis fails —
                          wilderness problem + labels     "extra labels")
```

That distinction is exactly what Gate 8 earned the right to test:
`meaningful_fraction`, backtrack, and the node-density relationship are
the instruments that tell the two apart.

## 3. What a "genuine intermediate beat" is (define before building)

An inserted required site counts as a **genuine intermediate beat**
only if **all** of these hold. If a design choice here is ambiguous,
**stop and ask** rather than picking one.

1. **Load-bearing.** Removing it breaks the solve — it is on the
   required circuit, not optional. For the experiment this means: it
   withholds a piece of information the player needs to locate or act
   on a *later* required site (e.g. the obstacle's location, the
   `require` item's location, or which control is correct), so the
   circuit genuinely cannot skip it.
2. **On the corridor.** Placed along the `spawn → … → escape` run
   (reuse the pacing-invariant-3d placement `build_mystery` already
   does), between two existing beats — not off in a pocket that forces
   a there-and-back. Detour cost (extra tiles vs walking straight past)
   must stay low; **backtrack is a hard quality gate** (§6).
3. **Carries real content.** It resolves to an evidence fragment the
   knowledge model actually uses — not a bare "you must stand here"
   tile. For the *experiment* the fragment can be a stub
   (`E_beat_k`); the point is that the site occupies the same
   structural slot a real authored beat would.
4. **Spaced, not stacked.** Two inserted beats may not land within a
   small radius of each other or of an existing site — that is
   clustering, which is the failure mode, not the goal.

## 4. What to build (behind a flag, default off)

A single class-level config on `Apocrysis`, default `None`:

```
_lever_scaled_beats = None   # or a scaling-form id (see §5)
```

When set, `build_mystery` (or an `escape.py` helper it calls) inserts
`k` extra required sites as `beat_1 … beat_k`, where `k` comes from the
scaling form, placed per §3, added to `m.sites` and to the required set
the harness walks. Obstacle-ready / solve gating is extended so the
beats are genuinely required (§3.1). **Every other generator behaviour
is unchanged; with the flag `None` the output is byte-identical to
`main` (the C.1 golden fixture must pass).**

Retired / not in this experiment:

- `_lever_cap_town_dist` (lever 3 — falsified in the matrix).
- `_lever_bound_gap` targeting / the Gate 8 ceiling sweep — **not
  combined here.** (The escape gap keeps its current baseline carve.)
- Any further attempt to squeeze the existing fixed circuit.
- Any change to combat / hunger / thirst / loot / survivor power / map
  growth — all frozen.

## 5. The scaling forms to sweep

`k = f(map)` — compare several forms so the experiment produces
**evidence for the eventual generator rule**, not another hand-picked
constant. Report each; **do not pick one.**

| id | `k` (extra required beats) | rationale |
|---|---|---|
| `fixed@1`, `fixed@2` | constant 1 / 2 regardless of size | control — isolates "did *any* extra structure help" from "did *scaling* help" |
| `log` | `round(c · log2(map_size / 15))` | sub-linear, gentle |
| `sqrt` | `round(c · (√playable − √playable₀) / S)` | matches Gate 8's finding that **linear map dimension**, not area, is the travel-distance scale |
| `linear` | `round(c · (map_size − 15) / S)` | upper bound — structure grows as fast as the map's side |

`c` a small sweep (e.g. 1, 1.5, 2); `S` a normalising constant chosen
so `fixed` and the scaled forms are comparable at mid-depth. Cap `k` at
a sane ceiling (e.g. 4) so a 34² map doesn't get 12 beats.
`playable₀` / the depth-0 map is the reference.

The question is **not** "which formula wins". It is:

> **How much additional required structure is actually necessary to
> prevent the deep-world collapse — and does the necessary amount track
> map size linearly, sub-linearly, or not at all?**

## 6. Metrics (per form, per depth, 10 mechanisms rotated, ≥250 seeds/depth)

Reuse `tools/scale_report.py`. Carry forward every Gate 8 column, add
the node-density relationship:

- **`ratio p90`** = required-circuit p90 / `USABLE_BUDGET` (32) — the gate, `< 1`.
- **`meaningful_fraction` p50** — journey share near story sites vs wilderness (Gate 8 metric). **Must recover toward the depth-0 value.**
- **`required_story_nodes`** (raw count) and **`nodes / √playable`** — report the raw relationship; **do not turn it into a target yet.**
- **`dens` / `dst/1k`** — density diagnostics. A form that passes the gate while `dens` keeps falling has **not** passed (the beats shrank the footprint instead of filling the world).
- **backtrack p50 / p90** — **hard quality gate.** Any rise above ~1.5× baseline means the beats are forcing retraces = "checkpoints", not geography. Fail that form.
- **`spawn→require` p90** and the per-leg breakdown — carried from Gate 8 to catch a circuit that just re-routes around the new beats.
- **`infeasible` %** — must stay 0. `> 0` = the beats made a required node unreachable; report and drop that form.

Depths `0,1,2,3,4,6,9,12`. Depth range is **not** redefined —
supported = 0–12 for this experiment (see §8).

## 7. Acceptance — the hypothesis is supported iff

A scaling form (ideally `log` / `sqrt` / `linear`, not `fixed`)
achieves **all** of:

1. `ratio p90 < 1` at every supported depth (0–12).
2. `meaningful_fraction` p50 at depths 9–12 recovers to within ~0.15 of
   the depth-0 baseline value (same bar as Gate 8 §5.2).
3. `dens` and `dst/1k` at depths 9–12 **≥ baseline** — the world gained
   content, it didn't get a tighter mystery.
4. backtrack p90 ≤ ~1.5× baseline at every depth.
5. `infeasible` = 0 %.
6. v1 byte-identity with the flag off.
7. **The `fixed` controls do *not* also pass** — if `fixed@2` passes
   the gate as well as `sqrt`, then "scaling" is not what did the work;
   a constant number of extra beats did, and the rule is "+N beats",
   not "+f(size) beats". That is still a useful result — report it
   plainly.

## 8. Falsification — and what each failure points to

- **No form gets `ratio p90 < 1` through depth 12 without
  `infeasible > 0` or a backtrack blow-up** → structural growth alone
  is not enough; the **survival envelope itself** is the wall at deep
  depth. → go to the *other* post-Gate-8 hypothesis: **formally bound
  supported depth to 0–N** (data suggests N ≈ 5–6) and make deep
  expeditions a deliberately different format (authored escalation /
  inheritance-balanced / a distinct late-game mode). That is a
  **campaign-design decision made on evidence**, not a rescue of this
  experiment.
- **A form passes the gate but `meaningful_fraction` doesn't recover /
  `dens` keeps falling / backtrack rises** → "more checkpoints, same
  geography problem, now with extra labels." The beats are not genuine
  intermediate structure. → revisit §3's definition, or conclude that
  *procedurally-generated* beats can't be made genuine and the deep
  campaign needs *authored* structure.
- **Only `fixed` passes, not the scaled forms** → the fix is "+N
  required beats", independent of size. Simpler rule; report it.
- **`linear` passes but `log`/`sqrt` don't** → structure must grow as
  fast as the map's side. Expensive but clear.

## 9. Frozen sequence (owner)

```
Gate 8 falsified
      │
      ▼
C.3.2a-6 spec (this doc)  ──►  owner review
      │
      ▼
build _lever_scaled_beats + the beat construct (§3, §4), flag off,
  C.1 golden fixture green
      │
      ▼
extend scale_report.py: --gate6 sweep + nodes/√playable column
      │
      ▼
run ≥250 seeds/depth × 8 depths × the §5 forms  →  gate6_matrix.json
  + SCALE_REPORT.md § "Scaled investigation structure" + per-form
  interpretation + explicit §7/§8 verdict
      │
      ▼
STOP.  owner reviews.  implementation spec only if §7 is met.
```

## 10. Note on tooling (Atlas)

The build is: a new `escape.py` helper + a `build_mystery` insertion
point (940-line module — past Atlas's edit ceiling, log rows 17/29/43+)
and a `scale_report.py` sweep extension (~100 lines procedural — past
the harness ceiling, Gate 8 `f430323f`). **Hand-written.** The
"genuine intermediate beat" definition and the falsification reasoning
are design judgement — not an Atlas surface. Log the attempt in
`ATLAS_CAPABILITY_LOG.md`; no new `atlas-self` todo unless a *new*
failure mode appears (the two relevant ones are already filed).

---

## STATUS — experiment RAN, hypothesis FALSIFIED (§8 path 1), 2026-08-30

`tools/scale_report.py --gate6`, 250 seeds/depth, 10 mechanisms, depths
0–12. Raw: `tools/gate6_matrix.json`. Full table + reading:
`SCALE_REPORT.md § Scaled investigation structure`.

**§7 verdict: no form passes — no scaled form, no `fixed` control.**
The failure is structural, not tuning:

- **Scaled beats fix the emptiness problem.** `meaningful_fraction` at
  depth 12: baseline 0.54, `sqrt@1` 0.74. `nodes / √playable` holds
  ~0.16 flat — the scaling function works as designed.
- **But they worsen viability.** `ratio p90` d12: 1.53 → 1.75. Every
  required beat is +2–4 required tiles; the survival budget counts
  tiles, not meaning. `require→obstacle` untouched (beats sit on the
  `spawn→route` spine); backtrack rises to 0.08–0.10.
- **The scaling form is irrelevant** — `fixed / log / sqrt / linear`
  all fail identically. The *sign* is wrong: added required structure
  can only lengthen the required circuit.

**Three experiments now converge (§8):** C.3.2a-5 rearrange → viable to
depth ~4–6; Gate 8 relational ceiling → same ceiling; C.3.2a-6 scaled
structure → fixes emptiness, worsens viability. **The survival envelope
is the wall.** → the next move is the campaign-design decision, not a
generator lever: **formally bound supported depth to 0–N ≈ 5–6**;
deep expeditions a deliberately different (non-procedurally-equivalent)
format.

**Keep as an option:** `_lever_scaled_beats` genuinely fixes
`meaningful_fraction` and, at shallow depth where the circuit already
fits, costs nothing. It is a content/texture lever for the 0–N range —
its own small decision, separate from the viability line.

---

*Experiment spec. Nothing ships. Baseline byte-identical. This tested
structural growth ALONE — no survival-envelope change, no lever
combination — and the evidence says: structural growth is the right
treatment for emptiness and the wrong one for viability. They are
different problems.*
