# `--dev` — the story-inspection harness

Owner-specced 2026-08-30. A way to **inspect one story section** of
World 1 without grinding 25 expeditions. It is **not** a second way to
play the game.

## Usage

```bash
python3 apocrysis.py --dev --seed 12345 --chapter 3      # TUI, drop into CH3
python3 apocrysis.py --dev --seed 12345 --chapter 5      # drop into CH5
python3 apocrysis.py --dev --seed 12345 --finale         # drop into expedition 25
python3 apocrysis.py --classic --dev --chapter 3         # print-loop instead of TUI
```

`--chapter` takes 1–6 (6 = the finale, same as `--finale`). `--seed`
defaults to `12345`. With no `--chapter`/`--finale`, it drops into
CH3.

## What the dev entry does — and only this

1. deterministic `seed`
2. `expeditions_completed` = the first expedition of the requested
   chapter (`campaign._CHAPTER_BOUNDS`)
3. every `WorldFact` in an **earlier** chapter marked KNOWN — so
   `next_target()` points at the first fact of the requested chapter,
   the regional-hypothesis rung is coherent, and the `wi` screen reads
   correctly
4. a survivor at the **level + gear a real run produces at that depth**
   (`equip_for_depth`, calibrated from `balance_autoplay` telemetry —
   CH3 ≈ L8 + Steel Katana + ~9 armor). **Survivor state only** — no
   change to combat formulas, encounter/loot rates, the difficulty
   curve, or hunger/thirst. Without this, a fresh L1 body can't survive
   the depth-N curve long enough to reach any story content (playtest
   2026-08-30: CH3 jump-in on a fresh survivor died turn 32, zero sites
   reached).
5. then it hands off to the **normal game** — no alternate story logic,
   no special rendering, no in-game bypass

