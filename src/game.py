# Auto-extracted from the original monolithic apocrysis.py during
# the src/ restructuring - see README.md for the project layout.

import random

from src.constants import (
    BASE_MAP_SIZE, MAP_GROWTH_PER_LEVEL, MAX_MAP_SIZE, DAY_COMPRESSION_SCALE,
)
from src.io_console import ConsoleIO
from src.items import Backpack
from src.objectives import Goal

from src.mixins.actions_mixin import ActionsMixin
from src.mixins.combat_mixin import CombatMixin
from src.mixins.objectives_mixin import ObjectivesMixin
from src.mixins.persistence_mixin import PersistenceMixin
from src.mixins.ui_mixin import UIMixin
from src.mixins.world_mixin import WorldMixin


class Apocrysis(
    PersistenceMixin,
    CombatMixin,
    WorldMixin,
    ObjectivesMixin,
    UIMixin,
    ActionsMixin,
):

    prize_for_next_game = False

    def __init__(self, name, map_size=None, level=1, seed=None, io=None):
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
        self.rng = random.Random(seed)

        self.xp = 0
        self.level = level
        self.max_xp = 100

        self.map_size = (
            map_size
            if map_size is not None
            else min(
                MAX_MAP_SIZE,
                BASE_MAP_SIZE + (level - 1) * MAP_GROWTH_PER_LEVEL,
            )
        )

        self.health = 100
        self.max_health = 100  # Maximum health at the start
        self.backpack = Backpack()
        self.equipped_weapon = None
        self.initialize_player()
        self.zombie_positions = set()  # Initialize as an empty set
        self.status_effects = {}  # Track active status effects (e.g., Bleeding, Stun)
        self.goals = [
            Goal(title="Find Food", description="Locate some food to sustain yourself.", goal_type="eat"),
            Goal(title="Stay Hydrated", description="Find a source of clean water.", goal_type="drink"),
            Goal(title="Gather Supplies", description="Collect medicine for emergencies.", goal_type="medicine"),
            Goal(title="Clear the Area", description="Defeat any nearby threats.", goal_type="kill"),
            Goal(title="Explore", description="Venture into uncharted territory.", goal_type=""),
            Goal(title="Reach the Town Center", description="Find your way to the Town Center to win.", goal_type="reach_town")
        ]  # Track player goals/objectives
        self.tasks = []  # Dynamic task system for side objectives and progression milestones
        self.won = False  # Win condition tracker

        # True once the player has found a map item revealing the
        # Town Center's location (world_mixin.find_loot()) - until
        # then, town tiles are hidden by fog-of-war exactly like any
        # other terrain (ui_mixin._render_map_lines()).
        self.town_known = False

        # Day/Night Cycle Initialization
        self.time_of_day = 480  # Start at 08:00 (minutes from midnight)
        self.visibility_radius = 3
        self.is_night = False
        self.day = 1
        self._update_time()

        # generate_map() sets self.current_position (spawn) itself -
        # visited starts as just that one tile, computed after
        # generate_map() runs rather than pre-guessed as the map
        # center (v3's random spawn, world_mixin.py, means the real
        # spawn isn't known until generate_map() picks it).
        self.generate_map()
        self.visited = {self.current_position}

        # Action tracking for automatic goal completion
        self.last_action = ""

        if Apocrysis.prize_for_next_game:
            self.io.say("\nYou received a generous prize for your next game!")
            self.backpack.food += 10
            self.backpack.water += 10
            self.backpack.medicine += 5
            self.backpack.ammo += 20
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
            
        # Night is from 20:00 to 06:00
        if hour >= 20 or hour < 6:
            self.is_night = True
            self.visibility_radius = 1
        else:
            self.is_night = False
            self.visibility_radius = 3

    def _apply_decay(self):
        # Hunger and thirst decay faster at night
        hunger_decay = 2 + (1 if self.is_night else 0)
        thirst_decay = 2 + (1 if self.is_night else 0)
        
        self.hunger = max(0, self.hunger - hunger_decay)
        self.thirst = max(0, self.thirst - thirst_decay)

