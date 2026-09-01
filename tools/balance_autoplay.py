#!/usr/bin/env python3
"""
Headless autoplay harness for balance-testing Apocrysis.

Plays full games end-to-end with a scripted heuristic bot - no human,
no LLM - so "is X too generous / too easy" has real numbers behind it
instead of one manual playthrough's gut feel. The bot answers every
io.ask()/ask_yes_no() the same way a real player would decide: eat/
drink/medicine when low, equip the strongest working weapon, reload
before it runs dry, drop excess duplicate weapons (the feature added
alongside this tool), occasionally craft, always fight (never flee),
and otherwise run the v4 investigation: walk to each generated
mystery site, `search` it, pick up the requirement item, clear the
obstacle, reach the escape route and `escape`. (On a rare degenerate
map with no mystery it falls back to walking to the Town Center.)

Run:
    python3 tools/balance_autoplay.py
    python3 tools/balance_autoplay.py --games 30 --max-turns 500
    python3 tools/balance_autoplay.py --level 5 --seed 42 --verbose
    python3 tools/balance_autoplay.py --expeditions-completed 6 --games 200

Updated for the map/player/campaign-level split: map size, obstacle
density, zombie composition/elites, and loot banding (both weapons
and armor) are now driven by expeditions_completed, NOT player level
- --level alone (the only axis this harness varied before that split)
now only affects starting combat stats, against a map/loot pool that
doesn't change with it at all. Pass --expeditions-completed to
actually vary map/loot difficulty; the two are independent by design,
so testing a level/expeditions combination that wouldn't arise from
normal single-campaign play (e.g. high level, expeditions_completed=0)
is a deliberate, valid thing to do here, not a harness bug - just be
aware of which axis you're testing.

The reverse combination has its own caveat: every game here starts a
completely fresh, gearless BalanceBot (empty backpack, starter
weapon only) at whatever --expeditions-completed you pass. In real
play, reaching expedition 9 means having accumulated loot/crafted
gear getting there - a level-15 character with zero gear thrown
straight at expedition-9 zombie composition/elites (confirmed live:
100% death rate across 30 games, several within the very first
encounter) is testing "zero-gear player vs late-game difficulty," not
a realistic point in a real campaign either. High --expeditions-
completed values are most meaningful paired with a --level roughly
consistent with having actually played that many expeditions.
"""

import argparse
import os
import random
import re
import statistics
import sys
from collections import Counter, defaultdict, deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.constants import CAMPAIGN_LENGTH, IMPASSABLE_TERRAIN, MINUTES_PER_DAY
from src.escape import MECHANISMS
from src.game import Apocrysis
from src.items import RangedWeapon

# Lines emitted by combat_mixin.py's per-hit messages - see
# take_damage() (player, always carries "Its current health is") vs
# the inline zombie-damage self.io.say() call (never does) for why
# that suffix is what disambiguates who was actually hit, not the
# name in the line (a zombie's name text can't be told apart from a
# custom player name by pattern alone).
_ZOMBIE_HIT_RE = re.compile(r"^The .+ takes (\d+) damage\.$")
_PLAYER_HIT_RE = re.compile(r"^The .+ takes (\d+) damage\. Its current health is (-?\d+)\.$")
_ENCOUNTER_RE = re.compile(r"^Encountered a (.+)! What will you do\?$")
_ZOMBIE_DEFEATED_RE = re.compile(r"^The (.+) has been defeated!$")
_OBTAINED_WEAPON_RE = re.compile(r"^You obtained a (.+)\.$")
# Distinct from weapon's "You obtained a {name}." - find_loot()'s
# armor branch omits the article: "You obtained {name}." (world_mixin.
# py). The old single `_OBTAINED_RE` never matched armor at all, so
# every armor pickup across every prior run of this harness was
# silently uncounted, not just unreported.
_OBTAINED_ARMOR_RE = re.compile(r"^You obtained (?!a )(.+)\.$")
_CRAFTED_RE = re.compile(r"^Crafted a (.+)!$")
_FLASHLIGHT_FOUND_RE = re.compile(r"^You found a working flashlight!")
_CAMPAIGN_COMPLETE_RE = re.compile(r"CAMPAIGN COMPLETE!")

# Tier 1 telemetry: death-cause inference. Grepping "health -=" /
# "self.health -=" across src/ turns up exactly three code paths that
# ever reduce player.health: a direct zombie hit (combat_mixin.py's
# take_damage(), always paired with the "takes N damage..." message
# _PLAYER_HIT_RE already matches above), a Bleeding/Poison status tick
# (also only ever applied mid-fight, combat_mixin.py's
# encounter_zombie()), a cold-water terrain chance (world_mixin.py's
# move_and_search()), and - since 2026-08-28 - a hunger/thirst-at-zero
# drain (game.py's _apply_decay(), 2 HP/turn each, announced with
# "The ... is wearing you down.").
_COLD_WATER_RE = re.compile(r"^The cold water chills you\. You lost some health\.$")
_STATUS_DAMAGE_RE = re.compile(r"^You are affected by (Bleeding|Poison)! Lost \d+ health\.$")
_STARVE_RE = re.compile(r"^The (hunger|thirst|hunger and thirst) is wearing you down\.")
_BUILDING_ENTER_RE = re.compile(r"^You enter a building\. It's a safe zone\.$")


class Metrics:
    """One playthrough's worth of counters, filled in as the bot plays."""

    def __init__(self):
        self.turns = 0
        self.outcome = None  # 'won' | 'died' | 'timeout'
        self.final_level = 1
        self.final_day = 1
        self.final_expeditions_completed = 0
        self.min_health = 100
        self.health_samples = []
        self.hits_dealt = []          # (level, damage) per hit landed on a zombie
        self.hits_taken = []          # (level, damage) per hit landed on the player
        self.crits = 0
        self.fights = 0
        self.zombies_defeated = 0
        self.weapons_looted = []
        self.armor_looted = []
        self.crafted = []
        self.drops_issued = 0
        self.weapon_drops_issued = 0
        self.reloads_issued = 0
        self.equips_issued = 0
        self.armor_equips_issued = 0
        self.flashlights_found = 0
        self.campaign_completions = 0
        self.max_weapon_damage_by_expedition = {}
        self.max_armor_reduction_by_expedition = {}
        self._current_zombie_name = None

        # --- Tier 1 additions ---
        self.starting_level = 1                # set by play_one_game before the loop runs
        self.xp_gained = 0                      # via a wrapped award_xp - see play_one_game
        self.max_distance_from_spawn = 0
        self.day_phase_counts = Counter()
        self.visibility_samples = []
        self.has_flashlight_at_end = False
        self.reached_night = False
        self.mechanism = None                    # v4: this expedition's escape mechanism
        self.mystery_solved = False               # v4: obstacle opened + hypothesis confirmed (even if the bot later died)
        self.searches_issued = 0                 # v4: `search` commands the bot issued
        self.spawn_to_objective_distance = None   # shortest-path steps from spawn to the escape tile (or town center) at game end
        self.tiles_moved = 0                    # count of turns where current_position actually changed
        self.terrain_counts = Counter()         # terrain type of each tile moved onto during the game
        self.final_visited_count = 0
        self.final_map_tiles = 0
        self.map_size = 0
        self.final_settlement_explored = False
        self.buildings_entered = 0              # "safe zone" building-tile entries; can repeat on revisit
        self.settlements_on_map = 0
        self.settlements_discovered = 0
        # Town-Center-specific telemetry (real vs decoy distinction blocked on Q6)
        self.town_center_discovered = False
        self.town_center_reached = False
        self.food_acquired = 0
        self.food_consumed = 0
        self.water_acquired = 0
        self.water_consumed = 0
        self.medicine_acquired = 0
        self.medicine_consumed = 0
        self.ammo_acquired = 0
        self.ammo_fired = 0
        self.final_food = 0
        self.final_water = 0
        self.final_medicine = 0
        self.final_ammo = 0
        self.final_weapon_count = 0
        self.final_armor_count = 0
        self.death_cause = None                 # only set when outcome == 'died'
        self._last_damage_event = None          # internal, feeds death_cause

    def observe_line(self, text):
        m = _ENCOUNTER_RE.match(text)
        if m:
            self._current_zombie_name = m.group(1)
            self.fights += 1
            return

        if text == "Critical Hit!":
            self.crits += 1
            return

        m = _PLAYER_HIT_RE.match(text)
        if m:
            self.hits_taken.append((self.final_level, int(m.group(1))))
            self._last_damage_event = "zombie combat"
            return

        if _COLD_WATER_RE.match(text):
            self._last_damage_event = "environmental (cold water)"
            return

        if _STARVE_RE.match(text):
            self._last_damage_event = "resource attrition (hunger/thirst)"
            return

        if _STATUS_DAMAGE_RE.match(text):
            # Bleeding/Poison are only ever applied mid-fight (combat_mixin.py) -
            # attributed to zombie combat, not a separate cause.
            self._last_damage_event = "zombie combat"
            return

        if _BUILDING_ENTER_RE.match(text):
            self.buildings_entered += 1
            return

        m = _ZOMBIE_HIT_RE.match(text)
        if m:
            self.hits_dealt.append((self.final_level, int(m.group(1))))
            return

        m = _ZOMBIE_DEFEATED_RE.match(text)
        if m and m.group(1) == self._current_zombie_name:
            self.zombies_defeated += 1
            self._current_zombie_name = None
            return

        m = _OBTAINED_WEAPON_RE.match(text)
        if m:
            self.weapons_looted.append(m.group(1))
            return

        m = _OBTAINED_ARMOR_RE.match(text)
        if m:
            self.armor_looted.append(m.group(1))
            return

        m = _CRAFTED_RE.match(text)
        if m:
            self.crafted.append(m.group(1))
            return

        if _FLASHLIGHT_FOUND_RE.match(text):
            self.flashlights_found += 1
            return

        if _CAMPAIGN_COMPLETE_RE.search(text):
            self.campaign_completions += 1
            return


