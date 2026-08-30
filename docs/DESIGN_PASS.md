# The post-playtest design pass

**Status:** design, not implementation. Written after run 7
(`docs/DEV_PLAYTEST.md`) closed the blind-playtest phase. Nothing is
built against these docs yet. Balance stays frozen until the design is
decided.

Run 7 is the boundary between evidence collection and design:

```
runs 1–7  +  500-game perceived-bot baseline
                     │
        ┌────────────┴────────────┐
        │   EVIDENCE COLLECTION   │   ← done
        └────────────┬────────────┘
                     │  run 7
        ┌────────────┴────────────┐
        │      DESIGN PASS        │   ← here
        └─────────────────────────┘
```

## What the seven runs established

**The game did not fail as a whole.** It failed at one consequential
interface boundary: the player learned the wrong combat behaviour
because the interface taught him that every zombie encounter was the
same decision.

1. **The story / navigation / escape spine works.** Runs 6–7 show that
   `goal → named thing → recognizable destination → action →
   persistent progress` is a viable native language for Apocrysis. The
   player followed the story without a compass because the world gave
   him things to understand and move toward. **Preserve this pattern.**
2. **Attention is a behavioural-training problem, not a decoration
   problem.** Run 7: ~8 `LOW / Fight ~100% / overkill` encounters
   trained the policy `‼ ZOMBIE = press f`; the one `EXTREME` encounter
   had the same visual structure and the trained policy killed him.
   The requirement: **attention must communicate not just that a
   decision exists, but how much the player should interrupt their
   current behaviour to reconsider it.**
3. **Combat calibration is independently proven bad.** A `LOW /
   overkill` encounter that removes 86 HP poisons the whole decision
   system. Even perfect attention design cannot fully fix that. Two
   separate layers:
   ```
   COMBAT MODEL           "what is actually happening?"
          ↓
   COMBAT COMMUNICATION   "how should the player understand it?"
   ```
   Do not conflate them.

## The five principles (frozen from the runs)

1. **Attention is graded.** Routine encounter → meaningful decision →
   dangerous decision → critical decision. The visual interruption
   itself is information, and it must correlate with actual
   consequence.
2. **Spatial language describes the world, not coordinates.** "Get the
   jerrycan / the ranger station is close by / take it to the
   generator shed / it's marked on your map" — not "go south-west."
   Cardinal directions are supporting information, never the primary
   semantic carrier.
3. **Objectives have a lifecycle.** Run 6: the objective *worked*,
   then lost behavioural priority once the player entered the
   exploration loop. The system must know the difference between "here
   is something interesting you learned" and "this is still the thing
   you are trying to accomplish" — without nagging every turn.
4. **Interaction inference removes ceremony.** If the player's
   world action unambiguously *is* the intended action, don't require
   a redundant command. Auto-escape is instance 1. The boundary is
   already drawn right: entering the escape tile → infer; `clear` /
   `open` / `pull <control>` → explicit decision.
5. **Routine must be distinguishable from exceptional.** The common
   thread behind the zombie problem *and* the safe-building problem:
   when everything gets the same presentation weight, nothing has
   attention, and the player adapts by filtering. Fresh vs Heavy
   Zombie; random residential building vs important narrative
   location; routine movement vs important discovery — all currently
   near-equivalent in weight.

**Overarching:** *Apocrysis needs a hierarchy of attention that
mirrors the hierarchy of meaning in the world.* Not more UI, colour,
or markers — hierarchy.

## The architecture of the design work

```
                    APOCRYSIS EXPERIENCE
                           │
             ┌─────────────┼─────────────┐
             │             │             │
         ATTENTION    SPATIAL LANGUAGE   INFERENCE
          how loudly?   what / where?    do I need to ask?
             │             │             │
             └─────────────┼─────────────┘
                           │
                    PLAYER EXPERIENCE
                           │
                    ┌──────┴──────┐
                 COMBAT       STORY / WORLD
                 MODEL         LANGUAGE
              simulation      narrative design
              experiment
```

Three interface specs + one model experiment, each independent:

| doc | question | not responsible for |
|---|---|---|
| [`DESIGN_ATTENTION_LANGUAGE.md`](DESIGN_ATTENTION_LANGUAGE.md) | how loudly should the game tell me this matters? | what the thing *is*, where it is, or whether the numbers are right |
| [`DESIGN_SPATIAL_LANGUAGE.md`](DESIGN_SPATIAL_LANGUAGE.md) | what/where is the thing I care about, in terms I can act on? | how loud the objective line is (attention), or combat |
| [`DESIGN_INTERACTION_INFERENCE.md`](DESIGN_INTERACTION_INFERENCE.md) | what can the world infer from my state + location without another command? | anything the player must *decide* |
| [`COMBAT_MODEL_EXPERIMENTS.md`](COMBAT_MODEL_EXPERIMENTS.md) | is what's actually happening in a fight sane, and does the forecast match outcomes? | how the fight is *presented* (attention) |

## Not starting from zero

Two working pieces of the eventual language already exist:

- **The ESCAPE panel** = working objective / spatial language. It is
  the reference implementation for `DESIGN_SPATIAL_LANGUAGE.md`, not
  something to replace.
- **auto-escape** = working interaction inference. Instance 1 for
  `DESIGN_INTERACTION_INFERENCE.md`.

The major missing piece is the **attention hierarchy**, and run 7 is
the clean demonstration of why it matters.

## Sequencing

1. Write the three interface specs + the combat-experiments doc
   (these files). Each must pass its own "test against real run-7
   examples" section before it is considered done.
2. Run the combat-model simulations (they need `tools/balance_autoplay`
   +/- new instrumentation, not more blind playtesting).
3. Implement against the specs — attention first (it is the missing
   piece and the run-7 killer), then spatial-language refinements,
   then the interaction-inference candidates.
4. The perceived-bot A/B (`tools/tui_autoplay.py --nav-phrasing`)
   validates the spatial-language change with numbers.
