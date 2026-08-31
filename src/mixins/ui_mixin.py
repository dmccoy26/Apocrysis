# Auto-extracted from the original monolithic apocrysis.py during
# the src/ restructuring - see README.md for the project layout.

import random
import shutil

from src.constants import (BOLD, CYAN, GREEN, RED, RESET, YELLOW, BLUE,
                           MAGENTA, ORANGE, GREY, TERRAIN_COLOR)
from src.items import RangedWeapon, format_weapon_list, format_armor_list
from src.text_utils import _visible_len, _display_ljust
from src.zombies import (Zombie, FreshZombie, RegularZombie, HeavyZombie,
                        speed_class_of)


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
        if here in ('closed', 'route', 'require', 'obstacle', 'power'):
            bar.insert(1, "search")
        if m is not None:
            if m.obstacle_open and m.knowledge.hypothesis_state() == 'confirmed' and not m.escaped:
                bar.insert(1, "ESCAPE")
            elif m.controls and here == 'require' and not m.obstacle_open:
                untried = [c for c in m.controls if c not in m.controls_tried]
                bar.insert(1, "pull <" + " / ".join(c.split()[-1] for c in (untried or m.controls)) + ">")
            elif here == m.power_role and self._mystery_has_item() and not m.power_restored:
                bar.insert(1, "(walk in - the fuel goes here)")
            elif getattr(m, 'saw_obstacle', False) and not m.obstacle_open and self._mystery_obstacle_ready():
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
        cmd_list.append("investigation (wi)")
        cmd_list.append("remember (rem)")
        cmd_list.append("inspect [thing]")
        if getattr(self, 'mystery', None) is not None:
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

        # docs/DESIGN_INTERACTION_INFERENCE.md - "auto-equip the
        # strongest weapon / armour at expedition start": unambiguous,
        # no alternative, no commitment, no decision - the survivor
        # "comes in wearing it". Also closes the armor-investigation
        # secondary finding (inherited armour left in the pack after a
        # death). Fires once per expedition, before the loop.
        if not getattr(self, '_auto_equipped', False):
            self._auto_equipped = True
            self._auto_equip_best()

        # F (nav): point the survivor at the entry point on turn 1 -
        # it's where they walked in, it's marked, and it's where the
        # first leads surface. Turns "wander" into "start there".
        _m = getattr(self, 'mystery', None)
        if _m is not None and not getattr(self, '_opening_beat_shown', False):
            self._opening_beat_shown = True
            _cl = _m.sites.get('closed')
            if _cl and _cl != self.current_position:
                from src.nav import bearing
                _b = bearing(self.current_position, _cl)
                self.announce_event(
                    "the way you came in",
                    f"Blocked - but a survivor before you would have "
                    f"looked there first. It's marked{f', {_b}' if _b else ''}.",
                    kind="objective", level=1)

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
                left_lines.extend(self.world.terrain_legend.split("\n"))

                # Right Panel: Stats & Inventory
                hour = self.time_of_day // 60
                minute = self.time_of_day % 60
                time_str = f"{hour:02d}:{minute:02d}"
                day_night = getattr(self, "day_phase", "night" if self.is_night else "day").title()

                right_lines.append(f"Day {self.day}  {time_str}  {day_night}   Turn {getattr(self, 'turns', 0)}")
                right_lines.append("--- Player Stats ---")
                from src.constants import stat_band as _band
                _bc = {"normal": "", "watch": YELLOW, "warning": ORANGE, "danger": RED}

                def _vit(kind, val, maximum=100, shown=None):
                    c = _bc[_band(kind, val, maximum)]
                    s = shown if shown is not None else val
                    return f"{c}{s}{RESET}" if c else str(s)

                stats_list = [
                    ("Health", _vit("hp", self.health, self.max_health,
                                    f"{self.health}/{self.max_health}")),
                    ("Hunger", _vit("hunger", self.hunger)),
                    ("Thirst", _vit("thirst", self.thirst)),
                    ("Fatigue", _vit("fatigue", self.fatigue)),
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
                     'exit', 'exit game', 'log', 'wi', 'investigation')
            if command and command not in _free:
                self.turns = getattr(self, 'turns', 0) + 1

            if getattr(self, 'playlog', None) is not None:
                self.playlog.command(command)

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
                'wi': self.world_investigation_screen,
                'investigation': self.world_investigation_screen,
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
                # v4 Phase B knowledge interface (KnowledgeMixin).
                'journal': self.knowledge_journal,
                'j': self.knowledge_journal,
                'remember': self.knowledge_remember,
                'rem': self.knowledge_remember,
                'think': self.knowledge_remember,
                't': self.knowledge_remember,
                'look': self.knowledge_look,
                'l': self.knowledge_look,
                # v4 investigation commands - the generated-mystery
                # implementation (KnowledgeMixin / MysteryMixin).
                'search': self._v4_search,
                'sr': self._v4_search,
                'escape': self._v4_escape,
                'clear': self._v4_clear,
                'open': self._v4_clear,
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
            elif (command.split(maxsplit=1) or [''])[0] in ('pull', 'try', 'operate'):
                # experimental family: `pull <control>` at the control room
                parts = command.split(maxsplit=1)
                self.mystery_pull_control(parts[1] if len(parts) > 1 else "")
            elif (command.split(maxsplit=1) or [''])[0] in ('use', 'fill', 'refuel', 'pour', 'apply'):
                # infrastructural family: `use fuel` / `fill generator` at the power site
                parts = command.split(maxsplit=1)
                self.mystery_apply_fix(parts[1] if len(parts) > 1 else "")
            elif command.isdigit() or (command[:1] == 'w' and command[1:].isdigit()):
                # numbered equip straight from the "> " prompt - the same
                # [1] / [W1] slots the `i` inventory view lists.
                weapons = list(self.backpack.weapons)
                armor = list(self.backpack.armor)
                if command.isdigit():
                    n = int(command)
                    if 1 <= n <= len(weapons):
                        self.equip_weapon(weapons[n - 1].name)
                    else:
                        self.io.say(f"No weapon [{n}]. Type `i` to see what you're carrying.")
                else:
                    n = int(command[1:])
                    if 1 <= n <= len(armor):
                        self.equip_armor(armor[n - 1].name)
                    else:
                        self.io.say(f"No armor [W{n}]. Type `i` to see what you're carrying.")
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
                # Accepts a name or a pack slot number ('wr 2' / 'wr W2').
                parts = command.split()
                if len(parts) > 1:
                    name = self._gear_arg(' '.join(parts[1:]), 'armor')
                    if name:
                        self.equip_armor(name)
                else:
                    self.io.say("Missing armor name or number for wear.")
            elif command.startswith(('dropa', 'da')):
                # Checked before the generic 'drop' below - 'dropa'
                # itself starts with 'drop', so this must come first
                # or the weapon-drop branch would swallow it.
                parts = command.split()
                if len(parts) > 1:
                    name = self._gear_arg(' '.join(parts[1:]), 'armor')
                    if name:
                        self.drop_armor(name)
                else:
                    self.io.say("Missing armor name or number for dropa.")
            elif command.startswith(('equip', 'eq')):
                parts = command.split()
                if len(parts) > 1:
                    name = self._gear_arg(' '.join(parts[1:]), 'weapon')
                    if name:
                        self.equip_weapon(name)
                else:
                    self.io.say("Missing weapon name or number for equip.")
            elif command.startswith('drop'):
                parts = command.split()
                if len(parts) > 1:
                    name = self._gear_arg(' '.join(parts[1:]), 'weapon')
                    if name:
                        self.drop_weapon(name)
                else:
                    self.io.say("Missing weapon name or number for drop.")
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

            # 1d: status effects (Bleeding / Poison / Stun) count down
            # every game-turn, not only inside combat. _apply_decay
            # already ticks on move/rest; this covers the turns it
            # doesn't (search, look, eat, …). The per-turn guard in
            # _tick_status_effects makes the double call a no-op.
            if command and command not in _free and not getattr(self, 'won', False):
                self._tick_status_effects()

            # docs/DESIGN_SPATIAL_LANGUAGE.md - objective lifecycle:
            # NEW -> ACTIVE -> DISTRACTED -> REMINDER -> URGENT ->
            # COMPLETE. Resurfaces the next step when the investigation
            # stalls; silent while it's progressing.
            if command and command not in _free and not getattr(self, 'won', False):
                self.objective_tick()

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
        # on a win finish_expedition() has already incremented the
        # counter (this run is done); on a death it hasn't (they died
        # ON this one).
        _map_lvl = self.expeditions_completed if won else self.expeditions_completed + 1
        stats = [
            f"map level           {_map_lvl}",
            f"turns survived      {getattr(self, 'turns', 0)}",
            f"days survived       {self.day}",
            f"final level         {self.level}",
            f"tiles visited       {len(getattr(self, 'visited', []))}",
        ]
        if k is not None and not k.is_empty():
            stats.append(f"facts established   {len(k.facts_known())}")
        if won:
            headline = ("YOU ESCAPED" if getattr(self, 'mystery', None) is not None
                        else "YOU MADE IT")
            title_color = f"{BOLD}{GREEN}"
            closing = "A stash of supplies is waiting for your next run."
        else:
            headline = "YOU DIED"
            title_color = f"{BOLD}{RED}"
            closing = (f"{self.name} did not make it out of "
                       f"{self.world.prose.get('region_noun', 'here')}.")
        _place = self.world.prose.get("place_name_fallback", "THE VALLEY")
        rows = [headline, f"{_place}  ·  DAY {self.day}", ""] + stats + ["", closing]
        w = max(len(r) for r in rows)
        pad = lambda r: r.center(w) if r in (headline, rows[1], closing) else r.ljust(w)
        box = ["╔" + "═" * (w + 2) + "╗"]
        box += [f"║ {pad(r)} ║" for r in rows]
        box += ["╚" + "═" * (w + 2) + "╝"]
        self.io.say("\n" + title_color + "\n".join(box) + RESET)
        self._render_investigation_retrospective(won)

    def _render_investigation_retrospective(self, won):
        """A.5.2: the what-changed beat - the transition THIS expedition
        caused for the World Investigation, plus what the next survivor
        can look into. Not a re-print of the `wi` screen."""
        wi = getattr(self, "world_investigation", None)
        if wi is None or not wi.all_facts():
            return
        titles = self.world.prose.get("thread_titles", {})
        learned = list(getattr(self, "_expedition_learned", []))
        lines = [""]
        lore_learned = list(getattr(self, "_expedition_lore_learned", []))
        if won and (learned or lore_learned):
            lines.append(f"{BOLD}{CYAN}WHAT YOU LEARNED{RESET}")
            for fid in learned:
                f = wi.fact(fid)
                if f is not None:
                    lines.append(f"  ✓ {f.statement}")
                    t = titles.get(f.thread, (f.thread.upper(), ""))[0]
                    k, tot = wi.thread_progress().get(f.thread, (0, 0))
                    lines.append(f"    ({t}: {k}/{tot} understood)")
            _by_id = {lo.id: lo for lo in getattr(self.world, "survivor_lore", ())}
            for lid in lore_learned:
                lo = _by_id.get(lid)
                if lo is not None:
                    lines.append(f"  ● {lo.blurb}")
                    lines.append("    (survivors after you will carry this)")
        elif not won:
            lines.append(f"{BOLD}{CYAN}THE INVESTIGATION STANDS{RESET}")
            for thread, (k, tot) in wi.thread_progress().items():
                if k:
                    lines.append(f"  {titles.get(thread, (thread.upper(), ''))[0]}: {k}/{tot}")
        nxt = wi.next_target()
        if nxt is not None:
            nf = wi.fact(nxt)
            if nf is not None:
                lines.append("")
                lines.append(f"{BOLD}{CYAN}THE NEXT SURVIVOR CAN LOOK INTO{RESET}")
                lines.append(f"  {nf.statement}")
        if len(lines) > 1:
            self.io.say("\n".join(lines))

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
        from src import runtime_paths
        from src.playlog import PlayLog, TeeIO
        if path is None:
            path = runtime_paths.resolve(
                "session_log",
                f"apocrysis_playlog_{datetime.datetime.now():%Y%m%d_%H%M%S}.txt")
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
        # world edge and still renders as terrain below.
        #
        # MAP_REALISM_SPEC.md Fix A: each tile renders as glyph + space,
        # so the SQUARE tile array (map_size x map_size) fills a
        # landscape rectangle on screen instead of a portrait one (a
        # terminal cell is ~2:1). Every line is exactly `2 * width`
        # visible chars; the two-column panel layout measures with
        # _visible_len so it still aligns.
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
                        char = f"{TERRAIN_COLOR['town']}{char}{RESET}"
                    elif in_range:
                        # Show real terrain (forest/water/building/
                        # plain), not a blanket '-' - see
                        # world.terrain_symbols. Tint by terrain
                        # (playtest: "colour the squares").
                        _terr = tile.get('terrain')
                        char = self.world.terrain_symbols.get(_terr, '.')
                        _c = TERRAIN_COLOR.get(_terr)
                        if _c:
                            char = f"{_c}{char}{RESET}"
                    elif (x, y) in self.visited:
                        char = '.'
                    else:
                        char = ' '
                elif isinstance(tile, Zombie):
                    if actually_visible and (x, y) in self.visited:
                        # Colour the glyph to its character: a zombie on
                        # the map reads as a threat at a glance, the same
                        # way P is tinted by health and terrain by type.
                        char = f"{BOLD}{RED}Z{RESET}"
                    else:
                        char = '.' if map_revealed else ' '
                else:
                    char = '.' if in_range and (x, y) in self.visited else ' '
                if (x, y) != self.current_position:
                    # Mystery-site markers show even on unexplored,
                    # un-mapped ground - a lead you've learned about is
                    # a destination you should be able to see and head
                    # for. Everything else still respects fog of war.
                    mark = self._mystery_site_mark(x, y)
                    if mark:
                        char = mark
                line += char + " "        # Fix A: glyph + space per tile
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
        # Informational family: the way out isn't a visible gap you can
        # spot on a map - it only exists once the response names it, so
        # it stays hidden until F_ROUTE is known.
        if m.escape_tile == (x, y):
            known = m.knowledge.facts_known()
            if getattr(m, 'family', None) == 'informational':
                show = 'F_ROUTE' in known
            else:
                show = getattr(self, 'map_revealed', False) or 'F_OBSTACLE' in known
            if show:
                return f"{BOLD}{GREEN}+{RESET}" if m.obstacle_open else f"{BOLD}{YELLOW}!{RESET}"
        # A site is marked once the player has LEARNED about it - either
        # by visiting it (_mystery_named) or by knowing the fact that
        # points to it. So "the fuel is at the harbourmaster's shed"
        # gives you a place on the map, not 40 identical buildings to
        # walk onto (playtest, repeatedly).
        known = m.knowledge.facts_known()
        # 'route'/'require' get marked the moment you know the fact that
        # points to them. 'closed' is marked FROM THE START (F, nav): it
        # is where the survivor walked in - they know where it is - and
        # for most mechanisms it's where the first real leads (F_ROUTE /
        # F_REQUIRE) surface. Signposting it turns the opening from
        # "wander until you hit the right building" into "head for the
        # entry point, then follow the leads" (docs/NAV_INVESTIGATION_
        # RESULTS.md: marker salience + earliness is the lever).
        role_known = {'closed': True,
                      'route': 'F_ROUTE' in known, 'require': 'F_REQUIRE' in known,
                      'power': 'F_POWER' in known}
        # B.2 BLUE_SIGNS: a survivor who learned that Protocol Seven
        # blue-signed its routes can pick the signed corridor out from
        # the start of an evac_corridor expedition (they still walk to
        # it). Legibility, not power.
        _sk = getattr(self, 'survivor_knowledge', None)
        if (_sk is not None and _sk.has('BLUE_SIGNS')
                and m.mechanism == 'evac_corridor'):
            role_known['route'] = True
        named = getattr(self, '_mystery_named', set())
        for role, xy in m.sites.items():
            if xy == (x, y) and (role in named or role_known.get(role)):
                return f"{BOLD}{YELLOW}!{RESET}"
        return None

    def perceived_map_grid(self):
        """The map as a plain-glyph 2D grid — exactly what a player can
        see this turn, and nothing more. For the autoplay perception
        boundary (tools/autoplay/): a bot policy pathfinds over THIS,
        never over the unfogged `self.map`.

        Mirrors `_render_map_lines`'s fog rule (`in_range` = within
        `visibility_radius` or a found map; else `.` if visited, else
        ` `) and its glyph choices, but emits no ANSI and no per-turn
        two-column layout. Keep the fog/glyph logic here in sync with
        `_render_map_lines` — that method stays the source of truth for
        what the human sees.

        Returns {"grid": [[glyph, ...], ...] (row-major, grid[y][x]),
        "player": (x, y), "size": n}. Glyphs: 'P' you · 'Z' a zombie
        you can see · '!'/'+' a mystery lead / opened route · terrain
        symbol (world.terrain_symbols) for visible ground · '.' seen
        before, now fogged · ' ' never seen.
        """
        import re as _re
        _ansi = _re.compile(r"\x1b\[[0-9;]*m")
        px, py = self.current_position
        map_revealed = getattr(self, 'map_revealed', False)
        grid = []
        for y, row in enumerate(self.map):
            out_row = []
            for x, tile in enumerate(row):
                dist = abs(x - px) + abs(y - py)
                actually_visible = dist <= self.visibility_radius
                in_range = actually_visible or map_revealed
                if (x, y) == (px, py):
                    out_row.append('P')
                    continue
                mark = self._mystery_site_mark(x, y)
                if mark:
                    out_row.append(_ansi.sub("", mark) or '!')
                    continue
                if isinstance(tile, dict):
                    if tile.get('terrain') == 'town' and (in_range or self.town_known):
                        out_row.append(tile.get('content') or 'T')
                    elif in_range:
                        _terr = tile.get('terrain')
                        out_row.append(self.world.terrain_symbols.get(_terr, '.'))
                    elif (x, y) in self.visited:
                        out_row.append('.')
                    else:
                        out_row.append(' ')
                elif isinstance(tile, Zombie):
                    if actually_visible and (x, y) in self.visited:
                        out_row.append('Z')
                    else:
                        out_row.append('.' if map_revealed else ' ')
                else:
                    out_row.append('.' if in_range and (x, y) in self.visited else ' ')
            grid.append(out_row)
        return {"grid": grid, "player": (px, py), "size": self.map_size}

    # --- the Apocrysis attention language (docs/ATTENTION_SYSTEM_SPEC.md) ---
    # Semantic CLASSES, not alarm levels. (glyph, colour, loud?) - only
    # DANGER and STORY get the full banner; the rest are one coloured,
    # glyph-prefixed line. Reserve red for DANGER.
    _ATTENTION = {
        "danger":    ("‼",  RED,     True),
        "story":     ("◈",  MAGENTA, True),
        "objective": ("◆",  BLUE,    False),
        "warning":   ("⚠",  ORANGE,  False),
        "discovery": ("✦",  YELLOW,  False),
        "success":   ("✓",  GREEN,   False),
        "info":      ("•",  CYAN,    False),
    }
    # Old kind strings -> (class, label prefix, default LEVEL). Kept so
    # no call site needs to change; the label text is preserved verbatim
    # (tests assert on it). LEVEL is the docs/DESIGN_ATTENTION_LANGUAGE.md
    # interruption grade: 0 folds into the stream · 1 a coloured line ·
    # 2 a banner · 3 a banner that must be acknowledged. A caller can
    # still pass `level=` to override (the encounter card grades from
    # the forecast; the supply/HP warnings grade from the deterioration
    # ladder; the objective lifecycle grades by stall depth).
    _KIND_ALIAS = {
        "warn":       ("warning",   "",                        1),
        "solved":     ("success",   "MYSTERY SOLVED — ",        2),
        "lore":       ("success",   "SURVIVORS NOW KNOW — ",    2),
        "milestone":  ("story",     "A PIECE FALLS INTO PLACE — ", 2),
        "correction": ("story",     "YOU HAD IT WRONG — ",      2),  # the E.1 beat - a loud banner
        "lead":       ("discovery", "NEW LEAD — ",              2),  # a lead names a destination
        "discovery":  ("discovery", "NEW DISCOVERY — ",         1),
        "objective":  ("objective", "OBJECTIVE UPDATED — ",     1),
        "reminder":   ("objective", "",                         1),  # objective-lifecycle nudge (no "UPDATED" prefix)
        "info":       ("info",      "",                         1),
        # the new class names, usable directly
        "danger":     ("danger",    "",                         2),
        "warning":    ("warning",   "",                         1),
        "story":      ("story",     "",                         2),
        "success":    ("success",   "",                         1),
    }

    def announce_event(self, title, *body_lines, kind="info", level=None):
        """One flare for a state change worth interrupting the scenery
        for. `kind` = the semantic channel; `level` (0–3) = how much to
        interrupt:  L0 folds into the stream · L1 a coloured line · L2 a
        banner · L3 a banner that must be acknowledged.
        """
        _alias = self._KIND_ALIAS.get(kind, ("info", "", 1))
        cls, prefix = _alias[0], _alias[1]
        glyph, color, _loud = self._ATTENTION[cls]
        if level is None:
            level = _alias[2] if len(_alias) > 2 else 1
        head = title.upper() if cls in ("danger", "warning") else title
        rows = [f"{glyph} {prefix}{head}"] + [str(b) for b in body_lines]
        body = "\n".join(rows)

        if level >= 2:
            width = (60 if level >= 3
                     else max(30, min(56, max(len(r) for r in rows) + 2)))
            rule = "═" * width
            lead = "\n\n" if level >= 3 else "\n"
            # L3 = a wider banner with a blank lead - the visual break
            # IS the "stop and reconsider". No forced Press-Enter: for
            # the one case that wants an explicit gate (an EXTREME
            # encounter) the combat card's own `[f]/[e]/[w]` prompt
            # follows immediately; a gate anywhere else (mid escape /
            # mid finish_expedition) just disrupts the sequence and
            # breaks non-interactive callers.
            self.io.say(f"{lead}{BOLD}{color}{rule}\n{body}\n{rule}{RESET}")
        elif level == 1:
            self.io.say(f"\n{BOLD}{color}{body}{RESET}")
        else:  # L0 — one quiet line, folded into the scenery
            tail = " — ".join(str(b) for b in body_lines)
            line = f"{glyph} {head}" + (f" — {tail}" if tail else "")
            self.io.say(f"{color}{line}{RESET}")

    def print_map(self):
        for line in self._render_map_lines():
            self.io.say(line)
        self.io.say(self.world.terrain_legend)

    def print_help(self):
        lines = [
            "",
            "--- Controls ---",
            "  arrow keys, or type n / s / e / w        Move",
            "",
            "  See & understand",
            "    m       the map",
            "    l       look around where you are",
            "    i       inventory  (then a number, or type the number straight)",
            "    j       journal - what you've discovered",
            "    t       think - what you currently believe",
            "    inspect <thing>   how certain are you? (e.g. 'inspect the way out')",
            "    ?       this help",
            "",
            "  Act",
            "    take            pick something up off the ground",
            "    open            open or clear the thing in your way",
            "    pull <thing>    work a control / lever / valve",
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
            "  Equipment",
            "    1 2 3 ...         equip that weapon from `i`   (W1 W2 = armor)",
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

    def world_investigation_screen(self):
        """A.4.1 / audit 1a - what this campaign has pieced together, and
        what it's still missing. Reads WorldInvestigation; never
        re-derives the DAG. Player-facing text only - thread titles,
        fact statements, and the short `lead` handles, no schema
        vocabulary. The player should leave this screen able to say
        what they know, what evidence remains, and what advances it."""
        wi = getattr(self, "world_investigation", None)
        if wi is None or not wi.all_facts():
            self.io.say("\nYou don't have enough yet to say what happened here.")
            return
        titles = self.world.prose.get("thread_titles", {})
        prog = wi.thread_progress()
        ms = len(wi.milestones_known())
        eligible = {f.id for f in wi.eligible()}

        # which fact THIS expedition can establish (generate_map bound
        # the mystery to wi.next_target()).
        _m = getattr(self, "mystery", None)
        _run_fid = getattr(_m, "world_fact_id", None) if _m is not None else None
        _run_fact = wi.fact(_run_fid) if _run_fid else None

        self.io.say(f"\n{BOLD}{CYAN}╔═══ THE APOCRYSIS ═══╗{RESET}")
        self.io.say(f"  {ms} milestone{'s' if ms != 1 else ''} understood")
        # E.1: the working theory - the belief that later milestones will
        # break. Shown so its fall lands.
        _hyp = wi.current_hypothesis()
        if _hyp is not None:
            self.io.say(f"  {YELLOW}What you think happened:{RESET} {_hyp.statement}")

        seen_threads = []
        for f in wi.all_facts():
            if f.thread not in seen_threads:
                seen_threads.append(f.thread)
        for thread in seen_threads:
            known, total = prog.get(thread, (0, 0))
            title, question = titles.get(thread, (thread.upper(), ""))
            bar_n = 12
            filled = 0 if not total else round(bar_n * known / total)
            bar = "█" * filled + "░" * (bar_n - filled)
            self.io.say(f"\n  {BOLD}{title}{RESET}   {bar}  {known}/{total}")
            if question:
                self.io.say(f"  {question}")
            deferred = 0
            for f in wi.all_facts():
                if f.thread != thread:
                    continue
                st = wi.status(f.id)
                if st == "known":
                    self.io.say(f"    {GREEN}✓{RESET} {f.statement}")
                elif st == "suspected":
                    self.io.say(f"    · {f.statement}")
                elif f.id in eligible:
                    # a lead you could pick up now - name it, so the
                    # player knows what evidence remains (audit 1a).
                    tag = (f"   {YELLOW}<- this expedition{RESET}"
                           if _run_fact is not None and f.id == _run_fact.id
                           else "")
                    self.io.say(f"    {YELLOW}○{RESET} {f.lead or f.id}{tag}")
                else:
                    deferred += 1
            if deferred:
                self.io.say(f"    {GREY}? {deferred} further, deeper in{RESET}")

        # NEXT - the single most useful thing to chase now.
        if _run_fact is not None and not wi.is_known(_run_fact.id):
            self.io.say(f"\n  {BOLD}NEXT{RESET}  this expedition can establish: "
                        f"{_run_fact.lead or _run_fact.id}")
            self.io.say(f"  {GREY}find the way out - solving it is what pieces "
                        f"this together.{RESET}")
        elif eligible:
            _nx = next((f for f in wi.all_facts() if f.id in eligible), None)
            if _nx is not None:
                self.io.say(f"\n  {BOLD}NEXT{RESET}  a lead you can pick up: "
                            f"{_nx.lead or _nx.id}")

        # B.2c: the concrete lessons carried between survivors.
        sk = getattr(self, "survivor_knowledge", None)
        learned = sk.learned_ids() if sk else []
        if learned:
            by_id = {lo.id: lo for lo in getattr(self.world, "survivor_lore", ())}
            self.io.say(f"\n  {BOLD}WHAT SURVIVORS HAVE LEARNED{RESET}")
            for lid in learned:
                lo = by_id.get(lid)
                if lo is not None:
                    self.io.say(f"    · {lo.blurb}")
        self.io.say("")

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
