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
import threading

from rich.markup import escape as _rich_escape
from rich.text import Text

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.widgets import (Header, Footer, Static, Input, RichLog,
                             ProgressBar, Button, Label, RadioSet, RadioButton)

from src.game import Apocrysis
from src.worlds import get_world, world_ids
from src.constants import stat_band, CAMPAIGN_LENGTH
from src.campaign import chapter_for_expedition, CHAPTER_TITLES
from src.mixins.persistence_mixin import profile_filename_for_name, campaign_filename
from src.nav import honest_bearing


class AppClosed(Exception):
    """Raised out of TextualIO.ask()/ask_yes_no() when the app is
    shutting down while the game thread is still waiting on an
    answer - see TextualIO._wait_for_answer()'s docstring."""


class GameClosed(Exception):
    """G2 (Phase G): raised out of the same blocking TextualIO prompt
    paths as AppClosed - but it means *only this game session* is
    being torn down. The Textual application stays alive. Distinct
    class, distinct handling: the _game_thread's AppClosed path calls
    app.exit(); its GameClosed path does not. See
    GameScreen.close_game()."""


class TextualIO:

    # Tells ui_mixin.py's run_game_loop() to skip its own classic
    # two-column ASCII block (io_console.py's ConsoleIO has the same
    # attribute, False) - this TUI's own widgets render the map/stats/
    # commands instead, via refresh_panels() below.
    renders_natively = True

    def __init__(self, host):
        # G1: `host` is the GameScreen that owns the log/input widgets
        # (was the App itself pre-extraction). call_from_thread /
        # is_running still live on the App - reached via host.app.
        self.host = host
        self.app = getattr(host, "app", host)
        self._answers = queue.Queue()

    def say(self, *args, **kwargs):
        text = " ".join(str(a) for a in args)
        self.app.call_from_thread(self.host.log_message, text)

    def ask(self, prompt=""):
        self._drain_stale_answers()
        self.app.call_from_thread(self.host.request_input, prompt)
        return self._wait_for_answer()

    def ask_yes_no(self, prompt):
        self._drain_stale_answers()
        self.app.call_from_thread(self.host.request_input, f"{prompt} (y/n)")
        while True:
            answer = self._wait_for_answer().strip().lower()
            if answer in ("y", "yes"):
                return True
            if answer in ("n", "no"):
                return False
            self.app.call_from_thread(self.host.log_message, "Please answer y or n.")
            self._drain_stale_answers()
            self.app.call_from_thread(self.host.request_input, f"{prompt} (y/n)")

    def ask_combat_letter(self):
        """Encounter card (combat_mixin._encounter_card): 'f' / 'e' / 'w'."""
        self._drain_stale_answers()
        self.app.call_from_thread(self.host.request_input,
                                  "[f] fight  [e] escape  [w] weapons")
        while True:
            a = self._wait_for_answer().strip().lower()
            if a in ("f", "fight", "y", "yes"):
                return "f"
            if a in ("e", "escape", "flee", "n", "no"):
                return "e"
            if a in ("w", "weapon", "weapons"):
                return "w"
            self.app.call_from_thread(self.host.log_message, "Type f, e, or w.")
            self._drain_stale_answers()
            self.app.call_from_thread(self.host.request_input,
                                      "[f] fight  [e] escape  [w] weapons")

    def ask_commit(self, prompt, default="cancel"):
        """P1 commitment gate (mixins/intervention_mixin.py). A bare Enter
        (empty submit - passes through mid-dialog, tui.py on_input_
        submitted) resolves to `default`; explicit y / n override it.
        `_expecting_command` is False for this non-'> ' prompt, so arrow
        keys inject nothing while it's up."""
        self._drain_stale_answers()
        self.app.call_from_thread(self.host.request_input, prompt)
        while True:
            a = self._wait_for_answer().strip().lower()
            if a == "":
                return default if default in ("proceed", "cancel") else "cancel"
            if a in ("y", "yes"):
                return "proceed"
            if a in ("n", "no"):
                return "cancel"
            self.app.call_from_thread(self.host.log_message, "Press y, n, or Enter.")
            self._drain_stale_answers()
            self.app.call_from_thread(self.host.request_input, prompt)

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
            # G2: same poll, second exit condition. The app is fine;
            # this game session has been deliberately ended (the
            # GameScreen set host._session_closing). Checked AFTER
            # is_running so a real app shutdown still reads as
            # AppClosed, never GameClosed.
            if getattr(self.host, "_session_closing", None) is not None \
                    and self.host._session_closing.is_set():
                raise GameClosed()
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


def _fmt_gear(item, equipped=False):
    """One coloured line for a weapon or armor piece. `equipped` gates
    the alert colours: an empty magazine is a problem for the weapon in
    your hand, not for a spare sitting in the pack (a `reload` away)."""
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
        c = "red" if (not ammo and equipped) else _DIM
        parts.append(f"[{c}]ammo {ammo}/{mx_ammo}[/]")
    dur = getattr(item, "durability", None)
    mxd = getattr(item, "max_durability", dur)
    c = _dur_color(dur, mxd)
    if c:
        parts.append(f"[{c}]{dur}/{mxd}[/]")
    return "  " + "  ".join(parts)


def _gear_lines(items, slot_tag=""):
    """Grouped, coloured lines - a contiguous run of identical items
    collapses to 'xK'. Each line is prefixed with the 1-based slot
    number(s) it covers ([3] / [3-5]), so `eq 3` / `wr W2` matches
    what's shown. Runs must be contiguous or the numbers would lie."""
    items = list(items)
    out = []
    i = 0
    while i < len(items):
        key = str(items[i])
        j = i
        while j < len(items) and str(items[j]) == key:
            j += 1
        n = j - i
        tag = f"{slot_tag}{i + 1}" if n == 1 else f"{slot_tag}{i + 1}-{slot_tag}{j}"
        line = f"  [{_DIM}][{tag}][/]" + _fmt_gear(items[i])
        if n > 1:
            line += f"  [{_DIM}]x{n}[/]"
        out.append(line)
        i = j
    return out


def _location_name(p):
    """A short name for where the player is standing - the mystery
    site label if they're on a named site, otherwise terrain-derived."""
    fallback = p.world.prose.get("place_name_fallback", "THE VALLEY")
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
        return names.get(t, fallback)
    return fallback


_FACT_LABEL = {
    "F_CLOSED": "the usual way out is shut",
    "F_ROUTE": "there's another route",
    "F_OBSTACLE": "that route is blocked",
    "F_REQUIRE": "know what unblocks it",
}


