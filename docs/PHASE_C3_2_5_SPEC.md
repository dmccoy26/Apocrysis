# Phase C.3.2a-5 — destination-network viability as geography expands (spec)

Grounded in **`SCALE_REPORT.md`** (200 seeds × 8 campaign depths).
Builds on `PHASE_C3_2_SPEC.md`. **Owner-approved 2026-08-29** (proceed
to task 1). **Spec only — no generator change until the lever matrix
is reviewed.**

## North star

> **Can the larger world contain proportionally enough meaningful
> destinations and routes that its increased physical scale remains
> playable?**

The question is *not* "can we make the mystery short enough?" — that
invites the spawn-cluster failure in a nicer shirt.

## The question

> **Can the world become physically *larger* without becoming
> proportionally *emptier*?**

Not "don't make maps too big." A later expedition *should* feel
geographically larger — the growth `15² → 24² → 27² → 33² → 34²` is not
assumed wrong. The mismatch the report exposes is:

> geography grows ~5× while the amount of meaningful content stays fixed.

## Two problems, now separated (this is the point of the report)

| | discovery / orientation | **completion** |
|---|---|---|
| question | "which way do I go?" | "how much geography must I cross to solve this?" |
| measured | nearest meaningful site ≈ **5 tiles at every depth** | solve circuit p50 **20 → 60 tiles**; p90 **28 → 80** |
| addressed by | pieces 0 ✅, 2 ✅ (and 1 / 4, parked) | **this spec** |

`SCALE_REPORT.md`: the fraction of maps whose solve circuit alone
exceeds a fresh survivor's whole movement budget goes **0 % → 24 %
(depth 4) → 54 % (depth 6) → 74 % (depth 12)**. The roguelite loop
masks it (inherited supplies); a fresh survivor or a post-death heir
hits the wall at depth 3–4.

## The invariant

> **An expedition's required investigative circuit must remain within a
> viable exploration budget as geography expands.**

Raw *sites per 1000 tiles* is a **diagnostic, not the requirement** —
five well-distributed sites can be perfectly playable; ten badly
placed ones can be miserable. The player-facing contract is a ratio:

> **primary metric — `required_circuit / survival_budget`, at p90 (not
> mean), at every supported campaign depth.**

### `survival_budget` is an empirical *envelope*, not the optimisation target

The gate is `required_circuit / survival_budget < 1` at p90. But a
lever must **not** be judged a success just because it drives that
ratio under 1. Two maps can both have a 70-tile required circuit and
play completely differently:

- 70 mostly-forward tiles with intermediate opportunities → fine;
- 70 tiles of repeated backtracking through already-cleared territory →
  awful, same number.

So `survival_budget` bounds *feasibility*; it does not define *quality*.
The measurement matrix below carries a third number precisely so we
don't "solve" this by generating efficient-but-boring spaghetti.

### The three-number measurement matrix

| measure | purpose |
|---|---|
| **required-circuit p50 / p90** (tiles) | how much travel the authored mystery actually demands |
| **survival-budget ratio p90** | the hard feasibility gate |
| **backtrack / repeated-travel proportion** | quality diagnostic — measure it, don't make it a hard invariant *yet*. A lever that passes the gate by producing high-backtrack routes has not really passed. |

### Methodological rule (locked)

**Do NOT evaluate the levers using nearest-site distance.** It stays
~5 tiles at every depth and tells us almost nothing about viability
(`SCALE_REPORT.md`). It stays in the tool as a labelled *diagnostic
only*. The primary synthetic question is:

> Given the generated world and the actual mystery structure, how much
> **traversable travel** does a survivor need to complete the required
> investigation **and reach the escape**?

### `required_circuit` (define precisely; `scale_report.py` currently
approximates it)

The shortest traversable path a survivor must actually walk to solve
the mystery, from `escape.py`'s real role set:

```
spawn → { route, require, [require2], [power] }  (nearest-first order)
      → obstacle_tile → escape_tile
```

**Excluded:** `closed` (context — "where you came in", the game itself
says it's low-value to signpost) and the town centre (info hub, not
the way out). Not the greedy "touch every site" circuit the tool
reports today. **Refining the tool to this true required set is task 1.**

### `survival_budget` (derived from the real mechanics, not guessed)

From `game.py` / `actions_mixin.py`:

