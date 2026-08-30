# Design spec — Attention Language

**Status:** IMPLEMENTED (2026-08-30) - see DESIGN_PASS.md. Original design note follows.

**Status:** design. Supersedes the *level* model in
`ATTENTION_SYSTEM_SPEC.md` (whose 7 semantic *channels* are kept). Not
implemented. Presentation-layer only — touches no balance.

## The question this system answers

> **How much should the player interrupt their current behaviour to
> reconsider this?**

Not: what is the thing (that's the channel, below, and it's mostly
solved). Not: where is it (spatial language). Not: are the underlying
numbers right (combat model). Just: **how loud, and why that loud.**

## Why run 7 forced this

`ATTENTION_SYSTEM_SPEC.md` shipped 7 channels but every zombie
encounter, Fresh through Elite Heavy, fires the **same** DANGER banner.
Run 7:

```
LOW zombie  → ‼ ZOMBIE banner → fight → survive
LOW zombie  → ‼ ZOMBIE banner → fight → survive          (×~8)
...
HEAVY zombie → ‼ ZOMBIE banner → fight → DEAD
```

The interface trained the policy `‼ ZOMBIE = press f`. The player did
not fail to read "EXTREME" — the interface had taught him the banner
carried no decision. **A channel is not enough. Attention must be
graded, and the grade must track consequence.**

## Two axes

Every event has a **channel** (what kind) and a **level** (how much to
interrupt). Level is the new thing.

### Channels (unchanged from `ATTENTION_SYSTEM_SPEC.md`)

`danger` · `warning` · `objective` · `discovery` · `story` ·
`success` · `narrative`. These pick colour + glyph.

### Levels — the interruption ladder

| level | name | how it breaks the stream | acknowledgement |
|---|---|---|---|
| **L0** | AMBIENT | folds into the narrative stream — one line, at most a coloured word | none |
| **L1** | NOTE | its own glyph-prefixed coloured line, breaks the paragraph | none |
| **L2** | STOP | a banner (rule above + below); the turn's output **leads** with it | none, but it's visually unmissable |
| **L3** | CRITICAL | full-width banner, blank line before, **cannot be scrolled past without `Press Enter`** | explicit |

L3 is rare by design. If more than ~one event per expedition is L3,
the mapping is miscalibrated.

## The mapping: (channel, consequence) → level

**This table is the spec.** "Consequence" is a real, derived quantity
— never a guess, never fixed per channel.

| channel | consequence signal | L0 | L1 | L2 | L3 |
|---|---|---|---|---|---|
| **danger** (zombie) | the combat forecast: threat tier + `fight%` + whether escape is the only survivable option | LOW, weapon adequate, you're near full HP | LOW/MEDIUM, some cost | HIGH, or MEDIUM at low HP, or "escape fails → you fight anyway" | EXTREME (`fight ~0%`), **or** any fight the forecast says you likely do not survive |
| **warning** (resource) | the deterioration ladder vs current stock and rate | — | first threshold ("getting hungry") | second threshold, or a stat actively draining HP | starvation imminent / HP dropping every turn with no supply |
| **objective** | is this the *first* time it's stated, or a re-statement; how long since the player last acted on it | a re-statement while actively pursued | new sub-step of an active objective | a brand-new objective, or a hypothesis that just became *confirmed* | — (objectives don't hit L3; urgency is the lifecycle's job — see spatial-language spec) |
| **discovery** | does it change the investigation (a fact / hypothesis rung) or is it flavour | flavour clue ("a child's drawing") | a `c*` clue that adds to a thread | a fact that advances a hypothesis, a new lead with a named destination | a hypothesis **correction** ("YOU HAD IT WRONG") |
| **story** | milestone weight in the WorldFact DAG | — | a minor beat | a milestone fact | the finale beats |
| **success** | did it resolve something the player was tracking at L2+ | routine loot | cleared a normal fight | opened the way / escaped / resolved an L2 warning | finished the expedition / the arc |
| **narrative** | — | everything else | — | — | — |

### The load-bearing row

The **danger** row is the run-7 fix. The encounter's level is a pure
function of `combat_forecast` output:

```
level = L0   if threat == LOW  and weapon_verdict in (adequate, overkill) and hp_frac > 0.6
        L1   if threat in (LOW, MEDIUM) and expected_hp_loss is modest
        L2   if threat == HIGH, or (threat == MEDIUM and hp_frac < 0.4),
                or fight% < 50 (escape-fails-you-fight-anyway)
        L3   if threat == EXTREME or fight% ~ 0 or forecast p(survive) < ~0.3
```

