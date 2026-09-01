# Auto-extracted from the original monolithic apocrysis.py during
# the src/ restructuring - see README.md for the project layout.

import glob
import json
import os
import re

from src import runtime_paths
from src.constants import LOOT_WEAPON_TABLE, ARMOR_TABLE
from src.items import MeleeWeapon, RangedWeapon, Armor
from src.zombies import Zombie, FreshZombie, RegularZombie, HeavyZombie


def _apply_heir_advantage(player, depth):
    """1d: the survivability floor a campaign inherits when a survivor
    dies. A heir starts a fresh life, but the *campaign's* accumulated
    preparation carries: a modest level floor, a real weapon (not the
    class default), one body-armour piece, and the depth-scaled ration
    floor. Everything here is ~2-3 expeditions behind what a survivor
    who actually reached `depth` would have, so the heir is still
    clearly weaker than the survivor they replace - just not
    defenceless. Combat formulas / encounter rates / the difficulty
    curve are untouched. See docs/COMBAT_PROGRESSION_PASS.md.
    """
    from src.game import depth_supply_bonus
    if depth <= 0:
        return

    # level floor ~0.45/depth: depth 3 -> L2, depth 6 -> L3, depth 12 -> L6
    lvl = max(player.level, 1 + round(depth * 0.45))
    bump = lvl - player.level
    if bump > 0:
        player.level = lvl
        player.strength += bump
        player.dexterity += bump
        player.max_health += 5 * bump
        player.health = player.max_health

    # a weapon ~4 expeditions back - never a downgrade, and always
    # short of the best a lucky survivor at this depth might have
    _band = max(0, depth - 4)
    _melee = [(n, s) for n, s in LOOT_WEAPON_TABLE.items()
              if s["type"] == "melee" and s.get("min_expedition", 0) <= _band]
    if _melee:
        n, s = max(_melee, key=lambda kv: kv[1]["damage"])
        if s["damage"] > getattr(player.equipped_weapon, "damage", 0):
            player.equipped_weapon = MeleeWeapon(n, s["damage"], s["durability"])

    # one body-armour piece ~4 expeditions back
    _aband = max(0, depth - 4)
    _body = [(n, s) for n, s in ARMOR_TABLE.items()
             if s["slot"] == "body" and s.get("min_expedition", 0) <= _aband]
    if _body and not player.equipped_armor.get("body"):
        n, s = max(_body, key=lambda kv: kv[1]["reduction"])
        player.equipped_armor["body"] = Armor(n, s["reduction"], s["durability"], "body")

    # the ration floor (mirrors the depth_supply_bonus a real run accrues)
    _b = depth_supply_bonus(depth)
    player.backpack.food = max(player.backpack.food, 10 + _b)
    player.backpack.water = max(player.backpack.water, 10 + _b)


DEFAULT_PROFILE_FILENAME = "apocrysis_profile.json"

# Phase B: the profile is one file with two logical records - a CAMPAIGN
# record (what's been figured out; survives every death) and a SURVIVOR
# record (identity/progression/gear; replaced when a survivor dies).
# These top-level keys belong to the campaign; everything else is
# survivor. Used to migrate a legacy flat Phase-A profile.
_CAMPAIGN_KEYS = (
    "world_id",
    "hardcore", "expeditions_completed", "used_mechanisms", "last_family",
    "recent_mechanisms", "recent_signatures", "world_investigation",
    "survivor_knowledge", "survivors_lost", "ending", "distance_walked",
)


def _normalise_profile(data):
    """Return the {"campaign": {...}, "survivor": {...}} shape from
    either that shape or a legacy flat Phase-A profile (all keys at the
    top level)."""
    if data is None:
        return None
    if "campaign" in data or "survivor" in data:
        data.setdefault("campaign", {})
        data.setdefault("survivor", {})
        return data
    campaign = {k: data[k] for k in _CAMPAIGN_KEYS if k in data}
    survivor = {k: v for k, v in data.items() if k not in _CAMPAIGN_KEYS}
    return {"campaign": campaign, "survivor": survivor}


def _profile_flat(profile):
    """A campaign+survivor profile flattened to one dict for the
    field-by-field restore in apply_profile(). The two record's key sets
    are disjoint, so the merge is lossless."""
    if profile is None:
        return {}
    if "campaign" not in profile and "survivor" not in profile:
        return profile  # already flat (a caller passed a raw dict)
    return {**profile.get("campaign", {}), **profile.get("survivor", {})}


def _profile_name(data):
    d = _normalise_profile(data)
    return d["survivor"].get("name") if d else None


