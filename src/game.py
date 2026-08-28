# Auto-extracted from the original monolithic apocrysis.py during
# the src/ restructuring - see README.md for the project layout.

import random

from src.constants import (
    BASE_MAP_SIZE, MAP_GROWTH_PER_LEVEL, MAX_MAP_SIZE, DAY_COMPRESSION_SCALE,
)
from src.io_console import ConsoleIO
from src.items import Backpack, ARMOR_SLOTS
from src.objectives import Goal

from src.mixins.actions_mixin import ActionsMixin
from src.mixins.combat_mixin import CombatMixin
from src.mixins.objectives_mixin import ObjectivesMixin
from src.mixins.persistence_mixin import PersistenceMixin
from src.mixins.ui_mixin import UIMixin
from src.mixins.world_mixin import WorldMixin
from src.mixins.knowledge_mixin import KnowledgeMixin
from src.mixins.slice_mixin import SliceMixin
from src.mixins.mystery_mixin import MysteryMixin
from src.knowledge import Knowledge


class Apocrysis(
    PersistenceMixin,
    CombatMixin,
    WorldMixin,
    ObjectivesMixin,
    UIMixin,
    ActionsMixin,
    KnowledgeMixin,
    MysteryMixin,
    SliceMixin,
):

    # v4 Phase C: escape-mechanism shuffle-bag across a campaign (no
    # repeat until the pool is exhausted). Class-level, like
    # prize_for_next_game.
    _used_mechanisms = []

    # v4: the fresh-start ration every non-slice game begins with, so
    # a game doesn't open in a food/water deficit. load_game() and
    # apply_profile() subtract this back off before their own additive
    # restore, so a full-state load is exact.
    STARTING_RATIONS = {"food": 8, "water": 8, "medicine": 2}

    prize_for_next_game = False

    def __init__(self, name, map_size=None, level=1, seed=None, io=None, hardcore=False, expeditions_completed=0, slice_mode=False):
        # io (v3 SPRINT step 6): defaults to ConsoleIO, byte-identical
        # to the original bare print()/input() calls - a TUI
        # (src/tui.py's TextualIO) passes its own instead. Every
        # mixin call site uses self.io.say()/self.io.ask()/
        # self.io.ask_yes_no() instead of bare print()/input().
        self.io = io if io is not None else ConsoleIO()

        # v3 SPRINT: no player_class param - every new game starts as
        # the easiest tier's representative class (initialize_player()
        # in actions_mixin.py). `level` lets a caller continuing a
        # persisted profile (cli.py's main()) carry the player's
        # accumulated level into a FRESH game's map sizing/distance/
        # obstacles (generate_map(), below) - level/xp/stats
        # themselves are then overwritten by the caller after
        # construction, the same established pattern
        # prize_for_next_game already uses.
        #
        # self.rng is a per-instance RNG (seedable for reproducible
        # map-generation tests) - generate_map() and
        # _select_zombie_for_encounter() use it instead of the bare
        # random module.

        self.name = name
        self.hardcore = hardcore
        self.expeditions_completed = expeditions_completed
        self.rng = random.Random(seed)

        # v4 vertical slice: a fixed, hand-authored investigation map
        # (src/slice_dam_road.py + SliceMixin) instead of procedural
        # generation, with survival pressure deliberately loosened so
        # the investigation loop can be evaluated in isolation. This
        # is throwaway experimental scaffolding, not a game mode.
        self.slice_mode = slice_mode

        # v4 Phase B: the player knowledge model (src/knowledge.py).
        # generate_map() / slice_setup() repopulate its catalogue;
        # this is just so it always exists.
        self.knowledge = Knowledge()

        # v4 Phase C: the generated escape mystery (src/escape.py).
        # world_mixin.generate_map() builds it and points
        # self.knowledge at it. None => fall back to reach-the-Town-
        # Center (degenerate maps, or slice mode).
        self.mystery = None

        self.xp = 0
        self.level = level
        self.max_xp = 100

        self.map_size = (
            map_size
            if map_size is not None
            else min(
                MAX_MAP_SIZE,
                BASE_MAP_SIZE + expeditions_completed * MAP_GROWTH_PER_LEVEL,
            )
        )

        self.health = 100
        self.max_health = 100  # Maximum health at the start
        self.backpack = Backpack()
        self.equipped_weapon = None
        # Equipment-slot investigation, multi-piece follow-up: one
        # independently-equippable piece per ARMOR_SLOTS entry, not a
        # single slot - see items.py's Armor.
        self.equipped_armor = {slot: None for slot in ARMOR_SLOTS}
        self.initialize_player()
        self.hunger = self.rng.randint(85, 95)
        self.thirst = self.rng.randint(85, 95)
        self.fatigue = self.rng.randint(0, 10)

        # v4 slice: come in already provisioned. Survival is
        # deliberately not the thing being tested here - the player
        # should never be managing hunger/thirst during the
        # investigation. (See _apply_decay's slice branch.)
        if slice_mode:
            self.backpack.food = 25
            self.backpack.water = 25
            self.backpack.medicine = 5
            self.fatigue = 0
        else:
            # v4: come in with a few days' rations instead of nothing.
            # Starting empty put every game in a food/water deficit from
            # turn one (balance report: net -0.7 food, -0.4 water per
            # game) - a starving player fights worse (_condition_penalty)
            # and dies to zombies, which is what "food and water were
            # always a problem" was.
            for _k, _v in self.STARTING_RATIONS.items():
                setattr(self.backpack, _k, _v)
        self.zombie_positions = set()  # Initialize as an empty set
        self.status_effects = {}  # Track active status effects (e.g., Bleeding, Stun)
        # v4 (V3_ASSUMPTION_AUDIT #1/#8): the hard-coded goal list and
        # the dynamic task system are gone - player intent in v4 is
        # expressed through investigation (journal / remember /
        # inspect), not a checklist. The lists stay (empty) for
        # save-file compatibility and the harmless no-op goal/task
        # methods.
        self.goals = []
        self.tasks = []
        self.won = False  # Win condition tracker

        # True once the player has found a map item revealing the
        # Town Center's location (world_mixin.find_loot()) - until
        # then, town tiles are hidden by fog-of-war exactly like any
        # other terrain (ui_mixin._render_map_lines()).
        self.town_known = False

        # Objective-driven win condition investigation: True once the
        # player has set foot in any settlement's non-Town-Center
        # tile (world_mixin.move_and_search()) - until then, reaching
        # the Town Center itself doesn't win. Reset each fresh
        # expedition/map, same as town_known.
        self.settlement_explored = False

        # Day/Night Cycle Initialization
        self.time_of_day = self.rng.randint(420, 540)  # Start between 07:00-09:00 (minutes from midnight)
        self.visibility_radius = 3
        self.is_night = False
        self.day_phase = "day"
        self.day = 1

        # Found via find_loot() (world_mixin.py, one-time like the
        # town-revealing map) - persists across expeditions once found
        # (save_profile()/apply_profile()), same as a carried weapon.
        # Substantially restores visibility during dawn/dusk/night
        # instead of a static, unavoidable penalty.
        self.has_flashlight = False

        # One-time discoverable item: waders that reduce water movement cost / prevent drowning (to be wired up in world_mixin.py)
        self.has_waders = False

        self._update_time()

        # generate_map() sets self.current_position (spawn) itself -
        # visited starts as just that one tile, computed after
        # generate_map() runs rather than pre-guessed as the map
        # center (v3's random spawn, world_mixin.py, means the real
        # spawn isn't known until generate_map() picks it).
        self.generate_map()
        self.visited = {self.current_position}
        self.tile_event_cooldowns = {}

        # Action tracking for automatic goal completion
        self.last_action = ""

        # v4: expedition turn counter (every command the player issues
        # in run_game_loop). Shown in the stats panel so time cost is
        # visible, not something to reverse-engineer from the sun.
        self.turns = 0

        # Recorded so load_game()/apply_profile() can do a clean SET
        # restore and re-add exactly this prize, instead of the fragile
        # "+= and hope it survives" pattern.
        self._prize_bonus = {}
        if Apocrysis.prize_for_next_game:
            self.io.say("\nYou received a generous prize for your next game!")
            self._prize_bonus = {"food": 10, "water": 10, "medicine": 5, "ammo": 20}
            for _k, _v in self._prize_bonus.items():
                setattr(self.backpack, _k, getattr(self.backpack, _k) + _v)
            Apocrysis.prize_for_next_game = False

    def _update_time(self, minutes=15):
        # v3 SPRINT step 5: minutes is now variable (terrain-dependent
        # move cost - world_mixin.py's move_and_search(), via
        # TERRAIN_MOVE_MINUTES) instead of always 15, and scaled up by
        # DAY_COMPRESSION_SCALE (constants.py) so a normal trek
        # actually crosses meaningful portions of a day/night cycle
        # instead of barely denting it. time_of_day itself stays on
        # the real 1440-minute clock - hour/minute display
        # (ui_mixin.py) and the is_night thresholds below are
        # unchanged.
        scaled_minutes = int(minutes * DAY_COMPRESSION_SCALE)
        prev_hour = self.time_of_day // 60
        self.time_of_day = (self.time_of_day + scaled_minutes) % 1440
        hour = self.time_of_day // 60
        
        # Day increments when transitioning from night (<6) to day (>=6)
        if prev_hour < 6 and hour >= 6:
            self.day += 1

        # Day/night phase granularity + flashlight investigation:
        # dawn/day/dusk/night instead of a single binary split, with
        # visibility_radius stepping down gradually rather than
        # jumping straight from 3 to 1. is_night stays derived exactly
        # as before (True only 20:00-06:00) so hunger/thirst decay
        # (_apply_decay()) and encounter_chance (world_mixin.py's
        # move_and_search()) are unaffected by this change.
        if hour >= 20 or hour < 6:
            self.day_phase = "night"
            base_visibility = 1
        elif hour < 8:
            self.day_phase = "dawn"
            base_visibility = 2
        elif hour < 18:
            self.day_phase = "day"
            base_visibility = 3
        else:
            self.day_phase = "dusk"
            base_visibility = 2

        self.is_night = self.day_phase == "night"

        # A found flashlight substantially restores visibility at any
        # non-day phase (dawn/dusk/night) rather than being purely a
        # static penalty - capped at 3 so it can't exceed full daytime
        # visibility.
        flashlight_bonus = 1 if (self.has_flashlight and self.day_phase != "day") else 0
        self.visibility_radius = min(3, base_visibility + flashlight_bonus)

    def _apply_decay(self):
        # v4 slice: survival pressure is deliberately loosened so a
        # player can spend 30+ turns investigating without dying -
        # explicitly temporary, not final tuning (see
        # docs/ESCAPE_WORLD_DESIGN_ASSESSMENT.md, "Vertical slice
        # prototype").
        if getattr(self, 'slice_mode', False):
            self.hunger = max(0, self.hunger - 1)
            self.thirst = max(0, self.thirst - 1)
            return

        # Hunger and thirst decay faster at night
        hunger_decay = 2 + (1 if self.is_night else 0)
        thirst_decay = 2 + (1 if self.is_night else 0)

        self.hunger = max(0, self.hunger - hunger_decay)
        self.thirst = max(0, self.thirst - thirst_decay)

