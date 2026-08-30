# Navigation / objective investigation

`tools/nav_autoplay.py` + the `objective` policy (`tools/autoplay/
policies.py`) + the `tui._SPATIAL_MODE` A/B switch. Run after
`RESOURCE_MODEL_RESULTS.md` put the attrition deaths downstream of
navigation.

The `objective` policy is perception-bounded: it acts on the `!` / `+`
mystery markers **visible on the rendered map** and, before any marker,
heads for the nearest visible structure to search it. It never reads
`m.sites`. The runner uses the real objective tile for **analysis
only** (distance-delta, "did this move close or widen").

## Findings

### 1. The map marker is the load-bearing spatial signal — not the panel text

Once the `objective` policy has a `!` marker on screen it navigates to
it cleanly:

| | before hysteresis | with commit-to-target |
|---|---|---|
| `wandering` turns | 46% | **~0%** (a handful) |
| expeditions won | 0 | **~18%** (34 / 191) |
| unique-tile ratio | 0.02 | 0.10–0.16 |

The bounce in the first version was equidistant markers (the `closed`
site is behind you); committing to one target until reached fixes it.

### 2. The cardinal-vs-landmark A/B is ~null — for a marker-navigating agent

12 campaigns each, same seed:

| metric | `landmark` (approach ladder) | `cardinal` (bare bearing) |
|---|---|---|
| pursuing / investigating / exploring | 20 / 61 / 16 % | 42 / 34 / 20 % |
| wandering | 0% | 0% |
| moves that widened distance (obj knowable) | 0% | 0% |
| objective knowable by turn (median) | 5 | 4 |
| unique-tile ratio | 0.10 | 0.12 |

**The perceived bot reads the `!` glyph, not the panel's `heading()`
text — so the panel phrasing barely moves it.** This is itself the
result: *a player who can see the marker on the map does not need the
bearing at all.* The panel wording only matters when there is **no
marker visible** (lead off-screen / not yet learned) — which is
exactly the runs-1–5 situation, and needs either a bot that navigates
by text (no marker peeking) or a human to A/B properly.

### 3. The bot still rarely *completes* — the discovery problem, not the pursuit problem

`objective tile physically reached: 1 / 191`; `investigating` is
34–61% of turns; `unique-tile ratio` ~0.1 (heavy revisiting). Leads
are learned by entering buildings, and a systematic building sweep is
hard for a naive agent (and, per the playtests, a naive human). The
navigation *pursuit* is tractable once a marker exists; getting the
marker to exist is the bottleneck.

## What this means for the design

- **The spatial-language lever is marker salience + earliness, not
  panel wording.** Make a `!` appear as soon as a lead is learned, keep
  it unambiguous (the hot-step site distinguished from stale ones),
  and the pursuit takes care of itself. The approach-ladder text
  (`ec9648b`) is a fine backstop for when the marker is off-screen but
  it is not the primary carrier.
- **The investigation thread needs the discovery loop surfaced** —
  "you've learned about a place; here's where it is" — which is the
  deferred *extend-the-ESCAPE-panel-to-the-investigation* work plus
  the objective *lifecycle*.
- **Re-run `resource_autoplay.py` with the `objective` policy** once
  the discovery loop is better: shorter, more directed runs should
  relieve the attrition the resource investigation flagged.

## Durable artifacts

- `objective` policy (marker-navigating, commit-to-target) — the
  starting point; needs a real building-sweep strategy to measure
  completion.
- `tui._SPATIAL_MODE` — `"landmark"` (default) / `"cardinal"`, for the
  A/B once a text-navigating bot or a human runs it.
- `nav` events in the telemetry stream (category, marker-visible,
  obj-distance + delta, why-wander) — the causal navigation dataset.

---

## F — mark the entry point from turn 1 (`src/mixins/ui_mixin.py`)

The bottleneck above was "getting the marker to exist". F acts on it
directly: the `closed` site (where the survivor walked in) is now
marked from turn 1 instead of only after you've stood on it, and an
opening beat ("the way you came in — blocked, but a survivor would
have looked there first; it's marked {bearing}") points at it. For
most mechanisms `closed` is exactly where the first real leads
(`F_ROUTE` / `F_REQUIRE`) surface, so this converts the opening from
"wander until you hit the right building" into "head for the entry
point, then follow the leads".

### Result (`fatigue_autoplay.py --campaigns 6`, `objective` / `objective_rest`)

| policy          | metric                | before F | after F |
|-----------------|-----------------------|----------|---------|
| objective       | wins                  | 11       | 21      |
| objective       | deaths                | 31       | 18      |
| objective       | timeouts              | 23       | 59      |
| objective_rest  | wins                  | 6        | 28      |
| objective_rest  | deaths                | 30       | 22      |
| `nav_autoplay`  | objective knowable by turn (median) | 5 | 1 |

Deaths down ~40%, wins roughly doubled: the early destination changes
behaviour from "wander and die of attrition" to "pursue leads". The
timeout rise is the flip side — expeditions that used to end in death
around turn ~83 now survive to the 600 cap, because the `objective`
policy still cannot execute the full mystery chain (`unique-tile
ratio` stays ~0.03; it oscillates between searched structures once the
marker is reached). That is a bot-quality ceiling, not a game defect:
the game now surfaces the destination early and clearly; a competent
navigator (human or a better policy) converts it. **F is the last
content-side navigation lever for World-1** — remaining lead-discovery
work is policy/tooling, not game code.
