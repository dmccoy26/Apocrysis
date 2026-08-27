# v3 SPRINT step 6: the textual TUI - the presentation layer for an
# already-finished game (steps 1-5 landed first, deliberately, so
# this renders the real final state shape rather than a moving
# target). Per the sprint plan's governing invariant, this reads/
# writes only through the one Apocrysis instance it owns - it never
# imports a mixin directly and never duplicates game logic.
#
# Apocrysis.run_game_loop() (ui_mixin.py) is a synchronous, blocking
# while-loop that calls self.io.say()/self.io.ask()/self.io.ask_yes_no()
# - unchanged by the TUI's existence (see io_console.py's ConsoleIO,
# the byte-identical default). TextualIO bridges that synchronous loop
# into Textual's async app by running the loop on a background worker
# thread; say() posts to the log from that thread, ask()/ask_yes_no()
# block the worker thread on a queue.Queue until the Input widget's
# Submitted handler (on the UI thread) supplies an answer.

import queue

from rich.text import Text

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Static, Input, RichLog, ProgressBar

from src.game import Apocrysis
from src.items import format_weapon_list, format_armor_list
from src.mixins.persistence_mixin import profile_filename_for_name


class AppClosed(Exception):
    """Raised out of TextualIO.ask()/ask_yes_no() when the app is
    shutting down while the game thread is still waiting on an
    answer - see TextualIO._wait_for_answer()'s docstring."""


class TextualIO:

    # Tells ui_mixin.py's run_game_loop() to skip its own classic
    # two-column ASCII block (io_console.py's ConsoleIO has the same
    # attribute, False) - this TUI's own widgets render the map/stats/
    # commands instead, via refresh_panels() below.
    renders_natively = True

    def __init__(self, app):
        self.app = app
        self._answers = queue.Queue()

    def say(self, *args, **kwargs):
        text = " ".join(str(a) for a in args)
        self.app.call_from_thread(self.app.log_message, text)

    def ask(self, prompt=""):
        self._drain_stale_answers()
        self.app.call_from_thread(self.app.request_input, prompt)
        return self._wait_for_answer()

    def ask_yes_no(self, prompt):
        self._drain_stale_answers()
        self.app.call_from_thread(self.app.request_input, f"{prompt} (y/n)")
        while True:
            answer = self._wait_for_answer().strip().lower()
            if answer in ("y", "yes"):
                return True
            if answer in ("n", "no"):
                return False
            self.app.call_from_thread(self.app.log_message, "Please answer y or n.")
            self._drain_stale_answers()
            self.app.call_from_thread(self.app.request_input, f"{prompt} (y/n)")

    def _drain_stale_answers(self):
        # Real bug found live: self._answers is never drained between
        # prompt cycles - rapidly pressing arrow keys during one "> "
        # prompt (action_move_direction below calls submit_answer()
        # directly, same queue the Input widget's Submitted handler
        # also feeds) can queue MORE entries than this prompt's single
        # _wait_for_answer() call consumes. Those leftovers then sit
        # in the queue and get silently handed to whichever LATER,
        # unrelated prompt calls _wait_for_answer() next (e.g. a "Do
        # you want to fight? (y/n)" dialog), answering it with a stale
        # keypress instead of waiting for real input directed at it.
        # Clearing the queue right before a new prompt starts
        # listening ensures it only ever consumes input submitted
        # during its OWN active window.
        while True:
            try:
                self._answers.get_nowait()
            except queue.Empty:
                break

    def _wait_for_answer(self):
        # Real bug found live: an unbounded self._answers.get() blocks
        # this OS thread (run_worker(thread=True), not a cancellable
        # asyncio task) forever if the app closes for any reason OTHER
        # than the game thread's own natural exit (a crash elsewhere,
        # the user force-closing the terminal, a test harness tearing
        # down) - and Python can't fully exit while that thread is
        # still alive. Poll with a short timeout and bail out via
        # AppClosed the moment app.is_running goes False, instead of
        # waiting on a queue nothing will ever fill again.
        while True:
            if not self.app.is_running:
                raise AppClosed()
            try:
                return self._answers.get(timeout=0.2)
            except queue.Empty:
                continue

    def submit_answer(self, text):
        self._answers.put(text)


