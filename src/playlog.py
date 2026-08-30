# ============================================================
# Apocrysis - human play logging (v4)
# File: src/playlog.py
#
# Writes a plain-text transcript of a play session - every command,
# every line of game output, and a per-turn state snapshot - to a
# .txt file, so a real playthrough can be handed to someone (or an
# LLM) for "how is this actually being played?" analysis.
#
# On by default for interactive play (one file per session, each
# expedition appended); toggle in game with `log`, suppress with
# `python3 apocrysis.py --no-log`.
# ============================================================

import datetime
import os


class PlayLog:
    def __init__(self, path, game):
        # absolute so the "saved to" message points somewhere the
        # player can actually find, regardless of launch cwd
        self.path = os.path.abspath(path)
        self.game = game
        self._f = open(self.path, "a", encoding="utf-8")
        self._closed = False
        self._turns_logged = 0
        self._write_header()

    # ---- writing --------------------------------------------

    def _w(self, text=""):
        # a stray write after the game loop has already closed the log
        # (e.g. the end-of-game "*** YOU DIED ***" banner) must never
        # take the whole game down with an I/O error
        if self._closed:
            return
        try:
            self._f.write(text + "\n")
        except ValueError:
            self._closed = True

    def _flush(self):
        try:
            self._f.flush()
        except ValueError:
            pass

    def _clock(self):
        p = self.game
        return f"{p.time_of_day // 60:02d}:{p.time_of_day % 60:02d}"

    def _write_header(self):
        p = self.game
        self._w("=" * 64)
        self._w(f"APOCRYSIS PLAY LOG   {datetime.datetime.now():%Y-%m-%d %H:%M:%S}")
        self._w(f"player      : {p.name}  (level {p.level})")
        try:
            from src.constants import CAMPAIGN_LENGTH as _CL
        except Exception:
            _CL = 25
        self._w(f"expedition  : {p.expeditions_completed + 1} of {_CL}")
        mystery = getattr(p, "mystery", None)
        if mystery is not None:
            self._w(f"escape mech : {mystery.mechanism}")
            self._w(f"  (this line is here so an analyst knows the intended answer -")
            self._w(f"   the player does NOT see it in game)")
        self._w(f"map size    : {p.map_size}x{p.map_size}")
        self._w(f"spawn       : {p.current_position}")
        self._w("=" * 64)
        self._w("Legend:  '> cmd' = what the player typed.  indented lines = game")
        self._w("output.  '[state]' = a per-turn snapshot (not shown in game).")
        self._flush()

    def command(self, cmd):
        p = self.game
        self._w()
        self._w(f"--- turn {getattr(p, 'turns', 0)} | day {p.day} {self._clock()} "
                f"{getattr(p, 'day_phase', '?')} | at {p.current_position} ---")
        self._w(f"> {cmd}")
        self._flush()

    def output(self, text):
        text = text or ""
        # strip ANSI colour codes so the log is clean plain text
        import re
        text = re.sub(r"\x1b\[[0-9;]*m", "", text)
        for line in (text.split("\n") if text else [""]):
            stripped = line.strip()
            if not stripped:
                continue  # drop the blank spacer lines
            if set(stripped) <= {"*"} and len(stripped) > 10:
                continue  # drop the turn-separator banner
            self._w(f"    {line}")

    def input_answer(self, prompt, answer):
        self._w(f"    [{prompt.strip()} -> {answer}]")

    def snapshot(self):
        p = self.game
        bits = [
            f"HP {p.health}/{p.max_health}",
            f"hunger {p.hunger} thirst {p.thirst} fatigue {p.fatigue}",
            f"food {p.backpack.food} water {p.backpack.water} "
            f"med {p.backpack.medicine} ammo {p.backpack.ammo}",
            f"visited {len(p.visited)} tiles",
        ]
        eq = p.equipped_weapon
        if eq:
            bits.append(f"weapon {eq.name}({getattr(eq, 'damage', '?')})")

        k = getattr(p, "knowledge", None)
        if k is not None and not k.is_empty():
            facts = sorted(k.facts_known())
            hyp = k.hypothesis_state() if getattr(k, "hypothesis", None) else "n/a"
            bits.append(f"facts_known {facts}")
            bits.append(f"evidence_found {sorted(k.found)}")
            bits.append(f"hypothesis {hyp}")

        m = getattr(p, "mystery", None)
        if m is not None:
            bits.append(f"obstacle_open {m.obstacle_open}")
            if p.map_revealed if hasattr(p, "map_revealed") else False:
                bits.append("map_revealed")

        self._w(f"    [state] {' | '.join(bits)}")
        self._turns_logged += 1
        self._flush()

    def close(self, reason):
        p = self.game
        self._w()
        self._w("=" * 64)
        self._w(f"END: {reason}")
        self._w(f"  turn {getattr(p, 'turns', 0)} | day {p.day} {self._clock()} | "
                f"level {p.level} | visited {len(p.visited)} tiles")
        k = getattr(p, "knowledge", None)
        if k is not None and not k.is_empty():
            self._w(f"  facts known : {sorted(k.facts_known())}")
            self._w(f"  hypothesis  : "
                    f"{k.hypothesis_state() if getattr(k, 'hypothesis', None) else 'n/a'}")
        self._w("=" * 64)
        try:
            self._f.close()
        except Exception:
            pass
        self._closed = True


class TeeIO:
    """Wraps the real IO so every say()/ask_yes_no() also lands in the
    play log. Unknown attributes delegate to the wrapped IO."""

    def __init__(self, inner, playlog):
        self._inner = inner
        self._playlog = playlog
        self.renders_natively = getattr(inner, "renders_natively", False)

    def say(self, *args, **kwargs):
        self._inner.say(*args, **kwargs)
        self._playlog.output(" ".join(str(a) for a in args) if args else "")

    def ask(self, prompt=""):
        return self._inner.ask(prompt)

    def ask_yes_no(self, prompt):
        answer = self._inner.ask_yes_no(prompt)
        self._playlog.input_answer(prompt, "yes" if answer else "no")
        return answer

    def ask_combat_letter(self):
        # Combat-info experiment (COMBAT_INFO_SPEC.md): log the player's
        # fight/escape/weapons choice so the playtest can score
        # decision-against-prediction.
        answer = self._inner.ask_combat_letter()
        self._playlog.input_answer("combat choice", answer)
        return answer

    def __getattr__(self, name):
        return getattr(self._inner, name)
