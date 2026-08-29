# Phase C.3.2a-5 — destination-network viability as geography expands (spec)

Grounded in **`SCALE_REPORT.md`** (200 seeds × 8 campaign depths).
Builds on `PHASE_C3_2_SPEC.md`. **Spec only — no generator change until
this is reviewed.**

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

### `required_circuit` (define precisely; `scale_report.py` currently
approximates it)

The shortest path a survivor must actually walk to solve the mystery:

```
spawn → { route, require, require2 } in nearest-first order → obstacle/escape_tile
```

Not the greedy "touch every site" circuit the tool reports today (that
includes `closed` and the town centre, which are context, not
requirements). Refining the tool to the true required set is the first
task of implementation.

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

- **Do NOT put all required sites into a compact spawn cluster.** We
  already know why: it makes the *map* bigger without making the
  *place* bigger. `near` is already flat at ~5 — that's the symptom of
  over-clustering, not a target to lean into.
- **Do NOT shrink the maps.** `map growth` is on the frozen balance
  list (`PHASE_C3_SPEC.md`). The world getting larger is a feature.
- **Do NOT touch** combat / hunger-thirst rates / encounter / loot —
  also frozen. This spec changes *where content goes*, not how fast
  the clock runs.
- **Do NOT** regress v1 byte-identity for depths where the lever
  doesn't change placement (the golden fixture covers depth ~2–3).

## What C.3.2a-5 is NOT

- not a navigation-UI change (that's pieces 0/1/2/4);
- not a mystery-mechanism change (the roles stay: closed / route /
  require / [require2] / [power] / escape);
- not the v2 irregular mask (still parked);
- not a campaign-length or roguelite-inheritance change.

## Method

1. Refine `scale_report.py`: `required_circuit` = the true required set
   (route/require/require2 → escape), not the greedy all-sites circuit.
2. Instrument 3–5 real expeditions at depths 3 / 6 / 9 to calibrate
   `survival_budget` and its margins against actual play.
3. Implement each lever behind a flag / constant; A/B each alone across
   all depths; fill the lever matrix with numbers.
4. Owner reviews the matrix → picks the combination → spec's
   implementation section written → implement → gate must pass →
   commit, tag.
5. Feel-test: a **fresh survivor** (new campaign or forced level 1,
   starter supplies) at depth 4 and depth 6 — can it be *completed*
   without inherited gear?

## Build order

1. `scale_report.py` refinement + budget calibration.
2. Lever A/B matrix (no game change shipped — flags only).
3. Owner review of the matrix.
4. Implement the chosen mix. Gate passes on `scale_report.py`.
5. Fresh-survivor feel-test at depth 4 / 6.
6. Then unpark **piece 1 / piece 4** only if navigation still needs it.

## Acceptance

- The gate (`p90 required_circuit < budget` at supported depths) passes
  on ≥ 300 seeds/depth.
- The lever matrix is in the doc with real numbers and a stated reason
  for the chosen combination.
- A fresh survivor completes a depth-4 and a depth-6 expedition in the
  owner's feel-test without relying on inherited supplies.
- v1 byte-identity holds where placement is unchanged.

---

*Spec only. No generator change until the lever matrix is reviewed.*
