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
_OBTAINED_RE = re.compile(r"^You obtained a (.+)\.$")
_CRAFTED_RE = re.compile(r"^Crafted a (.+)!$")


class Metrics:
    """One playthrough's worth of counters, filled in as the bot plays."""

    def __init__(self):
        self.turns = 0
        self.outcome = None  # 'won' | 'died' | 'timeout'
        self.final_level = 1
        self.final_day = 1
        self.min_health = 100
        self.health_samples = []
        self.hits_dealt = []          # (level, damage) per hit landed on a zombie
        self.hits_taken = []          # (level, damage) per hit landed on the player
        self.crits = 0
        self.fights = 0
        self.zombies_defeated = 0
        self.weapons_looted = []
        self.crafted = []
        self.drops_issued = 0
        self.reloads_issued = 0
        self.equips_issued = 0
        self.max_weapon_damage_by_level = {}
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

        m = _OBTAINED_RE.match(text)
        if m:
            self.weapons_looted.append(m.group(1))
            return

        m = _CRAFTED_RE.match(text)
        if m:
            self.crafted.append(m.group(1))
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
        self.metrics.min_health = min(self.metrics.min_health, p.health)
        self.metrics.health_samples.append(p.health)
        self.metrics.max_weapon_damage_by_level[p.level] = max(
            self.metrics.max_weapon_damage_by_level.get(p.level, 0),
            _weapon_power(p.equipped_weapon)[1],
            max((w.damage for w in p.backpack.weapons), default=0),
        )

        if self.metrics.turns > self.max_turns:
            return 'x'

        # 1. Swap in a strictly stronger working weapon if the
        #    backpack has one - equip_weapon() puts the old one back,
        #    so this never loses gear, just tests the equip path.
        best = max(p.backpack.weapons, key=_weapon_power, default=None)
        if best is not None and _weapon_power(best) > _weapon_power(p.equipped_weapon):
            self.metrics.equips_issued += 1
            return f"eq {best.name}"

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

        # 4. Thin out duplicate weapons once they start piling up -
        #    exercises the new drop command instead of letting the
        #    backpack grow unbounded.
        counts = Counter(w.name for w in p.backpack.weapons)
        for name, count in counts.items():
            if count > 2:
                self.metrics.drops_issued += 1
                return f"drop {name}"

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


def play_one_game(level, seed, max_turns, verbose=False):
    io = BotIO(max_turns=max_turns, verbose=verbose)
    player = Apocrysis("BalanceBot", level=level, seed=seed, io=io)
    io.player = player

    player.run_game_loop()

    if player.won:
        io.metrics.outcome = "won"
    elif player.health <= 0:
        io.metrics.outcome = "died"
    else:
        io.metrics.outcome = "timeout"

    return io.metrics


def _fmt(values):
    if not values:
        return "n/a"
    return f"avg {statistics.mean(values):.1f}, min {min(values)}, max {max(values)}"


def print_report(all_metrics, games, level, max_turns):
    print(f"\n{'=' * 60}")
    print(f"Apocrysis balance report - {games} game(s), start level {level}, cap {max_turns} turns")
    print(f"{'=' * 60}\n")

    outcomes = Counter(m.outcome for m in all_metrics)
    print("Outcomes:")
    for key in ("won", "died", "timeout"):
        print(f"  {key:8s}: {outcomes.get(key, 0)}/{games}")

    turns = [m.turns for m in all_metrics]
    levels = [m.final_level for m in all_metrics]
    days = [m.final_day for m in all_metrics]
    min_health = [m.min_health for m in all_metrics]

    print(f"\nTurns to finish : {_fmt(turns)}")
    print(f"Final level      : {_fmt(levels)}")
    print(f"Final day        : {_fmt(days)}")
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

    max_dmg_by_level = defaultdict(list)
    for m in all_metrics:
        for lvl, dmg in m.max_weapon_damage_by_level.items():
            max_dmg_by_level[lvl].append(dmg)
    if max_dmg_by_level:
        print("\nBest weapon damage available, by player level:")
        for lvl in sorted(max_dmg_by_level):
            print(f"  level {lvl:>2}: {_fmt(max_dmg_by_level[lvl])}")

    crafted = Counter(c for m in all_metrics for c in m.crafted)
    if crafted:
        print(f"\nItems crafted (total {sum(crafted.values())}):")
        for name, count in crafted.most_common():
            print(f"  {name}: {count}")

    print(f"\nDrop command used  : {sum(m.drops_issued for m in all_metrics)} time(s)")
    print(f"Reload command used: {sum(m.reloads_issued for m in all_metrics)} time(s)")
    print(f"Equip swaps        : {sum(m.equips_issued for m in all_metrics)} time(s)")

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
    if not signals:
        signals.append("- nothing jumped out automatically; read the numbers above directly.")
    for s in signals:
        print(s)
    print()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--games", type=int, default=20, help="number of games to simulate (default: 20)")
    parser.add_argument("--level", type=int, default=1, help="starting level for every game (default: 1)")
    parser.add_argument("--max-turns", type=int, default=400, help="per-game turn cap, to bound runaway/stuck games (default: 400)")
    parser.add_argument("--seed", type=int, default=None, help="base seed - each game uses seed+i for reproducibility; omit for random")
    parser.add_argument("--verbose", action="store_true", help="print every game message as it's generated")
    args = parser.parse_args()

    all_metrics = []
    for i in range(args.games):
        seed = None if args.seed is None else args.seed + i
        metrics = play_one_game(args.level, seed, args.max_turns, verbose=args.verbose)
        all_metrics.append(metrics)
        print(f"game {i + 1}/{args.games}: {metrics.outcome} in {metrics.turns} turns, "
              f"final level {metrics.final_level}, min health {metrics.min_health}")

    print_report(all_metrics, args.games, args.level, args.max_turns)


if __name__ == "__main__":
    main()