def _weapon_power(weapon):
    """(is_usable_right_now, damage) - sorts working weapons above
    broken/out-of-ammo ones, then by raw damage."""
    if weapon is None:
        return (False, -1)
    usable = weapon.durability > 0
    if isinstance(weapon, RangedWeapon):
        usable = usable and weapon.ammo > 0
    return (usable, weapon.damage)


def _armor_power(armor):
    """(is_usable_right_now, damage_reduction) - equipment-slot
    investigation's Armor, same shape as _weapon_power() above."""
    if armor is None:
        return (False, -1)
    return (armor.durability > 0, armor.damage_reduction)


def _settlement_regions(player):
    """4-connected components of 'town'-terrain tiles - each is one
    settlement's footprint (the real Town Center or a decoy, see
    world_mixin.py's generate_map()/multiple-settlements investigation).
    Used only for the balance report's discovery numbers below, not
    gameplay. Known gap: a tile a zombie was placed on (generate_map())
    never had a 'terrain' dict to begin with once occupied - excluded
    from every region by the isinstance(cell, dict) guard below - but
    zombies are never placed on town tiles in the first place, so this
    never actually loses a town tile in practice."""
    seen = set()
    regions = []
    for y in range(player.map_size):
        for x in range(player.map_size):
            if (x, y) in seen:
                continue
            cell = player.map[y][x]
            if not (isinstance(cell, dict) and cell.get('terrain') == 'town'):
                continue
            region = set()
            stack = [(x, y)]
            while stack:
                cx, cy = stack.pop()
                if (cx, cy) in region:
                    continue
                region.add((cx, cy))
                for dx, dy in ((0, -1), (0, 1), (1, 0), (-1, 0)):
                    nx, ny = cx + dx, cy + dy
                    if not (0 <= nx < player.map_size and 0 <= ny < player.map_size):
                        continue
                    if (nx, ny) in region:
                        continue
                    ncell = player.map[ny][nx]
                    if isinstance(ncell, dict) and ncell.get('terrain') == 'town':
                        stack.append((nx, ny))
            regions.append(region)
            seen |= region
    return regions


def _find_town_center(player):
    # Investigation note: a fresh 200-game batch run (--seed 7, default level 1/expeditions_completed=0) shows median game length still very short (~9.4 unique tiles visited, ~4.2% of a 225-tile map explored before outcome). IMPORTANT CAVEAT: this number is NOT yet a reliable measurement of real game pacing because _find_town_center() (this same function) currently scans player.map directly for the Town Center regardless of fog-of-war/visibility - the bot has known the exact winning location since turn one in every run, so it has essentially never had to explore to find it. That bot-omniscience issue is tracked as a separate, not-yet-fixed item. Until that lands and this measurement is re-run with a bot that genuinely explores, this 4% figure should be treated as an upper bound on how much exploration COULD be needed, not a confirmed finding about whether expeditions are 'too short' by design.
    for y, row in enumerate(player.map):
        for x, tile in enumerate(row):
            if isinstance(tile, dict) and tile.get('terrain') == 'town' and tile.get('content') == 'T':
                return (x, y)
    return None


def _bfs_path(player, start, goal):
    """Shortest cardinal-move path from start to goal as a list of
    'n'/'s'/'e'/'w' steps, using the same passability rule as the
    game's own connectivity guarantee (world_mixin._bfs_reachable)."""
    if start == goal:
        return []

    deltas = {(0, -1): 'n', (0, 1): 's', (1, 0): 'e', (-1, 0): 'w'}
    came_from = {start: None}
    queue = deque([start])

    while queue:
        x, y = queue.popleft()
        for (dx, dy), direction in deltas.items():
            nx, ny = x + dx, y + dy
            if not (0 <= nx < player.map_size and 0 <= ny < player.map_size):
                continue
            if (nx, ny) in came_from:
                continue
            cell = player.map[ny][nx]
            terrain = cell.get('terrain') if isinstance(cell, dict) else None
            if terrain in IMPASSABLE_TERRAIN:
                continue
            came_from[(nx, ny)] = (x, y, direction)
            if (nx, ny) == goal:
                queue.clear()
                break
            queue.append((nx, ny))

    if goal not in came_from:
        return None

    steps = []
    node = goal
    while came_from[node] is not None:
        x, y, direction = came_from[node]
        steps.append(direction)
        node = (x, y)
    steps.reverse()
    return steps


