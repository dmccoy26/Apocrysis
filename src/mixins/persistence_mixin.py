# Auto-extracted from the original monolithic apocrysis.py during
# the src/ restructuring - see README.md for the project layout.

import glob
import json
import os
import re

from src.items import MeleeWeapon, RangedWeapon, Armor
from src.objectives import Goal, Task
from src.zombies import Zombie, FreshZombie, RegularZombie, HeavyZombie


DEFAULT_PROFILE_FILENAME = "apocrysis_profile.json"


def profile_filename_for_name(name):
    """
    Derives a per-player profile filename from a display name, e.g.
    "Jess" -> "apocrysis_profile_Jess.json". Non-filename-safe
    characters are collapsed to "_" so an arbitrary player-entered
    name can't escape the current directory or collide with the
    named SESSION save-slot files (apocrysis_save*.json - a
    different concept, see the profile-persistence note below).
    """
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", name.strip()) or "player"
    return f"apocrysis_profile_{slug}.json"


def _serialize_weapon(w):
    return {
        "name": w.name,
        "damage": w.damage,
        "type": type(w).__name__,
        "durability": getattr(w, 'durability', None),
        "ammo": getattr(w, 'ammo', None),
        "max_ammo": getattr(w, 'max_ammo', None),
    }


def _deserialize_weapon(w_data):
    w_type = w_data.get("type")
    if w_type == "MeleeWeapon":
        return MeleeWeapon(
            w_data.get("name"), w_data.get("damage"),
            w_data.get("durability", 10),
        )
    elif w_type == "RangedWeapon":
        w = RangedWeapon(
            w_data.get("name"), w_data.get("damage"),
            w_data.get("max_ammo", 5), w_data.get("durability", 20),
        )
        w.ammo = w_data.get("ammo")
        return w
    else:
        raise ValueError(f'Unknown weapon type: {w_type}')


def _serialize_armor(a):
    return {
        "name": a.name,
        "damage_reduction": a.damage_reduction,
        "durability": a.durability,
        "max_durability": a.max_durability,
        "slot": a.slot,
    }


def _deserialize_armor(a_data):
    armor = Armor(
        a_data.get("name"), a_data.get("damage_reduction"),
        a_data.get("max_durability", 10),
        # Falls back to "body" for a save written before the multi-
        # piece follow-up (single equipped_armor object, no slot
        # field) - matches that design's implicit single body slot.
        a_data.get("slot", "body"),
    )
    armor.durability = a_data.get("durability", armor.max_durability)
    return armor


