#!/usr/bin/env python3
"""Automated full-arc story playthrough.

Plays one persisting character through all _CAMPAIGN_LENGTH expeditions
with the campaign bot (tools.balance_autoplay.BotIO - the strongest
completer). Two modes:

  1 run  (default) - narrate the WORLD arc: the chapter intro when the
          chapter turns over, every authored WorldFact the expedition
          establishes, the working regional hypothesis + the "YOU HAD
          IT WRONG" correction when a milestone breaks a rung, and the
          finale choice (driven by --ending) + the ending text.

  --runs N - run N campaigns (seeds seed .. seed+N-1) and print
          aggregate statistics: completion rate, attempts-per-campaign
          spread, which expeditions cost the most retries, outcome mix,
          and world-fact / finale coverage.

A death or a timeout retries the same expedition (real non-hardcore
behaviour); a win advances.

    python3 tools/story_playthrough.py --seed 7 --ending protect
    python3 tools/story_playthrough.py --runs 20 --seed 100
"""
import argparse
import os
import statistics
import sys
import tempfile
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.game import Apocrysis
from src.campaign import chapter_for_expedition, chapter_intro
from src.worlds import get_world
from tools.balance_autoplay import BotIO


# set by _use_world() at the start of play()/batch() - the tool is
# world-parametric now (Phase F).
_WORLD = None
_FACTS = {}
_MILESTONE_IDS = set()
_HYPS = []
_CAMPAIGN_LENGTH = 25
_ENDING_IDS = ("broadcast", "protect")


def _use_world(world_id):
    global _WORLD, _FACTS, _MILESTONE_IDS, _HYPS, _CAMPAIGN_LENGTH, _ENDING_IDS
    _WORLD = get_world(world_id)
    _FACTS = {f.id: f for f in _WORLD.world_facts}
    _MILESTONE_IDS = {i for i, f in _FACTS.items() if f.milestone}
    _HYPS = list(_WORLD.regional_hypotheses)
    _CAMPAIGN_LENGTH = _WORLD.manifest.campaign_length
    _f = _WORLD.finale
    _ENDING_IDS = (_f.option_a[0], _f.option_b[0]) if _f else ("a", "b")
    return _WORLD


def _wi_status():
    return dict(getattr(Apocrysis, "_world_investigation", {}) or {})


def _known(status):
    return {k for k, v in status.items() if v == "known"}


def _current_hypothesis(known):
    for h in _HYPS:
        if h.held_until not in known:
            return h
    return None


class StoryBotIO(BotIO):
    """BotIO that answers the one finale prompt from a fixed choice."""

    def __init__(self, *a, ending=None, **k):
        super().__init__(*a, **k)
        # "1" for option_a, "2" for option_b
        self._ending_pick = "1" if ending == _ENDING_IDS[0] else "2"

    def ask(self, prompt=""):
        if "(1 / 2)" in prompt:
            return self._ending_pick
        return super().ask(prompt)


def _fact_lines(new_ids):
    out = []
    for fid in sorted(new_ids, key=lambda i: (_FACTS[i].chapter, i)):
        f = _FACTS[fid]
        tag = "  [MILESTONE]" if f.milestone else ""
        out.append(f"      + {f.statement}{tag}")
    return out


