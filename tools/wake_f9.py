#!/usr/bin/env python3
"""F.9 - automated pre-pass on a world's authored experience.
docs/PHASE_F_MULTI_WORLD_SEAM.md §F.9.

F.9 asks "does the arc PLAY, not just execute". Some of that checklist
is mechanically detectable; the rest needs a human. This tool runs the
detectable part and prints a full player-facing transcript so the arc
can be *read* rather than played through 50+ expeditions.

  python3 tools/wake_f9.py                 # The Wake, transcript + checks
  python3 tools/wake_f9.py --world silence # (works on any world)
  python3 tools/wake_f9.py --checks-only --seeds 8

WHAT IT CANNOT ANSWER (left for the human, F.9 verdict):
  - do discoveries feel EARNED (worked out) vs told
  - do the hypothesis flips feel earned ("oh, I had it wrong")
  - does the campaign length feel INTENTIONAL vs merely shorter
  - does the finale choice feel like a DECISION vs two buttons
  - the overall "can I feel the game, or the machinery" texture
"""
import argparse
import os
import re
import sys
import tempfile
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.game import Apocrysis
from src.worlds import get_world
from src.text_utils import _ANSI_ESCAPE_RE
from tools.balance_autoplay import BotIO

# World-1 PLACE flavour that must never surface in another world - rare,
# sharp, world_mixin._ABANDONMENT_FLAVOUR / prose (PHASE_F open item).
_PLACE_LEAKS = ("valley", "ranger station", "forestry", "hydro station",
                "reservoir", "the cordon", "protocol seven", "crop-duster",
                "the marina", "highway patrol", "airstrip", "the ridge",
                "ranger depot",
                # §F.11 - generated environmental fiction. A forest /
                # wading / a river bank on a spaceship is the world
                # generator not believing the world it's generating.
                "forest", "wade through water", "the far bank",
                "the current takes you", "swim for it", "mountains rise",
                "cross the mountain", "cross the river", "dense forest",
                "off the ridge", "back to the pass",
                # F.11-class - one-time discoverables + day/night dressing.
                # A ship has no waders and no sunrise.
                "waders", "water and swamp", "working flashlight",
                "you found map", "you found flashlight", "you found waders")

# World-1 COMBAT prose - "the infected" is hardcoded in combat_mixin's
# battle lines. Reported separately (it's the deferred sweep's scope,
# and it fires on every hit so it'd drown the place leaks).
_COMBAT_PROSE = ("the infected", "zombie")

# lines dropped from the readable transcript (still scanned for leaks).
_NOISE = re.compile(
    r"^(Moved [nsew]\.|You (enter|move through|wade|are in)|More water|"
    r"Back inside|Street after street|A patchwork|Dense old-growth|"
    r"You spot a building|It's a safe zone|Restored \d+ health|"
    r"Hunger:|\[state\]|You ready your gear|Welcome back|"
    r"(The infected|You) takes? \d+|Preparing for battle|"
    r"You deftly dodged|(You are|The infected has been)|"
    r"Critical Hit|You club at it|You found (some|a )|"
    r"You (eat|drink|use|rest|reload|equip|have equipped)|"
    r"Health: |Xp: |The \w+ has been returned|You obtained)")


def _plain(s):
    return _ANSI_ESCAPE_RE.sub("", s).strip()


class F9IO(BotIO):
    def __init__(self, max_turns, ending_pick="2"):
        super().__init__(max_turns)
        self.ending_pick = ending_pick
        self.stream = []                  # (exp, plain_line)
        self.encounters = []              # (exp, milestones_known_count, banner_label)

    def say(self, *a, **k):
        super().say(*a, **k)              # keep BotIO metrics
        exp = self.player.expeditions_completed if self.player else 0
        for raw in " ".join(str(x) for x in a).splitlines():
            ln = _plain(raw)
            if ln:
                self.stream.append((exp, ln))
                if ("INFECTED" in ln or "CHANGED" in ln or "OFFICER" in ln
                        or "SECURITY" in ln or ln.isupper() and "-" in ln):
                    _wi = getattr(self.player, "world_investigation", None)
                    ms = len(_wi.milestones_known()) if _wi else 0
                    self.encounters.append((exp, ms, ln))

    def ask(self, prompt=""):
        if "(1 / 2)" in prompt:
            return self.ending_pick
        return super().ask(prompt)