| quantity | value |
|---|---|
| starting hunger / thirst | 85–95 (≈ 90) |
| starting food / water | 8 / 8 |
| decay per move | −2 day, −3 night (≈ −2.5 avg over the day/night cycle) |
| each ration / water portion | +5 |
| HP attrition once hunger **or** thirst hits 0 | −2/move each |

So a fresh survivor has `90 + 8×5 ≈ 130` hunger-points, `~130`
thirst-points, at `~2.5`/move ⇒ **≈ 50 moves before starvation
attrition begins.** Subtract margins the report's threshold didn't:

- **combat** — a fight costs ≈ 2 moves' worth of hunger/thirst; ~3–5
  fights/expedition ⇒ ~8–12 move-equivalents;
- **return travel** — from the last required site back to the obstacle
  and out to `escape_tile` (the circuit above ends there, but a real
  route detours);
- **non-beeline** — the player does not walk straight (no marker
  pre-lead); the report shows a real player takes materially longer
  than BFS distance.

⇒ **effective investigative budget ≈ 30–35 moves.** Derive the exact
figure during implementation from `balance_autoplay.py`'s survival
envelope and a few instrumented expeditions — do **not** hard-code 35
from this paragraph.

## The gate

> At every **supported** campaign depth (0 … `CAMPAIGN_LENGTH`), the
> **p90 `required_circuit` must sit below the derived fresh-survivor
> investigative budget**, with the margin above.

- "supported" is a decision, not an assumption — if depths 9–12 turn
  out to be balanced *around* inherited supplies by design, the spec
  says so explicitly and the gate applies to 0–N.
- p90, so the rare bad seed is allowed; the typical deep-campaign map
  is not.
- Re-run `scale_report.py` after each lever; the gate is the pass
  condition.

## The four candidate levers — hypotheses, tested independently

| lever | what it fixes | main risk |
|---|---|---|
| **1. scale settlement count with map *area*** (`SETTLEMENTS_PER_EXPEDITIONS` / `MAX_SETTLEMENTS`) | density | meaningless settlement spam — empty streets that dilute rather than orient |
| **2. bound the site-placement region** (place mystery sites within a radius that grows slower than the map) | circuit *length* directly | an artificial invisible boundary — the outer map becomes decoration |
| **3. cap `TOWN_DISTANCE_GROWTH_PER_LEVEL`** | the long-distance objective (town p50 8 → 32) | geography stops feeling *consequential* — the objective is always "nearby" |
| **4. distribute a mystery's sites across multiple settlements** | circuit *geometry* + gives real exploration between beats | may change mystery structure / the `_building_sites` contract in `escape.py` |

Each is a separate A/B against `scale_report.py` at all depths. Report
per lever: circuit p50/p90, the gate %, and the risk metric (e.g. for
lever 1: mean buildings-per-settlement; for lever 2: fraction of
playable tiles inside vs outside the bound).

**Likely the answer is a *combination*** (e.g. 1 + 3, or 2 + 4) — but
measure them alone first so the spec's implementation section can say
*why* the chosen mix.

## Prohibitions

- **Do NOT put all required sites into a compact spawn cluster.** It
  makes the *map* bigger without making the *place* bigger. `near` is
  already flat at ~5 — the symptom of over-clustering, not a target.
- **Do NOT let a lever pass merely by moving required locations closer
  together while the world stays increasingly empty around them.**
  That is the spawn-clustering problem wearing a nicer shirt. A lever
  that gets the ratio under 1 by shrinking the *required set's*
  footprint while `dens` (sites / 1000 playable tiles) keeps falling
  has NOT passed — the larger world must gain proportional content, not
  just a tighter mystery. Report `dens` alongside the gate for every
  lever.
- **Do NOT shrink the maps.** `map growth` is on the frozen balance
  list (`PHASE_C3_SPEC.md`). The world getting larger is a feature.
- **Do NOT touch** combat / hunger-thirst rates / encounter / loot /
  survivor power — also frozen. The experiment forces the
  **world-generation / content network** to carry the burden, not the
  survivor.
- **Do NOT** regress v1 byte-identity for depths where the lever
  doesn't change placement (the golden fixture covers depth ~2–3).

## What C.3.2a-5 is NOT

