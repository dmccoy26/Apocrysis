# Apocrysis — In-Game Commands

This documents the **current (v3) command set**. A new investigation-
focused set (`look`/`inspect`/`search`/`journal`/`remember`/`map`
sub-views) is designed but not yet built — see
`docs/ESCAPE_WORLD_DESIGN_ASSESSMENT.md`'s "Player cognition &
information architecture" section. This file will need updating once
that lands; don't treat it as describing the target design.

Every command below is typed at the `>` prompt during a game (or, in
the textual UI, triggered by the arrow keys / clicking, which just
submit the same commands under the hood). Commands are case-insensitive.
The list you actually see in-game is context-sensitive — e.g. `eat`
only appears once you have food, `f`/`fight` only appears when a
zombie is on your tile — but every command below always works if you
type it, whether or not it's currently listed.

## Movement

| Command | Aliases | Effect |
|---|---|---|
| `n` | `north`, ↑ | Move north |
| `s` | `south`, ↓ | Move south |
| `e` | `east`, →  | Move east |
| `w` | `west`, ←  | Move west |

Moving onto an unexplored tile may trigger a zombie encounter or let
you search for loot, depending on terrain and chance. Terrain affects
how much in-game time a move costs (plains/roads are fastest; forest,
water, and swamp are slower; mountains and rivers are impassable).

## Information

| Command | Aliases | Effect |
|---|---|---|
| `m` | `map` | Show the full map (same view as the side panel, plus the terrain legend) |
| `i` | `inventory` | List backpack contents: food, water, medicine, ammo, weapons, armor |
| `st` | `stats` | Show health, hunger, thirst, fatigue, core stats, equipped weapon/armor |
| `h` | `?` | Show the in-game help/command list |

## Survival

| Command | Aliases | Effect |
|---|---|---|
| `ea` | `eat` | Eat food: +hunger, +5 health. Requires food in backpack |
| `dr` | `drink` | Drink water: +thirst, +5 health. Requires water in backpack |
| `med` | `medicine` | Use medicine: +20 health. Requires medicine in backpack |
| `r` | `rest` | Recover fatigue (rate scales with Wisdom). Resting inside a building doubles the recovery rate |
| `a` | `auto` | Auto-play for a short stretch (moves randomly, eats/drinks/heals automatically as needed) |

Eating, drinking, and using medicine all also grant a small extra
fatigue-recovery bonus scaled by Wisdom.

## Combat

| Command | Aliases | Effect |
|---|---|---|
| `f` | `fight` | Fight the zombie on your current tile with your equipped weapon (or bare-handed if none equipped) |
| `p` | `punch` | Attack unarmed with your fists, regardless of what's equipped |

When a zombie is encountered while moving, you'll be asked "Do you
want to fight?" (`y`/`n`) — declining gives a 50% chance to flee (90%
if you're critically wounded mid-fight).

## Equipment

| Command | Aliases | Effect |
|---|---|---|
| `eq [name]` | `equip [name]` | Equip a weapon from your backpack by name |
| `drop [name]` | | Drop a weapon (salvages any remaining ammo back into your backpack) |
| `reload [name]` | `rl [name]` | Reload a ranged weapon to full, drawing from your backpack's ammo pool. Omit the name to reload your currently equipped weapon |
| `wr [name]` | `wear [name]` | Equip a piece of armor from your backpack by name (head/body/hands/feet — each slot is independent) |
| `da [name]` | `dropa [name]` | Drop a piece of armor |

## Crafting

| Command | Effect |
|---|---|
| `cr list` | `craft list` | List every recipe, including locked ones and what level unlocks them |
| `cr [recipe]` | `craft [recipe]` | Craft an item by recipe key (see table below) |

Crafted weapons have a chance to come out as a higher-quality
"Fine" or "Masterwork" variant (chance scales with Dexterity).

| Recipe key | Requires | Unlocks at level | Produces |
|---|---|---|---|
| `steel_sword` | 1 weapon, 2 food | 1 | Steel Sword (melee) |
| `heavy_bow` | 1 weapon, 3 ammo | 1 | Heavy Bow (ranged) |
| `combat_knife` | 1 weapon, 1 medicine | 1 | Combat Knife (melee) |
| `reinforced_blade` | 1 weapon, 1 medicine, 1 food | 4 | Reinforced Blade (melee) |
| `hunting_crossbow` | 1 weapon, 5 ammo, 1 food | 6 | Hunting Crossbow (ranged) |
| `repair_kit` | 2 medicine, 1 food | 8 | Fully restores your equipped weapon's and equipped armor's durability (produces no item) |
| `survivor_machete` | 2 weapons, 2 water | 9 | Survivor Machete (melee) |
| `military_carbine` | 1 weapon, 8 ammo, 2 medicine | 13 | Military Carbine (ranged) |
| `apex_blade` | 2 weapons, 3 medicine, 3 food | 18 | Apex Blade (melee) |

## Goals & tasks

| Command | Effect |
|---|---|
| `go` | Add a new goal (prompts for a title and type: `eat`/`drink`/`medicine`/`craft`/`kill`/`reach_town`) |
| `goals` | List your active and completed goals, with rewards |
| `complete` | Manually mark a goal complete by index (goals also auto-complete when you perform the matching action) |
| `ts` | List active tasks (dynamically generated exploration/combat/survival milestones) |
| `ct [idx]` | Complete a task by its listed index — tasks never auto-complete, this is the only way to claim their reward |

## Save & quit

| Command | Aliases | Effect |
|---|---|---|
| `sv` | `save` | Save your current game to a named slot |
| `ds` | `delete save` | Delete a save slot |
| `q` | `quit` | Quit (offers to save first) |
| `x` | `exit`, `exit game` | Exit immediately |

Beyond named save slots, your name/level/stats/backpack/gear are also
carried forward automatically between expeditions via a profile file —
no separate save step needed to keep campaign progress.

## Winning

Reach the Town Center *after* you've already set foot in a settlement
(any of its tiles) — arriving at the Town Center before that just
prints a warning that it's worth exploring first. A win advances your
campaign toward `CAMPAIGN_LENGTH` (10 expeditions); reaching it
triggers a distinct campaign-complete ending.
