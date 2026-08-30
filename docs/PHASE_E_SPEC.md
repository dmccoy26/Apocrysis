# Phase E — the endgame (spec)

Authored 2026-08-30. The World-1 `WorldFact` DAG is complete (23 facts,
CH1→FIN, `PHASE_A1_TRUTH.md`); `CAMPAIGN_LENGTH = 25`; the ending is
locked (Truth A, authored-canonical + one final binary choice). Phase E
is the three endgame **systems** that turn "you have established every
fact" into an ending. **Specs only — build in order after review.**

Sequence: **E.1 → E.2 → E.3**. E.1 is the smallest and E.3 depends on
both. Each ships behind its own tests, both suites green, balance
frozen (combat / hunger-thirst / encounter / loot / map growth /
survivor power — none of Phase E touches them).

---

## E.1 — Competing regional hypothesis + the wrong-commitment beat

### The problem

Today `WorldInvestigation` tracks each `WorldFact` as
KNOWN/SUSPECTED/UNKNOWN. That is an accreting list of true statements —
there is no moment where the player *believed something and was wrong*.
Candidate A's whole shape is a **wrong-assumptions ladder**: the player's
early reading is earned and mistaken, disproved in four stages. E.1 is
the system that makes that ladder a felt beat.

### Not a `knowledge.py` change

`knowledge.Hypothesis` is **per-escape-mystery** (the Escape Proof). The
regional hypothesis is **campaign-level**. E.1 lives in
`world_investigation.py` + a banner — `knowledge.py` is untouched for
World 1. (The roadmap's "`self.hypothesis` → a set" phrasing conflates
the two layers; the campaign layer is the one that needs this.)

### The four rungs (authored, `worlds/silence/`)

A new `REGIONAL_HYPOTHESES` tuple in `worlds/silence/truth.py` (or a
sibling `hypotheses.py`), each rung: `id`, `statement` (the belief, in
the player's voice), `held_until` (the milestone id whose discovery
disproves it), `corrected_to` (a one-line "what it actually was").

| # | the belief | falls when |
|---|---|---|
| 1 | "Everyone here was killed by the infected." | `DIS_ORGANISED` (M1) — the exodus was organised |
| 2 | "Everyone got out. The valley was evacuated." | `RESP_SEAL_SCHEDULED` (M5) — the corridors closed with people inside |
| 3 | "The military got them out — a rescue that ran out of time." | `RESP_ONE_COMMAND` (M6) — the same command opened and sealed the cordon |
| 4 | "The evacuation was a rescue that was betrayed at the end." | `RESP_THE_ORDER` (FIN) — the seal was signed before the first corridor opened. It was one plan. |

Rung 4's fall is the campaign's thesis landing; it happens in the
finale (E.2), not mid-game.

### Mechanics

- `WorldInvestigation` gains `current_hypothesis()` — the highest rung
  whose `held_until` milestone is **not** yet KNOWN (rung 1 if none
  disproved, rung 4 once M6 is known). Pure derivation from milestone
  state; no new persisted field (it falls out of the existing
  `_status` round-trip).
- When `mark_known` flips a milestone that is some rung's `held_until`,
  the resolution hook (already in `mystery_try_escape`) fires a
  **`kind="correction"`** `announce_event`: *"★ YOU HAD IT WRONG"* +
  the old belief struck through + `corrected_to`. One per rung, once.
- The `wi` screen (`ui_mixin.world_investigation_screen`) shows the
  current working theory as a line above the threads: *"What you think
  happened: …"* — so the belief is visible, which is what makes its
  fall land.

### Open decision (owner)

**Does committing to a wrong rung cost anything mechanical, or is it
purely a narrative beat?** Roadmap §10. **Recommendation: purely a
beat.** A mechanical penalty (a wasted expedition, a resource hit)
fights the elegiac tone and the "investigation hard, interface easy"
rule. The correction *is* the cost — the player reframes everything
they've seen. Ship it as narrative-only; revisit only if playtest says
it's weightless.

### Acceptance

- `current_hypothesis()` returns the right rung for every milestone
  subset; survives save/load.
- Exactly one correction banner per rung, in ladder order, even across
  deaths (milestone state is campaign-level).
- `wi` screen shows the working theory; no schema vocabulary leaks.
- A full-campaign sim (all 23 facts) fires rungs 1–3 mid-game and
  leaves rung 4 for the finale.

---

## E.2 — The bespoke final expedition

### What it is

Expedition 25 (`expeditions_completed == CAMPAIGN_LENGTH - 1`). Not the
random `build_mystery` roll — a **fixed, authored** expedition: the
regional command centre. Less procedural, realised from the player's
own `WorldInvestigation` state.

### Structure

- **Trigger.** `world_mixin.generate_map()` already branches on
  `target_fact = next_target()`. Add: when
  `expeditions_completed == CAMPAIGN_LENGTH - 1` **and** the finale
  facts (`RESP_THE_ORDER`, `RESP_THE_CHOICE`) are the only ones left,
  route to `build_finale()` instead of `build_mystery()`.
- **The map.** A dedicated archetype (`worlds/silence/`) — a walled
  compound at the valley head: the command centre building, a
  motor-pool, an antenna mast, and the road out past a manned (now
  empty) checkpoint. Still generated (seeded, connectivity-guaranteed
  via `MapGraph`) but from a **fixed archetype**, not the random
  settlement roll. Map size = the depth-25 cap (34²) but the layout is
  authored.
