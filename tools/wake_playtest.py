#!/usr/bin/env python3
"""wake_playtest.py - one bot, two reports for The Wake (World 2).

  COVERAGE  every spine + H1 feature is exercised and reachable across
            many seeded campaigns; anything broken, skipped or
            unreachable is flagged.

  READ      an automated pass at the F.9 / H1 *qualitative* questions
            from the same playthrough data - opening rhythm, the
            ?-airtime question (H1.1), encounter-beat delivery,
            crossing-type differentiation, pacing, endgame convergence.

The bot cannot answer the questions a human answers - does the
capability *arrive*, does `?`->`!` read as a meaning rather than a
flicker. It measures the things those questions depend on, and points
at where the numbers say "a human should look here".

    python3 tools/wake_playtest.py                 # 8 seeds, both reports
    python3 tools/wake_playtest.py --seeds 20
    python3 tools/wake_playtest.py --coverage-only
    python3 tools/wake_playtest.py --seed 100 --seeds 1

COVERAGE is world-agnostic - it reads the spine (sections / level_types
/ markers_need_device) off the manifest, so `--world <id>` will run it
against any future spine world (e.g. The Deep, once Phase 6 exists).
The READ section's opening-rhythm / endgame checks name Wake milestones
and are skipped for other worlds until those are filled in.
"""
import argparse
import os
import statistics
import sys
import tempfile
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.game import Apocrysis
from src.worlds import get_world
from src.sections import (section_name_for, level_type_for, is_encounter_level,
                          campaign_objective_line)
from src.zombies import Zombie
from tools.balance_autoplay import BotIO
from tools.wake_f9 import _plain, _PLACE_LEAKS

_ROLE_FACT = {"closed": "F_CLOSED", "route": "F_ROUTE",
              "require": "F_REQUIRE", "power": "F_POWER"}


# ----------------------------------------------------------------------
# instrumented IO - the F9 bot plus one per-turn state sample
# ----------------------------------------------------------------------
class PlaytestIO(BotIO):
    def __init__(self, max_turns, ending_pick="2"):
        super().__init__(max_turns)
        self.ending_pick = ending_pick
        self.lines = []
        self.samples = []          # per-turn: markers, has_scanner, camp_obj
        self._turn = 0

    def say(self, *a, **k):
        super().say(*a, **k)
        for raw in " ".join(str(x) for x in a).splitlines():
            ln = _plain(raw)
            if ln:
                self.lines.append(ln)

    def ask(self, prompt=""):
        if "(1 / 2)" in prompt:
            return self.ending_pick
        self._sample()
        return super().ask(prompt)

    def _sample(self):
        p = self.player
        if p is None:
            return
        self._turn += 1
        m = getattr(p, "mystery", None)
        markers = {}
        if m is not None:
            for role, xy in m.sites.items():
                if xy:
                    g = _plain(p._mystery_site_mark(*xy) or "")
                    if g in ("?", "!", "+"):
                        markers[role] = g
        try:
            camp = bool(campaign_objective_line(p))
        except Exception:
            camp = False
        self.samples.append({
            "turn": self._turn,
            "markers": markers,
            "has_scanner": bool(getattr(p, "has_scanner", False)),
            "camp_obj": camp,
        })