def play(seed, ending, max_turns, max_attempts, narrate=True):
    """One full campaign. Returns a stats dict; narrates to stdout when
    narrate=True."""
    Apocrysis._used_mechanisms = []
    Apocrysis._world_investigation = {}
    Apocrysis._campaign_ending = None

    profile = None
    level = 1
    exp = 0
    total_attempts = 0
    per_tier = defaultdict(int)          # exp index -> attempts spent
    outcomes = Counter()                 # won / died / timeout
    prev_known, prev_chapter, prev_hyp = set(), 0, None

    if narrate:
        print("=" * 70)
        print(" APOCRYSIS - automated full-arc playthrough")
        print(f" seed {seed} | ending choice: {ending.upper()} | "
              f"{_CAMPAIGN_LENGTH} expeditions")
        print("=" * 70)

    stuck_at = None
    with tempfile.TemporaryDirectory() as tmp:
        pf = os.path.join(tmp, "p.json")
        while exp < _CAMPAIGN_LENGTH:
            per_tier[exp] += 1
            total_attempts += 1
            if per_tier[exp] > max_attempts:
                stuck_at = exp
                if narrate:
                    print(f"\n  !! stuck at expedition {exp + 1} after "
                          f"{max_attempts} attempts - stopping.")
                break
            aseed = seed * 1000 + total_attempts

            io = StoryBotIO(max_turns=max_turns, ending=ending)
            p = Apocrysis("StoryBot", level=level, expeditions_completed=exp,
                          seed=aseed, io=io, world=_WORLD)
            if profile is not None:
                p.apply_profile(profile)
            io.player = p
            p.run_game_loop()

            outcome = ("won" if p.won else
                       "died" if p.health <= 0 else "timeout")
            outcomes[outcome] += 1
            level = p.level
            p.save_profile(pf)
            profile = Apocrysis.load_profile(pf)
            if not p.won:
                continue

            if narrate:
                ch = chapter_for_expedition(exp)
                known = _known(_wi_status())
                ms = len(known & _MILESTONE_IDS)
                if ch != prev_chapter:
                    prev_chapter = ch
                    print(f"\n\n{'-' * 70}")
                    _cts = _WORLD.manifest.chapter_titles
                    print(f" CHAPTER {ch}  -  {_cts[ch - 1] if ch <= len(_cts) else ''}")
                    print(f"{'-' * 70}")
                    print(chapter_intro(exp, ms, _WORLD))
                retries = per_tier[exp] - 1
                rtag = (f"  (after {retries} failed "
                        f"{'try' if retries == 1 else 'tries'})" if retries else "")
                print(f"\n  Expedition {exp + 1:>2}/{_CAMPAIGN_LENGTH}  -  "
                      f"level {p.level}{rtag}")
                new_facts = known - prev_known
                if new_facts:
                    print("    established:")
                    for ln in _fact_lines(new_facts):
                        print(ln)
                else:
                    print("    (no new world fact this expedition)")
                hyp = _current_hypothesis(known)
                if hyp is not prev_hyp:
                    if prev_hyp is not None:
                        print(f"    >> YOU HAD IT WRONG: {prev_hyp.corrected_to}")
                    print(f'    working theory: "{hyp.statement}"' if hyp
                          else "    working theory: none left - you know "
                               "what happened.")
                    prev_hyp = hyp
                prev_known = known

            exp = p.expeditions_completed

    kn = _known(_wi_status())
    rec = getattr(Apocrysis, "_campaign_ending", None)
    stats = {
        "seed": seed, "completed": stuck_at is None, "stuck_at": stuck_at,
        "total_attempts": total_attempts,
        "attempts_by_exp": dict(per_tier),
        "outcomes": dict(outcomes),
        "facts_known": len(kn), "milestones_known": len(kn & _MILESTONE_IDS),
        "missing_facts": [i for i in _FACTS if i not in kn],
        "final_level": level, "ending_recorded": rec,
    }

    if narrate:
        print(f"\n\n{'=' * 70}")
        print(" CAMPAIGN COMPLETE" if stats["completed"]
              else f" CAMPAIGN INCOMPLETE (stuck at expedition {stuck_at + 1})")
        print(f"{'=' * 70}")
        print(f" world facts established: {stats['facts_known']}/{len(_FACTS)}"
              f"   (milestones {stats['milestones_known']}/{len(_MILESTONE_IDS)})")
        if stats["missing_facts"]:
            print(f" never established: {', '.join(stats['missing_facts'])}")
        print(f" total expedition attempts: {total_attempts}"
              f"   (final level {level})")
        print(f" finale choice recorded in-game: {rec!r}"
              f"{'  (bot-driven, matches --ending)' if rec == ending else '  --'}")
        if stats["completed"]:
            print(f"\n ENDING - {ending.upper()}\n")
            E = _WORLD.finale.endings
            lead, body = E.get(ending) or next(iter(E.values()))
            for para in (lead, "", body):
                print(("   " + para) if para else "")
    return stats


