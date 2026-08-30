# Apocrysis — In-Game Commands

The current command set (v4 investigation mechanics + the Phase A–E
world-investigation spine and the full World-1 arc). Every command
below is typed at the `>` prompt during a game (or, in
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
| `m` | `map` | Show the full map — a plain grid of terrain glyphs, no border or coordinate ruler (both removed on player feedback). A lead you've learned about shows as a `!` marker; an opened route as `+` |
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
| `wi` | `investigation` | The world-investigation screen: what the campaign has worked out about the region so far, thread by thread. Campaign-level — it survives across expeditions and deaths, unlike everything else in a run |
| `inspect <thing>` | `ins <thing>` | What you actually know about one thing: *Observed* / *Known* / *Suspected* / nothing yet. Try `inspect the way out` |
| `clear` | `open` | Get past the obstacle on the escape route, once you have what it takes (walking into it with the item also works) |
| `escape` | | Leave from a distance, once your hypothesis is *confirmed* and the way is open. **Not needed if you walk to the way out itself** — reaching the cleared, confirmed escape tile ends the expedition automatically |
| `log` | | Toggle the plain-text session transcript (`apocrysis_playlog_<timestamp>.txt`). Logging is **on by default** for interactive play — one file per session, each expedition appended; launch with `--no-log` to turn it off. Free action. |

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

When a zombie is encountered while moving, an encounter card shows the
threat tier, your fight% / escape% with the equipped weapon, and a
weapon verdict, then prompts `[f] fight   [e] escape   [w] weapons`
(`[w]` opens a per-weapon fight-chance window and costs no turn).
Choosing escape is a ~50% flee roll; if it fails you fight anyway. The
card changes no combat math — it draws its numbers from a private
Monte-Carlo of the real round loop. (`--classic` and non-interactive
runs fall back to the old `Do you want to fight? (y/n)` prompt.)

## Equipment

| Command | Aliases | Effect |
|---|---|---|
| `eq [name/N]` | `equip [name/N]` | Equip a weapon by name **or by the slot number shown in the pack list** (`eq 3`). A bare `3` at the prompt also works |
| `drop [name/N]` | | Drop a weapon by name or slot number (salvages any remaining ammo back into your backpack) |
| `reload [name]` | `rl [name]` | Reload a ranged weapon to full, drawing from your backpack's ammo pool. Omit the name to reload your currently equipped weapon |
| `wr [name/N]` | `wear [name/N]` | Equip armor by name or slot number (`wr W2`; a bare `W2` also works). head/body/hands/feet — each slot is independent |
| `da [name/N]` | `dropa [name/N]` | Drop a piece of armor by name or slot number |

The pack list numbers each line — `[3]` for one weapon, `[5-7]` for a
run of three identical ones (any of them answers `eq 5`).

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
evidence pointed you to), and reach the route itself — arriving there
ends the expedition (or `escape` from a distance once it's confirmed
and open).

The Town Center is *not* the way out — under a generated mystery it's
just the most information-dense location on the map. (A "reach the
Town Center after exploring a settlement" fallback still exists for a
degenerate map with no mystery, but the generator now regenerates the
map until a mystery fits, so in practice every expedition has one.)

A win advances your campaign toward `CAMPAIGN_LENGTH` (25 expeditions —
the full World-1 arc, "The Cordon"). The zombie difficulty curve
ramps over the first `DIFFICULTY_RAMP_LENGTH` (10) expeditions and
then holds. Expedition 25 is a bespoke finale with one authored binary
choice; completing it triggers a branch-aware campaign retrospective.