# A/B switch for the navigation investigation (docs/AUTOPLAY_STRATEGY.md,
# docs/DESIGN_SPATIAL_LANGUAGE.md). "landmark" = the approach ladder
# (marker-in-sight -> close-now -> marked-on-map -> bearing). "cardinal"
# = the pre-redesign bare bearing, for the A arm of the A/B. Default
# landmark; the harness sets it.
_SPATIAL_MODE = "landmark"


def _route_heading(here, dest, grid, n):
    """C.3.2 piece 0 — the graph-honest compass suffix (" (north-east)")
    for a checklist "head for …" line. `nav.honest_bearing` does the
    work (straight-line claim vs the real early route); this just wraps
    it. "" dest → ""; no committed direction → " (near here)".
    """
    if not dest:
        return ""
    d = honest_bearing(here, dest, grid, n)
    return f" ({d})" if d else " (near here)"


def _objective_steps(p, m, k):
    """The OBJECTIVES checklist, generated from THIS mystery's own
    structure (site labels, mechanism, requirement item) rather than a
    generic list. It's the player's external memory - "what did I do
    80 turns ago" - so every line is phrased from what the player has
    actually learned, not the hidden Escape Proof. The one actionable
    step is highlighted; the journal keeps the detail."""
    try:
        from src.escape import MECHANISMS
        _spec = MECHANISMS.get(m.mechanism, {})   # grammar only (reveals_route)
        mech_name = getattr(m, "mech_name", None) or "the way out"
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

    def heading(role):
        # docs/DESIGN_SPATIAL_LANGUAGE.md - the approach ladder: an
        # on-screen marker beats a proximity cue beats a bare bearing
        # (runs 1-5: "south-west" alone is inert; run 6: named place +
        # "marked on your map" + "close by" worked). The bearing stays
        # as trailing seasoning, graph-honest via _route_heading.
        xy = getattr(m, "sites", {}).get(role)
        if not xy:
            return ""
        bearing = _route_heading(p.current_position, xy, p.map, p.map_size)
        if _SPATIAL_MODE == "cardinal":
            return bearing            # bare bearing only (the A arm)
        hx, hy = p.current_position
        dist = abs(xy[0] - hx) + abs(xy[1] - hy)
        vr = getattr(p, "visibility_radius", 3)
        if dist <= vr:
            return " - the marker's in sight"
        if dist <= vr + 4:
            return f" - close now{bearing}"
        return f" - marked on your map{bearing}"

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
                      "go to the way out to leave — or type `escape` from here"
                      if _can_leave else f"escaped by {mech_name}"))
        out = [f"[b]ESCAPE — {mech_name}[/b]"]
        # 1d Finding G: multi-part requirement reads as a set, not N
        # independent ✓ lines.
        _have_n = sum(1 for it in req_items if it in held or m.obstacle_open)
        if _have_n < len(req_items):
            out.append(f"  [{_DIM}]parts[/] [yellow]{_have_n} / {len(req_items)}[/]")
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
            cross_hot = "walk off the far side to leave — or type `escape`"
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
    # 7. escape - reaching the marked way out (cleared + confirmed)
    # leaves automatically; you can also `escape` from anywhere once
    # it's confirmed + open (a kid walked to the marker and died one
    # tile short - playtest).
    _can_leave = confirmed and m.obstacle_open
    steps.append((m.escaped, f"escaped by {mech_name}",
                  ("the voice has you - type `escape` now, no need to walk there"
                   if _can_leave and _info
                   else "go to the way out to leave — or type `escape` from here"
                   if _can_leave
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


def _investigation_strip(p):
    """A.5.1 / audit 1a: a compact, always-visible read of the World
    Investigation, built so the player can answer four questions -
    what do I know, what am I missing, what should I do next, can this
    expedition make progress. Thread titles + fact *leads*, never ids.
    Empty when the world carries no facts (bare test worlds)."""
    wi = getattr(p, "world_investigation", None)
    if wi is None or not wi.all_facts():
        return []
    titles = p.world.prose.get("thread_titles", {})
    ms = len(wi.milestones_known())
    sk = getattr(p, "survivor_knowledge", None)
    lore_n = len(sk.learned_ids()) if sk else 0
    head = f"[b]THE APOCRYSIS[/b]   [yellow]◆ {ms}[/yellow]"
    if lore_n:
        head += f"   [cyan]● {lore_n}[/cyan]"
    out = [head]

    # which thread THIS expedition advances, and the exact fact it can
    # establish. The mystery is bound to one WorldFact (generate_map
    # targets wi.next_target()); that fact's thread is the live one.
    _m = getattr(p, "mystery", None)
    _fid = getattr(_m, "world_fact_id", None) if _m is not None else None
    _run_fact = wi.fact(_fid) if (_fid and hasattr(wi, "fact")) else None
    _active_thread = getattr(_run_fact, "thread", None)

    for thread, (known, total) in wi.thread_progress().items():
        title = titles.get(thread, (thread.upper(), ""))[0]
        n = 4
        filled = 0 if not total else round(n * known / total)
        bar = "█" * filled + "░" * (n - filled)
        mark = "[yellow]▸[/yellow] " if thread == _active_thread else "  "
        out.append(f"{mark}{title}   {bar}  {known}/{total}")

    if _active_thread:
        facts = [f for f in wi.all_facts() if f.thread == _active_thread]
        q = titles.get(_active_thread, ("", ""))[1]
        if q:
            out.append(f"  [{_DIM}]{q}[/]")
        # WHAT I KNOW - the last few established leads on this thread
        known_leads = [f.lead or f.id for f in facts if wi.is_known(f.id)]
        if len(known_leads) > 3:
            out.append(f"  [green]✓[/green] [{_DIM}]+{len(known_leads) - 3} "
                       f"earlier[/]")
        for lead in known_leads[-3:]:
            out.append(f"  [green]✓[/green] [{_DIM}]{lead}[/]")
        # WHAT'S NEXT + CAN THIS RUN ADVANCE IT - the fact this
        # expedition is bound to, if it's still open; else the next
        # eligible lead on the thread.
        eligible = {f.id for f in wi.eligible()}
        if _run_fact is not None and not wi.is_known(_run_fact.id):
            out.append(f"  [yellow]▸ this run:[/] [yellow]"
                       f"{_run_fact.lead or _run_fact.id}[/]")
        else:
            nxt = next((f for f in facts
                        if f.id in eligible and not wi.is_known(f.id)), None)
            if nxt is not None:
                out.append(f"  [yellow]○ next:[/] {nxt.lead or nxt.id}")

    # the working theory, one line, wrapped short.
    _hyp = wi.current_hypothesis() if hasattr(wi, "current_hypothesis") else None
    if _hyp is not None:
        _t = _hyp.statement
        if len(_t) > 46:
            _t = _t[:45].rsplit(" ", 1)[0] + "…"
        out.append(f"  [{_DIM}]you think:[/] {_t}")
    return out


def _status_block(p, compact=False):
    """The bottom-right STATUS box: a compact World Investigation strip
    (A.5.1), the OBJECTIVES checklist (external memory of the current
    mystery), plus any active warnings. `compact` (G6 HUD density
    setting) collapses the WARNINGS list to a single line."""
    lines = []

    strip = _investigation_strip(p)
    if strip:
        lines += strip + [""]

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
        if compact:
            lines.append("[red]![/red] " + "  ·  ".join(warns))
        else:
            lines.append("[b][red]WARNINGS[/red][/b]")
            lines += [f"  [red]![/red] {x}" for x in warns]

    return "\n".join(lines)


class GameScreen(Screen):

    # G1 (Phase G): the entire game body - CSS, layout, worker thread,
    # TextualIO bridge, panel rendering, input handling - extracted
    # VERBATIM from what used to be ApocrysisApp into a Textual Screen.
    # Nothing about the game loop changed; only `self` is now a Screen,
    # so App-level calls (call_from_thread / exit / is_running) go via
    # self.app. ApocrysisApp (bottom of file) is now a thin shell that
    # pushes this screen on mount.
    #
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

    def __init__(self, *, game_name=None, level=1, seed=None, hardcore=False,
                 start_log=False, dev=None, world=None, settings=None):
        # Keyword-only game params: Screen.__init__ already claims the
        # positional `name` (a DOM id concept), so the survivor name
        # comes in as `game_name` and is stashed as self._name exactly
        # as before.
        super().__init__()
        self._name = game_name
        self._level = level
        self._seed = seed
        self._hardcore = hardcore
        # G3.2: the world id for a NEW campaign. Ignored when a profile
        # is loaded - apply_profile() re-points self.world from the
        # profile's own world_id.
        self._world = world
        # G6: player-global preferences (§8). A dict from src.settings;
        # falls back to the defaults so a directly-constructed
        # GameScreen (tests) still has every key.
        from src import settings as _settings_mod
        self._settings = dict(settings) if settings else _settings_mod.load()
        self._start_log = start_log
        # --dev: story-inspection harness (src/dev.py). Sandboxed.
        self._dev = dev
        if dev is not None:
            self._seed = dev.seed
        # One transcript file for the whole session - each expedition
        # after the first appends to it (see _game_thread's post-win
        # loop) rather than opening a new timestamped file.
        self._log_path = None
        self.player = None
        self.io = None
        self._expecting_command = False
        # Set by _new_player() each time it's called, so on_mount()
        # (main thread) and _game_thread() (worker thread) can each
        # emit the "Welcome back" greeting through the right channel
        # for their own thread - see _new_player()'s docstring.
        self._last_load_was_profile = False
        # G2: session-lifetime (not app-lifetime) machinery.
        # close_game() sets the event; TextualIO._wait_for_answer()
        # polls it and raises GameClosed to release a blocked worker.
        # _game_worker is the run_worker() handle so close_game() can
        # await its real termination rather than just abandon it.
        self._session_closing = threading.Event()
        self._game_worker = None

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
        p = self.player
        loc = _location_name(p)
        phase = getattr(p, "day_phase", "day")
        clk = f"{p.time_of_day // 60:02d}:{p.time_of_day % 60:02d}"
        # 1d HUD: the zone, plus a plain note when this ground is slow
        # to cross (so "why is travel dragging" has an answer on screen).
        _z = p._current_zone() if hasattr(p, "_current_zone") else ""
        _cell = p.map[p.current_position[1]][p.current_position[0]]
        _terr = _cell.get("terrain") if isinstance(_cell, dict) else None
        _slow = {"water": "slow going", "swamp": "slow, tiring ground",
                 "forest": "slower under cover"}.get(_terr, "")
        _help = "arrows move · type a command + Enter · ? for help"
        _sub = "  ·  ".join(x for x in (_z, _slow) if x)
        tail = f"{_sub}   —   {_help}" if _sub else _help
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
        if self._dev is not None:
            # --dev: synthetic coherent state at a chosen chapter, then
            # the normal game. Sandboxed - never reads a real profile.
            from src.dev import synthetic_state, dev_profile_path
            from src.mixins.persistence_mixin import _profile_flat
            _saved = Apocrysis.load_profile(dev_profile_path())  # only after a dev death
            if _saved is not None:
                _f = _profile_flat(_saved)
                Apocrysis._world_investigation = dict(_f.get("world_investigation", {}) or {})
                depth = _f.get("expeditions_completed", 0)
            else:
                depth, _wi = synthetic_state(self._dev)
                Apocrysis._world_investigation = dict(_wi)
            Apocrysis._survivor_knowledge = list(
                getattr(Apocrysis, "_survivor_knowledge", []) or [])
            self._last_load_was_profile = False
            _p = Apocrysis("Dev", level=1, seed=self._dev.seed,
                           hardcore=False, expeditions_completed=depth,
                           io=self.io)
            from src.dev import equip_for_depth
            equip_for_depth(_p, depth)
            _p._return_to_menu_hook = self._worker_return_to_menu
            _p._settings = self._settings
            return _p

        profile = (Apocrysis.load_campaign(self._world, self._name)
                   if self._name else None)
        self._last_load_was_profile = profile is not None
        if profile is not None:
            from src.mixins.persistence_mixin import _profile_flat
            flat = _profile_flat(profile)
            # A.5/B: seed the campaign class-vars before construction
            # (generate_map targets next_target() in __init__, before
            # apply_profile).
            Apocrysis._world_investigation = dict(
                flat.get("world_investigation", {}) or {})
            Apocrysis._survivor_knowledge = list(
                flat.get("survivor_knowledge", []) or [])
            player = Apocrysis(
                flat.get("name", self._name or "Survivor"),
                level=flat.get("level", 1),
                hardcore=flat.get("hardcore", self._hardcore),
                expeditions_completed=flat.get("expeditions_completed", 0),
                # G5: build with the profile's own world so __init__
                # constructs the investigation off THAT world's fact
                # DAG - apply_profile's re-point then becomes a no-op.
                world=flat.get("world_id"),
                io=self.io,
            )
            player.apply_profile(profile)
        else:
            player = Apocrysis(
                self._name or "Survivor",
                level=self._level,
                seed=self._seed,
                hardcore=self._hardcore,
                world=self._world,
                io=self.io,
            )
        # G3: the in-game `menu` command calls this hook (ui_mixin's
        # _request_return_to_menu). Set on every player this screen
        # builds - the first one and each post-win successor.
        player._return_to_menu_hook = self._worker_return_to_menu
        # G6: the combat card's full/terse choice (combat_mixin reads
        # player._settings; absent -> full, so bots are unaffected).
        player._settings = self._settings
        return player

    def _save_or_delete_profile(self):
        p = self.player
        if self._dev is not None:
            from src.dev import dev_profile_path
            _dev_profile = dev_profile_path()
            if p.health <= 0:
                Apocrysis._survivors_lost = int(getattr(Apocrysis, "_survivors_lost", 0)) + 1
                Apocrysis.persist_new_survivor(_dev_profile, "Dev", False,
                                               p.expeditions_completed)
            else:
                p.save_profile(_dev_profile)
            return
        campaign_file = campaign_filename(
            getattr(p.world, "id", None), self._name or p.name)
        if p.health <= 0:
            if p.hardcore:
                p.delete_profile()
                return
            # Phase B: the survivor died. Keep the campaign, hand it to
            # a fresh survivor (next launch picks them up).
            Apocrysis._survivors_lost = int(
                getattr(Apocrysis, "_survivors_lost", 0)) + 1
            from src.cli import _next_survivor_name
            Apocrysis.persist_new_survivor(
                campaign_file, _next_survivor_name(Apocrysis._survivors_lost),
                p.hardcore, p.expeditions_completed)
            return
        p.save_profile(campaign_file)

    def _prime_campaign_state(self):
        """G5 reset-then-restore (§7). This GameScreen is ONE campaign
        session. The campaign class-vars may still hold a *previous*
        campaign played in this same process (Menu -> A -> Menu -> B).
        Wipe them, and if we're resuming a saved campaign restore them
        from its profile - all BEFORE _new_player() constructs the
        Apocrysis, whose __init__ reads _world_investigation and the
        mechanism shuffle-bag while building the first map.

        Only fires here, on screen construction - NOT on the between-
        expedition _new_player() calls in _game_thread, where a
        mid-campaign wipe (Hardcore especially, which has no file to
        restore from) would lose the campaign's progress."""
        if self._dev is not None:
            return   # the dev harness seeds its own synthetic state
        flat = {}
        if self._name:
            from src.mixins.persistence_mixin import _profile_flat
            _prof = Apocrysis.load_campaign(self._world, self._name)
            if _prof is not None:
                flat = _profile_flat(_prof)
        Apocrysis.reset_campaign_state(restore_from=flat)

    def on_mount(self):
        self.io = TextualIO(self)
        self._prime_campaign_state()
        self.player = self._new_player()
        # G6: the "play log" preference is an OR with the --no-log CLI
        # flag / --dev's start_log - either turns the transcript on.
        if self._settings.get("play_log"):
            self._start_log = True
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
                self._log_path = log_path
                self.log_message(f"Play logging on -> {log_path}")
            except OSError as exc:
                self.log_message(f"Couldn't start the play log: {exc}")

        self.refresh_panels()
        self._focus_command_box()
        self._game_worker = self.run_worker(self._game_thread, thread=True)

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
                except GameClosed:
                    # G2/G3: this game session was deliberately ended -
                    # either close_game() (UI thread set the event) or
                    # the in-game `menu` command (_worker_return_to_menu
                    # set it then raised, right here on the worker).
                    # Persist per the session-end rule (Normal -> save
                    # once; Hardcore + alive -> nothing, campaign gone;
                    # Hardcore + dead -> delete), tidy this session's
                    # playlog, hand the UI thread the teardown (drain
                    # queue, pop GameScreen -> whatever's beneath, which
                    # in the real app is MenuScreen), and return - the
                    # app stays alive, so no app.exit() below.
                    self._persist_on_session_end()
                    self._end_session_playlog()
                    self.app.call_from_thread(self._finish_session_teardown)
                    return
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

                # run_game_loop() closes the previous expedition's
                # playlog on win; reopen the SAME file for the next one
                # so a session is one transcript, not one-per-expedition.
                # Skip if the player turned logging off with `log`.
                if self._log_path is not None:
                    try:
                        self.player.start_playlog(path=self._log_path)
                    except OSError as exc:
                        self.app.call_from_thread(
                            self.log_message,
                            f"Couldn't reopen the play log: {exc}")

                if self._last_load_was_profile:
                    # Worker thread here - self.io.say() is the
                    # correct channel, its call_from_thread() call is
                    # only valid off the app's own thread.
                    self.player.io.say(
                        f"Welcome back, {self.player.name} - level {self.player.level}."
                    )
                self.app.call_from_thread(self.refresh_panels)
        except GameClosed:
            # Belt-and-suspenders: GameClosed raised somewhere other
            # than inside run_game_loop() (e.g. between iterations).
            # The inner handler already returned in the common case;
            # here just persist once, hand off the teardown, and stop.
            self._persist_on_session_end()
            self._end_session_playlog()
            self.app.call_from_thread(self._finish_session_teardown)
            return
        except AppClosed:
            # App is already shutting down for some other reason -
            # nothing left to do here, and calling self.exit() again
            # below would be redundant (still safe, guarded by
            # is_running).
            pass

        if self.app.is_running:
            self.app.call_from_thread(self.app.exit)

    def _persist_on_session_end(self):
        """G2 session-end persistence rule (distinct from the app-
        teardown _save_or_delete_profile, which always saves a living
        character). GameClosed acceptance #4/#5:
          Normal, alive        -> save (exactly once)
          Normal, dead         -> hand the campaign to an heir
          Hardcore, alive      -> WRITE NOTHING (walked away = gone)
          Hardcore, dead       -> delete
        Everything except the hardcore-alive case is exactly what
        _save_or_delete_profile already does."""
        p = self.player
        if getattr(p, "hardcore", False) and p.health > 0:
            return
        self._save_or_delete_profile()

    def _end_session_playlog(self):
        """G2: on a GameClosed teardown the loop's own end-of-session
        playlog close (ui_mixin.run_game_loop, bottom) is skipped by
        the exception. Close it here so the transcript is flushed and
        the TeeIO wrapper is unwound - #8 (session-local machinery
        left clean). Worker thread; no announcement."""
        p = self.player
        pl = getattr(p, "playlog", None)
        if pl is None:
            return
        try:
            from src.playlog import TeeIO
            pl.close("game session ended")
            p.playlog = None
            if isinstance(p.io, TeeIO):
                p.io = p.io._inner
            if isinstance(self.io, TeeIO):
                self.io = self.io._inner
        except Exception:
            pass
        self._log_path = None

    def _finish_session_teardown(self):
        """UI thread. The worker calls this (via call_from_thread) once
        it has stopped and persisted. Scrubs session-local state so
        nothing leaks into the next session, then replaces this
        GameScreen with a fresh MenuScreen (switch_screen, not pop - a
        1:1 swap, no reliance on what was underneath)."""
        if self.io is not None:
            self.io._drain_stale_answers()
        self._expecting_command = False
        self._session_closing.clear()
        self._game_worker = None
        # MenuScreen sits under every GameScreen (ApocrysisApp.on_mount),
        # so popping this screen reveals it. Guard the base screen.
        if self.app.is_running and self in self.app.screen_stack \
                and self is not self.app.screen_stack[0]:
            self.app.pop_screen()

    async def close_game(self):
        """G2 lifecycle primitive: end THIS game session, leave the
        Textual application running. G3 wires a route to it (the
        in-game `menu` command -> _worker_return_to_menu, which reaches
        the same GameClosed path from the worker side). G5 owns the
        class-var reset contract.

        Signal the worker, wait for it to ACTUALLY terminate (not just
        abandon it); the worker persists exactly once and runs
        _finish_session_teardown itself before returning."""
        self._session_closing.set()
        w = self._game_worker
        if w is not None:
            try:
                await w.wait()
            except Exception:
                # WorkerFailed / already-finished - the worker is done
                # either way, which is all we need.
                pass
        # Normally the worker already tore down via call_from_thread.
        # If it somehow never reached the handler, finish here.
        if self._game_worker is not None or self._session_closing.is_set():
            self._finish_session_teardown()

    def _worker_return_to_menu(self):
        """Worker thread - the in-game `menu` command, installed as
        player._return_to_menu_hook. Hardcore first gets the abandon
        confirm (default = stay); on 'stay' this is a true no-op, the
        session is never signalled. Otherwise signal the session to end
        and raise GameClosed to unwind run_game_loop() - _game_thread's
        handler persists per the session-end rule and _finish_session_
        teardown pops back to the menu."""
        p = self.player
        if getattr(p, "hardcore", False):
            ask = getattr(p.io, "ask_commit", None)
            res = ask(
                "HARDCORE CAMPAIGN - leaving now abandons this campaign. "
                "There is no save to resume later. Leave anyway?  "
                "[y] leave  /  [Enter] stay",
                default="cancel") if ask else "proceed"
            if res != "proceed":
                p.io.say("Still here.")
                return
        self._session_closing.set()
        raise GameClosed()

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
        eq_line = _fmt_gear(eq, equipped=True) if eq else f"  [{_DIM}]bare hands[/]"
        if eq and getattr(eq, "durability", 1) <= 0:
            eq_line += "  [red]BROKEN[/]"
        # 1d HUD: an empty magazine in your hand is tactical information,
        # not a footnote. Loud when empty + you have spare rounds.
        _mx_ammo = getattr(eq, "max_ammo", 0) if eq else 0
        if _mx_ammo:
            _a = getattr(eq, "ammo", 0)
            if _a == 0 and p.backpack.ammo > 0:
                eq_line += "  [b red]⚠ RELOAD[/]"
            elif _a == 0:
                eq_line += "  [b red]⚠ EMPTY - NO AMMO[/]"
            elif _a <= 2 and p.backpack.ammo > 0:
                eq_line += "  [#ff8c00]low - reload[/]"

        _BAND_MARKUP = {"normal": "grey85", "watch": "#c8c84a",
                        "warning": "#ff8c00", "danger": "red"}

        def _sup(label, n, kind=None):
            band = stat_band(kind, n) if kind else ("danger" if n <= 0 else "normal")
            return f"[{_DIM}]{label}[/] [{_BAND_MARKUP[band]}]{n}[/]"

        _exp_n = getattr(p, "expeditions_completed", 0) + 1
        _world = getattr(p, "world", None)
        _manifest = getattr(_world, "manifest", None)
        _campaign_length = _manifest.campaign_length if _manifest else CAMPAIGN_LENGTH
        _ch_titles = _manifest.chapter_titles if _manifest else CHAPTER_TITLES
        _ch = chapter_for_expedition(getattr(p, "expeditions_completed", 0), _world)
        _ch_title = _ch_titles[_ch - 1] if 1 <= _ch <= len(_ch_titles) else ""
        _mode = "[b red]HARDCORE[/]" if getattr(p, "hardcore", False) else f"[{_DIM}]NORMAL[/]"
        _saved = ("[#ff8c00]● UNSAVED[/]" if getattr(p, "_unsaved", False)
                  else "[#4a9d4a]● SAVED[/]")
        _mi = getattr(p, "_distance_walked", 0.0)
        _vis_note = ""
        if phase in ("dusk", "night") and not getattr(p, "has_flashlight", False):
            _vis_note = f"  [{_DIM}]· sight reduced[/]"

        lines = [
            f"[bold]{_rich_escape(p.name)}[/bold]   {_mode}   {_saved}",
            f"[{_DIM}]Level {p.level} · XP {p.xp}/{p.max_xp}[/]",
            f"[{_HDR}]EXPEDITION {_exp_n} / {_campaign_length}[/]"
            + (f"   [{_DIM}]CH{_ch} — {_ch_title}[/]" if _ch_title else ""),
            f"[{pcol}]{glyph} {phase.upper()}[/]   [{_DIM}]Day {p.day} · {clock} · "
            f"Turn {getattr(p, 'turns', 0)}[/]{_vis_note}",
            f"[{_DIM}]Map {_exp_n} · {p.map_size}×{p.map_size}"
            + (f" · walked {_mi:.1f} mi" if _mi else "") + "[/]",
        ]

        # 1d HUD: the immediate actionable objective, impossible to
        # miss. HUD = what to do; the investigation strip below = why.
        # Finding F — the block flips to ✦ ESCAPE READY once the
        # discover/collect phase is done and only the walk-out remains.
        _next = None
        _ready = False
        if getattr(p, "mystery", None) is not None and hasattr(p, "_objective_next_step"):
            try:
                _next = p._objective_next_step()
                _ready = p._objective_ready_to_leave()
            except Exception:
                _next = None
        if _next and _ready:
            lines += ["", "[b #4a9d4a]✦ ESCAPE READY[/]", f"  [#4a9d4a]{_next}[/]"]
        elif _next:
            lines += ["", "[b #d8b84a]▸ THIS RUN[/]", f"  [#d8b84a]{_next}[/]"]

        lines += ["", f"[{_HDR}]EQUIPMENT[/]", eq_line]
        worn = [_fmt_gear(pc, equipped=True).replace("  ", f"  [{_DIM}]{slot}[/] ", 1)
                for slot, pc in p.equipped_armor.items() if pc]
        lines += worn or [f"  [{_DIM}]no armor[/]"]
        _armor_total = sum(getattr(a, "damage_reduction", 0)
                           for a in p.equipped_armor.values()
                           if a and getattr(a, "durability", 1) > 0)
        if _armor_total:
            lines.append(f"  [{_DIM}]protection[/] [cyan]{_armor_total}[/]")
        _pack_n = len(p.backpack.weapons)
        _pack_c = ("b #ff8c00" if _pack_n >= w_cap
                   else "#ff8c00" if _pack_n >= w_cap - 1 else _DIM)
        lines += [
            "",
            f"[{_HDR}]BACKPACK[/]  [{_pack_c}]{_pack_n}/{w_cap} weapons"
            + ("  FULL" if _pack_n >= w_cap else "") + "[/]",
        ]
        lines += _gear_lines(p.backpack.weapons) or [f"  [{_DIM}]empty[/]"]
        lines += _gear_lines(p.backpack.armor, slot_tag="W")
        lines += [
            "",
            "  ".join([
                _sup("food", p.backpack.food, "food"),
                _sup("water", p.backpack.water, "water"),
                _sup("med", p.backpack.medicine), _sup("ammo", p.backpack.ammo),
            ]),
        ]

        # 1d HUD: a CONDITIONS block, only when something is actually
        # wrong. Never a permanent row of labels.
        _cond = []
        for _fx in getattr(p, "status_effects", {}):
            _cond.append(str(_fx).upper())
        if stat_band("hp", p.health, p.max_health) == "danger":
            _cond.append("BADLY HURT")
        elif stat_band("hp", p.health, p.max_health) == "warning":
            _cond.append("WOUNDED")
        if p.fatigue > 85:
            _cond.append("EXHAUSTED")
        if p.hunger <= 0 or p.thirst <= 0:
            _cond.append("STARVING")
        _compact = self._settings.get("hud_density") == "compact"
        if _cond:
            _joined = " · ".join(f"[#ff8c00]{c}[/]" for c in _cond)
            if _compact:
                lines += [f"[b red]![/] {_joined}"]
            else:
                lines += ["", f"[b red]CONDITIONS[/]  " + _joined]

        stats_widget.update("\n".join(lines))

        # ATTENTION_SYSTEM_SPEC.md: the vitals bars shade with the
        # deterioration ladder - grey / orange / red.
        _BAND_RGB = {"normal": "grey", "watch": "#c8c84a",
                     "warning": "#ff8c00", "danger": "#e04040"}
        for _id, _kind, _val, _max in (
            ("health_bar", "hp", p.health, p.max_health),
            ("hunger_bar", "hunger", p.hunger, 100),
            ("thirst_bar", "thirst", p.thirst, 100),
            ("fatigue_bar", "fatigue", p.fatigue, 100),
        ):
            _bar = self.query_one(f"#{_id}", ProgressBar)
            _bar.update(progress=max(0, min(100, _val)))
            try:
                _bar.styles.color = _BAND_RGB[stat_band(_kind, _val, _max)]
            except Exception:
                pass

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
        if self._settings.get("command_hints", True):
            commands_widget.update(
                "[b]ACTIONS[/b]   (type `h` for the full command list)\n"
                + "  ·  ".join(p._action_bar())
            )
        else:
            commands_widget.update("")

        self.query_one("#status_block", Static).update(
            _status_block(p, compact=_compact))

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


def _ago(ts):
    """A coarse 'last played' - the menu doesn't need precision."""
    import time
    d = time.time() - ts
    if d < 3600:
        return "just now"
    if d < 86400:
        return "today"
    n = int(d // 86400)
    return "yesterday" if n == 1 else f"{n} days ago"


class MenuScreen(Screen):
    """The shell's home screen. Wired in G3.1 (navigation) and G3.2
    (CONTINUE + NEW CAMPAIGN). LOAD GAME is G4; SETTINGS is G6 - those
    still show a 'coming' note.

    Knows the registry-shaped concept of "a campaign" (world + survivor
    + mode + state) but no world's fiction - adding World 3 must never
    touch this class."""

    CSS = """
    MenuScreen {
        align: center middle;
    }
    #menu_box {
        width: 70;
        height: auto;
        padding: 3 8;
        border: round $accent;
    }
    #menu_title {
        width: 100%;
        height: auto;
        text-align: center;
        text-style: bold;
        color: $accent;
    }
    #menu_subtitle {
        width: 100%;
        height: auto;
        text-align: center;
        color: $text-muted;
        margin-bottom: 3;
    }
    #menu_items {
        width: 100%;
        height: auto;
        text-align: center;
    }
    #menu_note {
        width: 100%;
        height: auto;
        text-align: center;
        margin-top: 3;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("up", "cursor_up", "Up"),
        Binding("down", "cursor_down", "Down"),
        Binding("enter", "activate", "Select"),
        Binding("q", "quit_app", "Quit"),
    ]

    def __init__(self):
        super().__init__()
        self._sel = 0
        self._armed = None      # a two-press confirm ('continue')

    # ---- campaign discovery (reads persistence, never the game) ------

    def _continue_target(self):
        """The most-recently-played resumable campaign, or None.
        Q4: a campaign with a recorded ending is finished - it stays in
        LOAD but does not offer CONTINUE."""
        try:
            for s in Apocrysis.list_campaign_summaries():
                if not s.get("ending"):
                    return s
        except Exception:
            pass
        return None

    def _items(self):
        items = []
        if self._continue_target() is not None:
            items.append("CONTINUE")
        items += ["NEW CAMPAIGN", "LOAD GAME", "SETTINGS", "QUIT"]
        return items

    # ---- lifecycle -------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="menu_box"):
            yield Static("A P O C R Y S I S", id="menu_title")
            yield Static("THE WORLD REMEMBERS", id="menu_subtitle")
            yield Static(self._items_markup(), id="menu_items")
            yield Static("", id="menu_note")
        yield Footer()

    def on_mount(self):
        self._render_items()

    def on_screen_resume(self):
        # A campaign may have just been created / autosaved / abandoned
        # while this screen was in the background.
        self._armed = None
        self._sel = min(self._sel, len(self._items()) - 1)
        self._render_items()
        try:
            self.query_one("#menu_note", Static).update("")
        except Exception:
            pass

    def _items_markup(self):
        items = self._items()
        self._sel = max(0, min(self._sel, len(items) - 1))
        rows = []
        for i, item in enumerate(items):
            rows.append(f"[b]▸  {item}[/b]" if i == self._sel
                        else f"[dim]   {item}[/dim]")
        # double-spaced - the menu should have presence, not be a
        # cramped list in the corner of a big box.
        return "\n\n".join(rows)

    def _render_items(self):
        self.query_one("#menu_items", Static).update(self._items_markup())

    def action_cursor_up(self):
        self._armed = None
        self._sel = (self._sel - 1) % len(self._items())
        self._render_items()

    def action_cursor_down(self):
        self._armed = None
        self._sel = (self._sel + 1) % len(self._items())
        self._render_items()

    def action_quit_app(self):
        self.app.exit()

    def action_activate(self):
        choice = self._items()[self._sel]
        note = self.query_one("#menu_note", Static)

        if choice == "QUIT":
            self.app.exit()
        elif choice == "CONTINUE":
            self._activate_continue(note)
        elif choice == "NEW CAMPAIGN":
            self._armed = None
            self.app.push_screen(NewCampaignScreen(), self._on_new_campaign)
        elif choice == "LOAD GAME":
            self._armed = None
            self.app.push_screen(LoadGameScreen(), self._on_load_pick)
        else:  # SETTINGS
            self._armed = None
            self.app.push_screen(SettingsScreen(self.app._settings),
                                 self._on_settings)

    # ---- CONTINUE (two-press confirm card) --------------------------

    def _activate_continue(self, note):
        s = self._continue_target()
        if s is None:
            self._armed = None
            note.update("[dim]No active campaign - choose NEW CAMPAIGN.[/dim]")
            return
        if self._armed != "continue":
            self._armed = "continue"
            n = s["expeditions_completed"] + 1
            m = s["campaign_length"] or "?"
            note.update(
                f"Resume [b]{s['world_title']}[/b] - {s['name']}, "
                f"expedition {n}/{m}, last played {_ago(s['last_played'])}.\n"
                f"[dim]Press Enter again to resume.[/dim]")
            return
        self._armed = None
        self._start_game(name=s["name"], world=s.get("world_id"))

    # ---- starting a game ------------------------------------------

    def _on_new_campaign(self, result):
        # NewCampaignScreen.dismiss((world_id, name, hardcore)) or None.
        if not result:
            return
        world_id, name, hardcore = result
        self._start_game(name=name, world=world_id, hardcore=hardcore)

    def _on_load_pick(self, result):
        # LoadGameScreen.dismiss((world_id, name)) to load, or None
        # (Back / nothing left after deletes). Same survivor name can
        # exist in two worlds, so the world must come through too.
        if result:
            world_id, name = result
            self._start_game(name=name, world=world_id)

    def _on_settings(self, result):
        # SettingsScreen.dismiss(<settings dict>); it also wrote the
        # file on every change. Keep the app's live copy in sync so the
        # next game started from this menu picks it up.
        if result:
            self.app._settings = result

    def _start_game(self, *, name, world=None, hardcore=False):
        """Push a GameScreen on top of this menu. When the session ends
        (`menu` command / death / quit) GameScreen pops back to here."""
        self.app.push_screen(GameScreen(
            game_name=name,
            world=world,
            hardcore=hardcore,
            start_log=getattr(self.app, "_start_log", False),
            settings=self.app._settings,
        ))


class NewCampaignScreen(Screen):
    """G3.2: choose `world + survivor + mode`. Those three plus the
    (empty) initial state ARE the campaign's identity; world and mode
    are immutable for its life (enforced below the shell - this screen
    only collects them). Dismisses with (world_id, name, hardcore), or
    None if backed out."""

    CSS = """
    NewCampaignScreen {
        align: center middle;
    }
    #nc_box {
        width: 64;
        height: auto;
        padding: 2 4;
        border: round $accent;
    }
    #nc_title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    #nc_box Label {
        margin-top: 1;
        color: $text-muted;
    }
    #nc_mode_help {
        color: $text-muted;
        margin-bottom: 1;
    }
    #nc_start {
        margin-top: 1;
        width: 100%;
    }
    #nc_error {
        color: $error;
        margin-top: 1;
    }
    """

    BINDINGS = [Binding("escape", "back", "Back")]

    def __init__(self):
        super().__init__()
        self._world_ids = world_ids()

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="nc_box"):
            yield Static("NEW CAMPAIGN", id="nc_title")
            yield Label("WORLD")
            with RadioSet(id="nc_world"):
                for i, wid in enumerate(self._world_ids):
                    w = get_world(wid)
                    yield RadioButton(w.manifest.title, value=(i == 0))
            yield Label("SURVIVOR")
            yield Input(placeholder="name", id="nc_name", max_length=24)
            yield Label("MODE")
            with RadioSet(id="nc_mode"):
                yield RadioButton("Normal", value=True)
                yield RadioButton("Hardcore")
            yield Static(
                "Normal keeps your campaign - saved after each expedition, "
                "quit and resume any time.\nHardcore exists only while "
                "you're playing it: no save, no resume, death ends it.",
                id="nc_mode_help")
            yield Button("START CAMPAIGN", id="nc_start", variant="primary")
            yield Static("", id="nc_error")
        yield Footer()

    def on_mount(self):
        self.query_one("#nc_name", Input).focus()

    def action_back(self):
        self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted):
        if event.input.id == "nc_name":
            self._start()

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "nc_start":
            self._start()

    def _start(self):
        from src.mixins.persistence_mixin import clean_display_name
        err = self.query_one("#nc_error", Static)

        world_id = self._world_ids[
            max(0, self.query_one("#nc_world", RadioSet).pressed_index)]
        hardcore = self.query_one("#nc_mode", RadioSet).pressed_index == 1
        raw = self.query_one("#nc_name", Input).value
        name = clean_display_name(raw)
        if not raw.strip():
            err.update("Enter a name for your survivor.")
            return

        # Collision is per (world, survivor) - the same name can hold a
        # separate campaign in each world.
        collides = Apocrysis.load_campaign(world_id, name) is not None
        world_title = get_world(world_id).manifest.title
        if collides and not hardcore:
            err.update(
                f"{name} already has a campaign in {world_title} - "
                f"use CONTINUE or LOAD GAME to resume it.")
            return
        if collides and hardcore:
            # A Hardcore run has no file; it can't clobber the Normal
            # profile, but say so plainly.
            err.update(
                f"[dim]Note: a Normal campaign named {name} exists in "
                f"{world_title}. This Hardcore run is separate and "
                f"unsaved.[/dim]")

        self.dismiss((world_id, name, hardcore))


class LoadGameScreen(Screen):
    """G4: the campaign lister. Every on-disk campaign is Normal
    (Hardcore writes no file), so there's no MODE column. Finished
    campaigns (recorded ending) stay here - this is their home (Q4) -
    marked DONE. Load (Enter), Delete (two-press), Back (Esc).
    Dismisses the chosen survivor name, or None.

    Reads persistence via list_campaign_summaries; no world fiction."""

    CSS = """
    LoadGameScreen {
        align: center middle;
    }
    #lg_box {
        width: 76;
        height: auto;
        max-height: 90%;
        padding: 2 4;
        border: round $accent;
    }
    #lg_title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    #lg_head {
        color: $text-muted;
        text-style: bold;
    }
    #lg_rows {
        height: auto;
    }
    #lg_note {
        color: $text-muted;
        margin-top: 1;
    }
    """

    BINDINGS = [
        Binding("up", "cursor_up", "Up"),
        Binding("down", "cursor_down", "Down"),
        Binding("enter", "load", "Load"),
        Binding("d", "delete", "Delete"),
        Binding("escape", "back", "Back"),
    ]

    def __init__(self):
        super().__init__()
        self._sel = 0
        self._armed_delete = None      # survivor name armed for delete

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="lg_box"):
            yield Static("LOAD GAME", id="lg_title")
            yield Static(
                f"  {'WORLD':<18}{'SURVIVOR':<12}{'PROGRESS':<12}LAST PLAYED",
                id="lg_head")
            yield Static(id="lg_rows")
            yield Static("[dim]Enter load  ·  D delete  ·  Esc back[/dim]",
                         id="lg_note")
        yield Footer()

    def on_mount(self):
        self._reload()

    def _reload(self):
        self._rows = Apocrysis.list_campaign_summaries()
        if self._rows:
            self._sel = min(self._sel, len(self._rows) - 1)
        self._render_rows()

    def _render_rows(self):
        body = self.query_one("#lg_rows", Static)
        if not self._rows:
            body.update("[dim]  No saved campaigns.[/dim]")
            return
        lines = []
        for i, r in enumerate(self._rows):
            n = r["expeditions_completed"]
            m = r["campaign_length"] or "?"
            prog = "DONE" if r.get("ending") else f"EXP {n + 1}/{m}"
            row = (f"{r['world_title'][:17]:<18}{r['name'][:11]:<12}"
                   f"{prog:<12}{_ago(r['last_played'])}")
            if i == self._sel:
                lines.append(f"[b]▸ {row}[/b]")
            else:
                lines.append(f"[dim]  {row}[/dim]")
        body.update("\n".join(lines))

    def _clear_arm(self):
        if self._armed_delete is not None:
            self._armed_delete = None
            self.query_one("#lg_note", Static).update(
                "[dim]Enter load  ·  D delete  ·  Esc back[/dim]")

    def action_cursor_up(self):
        self._clear_arm()
        if self._rows:
            self._sel = (self._sel - 1) % len(self._rows)
            self._render_rows()

    def action_cursor_down(self):
        self._clear_arm()
        if self._rows:
            self._sel = (self._sel + 1) % len(self._rows)
            self._render_rows()

    def action_back(self):
        self.dismiss(None)

    def action_load(self):
        if not self._rows:
            self.dismiss(None)
            return
        r = self._rows[self._sel]
        self.dismiss((r.get("world_id"), r["name"]))

    def action_delete(self):
        if not self._rows:
            return
        r = self._rows[self._sel]
        target = r["name"]
        key = (r.get("world_id"), target)
        note = self.query_one("#lg_note", Static)
        if self._armed_delete != key:
            self._armed_delete = key
            note.update(
                f"[b]Delete {target}'s {r['world_title']} campaign? "
                f"This can't be undone.[/b] [dim]Press D again.[/dim]")
            return
        Apocrysis.delete_campaign(target, r.get("world_id"))
        self._armed_delete = None
        note.update(f"[dim]Deleted {target}.[/dim]")
        self._reload()


class SettingsScreen(Screen):
    """G6 (§8): the four player-global preferences. Every toggle writes
    settings.json immediately; dismisses the final dict. Player
    preferences only - no Hardcore toggle, no world picker (those are
    campaign identity, chosen once at creation). No world fiction."""

    CSS = """
    SettingsScreen {
        align: center middle;
    }
    #set_box {
        width: 60;
        height: auto;
        padding: 2 4;
        border: round $accent;
    }
    #set_title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    #set_note {
        color: $text-muted;
        margin-top: 1;
    }
    """

    BINDINGS = [
        Binding("up", "cursor_up", "Up"),
        Binding("down", "cursor_down", "Down"),
        Binding("enter", "toggle", "Toggle"),
        Binding("space", "toggle", "Toggle"),
        Binding("escape", "back", "Back"),
    ]

    def __init__(self, current):
        super().__init__()
        from src import settings as _s
        self._s = _s
        self._values = _s.load() if current is None else dict(current)
        self._sel = 0

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="set_box"):
            yield Static("SETTINGS", id="set_title")
            yield Static(id="set_rows")
            yield Static("[dim]Enter / Space toggle  ·  Esc back[/dim]",
                         id="set_note")
        yield Footer()

    def on_mount(self):
        self._render_rows()

    def _render_rows(self):
        keys = self._s.ORDER
        out = []
        for i, k in enumerate(keys):
            label = self._s.LABELS[k]
            val = self._s.display(self._values, k)
            row = f"{label:<18}{val}"
            out.append(f"[b]▸ {row}[/b]" if i == self._sel
                       else f"[dim]  {row}[/dim]")
        self.query_one("#set_rows", Static).update("\n".join(out))

    def action_cursor_up(self):
        self._sel = (self._sel - 1) % len(self._s.ORDER)
        self._render_rows()

    def action_cursor_down(self):
        self._sel = (self._sel + 1) % len(self._s.ORDER)
        self._render_rows()

    def action_toggle(self):
        key = self._s.ORDER[self._sel]
        self._values = self._s.save(self._s.toggled(self._values, key))
        self._render_rows()

    def action_back(self):
        self.dismiss(self._values)


class ApocrysisApp(App):
    """The shell. The game body lives on GameScreen; MenuScreen is the
    home screen. The __init__ signature is preserved (src/cli.py,
    src/tests depend on it).

    G3.2: the real launch (cli.main_tui, no args) lands on MenuScreen -
    there is no pre-Textual identity prompt any more. An explicit
    `name=` (tests, and back-compat) boots straight into a game for
    that name, with MenuScreen underneath so `menu` still works.
    `--dev` boots straight into its sandboxed game."""

    def __init__(self, name=None, level=1, seed=None, hardcore=False,
                 start_log=False, dev=None):
        super().__init__()
        self._start_log = start_log
        self._dev = dev
        self._boot_name = name
        self._boot_kw = dict(game_name=name, level=level, seed=seed,
                             hardcore=hardcore, start_log=start_log, dev=dev)
        # G6: player-global preferences, loaded once. MenuScreen reads
        # self.app._settings; SettingsScreen writes the file and updates
        # this copy; every GameScreen the menu starts is handed it.
        from src import settings as _settings_mod
        self._settings = _settings_mod.load()

    async def on_mount(self):
        # MenuScreen is always the base the shell rests on. A direct
        # boot (explicit name, or --dev) pushes GameScreen on top -
        # awaited in sequence so the background screen is fully mounted
        # before the compositor renders it.
        await self.push_screen(MenuScreen())
        if self._dev is not None or self._boot_name is not None:
            await self.push_screen(GameScreen(settings=self._settings,
                                              **self._boot_kw))
