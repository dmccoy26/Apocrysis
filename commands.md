# Apocrysis — In-Game Commands

The v4 command set. Every command below is typed at the `>` prompt during a game (or, in
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
| `m` | `map` | Show the full map. Rows are lettered down the side, columns numbered across the top — the top-left tile is `a1`, one right `a2`, one down `b1` |
| `i` | `inventory` | List backpack contents: food, water, medicine, ammo, weapons, armor |
| `st` | `stats` | Show health, hunger, thirst, fatigue, core stats, equipped weapon/armor |
| `h` | `?` | Show the in-game help/command list |

## Investigation (v4)

| Command | Aliases | Effect |
|---|---|---|
| `look` | `l` | Take stock of where you're standing. Some things you notice just by being there |
| `search` | `sr` | Go through the place properly — records, notes, the things that aren't obvious |
| `journal` | `j` | Everything you've found, and what it tells you. Your memory, not a quest list |
| `remember` | `rem` | Think it over — a synthesis of where your understanding stands right now |
| `inspect <thing>` | `ins <thing>` | What you actually know about one thing: *Observed* / *Known* / *Suspected* / nothing yet. Try `inspect the way out` |
| `clear` | `open` | Get past the obstacle on the escape route, once you have what it takes (walking into it with the item also works) |
| `escape` | | Leave. Only works once your hypothesis is *confirmed* and the way is open — and only from the actual route out |
| `log` | | Start / stop writing a plain-text transcript of this session to `apocrysis_playlog_<timestamp>.txt` (also `python3 apocrysis.py --log`). Free action. |

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

Removed in v4. The goal/task checklist is replaced by the investigation
interface (`journal` / `remember` / `inspect`). The `go` / `goals` /
`complete` / `ts` / `ct` commands still parse but operate on an empty
list.

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

Work out this expedition's way out of the valley and take it. Concretely:
find enough evidence that your hypothesis about the route becomes
*confirmed* (check with `remember` or `inspect the way out`), get past
whatever blocks that route (`clear` / `open`, with the item the
evidence pointed you to), reach the route itself, and `escape`.

The Town Center is *not* the way out — under a generated mystery it's
just the most information-dense location on the map. (On the rare
degenerate map with no mystery, reaching the Town Center after
exploring a settlement still wins, as a fallback.)

A win advances your campaign toward `CAMPAIGN_LENGTH` (10 expeditions);
the final one triggers a campaign-complete retrospective of the routes
you found.