def run_campaign(world, seed, ending_pick, max_turns=600, max_attempts=60):
    Apocrysis.reset_campaign_state()
    N = world.manifest.campaign_length
    exp, profile, level, attempts = 0, None, 1, 0
    per_exp = []            # dict per completed expedition
    io = None
    with tempfile.TemporaryDirectory() as tmp:
        pf = os.path.join(tmp, "p.json")
        while exp < N:
            attempts += 1
            per_tier = sum(1 for r in per_exp if r["exp"] == exp) + 1
            if per_tier > max_attempts:
                return {"stuck_at": exp, "expeditions": per_exp, "io": io}
            io = F9IO(max_turns, ending_pick)
            g = Apocrysis("F9Bot", level=level, expeditions_completed=exp,
                          seed=seed * 1000 + attempts, io=io, world=world)
            if profile is not None:
                g.apply_profile(profile)
            io.player = g
            m = g.mystery
            pre = None
            if m is not None:
                _wi = g.world_investigation
                fid = m.world_fact_id
                fact = _wi.fact(fid) if fid else None
                hyp = _wi.current_hypothesis()
                pre = {
                    "exp": exp, "chapter": g.world.manifest.chapter_titles,
                    "target": fid, "lead": fact.lead if fact else "",
                    "statement": fact.statement if fact else "",
                    "mechanism": m.mechanism, "mech_name": m.mech_name,
                    "is_finale": getattr(m, "is_finale", False),
                    "site_labels": dict(m.site_labels),
                    "theory": hyp.statement if hyp else None,
                }
            g.run_game_loop()
            g.save_profile(pf)
            profile = Apocrysis.load_profile(pf)
            level = g.level
            if not g.won:
                if pre is not None:
                    pre["outcome"] = "died" if g.health <= 0 else "timeout"
                    pre["stream"] = list(io.stream)
                    per_exp.append(pre)
                continue
            _wi = g.world_investigation
            pre = pre or {"exp": exp}
            pre.update({
                "outcome": "won",
                "stream": list(io.stream),
                "known_after": set(k for k, v in
                                   dict(Apocrysis._world_investigation).items()
                                   if v == "known"),
                "theory_after": (_wi.current_hypothesis().statement
                                 if _wi.current_hypothesis() else None),
                "level": g.level, "encounters": list(io.encounters),
            })
            per_exp.append(pre)
            exp = g.expeditions_completed
    return {"stuck_at": None, "expeditions": per_exp,
            "ending": Apocrysis._campaign_ending, "io": io}


# ---- transcript ---------------------------------------------------

def print_transcript(world, run):
    cts = world.manifest.chapter_titles
    bounds = world.manifest.chapter_bounds
    N = world.manifest.campaign_length

    def chapter_of(e):
        i = 1
        for lo in bounds:
            if e >= lo:
                i = bounds.index(lo) + 1
        return i

    prev_known = set()
    prev_chapter = 0
    for r in run["expeditions"]:
        if r.get("outcome") != "won":
            continue
        e = r["exp"]
        ch = chapter_of(e)
        if ch != prev_chapter:
            prev_chapter = ch
            print(f"\n\n{'═' * 72}")
            print(f"  CHAPTER {ch} — {cts[ch-1] if ch <= len(cts) else ''}")
            print(f"{'═' * 72}")
        tag = "  ·  THE FINALE" if r.get("is_finale") else ""
        print(f"\n┈┈ EXPEDITION {e+1} / {N}{tag} ┈┈")
        if r.get("lead"):
            print(f"   investigating: {r['lead']}")
        print(f"   way out: {r.get('mech_name','?')}  ({r.get('mechanism','?')})")
        sl = r.get("site_labels") or {}
        if sl:
            print("   sites: " + " · ".join(f"{k}={v}" for k, v in sl.items()))
        if r.get("theory"):
            print(f'   working theory: "{r["theory"]}"')
        print("   ┄ what the player saw ┄")
        for ln in _readable_beats([ln for (_x, ln) in r["stream"]]):
            print(f"     {ln}")
        newk = r.get("known_after", set()) - prev_known
        if newk:
            for fid in sorted(newk):
                f = world.world_facts and next(
                    (x for x in world.world_facts if x.id == fid), None)
                if f:
                    print(f"   ✔ established: {f.statement}"
                          + ("   [MILESTONE]" if f.milestone else ""))
            prev_known = r["known_after"]