The presets are **semantic** (`--chapter 3` = "the beginning of CH3 in
a coherent state"), so the command doesn't rot when the exact fact
count or milestone ids change.

## Guardrails (in `src/dev.py`)

- **No balance change.** The dev entry does not touch combat power,
  inventory, survivor progression, loot, hunger/thirst, map-generation
  rules, encounter rates, or difficulty. The C.3.2a-7 supply floor
  (`depth_supply_bonus`) applies exactly as it would for a real
  survivor arriving at that depth — nothing more.
- **Sandboxed persistence.** All saves go to `.dev_playtest_profile.json`
  (git-ignored), wiped at the start of every dev run. A dev session
  can never read or overwrite a real campaign profile.
- **No alternate gameplay path.** After the drop-in, it is the same
  `run_game_loop`. A death hands to a fresh survivor at the same depth
  (the normal lifecycle, sandboxed) so the section stays playable
  through a death.

## The playtest plan (owner)

| test | run | tells us |
|---|---|---|
| **1** | `--dev --chapter 3` → play CH3 | does this story section work locally? |
| **2** | `--dev --chapter 5` → play CH5 → FIN | does the last act + finale work? |
| **3** | full campaign, no `--dev`, expeditions 1 → 25 | does the *accumulation* make the finale land? |

Jump-ins measure **local narrative quality**. The straight-through run
measures **narrative accumulation** — the real test of E.1/E.2/E.3.
A CH5 jump-in is **not** a substitute for the full campaign when
judging whether the finale has emotional weight (that needs the
accumulated survivor and the felt weight of 23 expeditions).

## Record while playing (do not fix anything)

Where confused · where bored · which discoveries felt meaningful ·
which expeditions felt interchangeable · did the hypothesis
corrections land · did the ending choice feel earned · did the finale
feel like a culmination · did you understand *why* you were going
places · where did the world feel like game machinery rather than a
place.

That log — not another metric — drives the visual-language spec
(`[[apocrysis_visual_language_direction]]` in Claude's memory).

---

## Playtest run log

Player-evidence only. **No fixes are made from these during the
playtest** — fixing individual symptoms now would contaminate the
thing we are trying to learn. The runs are accumulating into a single
coherent picture, recorded at the bottom of this log.

### Run 5 — CH3 jump-in (`--dev --seed 12345 --chapter 3`)

**Primary finding: navigation failure, 5/5 runs.**

- Intended escape: south-west.
- Player movement: east ×6, north ×20.
- The ESCAPE panel displayed the correct heading every turn.
- Player never formed a hypothesis or reached the investigation
  response (`THE RESPONSE 0/14`, hypothesis `unknown`).
- Conclusion: directional text is not functioning as a navigation
  affordance.

**Secondary findings**

1. **Fatigue presentation / system.** Fatigue reached 100% around
   turn 14 and stayed there for ~78 turns. The HUD displayed the full
   fatigue bar as green. May be a presentation inversion, a missing
   recovery affordance, or both. Do not diagnose/fix during playtest.
2. **Combat / escape incoherence.** SEVERE / EXTREME threats continued
   to show ~50% escape. Player correctly selected escape twice; both
   failed, forcing combat and ultimately killing the run. Confirms the
   already-deferred hypothesis: threat assessment and escape
   probability are communicating contradictory recommendations.
   Separate post-playtest combat-model experiment.
3. **Town Center.** Explicitly framed as containing "the most
   information in one place." Produced no evidence, fact, or hypothesis
   movement. Potential mismatch between narrative promise and
   mechanical payoff. Important for the post-playtest spatial/story
   design pass.
4. **CH3 encounter / pacing.** ~12 zombie encounters / 91 turns, most
   LOW-threat / overkill. Fatigue accumulated without meaningful
   recovery. Potentially contributing to the fatigue problem and
   making movement/combat feel mechanically repetitive.
5. **Minor.** Multiple weapons acquired without meaningful equipment
   decisions. Double-eat at the resource cap wasted food.

No changes made. Working tree remains clean.

---

## The picture forming across runs 1–5

We are no longer accumulating unrelated bugs. The simulation contains
interesting things — the SW heading, the Town Center, the
investigation, the threat assessment, the fatigue state all exist —
but the player is not being given a strong enough language for
recognizing what matters and acting on it. The player's experience is
not communicating: *this is important; do this; go there; pay
attention now.*

This is why the attention-system idea is potentially far more
fundamental than "make zombie text red." **Do not build it yet.**
Run 6 (CH5), then FIN, then the straight-through campaign. Then design
the language from what the game is demonstrably failing to
communicate, rather than guessing.

### Run 6 — CH5 → FIN jump-in (`--dev --seed 12345 --chapter 5`)

**The question this run asked:** does CH5 work as a *local* story
section entered in a coherent, appropriately-powered state? (Not:
does the finale feel earned — that needs the straight-through run.)

**What worked — and it is a sharp, useful contrast with run 5.**

- **The escape chain is legible and had momentum.** The ESCAPE panel
  filled in as a real multi-step objective: found what blocks the
  route → transmitter runs off the generator shed → reached the shed →
  need a jerrycan → reached the ranger depot → got the jerrycan →
  *"take the jerrycan to the generator shed (west)."* The player
  followed six steps in order.
- **The reason this worked where run 5 failed:** every step arrived as
  an explicit `✦ NEW LEAD` with *"(close by), marked on your map."*
  When the game names a destination and marks it, the player goes.
  When it only prints a compass heading (run 5), the player does not.
  This is the clearest actionable signal from the playtest so far.
- **Facts accumulated well** — `F_CLOSED / F_POWER / F_REQUIRE /
  F_OBSTACLE` + c1–c5, `THE RESPONSE 8/14`. Story beats landed: the
  dropped bridge and *"everyone who left went the same way, and none
  of it worked,"* the muster-point note, the child's drawing of
  mountains, and the broadcast log — *"the valley's channel is still
  monitored from the regional station… someone has been listening the
  entire time."* That reveal is a genuine hook into the next chapter.

**Problems**

1. **The hypothesis correction never fired.** 104 turns, 9 facts,
   `THE RESPONSE 8/14`, and no `"YOU HAD IT WRONG"` correction banner
   at any point. The `you think:` line differs between chapters
   (CH3 "the valley was evacuated" → CH5 "a real rescue that was
   betrayed") so the E.1 ladder is tracking at campaign level, but
   nothing in a full CH5 playthrough surfaced a correction moment —
   the single most important E.1 mechanic. (The playlog's
   `hypothesis unknown` field also appears to be a separate,
   survivor-level concept — possible confusion, not diagnosed here.)
2. **The player never executed the final objective.** Got the
   jerrycan at turn 26, then spent turns 27–104 — 78 turns — exploring
   buildings and fighting, never returning ~6 tiles west to use it.
   An explicit final objective *with a direction* still lost to the
   exploration/loot loop after ~10 turns. Run 5's navigation failure
   in a subtler form: the lead was understood, then drifted from.
3. **Safe-zone building spam is extreme.** From ~turn 65 to death,
   nearly every tile is "You enter a building. It's a safe zone.
   Restored N health and recovered some fatigue." ~40 near-identical
   buildings in a row. This trivialises survival (HP/fatigue
   constantly topped up) and buries the meaningful locations — the
   broadcast log and generator shed read the same as the 30th
   "cupboards open, someone stripped this place." The run-5 "Town
   Center inert" finding, inverted: here the meaningful location *did*
   pay off, but it is indistinguishable from the filler around it.
4. **Fatigue recovery is real but entirely map-dependent.** It cycled
   0–100 here because CH5's map is wall-to-wall safe buildings; in
   CH3's forest it pinned at 100 for ~78 turns. Recovery exists,
   is never surfaced as an action, and forest chapters have none.
   Confirms run 5 finding 1 with the mechanism.
5. **Died to an Elite Heavy — HIGH, "Fight ~53%".** Honest number
   this time, but a coin-flip-to-die encounter with escape also at
   50% and no avoidance still feels arbitrary. Fatigue was 8, so not
   fatigue-driven. Feeds the deferred combat-model experiment.
6. **Minor (repeat):** eat/drink past the cap wasted rations three
   times; 8 unused backup weapons in the pack, Katana never swapped.

**CH5 scorecard**

| question | verdict |
|---|---|
| makes you want to know what's next | yes — the broadcast-log reveal |
| discoveries feel meaningful | the lead-driven ones yes; drowned in filler |
| hypothesis corrections land | **no — none fired in 104 turns** |
| locations feel like places | the *named* ones yes; residential = 40 identical boxes |
| understand why you're going somewhere | **yes, for the escape chain** — the key contrast with run 5 |
| chapter builds toward something | escape objective builds well; player never executed it |
| finale feels like an event | not reached — died in filler 78 turns after getting the final objective |

No changes made. Working tree remains clean.

---

## The picture after run 6 — sharper

Run 5: "the player lacks a language for recognizing what matters."
Run 6 sharpens it: **the game already contains a working prototype of
that language — the ESCAPE panel.** Explicit `NEW LEAD` + map marker +
running checklist made the player follow a six-step objective across a
chapter. The failures are now specific:

1. **The investigation thread has no equivalent surfacing.** No lead,
   no marker, no checklist, no correction moment — so 9 facts and
   `8/14` produced zero felt investigative progress and the hypothesis
   ladder never visibly moved.
2. **Meaningful locations are diluted to invisibility** by dense
   interchangeable filler (safe-zone buildings, overkill LOW zombies).
3. **Even an explicit final objective decays** — the exploration/loot
   loop reasserts within ~10 turns of the player being told exactly
   where to go and why.

The post-playtest design job is now concrete: extend the ESCAPE
panel's treatment to the investigation, and cut the filler that
dilutes both. Still **do not build it yet** — run 7 (full 1→25
straight-through) first, to see whether the finale lands on
accumulation.

---

## Emerging conclusion (owner, after run 6) — the design target

**The problem is not that Apocrysis lacks guidance. It has a working
guidance language. The problem is that guidance is inconsistently
expressed and loses salience over time.**

- Run 5: abstract directional instruction — "south-west" — failed
  repeatedly.
- Run 6: concrete, named, persistent, actionable instruction —
  `NEW LEAD → marked on your map → do X` — worked initially.
- Then: even the successful pattern degraded once the player fell
  back into the exploration loop.

That is a much better target than "make the compass better."

### The post-playtest design question

Not *"how do we add more UI?"* but *"how should Apocrysis communicate
importance, action, and urgency consistently across the whole
experience?"*

The ESCAPE panel already demonstrates one successful pattern:

> named thing → explicit action → persistent visibility → map
> association → progress checklist

The attention system extends that vocabulary into the story stream —
one consistent class per line, and **ordinary movement stays
ordinary** so there is a real signal-to-noise hierarchy:

```
◆ OBJECTIVE   Go to the Ranger Depot.
✦ DISCOVERY   NEW LEAD — Ranger Depot marked on your map.
⚠ WARNING     LOW WATER — 8 remaining.
‼ DANGER      ZOMBIE — Elite Heavy — EXTREME THREAT
✓ SUCCESS     You found the jerrycan.
```

### The deeper thing run 6 exposed — the attention *lifecycle*

The jerrycan case: the game *did* communicate the objective. The
player found it, understood it, had a named destination, a direction,
and the route six tiles away — and still spent ~78 turns elsewhere.

So the fix is not merely "display the objective." The question is
**what happens when the player stops pursuing it?** That likely needs
a lifecycle, not just coloured text:

```
NEW → ACTIVE → REMINDER → URGENT → COMPLETE
```

Not per-turn nagging. But the game needs to distinguish *"this is
still the thing you need to do"* from *"this was an interesting thing
you learned twelve turns ago."* Answer this after run 7.

**Do not build any of this yet.**

### The three tests, clean purposes

| run | question |
|---|---|
| 1–5 | Does the world / exploration work, and what repeatedly confuses the player? |
| 6 | Does the late-game local story work when entered coherently? |
| 7 | Does the whole accumulated story actually land? |

Run 7 is played **as a player, not as a debugger.** Do not compensate
for what we have found. Miss what a player would miss. Get bored where
a player would. Not understanding why you are somewhere is evidence.

The playtest phase is doing its job: not telling us what code to
write, but showing us what the game is actually communicating.

---

## Revision to the run 5 finding (owner) — the game gave a coordinate instruction without a coordinate system

**Verified in code:** player-facing navigation is `src/nav.py`
`bearing()` → cardinal words ("south-west"). The *only* reference
frame the player is given is the arrow-key legend at the bottom of the
screen (`↑ north ↓ south ← west → east`). The ASCII map has no compass
rose, no "north is up" marker, and no landmark tied to the escape
route. `world_mixin._spot_landmarks()` exists ("a building in the
distance", "rooftops in the distance") but it is ambient flavour, not
a directional cue for the objective.

So run 5 should **not** be read as a failed player-navigation test. We
tested an instruction the game has not made actionable. A player
should not be expected to translate "go south-west" into "press the
key that corresponds to south-west" unless the game has taught them
what south-west means on this screen.

### The finding, revised

Old: *"the heading is shown and ignored."*

New: **abstract cardinal-direction instructions are not sufficient
navigation affordances. Concrete destinations, landmarks, map markers,
and actionable objectives are.** This is a stronger finding, and it
explains run 6: CH5 succeeded not by giving *better directions* but by
giving a chain of concrete objects and actions — blocked route →
generator shed → jerrycan → ranger depot → take it to the shed. That
is human-readable navigation.

### What this implies for the spatial language (post-playtest, not now)

`◆` blue should not mean "here is some directional text." It should
mean "this is what you are trying to accomplish, and here is how you
recognise where to go." Three layers:

```
◆ OBJECTIVE              What am I trying to accomplish?
📍 DESTINATION / LANDMARK  What am I looking for?
→ ROUTE / PROXIMITY       Am I getting closer?
```

Examples of the shift:

```
current   ◆ The evacuation corridor lies south-west.

better    ◆ EVACUATION CORRIDOR
          The way out is beyond the forest, past the old water tower.
          Marked on your map.

best      ◆ EVACUATION CORRIDOR
          You can see the water tower rising above the trees.
          Head toward it.
```

The player then recognises a *thing in the world* rather than needing
east from west. Cardinal directions can still exist internally; they
should not be the primary player-facing navigation language unless the
game gives the player a compass / reference frame.

---

## Interaction cleanup (owner, from the maps 1 & 2 playlogs) — auto-escape

**The escape location is the objective, not an interaction point.** If
the player has navigated to the actual way out, asking them to type
`escape` turns *"I found the way out"* into *"I found the way out, now
perform an arbitrary command to prove it."* That is game machinery,
not world behaviour — the same problem as the (already removed)
redundant `search` step.

**Rule:** entering the *exact designated escape tile*, with the
mystery solved (obstacle open + hypothesis confirmed), ends the
expedition automatically — no prompt, no `escape` keystroke.

- Being *adjacent* is not the trigger — the exact tile is — so
  navigation stays meaningful. (Adjacency is a future hook for an
  attention-system "the way out is just ahead" line; not built.)
- The `escape` *command* stays as the shortcut to leave from a
  distance once solved (the "solved it, then starved on the walk
  back" fix).
- `clear` / `open` / `pull <control>` stay explicit — they are
  decisions/actions, not things the world can infer.

Shipped `7e35210`; `enter_escape_tile → expedition_completed` with no
intervening input request is asserted in
`test_world_investigation.py`.

General principle for Apocrysis: **don't make the player repeat an
action the world can already infer from what they just did.**

---

## The autoplay baseline (instrument, `tools/tui_autoplay.py`) — machine confirmation

500 games, `explorer` policy, fresh expedition:

| information | received | actionable |
|---|---|---|
| objective told | 100% | ~3% destination named |
| direction shown | 100% | **0% operational** |
| landmark named | 0% | 0% |
| map marker present | ~25% | — |

`objective_reached` **0.2%**. The bot is not failing at survival — it
lives a median ~116 turns and wanders freely. It almost never converts
the information it receives into successful navigation. This is the
five human CH3 runs, confirmed by a machine that has exactly the
player's information and nothing more.

**Diagnosis, precisely:** the game communicates an objective, and
sometimes a direction — but it does not give the player a usable
spatial reference system for turning that into movement.
*Information received ≠ information actionable.*

**The post-playtest design question is therefore not** *"how do we
make the compass better?"* — a player may not know which way is east,
so cardinal directions are not the assumed answer. It is:

> **What is Apocrysis's native spatial language — one a player can act
> on without already understanding a compass?**

`◆ EVACUATION CORRIDOR / beyond the water tower / the water tower is
north-west` is still broken if "north-west" is meaningless. `◆
EVACUATION CORRIDOR / past the water tower / the tower marker is on
your map` is actionable: **goal → identifiable thing → visible thing →
movement decision.** Run 6 is the evidence this chain works where a
bare heading did not.

Still: **build none of it before run 7.**

---

## The post-run design frame (owner) — three related-but-separate systems

Don't collapse these into one "add markers everywhere" change:

| system | question |
|---|---|
| **Attention** | How loudly does the game tell me *this matters*? |
| **Spatial language** | How do I understand *what / where* to act on? |
| **Interaction inference** | When I've already done the thing, don't make me perform a redundant command (auto-escape is the first instance). |

And the CH5 chain worked because it had **meaning**, not because it
was blue or marked: *blocked route → generator shed → jerrycan →
ranger depot → return to the generator shed* is an actual mental
model of the problem. The design primitive to carry forward:

> **goal → named thing → recognizable thing in the world → action →
> persistent progress**

### Six questions to ask of every important game element

1. **What matters?** — attention
2. **What am I trying to accomplish?** — objective
3. **What physical thing should I recognize?** — landmark / destination
4. **How do I know I'm making progress?** — proximity / progress
5. **What happens when I get distracted?** — lifecycle / reminder
6. **What happens when I arrive?** — world inference, not an extra command

The 500-game baseline is the measuring stick for 1–4: 100% of bots
received an objective, ~3% received a named destination, 0% an
operational direction, 0.2% reached the objective. That gap is a
communication pipeline breaking between **received → understood →
actionable → executed** — design the language as a system that closes
it, don't patch individual complaints.

**Run 7 first.** Then design from runs 1–7 + the perceived-bot baseline.

### Run 7 — full campaign, straight through (`python3 apocrysis.py`)

Noln, fresh L1. **Died on expedition 3 of 25** — to a HEAVY ZOMBIE
(Threat: EXTREME) on turn 9, after clearing every zombie on
expeditions 1 and 2 without incident.

**What worked — the whole story/navigation/escape spine.**

- Both completed expeditions followed the escape chain cleanly off the
  `✦ NEW LEAD` markers (`route at the trailhead noticeboard, marked on
  your map` → `key at the ranger station, (close by)` → back to the
  route). Small maps, explicit named destinations, map markers — the
  run-6 pattern, holding up.
- **Auto-escape worked both times** — walking onto the pass / the boat
  dock ended the expedition, no keystroke. Clean.
- Facts accumulated (4, then 8); `THE SILENCE` went 1/4 → 2/4; the
  retrospective "THE NEXT SURVIVOR CAN LOOK INTO" handoff read well.

**What killed the run — combat, and specifically its presentation.**

1. **The encounter card cried wolf in reverse.** Expedition 1, turn 5:
   `REGULAR ZOMBIE · Threat: LOW · Fight ~100% · your weapon is
   overkill` — took Noln **100 → 14 HP** and burned all 3 medicine.
   The card said trivial; it was nearly fatal. Every LOW/overkill
   encounter on exps 1–2 (there were ~8) taught the player that the
   card's verdict means "just press `f`".
2. **So the one EXTREME encounter didn't register as different in
   kind.** Expedition 3, turn 9: `HEAVY ZOMBIE · Threat: EXTREME ·
   Fight ~0% · poorly suited · In your pack: Sword (~33%) would help`.
   The card *did* warn — correctly and in detail. The player pressed
   `w`, saw the weapon window, equipped the Chipped Sword (~11%), and
   **chose `f` anyway.** Dead in 5 rounds (20 dmg/hit, L3, no armor).
   Owner: *"he didn't realize he was fighting a heavy zombie after
   fighting all the zombies without any problems on maps 1 and 2."*
3. **Every zombie encounter has identical visual weight.** `‼ ZOMBIE
   — <NAME>` / `Stop. This is a decision.` / threat line — a Fresh
   Zombie and a Heavy get the *same* banner; the only differentiator
   is one word ("LOW" vs "EXTREME") in the card body and the rule
   length. After ~10 identical banners the player is pattern-matched
   to `f`. The attention system fires a DANGER flare for *every*
   zombie regardless of threat — it is not graded. The encounter that
   is categorically more dangerous needs to *look* categorically
   different, not just say a different word.

**Ties two deferred threads together.** The attention system needs to
**grade the zombie encounter by threat tier** (LOW = a quiet line,
maybe no banner; EXTREME = stop everything), and the combat model
needs the low-level weapon math to stop saying "overkill / ~100%" for
a fight that costs 86 HP. Both stay deferred — recorded here for the
post-playtest design pass.

**Minor:** `mws` typo → "Unknown command" (exp 1 turn 6); a zombie
encounter fired in the same turn as the expedition-1 win (fought it
post-win, no effect); safe-zone building spam still trivialises
survival on exps 1–2.

---

## Playtest phase complete — 7 runs on the table

Runs 1–5 (exploration / navigation / fatigue / combat / salience),
run 6 (concrete objectives work), run 7 (the full arc — story spine
works, combat presentation kills it), plus the 500-game perceived-bot
baseline (received 100% / actionable ~0%, objective_reached 0.2%).

Nothing more to change in the game before the design pass. The three
systems to design, now with seven runs of evidence:

1. **Attention** — graded, not uniform. The zombie encounter is the
   sharpest case: identical weight for Fresh and Heavy trained the
   player to auto-fight the one that killed him.
2. **Spatial language** — `goal → named thing → recognizable thing →
   action → persistent progress`. Run 6 and run 7's exps 1–2 are the
   evidence it works when present; runs 1–5 are the evidence a bare
   heading isn't it.
3. **Interaction inference** — auto-escape shipped as the first
   instance; the principle generalises.

Combat-model calibration (low-level weapon math, escape-vs-threat
coherence, EXTREME encounters on a difficulty ramp) is its own
experiment, adjacent to the attention work.
