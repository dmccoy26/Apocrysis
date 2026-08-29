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
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Static, Input, RichLog, ProgressBar

from src.game import Apocrysis
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


_PHASE_GLYPH = {"day": "☀", "night": "☾", "dusk": "◐", "dawn": "☼"}
_PHASE_COLOR = {"day": "yellow", "night": "blue", "dusk": "#d08a3c", "dawn": "#d08a3c"}
_HDR = "bold grey70"          # section headers
_DIM = "grey50"


def _dur_color(cur, mx):
    if cur is None:
        return None
    if cur <= 0:
        return "red"
    if mx and cur <= mx * 0.25:
        return "yellow"
    return _DIM


def _fmt_gear(item):
    """One coloured line for a weapon or armor piece."""
    name = getattr(item, "name", "?")
    parts = [f"{name[:18]:<18}"]
    dmg = getattr(item, "damage", None)
    if dmg is not None:
        parts.append(f"[cyan]{dmg} dmg[/]")
    red = getattr(item, "damage_reduction", None)
    if red is not None:
        parts.append(f"[cyan]-{red}[/]")
    ammo, mx_ammo = getattr(item, "ammo", None), getattr(item, "max_ammo", None)
    if mx_ammo:
        c = "red" if not ammo else _DIM
        parts.append(f"[{c}]ammo {ammo}/{mx_ammo}[/]")
    dur = getattr(item, "durability", None)
    mxd = getattr(item, "max_durability", dur)
    c = _dur_color(dur, mxd)
    if c:
        parts.append(f"[{c}]{dur}/{mxd}[/]")
    return "  " + "  ".join(parts)


def _gear_lines(items):
    """Grouped, coloured lines - identical items collapse to 'xK'."""
    order, seen = [], {}
    for it in items:
        key = str(it)
        if key not in seen:
            seen[key] = [it, 0]
            order.append(key)
        seen[key][1] += 1
    out = []
    for key in order:
        it, n = seen[key]
        line = _fmt_gear(it)
        if n > 1:
            line += f"  [{_DIM}]x{n}[/]"
        out.append(line)
    return out


def _location_name(p):
    """A short name for where the player is standing - the mystery
    site label if they're on a named site, otherwise terrain-derived."""
    x, y = p.current_position
    cell = p.map[y][x]
    if isinstance(cell, dict):
        if cell.get("site_label"):
            return cell["site_label"].upper()
        if cell.get("terrain") == "town":
            d = cell.get("district")
            return f"{d.upper()} DISTRICT" if d else "SETTLEMENT"
        t = cell.get("terrain")
        names = {"forest": "FOREST", "water": "WATER", "swamp": "SWAMP",
                 "plain": "OPEN GROUND", "building": "A BUILDING",
                 "mountain": "THE MOUNTAIN WALL"}
        return names.get(t, "THE VALLEY")
    return "THE VALLEY"


_FACT_LABEL = {
    "F_CLOSED": "the usual way out is shut",
    "F_ROUTE": "there's another route",
    "F_OBSTACLE": "that route is blocked",
    "F_REQUIRE": "know what unblocks it",
}


