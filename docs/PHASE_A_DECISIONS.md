# Phase A — locked decisions (2026-08-29)

Ratifies the `APOCRYSIS_ROADMAP.md` §10 open decisions needed to start
Phase A. Decided by the project owner this session.

| § decision | lock |
|---|---|
| **World 1 truth** (`WORLD_TRUTH_CANDIDATES.md` A/B/C) | **A — "The Cordon."** Real evacuation + a seal scheduled from the start that left people inside. Institutional betrayal; fits the current elegiac prose; forces the `Deduction`/corroboration half of `knowledge.py` to do work. |
| **game vs engine / the `World` seam** (STORY_ENGINE §1B.1 / §1B.14) | **Build behind a thin `World` seam now.** `worlds/silence/` holds encounter table, tile vocabulary, prose voice, `WorldFact` DAG, ending logic; the engine takes a `World`. Do it even if there is only ever one world. |
| **causal model in world 1** (STORY_ENGINE §1E) | **Deferred. World 1 is a plain `WorldFact` DAG + `DiscoveryTemplate`s.** No events→consequences→traces model yet. Smallest Phase A. Revisit for world 2 or after Phase A ships. |
| **chapter count / maps-per-chapter** | 5 chapters + finale, ~25 expeditions (roadmap §4). Phase A authors **CH1 + CH2 only** (~10 facts, ~3 milestones). |
| **what carries on death** (STORY_ENGINE §1D) | Direction confirmed (three persistence tiers: Knowledge always / Narrative selected / Mechanical never), but this is a **Phase B** lock — not authored yet. |
| **region stability window** | Draft stands: region stable for a whole campaign, regenerates only on a new campaign. Phase B concern. |
| **ending shape** (§2.6) | Leaning locked for structure: truth at the command centre **+** a settlement that held as the final act. Content is Phase E. |

## Storage / database — decided: NOT now (2026-08-29)

- **No database in Phase A–B.** World content (facts, evidence
  definitions, mechanisms, encounters, history/truth) stays ordinary
  Python data structures behind the `World` seam.
- The existing persistence boundary (`save_game`/`load_game` +
  `save_profile`/`apply_profile`) is adequate and stays.
- **SQLite-backed `WorldStore`** is a **Phase C+** consideration —
  revisit once World 1's persistent truth/history/state has a known
  shape, so it's an architectural *consequence*, not a guess. SQLite
  (embedded, transactional, single-file, no server) is the candidate,
  not a client/server DB. It would let the engine *operate on* the
  world rather than *be* the world's storage; and a structured world
  state is also the substrate a future generated world would need.
- **ChromaDB / vector store**: later still, and **only as a semantic
  index over an authoritative store**, never as the source of truth.
  Use "SQLite says the player knows X; ChromaDB helps find what's
  *relevant* to consider" — not "the vector DB says the player knows X".
- A.0 guardrail: Atlas must not introduce any storage abstraction.

## Not yet decided (still open, don't need them for Phase A)

- ending: authored-canonical vs player-choice
- wrong-hypothesis commitment cost (whole expedition vs a correction beat) — Phase E
- can the player broadcast outward past the cordon — Phase E
- Survivor Knowledge effect count / strength cap — Phase B

## Vocabulary rename (do first, roadmap §10 "early regardless")

`expeditions_completed` / `CAMPAIGN_LENGTH` and the ad-hoc "expedition N"
framing → a real **Campaign → Chapter → Expedition** vocabulary, with
**World Investigation** as the persistent axis. Mechanical rename, no
behaviour change, lands before the seam so the seam is built in the new
vocabulary.
