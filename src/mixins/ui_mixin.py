# Auto-extracted from the original monolithic apocrysis.py during
# the src/ restructuring - see README.md for the project layout.

import random
import shutil

from src.constants import BOLD, CYAN, GREEN, RED, RESET, YELLOW, TERRAIN_LEGEND, TERRAIN_SYMBOLS
from src.items import RangedWeapon, format_weapon_list, format_armor_list
from src.text_utils import _visible_len, _display_ljust
from src.zombies import Zombie, FreshZombie, RegularZombie, HeavyZombie


class UIMixin:

    def print_stat_changes(self, old_stats):
        current_stats = {stat: getattr(self, stat) for stat in old_stats}

        changes = []
        for stat in old_stats:
            if current_stats[stat] != old_stats[stat]:
                diff = current_stats[stat] - old_stats[stat]
                sign = "+" if diff > 0 else ""
                color = (RED if diff > 0 else GREEN) if stat == "fatigue" else (GREEN if diff > 0 else RED)
                changes.append(f"{BOLD}{color}{stat.capitalize()}: {sign}{diff}{RESET}")
        
        if changes:
            self.io.say("\n" + " | ".join(changes))

    def _action_bar(self):
        """A short list of the verbs that matter right now, for the
        TUI's action bar - not the full reference (that's `help` /
        `_available_commands`). Movement is always live; the rest is
        situational."""
        bar = ["move  n/s/e/w", "look", "map", "journal", "?=help"]
        m = getattr(self, 'mystery', None)
        here = self._mystery_role_at(*self.current_position) if hasattr(self, '_mystery_role_at') and m else None
        if here in ('closed', 'route', 'require', 'obstacle'):
            bar.insert(1, "search")
        if m is not None:
            if m.obstacle_open and m.knowledge.hypothesis_state() == 'confirmed' and not m.escaped:
                bar.insert(1, "ESCAPE")
            elif getattr(m, 'saw_obstacle', False) and not m.obstacle_open and self._mystery_has_item():
                bar.insert(1, "open (at the gate)")
        if self.backpack.water == 0 and hasattr(self, '_at_natural_water') and self._at_natural_water():
            bar.append("drink (from the water)")
        if self.backpack.weapons:
            bar.append("eq <weapon>")
        if isinstance(self.equipped_weapon, RangedWeapon) and self.equipped_weapon.ammo < self.equipped_weapon.max_ammo:
            bar.append("reload")
        recipes = [r for r in self.describe_recipes() if not r["locked"]] if hasattr(self, 'describe_recipes') else []
        if recipes:
            bar.append("cr <recipe>")
        return bar

    def _available_commands(self):
        # v3 SPRINT step 6: pulled out of run_game_loop() so a native
        # UI (tui.py) can show the same context-sensitive command list
        # (eat/drink/craft/fight only when actually applicable)
        # without needing run_game_loop()'s own classic-mode ASCII
        # block at all - see the renders_natively split below.
        cmd_list = ["n (north)", "s (south)", "e (east)", "w (west)", "m (map)", "i (inventory)", "st (stats)", "h (help)", "x (exit game)", "q (quit)", "sv (save)", "ds (delete save)"]

        # v4 investigation commands - always available.
        cmd_list.append("look (l)")
        cmd_list.append("search (sr)")
        cmd_list.append("journal (j)")
        cmd_list.append("remember (rem)")
        cmd_list.append("inspect [thing]")
        if getattr(self, 'mystery', None) is not None or getattr(self, 'slice_mode', False):
            cmd_list.append("clear / open")
            cmd_list.append("escape")

        if self.backpack.weapons:
            cmd_list.append("eq [weapon name] (equip)")
        if self.backpack.weapons or self.equipped_weapon:
            cmd_list.append("drop [weapon name] (drop)")
        if isinstance(self.equipped_weapon, RangedWeapon):
            cmd_list.append(f"reload ({self.equipped_weapon.name})")
        if self.backpack.armor:
            cmd_list.append("wr [armor name] (wear)")
        if self.backpack.armor or any(self.equipped_armor.values()):
            cmd_list.append("da [armor name] (dropa)")

        cmd_list.append("cr [recipe] (craft) (type 'cr list' for recipes)")

        current_tile = self.map[self.current_position[1]][self.current_position[0]]
        # Zombie base class, not the FreshZombie/RegularZombie/HeavyZombie
        # tuple used elsewhere in this file (e.g. the map-render check
        # below) - matches punch()'s own isinstance(current_tile, Zombie)
        # check in combat_mixin.py, so SwiftZombie/ToxicZombie/ArmoredZombie
        # don't silently fall through both commands' availability checks.
        if isinstance(current_tile, Zombie):
            cmd_list.append("f (fight)")
            cmd_list.append("p (punch)")
        if self.backpack.food > 0:
            cmd_list.append("ea (eat)")
        if self.backpack.water > 0:
            cmd_list.append("dr (drink)")
        if self.backpack.medicine > 0:
            cmd_list.append("med (medicine)")

        return cmd_list

    def run_game_loop(self):
        try:
            term_width = shutil.get_terminal_size().columns
        except Exception:
            term_width = 80

        left_col_width = max(40, term_width // 2 - 1)
        right_col_width = term_width - left_col_width - 3

        # v3 SPRINT step 6: a native UI (tui.py's TextualIO) renders
        # the map/stats/commands itself via its own widgets - this
        # whole classic two-column ASCII block would otherwise get
        # pushed through self.io.say() every turn and flood a native
        # UI's message log with a redundant duplicate of what its own
        # panels already show. ConsoleIO.renders_natively is False
        # (the default), so classic mode's output is completely
        # unaffected by this split.
        native = getattr(self.io, "renders_natively", False)

        # One-time scene-setter for this expedition's map archetype
        # (world_mixin.generate_map stores it rather than emitting it -
        # generation runs on an io-unsafe thread in the TUI). Emitting
        # here means it lands on the same thread as the rest of the
        # loop's output, in both modes.
        _blurb = getattr(self, 'map_archetype_blurb', None)
        if _blurb and not getattr(self, '_archetype_blurb_shown', False):
            self._archetype_blurb_shown = True
            self.io.say(_blurb)

        while self.health > 0 and not getattr(self, 'won', False):
            # v3 SPRINT fix: this used to be cached once per turn
            # (self._last_cmd_list) and reused by the TUI's every
            # panel refresh - but combat/looting happen INSIDE a
            # single turn (this same while-loop iteration, after a
            # move triggers a fight) and can add weapons/food/water,
            # which that stale per-turn snapshot never picked up until
            # the NEXT command was submitted. Only classic mode needs
            # this list once per turn (for its single printed block);
            # the TUI now always asks fresh (tui.py's refresh_panels())
            # instead of relying on anything cached here.
            cmd_list = self._available_commands()

            if not native:
                # Visual separator between turns to prevent text overlap from previous screens
                self.io.say("\n" + "*" * term_width)

                left_lines = []
                right_lines = []

                # Left Panel: Map
                # Real bug found live: this used to be its own inline copy
                # of the map-rendering logic, separate from print_map()'s
                # - a fix applied to print_map() (terrain symbols, real
                # town feature letters, the legend) never showed up here,
                # since this is the rendering actually used every turn;
                # print_map() itself was only ever reached via the
                # explicit 'm'/'map' command. Sharing one method closes
                # that gap for good, not just for this one fix.
                left_lines.extend(self._render_map_lines())
                left_lines.extend(TERRAIN_LEGEND.split("\n"))

                # Right Panel: Stats & Inventory
                hour = self.time_of_day // 60
                minute = self.time_of_day % 60
                time_str = f"{hour:02d}:{minute:02d}"
                day_night = getattr(self, "day_phase", "night" if self.is_night else "day").title()

                right_lines.append(f"Day {self.day}  {time_str}  {day_night}   Turn {getattr(self, 'turns', 0)}")
                right_lines.append("--- Player Stats ---")
                stats_list = [
                    ("Health", f"{self.health}/{self.max_health}"),
                    ("Hunger", self.hunger),
                    ("Thirst", self.thirst),
                    ("Fatigue", self.fatigue),
                    ("Strength", self.strength),
                    ("Dexterity", self.dexterity),
                    ("Intelligence", self.intelligence),
                    ("Wisdom", self.wisdom),
                    ("Level", self.level),
                    ("XP", f"{self.xp}/{self.max_xp}"),
                ]
                for label, value in stats_list:
                    right_lines.append(f"{label:<12} : {value}")

                if self.equipped_weapon:
                    right_lines.append(f"{'Equipped Weapon':<12} : {self.equipped_weapon.name}")
                else:
                    right_lines.append("Equipped Weapon : None")

                right_lines.append("")
                right_lines.append("--- Inventory ---")
                inv_list = [
                    ("Food", self.backpack.food),
                    ("Water", self.backpack.water),
                    ("Medicine", self.backpack.medicine),
                    ("Ammo", self.backpack.ammo),
                ]
                for label, value in inv_list:
                    right_lines.append(f"{label:<12} : {value}")

                # Consolidated weapons section to fix positioning and overlap issues
                right_lines.append("--- Weapons ---")
                if self.equipped_weapon:
                    right_lines.append(f"Equipped: {self.equipped_weapon}")

                if self.backpack.weapons:
                    right_lines.append("Inventory:")
                    right_lines.extend(format_weapon_list(self.backpack.weapons))
                else:
                    right_lines.append("No weapons in inventory.")

                # Tasks Section (Dynamic Objectives)
                active_tasks = [t for t in self.tasks if not t.completed]
                if active_tasks:
                    right_lines.append("")
                    right_lines.append("--- Active Tasks ---")
                    for i, task in enumerate(active_tasks):
                        reward_info = f"+{task.reward_amount} {task.reward_type}"
                        right_lines.append(f"  [{i+1}] {task.title} ({reward_info})")

                right_lines.append("")
                right_lines.append("What would you like to do?")
                for c in cmd_list:
                    right_lines.append(f"  {c}")

                # Render side-by-side with dynamic column widths to minimize spacing
                max_left_len = max((_visible_len(line) for line in left_lines), default=0)
                max_right_len = max((_visible_len(line) for line in right_lines), default=0)

                left_col_width = max_left_len + 2
                right_col_width = max_right_len

                max_rows = max(len(left_lines), len(right_lines))
                for i in range(max_rows):
                    left_line = left_lines[i] if i < len(left_lines) else ""
                    right_line = right_lines[i] if i < len(right_lines) else ""

                    self.io.say(f"{_display_ljust(left_line, left_col_width)} | {_display_ljust(right_line, right_col_width)}")

            command = self.io.ask("> ").lower()

            direction_aliases = {"north": "n", "south": "s", "east": "e", "west": "w"}
            command = direction_aliases.get(command, command)

            _free = ('m', 'map', 'i', 'inv', 'inventory', 'st', 'stats',
                     'h', '?', 'help', 'commands', 'q', 'quit', 'x',
                     'exit', 'exit game', 'log')
            if command and command not in _free:
                self.turns = getattr(self, 'turns', 0) + 1

            if getattr(self, 'playlog', None) is not None:
                self.playlog.command(command)

            # Track action for automatic goal completion
            self.last_action = self._map_command_to_action(command)

            old_stats = {
                "health": self.health,
                "hunger": self.hunger,
                "thirst": self.thirst,
                "fatigue": self.fatigue,
                "strength": self.strength,
                "dexterity": self.dexterity,
                "intelligence": self.intelligence,
                "wisdom": self.wisdom,
                "level": self.level,
                "xp": self.xp,
            }

            dispatch_map = {
                'exit': lambda: self.io.say("Exiting game..."),
                'n': lambda: self.move_and_search('n'),
                's': lambda: self.move_and_search('s'),
                'e': lambda: self.move_and_search('e'),
                'w': lambda: self.move_and_search('w'),
                'm': self.print_map,
                'map': self.print_map,
                'i': self.display_inventory,
                'inv': self.display_inventory,
                'inventory': self.display_inventory,
                'st': self.stats,
                'stats': self.stats,
                'h': self.print_help,
                '?': self.print_help,
                'help': self.print_help,
                'commands': self.print_help,
                'q': lambda: self.io.say("Exiting game..."),
                'quit': lambda: self.io.say("Exiting game..."),
                'x': lambda: self.io.say("Exiting game..."),
                'exit game': lambda: self.io.say("Exiting game..."),
                'eat': self.eat,
                'ea': self.eat,
                'drink': self.drink,
                'dr': self.drink,
                'medicine': self.use_medicine,
                'med': self.use_medicine,
                'rest': self.rest,
                'r': self.rest,
                'auto': self.auto_play,
                'a': self.auto_play,
                'fight': lambda: self.encounter_zombie(),
                'f': lambda: self.encounter_zombie(),
                'punch': self.punch,
                'p': self.punch,
                'save': lambda: self.save_game(self.io.ask("Enter save slot name (e.g., 'Slot1'): ") + ".json"),
                'sv': lambda: self.save_game(self.io.ask("Enter save slot name (e.g., 'Slot1'): ") + ".json"),
                'ds': self._prompt_delete_save,
                'delete save': self._prompt_delete_save,
                'go': lambda: self.add_goal(self.io.ask("Goal title: "), goal_type=self.io.ask("Goal type (eat/drink/medicine/craft/kill/reach_town): ").lower()),
                'goals': self.list_goals,
                'complete': self._prompt_complete_goal,
                'ts': self.list_tasks,
                'ct': self._prompt_complete_task,
                # v4 Phase B knowledge interface (KnowledgeMixin).
                'journal': self.knowledge_journal,
                'j': self.knowledge_journal,
                'remember': self.knowledge_remember,
                'rem': self.knowledge_remember,
                'think': self.knowledge_remember,
                't': self.knowledge_remember,
                'look': self.knowledge_look,
                'l': self.knowledge_look,
                # v4 investigation commands - routed to the slice or
                # the generated-mystery implementation by mode.
                'search': self._v4_search,
                'sr': self._v4_search,
                'escape': self._v4_escape,
                'clear': self._v4_clear,
                'open': self._v4_clear,
                'open gate': self.slice_open_gate,
                'og': self.slice_open_gate,
                'log': self._toggle_playlog,
            }

            if command in ('q', 'quit'):
                save_choice = self.io.ask("Do you want to save? (y/n): ").lower()
                if save_choice == 'y':
                    self.save_game(self.io.ask("Enter save slot name (e.g., 'Slot1'): ") + ".json")
                self.io.say("\n" + "*" * term_width)
                self.quit = True
                break
            elif command in ('exit', 'x', 'exit game'):
                self.io.say("\n" + "*" * term_width)
                dispatch_map[command]()
                self.quit = True
                break
            
            action = dispatch_map.get(command)
            if action:
                self.io.say("\n" + "*" * term_width)
                action()
            elif command.startswith(('inspect', 'ins ')):
                # v4 Phase B: `inspect <thing>` - Observed/Known/
                # Suspected/Unknown for one thing.
                parts = command.split(maxsplit=1)
                self.knowledge_inspect(parts[1] if len(parts) > 1 else "")
            elif (command.split() or [''])[0] in ('take', 'get', 'grab', 'pickup') or command.startswith('pick up'):
                # v4: a player who finds a note/record and types
                # "take note". Evidence isn't carried - what you learn
                # goes to the journal automatically. But do pick up any
                # dropped gear on this tile, which IS takeable.
                x, y = self.current_position
                cell = self.map[y][x]
                had_ground = isinstance(cell, dict) and bool(cell.get('ground'))
                self.pick_up_ground_items()
                if not had_ground:
                    self.io.say(
                        "Nothing to pick up. Notes, records, signs - you don't "
                        "carry those. What you learn from them is written down "
                        "for you; check `journal` any time."
                    )
            elif command.startswith(('wear', 'wr')):
                # Checked before 'equip'/'eq' below - distinct prefix,
                # no ambiguity risk (equipment-slot investigation).
                parts = command.split()
                if len(parts) > 1:
                    self.equip_armor(' '.join(parts[1:]))
                else:
                    self.io.say("Missing armor name for wear.")
            elif command.startswith(('dropa', 'da')):
                # Checked before the generic 'drop' below - 'dropa'
                # itself starts with 'drop', so this must come first
                # or the weapon-drop branch would swallow it.
                parts = command.split()
                if len(parts) > 1:
                    self.drop_armor(' '.join(parts[1:]))
                else:
                    self.io.say("Missing armor name for dropa.")
            elif command.startswith(('equip', 'eq')):
                parts = command.split()
                if len(parts) > 1:
                    self.equip_weapon(' '.join(parts[1:]))
                else:
                    self.io.say("Missing weapon name for equip.")
            elif command.startswith('drop'):
                parts = command.split()
                if len(parts) > 1:
                    self.drop_weapon(' '.join(parts[1:]))
                else:
                    self.io.say("Missing weapon name for drop.")
            elif command.startswith(('reload', 'rl')):
                parts = command.split()
                weapon_name = ' '.join(parts[1:]) if len(parts) > 1 else None

                target_weapon = self.equipped_weapon
                if weapon_name:
                    candidates = list(self.backpack.weapons)
                    if self.equipped_weapon:
                        candidates.append(self.equipped_weapon)
                    for w in candidates:
                        if isinstance(w, RangedWeapon) and w.name.lower() == weapon_name.lower():
                            target_weapon = w
                            break

                if target_weapon and isinstance(target_weapon, RangedWeapon):
                    # Always tops off to max - drawing from the
                    # backpack's shared ammo pool - rather than asking
                    # the player to type an amount every time.
                    if target_weapon.ammo >= target_weapon.max_ammo:
                        self.io.say(f"{target_weapon.name} is already fully loaded.")
                    elif self.backpack.ammo <= 0:
                        self.io.say("No ammo in your backpack to reload with.")
                    else:
                        used = target_weapon.reload(self.backpack.ammo)
                        self.backpack.ammo -= used
                        self.io.say(
                            f"Reloaded {target_weapon.name} with {used} ammo "
                            f"({target_weapon.ammo}/{target_weapon.max_ammo})."
                        )
                else:
                    self.io.say("No valid ranged weapon found to reload.")
            elif command.startswith(('craft', 'cr')):
                parts = command.split()
                if len(parts) > 1:
                    self.craft(parts[1])
                else:
                    self.io.say("Usage: craft [recipe_name] (type 'craft list' for recipes)")
            else:
                self.io.say(f"Unknown command: '{command}'. Type 'help' for available commands.")

            self.print_stat_changes(old_stats)

            # v4 (V3_ASSUMPTION_AUDIT #1/#8): the goal/task system is
            # replaced by the investigation interface. _auto_check_goals
            # is a harmless no-op on the now-empty goal list; the
            # dynamic task generator is gone entirely.
            self._auto_check_goals()

            if getattr(self, 'playlog', None) is not None:
                self.playlog.snapshot()

        if getattr(self, 'playlog', None) is not None:
            from src.playlog import TeeIO
            reason = ("won - escaped the valley" if getattr(self, 'won', False)
                      else "died" if self.health <= 0
                      else "quit")
            log_path = self.playlog.path
            self.playlog.close(reason)
            self.playlog = None
            # unwrap the tee BEFORE the end-of-game banners below, or
            # their self.io.say() calls write to the now-closed log
            if isinstance(self.io, TeeIO):
                self.io = self.io._inner
            self.io.say(f"Play log saved to {log_path}")

        # v3 SPRINT: the loop above used to just silently end - real
        # gap found live: dying or winning closed the game (in the
        # TUI, the whole app) with nothing telling the player which
        # one happened or why. self.io.ask() blocks until
        # acknowledged in BOTH modes - a real pause to read the
        # result, not just a scrollback line that vanishes when the
        # TUI closes.
        if getattr(self, 'won', False) or self.health <= 0:
            self._render_end_screen()
            self.io.ask("Press Enter to continue...")

    def _render_end_screen(self):
        won = getattr(self, 'won', False)
        k = getattr(self, 'knowledge', None)
        stats = [
            f"turns survived      {getattr(self, 'turns', 0)}",
            f"days survived       {self.day}",
            f"final level         {self.level}",
            f"tiles visited       {len(getattr(self, 'visited', []))}",
        ]
        if k is not None and not k.is_empty():
            stats.append(f"facts established   {len(k.facts_known())}")
        if won:
            headline = "YOU ESCAPED" if (getattr(self, 'slice_mode', False)
                                         or getattr(self, 'mystery', None) is not None) \
                       else "YOU MADE IT"
            title_color = f"{BOLD}{GREEN}"
            closing = "A stash of supplies is waiting for your next run."
        else:
            headline = "YOU DIED"
            title_color = f"{BOLD}{RED}"
            closing = f"{self.name} did not make it out of the valley."
        rows = [headline, f"THE VALLEY  ·  DAY {self.day}", ""] + stats + ["", closing]
        w = max(len(r) for r in rows)
        pad = lambda r: r.center(w) if r in (headline, rows[1], closing) else r.ljust(w)
        box = ["╔" + "═" * (w + 2) + "╗"]
        box += [f"║ {pad(r)} ║" for r in rows]
        box += ["╚" + "═" * (w + 2) + "╝"]
        self.io.say("\n" + title_color + "\n".join(box) + RESET)

    def _toggle_playlog(self):
        """`log` command: start/stop writing a plain-text transcript of
        this session (src/playlog.py) for handing to an analyst."""
        from src.playlog import TeeIO
        if getattr(self, 'playlog', None) is not None:
            path = self.playlog.path
            self.playlog.close("logging stopped by player")
            self.playlog = None
            if isinstance(self.io, TeeIO):
                self.io = self.io._inner
            self.io.say(f"Play logging stopped. Saved to {path}")
            return
        try:
            log_path = self.start_playlog()
        except OSError as exc:
            self.io.say(f"Couldn't start the play log: {exc}")
            return
        # in-game `log` runs on the worker thread, so self.io.say is safe
        # here (unlike start_playlog's --log caller - see start_playlog)
        self.io.say(
            f"Play logging on -> {log_path}\n"
            "Everything you type and everything the game says goes to that "
            "file, plus a per-turn state snapshot. Type `log` again to stop."
        )

    def start_playlog(self, path=None):
        """Start the play log and return its absolute path (or None if
        one is already running). Callable directly for --log.

        Does NOT announce itself: the --log entry points call this from
        the TUI's main/app thread, where TextualIO.say() -> Textual's
        call_from_thread() raises. Callers emit their own confirmation
        by the route that's safe for their thread.
        """
        if getattr(self, 'playlog', None) is not None:
            return None
        import datetime
        from src.playlog import PlayLog, TeeIO
        if path is None:
            path = f"apocrysis_playlog_{datetime.datetime.now():%Y%m%d_%H%M%S}.txt"
        self.playlog = PlayLog(path, self)
        if not isinstance(self.io, TeeIO):
            self.io = TeeIO(self.io, self.playlog)
        return self.playlog.path

    def _render_map_lines(self):
        # Shared by print_map() (the standalone 'm'/'map' command) and
        # run_game_loop()'s per-turn left panel - a single source of
        # truth so a rendering fix here can never again land in one
        # call site and silently not exist in the other (see the
        # comment at run_game_loop()'s own left-panel block for what
        # that gap actually looked like live).
        # A plain grid of tile glyphs - no frame, no coordinate ruler.
        # Both were removed on player feedback (2026-08-28): the '*'
        # border and the a1/b2 row/column labels just invited
        # edge-following instead of reading the terrain. The map's own
        # impassable ring - '^' mountains, '=' rivers - is the real
        # world edge and still renders as terrain below. Every line is
        # exactly `width` visible chars, so the two-column panel layout
        # (which measures with _visible_len) still aligns.
        lines = []

        for y, row in enumerate(self.map):
            line = ""
            map_revealed = getattr(self, 'map_revealed', False)
            for x, tile in enumerate(row):
                dist = abs(x - self.current_position[0]) + abs(y - self.current_position[1])
                actually_visible = dist <= self.visibility_radius
                # A found map reveals the whole terrain/settlement
                # layout (todo 8f9ec034) - geography, not the dynamic
                # layer (zombies stay hidden until you've been there).
                in_range = actually_visible or map_revealed
                if (x, y) == self.current_position:
                    health_pct = self.health / max(1, self.max_health) * 100
                    if health_pct > 75:
                        color = GREEN
                    elif health_pct > 40:
                        color = YELLOW
                    else:
                        color = RED
                    char = f"{BOLD}{color}P{RESET}"
                elif isinstance(tile, dict):
                    if tile.get('terrain') == 'town' and (in_range or self.town_known):
                        # Real bug found live: town tiles used to
                        # render their real feature letter (House/
                        # Road/Shop/Building/Town center) completely
                        # unconditionally - the ONE terrain type that
                        # ignored fog-of-war entirely, so the player
                        # could always see exactly where the town (and
                        # therefore the win condition) was from turn
                        # one, no exploration required. Town tiles now
                        # follow the same in_range/visited/hidden rule
                        # as everything else below, with `town_known`
                        # (set by find_loot()'s map item) as the one
                        # deliberate override - a found map reveals
                        # the town regardless of current visibility.
                        char = tile.get('content') or 'T'
                    elif in_range:
                        # Show real terrain (forest/water/building/
                        # plain), not a blanket '-' - see
                        # TERRAIN_SYMBOLS above.
                        char = TERRAIN_SYMBOLS.get(tile.get('terrain'), '.')
                    elif (x, y) in self.visited:
                        char = '.'
                    else:
                        char = ' '
                elif isinstance(tile, (FreshZombie, RegularZombie, HeavyZombie)):
                    if actually_visible and (x, y) in self.visited:
                        char = 'Z'
                    else:
                        char = '.' if map_revealed else ' '
                else:
                    char = '.' if in_range and (x, y) in self.visited else ' '
                if (x, y) != self.current_position and ((x, y) in self.visited or map_revealed):
                    mark = self._mystery_site_mark(x, y)
                    if mark:
                        char = mark
                line += char
            lines.append(line)

        return lines

    def _mystery_site_mark(self, x, y):
        """Map glyph for a mystery location the player has already
        learned about, so 'the key is in the dam control room' doesn't
        degrade to walking onto every building again. `!` = a lead
        you've found (a named site, or the blocked route); `+` = that
        route once it's open. Returns None for tiles with no marker."""
        m = getattr(self, 'mystery', None)
        if m is None:
            return None
        if m.obstacle_tile == (x, y) and getattr(m, 'saw_obstacle', False):
            return f"{BOLD}{GREEN}+{RESET}" if m.obstacle_open else f"{BOLD}{YELLOW}!{RESET}"
        # The gap in the mountain wall - shown once you either have a
        # map or know there's a blocked route out there to look for.
        if m.escape_tile == (x, y):
            knows_route = 'F_OBSTACLE' in m.knowledge.facts_known()
            if getattr(self, 'map_revealed', False) or knows_route:
                return f"{BOLD}{GREEN}+{RESET}" if m.obstacle_open else f"{BOLD}{YELLOW}!{RESET}"
        for role in getattr(self, '_mystery_named', set()):
            if m.sites.get(role) == (x, y):
                return f"{BOLD}{YELLOW}!{RESET}"
        return None

    def announce_event(self, title, *body_lines, kind="info"):
        """One moment of emphasis for a state change worth interrupting
        the scenery for - a new understanding, an item that matters, an
        objective shift, a weapon breaking. Environmental text repeats
        until the eye tunes it out (playtest: "damn it, I had the
        key?"), so the things that actually CHANGE have to look
        different. The durable copy lives in the journal / objective
        panel afterward; this is just the flare. kind="warn" for bad
        news (red), "info" (cyan) otherwise.
        """
        glyph, color = ("[!]", f"{BOLD}{RED}") if kind == "warn" else ("*", f"{BOLD}{CYAN}")
        rows = [f"{glyph} {title.upper()}"] + [str(b) for b in body_lines]
        rule = "═" * max(30, min(56, max(len(r) for r in rows) + 2))
        body = "\n".join(rows)
        self.io.say(f"\n{color}{rule}\n{body}\n{rule}{RESET}")

    def print_map(self):
        for line in self._render_map_lines():
            self.io.say(line)
        self.io.say(TERRAIN_LEGEND)

    def print_help(self):
        lines = [
            "",
            "--- Controls ---",
            "  arrow keys, or type n / s / e / w        Move",
            "",
            "  See & understand",
            "    m       the map",
            "    l       look around where you are",
            "    i       inventory  (pick a number to equip)",
            "    j       journal - what you've discovered",
            "    t       think - what you currently believe",
            "    inspect <thing>   how certain are you? (e.g. 'inspect the way out')",
            "    ?       this help",
            "",
            "  Act",
            "    take            pick something up off the ground",
            "    open            open or clear the thing in your way",
            "    escape          leave the valley, once you're ready",
            "    search          go over a place again (usually not needed)",
            "",
            "  Survive",
            "    eat / drink / med / rest",
            "",
            "  Fight",
            "    fight           attack a nearby zombie",
            "    punch           attack unarmed",
            "    reload          reload your weapon",
            "",
            "  Equipment  (mostly done through the inventory - `i`)",
            "    equip <weapon>   wear <armor>   drop <thing>   craft <recipe>",
            "",
            "  q or x            quit",
            "",
        ]
        for ln in lines:
            self.io.say(ln)

    def display_inventory(self):
        w = list(self.backpack.weapons)
        a = list(self.backpack.armor)
        self.io.say("\n--- INVENTORY ---")
        if self.equipped_weapon:
            self.io.say(f"  equipped: {self.equipped_weapon}")
        self.io.say("WEAPONS")
        for i, it in enumerate(w, 1):
            self.io.say(f"  [{i}] {it}")
        if not w:
            self.io.say("  (none)")
        if a:
            self.io.say("ARMOR")
            for j, it in enumerate(a, 1):
                self.io.say(f"  [W{j}] {it}")
        self.io.say(f"SUPPLIES  food {self.backpack.food} · water {self.backpack.water} "
                    f"· med {self.backpack.medicine} · ammo {self.backpack.ammo}")

        if not w and not a:
            return
        pick = self.io.ask("Equip which? (number, W# for armor, Enter to close): ").strip().lower()
        if not pick:
            return
        if pick.startswith('w') and pick[1:].isdigit() and 1 <= int(pick[1:]) <= len(a):
            self.equip_armor(a[int(pick[1:]) - 1].name)
        elif pick.isdigit() and 1 <= int(pick) <= len(w):
            self.equip_weapon(w[int(pick) - 1].name)
        else:
            self.io.say("Nothing selected.")

    def stats(self):
        self.io.say("\n--- Player Stats ---")
        self.io.say(f"Health: {self.health}")
        self.io.say(f"Hunger: {self.hunger}")
        self.io.say(f"Thirst: {self.thirst}")
        self.io.say(f"Fatigue: {self.fatigue}")
        self.io.say(f"Strength: {self.strength}")
        self.io.say(f"Dexterity: {self.dexterity}")
        self.io.say(f"Intelligence: {self.intelligence}")
        self.io.say(f"Wisdom: {self.wisdom}")
        if self.equipped_weapon:
            self.io.say(f"Equipped Weapon: {self.equipped_weapon.name}")
        else:
            self.io.say("Equipped Weapon: None")
        for slot, piece in self.equipped_armor.items():
            self.io.say(f"Equipped Armor ({slot}): {piece.name if piece else 'None'}")

    def _map_command_to_action(self, command):
        if command in ('eat', 'ea'): return 'eat'
        if command in ('drink', 'dr'): return 'drink'
        if command.startswith(('craft', 'cr')): return 'craft'
        if command in ('fight', 'f', 'punch', 'p'): return 'kill'
        if command == 'm': return 'map'
        if command in ('n', 's', 'e', 'w'): return 'move'
        if command in ('rest', 'r'): return 'rest'
        if command.startswith(('wear', 'wr')): return 'equip'
        if command.startswith(('dropa', 'da')): return 'drop'
        if command.startswith(('equip', 'eq')): return 'equip'
        if command.startswith('drop'): return 'drop'
        if command.startswith('reload'): return 'reload'
        return ''