# ----------------------------------------------------------------------
# one full campaign, instrumented
# ----------------------------------------------------------------------
def run_campaign(world, seed, ending_pick, max_turns=600, max_attempts=60):
    Apocrysis.reset_campaign_state()
    N = world.manifest.campaign_length
    exp, profile, level = 0, None, 1
    exps = []
    with tempfile.TemporaryDirectory() as tmp:
        pf = os.path.join(tmp, "p.json")
        while exp < N:
            tries = sum(1 for r in exps if r["exp"] == exp) + 1
            if tries > max_attempts:
                return {"stuck_at": exp, "exps": exps, "ending": None}
            io = PlaytestIO(max_turns, ending_pick)
            g = Apocrysis("PT", level=level, expeditions_completed=exp,
                          seed=seed * 1000 + tries, io=io, world=world)
            if profile is not None:
                g.apply_profile(profile)
            io.player = g
            scanner_start = bool(getattr(g, "has_scanner", False))
            threat0 = sum(isinstance(c, Zombie) for row in g.map for c in row)
            known0 = set(k for k, v in dict(Apocrysis._world_investigation).items()
                         if v == "known")
            rec = {
                "exp": exp,
                "section": section_name_for(exp, world),
                "ltype": level_type_for(exp, world),
                "archetype": getattr(g, "map_archetype", None),
                "is_finale": getattr(getattr(g, "mystery", None), "is_finale", False),
                "mechanism": getattr(getattr(g, "mystery", None), "mechanism", None),
                "target": getattr(getattr(g, "mystery", None), "world_fact_id", None),
                "had_mystery": getattr(g, "mystery", None) is not None,
                "had_beat": getattr(g, "_encounter_beat", None) is not None,
                "beat_fact": getattr(g, "_encounter_fact", None),
                "had_pickup": getattr(g, "_discovery_pickup", None) is not None,
                "markers_gated_start": g._markers_gated(),
                "scanner_start": scanner_start,
                "threat0": threat0,
            }
            g.run_game_loop()
            g.save_profile(pf)
            profile = Apocrysis.load_profile(pf)
            level = g.level
            blob = "\n".join(io.lines)
            known1 = set(k for k, v in dict(Apocrysis._world_investigation).items()
                         if v == "known")
            rec.update({
                "outcome": ("won" if g.won else
                            "died" if g.health <= 0 else "timeout"),
                "tries_so_far": tries,
                "turns": getattr(g, "turns", 0),
                "fights": blob.count("fought one of the changed")
                          + sum(1 for ln in io.lines
                                if ln.startswith("The changed takes")),
                "new_facts": sorted(known1 - known0),
                "corrections": blob.count("YOU HAD IT WRONG"),
                "beat_seen": bool(getattr(g, "_encounter_beat_seen", False)),
                "pickup_taken": bool(getattr(g, "_discovery_pickup_taken", False)),
                "scanner_end": bool(getattr(g, "has_scanner", False)),
                "tactical_online": "TACTICAL SYSTEM ONLINE" in blob,
                "tactical_contact": "tactical - contact" in blob,
                "beat_prose": _beat_prose_fired(blob, getattr(g, "_encounter_fact", None)),
                "story_beats": sum(1 for ln in io.lines
                                   if any(s in ln for s in ("✦", "◆", "◈", "‼"))),
                "place_leaks": sorted({t for t in _PLACE_LEAKS
                                       if t in blob.lower()}),
                "samples": io.samples,
                "marker_bang_seen": any("!" in s["markers"].values()
                                        for s in io.samples),
                "marker_q_seen": any("?" in s["markers"].values()
                                     for s in io.samples),
                "camp_obj_turn": next((s["turn"] for s in io.samples
                                       if s["camp_obj"]), None),
                "q_to_bang": _q_to_bang(io.samples),
            })
            if rec["outcome"] == "won":
                exp = g.expeditions_completed
            exps.append(rec)
    return {"stuck_at": None, "exps": exps, "ending": Apocrysis._campaign_ending}


def _beat_prose_fired(blob, fid):
    keys = {
        "THE_CHANGED": "that's the crew",
        "ONE_AUTHORIZATION": "one authorization signature",
        "SURVIVORS_ON_A_CLOCK": "arithmetic they finished",
    }
    frag = keys.get(fid)
    return bool(frag and frag in blob.lower())


def _q_to_bang(samples):
    """Per role: turns between the first `?` sample and the first `!`
    sample. None if the role never showed `?`, or showed `!` first."""
    first_q, first_b, out = {}, {}, {}
    for s in samples:
        for role, g in s["markers"].items():
            if g == "?" and role not in first_q:
                first_q[role] = s["turn"]
            if g == "!" and role not in first_b:
                first_b[role] = s["turn"]
    for role, tq in first_q.items():
        tb = first_b.get(role)
        if tb is not None and tb >= tq:
            out[role] = tb - tq
    return out