- **The investigation.** Three sites, each gated on what the player
  already established (not re-proved):
  1. **The command centre** → `RESP_THE_ORDER`. The seal order + the
     signature. If the player already knows `RESP_ONE_COMMAND`, the
     evidence here *names the date*; if not, it's the first they see
     the two orders together.
  2. **The antenna mast** → confirms `RESP_A_POST_TRANSMITS` is a live
     channel, not a loop — the transmitter still reaches out.
  3. **The consolidation point** (just outside the compound) →
     `RESP_PEOPLE_ALIVE` becomes present-tense: there are people
     *there, now*, and they can see you coming.
- **The escape.** There is no mountain gap here — the way out is the
  checkpoint road (`escape_kind = "checkpoint"`, a minimal new value;
  the gap-carve is skipped, the road is the escape tile). Reaching it
  is not the win; the **choice** is (E.3).
- **Survivability.** Uses the E.1-era `depth_supply_bonus(24)` floor
  (+20 food/water) — the finale is long but the contract covers it.
  No combat changes; the compound has the same encounter rate.

### What E.2 does NOT do

- No new mechanic family. No `world_conditions` (that's Phase D). No
  NPC behaviour — the settlement people are a static group + a
  dialogue-free arrival scene.
- Does not re-litigate facts the player already established — the
  finale *converges* the investigation, it doesn't restart it.

### Acceptance

- Expedition 25 always routes to the finale; expeditions 1–24
  unchanged.
- The finale is reachable and completable from any valid
  `WorldInvestigation` state that has all CH1–CH5 facts KNOWN.
- If the player somehow reaches 25 with gaps (bot edge case), the
  finale still resolves — missing facts are surfaced as evidence in
  the compound rather than blocking.
- Seed-deterministic; `MapGraph` connectivity holds; both suites green.

---

## E.3 — The ending choice

### What it is

The single authored binary choice, acting on `RESP_THE_CHOICE`. Lands
at the checkpoint road once `RESP_THE_ORDER` and `RESP_PEOPLE_ALIVE`
are both KNOWN (both established in E.2).

### The choice

> The command centre transmitter still reaches past the cordon.

- **BROADCAST** — send the seal order and the signature out. The truth
  of Protocol Seven leaves the valley. The people who held the
  consolidation point lose their silence: the cordon now knows exactly
  where they are.
- **PROTECT** — walk out without transmitting. Protocol Seven stays
  filed as a success. The settlement keeps its silence and its chance.

Neither is "correct". Both endings are authored (~2 short screens
each): what the player did, what it cost, what it bought. The
`campaign_retrospective` (already exists) runs after, now branch-aware.

### Mechanics

- A `mystery`-free choice prompt at the checkpoint tile (reuse the
  `io.ask` / a numbered prompt like the equip flow — **not** a
  free-text parse).
- `finish_expedition` at expedition 25 → `finish_campaign(choice)`
  instead of the generic campaign-complete text. Records the choice on
  the campaign profile (`campaign.ending` = `"broadcast"` |
  `"protect"`) so a re-launch shows the resolved state.
- `campaign.py` gains `ENDINGS = {"broadcast": (...), "protect": (...)}`
  and `campaign_ending(choice, used_mechanisms)`.
- Hardcore vs normal: no difference — the choice is the same, the
  campaign is over either way.

### Open decisions (owner)

1. **Is the wider world reachable enough for BROADCAST to *mean*
   something?** Candidate A says "the cordon still has ears". Minimum:
   the transmission demonstrably gets out (an acknowledgement, or a
   later-launch note that something changed). **Recommendation:** the
   broadcast is received — a short, cold acknowledgement from outside —
   so the choice is a real act, not a shout into a void.
2. **Cause specifics** (research vs agricultural containment station) —
   needs a call before the command-centre evidence text is written.
   **Recommendation: a regional bio-containment research station** —
   fits "a contained neurological pathogen … during a transfer".

### Acceptance

- The choice fires exactly once, at expedition 25, after E.2's facts.
- Both branches produce a distinct, authored ending screen +
  branch-aware retrospective.
- `campaign.ending` persists; a re-launched completed campaign shows
  the resolved ending, doesn't re-prompt.
- No free-text parsing; the prompt is numbered/keyed.
- Both suites green.

---

## Sequencing + Atlas

```
E.1 (world_investigation.py + a banner + wi-screen line + REGIONAL_HYPOTHESES)
      ↓
E.2 (build_finale() + a fixed archetype + finale routing in generate_map)
      ↓
E.3 (choice prompt + finish_campaign + campaign.py ENDINGS)  ← needs E.1's
                                                                rung 4 + E.2's sites
```

`REGIONAL_HYPOTHESES` / `ENDINGS` are self-contained authored data —
the shape Atlas has succeeded on (`truth.py`, `lore.py`). The wiring
(`world_investigation.py` method, `generate_map` branch, `world_mixin`
finale, `ui_mixin` screen line, `tui` banner) is large-file /
cross-module — hand-write. Log per `ATLAS_CAPABILITY_LOG.md`.

---

*Spec only. Build E.1 → E.2 → E.3 after owner review. Balance frozen.
No NPC behaviour, no world_conditions, no knowledge.py change for
World 1.*
