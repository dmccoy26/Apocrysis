#!/usr/bin/env python3
"""Black-box telemetry recorder for Apocrysis.

Not an outcome counter - an EVENT STREAM. Every campaign produces a
`campaign → run → turn → event → payload` trace from which the rich
report is derived. Four levels:

  1. turn / environment  - per-turn snapshot: terrain, movement,
                           vitals, gear, distance
  2. survival state       - time in each band + the transitions
                           (HEALTHY→WOUNDED, FED→HUNGRY, …)
  3. combat               - per encounter: pre-state, the forecast AT
                           THE MOMENT OF DECISION (before the outcome),
                           the decision, per-round damage, the outcome
  4. decision             - what the bot believed vs what it did
                           (forecast tier / fight% / escape% vs action)

Constraint: the recorder OBSERVES; it never feeds the bot information
it wouldn't have, and forecast fields are captured pre-outcome.

    python3 tools/telemetry.py --campaigns 5
    python3 tools/telemetry.py --campaigns 20 --jsonl out/trace.jsonl --policy survival
"""
import argparse
import json
import os
import re
import statistics
import sys
import tempfile
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.constants import CAMPAIGN_LENGTH
from src.game import Apocrysis
from src import combat_forecast as cf
from tools.autoplay.perceive import build_perception, strip
from tools.autoplay import policies as _policies

_HIT = re.compile(r"^The .+ takes (\d+) damage\.(?: Its current health is (-?\d+)\.)?$")
_DEFEATED = re.compile(r"^The .+ has been defeated!$")
_GOT_AWAY = re.compile(r"^✓? ?You got away")
_FORCED = re.compile(r"COULDN'T GET AWAY|Couldn't get away")

# resource-economy lines (docs/RESOURCE_MODEL_RESULTS.md)
_FOUND = re.compile(r"^You found (?:some )?(food|water|medicine|ammo)!?")
_FOUND_QTY = re.compile(r"^You found (food|water) - enough for a while\. \(\+(\d+)\)")
_ATE = re.compile(r"^You eat (\d+) rations")
_DRANK = re.compile(r"^You drink (\d+) portions")
_MEDDED = re.compile(r"^You use medicine")
_RESTED = re.compile(r"^You rest and recover (\d+) fatigue")
_BLD_RECOVER = re.compile(r"recovered some fatigue|safe for now")
_GETTING = re.compile(r"^⚠ GETTING (HUNGRY|THIRSTY)")
_WEARING_DOWN = re.compile(r"is wearing you down")


