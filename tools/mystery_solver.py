#!/usr/bin/env python3
# ============================================================
# Apocrysis - generated-mystery solvability harness (v4 Stage 4)
# File: tools/mystery_solver.py
#
# Drives real generated maps to a win using ONLY player commands
# (move / search / clear / escape), navigating with BFS. Reports the
# solve rate and turn counts across many seeds - the "player
# solvability" guarantee from the design doc's Escape Proof section.
#
#   python3 tools/mystery_solver.py [n_seeds]
# ============================================================

import sys
import os
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.game import Apocrysis  # noqa: E402


class QuietIO:
    renders_natively = True

    def __init__(self):
        self.log = []
        self.game = None  # set by solve()

    def say(self, *a, **k):
        self.log.append(" ".join(str(x) for x in a))

    def ask(self, prompt=""):
        return "q"

    def ask_yes_no(self, prompt):
        # Fight when reasonably healthy (the solver is a competent-
        # enough player - combat survivability is the balance harness's
        # job, not this one's), flee when hurt.
        g = self.game
        return bool(g and g.health > 45)


def _passable(cell, goal_tile, xy):
    if isinstance(cell, dict):
        return cell.get("terrain") not in ("mountain", "river")
    return xy == goal_tile  # a zombie tile is only "enterable" if it's the target


def bfs(game, start, goal):
    n = game.map_size
    prev = {start: None}
    q = deque([start])
    while q:
        cur = q.popleft()
        if cur == goal:
            path = []
            while cur is not None:
                path.append(cur)
                cur = prev[cur]
            return path[::-1]
        x, y = cur
        for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < n and 0 <= ny < n and (nx, ny) not in prev:
                if _passable(game.map[ny][nx], goal, (nx, ny)):
                    prev[(nx, ny)] = cur
                    q.append((nx, ny))
    return None


def _step(game, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    return {(0, 1): "s", (0, -1): "n", (1, 0): "e", (-1, 0): "w"}[(dx, dy)]


def _maintain(game):
    if game.hunger < 45 and game.backpack.food > 0:
        game.eat()
    if game.thirst < 45 and game.backpack.water > 0:
        game.drink()
    if game.health < 55 and game.backpack.medicine > 0:
        game.use_medicine()
    # equip the strongest weapon available
    pool = list(game.backpack.weapons) + ([game.equipped_weapon] if game.equipped_weapon else [])
    if pool:
        best = max(pool, key=lambda w: getattr(w, "damage", 0))
        if best is not game.equipped_weapon:
            game.equip_weapon(best.name)
    # hole up in a building when badly hurt
    tile = game.map[game.current_position[1]][game.current_position[0]]
    if isinstance(tile, dict) and tile.get("terrain") == "building" and game.health < 45:
        for _ in range(6):
            if game.health > 80 or game.fatigue == 0:
                break
            game.rest()


def walk_to(game, target, turns):
    for _ in range(500):
        if game.current_position == target:
            return True
        _maintain(game)
        path = bfs(game, game.current_position, target)
        if not path or len(path) < 2:
            return game.current_position == target
        game.move_and_search(_step(game, path[0], path[1]))
        turns[0] += 1
        if game.health <= 0:
            return False
    return False


def solve(seed, expeditions=0):
    io = QuietIO()
    game = Apocrysis(f"Solver{seed}", seed=seed, expeditions_completed=expeditions, io=io)
    io.game = game
    m = game.mystery
    if m is None:
        return ("no-mystery", 0, None)
    turns = [0]

    # visit route + closed + require, searching each; then obstacle, then escape
    for role in ("closed", "route", "require"):
        if not walk_to(game, m.sites[role], turns):
            tag = "died-" if game.health <= 0 else "stuck-"
            return (tag + role, turns[0], m.mechanism)
        game.mystery_search()

    # approach the obstacle (walk_to its tile triggers the clear-with-item
    # path once we have the item; we searched 'require' so we should)
    ox, oy = m.obstacle_tile
    approach = None
    for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        c = game.map[oy + dy][ox + dx] if 0 <= ox + dx < game.map_size and 0 <= oy + dy < game.map_size else None
        if isinstance(c, dict) and c.get("terrain") not in ("mountain", "river"):
            approach = (ox + dx, oy + dy)
            break
    if approach and not walk_to(game, approach, turns):
        tag = "died-" if game.health <= 0 else "stuck-"
        return (tag + "approach", turns[0], m.mechanism)
    game.move_and_search(_step(game, game.current_position, m.obstacle_tile))  # clears in place
    turns[0] += 1

    if not m.obstacle_open:
        return ("obstacle-not-cleared", turns[0], m.mechanism)

    if not walk_to(game, m.escape_tile, turns):
        tag = "died-" if game.health <= 0 else "stuck-"
        return (tag + "escape", turns[0], m.mechanism)
    game.mystery_try_escape()
    return ("WIN" if game.won else "no-win", turns[0], m.mechanism)


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    from collections import Counter
    outcomes = Counter()
    wins = []
    for seed in range(n):
        result, turns, mech = solve(seed, expeditions=seed % 8)
        outcomes[result] += 1
        if result == "WIN":
            wins.append(turns)
        else:
            print(f"  seed {seed:3d} [{mech}] -> {result} ({turns} turns)")
    print()
    for k, v in outcomes.most_common():
        print(f"  {k}: {v}")
    if wins:
        wins.sort()
        print(f"\n  win turns: min {wins[0]}, median {wins[len(wins)//2]}, max {wins[-1]}")
