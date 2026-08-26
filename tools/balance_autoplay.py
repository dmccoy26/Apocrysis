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
and otherwise walk a precomputed shortest path toward the Town
Center.

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

from src.constants import IMPASSABLE_TERRAIN
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
        self.reloads_issued = 0
        self.equips_issued = 0
        self.armor_equips_issued = 0
        self.flashlights_found = 0
        self.campaign_completions = 0
        self.max_weapon_damage_by_expedition = {}
        self.max_armor_reduction_by_expedition = {}
        self._current_zombie_name = None

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


def _find_town_center(player):
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
        if p.thirst < 40 and p.backpack.water > 0:
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
        return self._next_move()

    def _next_move(self):
        p = self.player
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


def play_one_game(level, expeditions_completed, seed, max_turns, verbose=False):
    io = BotIO(max_turns=max_turns, verbose=verbose)
    player = Apocrysis(
        "BalanceBot", level=level, expeditions_completed=expeditions_completed,
        seed=seed, io=io,
    )
    io.player = player

    player.run_game_loop()

    if player.won:
        io.metrics.outcome = "won"
    elif player.health <= 0:
        io.metrics.outcome = "died"
    else:
        io.metrics.outcome = "timeout"

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
    from src.constants import CAMPAIGN_LENGTH

    profile = None
    level = 1
    expeditions_completed = 0
    total_attempts = 0
    attempts_per_expedition = defaultdict(int)

    with tempfile.TemporaryDirectory() as tmp:
        profile_path = os.path.join(tmp, 'campaign_profile.json')

        while expeditions_completed < CAMPAIGN_LENGTH:
            attempts_per_expedition[expeditions_completed] += 1
            total_attempts += 1

            if attempts_per_expedition[expeditions_completed] > max_attempts_per_tier:
                return {
                    'reached_campaign_length': False,
                    'total_attempts': total_attempts,
                    'attempts_per_expedition': dict(attempts_per_expedition),
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
        'final_level': level,
        'stuck_at': None,
    }


def _fmt(values):
    if not values:
        return "n/a"
    return f"avg {statistics.mean(values):.1f}, min {min(values)}, max {max(values)}"


def print_report(all_metrics, games, level, expeditions_completed, max_turns):
    print(f"\n{'=' * 60}")
    print(
        f"Apocrysis balance report - {games} game(s), start level {level}, "
        f"expeditions_completed {expeditions_completed}, cap {max_turns} turns"
    )
    print(f"{'=' * 60}\n")

    outcomes = Counter(m.outcome for m in all_metrics)
    print("Outcomes:")
    for key in ("won", "died", "timeout"):
        print(f"  {key:8s}: {outcomes.get(key, 0)}/{games}")

    turns = [m.turns for m in all_metrics]
    levels = [m.final_level for m in all_metrics]
    days = [m.final_day for m in all_metrics]
    min_health = [m.min_health for m in all_metrics]
    final_expeditions = [m.final_expeditions_completed for m in all_metrics]

    print(f"\nTurns to finish : {_fmt(turns)}")
    print(f"Final level      : {_fmt(levels)}")
    print(f"Final day        : {_fmt(days)}")
    print(f"Final expeditions_completed: {_fmt(final_expeditions)}")
    print(f"Lowest health seen: {_fmt(min_health)}")

    near_death = sum(1 for m in all_metrics if m.min_health <= 15)
    print(f"Games with a near-death moment (health <= 15): {near_death}/{games}")

    all_dealt = [d for m in all_metrics for _, d in m.hits_dealt]
    all_taken = [d for m in all_metrics for _, d in m.hits_taken]
    total_fights = sum(m.fights for m in all_metrics)
    total_defeated = sum(m.zombies_defeated for m in all_metrics)
    total_crits = sum(m.crits for m in all_metrics)

    print(f"\nZombie encounters : {total_fights}")
    print(f"Zombies defeated  : {total_defeated} ({(total_defeated / total_fights * 100) if total_fights else 0:.0f}% of encounters)")
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

    levels_seen = sorted(set(dealt_by_level) | set(taken_by_level))
    if levels_seen:
        print("\nDealt:taken ratio by player level (rising ratio = player pulling ahead of the difficulty curve):")
        for lvl in levels_seen:
            d = dealt_by_level.get(lvl, [])
            t = taken_by_level.get(lvl, [])
            if not d or not t:
                continue
            ratio = statistics.mean(d) / max(1, statistics.mean(t))
            print(f"  level {lvl:>2}: dealt avg {statistics.mean(d):5.1f}  taken avg {statistics.mean(t):5.1f}  ratio {ratio:5.2f}x  (n={len(d)}/{len(t)})")

    weapon_names = Counter(w for m in all_metrics for w in m.weapons_looted)
    print(f"\nWeapons looted (total {sum(weapon_names.values())}):")
    for name, count in weapon_names.most_common(10):
        print(f"  {name}: {count}")

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
            if d and t:
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
            print(f"  expeditions_completed {tier:>2}: {_fmt(tier_attempts[tier])}  (n={len(tier_attempts[tier])} campaigns reached this tier)")

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
            verbose=args.verbose,
        )
        all_metrics.append(metrics)
        print(f"game {i + 1}/{args.games}: {metrics.outcome} in {metrics.turns} turns, "
              f"final level {metrics.final_level}, min health {metrics.min_health}")

    print_report(all_metrics, args.games, args.level, args.expeditions_completed, args.max_turns)


if __name__ == "__main__":
    main()