# --------------------------------------------------------- analysis-only
def _manh(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _objective_tile(p):
    """The tile the survivor SHOULD be heading for right now, from real
    mystery state. ANALYSIS ONLY - never handed to a policy."""
    m = getattr(p, "mystery", None)
    if m is None:
        return None
    searched = getattr(p, "_mystery_named", set())
    for role in ("route", "require", "require2"):
        if role in m.sites and role not in searched \
                and p.current_position != m.sites[role]:
            return m.sites[role]
    if getattr(m, "power_role", None) and not m.power_restored:
        return m.sites.get(m.power_role)
    if not m.obstacle_open and getattr(m, "obstacle_tile", None):
        return m.obstacle_tile
    return m.escape_tile


# ---------------------------------------------------------------- bands
def _hp_band(hp, mx):
    f = hp / max(1, mx)
    return "critical" if f < 0.25 else "wounded" if f < 0.60 else "healthy"

def _hunger_band(h):
    return "starving" if h < 15 else "hungry" if h < 40 else "fed"

def _fatigue_band(f):
    return "exhausted" if f > 80 else "fatigued" if f > 50 else "rested"


class Recorder:
    def __init__(self, jsonl=None):
        self.events = []
        self._f = open(jsonl, "a") if jsonl else None
        self.campaign = 0
        self.run = 0

    def emit(self, turn, etype, **payload):
        e = {"campaign": self.campaign, "run": self.run, "turn": turn,
             "event": etype, **payload}
        self.events.append(e)
        if self._f:
            self._f.write(json.dumps(e, default=str) + "\n")

    def close(self):
        if self._f:
            self._f.close()


class TelemetryIO:
    """Wraps an autoplay Policy; records everything it sees. renders
    natively so the classic ASCII panel is suppressed."""
    renders_natively = True

    def __init__(self, policy, recorder, max_turns=600):
        self.policy = policy
        self.rec = recorder
        self.max_turns = max_turns
        self.player = None
        self._buf = []
        self._turn = 0
        self._last = None          # previous turn snapshot
        self._pending_combat = None  # dict being filled between decision and next turn
        self._spawn = None
        self._tiles = set()
        self._visits = defaultdict(int)   # (x,y) -> times stood on
        self._prev_time_min = None
        self._recent_combat_turn = -99    # for "food from loot" inference

    # -- output --
    def say(self, *a, **k):
        text = " ".join(str(x) for x in a)
        for ln in text.splitlines():
            s = strip(ln)
            if s:
                self._buf.append(s)
                if self._pending_combat is not None:
                    self._combat_line(s)
                self._resource_line(s)

    def _found_source(self):
        p = self.player
        pos = p.current_position
        cell = p.map[pos[1]][pos[0]]
        terr = cell.get("terrain") if isinstance(cell, dict) else None
        if self._pending_combat is not None or self._turn - self._recent_combat_turn <= 1:
            return "zombie-loot"
        if terr == "building" or (isinstance(cell, dict) and cell.get("content") in ("H", "R", "S", "B", "T")):
            return "building"
        return "ground"

    def _resource_line(self, s):
        t = self._turn
        m = _FOUND_QTY.match(s)
        if m:
            self.rec.emit(t, "resource", kind=m.group(1), op="found",
                          qty=int(m.group(2)), source=self._found_source())
            return
        m = _FOUND.match(s)
        if m:
            self.rec.emit(t, "resource", kind=m.group(1), op="found", qty=None,
                          source=self._found_source())
            return
        m = _ATE.match(s)
        if m:
            self.rec.emit(t, "resource", kind="food", op="consumed",
                          qty=int(m.group(1))); return
        m = _DRANK.match(s)
        if m:
            self.rec.emit(t, "resource", kind="water", op="consumed",
                          qty=int(m.group(1))); return
        if _MEDDED.match(s):
            self.rec.emit(t, "resource", kind="medicine", op="consumed", qty=1)
            return
        m = _RESTED.match(s)
        if m:
            self.rec.emit(t, "resource", kind="fatigue", op="rest",
                          qty=int(m.group(1))); return
        if _BLD_RECOVER.search(s):
            self.rec.emit(t, "resource", kind="fatigue", op="building_recover",
                          qty=None); return
        m = _GETTING.match(s)
        if m:
            self.rec.emit(t, "resource", kind=m.group(1).lower(), op="warned")
            return
        if _WEARING_DOWN.search(s):
            self.rec.emit(t, "resource", kind="hunger_thirst", op="damage")

    def _combat_line(self, s):
        pc = self._pending_combat
        m = _HIT.match(s)
        if m:
            dmg = int(m.group(1))
            if m.group(2) is not None:   # "...current health is N" -> a hit on the PLAYER
                pc["rounds"].append({"to": "player", "dmg": dmg, "player_hp": int(m.group(2))})
                pc["dmg_taken"] += dmg
            else:
                pc["rounds"].append({"to": "zombie", "dmg": dmg})
                pc["dmg_dealt"] += dmg
        elif _DEFEATED.match(s):
            pc["outcome"] = "win"
        elif _GOT_AWAY.match(s):
            pc["outcome"] = "escape"
        elif _FORCED.search(s):
            pc["forced_fight"] = True

    # -- prompts --
    def ask(self, prompt=""):
        if prompt.strip().startswith("Press Enter"):
            return ""
        # a real turn command -> close out the previous turn/combat
        self._flush_combat()
        self._turn += 1
        if self._turn > self.max_turns:
            raise _Stop
        per = self._perceive()
        self._buf.clear()
        snap = self._snapshot_turn(per)
        cmd = (self.policy.on_command(per) or "n").lower()
        snap["action"] = cmd
        self.rec.emit(self._turn, "turn", **{k: v for k, v in snap.items()
                                             if k != "turn"})
        return cmd

    def ask_yes_no(self, prompt):
        per = self._perceive()
        self._begin_combat(per, interactive=False)
        d = bool(self.policy.on_yes_no(per))
        self._pending_combat["decision"] = "fight" if d else "escape"
        self._record_decision(per)
        return d

    def ask_combat_letter(self):
        per = self._perceive()
        self._begin_combat(per, interactive=True)
        letter = self.policy.on_combat_letter(per)
        letter = letter if letter in ("f", "e", "w") else "f"
        if letter != "w":
            self._pending_combat["decision"] = "fight" if letter == "f" else "escape"
            self._record_decision(per)
        return letter

    # -- internals --
    def _perceive(self):
        return build_perception(self.player, list(self._buf), self._turn)

    def _snapshot_turn(self, per):
        from src.constants import MINUTES_PER_DAY
        p = self.player
        pos = p.current_position
        if self._spawn is None:
            self._spawn = pos
        self._tiles.add(pos)
        self._visits[pos] += 1
        cell = p.map[pos[1]][pos[0]]
        terrain = cell.get("terrain") if isinstance(cell, dict) else "zombie-tile"
        time_min = (p.day - 1) * MINUTES_PER_DAY + p.time_of_day
        dt = (None if self._prev_time_min is None
              else max(0, time_min - self._prev_time_min))
        self._prev_time_min = time_min
        snap = {
            "turn": self._turn, "day": p.day,
            "phase": getattr(p, "day_phase", "night" if p.is_night else "day"),
            "time_min": time_min, "dt_min": dt,
            "revisit": self._visits[pos],
            "obj_state": getattr(p, "_obj_state", None),
            "pos": list(pos), "terrain": terrain,
            "hp": p.health, "max_hp": p.max_health,
            "hunger": p.hunger, "thirst": p.thirst, "fatigue": p.fatigue,
            "level": p.level, "xp": p.xp,
            "weapon": getattr(p.equipped_weapon, "name", None),
            "weapon_dmg": getattr(p.equipped_weapon, "damage", 0),
            "armor": sum(a.damage_reduction for a in p.equipped_armor.values()
                         if a and getattr(a, "durability", 1) > 0),
            "food": p.backpack.food, "water": p.backpack.water,
            "med": p.backpack.medicine, "ammo": p.backpack.ammo,
            "dist_from_spawn": abs(pos[0] - self._spawn[0]) + abs(pos[1] - self._spawn[1]),
            "tiles_visited": len(self._tiles),
            "hp_band": _hp_band(p.health, p.max_health),
            "hunger_band": _hunger_band(p.hunger),
            "fatigue_band": _fatigue_band(p.fatigue),
            "action": None,
        }
        if self._last is not None:
            for key, label in (("hp_band", "hp"), ("hunger_band", "hunger"),
                               ("fatigue_band", "fatigue")):
                if snap[key] != self._last[key]:
                    self.rec.emit(self._turn, "state_transition", axis=label,
                                  frm=self._last[key], to=snap[key],
                                  hp=p.health, turn_from=self._last["turn"])
            if snap["obj_state"] != self._last["obj_state"]:
                m = getattr(p, "mystery", None)
                obj = _objective_tile(p) if m is not None else None
                self.rec.emit(self._turn, "objective_transition",
                              frm=self._last["obj_state"], to=snap["obj_state"],
                              turns_since_progress=(
                                  self._turn - getattr(p, "_obj_last_progress_turn", self._turn)),
                              dist_to_target=(_manh(pos, obj) if obj else None),
                              action=None)
        self._last = snap
        return snap

    def _begin_combat(self, per, interactive):
        if self._pending_combat is not None:
            self._flush_combat()
        self._recent_combat_turn = self._turn
        enc = per.encounter or {}
        p = self.player
        self._pending_combat = {
            "start_turn": self._turn,
            "zombie": enc.get("name") or "Zombie",
            "threat": enc.get("threat"),
            "fight_pct": enc.get("fight_pct"),
            "escape_pct": enc.get("escape_pct"),
            "weapon": getattr(p.equipped_weapon, "name", None),
            "weapon_dmg": getattr(p.equipped_weapon, "damage", 0),
            "hp": p.health, "max_hp": p.max_health,
            "armor": sum(a.damage_reduction for a in p.equipped_armor.values()
                         if a and getattr(a, "durability", 1) > 0),
            "fatigue": p.fatigue, "dexterity": p.dexterity,
            "hp_band": _hp_band(p.health, p.max_health),
            "fatigue_band": _fatigue_band(p.fatigue),
            "interactive": interactive,
            "decision": None, "rounds": [], "dmg_dealt": 0, "dmg_taken": 0,
            "outcome": None, "forced_fight": False,
        }

    def _record_decision(self, per):
        pc = self._pending_combat
        # what a threat-aware policy "should" do, for the mismatch stat
        threat = (pc["threat"] or "").upper()
        fp = pc["fight_pct"]
        expected = "escape" if (threat in ("EXTREME", "SEVERE")
                                or (fp is not None and fp < 35)) else "fight"
        self.rec.emit(pc["start_turn"], "combat_decision",
                      zombie=pc["zombie"], threat=pc["threat"],
                      fight_pct=fp, escape_pct=pc["escape_pct"],
                      hp_band=pc["hp_band"], fatigue_band=pc["fatigue_band"],
                      weapon=pc["weapon"], decision=pc["decision"],
                      expected=expected, mismatch=(pc["decision"] != expected))

    def _flush_combat(self):
        pc = self._pending_combat
        if pc is None:
            return
        self._pending_combat = None
        p = self.player
        if pc["outcome"] is None:
            pc["outcome"] = "death" if p.health <= 0 else (
                "win" if pc["decision"] == "fight" else "escape")
        pos = p.current_position
        cell = p.map[pos[1]][pos[0]]
        pc["terrain"] = cell.get("terrain") if isinstance(cell, dict) else "zombie-tile"
        self.rec.emit(pc["start_turn"], "combat", terrain=pc["terrain"],
                      zombie=pc["zombie"], threat=pc["threat"],
                      fight_pct=pc["fight_pct"], escape_pct=pc["escape_pct"],
                      weapon=pc["weapon"], weapon_dmg=pc["weapon_dmg"],
                      armor=pc["armor"], hp_before=pc["hp"],
                      hp_band=pc["hp_band"], fatigue_band=pc["fatigue_band"],
                      decision=pc["decision"], forced_fight=pc["forced_fight"],
                      rounds=len([r for r in pc["rounds"] if r["to"] == "zombie"]),
                      dmg_dealt=pc["dmg_dealt"], dmg_taken=pc["dmg_taken"],
                      outcome=pc["outcome"], hp_after=p.health,
                      round_detail=pc["rounds"])


class _Stop(Exception):
    pass


# ---------------------------------------------------------------- run
def run_campaign(rec, policy_name, seed, max_turns=600, max_attempts=6):
    import random
    Apocrysis._used_mechanisms = []
    profile, level, exp = None, 1, 0
    attempts = defaultdict(int)
    with tempfile.TemporaryDirectory() as tmp:
        pf = os.path.join(tmp, "p.json")
        while exp < CAMPAIGN_LENGTH:
            attempts[exp] += 1
            if attempts[exp] > max_attempts:
                rec.emit(0, "campaign_end", reason="stuck", stuck_at=exp, level=level)
                return
            rec.run += 1
            pol = _policies.make(policy_name, rng=random.Random(seed + rec.run))
            io = TelemetryIO(pol, rec, max_turns=max_turns)
            p = Apocrysis("Tel", level=level, expeditions_completed=exp,
                          seed=seed + rec.run * 7, io=io)
            if profile is not None:
                p.apply_profile(profile)
            io.player = p
            rec.emit(0, "expedition_start", exp=exp, level=level,
                     weapon=getattr(p.equipped_weapon, "name", None))
            try:
                p.run_game_loop()
            except _Stop:
                pass
            io._flush_combat()
            outcome = ("won" if getattr(p, "won", False)
                       else "died" if p.health <= 0 else "timeout")
            rec.emit(io._turn, "expedition_end", exp=exp, outcome=outcome,
                     turns=io._turn, level=p.level, hp=p.health,
                     tiles=len(io._tiles))
            level = p.level
            if getattr(p, "won", False):
                exp = p.expeditions_completed
                p.save_profile(pf)
                profile = Apocrysis.load_profile(pf)
            else:
                p.save_profile(pf)
                profile = Apocrysis.load_profile(pf)
    rec.emit(0, "campaign_end", reason="complete", level=level)


# ------------------------------------------------------------- report
_MOVE = set("nsew")
_RECOVER = {"eat", "drink", "med", "rest"}
_SLOW_TERRAIN = {"water", "swamp"}


def _turn_category(e):
    a = e.get("action")
    if a in _MOVE:
        return "revisiting" if e.get("revisit", 1) > 1 else "moving (new tile)"
    if a == "search":
        return "searching"
    if a in _RECOVER:
        return "recovering"
    return "other"


def report(events):
    turns = [e for e in events if e["event"] == "turn"]
    combats = [e for e in events if e["event"] == "combat"]
    decisions = [e for e in events if e["event"] == "combat_decision"]
    trans = [e for e in events if e["event"] == "state_transition"]
    res = [e for e in events if e["event"] == "resource"]
    exp_end = [e for e in events if e["event"] == "expedition_end"]
    camp_end = [e for e in events if e["event"] == "campaign_end"]

    key = lambda e: (e["campaign"], e["run"])
    by_run = defaultdict(list)
    for e in turns:
        by_run[key(e)].append(e)
    for v in by_run.values():
        v.sort(key=lambda e: e["turn"])
    combat_turns = {(key(e), e["turn"]) for e in combats}

    L = ["=" * 70, " APOCRYSIS TELEMETRY  -  where did the turns go?", "=" * 70]
    nc = len({e["campaign"] for e in events})
    done = sum(1 for e in camp_end if e.get("reason") == "complete")
    L.append(f" campaigns: {nc}   completed: {done}   expeditions: {len(exp_end)}"
             f"   turns: {len(turns)}")
    oc = Counter(e["outcome"] for e in exp_end)
    L.append(" expedition outcomes: " + "  ".join(f"{k} {v}" for k, v in oc.most_common()))
    tpe = [len(v) for v in by_run.values()]
    if tpe:
        L.append(f" turns / expedition: median {statistics.median(tpe):.0f}"
                 f"  (min {min(tpe)}  max {max(tpe)})")

    # ---------- WHERE THE TURNS WENT ----------
    L.append("\n WHERE THE TURNS WENT")
    cat = Counter()
    for e in turns:
        c = "in combat" if (key(e), e["turn"]) in combat_turns else _turn_category(e)
        cat[c] += 1
    tot = sum(cat.values()) or 1
    for c in ("moving (new tile)", "revisiting", "searching", "recovering",
              "in combat", "other"):
        L.append(f"   {c:<20} {cat.get(c, 0):>6}  ({100*cat.get(c, 0)//tot}%)")
    slow = sum(1 for e in turns if e.get("action") in _MOVE and e["terrain"] in _SLOW_TERRAIN)
    L.append(f"   ...of which slow-terrain (water/swamp) moves: {slow}")

    # ---------- OBJECTIVE LIFECYCLE ----------
    objt = [e for e in events if e["event"] == "objective_transition"]
    ostates = Counter(e.get("obj_state") for e in turns if e.get("obj_state"))
    if ostates:
        L.append("\n OBJECTIVE LIFECYCLE (turn-share)")
        ot = sum(ostates.values()) or 1
        for s in ("active", "distracted", "reminder", "urgent", "complete"):
            L.append(f"   {s:<12} {ostates.get(s, 0):>6}  ({100*ostates.get(s, 0)//ot}%)")
        tc = Counter((e["frm"], e["to"]) for e in objt)
        L.append("   transitions: " + ", ".join(
            f"{a or '·'}→{b} ×{n}" for (a, b), n in tc.most_common()))
        rem = [e for e in objt if e["to"] == "reminder"]
        urg = [e for e in objt if e["to"] == "urgent"]
        if rem:
            L.append(f"   REMINDER fired {len(rem)}× "
                     f"(median {statistics.median([e['turns_since_progress'] for e in rem]):.0f} "
                     f"turns since last progress)")
        if urg:
            L.append(f"   URGENT fired {len(urg)}× "
                     f"(median {statistics.median([e['turns_since_progress'] for e in urg]):.0f} "
                     f"turns since last progress)")
        # did the reminder/urgent work? turns from a reminder/urgent
        # firing to the next 'active' (back on track)
        back = [e for e in objt if e["frm"] in ("distracted", "reminder", "urgent")
                and e["to"] == "active"]
        L.append(f"   returned to ACTIVE after a stall: {len(back)}×")

    # ---------- TIME / TERRAIN ----------
    L.append("\n TIME / TERRAIN  (turns · in-game min · min per move · what happened there)")
    t_turns, t_min, t_moves, t_search, t_combat, t_recover, t_revisit = \
        (Counter() for _ in range(7))
    for run in by_run.values():
        for i, e in enumerate(run):
            terr = e["terrain"]
            t_turns[terr] += 1
            a = e.get("action")
            if a in _MOVE:
                t_moves[terr] += 1
                if e.get("revisit", 1) > 1:
                    t_revisit[terr] += 1
            elif a == "search":
                t_search[terr] += 1
            elif a in _RECOVER:
                t_recover[terr] += 1
            if (key(e), e["turn"]) in combat_turns:
                t_combat[terr] += 1
            # dt_min on the NEXT turn is the cost of this turn's action
            if i + 1 < len(run) and run[i + 1].get("dt_min"):
                t_min[terr] += run[i + 1]["dt_min"]
    L.append(f"   {'terrain':<12} {'turns':>6} {'min':>7} {'min/move':>9} "
             f"{'moves':>6} {'srch':>5} {'cbt':>4} {'rest':>5} {'revis':>6}")
    for terr, n in t_turns.most_common():
        mpm = t_min[terr] / t_moves[terr] if t_moves[terr] else 0
        L.append(f"   {terr:<12} {n:>6} {t_min[terr]:>7} {mpm:>9.0f} "
                 f"{t_moves[terr]:>6} {t_search[terr]:>5} {t_combat[terr]:>4} "
                 f"{t_recover[terr]:>5} {t_revisit[terr]:>6}")

    # ---------- MOVEMENT ----------
    moves = sum(1 for e in turns if e.get("action") in _MOVE)
    revis = sum(1 for e in turns if e.get("action") in _MOVE and e.get("revisit", 1) > 1)
    uniq = [e["unique_tiles"] if "unique_tiles" in e else None for e in exp_end]
    L.append(f"\n MOVEMENT: {moves} moves   {revis} onto a revisited tile "
             f"({100*revis//max(1,moves)}%)   "
             f"{sum(1 for e in turns if e.get('action')=='search')} searches   "
             f"{sum(1 for e in turns if e.get('action')=='rest')} rests")
    dist = defaultdict(int)
    for e in turns:
        dist[key(e)] = max(dist[key(e)], e["dist_from_spawn"])
    if dist:
        L.append(f"   max distance from spawn / expedition (median): "
                 f"{statistics.median(dist.values()):.0f} tiles   "
                 f"(travel:reach ratio = moves / that = "
                 f"{moves / max(1, sum(dist.values())):.1f}x)")

    # ---------- SURVIVAL STATE ----------
    L.append("\n SURVIVAL STATE (turn-share)")
    for axis, bands in (("hp_band", ["healthy", "wounded", "critical"]),
                        ("hunger_band", ["fed", "hungry", "starving"]),
                        ("fatigue_band", ["rested", "fatigued", "exhausted"])):
        c = Counter(e[axis] for e in turns)
        tt = sum(c.values()) or 1
        L.append(f"   {axis.split('_')[0]:<9} "
                 + "  ".join(f"{b} {100*c[b]//tt}%" for b in bands))
    tc = Counter((e["axis"], e["frm"], e["to"]) for e in trans)
    L.append("   transitions: " + ", ".join(
        f"{frm}→{to} ×{n}" for (ax, frm, to), n in tc.most_common(6)))

    # ---------- RESOURCES ----------
    L.append("\n RESOURCES")
    for kind in ("food", "water"):
        f = [e for e in res if e["kind"] == kind and e["op"] == "found"]
        c = [e for e in res if e["kind"] == kind and e["op"] == "consumed"]
        src = Counter(e.get("source") for e in f)
        empty = sum(1 for e in turns if e.get(kind, 1) == 0)
        L.append(f"   {kind:<6} found {len(f)} ({dict(src)})   "
                 f"consumed {len(c)} (~{sum(e['qty'] or 0 for e in c)} units)   "
                 f"turns at 0 in pack: {empty}")
    rests = [e for e in res if e["kind"] == "fatigue" and e["op"] == "rest"]
    blds = [e for e in res if e["kind"] == "fatigue" and e["op"] == "building_recover"]
    L.append(f"   fatigue recovery: {len(rests)} rests "
             f"(~{statistics.median([e['qty'] for e in rests]):.0f} each)  "
             if rests else "   fatigue recovery: 0 rests  ")
    L[-1] += f"{len(blds)} building-recover events"

    # ---------- COMBAT ----------
    L.append(f"\n COMBAT  ({len(combats)} encounters)")
    zc = Counter(_base(e["zombie"]) for e in combats)
    L.append("   composition: " + "  ".join(f"{k} {v}" for k, v in zc.most_common()))
    outc = Counter(e["outcome"] for e in combats)
    L.append("   outcomes:    " + "  ".join(f"{k} {v}" for k, v in outc.most_common())
             + f"   forced (escape failed): {sum(1 for e in combats if e['forced_fight'])}")
    dealt = sum(e["dmg_dealt"] for e in combats)
    taken = sum(e["dmg_taken"] for e in combats)
    L.append(f"   damage: dealt {dealt}   received {taken}")

    L.append("\n   per zombie type (fights · dmg dealt/taken · rounds):")
    byz = defaultdict(list)
    for e in combats:
        byz[_base(e["zombie"])].append(e)
    for z, es in sorted(byz.items(), key=lambda kv: -len(kv[1])):
        f = [e for e in es if e["decision"] == "fight" or e["forced_fight"]]
        rr = [e["rounds"] for e in f if e["rounds"]]
        L.append(f"     {z:<16} {len(f):>3}f  dealt {sum(e['dmg_dealt'] for e in f):>4} "
                 f"taken {sum(e['dmg_taken'] for e in f):>4}  "
                 f"{statistics.mean(rr):.1f}r" if rr else
                 f"     {z:<16} {len(f):>3}f  (no rounds recorded)")

    L.append("\n   per weapon (fights won · avg HP lost · avg rounds · total dealt):")
    byw = defaultdict(list)
    for e in combats:
        if e["decision"] == "fight" or e["forced_fight"]:
            byw[e["weapon"] or "bare hands"].append(e)
    for w, es in sorted(byw.items(), key=lambda kv: -len(kv[1])):
        wins = sum(1 for e in es if e["outcome"] == "win")
        loss = statistics.mean([e["dmg_taken"] for e in es]) if es else 0
        rr = [e["rounds"] for e in es if e["rounds"]]
        L.append(f"     {w:<18} {wins}/{len(es):<3}  {loss:>5.0f} HP  "
                 f"{(statistics.mean(rr) if rr else 0):.1f}r  "
                 f"{sum(e['dmg_dealt'] for e in es)} dealt")

    # ---------- DECISION vs FORECAST ----------
    L.append("\n DECISION vs FORECAST")
    if decisions:
        mm = sum(1 for d in decisions if d["mismatch"])
        L.append(f"   decisions: {len(decisions)}   policy mismatch: {mm} "
                 f"({100*mm//len(decisions)}%)")
        for tier in ("EXTREME", "SEVERE", "HIGH", "MODERATE", "LOW"):
            ds = [d for d in decisions if (d["threat"] or "").upper() == tier]
            if not ds:
                continue
            fought = sum(1 for d in ds if d["decision"] == "fight")
            L.append(f"   {tier:<9} n={len(ds):<3}  fought {100*fought//len(ds)}%   "
                     f"evaded {100*(len(ds)-fought)//len(ds)}%")
        dcs = [e for e in combats if e["outcome"] == "death"]
        bad = sum(1 for e in dcs if e["decision"] == "fight"
                  and (e["threat"] or "").upper() in ("EXTREME", "SEVERE"))
        L.append(f"   deaths after fighting an EXTREME/SEVERE: {bad} / {len(dcs)}")
    L.append("=" * 70)
    return "\n".join(L)


def _base(name):
    return (name or "Zombie").replace("Elite ", "")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--campaigns", type=int, default=5)
    ap.add_argument("--policy", default="explorer",
                    choices=["random", "survival", "explorer", "resource", "objective"])
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--max-turns", type=int, default=600)
    ap.add_argument("--jsonl", default=None, help="append the full event trace here")
    args = ap.parse_args()

    rec = Recorder(args.jsonl)
    try:
        for c in range(args.campaigns):
            rec.campaign = c + 1
            run_campaign(rec, args.policy, args.seed + c * 1000,
                         max_turns=args.max_turns)
            print(f"  campaign {c+1}/{args.campaigns} done "
                  f"({len(rec.events)} events)")
    finally:
        rec.close()

    print("\n" + report(rec.events))
    if args.jsonl:
        print(f"\n full event trace -> {args.jsonl}")


if __name__ == "__main__":
    main()
