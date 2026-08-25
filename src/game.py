# Auto-extracted from the original monolithic apocrysis.py during
# the src/ restructuring - see README.md for the project layout.

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

    def __init__(self, name, player_class, map_size):
        self.map_size = map_size
        self.name = name
        self.player_class = player_class
        self.health = 100
        self.max_health = 100  # Maximum health at the start
        self.backpack = Backpack()
        self.equipped_weapon = None
        self.current_position = (self.map_size // 2, self.map_size // 2)
        self.visited = set()  # Initialize visited tiles tracker
        self.visited.add(self.current_position)  # Mark the initial position as visited
        self.initialize_player(player_class)
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
        
        # Day/Night Cycle Initialization
        self.time_of_day = 480  # Start at 08:00 (minutes from midnight)
        self.visibility_radius = 3
        self.is_night = False
        self.day = 1
        self._update_time()
        
        self.generate_map()
        
        # Progression System Initialization
        self.xp = 0
        self.level = 1
        self.max_xp = 100
        
        # Action tracking for automatic goal completion
        self.last_action = ""

        if Apocrysis.prize_for_next_game:
            print("\nYou received a generous prize for your next game!")
            self.backpack.food += 10
            self.backpack.water += 10
            self.backpack.medicine += 5
            self.backpack.ammo += 20
            Apocrysis.prize_for_next_game = False

    def _update_time(self):
        prev_hour = self.time_of_day // 60
        # Advance time by 15 minutes per action/move
        self.time_of_day = (self.time_of_day + 15) % 1440
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

