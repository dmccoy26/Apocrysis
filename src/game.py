# Auto-extracted from the original monolithic apocrysis.py during
# the src/ restructuring - see README.md for the project layout.

import random

from src.constants import (
    BASE_MAP_SIZE, MAP_GROWTH_PER_LEVEL, MAX_MAP_SIZE, DAY_COMPRESSION_SCALE,
)
from src.worlds.silence import SILENCE
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
from src.mixins.mystery_mixin import MysteryMixin
from src.knowledge import Knowledge
from src.world_investigation import WorldInvestigation
from src.survivor_knowledge import SurvivorKnowledge


# C.3.2a-7 (docs/PHASE_C3_2_7_SUPPORTED_DEPTH.md): expeditions 0..N are
# fresh-survivor-viable on starter supplies; past N the required circuit
# outgrows a fixed budget (SCALE_REPORT.md - lever matrix + Gate 8 +
# C.3.2a-6 all falsified a generator fix). The campaign contract is that
# deep expeditions are inheritance-scaled: a survivor ARRIVING at depth
# d - including a persist_new_survivor heir who otherwise starts flat -
# gets a supply floor matched to depth d's circuit. N = 6.
SUPPORTED_DEPTH = 6
_SUPPLY_PER_DEPTH = 1.8      # rations of food AND water per depth past 2
_SUPPLY_BONUS_CAP = 20


def depth_supply_bonus(depth):
    """Extra units of food and (separately) water a survivor arriving at
    `depth` starts with, over the flat STARTING_RATIONS. 0 through the
    early band, then ~linear in depth, capped. Calibrated in
    PHASE_C3_2_7 section 4 against SCALE_REPORT's p90 circuit growth."""
    over = max(0, depth - 1)
    return int(min(_SUPPLY_BONUS_CAP, round(_SUPPLY_PER_DEPTH * over)))


