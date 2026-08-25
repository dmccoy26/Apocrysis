# Auto-extracted from the original monolithic apocrysis.py during
# the src/ restructuring - see README.md for the project layout.

import json
import os

from src.items import MeleeWeapon, RangedWeapon
from src.objectives import Goal, Task
from src.zombies import Zombie, FreshZombie, RegularZombie, HeavyZombie


class PersistenceMixin:

    ZOMBIE_CLASSES = {
        "FreshZombie": FreshZombie,
        "RegularZombie": RegularZombie,
        "HeavyZombie": HeavyZombie,
    }

    def _serialize_map(self):
        # Map cells are either a plain terrain dict (already JSON-safe)
        # or a real Zombie instance placed directly into the cell by
        # generate_map() - those need their type/health/attack pulled
        # out into a JSON-safe dict instead, or json.dump() would fail
        # outright on an object it doesn't know how to serialize.
        return [
            [
                {
                    "zombie_type": type(cell).__name__,
                    "health": cell.health,
                    "attack": cell.attack,
                }
                if isinstance(cell, Zombie)
                else cell
                for cell in row
            ]
            for row in self.map
        ]

    @classmethod
    def _deserialize_map(cls, map_data):
        return [
            [
                cls._zombie_from_cell(cell)
                if isinstance(cell, dict) and "zombie_type" in cell
                else cell
                for cell in row
            ]
            for row in map_data
        ]

    @classmethod
    def _zombie_from_cell(cls, cell):
        zombie_cls = cls.ZOMBIE_CLASSES.get(cell["zombie_type"], FreshZombie)
        zombie = zombie_cls()
        zombie.health = cell["health"]
        zombie.attack = cell["attack"]
        return zombie

    def save_game(self, filename="apocrysis_save.json"):
        data = {
            "name": self.name,
            "player_class": self.player_class,
            "map_size": self.map_size,
            "health": self.health,
            "max_health": self.max_health,
            "hunger": self.hunger,
            "thirst": self.thirst,
            "fatigue": self.fatigue,
            "strength": self.strength,
            "dexterity": self.dexterity,
            "intelligence": self.intelligence,
            "wisdom": self.wisdom,
            "level": self.level,
            "xp": self.xp,
            "max_xp": self.max_xp,
            "current_position": list(self.current_position),
            "time_of_day": self.time_of_day,
            "day": self.day,
            "is_night": self.is_night,
            "visibility_radius": self.visibility_radius,
            "last_action": self.last_action,
            "visited": [list(pos) for pos in self.visited],
            "backpack_food": self.backpack.food,
            "backpack_water": self.backpack.water,
            "backpack_medicine": self.backpack.medicine,
            "backpack_ammo": self.backpack.ammo,
            "weapons": [],
            "equipped_weapon": None,
            "goals": [{"title": g.title, "description": g.description, "completed": g.completed, "reward_type": g.reward_type, "reward_amount": g.reward_amount, "goal_type": getattr(g, 'goal_type', "")} for g in self.goals],
            "tasks": [{"title": t.title, "description": t.description, "completed": t.completed, "reward_type": t.reward_type, "reward_amount": t.reward_amount, "task_type": getattr(t, 'task_type', "")} for t in self.tasks],
            "status_effects": self.status_effects,
            "map": self._serialize_map(),
        }

        for w in self.backpack.weapons:
            data["weapons"].append({
                "name": w.name,
                "damage": w.damage,
                "type": type(w).__name__,
                "durability": getattr(w, 'durability', None),
                "ammo": getattr(w, 'ammo', None),
                "max_ammo": getattr(w, 'max_ammo', None)
            })

        if self.equipped_weapon:
            data["equipped_weapon"] = {
                "name": self.equipped_weapon.name,
                "damage": self.equipped_weapon.damage,
                "type": type(self.equipped_weapon).__name__,
                "durability": getattr(self.equipped_weapon, 'durability', None),
                "ammo": getattr(self.equipped_weapon, 'ammo', None),
                "max_ammo": getattr(self.equipped_weapon, 'max_ammo', None)
            }

        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Game saved to {filename}.")

    def _prompt_delete_save(self):
        try:
            save_files = [f for f in os.listdir(".") if f.endswith(".json")]
        except OSError:
            save_files = []

        if save_files:
            print("Available save files:", ", ".join(save_files))
        else:
            print("No saved games found.")
            return

        slot_name = input("Enter save slot name to delete: ").strip()
        if not slot_name.endswith(".json"):
            slot_name += ".json"
        self.delete_save(slot_name)

    def delete_save(self, filename="apocrysis_save.json"):
        if os.path.exists(filename):
            os.remove(filename)
            print(f"Saved game deleted from {filename}.")
        else:
            print("No saved game found to delete.")

    @classmethod
    def load_game(cls, filename="apocrysis_save.json"):
        if not os.path.exists(filename):
            return None
            
        with open(filename, 'r') as f:
            data = json.load(f)
            
        player = cls(
            data.get("name", "SavedPlayer"),
            data.get("player_class", "gamer"),
            data.get("map_size", 25),
        )

        player.health = data.get("health", 100)
        player.max_health = data.get("max_health", 100)
        player.hunger = data.get("hunger", 95)
        player.thirst = data.get("thirst", 95)
        player.fatigue = data.get("fatigue", 0)
        player.strength = data.get("strength", 10)
        player.dexterity = data.get("dexterity", 12)
        player.intelligence = data.get("intelligence", 13)
        player.wisdom = data.get("wisdom", 8)
        player.level = data.get("level", 1)
        player.xp = data.get("xp", 0)
        player.max_xp = data.get("max_xp", 100)
        player.day = data.get("day", 1)
        player.is_night = data.get("is_night", False)
        player.visibility_radius = data.get("visibility_radius", 3)
        player.last_action = data.get("last_action", "")

        # "won" is deliberately never restored from a save - main()'s
        # own post-game-loop check treats player.won as an immediate
        # win the moment run_game_loop() returns, so restoring True
        # here would end the loaded game before the player got a turn.

        # Backward compatible with older saves that predate map
        # persistence - falls back to whatever generate_map() already
        # built fresh during cls(...) above, same as before this fix.
        if "map" in data:
            player.map = cls._deserialize_map(data["map"])

        player.current_position = tuple(data.get("current_position", [12, 12]))
        player.time_of_day = data.get("time_of_day", 480)
        player.visited = set(tuple(pos) for pos in data.get("visited", []))
        
        # Real bug found live: this used to overwrite (=) the backpack
        # with the save file's own values, silently discarding any
        # win bonus __init__ just granted a moment earlier via
        # cls(...) above (prize_for_next_game is only checked in
        # __init__ - a load calls __init__ too, but its bonus was
        # being thrown away immediately after). Adding (+=) on top of
        # whatever __init__ already set - 0 for a normal load, or the
        # bonus amount right after a win - preserves it either way.
        player.backpack.food += data.get("backpack_food", 0)
        player.backpack.water += data.get("backpack_water", 0)
        player.backpack.medicine += data.get("backpack_medicine", 0)
        player.backpack.ammo += data.get("backpack_ammo", 0)
        
        for w_data in data.get("weapons", []):
            if w_data.get("type") == "MeleeWeapon":
                w = MeleeWeapon(w_data.get("name"), w_data.get("damage"), w_data.get("durability", 10))
            else:
                w = RangedWeapon(w_data.get("name"), w_data.get("damage"), w_data.get("max_ammo", 5), w_data.get("durability", 20))
                w.ammo = w_data.get("ammo")
            player.backpack.weapons.append(w)
            
        eq_w_data = data.get("equipped_weapon")
        if eq_w_data and eq_w_data.get("name"):
            if eq_w_data.get("type") == "MeleeWeapon":
                player.equipped_weapon = MeleeWeapon(eq_w_data.get("name"), eq_w_data.get("damage"), eq_w_data.get("durability", 10))
            else:
                player.equipped_weapon = RangedWeapon(eq_w_data.get("name"), eq_w_data.get("damage"), eq_w_data.get("max_ammo", 5), eq_w_data.get("durability", 20))
                player.equipped_weapon.ammo = eq_w_data.get("ammo")
                
        # Real bug found live: this used to APPEND the save's goals
        # onto whatever fresh __init__ already created, duplicating
        # every goal a save actually has (e.g. "Reach the Town
        # Center" once from __init__, once again from the save file).
        # A save with a real "goals" key is a complete snapshot of
        # what the player's goals actually were - it should replace
        # the fresh set, not blend with it. An older save with no
        # "goals" key at all (saved before goal persistence existed)
        # still falls back to the fresh __init__ goals untouched.
        if "goals" in data:
            player.goals = [
                Goal(
                    title=g_data["title"],
                    description=g_data.get("description", ""),
                    completed=g_data.get("completed", False),
                    reward_type=g_data.get("reward_type", "health"),
                    reward_amount=g_data.get("reward_amount", 5),
                    goal_type=g_data.get("goal_type", "")
                )
                for g_data in data["goals"]
            ]

        for t_data in data.get("tasks", []):
            player.tasks.append(Task(
                title=t_data["title"],
                description=t_data.get("description", ""),
                completed=t_data.get("completed", False),
                reward_type=t_data.get("reward_type", "xp"),
                reward_amount=t_data.get("reward_amount", 10),
                task_type=t_data.get("task_type", "")
            ))

        player.status_effects = data.get("status_effects", {})
                
        return player