class BotIO:
    """Drop-in replacement for ConsoleIO/TextualIO that plays the game
    itself instead of asking a human. See io_console.py for the
    interface every mixin actually calls through (say/ask/ask_yes_no)."""

    renders_natively = True  # suppress the classic per-turn ASCII block

    def __init__(self, max_turns, verbose=False):
        self.player = None  # set after construction, chicken/egg with Apocrysis(io=...)
        self.max_turns = max_turns
        self.verbose = verbose
        self.metrics = Metrics()
        self._path = None
        self._path_index = 0
        self._town_center = None

        # v4: investigation-aware bot state. Which mystery sites the
        # bot has already searched, and its current navigation target.
        self._m_searched = set()
        self._m_target = None
        self._m_path = None
        self._m_path_i = 0

        # Tier 1 telemetry state - see the sampling block at the top
        # of _choose_command() for what each of these feeds.
        self._spawn = None
        self._last_position = None
        self._last_weapon_id = None
        self._last_weapon_ammo = None
        self._last_food = None
        self._last_water = None
        self._last_medicine = None
        self._last_ammo = None

    def say(self, *args, **kwargs):
        text = " ".join(str(a) for a in args)
        if self.verbose:
            print(text)
        for line in text.splitlines():
            self.metrics.observe_line(line.strip())

    def ask(self, prompt=""):
        if prompt == "Press Enter to continue...":
            return ""
        return self._choose_command()

    def ask_yes_no(self, prompt):
        # Always fight - fleeing is a distinct game system worth its
        # own pass, but sampling as many hits as possible per game is
        # what this harness needs for damage-dealt/taken numbers.
        return True

    # ------------------------------------------------------------
    # Policy
    # ------------------------------------------------------------

    def _choose_command(self):
        p = self.player
        self.metrics.turns += 1
        self.metrics.day_phase_counts[p.day_phase] += 1
        self.metrics.visibility_samples.append(p.visibility_radius)
        if p.is_night: self.metrics.reached_night = True
        self.metrics.final_level = p.level
        self.metrics.final_day = p.day
        self.metrics.final_expeditions_completed = p.expeditions_completed
        self.metrics.min_health = min(self.metrics.min_health, p.health)
        self.metrics.health_samples.append(p.health)
        exp = p.expeditions_completed
        self.metrics.max_weapon_damage_by_expedition[exp] = max(
            self.metrics.max_weapon_damage_by_expedition.get(exp, 0),
            _weapon_power(p.equipped_weapon)[1],
            max((w.damage for w in p.backpack.weapons), default=0),
        )
        self.metrics.max_armor_reduction_by_expedition[exp] = max(
            self.metrics.max_armor_reduction_by_expedition.get(exp, 0),
            max((_armor_power(a)[1] for a in p.equipped_armor.values()), default=0),
            max((a.damage_reduction for a in p.backpack.armor), default=0),
        )

        # --- Tier 1 telemetry: state sampled every turn, same pattern
        # as final_level/min_health above ---
        if self._spawn is None:
            self._spawn = p.current_position
        dist_from_spawn = abs(p.current_position[0] - self._spawn[0]) + abs(p.current_position[1] - self._spawn[1])
        self.metrics.max_distance_from_spawn = max(self.metrics.max_distance_from_spawn, dist_from_spawn)
        if self._last_position is not None and p.current_position != self._last_position:
            self.metrics.tiles_moved += 1
            # Record terrain of the tile we just moved onto (observed at start of next turn)
            cell = p.map[p.current_position[1]][p.current_position[0]]
            terrain = cell.get('terrain') if isinstance(cell, dict) else 'unknown'
            self.metrics.terrain_counts[terrain] += 1
        self._last_position = p.current_position

        # Ammo fired: use() (items.py) is the ONLY code path that ever
        # decrements a weapon's own .ammo (combat_mixin.py's
        # encounter_zombie()/punch()) - reload only ever increases it,
        # and dropping a ranged weapon salvages its ammo back into the
        # backpack instead of losing it. Tracking the EQUIPPED
        # weapon's ammo turn-over-turn, by identity (so a weapon swap
        # never gets misread as firing), captures every shot with no
        # gaps or double-counting.
        eq_weapon = p.equipped_weapon
        cur_weapon_ammo = eq_weapon.ammo if isinstance(eq_weapon, RangedWeapon) else None
        if (
            cur_weapon_ammo is not None
            and self._last_weapon_id == id(eq_weapon)
            and self._last_weapon_ammo is not None
            and cur_weapon_ammo < self._last_weapon_ammo
        ):
            self.metrics.ammo_fired += self._last_weapon_ammo - cur_weapon_ammo
        self._last_weapon_id = id(eq_weapon) if eq_weapon is not None else None
        self._last_weapon_ammo = cur_weapon_ammo

        # Food/water/medicine acquired vs consumed: every source that
        # touches backpack stock (loot finds, zombie-kill loot, goal/
        # task rewards, crafting ingredients, eat/drink/medicine) goes
        # through the same backpack.food/.water/.medicine properties,
        # so a straight turn-over-turn delta captures all of them
        # without a separate regex per code path.
        for attr, acquired_attr, consumed_attr, last_attr in (
            ('food', 'food_acquired', 'food_consumed', '_last_food'),
            ('water', 'water_acquired', 'water_consumed', '_last_water'),
            ('medicine', 'medicine_acquired', 'medicine_consumed', '_last_medicine'),
        ):
            cur = getattr(p.backpack, attr)
            last = getattr(self, last_attr)
            if last is not None:
                delta = cur - last
                if delta > 0:
                    setattr(self.metrics, acquired_attr, getattr(self.metrics, acquired_attr) + delta)
                elif delta < 0:
                    setattr(self.metrics, consumed_attr, getattr(self.metrics, consumed_attr) - delta)
            setattr(self, last_attr, cur)

        # Ammo acquired: only the positive side of backpack.ammo's
        # delta (loot finds). Reload's decrease (ammo moving from pack
        # into the weapon, not being spent) is deliberately excluded -
        # ammo_fired above already tracks real consumption. A dropped
        # ranged weapon's ammo salvage (drop_weapon(), actions_mixin.py)
        # also shows up as a positive delta here and will slightly
        # overcount true "found" ammo - a minor, known caveat.
        cur_ammo_pool = p.backpack.ammo
        if self._last_ammo is not None and cur_ammo_pool > self._last_ammo:
            self.metrics.ammo_acquired += cur_ammo_pool - self._last_ammo
        self._last_ammo = cur_ammo_pool

        if self.metrics.turns > self.max_turns:
            return 'x'

        # 1a. Swap in a strictly stronger working weapon if the
        #     backpack has one - equip_weapon() puts the old one back,
        #     so this never loses gear, just tests the equip path.
        best = max(p.backpack.weapons, key=_weapon_power, default=None)
        if best is not None and _weapon_power(best) > _weapon_power(p.equipped_weapon):
            self.metrics.equips_issued += 1
            return f"eq {best.name}"

        # 1b. Same idea for armor, but per-slot (equipment-slot
        #     investigation, multi-piece follow-up: four independent
        #     slots, not one) - pick whichever single upgrade across
        #     any slot improves that slot's reduction the most, one
        #     per turn, same pacing as the weapon swap above.
        best_armor_upgrade = None
        best_armor_delta = 0
        for piece in p.backpack.armor:
            current = p.equipped_armor.get(piece.slot)
            delta = _armor_power(piece)[1] - _armor_power(current)[1]
            if _armor_power(piece) > _armor_power(current) and delta > best_armor_delta:
                best_armor_upgrade = piece
                best_armor_delta = delta
        if best_armor_upgrade is not None:
            self.metrics.armor_equips_issued += 1
            return f"wr {best_armor_upgrade.name}"

        # 2. Survival triage, most urgent first.
        if p.health <= p.max_health * 0.4 and p.backpack.medicine > 0:
            return 'med'
        if p.hunger < 40 and p.backpack.food > 0:
            return 'ea'
        if p.thirst < 40 and (p.backpack.water > 0
                              or (hasattr(p, '_at_natural_water') and p._at_natural_water())):
            return 'dr'
        if p.fatigue > 85:
            return 'r'

        # 3. Reload only once truly empty - reloading at "below half"
        #    re-triggers every single turn while the ammo pool trickles
        #    back in slowly from loot, starving movement progress
        #    (confirmed live: 294 reload calls across 40 games with
        #    that threshold, one game hitting the turn cap without
        #    ever finishing its walk to the Town Center).
        eq = p.equipped_weapon
        if isinstance(eq, RangedWeapon) and eq.ammo == 0 and p.backpack.ammo > 0:
            self.metrics.reloads_issued += 1
            return f"reload {eq.name}"

        # 4. Thin out duplicate weapons/armor once they start piling
        #    up - exercises the drop/dropa commands instead of
        #    letting the backpack grow unbounded (armor has its own
        #    much smaller MAX_ARMOR cap than weapons' MAX_WEAPONS).
        counts = Counter(w.name for w in p.backpack.weapons)
        for name, count in counts.items():
            if count > 2:
                self.metrics.drops_issued += 1
                self.metrics.weapon_drops_issued += 1
                return f"drop {name}"

        armor_counts = Counter(a.name for a in p.backpack.armor)
        for name, count in armor_counts.items():
            if count > 2:
                self.metrics.drops_issued += 1
                return f"dropa {name}"

        # 5. Occasionally try crafting - cheap way to sample whether
        #    the recipe system produces a big power spike.
        if self.metrics.turns % 15 == 0:
            for recipe in p.describe_recipes():
                if not recipe["locked"]:
                    return f"cr {recipe['key']}"

        # 6. Otherwise, make progress toward the win condition.
        #    v4: run the investigation when there's a generated mystery;
        #    otherwise fall back to the old walk-to-Town-Center.
        if getattr(p, 'mystery', None) is not None and not getattr(p, 'won', False):
            return self._next_mystery_move()
        return self._next_move()

    def _next_mystery_move(self):
        """One command toward solving the generated mystery: visit and
        `search` the closed/route/require sites, step onto the obstacle
        (auto-clears once the requirement item is carried), reach the
        escape tile, `escape`."""
        p = self.player
        m = p.mystery

        # what's the current objective tile?
        target = None
        do_here = None
        # transportation adds a second requirement store (require2); the
        # bot visits + searches it like the others so it picks up the
        # second part before stepping onto the plane.
        roles = ["closed", "route", "require"]
        if "require2" in m.sites:
            roles.append("require2")
        # time-pressure (tidal_causeway): the 'require' site is the tide
        # board - optional evidence a focused player skips. The bot
        # triages by skipping it: route -> escape, straight across.
        if getattr(m, "deadline", None) is not None or \
                MECHANISMS.get(m.mechanism, {}).get("deadline_turns"):
            roles = ["closed", "route"]
        for role in roles:
            if role not in self._m_searched:
                target = m.sites[role]
                if p.current_position == target:
                    self._m_searched.add(role)
                    self.metrics.searches_issued = getattr(self.metrics, 'searches_issued', 0) + 1
                    return "search"
                break
        else:
            # Experimental family: the obstacle opens from the control
            # room (the 'require' site) by pulling the right control.
            # The bot already reads m.sites directly, so it reads the
            # answer too - a comprehension proxy, not a solver of the
            # 'which one' puzzle (that's the human test's job).
            if getattr(m, "controls", None) and not m.obstacle_open:
                if p.current_position == m.sites["require"]:
                    return f"pull {m.correct_control}"
                target = m.sites["require"]
            # Infrastructural family: carry the requirement item to the
            # power site (the game consumes it there and restores power)
            # BEFORE the obstacle will open.
            elif getattr(m, "power_role", None) and not m.power_restored:
                target = m.sites[m.power_role]
            elif not m.obstacle_open:
                target = m.obstacle_tile  # stepping onto it clears it with the item
            elif p.current_position != m.escape_tile:
                target = m.escape_tile
            else:
                return "escape"

        if target is None:
            return self._random_legal_step()

        # (re)compute a path to the target when needed
        if (self._m_target != target or not self._m_path
                or self._m_path_i >= len(self._m_path)):
            self._m_target = target
            self._m_path = _bfs_path(p, p.current_position, target)
            self._m_path_i = 0
        if self._m_path:
            while self._m_path_i < len(self._m_path):
                d = self._m_path[self._m_path_i]
                self._m_path_i += 1
                if self._step_is_legal(d) or self._one_ahead_is(d, target):
                    return d
        return self._random_legal_step()

    def _one_ahead_is(self, direction, target):
        p = self.player
        dx, dy = {"n": (0, -1), "s": (0, 1), "e": (1, 0), "w": (-1, 0)}[direction]
        return (p.current_position[0] + dx, p.current_position[1] + dy) == target

    def _next_move(self):
        p = self.player
        # WAKE_SPINE §5: a scheduled section crossing - head for the
        # carved far-wall exit (no mystery, no town center). An encounter
        # crossing has a load-bearing beat tile to reach first.
        _sx = getattr(p, "section_exit", None)
        if _sx is not None:
            _beat = getattr(p, "_encounter_beat", None)
            _goal = (_beat if (_beat is not None
                               and not getattr(p, "_encounter_beat_seen", False))
                     else _sx)
            if getattr(self, "_sx_cached", None) != _goal or not self._path:
                self._sx_cached = _goal
                self._path = _bfs_path(p, p.current_position, _goal)
                self._path_index = 0
            if self._path:
                while self._path_index < len(self._path):
                    d = self._path[self._path_index]
                    self._path_index += 1
                    if self._step_is_legal(d):
                        return d
            return self._random_legal_step()

        if self._town_center is None:
            self._town_center = _find_town_center(p)
            if self._town_center is not None:
                self._path = _bfs_path(p, p.current_position, self._town_center)
                self._path_index = 0

        if self._path:
            while self._path_index < len(self._path):
                direction = self._path[self._path_index]
                self._path_index += 1
                if self._step_is_legal(direction):
                    return direction
            # Path exhausted or blocked (e.g. town center itself was
            # reached and win already fired before we got here) -
            # fall through to a random legal step.

        return self._random_legal_step()

    def _step_is_legal(self, direction):
        p = self.player
        deltas = {"n": (0, -1), "s": (0, 1), "e": (1, 0), "w": (-1, 0)}
        dx, dy = deltas[direction]
        nx, ny = p.current_position[0] + dx, p.current_position[1] + dy
        if not (0 <= nx < p.map_size and 0 <= ny < p.map_size):
            return False
        cell = p.map[ny][nx]
        terrain = cell.get('terrain') if isinstance(cell, dict) else None
        return terrain not in IMPASSABLE_TERRAIN

    def _random_legal_step(self):
        p = self.player
        legal = [d for d in ("n", "s", "e", "w") if self._step_is_legal(d)]
        return random.choice(legal) if legal else 'n'


