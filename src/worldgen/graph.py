"""MapGraph - the connectivity graph over a realised map. Nodes are
named points of interest (spawn, exit, mystery sites, settlement
centres); edges are BFS distances over passable terrain. The engine
uses this to GUARANTEE reachability by design instead of patching it
afterward. See docs/PHASE_C_SPEC.md.

Pure - imports only src.worldgen.reachable.
"""
from src.worldgen.reachable import reachable_set, shortest_path


class MapGraph:
    def __init__(self, grid, n, nodes):
        self._grid = grid
        self._n = n
        self.nodes = dict(nodes)
        self._reach = {}
        self.adj = {}
        for name, xy in self.nodes.items():
            seen = reachable_set(grid, n, xy)
            self._reach[name] = seen
            self.adj[name] = {
                other: self._path_len(xy, oxy)
                for other, oxy in self.nodes.items()
                if other != name and oxy in seen
            }

    def _path_len(self, a, b):
        p = shortest_path(self._grid, self._n, a, b)
        return None if p is None else len(p) - 1

    def reachable(self, a, b):
        return self.nodes[b] in self._reach.get(a, set())

    def distance(self, a, b):
        return self.adj.get(a, {}).get(b)

    def unreachable_from(self, root):
        """Node names not reachable from `root` (excluding root)."""
        seen = self._reach.get(root, set())
        return [name for name, xy in self.nodes.items()
                if name != root and xy not in seen]

    def critical_path_tiles(self, root, *musts):
        """The union of shortest-path tiles from `root` to each `must`
        node - the corridor a player has to be able to walk."""
        tiles = set()
        for m in musts:
            if m not in self.nodes:
                continue
            p = shortest_path(self._grid, self._n, self.nodes[root], self.nodes[m])
            if p:
                tiles.update(p)
        return tiles