class Apocrysis(
    PersistenceMixin,
    CombatMixin,
    WorldMixin,
    ObjectivesMixin,
    UIMixin,
    ActionsMixin,
    KnowledgeMixin,
    MysteryMixin,
):

    # v4 Phase C: escape-mechanism shuffle-bag across a campaign (no
    # repeat until the pool is exhausted). Class-level, like
    # prize_for_next_game.
    _used_mechanisms = []
    # v4 variety rules B + C: a short ring of the last couple of
    # mechanisms and of their story signatures, so consecutive
    # expeditions don't just alternate two scenarios or repeat a shape.
    _recent_mechanisms = []
    _recent_signatures = []
    # A.3: World Investigation status that carries across expeditions /
    # deaths, same class-var + profile round-trip pattern as the lists
    # above. { world_fact_id: "known" | "suspected" }.
    _world_investigation = {}
    # B.2: learned SurvivorLore ids - campaign-level, survives death.
    _survivor_knowledge = []
    # B.1b: how many survivors this campaign has lost (drives the next
    # survivor's name). Campaign-level.
    _survivors_lost = 0
    # E.3: the ending chosen at the finale ("broadcast" | "protect" |
    # None). Campaign-level; persisted so a completed campaign never
    # re-prompts.
    _campaign_ending = None
    # C.3: which map generator to use. "v1" is the frozen rectangular
    # pipeline; "v2" is the irregular-valley experiment. Default stays
    # "v1" until C.3 is accepted. A constructor arg overrides this;
    # tools/geo_compare.py flips the class default for its bot runs.
    _default_mapgen = "v1"

    # C.3.2a-5 lever A/B (docs/PHASE_C3_2_5_LEVER_MATRIX.md). MEASUREMENT
    # ONLY - all off by default, generation is byte-identical to
    # baseline with these unset. tools/lever_matrix.py flips them per
    # variant. Never combined; never a shipped default.
    _lever_settlements_by_area = False   # lever 1
    _lever_bound_gap = None              # lever 2: int target gap distance
    _lever_cap_town_dist = None          # lever 3: int cap on town min-dist
    _lever_spread_sites = False          # lever 4
    _lever_scaled_beats = None           # C.3.2a-6: (form_id, c) or None

    # v4: the fresh-start ration every game begins with, so a game
    # doesn't open in a food/water deficit. apply_profile() / load_game()
    # SET backpack.* from the profile afterward, so a returning survivor
    # is governed by their saved state + the win prize, not this.
    STARTING_RATIONS = {"food": 8, "water": 8, "medicine": 2}

    prize_for_next_game = False

    def __init__(self, name, map_size=None, level=1, seed=None, io=None, hardcore=False, expeditions_completed=0, world=None, mapgen=None):
        # io (v3 SPRINT step 6): defaults to ConsoleIO, byte-identical
        # to the original bare print()/input() calls - a TUI
        # (src/tui.py's TextualIO) passes its own instead. Every
        # mixin call site uses self.io.say()/self.io.ask()/
        # self.io.ask_yes_no() instead of bare print()/input().
        self.io = io if io is not None else ConsoleIO()
        self.world = world if world is not None else SILENCE

        # A.3: the campaign's World Investigation, seeded from the
        # class-var (which apply_profile restores from the profile).
        self.world_investigation = WorldInvestigation(
            self.world.world_facts, self.world.regional_hypotheses)
        self.world_investigation.restore({"status": dict(type(self)._world_investigation)})
        # B.2: the campaign's Survivor Knowledge, seeded from the
        # class-var (apply_profile restores that from the profile).
        self.survivor_knowledge = SurvivorKnowledge(type(self)._survivor_knowledge)

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
        self._mapgen = mapgen or type(self)._default_mapgen
        self.rng = random.Random(seed)

        # v4 Phase B: the player knowledge model (src/knowledge.py).
        # generate_map() repopulates its catalogue; this is just so it
        # always exists.
        self.knowledge = Knowledge()

        # v4 Phase C: the generated escape mystery (src/escape.py).
        # world_mixin.generate_map() builds it and points
        # self.knowledge at it. None => fall back to reach-the-Town-
        # Center (degenerate maps only).
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

        # v4: come in with a few days' rations instead of nothing.
        # Starting empty put every game in a food/water deficit from
        # turn one (balance report: net -0.7 food, -0.4 water per
        # game) - a starving player fights worse (_condition_penalty)
        # and dies to zombies, which is what "food and water were
        # always a problem" was.
        _supply_bonus = depth_supply_bonus(self.expeditions_completed)
        for _k, _v in self.STARTING_RATIONS.items():
            # C.3.2a-7: food/water get the inheritance-scaled floor so a
            # fresh heir taking up a deep campaign isn't dropped onto a
            # circuit their starter rations can't cover. medicine flat.
            _bonus = _supply_bonus if _k in ("food", "water") else 0
            setattr(self.backpack, _k, _v + _bonus)
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

        # v4 (todo 8f9ec034): finding a map item reveals the whole
        # GEOGRAPHY - terrain and settlement layout across the entire
        # map (world_mixin.find_loot(), ui_mixin._render_map_lines()).
        # Not the dynamic layer: zombies stay hidden until you've
        # actually been somewhere. town_known kept as a subset for
        # older saves / the town-tile branch.
        self.map_revealed = False
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

        # v4: human play logging (src/playlog.py) - None until the
        # `log` command or --log turns it on.
        self.playlog = None

        # Recorded so load_game()/apply_profile() can do a clean SET
        # restore and re-add exactly this prize, instead of the fragile
        # "+= and hope it survives" pattern.
        self._prize_bonus = {}
        if Apocrysis.prize_for_next_game:
            self.io.say("\nYou received a generous prize for your next game!")
            # C.3.2a-7: the win prize's food/water scale with campaign
            # depth too, so a returning winner's supply floor tracks the
            # circuit the same way a fresh heir's does.
            _pb = depth_supply_bonus(self.expeditions_completed)
            self._prize_bonus = {"food": 10 + _pb, "water": 10 + _pb,
                                 "medicine": 5, "ammo": 20}
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
        # Hunger and thirst decay faster at night
        hunger_decay = 2 + (1 if self.is_night else 0)
        thirst_decay = 2 + (1 if self.is_night else 0)

        self.hunger = max(0, self.hunger - hunger_decay)
        self.thirst = max(0, self.thirst - thirst_decay)

        # At zero, hunger/thirst stop being just a combat debuff
        # (_condition_penalty) and start costing health directly -
        # playtest: "being thirsty and hungry should have more of an
        # effect on your health." -2 each, so an empty pack in hostile
        # terrain is a real clock, not a footnote.
        starving = (2 if self.hunger <= 0 else 0) + (2 if self.thirst <= 0 else 0)
        if starving:
            self.health = max(0, self.health - starving)
            # Say so - not every turn (noise), but on the turn it
            # starts and periodically after, so the HP loss isn't a
            # mystery and the balance harness can attribute the death.
            self._starve_turns = getattr(self, '_starve_turns', 0) + 1
            if self._starve_turns == 1 or self._starve_turns % 4 == 0:
                what = ("hunger and thirst" if starving >= 4
                        else "hunger" if self.hunger <= 0 else "thirst")
                self.io.say(f"The {what} is wearing you down. (-{starving} health)")
        else:
            self._starve_turns = 0

        self._supply_warnings()

    def _supply_warnings(self):
        """Escalating hunger/thirst warnings. A kid ran to 0/0 with food
        still in the pack - the single -30 nudge fired once and never
        again (playtest). Three tiers, one shot each per depletion
        episode, re-armed once the level recovers past 45. NO movement
        cap - starvation stays HP attrition; this just makes the state
        unmistakable so the player owns the "12 HP, exit's three tiles
        away, do I risk it?" call."""
        for kind, level, supply in (
            ("hunger", self.hunger, self.backpack.food),
            ("thirst", self.thirst, self.backpack.water),
        ):
            attr = f"_{kind}_warned"
            if level > 45:
                setattr(self, attr, 0)
                continue
            tier = 3 if level <= 0 else 2 if level <= 10 else 1 if level <= 30 else 0
            if tier <= getattr(self, attr, 0):
                continue
            setattr(self, attr, tier)
            verb = "eat" if kind == "hunger" else "drink"
            noun = "food" if kind == "hunger" else "water"
            adj = "hungry" if kind == "hunger" else "thirsty"
            if tier == 1 and supply > 0:
                self.announce_event(f"getting {adj}",
                                    f"Type `{verb}` - you've got {noun} in your pack.", kind="warn")
            elif tier == 2:
                if supply > 0:
                    self.announce_event(f"YOU'RE {adj.upper()} - {verb} NOW",
                                        f"You have {noun} in your pack. It costs health once it hits zero.",
                                        kind="warn")
                else:
                    self.announce_event(f"getting {adj}, and no {noun}",
                                        f"Find some - at zero, {kind} starts costing you health.",
                                        kind="warn")
            elif tier == 3:
                if supply > 0:
                    self.announce_event(f"YOU ARE {adj.upper()} - {verb} SOMETHING",
                                        f"There's {noun} in your pack and {kind} is costing you health right now.",
                                        kind="warn")
                else:
                    self.announce_event(f"YOU ARE {adj.upper()}",
                                        f"No {noun} left, and {kind} is costing you health. Find some or get out.",
                                        kind="warn")