def _objective_steps(p, m, k):
    """The OBJECTIVES checklist, generated from THIS mystery's own
    structure (site labels, mechanism, requirement item) rather than a
    generic list. It's the player's external memory - "what did I do
    80 turns ago" - so every line is phrased from what the player has
    actually learned, not the hidden Escape Proof. The one actionable
    step is highlighted; the journal keeps the detail."""
    try:
        from src.escape import MECHANISMS
        _spec = MECHANISMS.get(m.mechanism, {})
        mech_name = _spec.get("name", "the way out")
    except Exception:
        _spec = {}
        mech_name = "the way out"
    known = k.facts_known()
    # informational (reveals_route): the route has no name the player
    # knows until the response gives it - don't leak it in the header.
    _info = bool(_spec.get("reveals_route"))
    if _info and "F_ROUTE" not in known:
        mech_name = "the way out"
    named = getattr(p, "_mystery_named", set())
    labels = getattr(m, "site_labels", {})
    has_item = (any(getattr(it, "name", None) == m.requirement_item
                    for it in p.backpack.items)
                or m.obstacle_open or m.power_restored)
    confirmed = k.hypothesis_state() == "confirmed"

    def place(role, generic):
        return labels.get(role, generic) if role in named else generic

    def _compass(xy):
        if not xy:
            return ""
        px, py = p.current_position
        dx, dy = xy[0] - px, xy[1] - py
        ns = "north" if dy < -1 else "south" if dy > 1 else ""
        ew = "west" if dx < -1 else "east" if dx > 1 else ""
        d = "-".join(x for x in (ns, ew) if x)
        return f" ({d})" if d else " (near here)"

    def heading(role):
        # compass hint from where the player IS to a known site - a kid
        # had the objective ("fuel at the ranger depot, marked") and
        # still couldn't find it on the ASCII map (playtest).
        return _compass(getattr(m, "sites", {}).get(role))

    item = m.requirement_item
    steps = []
    # 1. the route (skip for informational - the route is unknowable
    # until the response names it, so this step can only ever be the
    # hot line pointing nowhere)
    if not _info:
        _route_done = "route" in named or "F_ROUTE" in known
        # A kid did the whole fuel/generator chain but never found the
        # tunnel mouth - the hot line just said "found a way toward
        # another route" with no place, no direction (playtest). Point
        # a direction at it even before it's named.
        steps.append((_route_done,
                      f"found {place('route', 'a way toward another route')}",
                      f"head for {place('route', 'the way out')}{heading('route')}"))
    # 2. what blocks it
    if "F_OBSTACLE" in known or m.saw_obstacle:
        steps.append((True, "found what blocks the route"))

    # --- experimental family (dam_valves): no fetch, no dependency -
    # you have to work out which control it is by trying them.
    if m.controls:
        if "F_REQUIRE" in known:
            steps.append((True, f"found {place('require', 'the controls')}"))
        steps.append((m.obstacle_open,
                      "worked out which control clears the way",
                      "try the controls one at a time - pull each"))
        steps.append((m.obstacle_open, "opened the way through"))
        steps.append((m.escaped, f"escaped by {mech_name}"))
        out = [f"[b]ESCAPE — {mech_name}[/b]"]
        hyp = getattr(k, "hypothesis", None)
        hstate = k.hypothesis_state() if hyp else "unknown"
        if hyp and hstate in ("suspected", "confirmed"):
            tag = "you think" if hstate == "suspected" else "you know"
            out.append(f"  [{_DIM}]{tag}:[/] {hyp.statement}")
        hot = next((i for i, s in enumerate(steps) if not s[0]), None)
        for i, s in enumerate(steps):
            dn, label = s[0], s[1]
            todo = s[2] if len(s) > 2 else label
            if dn:
                out.append(f"  [green]✓[/green] {label}")
            elif i == hot:
                out.append(f"  [yellow]▸[/yellow] [yellow]{todo}[/]")
            else:
                out.append(f"  [{_DIM}]☐ {label}[/]")
        return out

    # --- transportation family (airfield_plane): the way out is a
    # machine that needs a checklist of parts, fetched in any order.
    req_items = getattr(m, "requirement_items", None) or []
    if len(req_items) > 1:
        held = {getattr(it, "name", None) for it in p.backpack.items}
        roles_for = {req_items[0]: "require"}
        for extra in req_items[1:]:
            roles_for[extra] = "require2"
        if "F_REQUIRE" in known:
            steps.append((True, "found out what the machine needs"))
        for it_name in req_items:
            r = roles_for.get(it_name, "require")
            got = (it_name in held) or m.obstacle_open
            steps.append((got, f"got the {it_name}",
                          f"go to {place(r, 'where it is kept')}{heading(r)} for the {it_name}"))
        steps.append((m.obstacle_open, "fitted the parts and started the engine",
                      f"bring the parts to {place('route', 'the machine')} and start it"))
        _can_leave = confirmed and m.obstacle_open
        steps.append((m.escaped, f"escaped by {mech_name}",
                      "type `escape` to leave" if _can_leave else f"escaped by {mech_name}"))
        out = [f"[b]ESCAPE — {mech_name}[/b]"]
        hyp = getattr(k, "hypothesis", None)
        hstate = k.hypothesis_state() if hyp else "unknown"
        if hyp and hstate in ("suspected", "confirmed"):
            tag = "you think" if hstate == "suspected" else "you know"
            out.append(f"  [{_DIM}]{tag}:[/] {hyp.statement}")
        hot = next((i for i, s in enumerate(steps) if not s[0]), None)
        for i, s in enumerate(steps):
            dn, label = s[0], s[1]
            todo = s[2] if len(s) > 2 else label
            if dn:
                out.append(f"  [green]✓[/green] {label}")
            elif i == hot:
                out.append(f"  [yellow]▸[/yellow] [yellow]{todo}[/]")
            else:
                out.append(f"  [{_DIM}]☐ {label}[/]")
        return out

    # --- time-pressure family (tidal_causeway): no fetch, no fix - a
    # window. The one live number is turns-to-the-tide.
    if _spec.get("deadline_turns"):
        dl = getattr(m, "deadline", None)
        recov = getattr(m, "tide_recovery", 0)
        crossed = getattr(m, "crossed", False)
        if crossed or m.escaped:
            cross_hot = "type `escape` to leave"
        elif recov > 0:
            cross_hot = f"wait it out - about {recov} turns to the next low tide"
        elif dl is not None:
            cross_hot = f"cross now - the tide turns in about {dl} turns"
        else:
            cross_hot = f"get to {place('route', 'the shore')}{heading('route')} and read the tide"
        steps.append((crossed or m.escaped, "crossed the causeway", cross_hot))
        steps.append((m.escaped, f"escaped by {mech_name}"))
        out = [f"[b]ESCAPE — {mech_name}[/b]"]
        hyp = getattr(k, "hypothesis", None)
        hstate = k.hypothesis_state() if hyp else "unknown"
        if hyp and hstate in ("suspected", "confirmed"):
            tag = "you think" if hstate == "suspected" else "you know"
            out.append(f"  [{_DIM}]{tag}:[/] {hyp.statement}")
        hot = next((i for i, s in enumerate(steps) if not s[0]), None)
        for i, s in enumerate(steps):
            dn, label = s[0], s[1]
            todo = s[2] if len(s) > 2 else label
            if dn:
                out.append(f"  [green]✓[/green] {label}")
            elif i == hot:
                out.append(f"  [yellow]▸[/yellow] [yellow]{todo}[/]")
            else:
                out.append(f"  [{_DIM}]☐ {label}[/]")
        return out

    # 2b. infrastructural / informational: the dependency
    if m.power_role and ("F_POWER" in known):
        steps.append((True,
                      f"learned the transmitter runs off {place('power', 'a generator somewhere')}"
                      if _info else
                      f"learned it's powered from {place('power', 'somewhere else')}"))
        _pl = labels.get('power', 'the power source')
        steps.append(("power" in named or m.power_restored,
                      f"reached {_pl}",
                      f"go to {_pl}{heading('power')}"))
    # 3. what you need
    if "F_REQUIRE" in known:
        steps.append((True, f"learned you need a {item}"
                            + (f" — kept at {labels['require']}" if 'require' in labels else "")))
    # 4. reached the place it's kept
    if "F_REQUIRE" in known:
        _rl = labels.get('require', 'where it is kept')
        steps.append(("require" in named or has_item,
                      f"reached {_rl}",
                      f"go to {_rl}{heading('require')}"))
    # 5. got it
    if "F_REQUIRE" in known or has_item:
        _rl = labels.get('require', 'where it is kept')
        steps.append((has_item, f"got the {item}",
                      f"go to {_rl}{heading('require')} and pick up the {item}"))
    # 5b. infrastructural / informational: apply the fix
    if m.power_role and ("F_REQUIRE" in known or has_item):
        _pl = labels.get('power', 'the power source')
        steps.append((m.power_restored,
                      "got the transmitter running" if _info
                      else f"restored power at {_pl}",
                      f"take the {item} to {_pl}{heading('power')}"))
    # 6. open the way / get the directions
    steps.append((m.obstacle_open,
                  "the outside named a way out" if _info else "opened the way through"))
    # 7. escape - once it's confirmed + open you can `escape` from
    # anywhere; a kid walked to the map marker and died one tile short
    # (playtest). Make the hot line an instruction, not a place.
    _can_leave = confirmed and m.obstacle_open
    steps.append((m.escaped, f"escaped by {mech_name}",
                  ("type `escape` now - you don't have to walk there" if _can_leave and _info
                   else "type `escape` to leave" if _can_leave
                   else f"escaped by {mech_name}")))

    out = [f"[b]ESCAPE — {mech_name}[/b]"]
    # highlight the first not-done step
    hot = next((i for i, s in enumerate(steps) if not s[0]), None)
    for i, s in enumerate(steps):
        dn, label = s[0], s[1]
        todo = s[2] if len(s) > 2 else label
        if dn:
            out.append(f"  [green]✓[/green] {label}")
        elif i == hot:
            star = confirmed and m.obstacle_open and "escaped" in label
            mark = "[b yellow]★[/]" if (star or "escaped" in label and confirmed) else "[yellow]▸[/]"
            out.append(f"  {mark} [yellow]{todo}[/]")
        else:
            out.append(f"  [{_DIM}]☐ {label}[/]")
    return out


