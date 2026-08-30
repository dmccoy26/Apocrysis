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

    def _resource_line(self, s):
        t = self._turn
        m = _FOUND_QTY.match(s)
        if m:
            self.rec.emit(t, "resource", kind=m.group(1), op="found",
                          qty=int(m.group(2)))
            return
        m = _FOUND.match(s)
        if m:
            self.rec.emit(t, "resource", kind=m.group(1), op="found", qty=None)
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
        p = self.player
        pos = p.current_position
        if self._spawn is None:
            self._spawn = pos
        self._tiles.add(pos)
        cell = p.map[pos[1]][pos[0]]
        terrain = cell.get("terrain") if isinstance(cell, dict) else "zombie-tile"
        snap = {
            "turn": self._turn, "day": p.day,
            "phase": getattr(p, "day_phase", "night" if p.is_night else "day"),
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
        self._last = snap
        return snap

    def _begin_combat(self, per, interactive):
        if self._pending_combat is not None:
            self._flush_combat()
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
def report(events):
    turns = [e for e in events if e["event"] == "turn"]
    combats = [e for e in events if e["event"] == "combat"]
    decisions = [e for e in events if e["event"] == "combat_decision"]
    trans = [e for e in events if e["event"] == "state_transition"]
    exp_end = [e for e in events if e["event"] == "expedition_end"]
    camp_end = [e for e in events if e["event"] == "campaign_end"]

    L = []
    L.append("=" * 64)
    L.append(" APOCRYSIS TELEMETRY")
    L.append("=" * 64)
    nc = len({e["campaign"] for e in events})
    done = sum(1 for e in camp_end if e.get("reason") == "complete")
    L.append(f" campaigns: {nc}   completed: {done}   "
             f"expeditions: {len(exp_end)}")
    oc = Counter(e["outcome"] for e in exp_end)
    L.append(f" expedition outcomes: " + "  ".join(f"{k} {v}" for k, v in oc.most_common()))

    # --- environment ---
    L.append("\n ENVIRONMENT")
    terr = Counter(e["terrain"] for e in turns)
    enc_terr = Counter(e.get("terrain") for e in combats)
    L.append(f"   {'terrain':<14} {'turns':>6} {'encounters':>11}")
    for t, n in terr.most_common():
        L.append(f"   {t:<14} {n:>6} {enc_terr.get(t, 0):>11}")
    # max distance from spawn, per expedition
    per_exp = defaultdict(int)
    for e in turns:
        per_exp[(e["campaign"], e["run"])] = max(
            per_exp[(e["campaign"], e["run"])], e["dist_from_spawn"])
    if per_exp:
        L.append(f"   max distance from spawn / expedition (median): "
                 f"{statistics.median(per_exp.values()):.0f} tiles")

    # --- survival state ---
    L.append("\n SURVIVAL STATE (turn-share)")
    for axis, bands in (("hp_band", ["healthy", "wounded", "critical"]),
                        ("hunger_band", ["fed", "hungry", "starving"]),
                        ("fatigue_band", ["rested", "fatigued", "exhausted"])):
        c = Counter(e[axis] for e in turns)
        tot = sum(c.values()) or 1
        L.append("   " + "  ".join(f"{b} {100*c[b]//tot}%" for b in bands))
    tc = Counter((e["axis"], e["frm"], e["to"]) for e in trans)
    L.append("   transitions: " + ", ".join(
        f"{frm}→{to} ×{n}" for (ax, frm, to), n in tc.most_common(6)))

    # --- combat ---
    L.append(f"\n COMBAT  ({len(combats)} encounters)")
    zc = Counter(_base(e["zombie"]) for e in combats)
    L.append("   composition: " + "  ".join(f"{k} {v}" for k, v in zc.most_common()))
    outc = Counter(e["outcome"] for e in combats)
    L.append("   outcomes:    " + "  ".join(f"{k} {v}" for k, v in outc.most_common()))
    forced = sum(1 for e in combats if e["forced_fight"])
    L.append(f"   forced fights (escape failed): {forced}")

    # --- weapon performance ---
    L.append("\n WEAPON PERFORMANCE (fights won / avg HP lost / avg rounds)")
    byw = defaultdict(list)
    for e in combats:
        if e["decision"] == "fight" or e["forced_fight"]:
            byw[e["weapon"] or "bare hands"].append(e)
    for w, es in sorted(byw.items(), key=lambda kv: -len(kv[1])):
        wins = sum(1 for e in es if e["outcome"] == "win")
        loss = statistics.mean([e["dmg_taken"] for e in es]) if es else 0
        rnds = statistics.mean([e["rounds"] for e in es if e["rounds"]]) if any(e["rounds"] for e in es) else 0
        L.append(f"   {w:<18} {wins}/{len(es):<3}  {loss:>5.0f} HP   {rnds:.1f} rounds")

    # --- decision / forecast mismatch ---
    L.append("\n DECISION vs FORECAST")
    if decisions:
        mm = sum(1 for d in decisions if d["mismatch"])
        L.append(f"   total decisions: {len(decisions)}   "
                 f"policy mismatch: {mm} ({100*mm//len(decisions)}%)")
        for tier in ("EXTREME", "SEVERE", "HIGH", "MODERATE", "LOW"):
            ds = [d for d in decisions if (d["threat"] or "").upper() == tier]
            if not ds:
                continue
            fought = sum(1 for d in ds if d["decision"] == "fight")
            L.append(f"   {tier:<9} n={len(ds):<3}  fought {fought} "
                     f"({100*fought//len(ds)}%)   evaded {len(ds)-fought}")
        # deaths that followed a "should evade" fight
        death_combats = [e for e in combats if e["outcome"] == "death"]
        bad = sum(1 for e in death_combats
                  if e["decision"] == "fight"
                  and (e["threat"] or "").upper() in ("EXTREME", "SEVERE"))
        L.append(f"   deaths after fighting an EXTREME/SEVERE: {bad} / {len(death_combats)}")
    L.append("=" * 64)
    return "\n".join(L)


def _base(name):
    return (name or "Zombie").replace("Elite ", "")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--campaigns", type=int, default=5)
    ap.add_argument("--policy", default="explorer",
                    choices=["random", "survival", "explorer"])
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
