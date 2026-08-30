"""PerceivedBotIO + run_one() — drive one perception-bounded game.

`PerceivedBotIO` is a drop-in `io` (like ConsoleIO / BotIO). It:
  - suppresses the classic ASCII panel (`renders_natively = True`)
  - buffers every `say()` line (ANSI-stripped) since the last prompt
  - on each prompt, builds a `Perception` and asks the `Policy`

Unlike `tools/balance_autoplay.py:BotIO` it exposes `ask_combat_letter`
so the bot sees the real encounter card — this perturbs the combat RNG
stream vs the balance lab (by design; different tool, different
question) but stays seed-deterministic within this harness.

`run_one()` sets up a synthetic chapter state the same way
`src/cli.py`'s `--dev` path does (via `src/dev.py`), runs the loop,
and returns a filled `RunRecord`. The only "privileged" reads are in
the post-game analysis block (objective_reached etc.) — outcome facts,
never fed to a policy.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from src.game import Apocrysis                       # noqa: E402
from src.dev import DevConfig, synthetic_state, equip_for_depth  # noqa: E402
from tools.autoplay.perceive import build_perception, strip      # noqa: E402
from tools.autoplay.metrics import RunRecord                      # noqa: E402
from tools.autoplay import policies as _policies                  # noqa: E402


class _StopGame(Exception):
    pass


class PerceivedBotIO:
    renders_natively = True   # suppress the per-turn ASCII two-column block

    def __init__(self, policy, max_turns):
        self.policy = policy
        self.max_turns = max_turns
        self.player = None
        self.record = RunRecord(policy=policy.name)
        self._buf = []          # say() lines since the last prompt
        self._turn = 0
        self._positions = []    # (x, y) at the top of each command
        self._last_pos = None
        self._prev_lead_dist = None
        self._min_health = 10 ** 9

    # --- output -----------------------------------------------------
    def say(self, *args, **kwargs):
        text = " ".join(str(a) for a in args)
        for line in text.splitlines():
            s = strip(line)
            if s:
                self._buf.append(s)

    # --- prompts --------------------------------------------------
    def ask(self, prompt=""):
        if prompt.strip().startswith("Press Enter"):
            return ""
        # a real turn command
        self._turn += 1
        self.record.turns = self._turn
        if self._turn > self.max_turns:
            raise _StopGame
        per = self._perceive()
        self._buf.clear()
        self.record.observe(per)
        self._track_movement(per)
        cmd = self.policy.on_command(per)
        return (cmd or "n").lower()

    def ask_yes_no(self, prompt):
        per = self._perceive()
        self.record.observe(per)
        return bool(self.policy.on_yes_no(per))

    def ask_combat_letter(self):
        per = self._perceive()
        self.record.observe(per)
        letter = self.policy.on_combat_letter(per)
        return letter if letter in ("f", "e", "w") else "f"

    # --- internals ------------------------------------------------
    def _perceive(self):
        return build_perception(self.player, list(self._buf), self._turn)

    def _track_movement(self, per):
        pos = per.player_xy
        self._positions.append(pos)
        self._min_health = min(self._min_health, per.hud["health"])
        # pursuing vs wandering: did this turn step us closer to a
        # visible mystery marker than the last?
        leads = per.glyph_positions("!+")
        if leads:
            px, py = pos
            dist = min(abs(px - lx) + abs(py - ly) for lx, ly in leads)
            if self._prev_lead_dist is not None:
                if dist < self._prev_lead_dist:
                    self.record.turns_pursuing += 1
                else:
                    self.record.turns_wandering += 1
            self._prev_lead_dist = dist
        else:
            self.record.turns_wandering += 1


def _apply_chapter(seed, chapter):
    """Prime the class-level synthetic state exactly like cli.main_classic's
    --dev branch, and return (expeditions_completed, wi_status)."""
    if chapter is None:
        return 0, None
    cfg = DevConfig(seed=seed, chapter=chapter, finale=False)
    depth, wi_status = synthetic_state(cfg)
    return depth, wi_status


def run_one(seed, chapter, policy_name, max_turns=600, nav_phrasing="cardinal"):
    import random as _r
    # The encounter card (combat_forecast) draws from the *global*
    # random stream — unlike balance_autoplay, which omits
    # ask_combat_letter for exactly that reason. Seed it so a given
    # (seed, policy) run is reproducible. The engine's own world/combat
    # RNG (player.rng) is seeded separately by Apocrysis(seed=...).
    if seed is not None:
        _r.seed(seed)
    policy = _policies.make(policy_name, rng=_r.Random(seed))

    depth, wi_status = _apply_chapter(seed, chapter)
    io = PerceivedBotIO(policy, max_turns=max_turns)

    if wi_status is not None:
        Apocrysis._world_investigation = dict(wi_status)
        Apocrysis._survivor_knowledge = []
        player = Apocrysis("Bot", level=1, seed=seed, hardcore=False,
                           expeditions_completed=depth, io=io)
        equip_for_depth(player, depth)
    else:
        player = Apocrysis("Bot", level=1, seed=seed, io=io)
    io.player = player

    rec = io.record
    rec.seed = seed
    rec.chapter = chapter
    rec.nav_phrasing = nav_phrasing

    try:
        player.run_game_loop()
    except _StopGame:
        pass

    # ---------- outcome ----------
    if getattr(player, "won", False):
        rec.outcome = "won"
    elif player.health <= 0:
        rec.outcome = "died"
    else:
        rec.outcome = "timeout"
    rec.final_level = player.level
    rec.final_day = player.day
    rec.min_health = 0 if io._min_health >= 10 ** 9 else io._min_health
    rec.final_food = player.backpack.food
    rec.final_water = player.backpack.water

    # ---------- post-game analysis (privileged reads — never a policy input) ----------
    m = getattr(player, "mystery", None)
    if m is not None:
        k = getattr(m, "knowledge", None)
        rec.facts_found = len(k.facts_known()) if k else 0
        rec.facts_available = len(k.facts) if k else 0
        rec.mystery_solved = bool(
            getattr(m, "obstacle_open", False)
            and k and k.hypothesis_state() == "confirmed")
        esc = getattr(m, "escape_tile", None)
        if esc is not None:
            reached = [i for i, p in enumerate(io._positions) if p == esc]
            rec.objective_reached = bool(reached) or getattr(player, "won", False)
            rec.turns_to_objective = (reached[0] + 1) if reached else None

    uniq = len(set(io._positions))
    steps = max(1, len(io._positions))
    rec.tiles_visited = uniq
    rec.revisit_ratio = round(1 - uniq / steps, 3)
    if io._positions:
        sx, sy = io._positions[0]
        rec.max_distance_from_spawn = max(
            abs(x - sx) + abs(y - sy) for x, y in io._positions)
    if rec.outcome == "died":
        rec.combat_deaths = 1  # this harness only dies in combat/starvation;
        rec.death_cause = "combat-or-attrition"

    return rec


if __name__ == "__main__":
    import sys
    sys.exit(
        "tools/autoplay/runner.py is a library module, not a runnable command.\n"
        "It is imported by the autoplay/telemetry CLIs. Run one of those:\n"
        "  python3 tools/telemetry.py --help\n"
        "  python3 tools/nav_autoplay.py --help\n"
        "  python3 tools/resource_autoplay.py --help\n"
        "  python3 tools/fatigue_autoplay.py --help\n"
        "  python3 tools/story_playthrough.py --help\n"
        "See tools/autoplay/README.md for the seam design.")