def _restore_equipped_armor(player, eq_a_data):
    """
    Shared by load_game() and apply_profile(). Handles both the
    current shape (a dict of slot -> serialized piece or {}) and the
    legacy single-slot shape (a save/profile written before the
    multi-piece follow-up, where "equipped_armor" was either None or
    one serialized piece directly, with no per-slot keys).
    """
    if not eq_a_data:
        return
    if "name" in eq_a_data:
        # Legacy single-piece shape - _deserialize_armor() already
        # falls back to the "body" slot when no "slot" key is present.
        piece = _deserialize_armor(eq_a_data)
        player.equipped_armor[piece.slot] = piece
        return
    for slot, piece_data in eq_a_data.items():
        if piece_data and piece_data.get("name") and slot in player.equipped_armor:
            player.equipped_armor[slot] = _deserialize_armor(piece_data)


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
        zombie_cls = cls.ZOMBIE_CLASSES.get(cell.get("zombie_type"), FreshZombie)
        zombie = zombie_cls()
        zombie.health = cell.get("health", zombie.health)
        zombie.attack = cell.get("attack", zombie.attack)
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
            "day_phase": self.day_phase,
            "visibility_radius": self.visibility_radius,
            "has_flashlight": self.has_flashlight,
            "last_action": self.last_action,
            "visited": [list(pos) for pos in self.visited],
            "backpack_food": self.backpack.food,
            "backpack_water": self.backpack.water,
            "backpack_medicine": self.backpack.medicine,
            "backpack_ammo": self.backpack.ammo,
            "weapons": [],
            "equipped_weapon": None,
            "armor": [],
            "equipped_armor": {},
            "goals": [{"title": g.title, "description": g.description, "completed": g.completed, "reward_type": g.reward_type, "reward_amount": g.reward_amount, "goal_type": getattr(g, 'goal_type', "")} for g in self.goals],
            "tasks": [{"title": t.title, "description": t.description, "completed": t.completed, "reward_type": t.reward_type, "reward_amount": t.reward_amount, "task_type": getattr(t, 'task_type', "")} for t in self.tasks],
            "status_effects": self.status_effects,
            "map": self._serialize_map(),
            "town_known": self.town_known,
            "map_revealed": getattr(self, 'map_revealed', False),
            "knowledge": self.knowledge.to_dict() if getattr(self, 'knowledge', None) else None,
            "mystery": self.mystery.to_dict() if getattr(self, 'mystery', None) else None,
            "slice_mode": getattr(self, 'slice_mode', False),
        }

        for w in self.backpack.weapons:
            data["weapons"].append(_serialize_weapon(w))

        if self.equipped_weapon:
            data["equipped_weapon"] = _serialize_weapon(self.equipped_weapon)

        for a in self.backpack.armor:
            data["armor"].append(_serialize_armor(a))

        data["equipped_armor"] = {
            slot: _serialize_armor(piece)
            for slot, piece in self.equipped_armor.items()
            if piece
        }

        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        self.io.say(f"Game saved to {filename}.")

    def _prompt_delete_save(self):
        try:
            save_files = [f for f in os.listdir(".") if f.endswith(".json")]
        except OSError:
            save_files = []

        if save_files:
            self.io.say("Available save files:", ", ".join(save_files))
        else:
            self.io.say("No saved games found.")
            return

        slot_name = self.io.ask("Enter save slot name to delete: ").strip()
        if not slot_name.endswith(".json"):
            slot_name += ".json"
        self.delete_save(slot_name)

    def delete_save(self, filename="apocrysis_save.json"):
        if os.path.exists(filename):
            os.remove(filename)
            self.io.say(f"Saved game deleted from {filename}.")
        else:
            self.io.say("No saved game found to delete.")

    @classmethod
    def load_game(cls, filename="apocrysis_save.json"):
        if not os.path.exists(filename):
            return None
            
        with open(filename, 'r') as f:
            data = json.load(f)
            
        player = cls(
            data.get("name", "SavedPlayer"),
            map_size=data.get("map_size", 25),
            level=data.get("level", 1),
        )

        # player_class is no longer chosen (v3) - restored here purely
        # for older-save display/compatibility; initialize_player()
        # already set it to the current STARTER_CLASS_NAME, and the
        # tier system (combat_mixin.py's level_up()) is what actually
        # updates it going forward.
        player.player_class = data.get("player_class", player.player_class)

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
        player.day_phase = data.get("day_phase", "day")
        player.visibility_radius = data.get("visibility_radius", 3)
        player.has_flashlight = data.get("has_flashlight", False)
        player.last_action = data.get("last_action", "")
        player.town_known = data.get("town_known", False)
        player.map_revealed = data.get("map_revealed", False)

        # v4 knowledge/mystery - restored verbatim (the map is restored,
        # not regenerated, so the mystery can't be rebuilt). Older saves
        # have neither key: keep whatever __init__ built.
        if data.get("mystery") is not None:
            from src.escape import Mystery
            player.mystery = Mystery.from_dict(data["mystery"])
            player.knowledge = player.mystery.knowledge
        elif data.get("knowledge") is not None:
            from src.knowledge import Knowledge
            player.mystery = None
            player.knowledge = Knowledge.from_dict(data["knowledge"])

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
        
        # Full-state restore: SET the backpack to exactly what was
        # saved, then re-add any win prize __init__ granted this
        # construction (recorded on player._prize_bonus). This replaces
        # an older fragile "+=" that assumed __init__ left consumables
        # at 0 - no longer true with v4's fresh-start ration.
        _prize = getattr(player, "_prize_bonus", {}) or {}
        player.backpack.food = data.get("backpack_food", 0) + _prize.get("food", 0)
        player.backpack.water = data.get("backpack_water", 0) + _prize.get("water", 0)
        player.backpack.medicine = data.get("backpack_medicine", 0) + _prize.get("medicine", 0)
        player.backpack.ammo = data.get("backpack_ammo", 0) + _prize.get("ammo", 0)
        
        for w_data in data.get("weapons", []):
            player.backpack.weapons.append(_deserialize_weapon(w_data))

        eq_w_data = data.get("equipped_weapon")
        if eq_w_data and eq_w_data.get("name"):
            player.equipped_weapon = _deserialize_weapon(eq_w_data)

        for a_data in data.get("armor", []):
            player.backpack.armor.append(_deserialize_armor(a_data))

        _restore_equipped_armor(player, data.get("equipped_armor"))


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

        # Same pattern as goals: a save with a "tasks" key is a
        # complete snapshot of what the player's tasks actually were.
        # Replace the fresh __init__ tasks rather than appending to
        # avoid duplication. Older saves without a "tasks" key fall
        # back to the fresh __init__ tasks untouched.
        if "tasks" in data:
            player.tasks = [
                Task(
                    title=t_data["title"],
                    description=t_data.get("description", ""),
                    completed=t_data.get("completed", False),
                    reward_type=t_data.get("reward_type", "xp"),
                    reward_amount=t_data.get("reward_amount", 10),
                    task_type=t_data.get("task_type", "")
                )
                for t_data in data["tasks"]
            ]

        player.status_effects = data.get("status_effects", {})

        return player

    # --------------------------------------------------
    # Profile persistence (v3 SPRINT, step 1)
    # --------------------------------------------------
    #
    # Distinct from save_game()/load_game() above on purpose: those
    # capture a full playthrough snapshot (map, position, day/time)
    # for exact resume. The profile is the player's IDENTITY and
    # PROGRESSION only (name/level/xp/stats/backpack/weapon) - what
    # should carry into a brand new game (a new map, sized/placed
    # from the carried-forward level - see game.py's __init__ and
    # world_mixin.py's generate_map()), not a resume of the old map.
    # cli.py's main() uses these instead of prompting for name/class
    # on every launch when a profile already exists.

    def save_profile(self, filename=DEFAULT_PROFILE_FILENAME):
        data = {
            "name": self.name,
            "player_class": self.player_class,
            "level": self.level,
            "xp": self.xp,
            "max_xp": self.max_xp,
            "strength": self.strength,
            "dexterity": self.dexterity,
            "intelligence": self.intelligence,
            "wisdom": self.wisdom,
            "backpack_food": self.backpack.food,
            "backpack_water": self.backpack.water,
            "backpack_medicine": self.backpack.medicine,
            "backpack_ammo": self.backpack.ammo,
            "weapons": [_serialize_weapon(w) for w in self.backpack.weapons],
            "equipped_weapon": (
                _serialize_weapon(self.equipped_weapon)
                if self.equipped_weapon
                else None
            ),
            "armor": [_serialize_armor(a) for a in self.backpack.armor],
            "equipped_armor": {
                slot: _serialize_armor(piece)
                for slot, piece in self.equipped_armor.items()
                if piece
            },
            "hardcore": getattr(self, "hardcore", False),
            "expeditions_completed": self.expeditions_completed,
            "has_flashlight": getattr(self, "has_flashlight", False),
            # Story-variety guarantee (schema 3a) must survive quit/
            # relaunch, not just live for one session - a kid playing
            # one expedition per sitting got the same mechanism twice.
            "used_mechanisms": list(getattr(self.__class__, "_used_mechanisms", []) or []),
            "last_family": getattr(self.__class__, "_last_family", None),
        }

        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def load_profile(filename=DEFAULT_PROFILE_FILENAME):
        if not os.path.exists(filename):
            return None

        with open(filename, 'r') as f:
            return json.load(f)

    @staticmethod
    def list_profile_names():
        """
        Display names of every selectable profile: one per
        apocrysis_profile_<name>.json file on disk (name read from
        the file's own "name" field, not derived from the filename,
        so display casing survives the slugging in
        profile_filename_for_name()), plus the legacy single
        apocrysis_profile.json file if it's still present and hasn't
        been migrated into the per-name scheme yet (see
        load_profile_by_name()).
        """
        names = []
        for path in sorted(glob.glob("apocrysis_profile_*.json")):
            data = PersistenceMixin.load_profile(path)
            name = data.get("name") if data else None
            if name and name not in names:
                names.append(name)

        legacy = PersistenceMixin.load_profile(DEFAULT_PROFILE_FILENAME)
        legacy_name = legacy.get("name") if legacy else None
        if legacy_name and legacy_name not in names:
            names.append(legacy_name)

        return names

    @classmethod
    def load_profile_by_name(cls, name):
        """
        Loads the profile for `name` from its own per-name file. The
        first time a name is picked that only exists in the legacy
        single apocrysis_profile.json (pre-multi-profile saves),
        transparently migrates it into a per-name file and returns
        that instead, so every profile from here on lives at a
        name-derived path.
        """
        per_name_file = profile_filename_for_name(name)
        profile = cls.load_profile(per_name_file)
        if profile is not None:
            return profile

        legacy = cls.load_profile(DEFAULT_PROFILE_FILENAME)
        if legacy is not None and legacy.get("name") == name:
            with open(per_name_file, 'w') as f:
                json.dump(legacy, f, indent=2)
            return legacy

        return None

    def delete_profile(self):
        """
        Removes this player's own profile file - the permadeath path
        for a hardcore character who died, so the next launch can't
        reload a dead hardcore run under this name.
        """
        filename = profile_filename_for_name(self.name)
        if os.path.exists(filename):
            os.remove(filename)

        legacy = self.load_profile(DEFAULT_PROFILE_FILENAME)
        if legacy is not None and legacy.get("name") == self.name:
            os.remove(DEFAULT_PROFILE_FILENAME)

    def apply_profile(self, profile):
        """
        Overwrites this (freshly constructed) instance's identity/
        progression fields from a profile dict (load_profile()'s
        return value) - same after-construction-overwrite pattern
        __init__ already uses for prize_for_next_game, just applied
        explicitly by the caller instead of automatically.
        """

        self.name = profile.get("name", self.name)
        self.player_class = profile.get("player_class", self.player_class)
        self.hardcore = profile.get("hardcore", getattr(self, "hardcore", False))
        self.expeditions_completed = profile.get("expeditions_completed", self.expeditions_completed)
        # Restore the escape-story shuffle-bag so the "no back-to-back
        # family" rule holds across sessions, not just within one.
        _um = profile.get("used_mechanisms")
        if _um is not None:
            self.__class__._used_mechanisms = list(_um)
        if profile.get("last_family") is not None:
            self.__class__._last_family = profile["last_family"]
        self.has_flashlight = profile.get("has_flashlight", getattr(self, "has_flashlight", False))
        self._update_time(0)  # refresh visibility_radius for a restored flashlight, without advancing time
        self.level = profile.get("level", self.level)
        self.xp = profile.get("xp", self.xp)
        self.max_xp = profile.get("max_xp", self.max_xp)
        self.strength = profile.get("strength", self.strength)
        self.dexterity = profile.get("dexterity", self.dexterity)
        self.intelligence = profile.get("intelligence", self.intelligence)
        self.wisdom = profile.get("wisdom", self.wisdom)

        # SET from the profile, then re-add any win prize __init__ just
        # granted (recorded on self._prize_bonus) - same handling as
        # load_game(). Replaces the older fragile "+=".
        _prize = getattr(self, "_prize_bonus", {}) or {}
        self.backpack.food = profile.get("backpack_food", 0) + _prize.get("food", 0)
        self.backpack.water = profile.get("backpack_water", 0) + _prize.get("water", 0)
        self.backpack.medicine = profile.get("backpack_medicine", 0) + _prize.get("medicine", 0)
        self.backpack.ammo = profile.get("backpack_ammo", 0) + _prize.get("ammo", 0)

        for w_data in profile.get("weapons", []):
            self.backpack.weapons.append(_deserialize_weapon(w_data))

        eq_w_data = profile.get("equipped_weapon")
        if eq_w_data and eq_w_data.get("name"):
            self.equipped_weapon = _deserialize_weapon(eq_w_data)

        for a_data in profile.get("armor", []):
            self.backpack.armor.append(_deserialize_armor(a_data))

        _restore_equipped_armor(self, profile.get("equipped_armor"))