# ----------------------------------------------------------------------
# COVERAGE
# ----------------------------------------------------------------------
def coverage(world, runs):
    print(f"\n{'═'*70}\n  COVERAGE  ({world.id}, {len(runs)} campaigns)\n{'═'*70}")
    facts = list(world.world_facts)
    fac_ids = {f.id for f in facts}
    ms_ids = {f.id for f in facts if f.milestone}
    n_rungs = len(world.regional_hypotheses)
    sec_names = list(world.manifest.section_names)
    sec_arch = list(world.manifest.section_archetypes)
    completed = [r for r in runs if r["stuck_at"] is None]
    results = []

    def chk(label, bad_seeds):
        """bad_seeds: list of (seed_index, detail) that failed this check."""
        results.append((label, list(bad_seeds)))

    # one entry per campaign, keyed by its list index
    def per_campaign(label, fn):
        bad = []
        for i, r in enumerate(completed):
            d = fn(r)
            if d:
                bad.append((i, d))
        chk(label, bad)

    chk("every campaign completes",
        [(i, f"stuck L{r['stuck_at']+1}") for i, r in enumerate(runs)
         if r["stuck_at"] is not None])

    def _known(r):
        won = [e for e in r["exps"] if e["outcome"] == "won"]
        return set().union(*[set(e["new_facts"]) for e in won]) if won else set()

    per_campaign(f"all {len(fac_ids)} WorldFacts established",
                 lambda r: sorted(fac_ids - _known(r)) or None)
    per_campaign(f"all {len(ms_ids)} milestones established",
                 lambda r: sorted(ms_ids - _known(r)) or None)
    per_campaign(f"all {n_rungs} hypothesis-ladder corrections fire",
                 lambda r: (f"only {sum(e['corrections'] for e in r['exps'] if e['outcome']=='won')}"
                            if sum(e["corrections"] for e in r["exps"]
                                   if e["outcome"] == "won") < n_rungs else None))

    endings = Counter(r["ending"] for r in completed)
    chk("both endings reached",
        [] if len(endings) >= 2 else [(-1, f"only {dict(endings)}")])

    def _won_by_exp(r):
        return {e["exp"]: e for e in r["exps"] if e["outcome"] == "won"}

    per_campaign("sections strictly monotone Bridge -> Main Engineering",
                 lambda r: None if [e["section"] for e in r["exps"] if e["outcome"] == "won"]
                 == sorted([e["section"] for e in r["exps"] if e["outcome"] == "won"],
                           key=sec_names.index) else "out of order")
    per_campaign("all 7 sections visited",
                 lambda r: str(set(sec_names) - {e["section"] for e in r["exps"]
                               if e["outcome"] == "won"}) if set(sec_names) -
                 {e["section"] for e in r["exps"] if e["outcome"] == "won"} else None)
    per_campaign("each expedition renders its section's archetype",
                 lambda r: str([(e["exp"]+1, e["archetype"]) for e in r["exps"]
                               if e["outcome"] == "won" and e["archetype"]
                               != sec_arch[sec_names.index(e["section"])]][:3]) or None
                 if [e for e in r["exps"] if e["outcome"] == "won" and e["archetype"]
                     != sec_arch[sec_names.index(e["section"])]] else None)

    per_campaign("all 3 encounter beats played + fired their authored scene",
                 lambda r: _enc_detail(r))
    per_campaign("every encounter beat established a fact on completion",
                 lambda r: str([e["exp"]+1 for e in _won_by_exp(r).values()
                               if e["ltype"] == "encounter" and not set(e["new_facts"])])
                 or None if [e for e in _won_by_exp(r).values()
                             if e["ltype"] == "encounter" and not set(e["new_facts"])]
                 else None)
    per_campaign("all 6 plain crossings completed (traversal/discovery/quiet)",
                 lambda r: None if len([e for e in _won_by_exp(r).values()
                     if e["ltype"] in ("traversal", "discovery", "quiet")]) == 6
                 else f"{len([e for e in _won_by_exp(r).values() if e['ltype'] in ('traversal','discovery','quiet')])}/6")

    # H1
    per_campaign("L5 helmet: placed -> taken -> TACTICAL SYSTEM ONLINE -> persists",
                 lambda r: _helmet_detail(r))
    per_campaign("pre-helmet: no ADVANCE `!` marker on turn 1 of a fact level",
                 lambda r: _preadvance_detail(r))
    per_campaign("pre-helmet: `?` never appears (no scanner)",
                 lambda r: str([e["exp"]+1 for e in _won_by_exp(r).values()
                               if not e["scanner_start"] and e["marker_q_seen"]]) or None
                 if [e for e in _won_by_exp(r).values()
                     if not e["scanner_start"] and e["marker_q_seen"]] else None)
    per_campaign("post-helmet: `!` markers return",
                 lambda r: None if any(e["marker_bang_seen"] for e in
                     _won_by_exp(r).values() if e["scanner_start"] and e["had_mystery"])
                 else "no ! after the helmet")
    per_campaign("post-helmet: `?` detection appears",
                 lambda r: None if any(e["marker_q_seen"] for e in
                     _won_by_exp(r).values() if e["scanner_start"])
                 else "no ? after the helmet")

    per_campaign("CAMPAIGN objective hidden through L3, shown by L5+",
                 lambda r: _campobj_detail(r))

    # quiet materially calmer (aggregate)
    q_t = [e["threat0"] for r in completed for e in r["exps"]
           if e["ltype"] == "quiet" and e["outcome"] == "won"]
    f_t = [e["threat0"] for r in completed for e in r["exps"]
           if e["ltype"] == "fact" and e["outcome"] == "won"]
    if q_t and f_t:
        m_q, m_f = statistics.mean(q_t), statistics.mean(f_t)
        chk(f"quiet threat materially below a fact level ({m_q:.0f} vs {m_f:.0f})",
            [] if m_q < 0.7 * m_f else [(-1, "not < 70%")])

    leaks = sorted({t for r in runs for e in r["exps"] for t in e["place_leaks"]})
    chk("no World-1 place / vocabulary leak", [] if not leaks else [(-1, str(leaks))])

    ok = True
    for label, bad in results:
        if bad:
            ok = False
            seeds = ", ".join(f"#{i}" if i >= 0 else "" for i, _ in bad).strip(", ")
            det = "; ".join(str(d) for _, d in bad if d)
            print(f"  [FLAG] {label}"
                  + (f"  ({seeds})" if seeds else "")
                  + (f"  - {det}" if det else ""))
        else:
            print(f"  [ok]   {label}")
    print(f"\n  ── COVERAGE: {'PASS' if ok else 'FLAGS - see above'} ──")
    return ok


