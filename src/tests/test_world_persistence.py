"""v4 Stage 2B - world persistence (dropped items, defeated zombies,
abandonment states)."""

import unittest

from src.game import Apocrysis
from src.items import MeleeWeapon
from src.zombies import FreshZombie


class _IO:
    renders_natively = True

    def __init__(self):
        self.log = []

    def say(self, *a, **k):
        self.log.append(" ".join(str(x) for x in a))

    def ask(self, prompt=""):
        return "q"

    def ask_yes_no(self, prompt):
        return True


class TestWorldPersistence(unittest.TestCase):
    def setUp(self):
        self.io = _IO()
        self.game = Apocrysis("PersistTest", map_size=14, seed=7, io=self.io)

    def test_dropped_weapon_persists_on_the_tile_and_is_reclaimed(self):
        g = self.game
        g.backpack.add_weapon(MeleeWeapon("Machete", 14, 40))
        start = g.current_position
        g.drop_weapon("Machete")

        cell = g.map[start[1]][start[0]]
        self.assertTrue(cell.get("ground"), "dropped weapon should be on the tile")
        self.assertFalse(any(w.name == "Machete" for w in g.backpack.weapons))

        # leave and come back
        moved = None
        for d in ("n", "s", "e", "w"):
            g.move_and_search(d)
            if g.current_position != start:
                moved = d
                break
        self.assertIsNotNone(moved, "test needs one legal move off the start tile")
        g.move_and_search({"n": "s", "s": "n", "e": "w", "w": "e"}[moved])

        self.assertEqual(g.current_position, start)
        self.assertTrue(any(w.name == "Machete" for w in g.backpack.weapons),
                        "the weapon should be picked back up on return")
        self.assertFalse(g.map[start[1]][start[0]].get("ground"))

    def test_defeated_tile_zombie_clears_back_to_terrain(self):
        g = self.game
        x, y = g.current_position
        z = FreshZombie()
        z.health = 1
        g.map[y][x] = z  # a zombie standing on the player's tile

        g.punch()  # 1-HP zombie dies to a punch

        cell = g.map[y][x]
        self.assertIsInstance(cell, dict)
        self.assertNotIn(cell.get("terrain"), (None,))
        self.assertNotIn((x, y), g.zombie_positions)

    def test_buildings_carry_a_generated_abandonment_cause(self):
        g = self.game
        building_cells = [
            cell for row in g.map for cell in row
            if isinstance(cell, dict) and cell.get("terrain") in ("building", "town")
        ]
        self.assertTrue(building_cells, "seed 7 map should have some buildings")
        for cell in building_cells:
            self.assertIn(cell.get("abandonment"), g._ABANDONMENT_FLAVOUR)


if __name__ == "__main__":
    unittest.main()