def clean_display_name(raw, fallback="Survivor"):
    """Sanitise a player-typed survivor name before it becomes
    self.name. The name flows into Rich markup (the TUI HUD does
    f"[bold]{name}[/bold]"), plain-text play logs, combat lines and
    profile-filename slugs, so a stray '[', ']' or '\\' otherwise
    corrupts the HUD or desyncs the profile file. Keeps letters,
    digits, spaces and a few name punctuation marks; collapses
    whitespace; caps length."""
    if not raw:
        return fallback
    kept = re.sub(r"[^A-Za-z0-9 '.\-]+", "", str(raw))
    kept = re.sub(r"\s+", " ", kept).strip(" .-'")
    return kept[:24].strip() or fallback


def _name_slug(name):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", (name or "").strip()) or "player"


def campaign_filename(world_id, name):
    """The on-disk filename for a (world, survivor) campaign. The
    default world keeps the bare ``apocrysis_profile_<name>.json`` so
    every pre-multi-world save still resolves; other worlds get
    ``apocrysis_profile_<world>__<name>.json``, so the same survivor
    name can hold a separate campaign in each world (G: campaign
    identity is world + survivor + mode, not survivor alone).
    """
    from src.worlds import DEFAULT_WORLD_ID
    base = _name_slug(name)
    if not world_id or world_id == DEFAULT_WORLD_ID:
        return f"apocrysis_profile_{base}.json"
    return f"apocrysis_profile_{_name_slug(world_id)}__{base}.json"