def _enc_detail(r):
    enc = [e for e in r["exps"] if e["outcome"] == "won" and e["ltype"] == "encounter"]
    if len(enc) != 3:
        return f"{len(enc)}/3 played"
    bad = [e["exp"]+1 for e in enc if not (e["beat_seen"] and e["beat_prose"])]
    return f"scene missing on L{bad}" if bad else None


def _helmet_detail(r):
    won = [e for e in r["exps"] if e["outcome"] == "won"]
    l5 = next((e for e in won if e["had_pickup"]), None)
    if l5 is None:
        return "no pickup placed"
    if not (l5["pickup_taken"] and l5["tactical_online"] and l5["scanner_end"]):
        return (f"L{l5['exp']+1}: taken={l5['pickup_taken']} "
                f"online={l5['tactical_online']} scanner={l5['scanner_end']}")
    return None


def _preadvance_detail(r):
    won = [e for e in r["exps"] if e["outcome"] == "won"]
    bad = []
    for e in won:
        if e["scanner_start"] or not e["had_mystery"] or not e["samples"]:
            continue
        if e["samples"][0]["markers"]:      # any marker on turn 1 = advance
            bad.append(e["exp"] + 1)
    return f"advance markers on L{bad}" if bad else None


def _campobj_detail(r):
    won = {e["exp"]: e for e in r["exps"] if e["outcome"] == "won"}
    early = [e["exp"]+1 for e in won.values() if e["exp"] <= 2 and e["camp_obj_turn"]]
    if early:
        return f"showed too early on L{early}"
    if not any(e["camp_obj_turn"] for e in won.values() if e["exp"] >= 5):
        return "never showed"
    return None


