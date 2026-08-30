"""Reachability and carving over a map grid (game.map, a list of rows
of tile dicts). Pure - no engine imports. Shared by src/worldgen and
src/escape."""
from collections import deque

IMPASSABLE = ('mountain', 'river')

def _wh(n):
    """`n` is either a square side (int) or a (width, height) pair -
    landscape maps (docs/MAP_REALISM_SPEC.md) pass the pair."""
    return (n, n) if isinstance(n, int) else (n[0], n[1])

def _passable(grid, n, x, y):
    w, h = _wh(n)
    if not (0 <= x < w and 0 <= y < h):
        return False
    c = grid[y][x]
    return isinstance(c, dict) and c.get('terrain') not in IMPASSABLE

def reachable_set(grid, n, start):
    seen = {start}
    q = deque([start])
    while q:
        x, y = q.popleft()
        for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nx, ny = x + dx, y + dy
            if (nx, ny) not in seen and _passable(grid, n, nx, ny):
                seen.add((nx, ny))
                q.append((nx, ny))
    return seen

def is_reachable(grid, n, start, goal):
    if start == goal:
        return True
    return goal in reachable_set(grid, n, start)

def shortest_path(grid, n, start, goal):
    prev = {start: None}
    q = deque([start])
    while q:
        cur = q.popleft()
        if cur == goal:
            out = []
            while cur is not None:
                out.append(cur)
                cur = prev[cur]
            return out[::-1]
        x, y = cur
        for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nx, ny = x + dx, y + dy
            if (nx, ny) not in prev and _passable(grid, n, nx, ny):
                prev[(nx, ny)] = cur
                q.append((nx, ny))
    return None