def _spread(xs):
    xs = sorted(xs)
    if not xs:
        return "n/a"
    return (f"min {xs[0]}  p25 {statistics.quantiles(xs, n=4)[0]:.0f}  "
            f"median {statistics.median(xs):.0f}  "
            f"p75 {statistics.quantiles(xs, n=4)[2]:.0f}  max {xs[-1]}"
            if len(xs) >= 4 else
            f"min {xs[0]}  median {statistics.median(xs):.0f}  max {xs[-1]}")


def batch(seed0, runs, ending, max_turns, max_attempts):
    print("=" * 70)
    print(f" APOCRYSIS - {runs} full-arc campaigns   "
          f"(seeds {seed0}..{seed0 + runs - 1}, ending {ending.upper()})")
    print("=" * 70)
    results = []
    for i in range(runs):
        s = seed0 + i
        r = play(s, ending, max_turns, max_attempts, narrate=False)
        results.append(r)
        flag = "ok " if r["completed"] else "STUCK"
        print(f"  seed {s:>4}  {flag}  attempts {r['total_attempts']:>4}  "
              f"facts {r['facts_known']}/{len(_FACTS)}  "
              f"ms {r['milestones_known']}/{len(_MILESTONE_IDS)}  "
              f"end={r['ending_recorded']}")

    done = [r for r in results if r["completed"]]
    _nfacts = len(_FACTS)
    print(f"\n{'=' * 70}\n AGGREGATE  ({len(results)} campaigns)\n{'=' * 70}")
    print(f" completed {_CAMPAIGN_LENGTH}/{_CAMPAIGN_LENGTH} expeditions : {len(done)}/{len(results)}")
    if done:
        print(f" attempts per campaign      : {_spread([r['total_attempts'] for r in done])}")
        print(f" final character level      : {_spread([r['final_level'] for r in done])}")
        allf = sum((Counter(r['outcomes']) for r in done), Counter())
        tot = sum(allf.values()) or 1
        print(f" expedition outcome mix     : "
              + "  ".join(f"{k} {allf[k]} ({100*allf[k]//tot}%)"
                          for k in ("won", "died", "timeout") if allf[k]))
        fc = Counter(r["facts_known"] for r in done)
        print(f" world facts at completion  : "
              + (f"always {_nfacts}/{_nfacts}" if set(fc) == {_nfacts}
                 else "  ".join(f"{k}:{v}" for k, v in sorted(fc.items()))))
        ec = Counter(r["ending_recorded"] for r in done)
        print(f" finale choice recorded     : "
              + "  ".join(f"{k}={v}" for k, v in ec.items()))

        # which expeditions eat the retries
        agg = defaultdict(list)
        for r in done:
            for e, n in r["attempts_by_exp"].items():
                agg[e].append(n)
        worst = sorted(agg.items(), key=lambda kv: -statistics.mean(kv[1]))[:8]
        print("\n retry hotspots (expedition : mean attempts, worst-first)")
        for e, ns in worst:
            print(f"   exp {e + 1:>2}  (CH{chapter_for_expedition(e)})  "
                  f"mean {statistics.mean(ns):>4.1f}   max {max(ns)}")
    stuck = [r for r in results if not r["completed"]]
    if stuck:
        sc = Counter(r["stuck_at"] + 1 for r in stuck)
        print("\n stuck at expedition : "
              + "  ".join(f"{k} (x{v})" for k, v in sorted(sc.items())))


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--world", default="silence",
                    help="world id (silence, the_wake)")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--runs", type=int, default=1,
                    help="run N campaigns (seeds seed..seed+N-1) and print stats")
    ap.add_argument("--ending", default=None,
                    help="finale choice id (defaults to the world's option_b)")
    ap.add_argument("--max-turns", type=int, default=600)
    ap.add_argument("--max-attempts", type=int, default=60,
                    help="retry cap per expedition tier before giving up")
    args = ap.parse_args()
    _use_world(args.world)
    if args.ending is None:
        args.ending = _ENDING_IDS[1]
    if args.runs > 1:
        batch(args.seed, args.runs, args.ending, args.max_turns, args.max_attempts)
    else:
        play(args.seed, args.ending, args.max_turns, args.max_attempts)


if __name__ == "__main__":
    main()