# ----------------------------------------------------------------------
# READ
# ----------------------------------------------------------------------
def read(world, runs):
    print(f"\n\n{'═'*70}\n  READ  (automated pass at the feel questions)\n{'═'*70}")
    completed = [r for r in runs if r["stuck_at"] is None]
    won = [e for r in completed for e in r["exps"] if e["outcome"] == "won"]
    by_exp = defaultdict(list)
    for e in won:
        by_exp[e["exp"]].append(e)

    # -- opening rhythm L1-7 --------------------------------------------
    print("\n  OPENING RHYTHM (L1-7)")
    print("   scheduled types:",
          " ".join(f"L{i+1}:{level_type_for(i, world)[:4]}" for i in range(7)))
    ms_turn = defaultdict(list)
    for e in won:
        for fid in e["new_facts"]:
            f = next((x for x in world.world_facts if x.id == fid), None)
            if f and f.milestone:
                ms_turn[fid].append(e["exp"] + 1)
    for fid in ("SECTIONS_SEALED", "THE_CHANGED"):
        lv = ms_turn.get(fid)
        if lv:
            print(f"   {fid:16s} lands on L{_mode(lv)}  (want L4 / L8)")
    print("   read: is L3->L4 a hook->payoff, or L4 the fourth lore delivery?  [human]")

    # -- the ?-airtime question (H1.1) --------------------------------
    print("\n  ?-AIRTIME  (the H1.1 question - do NOT tune on this alone)")
    gaps = [g for e in won for g in e["q_to_bang"].values()]
    q_levels = [e["exp"]+1 for e in won if e["marker_q_seen"]]
    if gaps:
        print(f"   `?`->`!` gap (turns): n={len(gaps)}  "
              f"min {min(gaps)}  median {statistics.median(gaps):.0f}  "
              f"max {max(gaps)}")
        share_1 = sum(1 for g in gaps if g <= 1) / len(gaps)
        print(f"   share resolving in <=1 turn: {share_1:.0%}")
        if statistics.median(gaps) <= 1:
            print("   >> FLAG: median gap <=1 turn. `?` may be a flicker, not a "
                  "state. Candidate H1.1 evidence - a human read decides.")
        else:
            print("   the `?` state has some turns to exist; a human read decides "
                  "whether it reads as meaning.")
    else:
        print("   no `?`->`!` transition observed in a bot run "
              f"({len(q_levels)} levels showed `?` at all). "
              "The bot rarely lingers - this is expected; a human read is the test.")

    # -- encounter beats ----------------------------------------------
    print("\n  ENCOUNTER BEATS")
    for lt_exp in sorted({e["exp"] for e in won if e["ltype"] == "encounter"}):
        es = by_exp[lt_exp]
        prose = sum(e["beat_prose"] for e in es) / len(es)
        landed_on_completion = all(set(e["new_facts"]) and e["beat_seen"] for e in es)
        fid = es[0]["beat_fact"]
        print(f"   L{lt_exp+1:2d}  fact={fid:20s}  scene fired {prose:.0%}  "
              f"fact-on-completion {'yes' if landed_on_completion else 'NO'}")
    print("   read: does each beat change the KIND of interaction, not just add prose?  [human]")

    # -- crossing-type differentiation -------------------------------
    print("\n  CROSSING-TYPE DIFFERENTIATION  (fiction-only is the current design)")
    print(f"   {'type':10s} {'n':>3} {'threat0':>8} {'turns':>7} {'fights':>7} {'beats':>6}")
    for lt in ("fact", "traversal", "discovery", "quiet", "encounter"):
        es = [e for e in won if e["ltype"] == lt]
        if not es:
            continue
        print(f"   {lt:10s} {len(es):>3} "
              f"{statistics.mean(e['threat0'] for e in es):>8.1f} "
              f"{statistics.mean(e['turns'] for e in es):>7.1f} "
              f"{statistics.mean(e['fights'] for e in es):>7.1f} "
              f"{statistics.mean(e['story_beats'] for e in es):>6.1f}")
    print("   read: traversal/discovery/quiet are mechanically identical by design "
          "(only `quiet` threat is cut). Do they FEEL different?  [human]")

    # -- pacing ------------------------------------------------------
    print("\n  PACING")
    tries = {}
    for r in completed:
        c = Counter(e["exp"] for e in r["exps"])
        for k, v in c.items():
            tries.setdefault(k, []).append(v)
    hot = sorted(((k+1, statistics.mean(v)) for k, v in tries.items()),
                 key=lambda kv: -kv[1])[:5]
    print("   retry hotspots (level : mean attempts): "
          + "  ".join(f"L{k}:{v:.1f}" for k, v in hot))
    filler = sorted({e["exp"]+1 for e in won if e["story_beats"] <= 1})
    print(f"   expeditions with <=1 story beat: {filler or 'none'}")

    # -- endgame L20-25 --------------------------------------------
    print("\n  ENDGAME (L20-25)")
    soc = ms_turn_all(won, world, "SURVIVORS_ON_A_CLOCK")
    print(f"   SURVIVORS_ON_A_CLOCK lands on L{_mode(soc) if soc else '?'}  (want L24, the convergence beat)")
    fin = [e for e in won if e["is_finale"]]
    if fin:
        fused = all(e["corrections"] >= 1 and set(e["new_facts"]) for e in fin)
        print(f"   finale expedition: hyp-4 correction + WAKE_RESTART_RELEASES + "
              f"the choice land together: {'yes (accepted fusion)' if fused else 'no'}")
    print("   read: at L24 do you understand the human cost before you choose?  [human]")

    print(f"\n  ── READ complete. FLAGS above are 'a human should look here', "
          f"not failures. ──")


