# Design spec — Interaction Inference

**Status:** IMPLEMENTED (2026-08-30) - see DESIGN_PASS.md. Original design note follows.

**Status:** design. auto-escape (`7e35210`) is instance 1 and the
worked example. This spec exists so "auto-escape" does not generalise
into "automate everything" — it defines the rule and enumerates the
candidates rather than inferring opportunistically.

## The question this system answers

> **What can the world infer from the player's state and location
> without asking for another command?**

## The rule

An action is **inferable** only if all four hold:

1. **Unambiguous.** The player's world state + position *determines*
   the intended action — there is exactly one thing a reasonable
   player means here.
2. **No live alternative.** There is no other action the player might
   plausibly choose in this exact state instead.
3. **Not a commitment.** It does not spend a scarce/irreversible
   resource, and it is not the moment a puzzle is *answered*.
4. **Cognitive work already done.** The command would only be
   re-stating a decision the player has already made by getting here.

If any one fails, it stays an explicit command. When in doubt, it
stays a command — a redundant keystroke is a small cost; an inferred
action the player didn't intend is a large one.

## What must stay explicit — and why

| action | fails rule | why it's a real decision |
|---|---|---|
| `clear` / `open` the obstacle | **3** (commitment) | consumes the requirement item; it's the "I am spending my one key here, now" moment |
| `pull <control>` (dam_valves) | **1, 2** | *which* control is the puzzle — the whole point of the experimental family |
| `eat` / `drink` / `med` | **2, 3** | resource management is the game; auto-consuming removes a decision and a failure mode, and there's always the alternative of "push on and find more first" |
| `eq <weapon>` mid-encounter | **2** | loadout is a choice with tradeoffs (durability, ammo, reach); the encounter card already surfaces the better option via `[w]` without taking the choice |
| `reload` | **2, 3** | timing a reload (now, vs after this fight, vs never) is tactical |
| `rest` | **2, 3** | rest trades in-game time for fatigue; when to pay that is a decision. (The playtest finding here is a *surfacing* problem — solve it in the attention/spatial specs, not by auto-resting.) |
| the finale binary choice | **1, 2** | it is *the* authored decision of the campaign |

## What is already inferred (and correct)

These predate this spec but pass the rule — recorded so they're not
"discovered" and second-guessed later:

| inferred action | trigger | rule check |
|---|---|---|
| **escape** | arrive at the escape tile with the mystery solved (obstacle open + hypothesis confirmed) | ✓ all four — you navigated here having done the whole investigation; there is nothing else "arrive at the exit" could mean |
| **pick up the requirement item** | arrive at the `require` site | ✓ — the clue told you it's here; taking it is not a choice |
| **surface a site's evidence** (the old `search` step) | arrive at any named mystery site | ✓ — "go through the place" was ceremony; being there *is* the investigation |
| **finish the expedition** | reach the Town Center on a no-mystery map (degenerate fallback) | ✓ — the only win condition on that map |
| **name a location** | first arrival at a labelled site | ✓ — recognition, not action |

## Candidate list — evaluated, not implemented

Anything proposed in future is added here and checked against the rule
*before* code:

| candidate | verdict | reason |
|---|---|---|
| auto-`clear` the obstacle when you step onto it carrying the item | **rejected** | fails rule 3 — see table above. Keep the keystroke; it's the commitment beat. (The ESCAPE panel should make it obvious it's the next step — that's spatial language, not inference.) |
| auto-advance "Press Enter to continue" on pure-information screens | **rejected** | those are pacing beats; the pause is deliberate |
| auto-equip the starting weapon at expedition start | **accepted** | unambiguous, no alternative, no commitment, no decision — the survivor "comes in wearing it" (already done in `dev.equip_for_depth`; make it the normal path too) |
| auto-drop a broken weapon when picking up a strictly-better one and the pack is full | **needs design** | fails rule 2 if the "broken" weapon is craftable-into-something; revisit with the crafting model |
| end the expedition-1-style post-win zombie encounter (run 7: a fight fired in the same turn as the win) | **accepted** | once `won` is set the expedition is over; nothing that turn should still prompt a combat decision |

## Instance 1 — auto-escape, as built

```
arrive at m.escape_tile
  └─ obstacle_open AND hypothesis confirmed?
       ├─ yes → mystery_try_escape()  → MYSTERY SOLVED / milestone /
       │                                correction / finale choice /
       │                                finish_expedition   (no prompt)
       └─ no  → one L1 line: "this is the way out — still blocked" /
                "…not sure yet it leads anywhere"
```

Adjacency is **not** the trigger — the exact designated tile is — so
navigation stays meaningful. The `escape` command remains as the
leave-from-a-distance shortcut once solved (a separate convenience,
not inference). Asserted: `enter_escape_tile → expedition_completed`
with zero input requests
(`test_world_investigation.test_reaching_the_open_way_out_escapes_without_the_keystroke`).

## What this spec is NOT responsible for

- **Making the next step obvious** — that's spatial language (the
  ESCAPE panel hot line). Inference removes a keystroke; it does not
  substitute for the player knowing what to do.
- **Difficulty** — none of these changes make the game easier; they
  remove interface bureaucracy, not challenge.
- **Automating play** — the `auto` / `a` command is a separate,
  explicit, player-invoked thing and out of scope here.