def profile_filename_for_name(name):
    """
    Derives a per-player profile filename from a display name, e.g.
    "Jess" -> "apocrysis_profile_Jess.json". Non-filename-safe
    characters are collapsed to "_" so an arbitrary player-entered
    name can't escape the current directory or collide with the
    named SESSION save-slot files (apocrysis_save*.json - a
    different concept, see the profile-persistence note below).

    This is the default-world / classic-mode filename; the shell uses
    campaign_filename(world_id, name) directly.
    """
    return campaign_filename(None, name)


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
        filename = runtime_paths.resolve("save", filename)
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
            "visited": [list(pos) for pos in self.visited],
            "backpack_food": self.backpack.food,
            "backpack_water": self.backpack.water,
            "backpack_medicine": self.backpack.medicine,
            "backpack_ammo": self.backpack.ammo,
            "weapons": [],
            "equipped_weapon": None,
            "armor": [],
            "equipped_armor": {},
            "status_effects": self.status_effects,
            "map": self._serialize_map(),
            "town_known": self.town_known,
            "map_revealed": getattr(self, 'map_revealed', False),
            "knowledge": self.knowledge.to_dict() if getattr(self, 'knowledge', None) else None,
            "mystery": self.mystery.to_dict() if getattr(self, 'mystery', None) else None,
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
        self._unsaved = False   # 1d HUD
        self.io.say(f"Game saved to {filename}.")

    def _prompt_delete_save(self):
        try:
            save_files = [f for f in os.listdir(runtime_paths.saves_dir())
                          if f.endswith(".json")]
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
        filename = runtime_paths.resolve("save", filename)
        if os.path.exists(filename):
            os.remove(filename)
            self.io.say(f"Saved game deleted from {filename}.")
        else:
            self.io.say("No saved game found to delete.")

    @classmethod
    def load_game(cls, filename="apocrysis_save.json"):
        filename = runtime_paths.resolve("save", filename)
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

        # audit 1c: the Goal/Task systems were removed. Obsolete
        # "goals" / "tasks" / "last_action" keys in an old save are
        # discarded at this boundary - nothing reads them now.

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
        filename = runtime_paths.resolve("player", filename)
        # Phase B: one file, two logical records.
        #   SURVIVOR  - identity + progression + gear + physical state;
        #               replaced wholesale when a survivor dies.
        #   CAMPAIGN  - what has been figured out about the world;
        #               carries across every death. save_profile() only
        #               SERIALISES - the game lifecycle decides when the
        #               survivor record is replaced (PHASE_B_SPEC.md).
        survivor = {
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
            "has_flashlight": getattr(self, "has_flashlight", False),
        }
        campaign = {
            # Phase F: which world this campaign belongs to. A profile
            # without it is a pre-Phase-F save -> the default world.
            "world_id": getattr(self.world, "id", None),
            "hardcore": getattr(self, "hardcore", False),
            "expeditions_completed": self.expeditions_completed,  # DEPTH, not survivor progress
            # Story-variety guarantee (schema 3a) must survive quit/
            # relaunch, not just live for one session.
            "used_mechanisms": list(getattr(self.__class__, "_used_mechanisms", []) or []),
            "last_family": getattr(self.__class__, "_last_family", None),
            "recent_mechanisms": list(getattr(self.__class__, "_recent_mechanisms", []) or []),
            "recent_signatures": list(getattr(self.__class__, "_recent_signatures", []) or []),
            # A.3: World Investigation status carries across death.
            "world_investigation": dict(getattr(self.__class__, "_world_investigation", {}) or {}),
            # B.2: Survivor Knowledge - learned SurvivorLore ids.
            "survivor_knowledge": list(getattr(self.__class__, "_survivor_knowledge", []) or []),
            # B.1b: how many survivors this campaign has lost.
            "survivors_lost": int(getattr(self.__class__, "_survivors_lost", 0) or 0),
            # 1d HUD: campaign-cumulative distance walked.
            "distance_walked": round(float(getattr(self, "_distance_walked", 0.0)), 2),
            # E.3: the ending the player chose at the finale, if any -
            # so a relaunched completed campaign shows the resolved
            # state and never re-prompts.
            "ending": getattr(self.__class__, "_campaign_ending", None),
        }

        with open(filename, 'w') as f:
            json.dump({"campaign": campaign, "survivor": survivor}, f, indent=2)
        self._unsaved = False   # 1d HUD

    @staticmethod
    def load_profile(filename=DEFAULT_PROFILE_FILENAME):
        filename = runtime_paths.resolve("player", filename)
        if not os.path.exists(filename):
            return None

        with open(filename, 'r') as f:
            return _normalise_profile(json.load(f))

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
        _pat = os.path.join(runtime_paths.player_dir(), "apocrysis_profile_*.json")
        for path in sorted(glob.glob(_pat)):
            name = _profile_name(PersistenceMixin.load_profile(path))
            if name and name not in names:
                names.append(name)

        legacy_name = _profile_name(PersistenceMixin.load_profile(DEFAULT_PROFILE_FILENAME))
        if legacy_name and legacy_name not in names:
            names.append(legacy_name)

        return names

    @staticmethod
    def list_campaign_summaries():
        """Newest-first metadata for every on-disk campaign profile -
        which, post-Q1, means every *Normal* campaign (Hardcore writes
        no file, ever). Each entry:
          name    - the CURRENT survivor's display name (rotates on
                    death -> heir); for the SURVIVOR column
          key     - the campaign's stable identity, from the filename;
                    resume / delete address the campaign by this, NOT
                    by `name` (which changes)
          world_id / world_title, expeditions_completed /
          campaign_length, ending, last_played (mtime), path

        The Phase-G shell's CONTINUE and LOAD read this; the game
        proper never does. Deliberately tolerant - a profile naming a
        removed world still lists (get_world falls back)."""
        from src.worlds import get_world
        _pat = os.path.join(runtime_paths.player_dir(),
                            "apocrysis_profile_*.json")
        out = []
        for path in glob.glob(_pat):
            prof = PersistenceMixin.load_profile(path)
            if prof is None:
                continue
            flat = _profile_flat(prof)
            name = flat.get("name")
            if not name:
                continue
            wid = flat.get("world_id")
            try:
                _w = get_world(wid)
                length = _w.manifest.campaign_length
                title = _w.manifest.title
            except Exception:
                length, title = None, (wid or "?")
            # key = the filename stem after apocrysis_profile_ and any
            # <world>__ prefix. This is what the campaign was created
            # under; the survivor name inside can differ after an heir.
            stem = os.path.basename(path)[len("apocrysis_profile_"):-len(".json")]
            key = stem.split("__", 1)[1] if "__" in stem else stem
            out.append({
                "name": name,
                "key": key,
                "world_id": wid,
                "world_title": title,
                "expeditions_completed": int(
                    flat.get("expeditions_completed", 0) or 0),
                "campaign_length": length,
                "ending": flat.get("ending"),
                "last_played": os.path.getmtime(path),
                "path": path,
            })
        out.sort(key=lambda s: s["last_played"], reverse=True)
        return out

    @classmethod
    def load_campaign(cls, world_id, name):
        """Load a Normal campaign by (world, survivor). For the default
        world / legacy saves this is just load_profile_by_name (which
        also migrates the pre-multi-profile single file); other worlds
        read their own ``<world>__<name>.json``."""
        from src.worlds import DEFAULT_WORLD_ID
        if not world_id or world_id == DEFAULT_WORLD_ID:
            return cls.load_profile_by_name(name)
        return cls.load_profile(campaign_filename(world_id, name))

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
        if legacy is not None and _profile_name(legacy) == name:
            with open(runtime_paths.resolve("player", per_name_file), 'w') as f:
                json.dump(legacy, f, indent=2)   # already normalised to {campaign, survivor}
            return legacy

        return None

    @classmethod
    def persist_new_survivor(cls, campaign_file, heir_name, hardcore, depth):
        """Phase B: this survivor died (non-hardcore). The campaign is
        still held in the class-vars; a fresh survivor takes it up.
        Writes {campaign: <verbatim>, survivor: <fresh>} to
        `campaign_file` and returns the heir game (unstarted).

        1d: the campaign inherits a *survivability floor*
        (_apply_heir_advantage) - the heir is a fresh survivor but not a
        Level-1-with-a-screwdriver one dropped into a depth-N combat
        environment. Their own progression still starts near-scratch and
        stacks on top.
        """
        heir = cls(heir_name, hardcore=hardcore, expeditions_completed=depth)
        _apply_heir_advantage(heir, depth)
        heir.save_profile(campaign_file)
        return heir

    @staticmethod
    def delete_campaign(name, world_id=None):
        """G4: remove a Normal campaign by (world, survivor) - the
        Phase-G LOAD GAME screen's Delete. Distinct from the
        instance-bound delete_profile() below: here there's no live
        game, just a row the player picked off a list. Returns True if
        a file went."""
        path = runtime_paths.resolve(
            "player", campaign_filename(world_id, name))
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def delete_profile(self):
        """
        Removes this player's own profile file - the permadeath path
        for a hardcore character who died, so the next launch can't
        reload a dead hardcore run under this name.
        """
        filename = runtime_paths.resolve(
            "player",
            campaign_filename(getattr(self.world, "id", None), self.name))
        if os.path.exists(filename):
            os.remove(filename)

        legacy = self.load_profile(DEFAULT_PROFILE_FILENAME)
        if legacy is not None and _profile_name(legacy) == self.name:
            os.remove(runtime_paths.resolve("player", DEFAULT_PROFILE_FILENAME))

    def apply_profile(self, profile):
        """
        Overwrites this (freshly constructed) instance's identity/
        progression fields from a profile dict (load_profile()'s
        return value) - same after-construction-overwrite pattern
        __init__ already uses for prize_for_next_game, just applied
        explicitly by the caller instead of automatically.

        Accepts the Phase-B {campaign, survivor} shape or a legacy flat
        dict; flattened internally so the field restore below is
        shape-agnostic.
        """
        profile = _profile_flat(profile)

        # Phase F: a profile belongs to a world. If it names a different
        # world than this instance was built with, re-point self.world
        # and rebuild the investigation off that world's fact DAG before
        # restoring campaign state onto it.
        _wid = profile.get("world_id")
        if _wid is not None and _wid != getattr(self.world, "id", None):
            from src.worlds import get_world
            self.world = get_world(_wid)
            from src.world_investigation import WorldInvestigation
            self.world_investigation = WorldInvestigation(
                self.world.world_facts, self.world.regional_hypotheses)

        _sk = profile.get("survivor_knowledge")
        if _sk is not None:
            self.__class__._survivor_knowledge = list(_sk)
            if getattr(self, "survivor_knowledge", None) is not None:
                self.survivor_knowledge.restore(_sk)
        if profile.get("survivors_lost") is not None:
            self.__class__._survivors_lost = int(profile["survivors_lost"])
        self.__class__._campaign_ending = profile.get("ending")

        self.name = profile.get("name", self.name)
        self.player_class = profile.get("player_class", self.player_class)
        self.hardcore = profile.get("hardcore", getattr(self, "hardcore", False))
        self.expeditions_completed = profile.get("expeditions_completed", self.expeditions_completed)
        self._distance_walked = float(profile.get("distance_walked", 0.0) or 0.0)  # 1d HUD
        self._unsaved = False   # 1d HUD: campaign is persisted through the last expedition
        # Restore the escape-story shuffle-bag so the "no back-to-back
        # family" rule holds across sessions, not just within one.
        _um = profile.get("used_mechanisms")
        if _um is not None:
            self.__class__._used_mechanisms = list(_um)
        if profile.get("last_family") is not None:
            self.__class__._last_family = profile["last_family"]
        if profile.get("recent_mechanisms") is not None:
            self.__class__._recent_mechanisms = list(profile["recent_mechanisms"])
        if profile.get("recent_signatures") is not None:
            self.__class__._recent_signatures = list(profile["recent_signatures"])
        _wi = profile.get("world_investigation")
        if _wi is not None:
            self.__class__._world_investigation = dict(_wi)
            if getattr(self, "world_investigation", None) is not None:
                self.world_investigation.restore({"status": dict(_wi)})
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