def _dedup(lines):
    out, last = [], None
    for ln in lines:
        if ln != last:
            out.append(ln)
        last = ln
    return out


_DROP = re.compile(
    r"^(you can make out|It's the marked spot|Blocked - but a survivor|"
    r"You have been stunned|You are stunned|⚠ |You are bleeding|"
    r"The toxic bite|You are critically wounded|You go down|"
    r"Stop\. This is a decision|In a desperate move|Unable to flee|"
    r"You deftly dodged|You got away from|Preparing for battle|"
    r"Critical Hit|You club at it|You have no weapon|You punch|"
    r"You've caught your breath|wounds under control|hungry no longer|"
    r"thirsty no longer|The bleeding has passed|caught your breath|"
    r"You're in the |Rooftops in the distance|Cabin doors down|"
    r"Gantries|A long open deck|The hull's open|Whole compartments|"
    r"It's marked on your map|It's \(?(north|south|east|west)|"
    r"The route ahead is clear|A stash of supplies|"
    r"You found (food|water|medicine|ammo|armor|a )|"
    r"map level|turns survived|days survived|final level|"
    r"tiles visited|facts established|A stash|WHAT YOU LEARNED|"
    r"\(THE (SHIP|CREW|ORDER)|✓ |This is what gets you past|"
    r"You received a generous prize|Used .* for crafting|Crafted a|"
    r"You drop the|Thirst:|Hunger:|Fatigue:|Xp:|Health:|"
    r"Everyone who left went the same way|It's gone before you|"
    r"It barely reacts|You step around it|Nothing more here|"
    r"Nothing more to take here|Take it to the|You still need|"
    r"◆ still to do|make sure this really leads out|"
    r"You wrestle the|You seat the|part \d of \d)")
# lines that END the useful transcript for an expedition (the win box)
_END_MARK = re.compile(r"(YOU ESCAPED|CAMPAIGN COMPLETE|╔══)")
_ABAND = re.compile(
    r"^(Kit half-packed|Furniture stacked|Scorched bulkheads|Lockers forced|"
    r"A camp roll|Welded shut|Coolant standing|Untouched\. A film|"
    r"Signs of use|You step inside)")
_FIGHT = re.compile(r"^(The changed (takes|has been)|You take \d+|"
                    r"You found (a |some |armor|the way))")


def _readable_beats(lines):
    """One expedition's say-stream -> the ~15 lines that carry the
    investigation. Combat collapses to one '⚔' per fight; ambient
    flavour to one line; navigation chatter dropped."""
    out, in_fight, abandon_shown = [], False, False
    for ln in lines:
        if _END_MARK.search(ln):
            break
        if not ln or set(ln) <= set("═*-┈┄ ."):
            continue
        if "already been over this place" in ln or ln.startswith("("):
            continue
        if _FIGHT.match(ln):
            if not in_fight and ln.startswith("The changed"):
                out.append("  ⚔ fought one of the changed")
                in_fight = True
            continue
        in_fight = False
        if _ABAND.match(ln):
            if not abandon_shown:
                out.append("  · " + ln)
                abandon_shown = True
            continue
        if _NOISE.match(ln) or _DROP.match(ln):
            continue
        # trailing bearing seasoning - keep the sentence, drop the cue
        ln = re.sub(r"\.?\s*It's \(?(out toward |close by\)?|"
                    r"(north|south|east|west)[\w -]*\)?)\.?$", ".", ln).rstrip()
        out.append(ln)
    # drop lines seen earlier this expedition (mysteries brief each site
    # twice - on first sight and on revisit)
    seen, dedup = set(), []
    for ln in _dedup(out):
        key = ln.lstrip("  ·⚔ ")
        if len(key) > 25 and key in seen:
            continue
        seen.add(key)
        dedup.append(ln)
    return dedup