class ApocrysisApp(App):

    # v3 SPRINT: exactly 3 bordered panels - map, stats, and one
    # "console" panel that holds BOTH the message log and the command
    # input (sharing #console's single border, each with border:none
    # of its own) rather than the log and input reading as two
    # separate boxes.
    # v3 SPRINT: main (map+stats) vs console (log+input) used to
    # split 1fr-vs-fixed-12, which starved the console - the one
    # place all the game's narrative text goes - of any real room.
    # Both now share the remaining space (roughly 55/45) so the log
    # actually has enough height to read without constant scrolling.
    CSS = """
    #body {
        height: 1fr;
    }
    #left_col {
        width: 1fr;
    }
    #main {
        height: 65%;
    }
    #map_panel_wrap {
        width: 1fr;
        border: solid $accent;
        padding: 1;
    }
    #directions_text {
        color: $text-muted;
        margin-bottom: 1;
    }
    #map_scroll {
        overflow: auto auto;
    }
    #map_panel {
        width: auto;
        height: auto;
    }
    #stats_panel {
        width: 60;
        height: 1fr;
        border: solid $accent;
        padding: 1;
        overflow-y: auto;
    }
    .stat_row {
        height: 1;
        margin-bottom: 1;
    }
    .stat_label {
        width: 10;
    }
    .stat_bar {
        width: 1fr;
    }
    #console {
        height: 1fr;
        border: solid $accent;
    }
    #log {
        height: 1fr;
        border: none;
    }
    #command_input {
        border: none;
        height: 3;
    }
    """

    # v3 SPRINT: arrow keys move directly, without needing to type
    # n/s/e/w into the command box and press Enter. priority=True so
    # they fire even while the Input has focus (Textual would
    # otherwise let a focused Input consume arrow keys itself, for
    # cursor movement). Only actually submits a move when the game is
    # at its main "> " command prompt (see _expecting_command below) -
    # not mid-dialog (a save-slot name, a goal title, a y/n prompt),
    # where an arrow key press should do nothing rather than silently
    # submit "n"/"s"/etc. as if it were text.
    BINDINGS = [
        ("up", "move_direction('n')", "Move north"),
        ("down", "move_direction('s')", "Move south"),
        ("left", "move_direction('w')", "Move west"),
        ("right", "move_direction('e')", "Move east"),
    ]

    def __init__(self, name=None, level=1, seed=None, hardcore=False):
        super().__init__()
        self._name = name
        self._level = level
        self._seed = seed
        self._hardcore = hardcore
        self.player = None
        self.io = None
        self._expecting_command = False
        # Set by _new_player() each time it's called, so on_mount()
        # (main thread) and _game_thread() (worker thread) can each
        # emit the "Welcome back" greeting through the right channel
        # for their own thread - see _new_player()'s docstring.
        self._last_load_was_profile = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="body"):
            with Vertical(id="left_col"):
                with Horizontal(id="main"):
                    with Vertical(id="map_panel_wrap"):
                        yield Static(
                            "Directions:  ↑/N  ↓/S  ←/W  →/E   "
                            "(arrow keys or type n/s/e/w)",
                            id="directions_text",
                        )
                        with ScrollableContainer(id="map_scroll"):
                            yield Static(id="map_panel")
                with Vertical(id="console"):
                    yield RichLog(id="log", max_lines=200)
                    yield Input(placeholder="command", id="command_input")
            with Vertical(id="stats_panel"):
                yield Static(id="stats_text")
                yield Static(id="objective_text")
                with Horizontal(classes="stat_row"):
                    yield Static("Health", classes="stat_label")
                    yield ProgressBar(id="health_bar", total=100, show_eta=False, classes="stat_bar")
                with Horizontal(classes="stat_row"):
                    yield Static("Hunger", classes="stat_label")
                    yield ProgressBar(id="hunger_bar", total=100, show_eta=False, classes="stat_bar")
                with Horizontal(classes="stat_row"):
                    yield Static("Thirst", classes="stat_label")
                    yield ProgressBar(id="thirst_bar", total=100, show_eta=False, classes="stat_bar")
                with Horizontal(classes="stat_row"):
                    yield Static("Fatigue", classes="stat_label")
                    yield ProgressBar(id="fatigue_bar", total=100, show_eta=False, classes="stat_bar")
                yield Static(id="commands_text")
        yield Footer()

    def action_move_direction(self, direction):
        if self.io is not None and self._expecting_command:
            self.io.submit_answer(direction)

    def _new_player(self):
        # Shared by on_mount() (first launch, main thread) and
        # _game_thread()'s post-win loop below (worker thread) - both
        # need the exact same "continue from a saved profile, or
        # start fresh" construction. Real bug found live: this used
        # to build the greeting itself via self.io.say(), which calls
        # Textual's call_from_thread() internally - that raises
        # RuntimeError when called from the SAME thread as the app
        # loop, which is exactly the case for on_mount()'s call here.
        # Instead this just records whether a profile was loaded
        # (self._last_load_was_profile) and leaves emitting the
        # greeting to each caller, which knows its own thread.
        profile = Apocrysis.load_profile_by_name(self._name) if self._name else None
        self._last_load_was_profile = profile is not None
        if profile is not None:
            player = Apocrysis(
                profile.get("name", self._name or "Survivor"),
                level=profile.get("level", 1),
                hardcore=profile.get("hardcore", self._hardcore),
                expeditions_completed=profile.get("expeditions_completed", 0),
                io=self.io,
            )
            player.apply_profile(profile)
        else:
            player = Apocrysis(
                self._name or "Survivor",
                level=self._level,
                seed=self._seed,
                hardcore=self._hardcore,
                io=self.io,
            )
        return player

    def _save_or_delete_profile(self):
        if self.player.hardcore and self.player.health <= 0:
            self.player.delete_profile()
        else:
            self.player.save_profile(profile_filename_for_name(self.player.name))

    def on_mount(self):
        self.io = TextualIO(self)
        self.player = self._new_player()
        if self._last_load_was_profile:
            # Main thread here (on_mount runs on the app's own event
            # loop) - log_message() directly, not self.io.say()'s
            # call_from_thread() marshaling, which would raise.
            self.log_message(
                f"Welcome back, {self.player.name} - level {self.player.level}."
            )

        self.refresh_panels()
        self.query_one("#command_input", Input).focus()
        self.run_worker(self._game_thread, thread=True)

    def _game_thread(self):
        # Real bug found live: this used to always exit the whole app
        # the moment run_game_loop() returned, for ANY reason - quit,
        # death, OR a win. Classic mode's cli.py main() loop already
        # gets this right (checks player.won and starts a fresh game
        # instead of exiting); the TUI never had the same check, so
        # pressing Enter at the "Press Enter to continue..." prompt
        # after a WIN just closed the whole app instead of starting
        # the next game with the carried-forward profile.
        try:
            while True:
                try:
                    self.player.run_game_loop()
                except AppClosed:
                    # Real bug found live: AppClosed raised mid-
                    # run_game_loop() (app shutting down while blocked
                    # on an ask()/ask_yes_no() prompt) skipped straight
                    # to the outer except below, past the
                    # save_profile() call two lines down - a valid,
                    # in-progress player's identity/progression was
                    # silently never saved on shutdown. Save (or, for
                    # a hardcore character who already died, delete)
                    # here, using whatever state self.player was
                    # actually in when the shutdown interrupted it,
                    # then re-raise to the same outer handling as
                    # before.
                    self._save_or_delete_profile()
                    raise

                self._save_or_delete_profile()

                if not getattr(self.player, 'won', False):
                    break  # quit or death - a real exit, not a new game

                self.player = self._new_player()
                if self._last_load_was_profile:
                    # Worker thread here - self.io.say() is the
                    # correct channel, its call_from_thread() call is
                    # only valid off the app's own thread.
                    self.player.io.say(
                        f"Welcome back, {self.player.name} - level {self.player.level}."
                    )
                self.call_from_thread(self.refresh_panels)
        except AppClosed:
            # App is already shutting down for some other reason -
            # nothing left to do here, and calling self.exit() again
            # below would be redundant (still safe, guarded by
            # is_running).
            pass

        if self.is_running:
            self.call_from_thread(self.exit)

    def request_input(self, prompt):
        input_widget = self.query_one("#command_input", Input)
        # Real bug found live: this only ever updated .placeholder
        # (shown when the field is empty) - text a player had already
        # TYPED but not yet submitted stayed sitting in .value,
        # untouched, when the prompt underneath it changed (e.g. a
        # move triggers a zombie encounter's "Do you want to fight?"
        # while the player had already typed their next intended move
        # and just hadn't hit Enter yet). Pressing Enter then silently
        # submitted that stale text as the answer to whatever's
        # actually being asked NOW, not what was on screen when it was
        # typed - a fast typist could end up "answering" a fight
        # prompt with a movement letter (which, since 'n' also means
        # "no", could decline to fight, or on any other stray text,
        # re-prompt) with no visible error, just an unintended outcome
        # that looked like "random" movement/combat to the player.
        # Clearing .value here forces a conscious re-type of whatever
        # the CURRENT prompt is actually asking.
        input_widget.value = ""
        input_widget.placeholder = prompt
        # Arrow-key movement (action_move_direction above) only
        # submits when the game is actually waiting at its main "> "
        # command prompt - not mid-dialog (save-slot name, goal
        # title, a y/n prompt), where an arrow press should do
        # nothing rather than submit a stray "n"/"s"/etc. as text.
        self._expecting_command = (prompt == "> ")
        # Refresh right before waiting for the next command too, not
        # just after a message - covers a turn where nothing was said
        # but state still changed (defensive; in practice
        # move_and_search() etc. always say() at least "Moved n.").
        self.refresh_panels()

    def log_message(self, text):
        # Same ANSI issue as the map panel above - plenty of game
        # messages (level-ups, victory/death text, print_stat_changes'
        # colored deltas) carry raw BOLD/GREEN/RED/RESET escape codes
        # meant for a real terminal's print(). Text.from_ansi() turns
        # them into real Rich styling instead of literal garbage bytes.
        if text and text.strip():
            self.query_one("#log", RichLog).write(Text.from_ansi(text))
        self.refresh_panels()

    def refresh_panels(self):
        if self.player is None:
            return

        p = self.player

        # Real bug found live: _render_map_lines() (ui_mixin.py, shared
        # with classic mode) embeds raw ANSI escape codes to color the
        # player marker by health - correct for a real terminal's
        # print(), but Static.update() with a plain string doesn't
        # interpret those bytes as color codes at all. The result was
        # an apparently blank map panel and stray artifact characters
        # (the literal, un-parsed escape bytes) - Text.from_ansi()
        # parses the same string into real Rich styling instead.
        map_widget = self.query_one("#map_panel", Static)
        map_widget.update(Text.from_ansi("\n".join(p._render_map_lines())))

        stats_widget = self.query_one("#stats_text", Static)
        # v3 SPRINT: showed only the bare weapon name (equipped and
        # backpack both) - no way to compare a looted weapon against
        # what's equipped without typing "i". str(weapon) already
        # carries damage/durability (items.py) - use it here too.
        equipped = str(p.equipped_weapon) if p.equipped_weapon else "None"
        equipped_armor = "\n  ".join(
            f"{slot}: {piece.name if piece else 'None'}"
            for slot, piece in p.equipped_armor.items()
        )
        backpack_weapons = (
            "\n  ".join(format_weapon_list(p.backpack.weapons))
            if p.backpack.weapons
            else "(none)"
        )
        backpack_armor = (
            "\n  ".join(format_armor_list(p.backpack.armor))
            if p.backpack.armor
            else "(none)"
        )
        day_phase = getattr(p, "day_phase", "night" if p.is_night else "day").title()
        stats_widget.update(
            f"{p.name} - Level {p.level}\n"
            f"XP: {p.xp}/{p.max_xp}\n"
            f"Day {p.day} - {day_phase}\n"
            f"Equipped: {equipped}\n"
            f"Armor:\n  {equipped_armor}\n"
            f"Backpack weapons:\n  {backpack_weapons}\n"
            f"Backpack armor:\n  {backpack_armor}\n"
            f"Food {p.backpack.food}  Water {p.backpack.water}  "
            f"Medicine {p.backpack.medicine}  Ammo {p.backpack.ammo}\n"
        )

        self.query_one("#health_bar", ProgressBar).update(progress=max(0, min(100, p.health)))
        self.query_one("#hunger_bar", ProgressBar).update(progress=max(0, min(100, p.hunger)))
        self.query_one("#thirst_bar", ProgressBar).update(progress=max(0, min(100, p.thirst)))
        self.query_one("#fatigue_bar", ProgressBar).update(progress=max(0, min(100, p.fatigue)))

        # v3 SPRINT: real gap found live - nothing on screen told the
        # player what they were actually supposed to DO (move to the
        # town center to win). Surface the first incomplete goal as a
        # standing objective line, not just buried in a "goals" list
        # command the player has to know to type.
        objective_widget = self.query_one("#objective_text", Static)
        next_goal = next((g for g in p.goals if not g.completed), None)
        if next_goal is not None:
            objective_widget.update(f"Objective: {next_goal.title}\n{next_goal.description}")
        else:
            objective_widget.update("Objective: all goals complete")

        # Context-sensitive available commands (ui_mixin.py's
        # _available_commands()) - the same list the classic ASCII
        # block would have shown, now rendered natively instead of
        # being pushed through the log. Always computed fresh here
        # (real bug found live: a cached once-per-turn snapshot went
        # stale mid-turn, e.g. right after combat added a weapon to
        # the backpack but before the next command started a new
        # turn - eat/drink/eq silently vanished from the list until
        # the player submitted another command).
        commands_widget = self.query_one("#commands_text", Static)
        commands_widget.update(
            "Commands:\n"
            + "\n".join(f"  {c}" for c in p._available_commands())
        )

    def on_input_submitted(self, event: Input.Submitted):
        text = event.value
        event.input.value = ""
        event.input.placeholder = "command"
        if self.io is not None:
            self.io.submit_answer(text)
