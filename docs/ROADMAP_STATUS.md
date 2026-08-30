# Roadmap status — World 1 (~25-expedition arc)

*Snapshot 2026-08-29. What's built, what's left, and the two gates that
come before content authoring.*

## What "the arc" is (`APOCRYSIS_ROADMAP.md` §9)

~5 chapters + finale, ~4–5 maps each, **~25 expeditions total**, ending
in a bespoke final expedition realised from the player's own
discoveries plus an ending choice.

**What is built today is the roadmap's Phase A deliverable — an 8–10
expedition mini-campaign.** `CAMPAIGN_LENGTH = 10`; `campaign.py` has 10
chapter-intro lines; the WorldFact DAG covers **CH1 + CH2 only**
(9 of ~24 authored facts).

## Built and frozen — the engine + the first ~40 % of the story

| | state |
|---|---|
| **Phase A — the spine** | ✅ `worlds/` seam · `WorldFact` DAG (CH1 THE SILENCE = 4, CH2 THE INFECTED = 5) · 12 `DiscoveryTemplate`s · persistent `WorldInvestigation` · `wi` screen · milestone banner · milestone-keyed chapter intros |
| **Phase B — roguelite loop** | ✅ death → new survivor · campaign/survivor profile split · 3 `SurvivorLore` (legibility not power). B.3 optional-evidence valley file skipped. |
| **Phase C foundation** | ✅ `src/worldgen/` extraction (byte-identical) · `MapGraph` connectivity guarantee · deterministic structural suite. **C's irregular-map rewrite was experimented and rejected** (`PHASE_C3_SPEC.md`). |
| QoL since | auto-play-log, name sanitisation, numbered gear, map terrain colour, graph-honest ESCAPE heading (piece 0), `look` recovers the route direction (piece 2 — validated in real play). |

## Not built — what the full arc still needs

| bucket | state | size | note |
|---|---|---|---|
| ~~Pick the ending~~ | ✅ **DECIDED 2026-08-29** | — | Truth A "The Cordon"; **authored-canonical ending + one final binary choice** (broadcast the truth outward vs protect the settlement's silence). `PHASE_A_DECISIONS.md` / `WORLD_TRUTH_CANDIDATES.md`. Gate cleared — CH3–FIN authoring unblocked once C.3.2a-5 lands. |
| ~~Scale viability — C.3.2a-5~~ | ✅ **RESOLVED (C.3.2a-7)** | — | Content levers exhausted (lever matrix + Gate 8 + C.3.2a-6 all falsified — `SCALE_REPORT.md`). Fixed structurally: `game.depth_supply_bonus` scales starting food/water + win prize with campaign depth → `ratio p90 < 1` through depth 12, zero campaign-bot regression. Deep expeditions inheritance-scaled by design. |
| ~~Story content CH3–5 + finale~~ | ✅ **AUTHORED 2026-08-30** | — | `truth.py` 9 → 23 `WorldFact`s; 14 on the RESPONSE thread across CH3-FIN; 8 milestones; every fact `DiscoveryTemplate`-bound; DAG walks clean; 56/56 targeted mysteries valid. `PHASE_A1_TRUTH.md` CH3-FIN section. |
| ~~Competing hypotheses + wrong-commitment arc~~ (E.1) | ✅ **DONE 2026-08-30** | — | `worlds/silence/hypotheses.py` 4-rung ladder + `current_hypothesis()` + correction banner. NOT a `knowledge.py` change (campaign-level, not per-mystery). |
| ~~The final expedition + ending choice~~ (E.2/E.3) | ✅ **DONE 2026-08-30** | — | expedition 25 routes to a finale-stamped mystery; `_finale_choice()` BROADCAST/PROTECT; two authored endings; `campaign.ending` persists. Bot completes 4/4. |
| ~~Campaign 10 → 25~~ | ✅ **DONE 2026-08-30** | — | `CAMPAIGN_LENGTH = 25` + `DIFFICULTY_RAMP_LENGTH = 10` (curve decoupled from arc length); `campaign.py` 6 chapters + `_CHAPTER_BOUNDS` + `chapter_for_expedition`. Bot completes 7/8 full runs. |
| **Phase D — world conditions + region mutation + `escape_kind`** | 0 % | large | roadmap puts it on the path to E; arguably deferrable for a *rough* first arc |
| **Nav affordances — C.3.2 pieces 1 / 4** | parked | small | only if navigation still needs it after C.3.2a-5 |
| **Long-campaign balance** | untuned | medium | a survivor 15 expeditions deep without dying is drowning in inherited loot (BlueNoodle had 4 guns at expedition 4). `_prize_bonus` + inheritance compound. |

## Bottom line (2026-08-30)

**The full World-1 arc is playable start to finish.** All five chapters
+ the finale are authored (23 `WorldFact`s); `CAMPAIGN_LENGTH = 25`; the
finale routes to a bespoke command-centre expedition ending on the
BROADCAST-or-PROTECT choice with two authored endings. 300+100 tests
green; the bot completes 4/4 full 25-expedition campaigns.

```
pick the ending                       ✅ Truth A, authored + one choice
      ↓
land C.3.2a-5 (or equivalent)         ✅ C.3.2a-7 inheritance-scaled supply
      ↓
author CH3–FIN facts + templates + prose      ✅ 23 WorldFacts, DAG clean
      ↓
CAMPAIGN_LENGTH = 25  +  5-chapter grouping   ✅ + DIFFICULTY_RAMP_LENGTH
      ↓
finale + ending choice (E.1/E.2/E.3)          ✅ shipped
```

### What's left — polish, not blockers

- **A human blind playtest of the full 25-expedition arc** — highest value.
- Phase D (world conditions / region mutation / `escape_kind` variety).
- Parked nav pieces 1/4; the `DIS_FEW_REMAINS`→only-`mountain_pass`
  variety fix (every fresh campaign's expedition 1 is identical).
- Long-campaign loot balance (inherited loot compounds past ~exp 10).
- A dedicated finale map *archetype* (E.2 uses the normal generator +
  a fixed target + labels); an NPC-adjacent arrival scene at the
  consolidation point.
- The known expedition-9 combat-power wall (bot gets stuck there ~1/8).
