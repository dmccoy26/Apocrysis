# Design spec — Spatial Language

**Status:** IMPLEMENTED (2026-08-30) - see DESIGN_PASS.md. Original design note follows.

**Status:** design. Not implemented. The ESCAPE panel + the `✦ NEW
LEAD` messages are the **reference implementation** — this spec
formalises what they already do right and fixes the two places they
fall short (bare compass headings; objectives losing behavioural
priority).

## The question this system answers

> **What / where is the thing I care about, in terms I can act on
> without already understanding a compass?**

Not: how loud is the objective line (attention). Not: is the fight
survivable (combat). Just: does the player know what they're looking
for, recognise it, find it on the map, know they're getting closer,
and have it register when they arrive.

## What the runs proved

- **Runs 1–5:** a bare heading ("the evacuation corridor lies
  south-west") is not a navigation affordance — the game gave a
  coordinate instruction without a coordinate system. 5/5 failed.
  The 500-game bot: `direction_operational` **0%**.
- **Runs 6–7 exps 1–2:** `✦ NEW LEAD — the route is at the trailhead
  noticeboard / marked on your map` + `the key is at the ranger
  station / (close by)` produced clean navigation, every time, no
  compass. The bot metric this maps to: `objective_destination_named`.
- **Run 6:** the objective *worked* — then lost behavioural priority.
  The player had "take the jerrycan to the generator shed" and spent
  78 turns looting instead. Objectives need a lifecycle, not just a
  statement.

## The primitive

Every important destination is expressed as a chain:

```
goal  →  named thing  →  recognizable thing  →  action  →  persistent progress
```

- **goal** — what the player is trying to accomplish, in a verb
- **named thing** — the proper-noun label for the destination ("the
  ranger station"), so a clue that mentions it connects to a place
- **recognizable thing** — how the player knows it when they see it:
  a map marker, a landmark glyph, an approach line
- **action** — what to do there (usually: just arrive)
- **persistent progress** — the ESCAPE-panel checklist line that ticks

Cardinal directions are **supporting information only** — a
parenthetical on the named thing (`the ranger station (close by, to
the north)`), never the primary carrier. A player who doesn't know
which way is north still has the name and the marker.

## The six questions, applied to World 1's destination types

World 1 destinations are procedurally labelled (`mystery.site_labels`)
but fall into a fixed set of *types*. For each:

| type | 1. accomplish? | 2. named thing | 3. recognizable how? | 4. map association | 5. approaching? | 6. on arrival |
|---|---|---|---|---|---|---|
| **the route** (mountain pass, marina, evac sign, rail tunnel…) | leave the valley this way | `site_labels['route']` | a `!` marker (→ `+` when open); the mechanism blurb names a real feature ("a foot pass over the ridge") | marked the moment `F_ROUTE` is known | **gap today** — only a compass bearing. Fix: a proximity line at ≤ N tiles ("the ridge line is right above you") | auto-escape if solved; else "this is the way out — still blocked" |
| **the requirement site** (ranger station, harbourmaster's shed, police station) | get the item that unblocks the route | `site_labels['require']` | `!` marker; NEW LEAD names it + "(close by)" / bearing | marked when `F_REQUIRE` known | proximity line; the marker is on-screen | "This is the ranger station. You find the forestry gate key." → objective updates to "head back to the route" |
| **the obstacle** (locked gate, dropped bridge, collapsed overpass) | get past it | described in the blurb, not always labelled | on the route between you and the `!`; blocks the tile | you're walking the route toward it | you see it before you reach it ("A locked forestry gate blocks the trail") | `clear` / `open` (explicit — it's a decision), then the route tile is passable |
| **the Town Center** | (decoy) read the densest information in the valley | "the Town Center" | town glyph `T`, revealed by a found map | shown once `town_known` | — | L2 banner naming it + *"but this isn't the way out"* on first arrival; L0 bare line thereafter |
| **a generic safe building** | shelter / incidental loot | none | building glyph, indistinct from 40 others | not marked | — | **L0 only.** These must NOT compete with the named destinations (run-6 safe-building failure) |
| **a world-investigation site** (broadcast log, generator shed in later chapters) | advance the campaign thread | `site_labels` / the discovery template | `!` marker if it's a mystery site; otherwise flavour | marked if a lead points to it | proximity line | the discovery fires at its attention level (L2 for a milestone) |

The recurring gap is column 5 — **"how does the player know they're
approaching it?"** Today: a compass bearing, which runs 1–5 proved
inert. See below.

## The fix for column 5 — approach language

Replace / demote the bearing. In priority order, the game should give
the player the strongest available cue:

1. **On the map, on screen** — the `!` marker is visible in the map
   panel right now. The ESCAPE-panel line says so: `▸ the ranger
   station — on your map, near here`.
2. **Landmark line of sight** — when the destination is a feature the
   world can show (a ridge, a water tower, a marina), and the player
   is within visual range, an L1 line: *"You can see the ridge line
   from here — the pass cuts through it."* This is the run-6
   "you can see the water tower" pattern; it needs the world to
   actually place a recognisable feature at/near the site.
3. **Proximity, no line of sight** — within N tiles but nothing
   visible yet: *"You're close to the marina now."*
4. **Named + marked, far** — `the marina — marked on your map` (what
   NEW LEAD already says; the working baseline).
5. **Bearing** — only as a trailing parenthetical, and only when it is
   graph-honest (`nav.honest_bearing`, already built): `(north-west,
   past the fields)`.

A player should never be *given* level 5 alone. It's the seasoning.

## The objective lifecycle (the run-6 fix)

An objective is not a static line. It has behavioural priority that
rises and falls:

```
NEW ──▶ ACTIVE ──▶ DISTRACTED ──▶ REMINDER ──▶ URGENT ──▶ COMPLETE
             ▲           │             │           │
             └───────────┴─────────────┴───────────┘
                  (any objective action returns to ACTIVE)
```

| state | trigger | presentation |
|---|---|---|
| **NEW** | the objective is first established | L2 banner (attention spec): goal + first step + how to recognise the destination |
| **ACTIVE** | player is moving toward the marker / acting on it | the ESCAPE-panel hot `▸` line; nothing in the event stream |
| **DISTRACTED** | ~M turns of non-objective actions (looting, moving away from the marker, fighting) with the objective unmet | still just the panel line — the game is *watching*, not talking yet |
| **REMINDER** | DISTRACTED persists another ~M turns | one L1 line resurfaces the hot step: `◆ Still to do: take the jerrycan to the generator shed — it's marked.` Once. |
| **URGENT** | a real cost is now in play — food/water low, nightfall, a deadline mechanic, or a long time distracted with the item already in hand | L2 re-banner: the step + the concrete pressure (*"You've had the fuel for 60 turns. Two days of food left. The boat's still at the dock."*) |
| **COMPLETE** | arrival at the destination (interaction-inference spec) | L2 success + the checklist line ticks; the next step becomes ACTIVE |

**Not nagging.** DISTRACTED is silent. REMINDER fires once per
distraction episode. URGENT requires an actual stake, not just a turn
count. The game distinguishes *"here is something you learned"* from
*"this is still the thing you are trying to do"* — and only raises its
voice when the second one is being dropped at a cost.

## The ESCAPE panel as reference implementation

Keep it. It already does:

- named things (`site_labels`), revealed progressively
- a persistent checklist (external memory — the run's "what did I do
  60 turns ago")
- one highlighted hot step (`▸`)
- graph-honest headings, routed so they can't contradict the terrain

What this spec adds to it:

- the approach-language ladder in the hot-step text (not a bare
  bearing)
- the lifecycle states driving whether the hot step also surfaces in
  the event stream
- the same panel treatment extended to the **world-investigation
  thread** (runs 6–7: `THE RESPONSE 0/14` produced zero felt progress
  because it had no panel, no leads, no hot step — see
  `DEV_PLAYTEST.md` run 6 finding 1)

## What this spec is NOT responsible for

- **How loud any of this is** — the attention spec sets the level of
  NEW / REMINDER / URGENT. This spec only says *when* those states
  fire.
- **Whether the destination is reachable / the map is fair** — that's
  worldgen + the connectivity guarantee, already solved.
- **Combat on the way** — combat model / attention.
- **The narrative content of the leads** — that's story design
  (`ESCAPE_STORY_*` docs); this spec is the delivery grammar.