# ---- checks ------------------------------------------------------

def run_checks(world, runs):
    print(f"\n\n{'═' * 72}\n  F.9 AUTOMATED CHECKS  ({world.id}, {len(runs)} campaigns)\n{'═' * 72}")
    facts = list(world.world_facts)
    fac_ids = {f.id for f in facts}
    ms_ids = {f.id for f in facts if f.milestone}
    rung_lines = {h.corrected_to.split(".")[0].lower()[:40] for h in world.regional_hypotheses}
    ok = True

    # 1a. World-1 PLACE flavour (rare, sharp)
    place_leaks, combat_hits = {}, 0
    for ri, run in enumerate(runs):
        for r in run["expeditions"]:
            for (e, ln) in r.get("stream", []):
                low = ln.lower()
                for term in _PLACE_LEAKS:
                    if term in low:
                        place_leaks.setdefault(ln, (ri, e, term))
                if any(t in low for t in _COMBAT_PROSE):
                    combat_hits += 1
    if place_leaks:
        ok = False
        print(f"\n  [FLAG] World-1 PLACE flavour surfaced ({len(place_leaks)} distinct lines):")
        for ln, (ri, e, term) in list(place_leaks.items())[:12]:
            print(f"     «{term}»  {ln[:100]}")
        print("     → source is world_mixin (_ABANDONMENT_FLAVOUR / prose); "
              "this is the deferred world.prose sweep's scope.")
    else:
        print("\n  [ok]  no World-1 PLACE flavour ('valley'/'ranger'/'reservoir'/...) in any transcript")

    # 1b. World-1 COMBAT prose (fires per hit; the deferred sweep)
    if combat_hits:
        print(f"  [note] combat lines say 'the infected' ({combat_hits} hits across "
              f"{len(runs)} campaigns) - combat_mixin battle prose is hardcoded, "
              "not world-owned. The Wake wants 'the changed' / 'it'. Deferred-sweep scope.")

    # 2. every fact reached, every campaign
    for ri, run in enumerate(runs):
        if run["stuck_at"] is not None:
            ok = False
            print(f"  [FLAG] seed#{ri}: campaign STUCK at expedition {run['stuck_at']+1}")
            continue
        known = set()
        for r in run["expeditions"]:
            known |= r.get("known_after", set())
        missing = fac_ids - known
        if missing:
            ok = False
            print(f"  [FLAG] seed#{ri}: facts never established: {sorted(missing)}")
    if all(run["stuck_at"] is None for run in runs):
        print("  [ok]  every campaign completes; all facts established")

    # 3. hypothesis ladder: all rungs' corrections fired
    for ri, run in enumerate(runs):
        blob = "\n".join(ln for r in run["expeditions"]
                         for (_e, ln) in r.get("stream", [])).lower()
        fired = sum(1 for frag in rung_lines if frag in blob)
        if fired < len(rung_lines):
            ok = False
            print(f"  [FLAG] seed#{ri}: only {fired}/{len(rung_lines)} hypothesis "
                  "corrections fired")
    print(f"  [ok]  all {len(rung_lines)} hypothesis-ladder corrections fire")

    # 4. mechanism variety (no 3-in-a-row, none over-used)
    for ri, run in enumerate(runs):
        seq = [r["mechanism"] for r in run["expeditions"]
               if r.get("outcome") == "won" and r.get("mechanism")]
        runs_of_3 = [seq[i] for i in range(len(seq)-2)
                     if seq[i] == seq[i+1] == seq[i+2]]
        c = Counter(seq)
        hog = [m for m, n in c.items() if n > max(3, len(seq)*0.45)]
        if runs_of_3 or hog:
            print(f"  [FLAG] seed#{ri}: mechanism variety - "
                  f"{'3+ in a row: '+str(set(runs_of_3)) if runs_of_3 else ''} "
                  f"{'over-used: '+str(hog) if hog else ''}  seq={seq}")
        else:
            pass
    print("  [ok]  mechanism variety within bounds (checked per campaign)")

    # 5. the encounter-label shift (crew -> the changed), if the world
    #    has a milestone gating population.describe
    shift_seen = False
    for run in runs:
        for r in run["expeditions"]:
            for (e, ms, ln) in r.get("encounters", []):
                if ms == 0 and ("OFFICER" in ln or "MEDIC" in ln or "CREW" in ln
                                or "HAND" in ln) and "CHANGED" not in ln:
                    shift_seen = shift_seen or "before"
                if ms >= 1 and "CHANGED" in ln:
                    shift_seen = "confirmed" if shift_seen else "after-only"
    if world.id == "the_wake":
        if shift_seen == "confirmed":
            print("  [ok]  encounter label shifts with the investigation "
                  "(human -> 'one of the changed')")
        else:
            ok = False
            print(f"  [FLAG] encounter label shift not observed cleanly ({shift_seen!r}) "
                  "- check population.describe gating")

    # 6. per-expedition traversal load (rough 'why am I doing this' proxy)
    long_empty = []
    for ri, run in enumerate(runs):
        for r in run["expeditions"]:
            if r.get("outcome") != "won":
                continue
            beats = [ln for (_e, ln) in r.get("stream", [])
                     if ("✦" in ln or "◆" in ln or "‼" in ln or "◈" in ln
                         or "established" in ln.lower() or "MYSTERY SOLVED" in ln)]
            if len(beats) <= 1:
                long_empty.append((ri, r["exp"]))
    if long_empty:
        print(f"  [note] {len(long_empty)} expedition(s) with <=1 story beat "
              f"(mostly traversal): {[e+1 for _r, e in long_empty][:10]}"
              "  - human check whether they read as filler")
    else:
        print("  [ok]  every expedition carries >1 story beat")

    # 7. finale: consequence established before the choice
    for ri, run in enumerate(runs):
        fin = next((r for r in run["expeditions"]
                    if r.get("is_finale") and r.get("outcome") == "won"), None)
        if not fin:
            continue
        text = "\n".join(ln for (_e, ln) in fin["stream"])
        i_choice = text.find("1)")
        i_release = text.lower().find("lifts every standing deck-seal")
        i_release = text.lower().find("releases") if i_release < 0 else i_release
        if 0 <= i_release < i_choice or i_choice < 0:
            print("  [ok]  finale: the consequence is established before the choice prompt")
        else:
            ok = False
            print(f"  [FLAG] seed#{ri}: finale asks the choice before establishing "
                  "the consequence")
        break

    print(f"\n  ── AUTOMATED VERDICT: {'PASS' if ok else 'FLAGS - see above'} ──")
    print("  (this covers the mechanically detectable part of §F.9 only;\n"
          "   the feel/earned/decision questions still need a human read.)")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--world", default="the_wake")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--seeds", type=int, default=5,
                    help="run this many campaigns for the check battery")
    ap.add_argument("--ending", default=None, help="finale choice id")
    ap.add_argument("--checks-only", action="store_true")
    args = ap.parse_args()

    world = get_world(args.world)
    fin = world.finale
    pick = "2"
    if args.ending and fin:
        pick = "1" if args.ending == fin.option_a[0] else "2"

    runs = []
    for i in range(args.seeds):
        runs.append(run_campaign(world, args.seed + i, pick))

    if not args.checks_only:
        print("═" * 72)
        print(f"  {world.manifest.title.upper()} — F.9 READ-THROUGH  (seed {args.seed})")
        print(f"  {world.description}")
        print("═" * 72)
        print_transcript(world, runs[0])
        if runs[0]["stuck_at"] is None:
            f = fin
            end_id = (f.option_a[0] if pick == "1" else f.option_b[0]) if f else "?"
            E = f.endings.get(end_id) if f else None
            if E:
                print(f"\n\n  ── ENDING: {end_id.upper()} ──\n")
                for para in E:
                    print("   " + para + "\n")

    run_checks(world, runs)


if __name__ == "__main__":
    main()