def play_one_game(level, expeditions_completed, seed, max_turns, verbose=False,
                  force_mechanism=None):
    io = BotIO(max_turns=max_turns, verbose=verbose)
    # v4: --force-mechanism pins every game to one escape family (for a
    # per-family solve/survival check). Prime the shuffle-bag so
    # choose_mechanism() has exactly one candidate left, the same trick
    # the test suite's _force_mechanism helper uses.
    _saved_used = list(getattr(Apocrysis, "_used_mechanisms", []) or [])
    _saved_last = getattr(Apocrysis, "_last_family", None)
    if force_mechanism:
        from src.escape import MECHANISMS as _M
        Apocrysis._used_mechanisms = [k for k in _M if k != force_mechanism]
        Apocrysis._last_family = None
    try:
        player = Apocrysis(
            "BalanceBot", level=level, expeditions_completed=expeditions_completed,
            seed=seed, io=io,
        )
    finally:
        if force_mechanism:
            Apocrysis._used_mechanisms = _saved_used
            Apocrysis._last_family = _saved_last
    io.player = player
    io.metrics.starting_level = level

    # XP gained (item 9): award_xp() (combat_mixin.py) never emits an
    # io.say() message carrying the amount, so there's no text signal
    # to regex - wrapping the bound method is the only way to observe
    # the real total without reimplementing the level-threshold math
    # here and risking drift from the engine's own values.
    _original_award_xp = player.award_xp

    def _tracked_award_xp(amount, _orig=_original_award_xp, _metrics=io.metrics):
        if amount > 0:
            _metrics.xp_gained += amount
        return _orig(amount)

    player.award_xp = _tracked_award_xp

    player.run_game_loop()

    if getattr(player, 'mystery', None) is not None:
        io.metrics.mechanism = player.mystery.mechanism
        # v4: did the bot actually SOLVE the investigation (open the
        # obstacle / restore the route + confirm the hypothesis), even
        # if it then died on the walk out? This is the "can the bot
        # solve this family" signal, separate from survival.
        _mk = player.mystery.knowledge
        io.metrics.mystery_solved = bool(
            player.mystery.obstacle_open
            and _mk.hypothesis_state() == "confirmed")

    # Compute spawn-to-objective distance after the game loop finishes.
    # v4: the objective is the escape tile; fall back to the Town
    # Center on a no-mystery map.
    objective = (player.mystery.escape_tile
                 if getattr(player, 'mystery', None) is not None
                 else getattr(player, 'section_exit', None)
                 or _find_town_center(player))
    if io._spawn is not None and objective is not None:
        path = _bfs_path(player, io._spawn, objective)
        io.metrics.spawn_to_objective_distance = len(path) if path else 0

    if player.won:
        io.metrics.outcome = "won"
        # Re-sample final_expeditions_completed here because _choose_command() only samples it at the START of each turn.
        # If the game ends on a winning move, there's no subsequent turn to re-sample from, so this captures the real post-win value.
        io.metrics.final_expeditions_completed = player.expeditions_completed
    elif player.health <= 0:
        io.metrics.outcome = "died"
        io.metrics.death_cause = io.metrics._last_damage_event or "other (unattributed)"
    else:
        io.metrics.outcome = "timeout"

    # Final-state snapshot (items 3, 5, 8) - read directly off the
    # player/map/backpack now that the loop has ended, same spirit as
    # the per-turn sampling in BotIO._choose_command.
    io.metrics.final_food = player.backpack.food
    io.metrics.final_water = player.backpack.water
    io.metrics.final_medicine = player.backpack.medicine
    io.metrics.final_ammo = player.backpack.ammo
    io.metrics.has_flashlight_at_end = player.has_flashlight
    io.metrics.final_weapon_count = len(player.backpack.weapons) + (1 if player.equipped_weapon else 0)
    io.metrics.final_armor_count = len(player.backpack.armor) + sum(1 for a in player.equipped_armor.values() if a)
    io.metrics.final_visited_count = len(player.visited)
    io.metrics.final_map_tiles = player.map_size ** 2
    io.metrics.map_size = player.map_size
    io.metrics.final_settlement_explored = player.settlement_explored

    # Objective/quest system: the legacy Goal/Task systems were removed
    # (docs/OBJECTIVES_AUDIT.md). Player intent is the investigation +
    # the expedition mystery; there is no generic quest bookkeeping to
    # sample here.

    regions = _settlement_regions(player)
    io.metrics.settlements_on_map = len(regions)
    io.metrics.settlements_discovered = sum(1 for r in regions if r & player.visited)

    # Town-Center telemetry (sampled at game end, same point as settlements above)
    tc_pos = _find_town_center(player)
    io.metrics.town_center_discovered = tc_pos is not None and tc_pos in player.visited  # real vs decoy distinction blocked on Q6
    io.metrics.town_center_reached = (tc_pos == player.current_position) if tc_pos else False

    return io.metrics