- not a navigation-UI change (that's pieces 0/1/2/4);
- not a mystery-mechanism change (the roles stay: closed / route /
  require / [require2] / [power] / escape);
- not the v2 irregular mask (still parked);
- not a campaign-length or roguelite-inheritance change.

## As built — tasks 1–3 (2026-08-29)

`tools/scale_report.py` refined:
- **`required_circuit`** = the true required set
  (`route/require/require2/power → obstacle → escape`), greedy
  nearest-first — no more `closed` / town-centre inflation.
- **survival budget calibrated**: `GROSS_BUDGET = 50`,
  `USABLE_BUDGET = 32` (derivation + the v1-death cross-check are in
  the file's header comment).
- **backtrack diagnostic** added (`1 - unique tiles / circuit length`).
- `near` demoted to a labelled diagnostic column.

Result (250 seeds/depth, **all 10 mechanisms rotated**,
`SCALE_REPORT.md`): the gate (`ratio p90 < 1`) **fails from depth 3**;
depth 6 = 1.31 / 52 % over budget; depth 12 = 1.53 / 74 %.
`backtrack ≈ 0` and `infeasible = 0 %` at every depth — a pure
*distance*-budget problem, not spaghetti and not connectivity. It is
**systemic across all 10 mechanisms** (they cluster tightly;
`airfield_plane` d6 p90 = 65 is the worst, = BlueNoodle's death).

### The decomposition finding — the escape gap is the scaling driver

`spawn → endpoint` distance: `route` / `require` stay near spawn
(6 → 10 / 15). **`obstacle` and `escape` grow** — `spawn→escape` p50
**12 → 32**. The escape gap is carved at *"the far corner"*
(`escape.py` `_carve_escape_pass`); the map grows, the exit moves out
proportionally. Leg-by-leg localises it: **`require→obstacle`** (fetch
the item, walk to the gate) scales p50 **7 → 22**.

**This sharpens the lever set.** The dominant driver is *the distance
from the spawn-clustered investigation to the far-corner escape gap*,
not the town (which isn't on the required circuit). So:

| lever | now |
|---|---|
| **2. bound placement region** | **strongest candidate** — but the thing to bound is the **escape-gap / `require→obstacle` span**, not a generic "region". Refine the lever to that. |
| 4. spread sites across settlements | plausible — a settlement near the escape corner splits the trek; but watch backtrack (currently 0) |
| 1. settlements ∝ area | addresses density (`dst/1k` 5 → 0.3) but may not shorten the required trek |
| 3. cap `TOWN_DISTANCE_GROWTH` | weaker than expected — town isn't on the required circuit; it only drifts `route`/`require` out a little |

**Next: the lever A/B matrix (tasks 4–7).** Each lever a flag in
placement; nothing shipped; owner reviews the matrix (with the
refined lever 2) before any combination is chosen.

## Frozen sequence (owner)

```
PHASE_C3_2a-5
      │
      ▼
1. refine required-circuit measurement (true required set, not all-sites)
      │
      ▼
2. calibrate the survival envelope from actual mechanics + instrumented play
      │
      ▼
3. add the backtrack / repeated-travel diagnostic
      │
      ▼
4. A/B lever #1  (settlements ∝ area)      ─┐
5. A/B lever #2  (bounded placement region) │  each ALONE, all depths,
6. A/B lever #3  (town-distance cap)         │  flags only, nothing shipped
7. A/B lever #4  (sites across settlements) ─┘
      │
      ▼
   owner review of the matrix
      │
      ▼
   choose combination  →  implement + regression gate
      │
      ▼
  fresh-survivor playtest  (depth 4 + depth 6, starter supplies only)
      │
      ▼
  then unpark piece 1 / piece 4 only if navigation still needs it
```

Each lever tested **alone first** — otherwise we won't know what
actually moved the 74 %.

## Acceptance

- The gate (`p90 required_circuit / survival_budget < 1` at supported
  depths) passes on ≥ 300 seeds/depth.
- **`dens` (sites / 1000 playable tiles) does not keep falling** at the
  chosen lever combination — the larger world gained proportional
  content, it didn't just get a tighter mystery.
- **Backtrack proportion did not worsen** vs the current generator at
  the chosen combination (measured, not gated).
- The lever matrix is in the doc with real numbers and a stated reason
  for the chosen combination.
- A **fresh** survivor completes a depth-4 and a depth-6 expedition in
  the owner's feel-test with starter supplies only.
- v1 byte-identity holds where placement is unchanged.

---

*Spec only. No generator change until the lever matrix is reviewed.
Nothing in C.3.2a-5 touches combat / hunger / thirst / loot / survivor
power — the world-generation / content network carries the burden.*
