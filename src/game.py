# Auto-extracted from the original monolithic apocrysis.py during
# the src/ restructuring - see README.md for the project layout.

import random

from src.constants import (
    BASE_MAP_SIZE, MAP_GROWTH_PER_LEVEL, MAX_MAP_SIZE, MAP_ASPECT, DAY_COMPRESSION_SCALE,
    STATUS_EFFECT_DAMAGE,
)
from src.worlds import get_world
from src.io_console import ConsoleIO
from src.items import Backpack, ARMOR_SLOTS

from src.mixins.actions_mixin import ActionsMixin
from src.mixins.combat_mixin import CombatMixin
from src.mixins.persistence_mixin import PersistenceMixin
from src.mixins.ui_mixin import UIMixin
from src.mixins.world_mixin import WorldMixin
from src.mixins.knowledge_mixin import KnowledgeMixin
from src.mixins.mystery_mixin import MysteryMixin
from src.mixins.intervention_mixin import InterventionMixin
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
    UIMixin,
    ActionsMixin,
    KnowledgeMixin,
    MysteryMixin,
    InterventionMixin,
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

    @classmethod
    def reset_campaign_state(cls, restore_from=None):
        """Phase F / Phase G (§7): wipe every campaign-scoped class var,
        then - if `restore_from` (a flattened profile dict) is given -
        immediately re-apply that campaign's values. This is the
        reset-then-restore the Player Shell needs: it lets you play
        campaign A, return to the menu, and load campaign B in the same
        process without ANY of A's mechanisms / investigation /
        survivors-lost / ending leaking into B (and after Phase F, B may
        be a different world entirely). Never a merge.

        Call it BEFORE constructing the Apocrysis for a campaign -
        __init__ reads _world_investigation and the mechanism
        shuffle-bag while building the first map, so they must already
        hold the target campaign's values, not the previous one's.
        `prize_for_next_game` always resets to False on a load-switch:
        a saved campaign's win bonus is already baked into its stored
        backpack."""
        f = restore_from or {}
        cls._used_mechanisms = list(f.get("used_mechanisms", []) or [])
        cls._recent_mechanisms = list(f.get("recent_mechanisms", []) or [])
        cls._recent_signatures = list(f.get("recent_signatures", []) or [])
        cls._world_investigation = dict(f.get("world_investigation", {}) or {})
        cls._survivor_knowledge = list(f.get("survivor_knowledge", []) or [])
        cls._survivors_lost = int(f.get("survivors_lost", 0) or 0)
        cls._campaign_ending = f.get("ending")
        cls._last_family = f.get("last_family")
        cls.prize_for_next_game = False

    def __init__(self, name, map_size=None, level=1, seed=None, io=None, hardcore=False, expeditions_completed=0, world=None, mapgen=None):
        # `world` may be a World, a world id string, or None (default).
        # io (v3 SPRINT step 6): defaults to ConsoleIO, byte-identical
        # to the original bare print()/input() calls - a TUI
        # (src/tui.py's TextualIO) passes its own instead. Every
        # mixin call site uses self.io.say()/self.io.ask()/
        # self.io.ask_yes_no() instead of bare print()/input().
        self.io = io if io is not None else ConsoleIO()
        if isinstance(world, str) or world is None:
            self.world = get_world(world)
        else:
            self.world = world

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
        self._seed = seed
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
        # docs/MAP_REALISM_SPEC.md 1b: the "landscape" generator makes the
        # grid wider than tall (terminal cells are ~2:1, and a valley is
        # wider than deep). v1 stays square, so map_w == map_h ==
        # map_size and every existing call site is byte-identical.
        self.map_h = self.map_size
        self.map_w = (round(self.map_size * MAP_ASPECT)
                      if self._mapgen == "landscape" else self.map_size)

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
        # v4 (V3_ASSUMPTION_AUDIT #1/#8) / audit 1c: the hard-coded goal
        # list and the dynamic task system are gone - player intent is
        # expressed through the investigation (journal / remember /
        # inspect / wi) and the expedition objective, not a checklist.
        # The Goal/Task classes and ObjectivesMixin were removed in 1c;
        # obsolete goals/tasks keys in an old save are simply ignored.
        self.won = False  # Win condition tracker

        # 1d HUD pass: unsaved-changes flag (any action flips it true;
        # save_game / save_profile clear it) and cumulative distance
        # walked - campaign-total (round-trips through the profile) plus
        # a per-expedition tally the stats screen shows.
        self._unsaved = False
        self._distance_walked = 0.0        # campaign miles, persisted
        self._expedition_distance = 0.0    # this expedition only

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
        # 1d HUD: any action that spends time is unsaved progress.
        if minutes:
            self._unsaved = True
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

        self._tick_status_effects()
        self._supply_warnings()
        self._hp_warnings()
        self._fatigue_warnings()
        self._ammo_warnings()
        self._intervention_gates()

    def _tick_status_effects(self):
        """One decrement + damage pass over active status effects, at
        most once per game-turn (`self.turns`).

        1d playtest bug: Bleeding / Poison only ticked inside combat
        rounds, so an effect left over from a fight sat frozen forever
        while you explored - visible in the HUD CONDITIONS block, doing
        nothing, curable by nothing. Now it counts down and deals its
        damage every turn (move / rest / search / …). Combat keeps its
        own per-round pass; the turn-stamp stops the two double-counting
        the turn a move walks into a fight. `Stun` counts down here too
        (so it can't freeze between fights) but has no exploration
        effect - there is no turn to skip while walking. Damage and
        durations are unchanged - this only fixes *when* the mechanic
        runs."""
        t = getattr(self, "turns", 0)
        if getattr(self, "_status_tick_turn", None) == t:
            return
        self._status_tick_turn = t
        for effect in list(self.status_effects.keys()):
            dmg = STATUS_EFFECT_DAMAGE.get(effect)
            if dmg:
                self.health = max(0, self.health - dmg)
                self.io.say(f"You are affected by {effect}! Lost {dmg} health.")
            self.status_effects[effect] -= 1
            if self.status_effects[effect] <= 0:
                del self.status_effects[effect]
                self.io.say(f"The {effect.lower()} has passed.")

    def _fatigue_warnings(self):
        """Fatigue as a standing condition (docs/FATIGUE_INVESTIGATION_
        RESULTS.md Q4). Was never announced - a naive player had no
        prompt to `rest`. tier 1 (exhausted, >80) an L1 line, tier 2
        (>92, every move is a real cost) an L2 banner; one shot each,
        re-armed at <55, completion line on recovery."""
        f = self.fatigue
        prev = getattr(self, "_fatigue_warned", 0)
        if f < 55:
            if prev:
                self.announce_event("you've caught your breath",
                                    f"Fatigue down to {f}.",
                                    kind="success", level=1)
            self._fatigue_warned = 0
            return
        tier = 2 if f > 92 else 1 if f > 80 else 0
        if tier <= prev:
            return
        self._fatigue_warned = tier
        if tier == 1:
            self.announce_event(
                "you're exhausted",
                "Moving is getting costly. `rest` here, or duck into a "
                "building - a building rests you faster.",
                kind="warning", level=1)
        else:
            self.announce_event(
                "YOU'RE SPENT",
                "Every move is a real cost now. `rest` before the next "
                "fight or river.",
                kind="warning", level=2)

    def _ammo_warnings(self):
        """1d HUD pass: the human playtest showed players walking into
        fights with an empty equipped gun and only noticing when it
        clicked dry mid-combat. One nudge when the equipped ranged
        weapon hits empty and there are rounds in the pack; re-armed on
        reload."""
        from src.items import RangedWeapon
        w = self.equipped_weapon
        empty = (isinstance(w, RangedWeapon) and getattr(w, "ammo", 1) == 0
                 and self.backpack.ammo > 0)
        if not empty:
            self._ammo_warned = False
            return
        if getattr(self, "_ammo_warned", False):
            return
        self._ammo_warned = True
        self.announce_event(
            "your gun is empty",
            f"`reload` - you have {self.backpack.ammo} rounds in your pack. "
            "Do it before the next fight, not during it.",
            kind="warning", level=1)

    def _hp_warnings(self):
        """Wounds as a standing condition (docs/DESIGN_ATTENTION_LANGUAGE.md).
        HP only announced through combat before this - a survivor
        bleeding out between fights got nothing. One shot per tier per
        wound episode; re-armed at 55%; a completion line on recovery."""
        frac = self.health / max(1, self.max_health)
        prev = getattr(self, "_hp_warned", 0)
        if frac > 0.65:          # re-arm well clear of the tier-1 line (0.40)
            if prev:
                self.announce_event("wounds under control",
                                    f"Back to {self.health}/{self.max_health}.",
                                    kind="success", level=1)
            self._hp_warned = 0
            return
        tier = 2 if frac <= 0.20 else 1
        if tier <= prev:
            return
        self._hp_warned = tier
        has_med = self.backpack.medicine > 0
        if tier == 1:
            self.announce_event(
                "you're hurt",
                "Use `med` before a fight finds you." if has_med
                else "No medicine - a building is a safe place to recover.",
                kind="warning", level=1)
        else:
            self.announce_event(
                "YOU'RE BADLY HURT",
                f"{self.health}/{self.max_health}. "
                + ("`med` now." if has_med else "No medicine. Avoid every fight."),
                kind="warning", level=2)

    def _supply_warnings(self):
        """Escalating hunger/thirst warnings. A kid ran to 0/0 with food
        still in the pack - the single -30 nudge fired once and never
        again (playtest). Three tiers, one shot each per depletion
        episode, re-armed once the level recovers past 45, with a
        completion line on recovery (attention lifecycle). NO movement
        cap - starvation stays HP attrition; this just makes the state
        unmistakable so the player owns the "12 HP, exit's three tiles
        away, do I risk it?" call."""
        for kind, level, supply in (
            ("hunger", self.hunger, self.backpack.food),
            ("thirst", self.thirst, self.backpack.water),
        ):
            attr = f"_{kind}_warned"
            adj = "hungry" if kind == "hunger" else "thirsty"
            if level > 45:
                if getattr(self, attr, 0) >= 2:
                    self.announce_event(f"{adj} no longer",
                                        f"{kind.capitalize()} back up.",
                                        kind="success", level=1)
                setattr(self, attr, 0)
                continue
            tier = 3 if level <= 0 else 2 if level <= 10 else 1 if level <= 30 else 0
            if tier <= getattr(self, attr, 0):
                continue
            setattr(self, attr, tier)
            verb = "eat" if kind == "hunger" else "drink"
            noun = "food" if kind == "hunger" else "water"
            if tier == 1 and supply > 0:
                self.announce_event(f"getting {adj}",
                                    f"Type `{verb}` - you've got {noun} in your pack.",
                                    kind="warning", level=1)
            elif tier == 2:
                if supply > 0:
                    self.announce_event(f"YOU'RE {adj.upper()} - {verb} NOW",
                                        f"You have {noun} in your pack. It costs health once it hits zero.",
                                        kind="warning", level=2)
                else:
                    self.announce_event(f"getting {adj}, and no {noun}",
                                        f"Find some - at zero, {kind} starts costing you health.",
                                        kind="warning", level=2)
            elif tier == 3:
                # attrition is ACTIVE now - DANGER.
                if supply > 0:
                    self.announce_event(f"YOU ARE {adj.upper()} - {verb} SOMETHING",
                                        f"There's {noun} in your pack and {kind} is costing you health right now.",
                                        kind="danger", level=3)
                else:
                    self.announce_event(f"YOU ARE {adj.upper()}",
                                        f"No {noun} left, and {kind} is costing you health. Find some or get out.",
                                        kind="danger", level=3)

    # ---- P1 Commitment & Intervention Pass ---------------------------
    # docs/PHASE_P1_COMMITMENT_INTERVENTION_SPEC.md §3.4 / §3.5.
    # These run from _apply_decay (move / rest time) - always OUT of
    # combat - so no _in_combat guard is needed. Every predicate and
    # re-arm below lives HERE, in the caller; commit_gate only presents
    # the interruption and returns the choice. Interactive-only via
    # commit_gate's "skip" contract - the bot never sees them.

    def _intervention_gates(self):
        frac = self.health / max(1, self.max_health)
        if frac > 0.55:                       # re-arm, same band as _hp_warned
            self.gate_rearm("critical_hp")
        self._crit_hp_gate()
        self._weapon_ready_gate()

    def _crit_hp_gate(self):
        """P1-d: critically hurt with medicine on hand. Also fired at the
        top of an encounter (combat_mixin.encounter_zombie)."""
        if self.health / max(1, self.max_health) > 0.20:
            return
        if self.backpack.medicine <= 0:
            return
        if self.commit_gate(
                "critical_hp", "CRITICALLY HURT",
                f"{self.health}/{self.max_health} health - "
                f"{self.backpack.medicine} medicine in your pack.",
                default="proceed",
                confirm_label="use medicine now") == "proceed":
            self.use_medicine()

    def _weapon_ready_gate(self):
        """P1-c: the equipped weapon can't land a hit and a usable one is
        in the pack. Pre-fight only. The mid-fight auto-swap
        (_weapon_condition_check) stays the sole owner during combat; the
        reload nudge stays with _ammo_warnings."""
        from src.items import RangedWeapon

        def _usable(x):
            if x is None or getattr(x, "durability", 1) <= 0:
                return False
            if isinstance(x, RangedWeapon) and x.ammo <= 0:
                return False
            return True

        w = self.equipped_weapon
        if _usable(w):
            self.gate_rearm("weapon_empty")
            return
        if isinstance(w, RangedWeapon) and w.ammo <= 0 and self.backpack.ammo > 0:
            return                            # _ammo_warnings owns "reload"
        spare = max((b for b in self.backpack.weapons if _usable(b)),
                    key=lambda b: b.damage, default=None)
        if spare is None:
            return
        if self.commit_gate(
                "weapon_empty", "YOUR WEAPON IS EMPTY",
                f"{w.name if w else 'Nothing'} can't strike - "
                f"{spare.name} ({spare.damage} dmg) is in your pack.",
                default="proceed",
                confirm_label=f"equip {spare.name}") == "proceed":
            self._auto_equip_best()