def play_campaign(seed, max_turns, max_attempts_per_tier, verbose=False):
    """
    Simulates one full campaign from a fresh level-1 character: plays
    consecutive expeditions with ONE persisting character, reusing the
    real game's own save_profile()/apply_profile() to carry level/xp/
    stats/backpack/weapons/armor forward exactly the way cli.py's
    main() loop does - a win advances expeditions_completed and keeps
    everything; a death keeps everything BUT expeditions_completed
    (retry the same tier, matching the real non-hardcore death-
    preserves-progress behavior); health resets fresh either way via a
    brand-new Apocrysis instance. A timeout (turn cap hit) also
    retries the same tier, same as a death.

    Returns a dict: reached_campaign_length (bool), total_attempts,
    attempts_per_expedition (dict: expeditions_completed -> attempt
    count spent at that tier before advancing or giving up),
    final_level, stuck_at (the expeditions_completed value it gave up
    at, or None if it completed).
    """
    import tempfile

    # v4: fresh escape-mechanism shuffle-bag per campaign so each
    # simulated campaign sees the same no-repeat-until-exhausted
    # rotation a real player would.
    Apocrysis._used_mechanisms = []

    profile = None
    level = 1
    expeditions_completed = 0
    total_attempts = 0
    attempts_per_expedition = defaultdict(int)
    failure_reasons_per_expedition = defaultdict(Counter)
    power_by_expedition = defaultdict(list)

    with tempfile.TemporaryDirectory() as tmp:
        profile_path = os.path.join(tmp, 'campaign_profile.json')

        while expeditions_completed < CAMPAIGN_LENGTH:
            current_tier = expeditions_completed
            attempts_per_expedition[expeditions_completed] += 1
            total_attempts += 1

            if attempts_per_expedition[expeditions_completed] > max_attempts_per_tier:
                return {
                    'reached_campaign_length': False,
                    'total_attempts': total_attempts,
                    'attempts_per_expedition': dict(attempts_per_expedition),
                    'failure_reasons_per_expedition': {k: dict(v) for k, v in failure_reasons_per_expedition.items()},
                    'power_by_expedition': dict(power_by_expedition),
                    'final_level': level,
                    'stuck_at': expeditions_completed,
                }

            attempt_seed = None if seed is None else seed + total_attempts

            io = BotIO(max_turns=max_turns, verbose=verbose)
            player = Apocrysis(
                'CampaignBot', level=level,
                expeditions_completed=expeditions_completed,
                seed=attempt_seed, io=io,
            )
            if profile is not None:
                player.apply_profile(profile)
            io.player = player

            player.run_game_loop()

            power_by_expedition[current_tier].append({
                'level': player.level,
                'best_weapon_damage': max([player.equipped_weapon.damage if player.equipped_weapon else 0] + [w.damage for w in player.backpack.weapons], default=0),
                'best_armor_reduction': max([a.damage_reduction for a in player.equipped_armor.values() if a] + [a.damage_reduction for a in player.backpack.armor], default=0),
                'ammo': player.backpack.ammo,
            })

            # Classify outcome exactly like play_one_game() does.
            if player.won:
                outcome = 'won'
            elif player.health <= 0:
                outcome = 'died'
                death_cause = io.metrics._last_damage_event or 'other (unattributed)'
                failure_reasons_per_expedition[current_tier][f'died: {death_cause}'] += 1
            else:
                outcome = 'timeout'
                failure_reasons_per_expedition[current_tier]['timeout'] += 1

            level = player.level
            if player.won:
                expeditions_completed = player.expeditions_completed
            # else: died or timed out - expeditions_completed unchanged, retry same tier

            player.save_profile(profile_path)
            profile = Apocrysis.load_profile(profile_path)

    return {
        'reached_campaign_length': True,
        'total_attempts': total_attempts,
        'attempts_per_expedition': dict(attempts_per_expedition),
        'failure_reasons_per_expedition': {k: dict(v) for k, v in failure_reasons_per_expedition.items()},
        'power_by_expedition': dict(power_by_expedition),
        'final_level': level,
        'stuck_at': None,
    }


def _fmt(values):
    if not values:
        return "n/a"
    s = sorted(values)
    n = len(s)

    def pct(p):
        k = (n - 1) * p / 100.0
        f = int(k)
        c = min(f + 1, n - 1)
        return s[f] + (k - f) * (s[c] - s[f])

    return (
        f"avg {statistics.mean(values):.1f}, median {statistics.median(values):.1f}, "
        f"p25 {pct(25):.1f}, p75 {pct(75):.1f}, p95 {pct(95):.1f}, "
        f"min {s[0]}, max {s[-1]}"
    )


_TURNS_BUCKETS = [(1, 5), (6, 10), (11, 20), (21, 40), (41, 80), (81, None)]


def _turns_bucket_label(n):
    for lo, hi in _TURNS_BUCKETS:
        if hi is None or n <= hi:
            return f"{lo}-{hi}" if hi is not None else f"{lo}+"
    return "?"  # unreachable - last bucket's hi is None


