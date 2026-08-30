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