def ms_turn_all(won, world, fid):
    out = []
    for e in won:
        if fid in e["new_facts"]:
            out.append(e["exp"] + 1)
    return out


def _mode(xs):
    return Counter(xs).most_common(1)[0][0] if xs else "?"


# ----------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--world", default="the_wake")
    ap.add_argument("--seed", type=int, default=1000)
    ap.add_argument("--seeds", type=int, default=8)
    ap.add_argument("--coverage-only", action="store_true")
    ap.add_argument("--read-only", action="store_true")
    ap.add_argument("--max-attempts", type=int, default=60)
    args = ap.parse_args()

    world = get_world(args.world)
    if not world.manifest.section_bounds:
        print(f"'{args.world}' has no spatial spine - nothing for this tool to "
              "playtest. (COVERAGE is spine-shaped.)")
        sys.exit(2)
    runs = []
    print(f"running {args.seeds} Wake campaigns "
          f"(seeds {args.seed}..{args.seed+args.seeds-1}) ...")
    for i in range(args.seeds):
        pick = "1" if i % 2 else "2"      # alternate endings for coverage
        runs.append(run_campaign(world, args.seed + i, pick,
                                 max_attempts=args.max_attempts))
        s = runs[-1]
        tag = (f"stuck L{s['stuck_at']+1}" if s["stuck_at"] is not None
               else f"end={s['ending']}")
        print(f"  seed {args.seed+i}: {tag}")

    if not args.read_only:
        cov_ok = coverage(world, runs)
    if not args.coverage_only:
        read(world, runs)

    if not args.read_only:
        sys.exit(0 if cov_ok else 1)


if __name__ == "__main__":
    main()