def print_report(all_metrics, games, level, expeditions_completed, max_turns):
    print(f"\n{'=' * 60}")
    print(
        f"Apocrysis balance report - {games} game(s), start level {level}, "
        f"expeditions_completed {expeditions_completed}, cap {max_turns} turns"
    )
    print(f"{'=' * 60}\n")

    # Scenario/config header (item 10) - only real constants/attributes,
    # nothing invented. Map size is read off the first game's player
    # (generate_map()'s size formula is deterministic given
    # expeditions_completed, so every game in this run has the same
    # map_size unless --expeditions-completed itself varies mid-run,
    # which this harness never does).
    map_size = all_metrics[0].map_size if all_metrics else 0
    print("Scenario configuration:")
    print(f"  Starting level            : {level}")
    print(f"  expeditions_completed     : {expeditions_completed}")
    print(f"  Campaign length           : {CAMPAIGN_LENGTH} expeditions to complete")
    print(f"  Map size                  : {map_size}x{map_size} ({map_size ** 2} tiles)")
    print(f"  Day length                : {MINUTES_PER_DAY} in-game minutes of trek time per day")
    print(f"  Per-game turn cap         : {max_turns}")

    outcomes = Counter(m.outcome for m in all_metrics)
    print("\nOutcomes:")
    for key in ("won", "died", "timeout"):
        print(f"  {key:8s}: {outcomes.get(key, 0)}/{games}")

    # Death/win reasons (item 1). Inferred from the "last damage event"
    # the BotIO saw before health hit 0 - a real classification of this
    # engine's health-reduction code paths (grepped): zombie combat
    # (+ Bleeding/Poison, always mid-fight), the cold-water terrain
    # roll, and the hunger/thirst-at-zero drain. `death_cause` is
    # whichever fired last; a starving player finished off by a zombie
    # bite shows as "zombie combat" even though attrition set it up -
    # cross-check with the loot-economy net numbers below. Fatigue
    # still never reduces health.
    died_metrics = [m for m in all_metrics if m.outcome == "died"]
    if died_metrics:
        death_causes = Counter(m.death_cause for m in died_metrics)
        print("\nDeath reasons (whichever damage source fired last):")
        for cause in ("zombie combat", "resource attrition (hunger/thirst)",
                      "environmental (cold water)", "other (unattributed)"):
            if death_causes.get(cause):
                print(f"  {cause:34s}: {death_causes[cause]}/{len(died_metrics)}")
        print(f"  {'fatigue':34s}: 0/{len(died_metrics)}  (fatigue never reduces health)")

    # Win reasons (v4): winning = working out the generated escape
    # mechanism and taking it (mystery_try_escape). "expedition win"
    # vs "CAMPAIGN COMPLETE" is the same act at CAMPAIGN_LENGTH.
    won_metrics = [m for m in all_metrics if m.outcome == "won"]
    if won_metrics:
        campaign_wins = sum(1 for m in won_metrics if m.campaign_completions > 0)
        print("\nWin reasons (v4: found and took this expedition's escape route):")
        print(f"  escaped (expedition win)     : {len(won_metrics) - campaign_wins}/{len(won_metrics)}")
        print(f"  escaped (CAMPAIGN COMPLETE)  : {campaign_wins}/{len(won_metrics)}")
        mechs = Counter(m.mechanism for m in won_metrics if getattr(m, 'mechanism', None))
        if mechs:
            print("  by mechanism: " + ", ".join(f"{k} {v}" for k, v in mechs.most_common()))

    # v4: per-mechanism campaign-goal breakdown. The "goal" of every
    # expedition is to reconstruct the Escape Proof and take the route;
    # `mystery_solved` is that goal reached (obstacle open + hypothesis
    # confirmed), counted even when the bot then died on the walk out -
    # so a family that plays fine but is hard to survive (by design,
    # e.g. time-pressure) reads as high-solved / lower-survived rather
    # than looking broken. Over a large run (e.g. --games 10000) this is
    # the table to watch when a new mechanism lands.
    by_mech = defaultdict(list)
    for m in all_metrics:
        if getattr(m, 'mechanism', None):
            by_mech[m.mechanism].append(m)
    if by_mech:
        print("\nPer-mechanism (campaign goal = solve the Escape Proof + take the route):")
        print(f"  {'mechanism':18s} {'n':>5} {'solved':>8} {'survived':>9} {'median turns':>13}")
        for name in sorted(by_mech, key=lambda k: -len(by_mech[k])):
            ms = by_mech[name]
            n = len(ms)
            solved = sum(1 for x in ms if getattr(x, 'mystery_solved', False))
            survived = sum(1 for x in ms if x.outcome == "won")
            med = statistics.median([x.turns for x in ms]) if ms else 0
            print(f"  {name:18s} {n:>5} {solved / n * 100:>7.1f}% "
                  f"{survived / n * 100:>8.1f}% {med:>13.0f}")

    turns = [m.turns for m in all_metrics]
    levels = [m.final_level for m in all_metrics]
    days = [m.final_day for m in all_metrics]
    min_health = [m.min_health for m in all_metrics]
    final_expeditions = [m.final_expeditions_completed for m in all_metrics]

    print(f"\nTurns to finish : {_fmt(turns)}")
    print(f"Final level      : {_fmt(levels)}")
    print(f"Final day        : {_fmt(days)}")
    reached_night = sum(1 for m in all_metrics if m.reached_night)
    print(f'Games reaching night : {reached_night}/{games}')
    combined_phases = Counter()
    for m in all_metrics:
        combined_phases.update(m.day_phase_counts)
    total_phase_turns = sum(combined_phases.values()) or 1
    print('Day phase distribution (% of total turns):')
    for phase, count in combined_phases.most_common():
        pct = (count / total_phase_turns * 100) if total_phase_turns else 0
        print(f'  {phase:20s}: {count:>5} ({pct:.1f}%)')
    all_visibility = [v for m in all_metrics for v in m.visibility_samples]
    flashlight_games = sum(1 for m in all_metrics if m.has_flashlight_at_end)
    print(f'Visibility radius (avg/median across all turns): {_fmt(all_visibility)}')
    print(f'Games with a flashlight by end: {flashlight_games}/{games}')
    print(f"Final expeditions_completed: {_fmt(final_expeditions)}")
    print(f"Lowest health seen: {_fmt(min_health)}")

    # Turns distribution (item 2) - a histogram instead of just avg,
    # since avg alone hides a bimodal split (e.g. quick deaths vs long
    # wins) entirely.
    turns_histogram = Counter(_turns_bucket_label(t) for t in turns)
    print("\nTurns distribution:")
    for lo, hi in _TURNS_BUCKETS:
        label = f"{lo}-{hi}" if hi is not None else f"{lo}+"
        count = turns_histogram.get(label, 0)
        bar = "#" * count
        print(f"  {label:>6}: {count:>3}/{games}  {bar}")

    won_turns = [m.turns for m in all_metrics if m.outcome == "won"]
    died_turns = [m.turns for m in all_metrics if m.outcome == "died"]
    print(f"Turns on a win   : {_fmt(won_turns)}")
    print(f"Turns on a death : {_fmt(died_turns)}")

    near_death = sum(1 for m in all_metrics if m.min_health <= 15)
    print(f"Games with a near-death moment (health <= 15): {near_death}/{games}")

    all_dealt = [d for m in all_metrics for _, d in m.hits_dealt]
    all_taken = [d for m in all_metrics for _, d in m.hits_taken]
    total_fights = sum(m.fights for m in all_metrics)
    total_defeated = sum(m.zombies_defeated for m in all_metrics)
    total_crits = sum(m.crits for m in all_metrics)

    print(f"\nZombie encounters : {total_fights}")
    print(f"Zombies defeated  : {total_defeated} ({(total_defeated / total_fights * 100) if total_fights else 0:.0f}% of encounters)")
    encounters_per_game = total_fights / games
    kills_per_game = total_defeated / games
    dealt_per_game = sum(len(m.hits_dealt) and sum(d for _, d in m.hits_dealt) or 0 for m in all_metrics) / games
    taken_per_game = sum(len(m.hits_taken) and sum(d for _, d in m.hits_taken) or 0 for m in all_metrics) / games
    print(f'Encounters/game   : {encounters_per_game:.1f}')
    print(f'Kills/game        : {kills_per_game:.1f}')
    print(f'Total damage dealt/game: {dealt_per_game:.1f}')
    print(f'Total damage taken/game: {taken_per_game:.1f}')
    print(f"Critical hits     : {total_crits}")
    print(f"Damage dealt/hit  : {_fmt(all_dealt)}")
    print(f"Damage taken/hit  : {_fmt(all_taken)}")
    if all_dealt and all_taken:
        ratio = statistics.mean(all_dealt) / max(1, statistics.mean(all_taken))
        print(f"Dealt:taken ratio : {ratio:.2f}x")

    # Bucket the dealt:taken ratio by player level to see whether
    # power scaling favors the player more as they level up - the
    # actual "are levels overpowered" question, not just a single
    # game-wide average.
    dealt_by_level = defaultdict(list)
    taken_by_level = defaultdict(list)
    for m in all_metrics:
        for lvl, dmg in m.hits_dealt:
            dealt_by_level[lvl].append(dmg)
        for lvl, dmg in m.hits_taken:
            taken_by_level[lvl].append(dmg)

    LOW_SAMPLE_THRESHOLD = 30

    levels_seen = sorted(set(dealt_by_level) | set(taken_by_level))
    if levels_seen:
        print("\nDealt:taken ratio by player level (rising ratio = player pulling ahead of the difficulty curve):")
        for lvl in levels_seen:
            d = dealt_by_level.get(lvl, [])
            t = taken_by_level.get(lvl, [])
            if not d or not t:
                continue
            ratio = statistics.mean(d) / max(1, statistics.mean(t))
            low_sample_flag = "" if (len(d) >= LOW_SAMPLE_THRESHOLD and len(t) >= LOW_SAMPLE_THRESHOLD) else " [LOW SAMPLE]"
            print(f"  level {lvl:>2}: dealt avg {statistics.mean(d):5.1f}  taken avg {statistics.mean(t):5.1f}  ratio {ratio:5.2f}x  (n={len(d)}/{len(t)}){low_sample_flag}")

    weapon_names = Counter(w for m in all_metrics for w in m.weapons_looted)
    print(f"\nWeapons looted (total {sum(weapon_names.values())}):")
    for name, count in weapon_names.most_common(10):
        print(f"  {name}: {count}")

    weapons_acquired_per_game = sum(len(m.weapons_looted) for m in all_metrics) / games
    weapons_equipped_per_game = sum(m.equips_issued for m in all_metrics) / games
    weapons_discarded_per_game = sum(m.weapon_drops_issued for m in all_metrics) / games
    weapons_remaining = [m.final_weapon_count for m in all_metrics]
    print('\nWeapon lifecycle (per game):')
    print(f'  Acquired : {weapons_acquired_per_game:.1f}/game')
    print(f'  Equipped : {weapons_equipped_per_game:.1f}/game')
    print(f'  Discarded: {weapons_discarded_per_game:.1f}/game')
    print(f'  Remaining at game end: {_fmt(weapons_remaining)}')

    armor_names = Counter(a for m in all_metrics for a in m.armor_looted)
    print(f"\nArmor looted (total {sum(armor_names.values())}):")
    for name, count in armor_names.most_common(10):
        print(f"  {name}: {count}")

    # Bucketed by expeditions_completed, not player level - map/loot
    # generation now key off expeditions_completed (map/player/
    # campaign-level split), so that's the axis that actually
    # determines what's reachable, independent of combat level.
    max_dmg_by_expedition = defaultdict(list)
    max_reduction_by_expedition = defaultdict(list)
    for m in all_metrics:
        for exp, dmg in m.max_weapon_damage_by_expedition.items():
            max_dmg_by_expedition[exp].append(dmg)
        for exp, reduction in m.max_armor_reduction_by_expedition.items():
            max_reduction_by_expedition[exp].append(reduction)
    if max_dmg_by_expedition:
        print("\nBest weapon damage available, by expeditions_completed:")
        for exp in sorted(max_dmg_by_expedition):
            print(f"  expeditions_completed {exp:>2}: {_fmt(max_dmg_by_expedition[exp])}")
    if max_reduction_by_expedition:
        print("\nBest armor reduction available (any one slot), by expeditions_completed:")
        for exp in sorted(max_reduction_by_expedition):
            print(f"  expeditions_completed {exp:>2}: {_fmt(max_reduction_by_expedition[exp])}")

    crafted = Counter(c for m in all_metrics for c in m.crafted)
    if crafted:
        print(f"\nItems crafted (total {sum(crafted.values())}):")
        for name, count in crafted.most_common():
            print(f"  {name}: {count}")

    total_flashlights = sum(m.flashlights_found for m in all_metrics)
    total_campaign_completions = sum(m.campaign_completions for m in all_metrics)

    print(f"\nDrop command used   : {sum(m.drops_issued for m in all_metrics)} time(s)")
    print(f"Reload command used : {sum(m.reloads_issued for m in all_metrics)} time(s)")
    print(f"Weapon equip swaps  : {sum(m.equips_issued for m in all_metrics)} time(s)")
    print(f"Armor equip swaps   : {sum(m.armor_equips_issued for m in all_metrics)} time(s)")
    print(f"Flashlights found   : {total_flashlights}/{games} game(s)")
    print(f"Campaign completions: {total_campaign_completions}/{games} game(s) "
          f"(expeditions_completed reaching CAMPAIGN_LENGTH mid-game)")

    # Terrain traversal breakdown across the batch.
    total_terrain_steps = sum(m.tiles_moved for m in all_metrics) or 1
    terrain_totals = Counter()
    for m in all_metrics:
        terrain_totals.update(m.terrain_counts)
    
    print("\nTerrain traversal (% of total steps moved):")
    for terrain, count in terrain_totals.most_common():
        pct = (count / total_terrain_steps * 100) if total_terrain_steps else 0
        print(f"  {terrain:20s}: {count:>5} ({pct:.1f}%)")

    # Map exploration (item 3) + distance traveled (item 4).
    explore_pct = [
        (m.final_visited_count / m.final_map_tiles * 100) if m.final_map_tiles else 0
        for m in all_metrics
    ]
    tiles_moved = [m.tiles_moved for m in all_metrics]
    unique_visited = [m.final_visited_count for m in all_metrics]
    max_dist = [m.max_distance_from_spawn for m in all_metrics]
    print("\nMap exploration:")
    print(f"  Tiles moved (total steps, revisits counted): {_fmt(tiles_moved)}")
    print(f"  Unique tiles visited                       : {_fmt(unique_visited)}")
    print(f"  Map explored before outcome                : {_fmt([round(p, 1) for p in explore_pct])}%")
    print(f"  Max distance from spawn (tiles, Manhattan)  : {_fmt(max_dist)}")

    # Spawn-to-objective telemetry.
    spawn_to_obj_dists = [m.spawn_to_objective_distance for m in all_metrics if m.spawn_to_objective_distance is not None]
    print(f"  Spawn to objective distance (avg/median)   : {_fmt(spawn_to_obj_dists)}")

    # Ratio of tiles_moved to spawn-to-objective distance per game.
    move_ratios = []
    for m in all_metrics:
        if m.spawn_to_objective_distance is not None and m.spawn_to_objective_distance > 0:
            move_ratios.append(m.tiles_moved / m.spawn_to_objective_distance)
    print(f"  Tiles moved per spawn-to-obj step (avg/med): {_fmt(move_ratios)}")

    # Buildings/settlements discovered (item 5).
    buildings_entered = [m.buildings_entered for m in all_metrics]
    settlements_discovered = [m.settlements_discovered for m in all_metrics]
    settlements_on_map = [m.settlements_on_map for m in all_metrics]
    explored_settlement = sum(1 for m in all_metrics if m.final_settlement_explored)
    tc_discovered = sum(1 for m in all_metrics if m.town_center_discovered)
    tc_reached = sum(1 for m in all_metrics if m.town_center_reached)

    print("\nBuildings & settlements discovered:")
    print(f"  Building 'safe zone' entries (can repeat on revisit): {_fmt(buildings_entered)}")
    print(f"  Settlements on the map                              : {_fmt(settlements_on_map)}")
    print(f"  Settlements discovered (any tile visited)           : {_fmt(settlements_discovered)}")
    print(f"  Town Center discovered (any tile visited)           : {tc_discovered}/{games}  # real vs decoy distinction blocked on Q6")
    print(f"  Town Center reached at game end                     : {tc_reached}/{games}")
    print(f"  Games that explored a settlement (win-gate met)     : {explored_settlement}/{games}")

    # Loot acquired vs consumed (item 7).
    print("\nLoot economy (acquired vs consumed, real backpack-stock units):")
    food_acq = sum(m.food_acquired for m in all_metrics) / games
    water_acq = sum(m.water_acquired for m in all_metrics) / games
    med_acq = sum(m.medicine_acquired for m in all_metrics) / games
    ammo_acq = sum(m.ammo_acquired for m in all_metrics) / games
    
    print(f"  Food     acquired {food_acq:>6.1f}  consumed {sum(m.food_consumed for m in all_metrics)/games:>.1f}  net {(food_acq - sum(m.food_consumed for m in all_metrics)/games):>+7.1f}  final avg {sum(m.final_food for m in all_metrics)/games:.1f}")
    print(f"  Water    acquired {water_acq:>6.1f}  consumed {sum(m.water_consumed for m in all_metrics)/games:>.1f}  net {(water_acq - sum(m.water_consumed for m in all_metrics)/games):>+7.1f}  final avg {sum(m.final_water for m in all_metrics)/games:.1f}")
    print(f"  Medicine acquired {med_acq:>6.1f}  consumed {sum(m.medicine_consumed for m in all_metrics)/games:>.1f}  net {(med_acq - sum(m.medicine_consumed for m in all_metrics)/games):>+7.1f}  final avg {sum(m.final_medicine for m in all_metrics)/games:.1f}")
    print(f"  Ammo     acquired {ammo_acq:>6.1f}  fired {sum(m.ammo_fired for m in all_metrics)/games:>.1f}  remaining/game {sum(m.final_ammo for m in all_metrics)/games:.1f}")

    # Final inventory (item 8) - avg/median/max, not just avg.
    print("\nFinal inventory at game end:")
    print(f"  Food     : {_fmt([m.final_food for m in all_metrics])}")
    print(f"  Water    : {_fmt([m.final_water for m in all_metrics])}")
    print(f"  Medicine : {_fmt([m.final_medicine for m in all_metrics])}")
    print(f"  Ammo     : {_fmt([m.final_ammo for m in all_metrics])}")
    print(f"  Weapons (equipped + backpack) : {_fmt([m.final_weapon_count for m in all_metrics])}")
    print(f"  Armor pieces (equipped + backpack) : {_fmt([m.final_armor_count for m in all_metrics])}")

    # Starting vs ending level, levels gained, XP gained (item 9).
    starting_levels = [m.starting_level for m in all_metrics]
    levels_gained = [m.final_level - m.starting_level for m in all_metrics]
    xp_gained = [m.xp_gained for m in all_metrics]
    print("\nProgression:")
    print(f"  Starting level : {_fmt(starting_levels)}")
    print(f"  Ending level   : {_fmt(levels)}")
    print(f"  Levels gained  : {_fmt(levels_gained)}")
    print(f"  XP gained      : {_fmt(xp_gained)}")

    print(f"\n{'-' * 60}")
    print("Signals worth a human look:")
    signals = []
    win_rate = outcomes.get("won", 0) / games if games else 0
    if win_rate >= 0.9 and near_death / games <= 0.2 if games else False:
        signals.append(f"- {win_rate * 100:.0f}% win rate with only {near_death}/{games} near-death games - zombies may be too weak or loot too generous.")
    if levels_seen and len(levels_seen) >= 2:
        first_ratio = None
        last_ratio = None
        for lvl in levels_seen:
            d, t = dealt_by_level.get(lvl), taken_by_level.get(lvl)
            # Exclude low-sample buckets from automatic signal detection to avoid false positives.
            if not d or not t or len(d) < LOW_SAMPLE_THRESHOLD or len(t) < LOW_SAMPLE_THRESHOLD:
                continue
            r = statistics.mean(d) / max(1, statistics.mean(t))
            if first_ratio is None:
                first_ratio = r
            last_ratio = r
        if first_ratio and last_ratio and last_ratio > first_ratio * 1.5:
            signals.append(f"- dealt:taken ratio grows from {first_ratio:.2f}x at level {levels_seen[0]} to {last_ratio:.2f}x at level {levels_seen[-1]} - player power is outscaling zombie difficulty.")
    if outcomes.get("timeout", 0) / games > 0.3 if games else False:
        signals.append(f"- {outcomes.get('timeout', 0)}/{games} games hit the turn cap without winning or dying - either the map/win condition takes very long, or the bot's pathing is getting stuck (check with --verbose).")
    if expeditions_completed == 0 and level > 5:
        signals.append(
            f"- start level {level} with expeditions_completed=0: map size/obstacle "
            "density/zombie composition/elites and loot banding (both weapons and "
            "armor) are all still at their easiest/smallest tier regardless of "
            "level - this combination tests raw combat power against the weakest "
            "possible map, not a realistic point in a real campaign. Pass "
            "--expeditions-completed to test actual map/loot difficulty."
        )
    death_rate = outcomes.get("died", 0) / games if games else 0
    if death_rate >= 0.5 and expeditions_completed >= 3:
        signals.append(
            f"- {death_rate * 100:.0f}% death rate at expeditions_completed="
            f"{expeditions_completed}: every game here starts a completely fresh, "
            "gearless character at that difficulty tier - real play would have "
            "accumulated loot/crafted gear getting there. A high death rate here "
            "may mean the zombie composition/elite chance at this expedition "
            "count is genuinely too harsh for a GEARLESS character specifically, "
            "not necessarily too harsh overall - re-run with a --level roughly "
            "consistent with having played that many expeditions before judging."
        )
    if not signals:
        signals.append("- nothing jumped out automatically; read the numbers above directly.")
    for s in signals:
        print(s)

    print('\nSurvival rate by map exploration %:')
    explore_buckets = [(0, 10), (10, 25), (25, 50), (50, 101)]
    for lo, hi in explore_buckets:
        bucket = [m for m in all_metrics if m.final_map_tiles and lo <= (m.final_visited_count / m.final_map_tiles * 100) < hi]
        if bucket:
            wins = sum(1 for m in bucket if m.outcome == 'won')
            print(f'  {lo}-{hi if hi <= 100 else 100}%: {wins}/{len(bucket)} ({wins / len(bucket) * 100:.0f}%)')

    print('\nSurvival rate by player level:')
    for lvl in sorted(set(m.final_level for m in all_metrics)):
        bucket = [m for m in all_metrics if m.final_level == lvl]
        wins = sum(1 for m in bucket if m.outcome == 'won')
        print(f'  level {lvl:>2}: {wins}/{len(bucket)} ({wins / len(bucket) * 100:.0f}%)')

    print('\nSurvival rate by expeditions_completed (starting tier):')
    for exp in sorted(set(m.starting_level for m in all_metrics)) if False else sorted(set(getattr(m, "final_expeditions_completed", 0) for m in all_metrics)):
        bucket = [m for m in all_metrics if getattr(m, 'final_expeditions_completed', 0) == exp]
        wins = sum(1 for m in bucket if m.outcome == 'won')
        print(f'  expeditions_completed {exp:>2}: {wins}/{len(bucket)} ({wins / len(bucket) * 100:.0f}%)')

    print('\nSurvival rate by final ammo held:')
    ammo_buckets = [(0, 20), (20, 50), (50, 100), (100, 10**9)]
    for lo, hi in ammo_buckets:
        bucket = [m for m in all_metrics if lo <= m.final_ammo < hi]
        if bucket:
            wins = sum(1 for m in bucket if m.outcome == 'won')
            label = f'{lo}-{hi}' if hi < 10**9 else f'{lo}+'
            print(f'  ammo {label:>8s}: {wins}/{len(bucket)} ({wins / len(bucket) * 100:.0f}%)')

    print()


