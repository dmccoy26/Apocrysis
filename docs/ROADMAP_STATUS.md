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
| **Scale viability — C.3.2a-5** | **content-lever search EXHAUSTED** (`SCALE_REPORT.md`: lever matrix + Gate 8 + C.3.2a-6, all falsified) | — | **Gate, now a campaign-design decision not a generator one.** Three experiments converge: the required circuit can't be made to fit a fixed survival budget as the map grows (rearranging → viable to depth ~4–6; adding scaled structure → fixes emptiness, worsens viability; shrinking/clustering forbidden). **The survival envelope is the wall.** Next: formally bound supported depth to 0–N ≈ 5–6; expeditions N…25 a deliberately different format (inherited-supply / authored escalation / distinct mode). Owner picks the format. |
| **Story content CH3–5 + finale** | 0 % | **largest single chunk** | ~15 more `WorldFact`s + `DiscoveryTemplate`s + evidence text + milestones + **THE RESPONSE thread** (only its title string exists today) |
| **Competing hypotheses + wrong-commitment arc** (Phase E.2) | 0 % | medium-large | engine change: `knowledge.py` `self.hypothesis` → a competing set + a correction beat |
| **The final expedition** (Phase E.3) | 0 % | medium-large | bespoke, less procedural, realised from the player's own discoveries; the designed truth revealed; the ending choice |
| **Campaign 10 → 25** | structure ~40 % | small-medium | 15 more chapter intros grouped into 5 chapters + finale; pacing across 25 |
| **Phase D — world conditions + region mutation + `escape_kind`** | 0 % | large | roadmap puts it on the path to E; arguably deferrable for a *rough* first arc |
| **Nav affordances — C.3.2 pieces 1 / 4** | parked | small | only if navigation still needs it after C.3.2a-5 |
| **Long-campaign balance** | untuned | medium | a survivor 15 expeditions deep without dying is drowning in inherited loot (BlueNoodle had 4 guns at expedition 4). `_prize_bonus` + inheritance compound. |

## Bottom line

**The engine is ~done. Two of five chapters are authored and playable.
Roughly 55–70 % of the total build remains**, and it is front-loaded
with two gates:

1. ~~**Decide the ending**~~ — ✅ done 2026-08-29 (authored-canonical A +
   one final binary choice).
2. **Land C.3.2a-5** — content-lever search is exhausted (lever matrix
   + Gate 8 + C.3.2a-6 all falsified). Now a campaign-design decision:
   **bound supported depth to 0–N ≈ 5–6, format N…25 differently.**
   Owner's call on the late-game format; then CH3–FIN authors against
   a real structure.

After the gates, the bulk is **authoring** (CH3–FIN ≈ 15 facts + all
their evidence / templates / prose) plus **three endgame systems**
(competing hypotheses, the bespoke final expedition, the ending).
Phase D and the parked nav pieces are quality layers the arc could ship
without.

### Minimum path to "playable start to finish, even if rough"

```
pick the ending
      ↓
land C.3.2a-5 (or equivalent)
      ↓
author CH3–FIN facts + templates + prose
      ↓
CAMPAIGN_LENGTH = 25  +  5-chapter grouping
      ↓
a minimal final expedition (truth reveal + one ending choice)
```

Everything else is polish on that skeleton.
