# How the player understands the game

The design problem for the next phase is not "more escape mechanisms"
(the schema handles that). It is: **the player should understand what
a given mystery is asking them to figure out — without decoding the
interface.**

Playtest that named it: the player had a clue, followed it, found the
named place, got the key — and the game did not tell them loudly
enough that *the problem had changed*. They spent 219 turns still
behaving as if investigating, and the repeated environmental text had
become noise they'd correctly learned to ignore.

## Rule 1 — most text is ambient; important information interrupts

Do **not** try to make repeated traversal text more interesting.
Make it *less important*. The player's eye should learn:

```
Forest.
You move north.
Building.
You search.  Nothing useful here.
You move east.
════════════════════════════════
★ NEW DISCOVERY
The marina office contains a navigation chart.
════════════════════════════════
```

- **normal text** → peripheral vision, don't stop
- **banner** (`═══` rule + `★` / `⚠`) → stop and think

Banner-worthy events, and only these:
- `★ NEW LEAD` — a clue that names a place / points somewhere (the
  place gets a map marker in the same beat)
- `★ OBJECTIVE UPDATED` — the actionable step changed (new
  understanding, item acquired, obstacle opened, hypothesis
  suspected/confirmed)
- `★ NEW DISCOVERY` — a piece of evidence that moves a fact
- `⚠ WEAPON BROKEN` / `⚠` warnings — a state change that needs a
  response

Everything else stays a plain line, and revisits get the terse form
or nothing.

## Rule 2 — the four panels answer the four questions

| Panel | Player question |
|---|---|
| **Map** | WHERE am I? (and where are the places I've learned about?) |
| **Journal** | WHAT did I learn? (the evidence record) |
| **Think** (`t`) | WHAT do I believe? (the player's synthesis) |
| **Objectives** | WHAT do I do next? |

Consequence: **human memory is no longer part of the difficulty.**
The player should never have to recall "130 turns ago someone said
the keys were in the police station" — the objective panel remembers
it, the map marks it, the journal records it. The difficulty is the
*reasoning*, not the bookkeeping.

## Rule 3 — the Objectives panel is a decision aid, not a task list

```
ESCAPE — RADIO BEACON
  ✓ Found the emergency broadcast log
  ✓ Learned the beacon is at the western lookout
  ✓ Reached the lookout
  ✓ Found the dead generator
  ✓ Learned the generator needs fuel
  ▸ Find fuel
  ☐ Restore the beacon
  ☐ Follow the response
  ☐ Escape
```

- `✓` — things you know / have done
- `▸` — what the game believes is **currently actionable** (exactly one)
- `☐` — future consequences, shown so the shape of the problem is legible

Every line phrased from what the player has *actually learned* — a
named place appears only once it's known. (Implemented in `c97557a`.)

## Rule 4 — the player experiences the loop; never the taxonomy

The schema's `discovery → reasoning → resolution → confirmation` is
**generator metadata**. The player must never see `family: experimental`
or `reasoning: revise`. They experience:

1. **Discovery** — "something is wrong / something exists"
2. **Reasoning** — "I think this means…"
3. **Action** — "I'm going to try this"
4. **Confirmation** — "yep, that worked"
5. **Objective update** — "here's what matters now"

The game announces the transitions between these states (that's what
the `★` banners are). The schema is for us; the story is for the
player.

## Rule 5 — the objective and the banners say WHAT STATE, never HOW

The `▸` line and the `★` banners are powerful enough to accidentally
solve the mystery. The discipline:

| good (state to reach / why to care) | bad (a walkthrough) |
|---|---|
| `▸ Find the ranger station` | `▸ Go to 11,4, search the desk, take the red key, return to the western gate` |
| `★ NEW LEAD — the maintenance log mentions a service road beyond the quarry. Marked on your map.` | `★ NEW LEAD — go to the quarry, find the equipment shed, take the battery, use it on the bulldozer` |

The objective tells the player *what state they're trying to reach*;
the world still makes them work out *how*. Especially load-bearing
for the **corroborative** and **experimental** families, where the
"how" IS the game.

Concretely: objective lines are phrased from facts the player has
*discovered* (a named place, an item name, "the way is open"), never
from `m.sites` coordinates, evidence ids, or the resolution verb. A
banner answers "why should I care about this?" — not "here's the
solution."

## The bar for the next phase — the three-mystery test (`9ae794b9`)

**Freeze the balance numbers.** ~86% bot survival, combat-only deaths,
median 44-turn wins — that is stable and adequate. Do NOT tune combat
off the bot from here. The bot has done its job.

Build **just enough** to run the test: at least two genuinely
different families — the current `spatial` plus `infrastructural`
(dependency chains, `c67cbd25`) — ideally a third (`experimental`,
`e0475adf`). Then hand a human three generated mysteries, one per
family, **without saying which family each is**.

For each, record only:

| Question | Pass condition |
|---|---|
| What am I trying to accomplish? | player can explain it |
| What is my current lead? | player knows without rereading history |
| Where should I go? | map / objective makes it apparent |
| What am I trying to understand? | player can articulate a hypothesis |
| What should I do next? | the `▸` objective makes sense |
| When something changed, did I notice? | a banner interrupted attention |
| After a wrong action, did I understand the consequence? | result made sense without dev knowledge |

Then the gold question: *"What did you think the game wanted you to
figure out?"* — three answers like

- "A wanted me to **find** something"
- "B wanted me to figure out **what was powering** something"
- "C wanted me to figure out **which control** actually affected the route"

= the test passing. Apocrysis generates different *problems*, not
different scenery. Only after that passes do the remaining Tier-2
families get built.

## Original phase-bar note

Not another 10,000-game sweep. **Can a human play three radically
different generated mysteries** — e.g. a spatial pass, an
infrastructural power-dependency chain, an experimental dam-valve
puzzle — **and immediately understand what each one is asking them to
figure out?** If yes, the investigation game exists. If they're
confused about *what kind of problem* they're in, the transition
announcements or the objective phrasing aren't doing their job yet.