def print_campaign_report(campaign_results, runs, max_attempts_per_tier):
    print(f"\n{'=' * 60}")
    print(f"Apocrysis CAMPAIGN report - {runs} campaign run(s), max {max_attempts_per_tier} attempts per expedition tier")
    print(f"{'=' * 60}\n")

    completed = sum(1 for r in campaign_results if r['reached_campaign_length'])
    print(f"Campaigns completed (reached CAMPAIGN_LENGTH): {completed}/{runs}")

    attempts = [r['total_attempts'] for r in campaign_results]
    print(f"Total attempts per campaign: {_fmt(attempts)}")

    final_levels = [r['final_level'] for r in campaign_results]
    print(f"Final level reached: {_fmt(final_levels)}")

    stuck = Counter(r['stuck_at'] for r in campaign_results if r['stuck_at'] is not None)
    if stuck:
        print("\nCampaigns that gave up, by expedition tier they got stuck at:")
        for tier in sorted(stuck):
            print(f"  expeditions_completed {tier:>2}: {stuck[tier]} campaign(s)")

    # Average attempts needed per expedition tier, across all campaigns
    # that got at least that far - shows WHERE difficulty spikes are,
    # not just whether the whole campaign succeeded.
    tier_attempts = defaultdict(list)
    for r in campaign_results:
        for tier, count in r['attempts_per_expedition'].items():
            tier_attempts[tier].append(count)
    if tier_attempts:
        print("\nAverage attempts needed to clear each expedition tier:")
        for tier in sorted(tier_attempts):
            vals = tier_attempts[tier]
            censored_note = ""
            if vals and (statistics.median(vals) >= max_attempts_per_tier or statistics.mean(vals) >= max_attempts_per_tier):
                censored_note = " [CENSORED: median/avg at or above cap; true difficulty unknown]"
            print(f"  expeditions_completed {tier:>2}: {_fmt(vals)}  (n={len(vals)} campaigns reached this tier){censored_note}")

    combined_failure_reasons = defaultdict(Counter)
    for r in campaign_results:
        for tier, reasons in r.get('failure_reasons_per_expedition', {}).items():
            combined_failure_reasons[tier].update(reasons)
    if combined_failure_reasons:
        print('\nFailure-reason breakdown by expedition tier:')
        for tier in sorted(combined_failure_reasons):
            total = sum(combined_failure_reasons[tier].values())
            print(f'  expeditions_completed {tier:>2} ({total} failed attempt(s)):')
            for reason, count in combined_failure_reasons[tier].most_common():
                print(f'    {reason:30s}: {count} ({count / total * 100:.0f}%)')

    combined_power = defaultdict(list)
    for r in campaign_results:
        for tier, entries in r.get('power_by_expedition', {}).items():
            combined_power[tier].extend(entries)
    if combined_power:
        print('\nPlayer power vs. expedition tier (at time of attempting each tier):')
        for tier in sorted(combined_power):
            entries = combined_power[tier]
            levels = [e['level'] for e in entries]
            weapons = [e['best_weapon_damage'] for e in entries]
            armors = [e['best_armor_reduction'] for e in entries]
            ammos = [e['ammo'] for e in entries]
            print(f'  expeditions_completed {tier:>2}: level {_fmt(levels)} | best weapon dmg {_fmt(weapons)} | best armor reduction {_fmt(armors)} | ammo {_fmt(ammos)}')

    print()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--games", type=int, default=20, help="number of games to simulate (default: 20)")
    parser.add_argument("--level", type=int, default=1, help="starting level for every game (default: 1)")
    parser.add_argument(
        "--expeditions-completed", type=int, default=0,
        help="starting expeditions_completed for every game (default: 0) - "
             "drives map size/obstacle density/zombie composition & elites/loot "
             "banding (weapons and armor), independent of --level since the "
             "map/player/campaign-level split",
    )
    parser.add_argument("--max-turns", type=int, default=400, help="per-game turn cap, to bound runaway/stuck games (default: 400)")
    parser.add_argument("--seed", type=int, default=None, help="base seed - each game uses seed+i for reproducibility; omit for random")
    parser.add_argument("--verbose", action="store_true", help="print every game message as it's generated")
    parser.add_argument("--campaign", action="store_true", help="simulate full campaigns (consecutive expeditions, one persisting character per run) instead of isolated single games")
    parser.add_argument("--campaign-runs", type=int, default=10, help="number of independent campaign playthroughs to simulate (default: 10, only used with --campaign)")
    parser.add_argument("--campaign-max-attempts", type=int, default=50, help="max retry attempts allowed at a single expedition tier before giving up on that campaign run (default: 50, only used with --campaign)")
    parser.add_argument("--force-mechanism", type=str, default=None,
                        help="pin every game to one escape mechanism (e.g. airfield_plane, "
                             "tidal_causeway) - for a per-family solve/survival check")
    args = parser.parse_args()

    if args.campaign:
        campaign_results = []
        for i in range(args.campaign_runs):
            seed = None if args.seed is None else args.seed + i * 10000
            result = play_campaign(seed, args.max_turns, args.campaign_max_attempts, verbose=args.verbose)
            campaign_results.append(result)
            status = "completed" if result['reached_campaign_length'] else f"stuck at expedition {result['stuck_at']}"
            print(f"campaign {i + 1}/{args.campaign_runs}: {status} after {result['total_attempts']} attempts, final level {result['final_level']}")
        print_campaign_report(campaign_results, args.campaign_runs, args.campaign_max_attempts)
        return

    all_metrics = []
    for i in range(args.games):
        seed = None if args.seed is None else args.seed + i
        metrics = play_one_game(
            args.level, args.expeditions_completed, seed, args.max_turns,
            verbose=args.verbose, force_mechanism=args.force_mechanism,
        )
        all_metrics.append(metrics)
        print(f"game {i + 1}/{args.games}: {metrics.outcome} in {metrics.turns} turns, "
              f"final level {metrics.final_level}, min health {metrics.min_health}")

    print_report(all_metrics, args.games, args.level, args.expeditions_completed, args.max_turns)


if __name__ == "__main__":
    main()