A LOW zombie you're equipped for should **barely interrupt** — an L0
line in the stream, not a banner. The player earns the right to
auto-fight those *because the game stopped dressing them up as
decisions.* Then L2/L3 means something.

## What appears at each level

| level | content |
|---|---|
| L0 | the fact, one line. (`A shambler steps out; you put it down.` — resolved inline if the outcome isn't in doubt) |
| L1 | glyph + one line of what + (if actionable) one line of what to do |
| L2 | banner: what it is · the consequence in plain terms · the choice / the one action · (combat) fight% / escape% / weapon verdict |
| L3 | everything L2 has, plus: an explicit statement of why this is different from the routine case, and the `Press Enter` gate |

## Decay

- **One-shot events** (a fight resolved, a discovery made) do not
  decay — they happened, they scroll away.
- **Standing conditions** (an unmet objective, an active warning)
  **de-escalate one level** after ~N turns of being shown at L2+ with
  no state change and no player action toward them, becoming a
  persistent L1 line rather than re-bannering every turn. They do
  **not** disappear — L1 is the floor for an unresolved standing
  condition.
- The HUD readout (the shipped Phase 2 `stat_band` shading) is the
  always-on L0 channel for resources — it carries the state
  continuously so the event stream doesn't have to repeat it.

## Escalation

A standing condition **re-escalates to a higher level** when its
consequence signal crosses a worse threshold — water 30 → L1, water 15
→ L2, water 5 → L3. Re-escalation always re-banners even if the
condition had de-escalated to a quiet L1.

## Completion

When a condition the player was tracking at L2+ resolves, emit **one**
`success` line at the level the condition last held, then it is gone.
"✓ Water back up — 40 in the pack." No lingering.

## What must remain visually ordinary (L0, forever)

- routine movement and first-visit terrain flavour
- entering a generic building / safe zone
- LOW-threat encounters you're equipped for (see the danger row)
- routine loot pickups
- ambient landmark spotting ("rooftops in the distance")
- district lines inside a settlement

If any of these ever renders above L0, the player's filter
recalibrates and the whole hierarchy degrades — that is exactly the
run-6 safe-building failure and the run-7 combat failure.

## The test — six real events from the runs

The design is **not finished** if the same treatment would apply to
all six. Each must land at a visibly different place on the ladder:

| event (from the runs) | channel | consequence | level | rendering |
|---|---|---|---|---|
| **Fresh Zombie, LOW, screwdriver "overkill", full HP** (run 7 exp 1) | danger | trivial | **L0** | `A fresh one lurches out of the trees; you put it down.` — inline, no banner, no prompt |
| **Heavy Zombie, EXTREME, `fight ~0%`, no armor, L3** (run 7 exp 3) | danger | likely death | **L3** | full banner + *"This is not the fights you've been winning. Your weapon barely lands. If you fight, you probably die here."* + `Press Enter` |
| **broadcast-log discovery** (run 6) — "someone has been listening the entire time" | story / discovery | milestone, reframes the thread | **L2** | banner: the line, + `◈ A PIECE FALLS INTO PLACE` |
| **new objective** — "The old mountain pass is the way out" (run 7 exp 1) | objective | first statement of the run's goal | **L2** | banner: the goal + the first step + "marked on your map" |
| **low water** — "GETTING THIRSTY" at 29 (run 7) | warning | first threshold, supply in pack | **L1** | `⚠ Thirst climbing — you've water in the pack.` one line; HUD number already orange |
| **important location** — the Town Center / a trailhead noticeboard | discovery | information-dense but *not* the way out | **L2** on first arrival (it hands you leads), **L0** thereafter | banner naming it + the leads it gives; a bare re-entry line afterward |

Six events, five distinct levels, and the two that share a level (the
broadcast log and the new objective, both L2) share it for the same
reason — both are "stop, this changes what you're doing" — and render
differently by *channel* (purple story beat vs blue objective banner).
That is the design working.

## What this spec is NOT responsible for

- **What the thing is** — the channel vocabulary is inherited, not
  re-litigated here.
- **Where the thing is / how to get there** — spatial language.
- **Whether the fight numbers are sane** — combat model. This spec
  takes `combat_forecast`'s output as given and only decides how
  loudly to present it. If the forecast lies (run 7 exp 1), that's a
  combat-model bug, and attention grading will still mis-level the
  event until it's fixed — the two must land together.
- **Objective urgency over time** — that's the objective lifecycle in
  the spatial-language spec; this spec only sets the level of the
  *initial* statement and each re-statement.