def _status_block(p):
    """The bottom-right STATUS box: the OBJECTIVES checklist (external
    memory of the investigation, generated from the mystery) plus any
    active warnings (the standing version of the ⚠ events)."""
    lines = []

    k = getattr(p, "knowledge", None)
    m = getattr(p, "mystery", None)
    if m is not None and k is not None:
        lines += _objective_steps(p, m, k)

    warns = []
    w = p.equipped_weapon
    from src.items import RangedWeapon
    spare = [b for b in p.backpack.weapons if getattr(b, "durability", 1) > 0
             and not (isinstance(b, RangedWeapon) and b.ammo <= 0)]
    if w is None:
        warns.append("no weapon equipped")
    elif getattr(w, "durability", 1) <= 0:
        warns.append(f"{w.name} is broken" + (" — eq another" if spare else ""))
    elif isinstance(w, RangedWeapon) and w.ammo <= 0:
        warns.append(f"{w.name} out of ammo" + (" — eq a blade" if spare else ""))
    elif 0 < getattr(w, "durability", 99) <= 5:
        warns.append(f"{w.name} nearly worn out ({w.durability})")
    if m is not None:
        _recov = getattr(m, "tide_recovery", 0)
        _dl = getattr(m, "deadline", None)
        if not getattr(m, "crossed", False) and not getattr(m, "escaped", False):
            if _recov > 0:
                warns.append(f"causeway flooded — ~{_recov} to low tide")
            elif _dl is not None and _dl <= 10:
                warns.append(f"the tide turns in ~{_dl}")
    if 0 < p.health <= p.max_health * 0.2:
        warns.append("critically hurt")
    if p.hunger <= 0:
        warns.append("starving")
    if p.thirst <= 0:
        warns.append("parched")
    if warns:
        if lines:
            lines.append("")
        lines.append("[b][red]WARNINGS[/red][/b]")
        lines += [f"  [red]![/red] {x}" for x in warns]

    return "\n".join(lines)


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
        height: auto;
    }
    #map_scroll {
        overflow: auto auto;
        align: center middle;
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
        border-top: solid $accent;
        height: 3;
    }
    #stats_text {
        height: auto;
    }
    #commands_text {
        height: auto;
        border-top: solid $accent;
        padding-top: 1;
        color: $text-muted;
    }
    #status_block {
        height: auto;
        border-top: solid $accent;
        padding-top: 1;
    }
    """

    # Input model: the command box is ALWAYS focused. Type any command
    # (n/s/e/w, search, eq sword, 1, ...) and press Enter. The arrow
    # keys move directly without typing - priority=True so they fire
    # even though the Input has focus (Textual would otherwise let a
    # focused Input consume arrow keys for cursor movement). Arrows only
    # submit a move at the main "> " command prompt (see
    # _expecting_command below), not mid-dialog (a save-slot name, a
    # y/n prompt), where an arrow press should do nothing.
    BINDINGS = [
        Binding("up", "move_direction('n')", "Move north", priority=True),
        Binding("down", "move_direction('s')", "Move south", priority=True),
        Binding("left", "move_direction('w')", "Move west", priority=True),
        Binding("right", "move_direction('e')", "Move east", priority=True),
    ]

    def __init__(self, name=None, level=1, seed=None, hardcore=False, start_log=False):
        super().__init__()
        self._name = name
        self._level = level
        self._seed = seed
        self._hardcore = hardcore
        self._start_log = start_log
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
                        yield Static("", id="directions_text")
                        with ScrollableContainer(id="map_scroll"):
                            yield Static(id="map_panel")
                with Vertical(id="console"):
                    yield RichLog(id="log", max_lines=200)
                    yield Input(placeholder="command", id="command_input")
            with Vertical(id="stats_panel"):
                yield Static(id="stats_text")
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
                yield Static(id="status_block")
        yield Footer()

    def action_move_direction(self, direction):
        if self.io is not None and self._expecting_command:
            self.io.submit_answer(direction)

    # ---- input --------------------------------------------------------

    def _focus_command_box(self):
        try:
            self.query_one("#command_input", Input).focus()
        except Exception:
            pass

    def _refresh_location_line(self):
        try:
            w = self.query_one("#directions_text", Static)
        except Exception:
            return
        if self.player is None:
            return
        loc = _location_name(self.player)
        phase = getattr(self.player, "day_phase", "day")
        clk = f"{self.player.time_of_day // 60:02d}:{self.player.time_of_day % 60:02d}"
        tail = "arrows move · type a command + Enter · ? for help"
        w.update(f"[b]{loc}[/b]   [{_PHASE_COLOR.get(phase, _DIM)}]"
                 f"{_PHASE_GLYPH.get(phase, '·')} {phase.upper()} {clk}[/]\n[dim]{tail}[/dim]")

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

        if getattr(self, "_start_log", False):
            try:
                # main thread here - start_playlog() does file IO only and
                # never marshals; announce via log_message() directly.
                log_path = self.player.start_playlog()
                self.log_message(f"Play logging on -> {log_path}")
            except OSError as exc:
                self.log_message(f"Couldn't start the play log: {exc}")

        self.refresh_panels()
        self._focus_command_box()
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
        # The command box is always focused - the same box answers the
        # "> " prompt, a y/n, a save-slot name. Arrow-key movement is
        # gated on _expecting_command (action_move_direction).
        self._focus_command_box()
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
            body = Text.from_ansi(text)
            # Dim in-game timestamp on ordinary one-line narrative, so
            # the log reads as an event feed. Skip it for the boxed
            # ◆/⚠ emphasis blocks and anything multi-line.
            p = self.player
            if p is not None and "\n" not in text and text.lstrip()[:1] not in "═╭│╰◆⚠*[":
                hhmm = f"{p.time_of_day // 60:02d}:{p.time_of_day % 60:02d}"
                body = Text.assemble((f"{hhmm}  ", "dim"), body)
            self.query_one("#log", RichLog).write(body)
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
        self._refresh_location_line()

        map_widget = self.query_one("#map_panel", Static)
        map_widget.update(Text.from_ansi("\n".join(p._render_map_lines())))

        stats_widget = self.query_one("#stats_text", Static)
        phase = getattr(p, "day_phase", "night" if p.is_night else "day")
        glyph = _PHASE_GLYPH.get(phase, "·")
        pcol = _PHASE_COLOR.get(phase, _DIM)
        clock = f"{p.time_of_day // 60:02d}:{p.time_of_day % 60:02d}"

        w_cap = getattr(p.backpack, "MAX_WEAPONS", len(p.backpack.weapons))
        eq = p.equipped_weapon
        eq_line = _fmt_gear(eq) if eq else f"  [{_DIM}]bare hands[/]"
        if eq and getattr(eq, "durability", 1) <= 0:
            eq_line += "  [red]BROKEN[/]"

        def _sup(label, n):
            c = "red" if n <= 0 else "grey85"
            return f"[{_DIM}]{label}[/] [{c}]{n}[/]"

        _map_lvl = getattr(p, "expeditions_completed", 0) + 1
        lines = [
            f"[bold]{p.name}[/bold]   [{_DIM}]Level {p.level} · XP {p.xp}/{p.max_xp}[/]",
            f"[{pcol}]{glyph} {phase.upper()}[/]   [{_DIM}]Day {p.day} · {clock} · "
            f"Turn {getattr(p, 'turns', 0)}[/]",
            f"[{_DIM}]Map {_map_lvl} · {p.map_size}×{p.map_size}[/]",
            "",
            f"[{_HDR}]EQUIPMENT[/]",
            eq_line,
        ]
        worn = [_fmt_gear(pc).replace("  ", f"  [{_DIM}]{slot}[/] ", 1)
                for slot, pc in p.equipped_armor.items() if pc]
        lines += worn or [f"  [{_DIM}]no armor[/]"]
        lines += [
            "",
            f"[{_HDR}]BACKPACK[/]  [{_DIM}]{len(p.backpack.weapons)}/{w_cap}[/]",
        ]
        lines += _gear_lines(p.backpack.weapons) or [f"  [{_DIM}]empty[/]"]
        lines += _gear_lines(p.backpack.armor)
        lines += [
            "",
            "  ".join([
                _sup("food", p.backpack.food), _sup("water", p.backpack.water),
                _sup("med", p.backpack.medicine), _sup("ammo", p.backpack.ammo),
            ]),
        ]
        stats_widget.update("\n".join(lines))

        self.query_one("#health_bar", ProgressBar).update(progress=max(0, min(100, p.health)))
        self.query_one("#hunger_bar", ProgressBar).update(progress=max(0, min(100, p.hunger)))
        self.query_one("#thirst_bar", ProgressBar).update(progress=max(0, min(100, p.thirst)))
        self.query_one("#fatigue_bar", ProgressBar).update(progress=max(0, min(100, p.fatigue)))

        # (The objective lives only in the bottom-right OBJECTIVES
        # panel now - _status_block - not duplicated up here.)

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
            "[b]ACTIONS[/b]   (type `h` for the full command list)\n"
            + "  ·  ".join(p._action_bar())
        )

        self.query_one("#status_block", Static).update(_status_block(p))

    def on_input_submitted(self, event: Input.Submitted):
        text = event.value
        event.input.value = ""
        # A bare Enter at the "> " prompt is a no-op, not "Unknown
        # command: ''". Mid-dialog an empty answer still goes through
        # (some prompts treat it as a default / "close").
        if self._expecting_command and not text.strip():
            self._focus_command_box()
            return
        if self.io is not None:
            self.io.submit_answer(text)
        self._focus_command_box()
