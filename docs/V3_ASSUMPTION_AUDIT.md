# V3-assumption audit (Stage 1.1)

2026-08-28. Every V3 mechanic that assumes something the v4 premise
breaks, classified KEEP / MODIFY / DELETE / DISABLE. v4 is a premise
change (survival game → investigation game that uses survival as
pressure), not v3 + an investigation system bolted on.

| # | V3 assumption | Where | Verdict | Notes |
|---|---|---|---|---|
| 1 | **There is a known objective the player is heading toward** | `game.py` `self.goals` (6 hard-coded Goals incl. "Reach the Town Center"); `objectives_mixin` | **DELETE** | The whole point of v4 is the player doesn't know the objective. The Goal list is replaced by the knowledge layer (`journal`/`remember`). `go`/`goals`/`complete` commands go. Stage 5.4 (`87dc4cf0`). |
| 2 | **Town Center = the win tile** | `world_mixin.move_and_search()` `content == 'T'` branch; `self.won` | **MODIFY** | Town Center becomes an information-rich location; the win condition becomes "hypothesis Confirmed + escape action at the escape location". Stage 4.3. |
| 3 | **Combat is the primary activity** | `combat_mixin`; 10%-of-tiles zombie placement; `encounter_chance` 0.3/0.5 per move | **MODIFY (down-weight)** | Combat stays as *pressure*, not the main loop. Encounter density and the "every move rolls an encounter" model get retuned so a player can investigate for 20-30 turns without it dominating. Not deleted - the slice proved investigation-in-isolation works; now survival comes back *tuned*, per the design doc. Stage 2A / balance pass. |
| 4 | **Exploration = finding settlements** | `settlement_explored` flag; `_generate_settlement()`; map item reveals the town | **MODIFY** | Exploration = building a mental model of a place. Settlements become one kind of evidence-bearing location among many (mine, dam, marina...). `settlement_explored` as a single global bool is already flagged as the Q6 core fix (`4b0fafcc`, folded into Stage 4.3). |
| 5 | **Loot is a primary reward** | `find_loot()` global pool; `LOOT_WEAPON_TABLE`/`ARMOR_TABLE` `min_expedition` bands | **MODIFY** | Loot splits into 5 categories (survival / equipment / tools / evidence / context), evidence routes to the knowledge system not the backpack, and selection becomes location-contextual not expedition-tier-gated. Stage 2A.6 + Stage 2D + Stage 4. |
| 6 | **Progression (level/XP/bigger map) is the reason to continue** | `game.py` level→map_size; `combat_mixin.level_up()`; `MAP_GROWTH_PER_LEVEL` | **MODIFY** | Later expeditions get *conceptually* harder (richer mystery), not *physically* bigger. Map size gets a hard ceiling (Stage 2A.1). XP/level stay as a minor combat-competence axis, not the point. |
| 7 | **The player can use global map knowledge** | fog-of-war already gates this correctly for terrain; `town_known` overrides it for the town | **KEEP (already correct) / MODIFY the one exception** | Fog-of-war is already the right model. The `town_known` map-item override becomes "a found map reveals *geography*, not the answer" (Q3, `8f9ec034`, pairs with Stage 2C.6). |
| 8 | **The goal/task system represents player intent** | `objectives_mixin` dynamic tasks ("Scout the Wastes", "Hunt the Infected") | **DELETE** | Player intent in v4 is expressed through investigation, not a task list. The dynamic-task generator is already `slice_mode`-disabled; Stage 5.4 removes it for the real game too. |
| 9 | **Every map is a full rectangle the player spawns into** | `generate_map()` rectangular grid | **KEEP through Phase A-C, MODIFY at Phase D** | Mountain-boundary Phases 1-3 progressively turn the rectangle edge into real world-edge content; the playable shape only goes irregular at Phase D. |
| 10 | **Zombies are placed once at generation and never change** | `generate_map()` one-shot placement; no tile clears on kill | **MODIFY** | Killed zombies clear the tile (`93edaf83`, Stage 2B.1); ecology keyed to zone (`1255e24e`). Full ecological simulation stays out of scope (design doc "Zombies" open questions). |
| 11 | **Dropped items vanish** | `actions_mixin` `drop_weapon()`/`drop_armor()` delete with no world placement | **MODIFY** | Dropped items persist as world objects (`6c9a4ca6`, Stage 2B.2) - the same trust principle as evidence persistence. |
| 12 | **Player identity is fixed (husband / Kitchen Knife)** | `actions_mixin.initialize_player(STARTER_CLASS_NAME)` | **MODIFY** | Randomised from the existing class pool at spawn (`b31aac00`, Stage 2A.5). Reverses an earlier v4-design decision - noted in the design doc. |

## Sequencing implication

Nothing here is a Stage 1 code change - it's the classification that
tells later stages what they're doing. The two **DELETE**s (#1, #8,
the goal/task system) are a single Stage 5.4 change and should not be
touched earlier: `journal`/`remember` (Stage 2C) need to be proven as
the replacement *before* the thing they replace is removed.

The **MODIFY**s are already distributed across Stages 2-4 in the build
order. This audit just makes explicit that they are *replacements of a
broken assumption*, not additive features - which matters for how
aggressively to cut the old code path when each lands.
