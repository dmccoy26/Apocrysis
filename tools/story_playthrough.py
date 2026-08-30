#!/usr/bin/env python3
"""Automated full-arc story playthrough.

Plays one persisting character through all CAMPAIGN_LENGTH expeditions
with the campaign bot (tools.balance_autoplay.BotIO - the strongest
completer), and narrates the WORLD arc rather than the survival stats:

  - the chapter intro when the chapter turns over
  - every authored WorldFact the expedition establishes
  - the working regional hypothesis, and the "YOU HAD IT WRONG"
    correction when a milestone breaks a rung
  - the finale choice (driven by --ending) and the ending text

A death or a timeout retries the same expedition (real non-hardcore
behaviour); only the narrative-bearing wins are reported in detail.

    python3 tools/story_playthrough.py --seed 7 --ending protect
"""
import argparse
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.game import Apocrysis
from src.constants import CAMPAIGN_LENGTH
from src.campaign import (chapter_for_expedition, chapter_intro, CHAPTER_TITLES,
                          campaign_ending)
from src.worlds.silence.world import SILENCE
from tools.balance_autoplay import BotIO


_FACTS = {f.id: f for f in SILENCE.world_facts}
_HYPS = list(SILENCE.regional_hypotheses)


def _wi_status():
    """The campaign-wide investigation status dict (class-var, the same
    thing the profile round-trips)."""
    return dict(getattr(Apocrysis, "_world_investigation", {}) or {})


def _known(status):
    return {k for k, v in status.items() if v == "known"}


def _current_hypothesis(known):
    for h in _HYPS:
        if h.held_until not in known:
            return h
    return None


class StoryBotIO(BotIO):
    """BotIO that answers the one finale prompt from a fixed choice and
    keeps the ending prose it prints."""

    def __init__(self, *a, ending="protect", **k):
        super().__init__(*a, **k)
        self._ending_pick = "1" if ending == "broadcast" else "2"
        self.finale_prose = []
        self._in_finale_prose = False

    def ask(self, prompt=""):
        if "Broadcast, or protect" in prompt or "protect? (1 / 2)" in prompt:
            return self._ending_pick
        return super().ask(prompt)

    def say(self, *args, **kwargs):
        text = " ".join(str(a) for a in args)
        # the finale prose block is one big say() from campaign_ending()
        if "acknowledges receipt" in text or "switch it off" in text \
                or "stays a success on someone's ledger" in text:
            self.finale_prose.append(text)
        super().say(*args, **kwargs)


def _fact_lines(new_ids):
    out = []
    for fid in sorted(new_ids, key=lambda i: (_FACTS[i].chapter if i in _FACTS else 9, i)):
        f = _FACTS.get(fid)
        if f is None:
            out.append(f"      + {fid}")
            continue
        tag = "  [MILESTONE]" if f.milestone else ""
        out.append(f"      + {f.statement}{tag}")
    return out


def play(seed, ending, max_turns, max_attempts):
    Apocrysis._used_mechanisms = []
    Apocrysis._world_investigation = {}
    Apocrysis._campaign_ending = None

    profile = None
    level = 1
    exp = 0
    total_attempts = 0
    per_tier = {}
    prev_known = set()
    prev_chapter = 0
    prev_hyp = None
    finale_prose = []

    print("=" * 70)
    print(f" APOCRYSIS - automated full-arc playthrough")
    print(f" seed {seed} | ending choice: {ending.upper()} | "
          f"{CAMPAIGN_LENGTH} expeditions")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmp:
        pf = os.path.join(tmp, "p.json")
        while exp < CAMPAIGN_LENGTH:
            per_tier[exp] = per_tier.get(exp, 0) + 1
            total_attempts += 1
            if per_tier[exp] > max_attempts:
                print(f"\n  !! stuck at expedition {exp + 1} after "
                      f"{max_attempts} attempts - stopping.")
                return
            aseed = seed + total_attempts

            io = StoryBotIO(max_turns=max_turns, ending=ending)
            p = Apocrysis("StoryBot", level=level, expeditions_completed=exp,
                          seed=aseed, io=io)
            if profile is not None:
                p.apply_profile(profile)
            io.player = p
            p.run_game_loop()

            outcome = ("won" if p.won else
                       "died" if p.health <= 0 else "timeout")
            level = p.level

            if not p.won:
                p.save_profile(pf)
                profile = Apocrysis.load_profile(pf)
                continue

            # ---- a win: narrate the world step ----
            ch = chapter_for_expedition(exp)
            known = _known(_wi_status())
            ms_known = len(known & {i for i, f in _FACTS.items() if f.milestone})

            if ch != prev_chapter:
                prev_chapter = ch
                print(f"\n\n{'-' * 70}")
                print(f" CHAPTER {ch}  -  {CHAPTER_TITLES[ch - 1]}")
                print(f"{'-' * 70}")
                print(chapter_intro(exp, ms_known))

            retries = per_tier[exp] - 1
            rtag = f"  (after {retries} failed {'try' if retries == 1 else 'tries'})" if retries else ""
            print(f"\n  Expedition {exp + 1:>2}/{CAMPAIGN_LENGTH}  -  "
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
                if hyp is not None:
                    print(f"    working theory: \"{hyp.statement}\"")
                else:
                    print("    working theory: none left - you know what happened.")
                prev_hyp = hyp

            prev_known = known
            if io.finale_prose:
                finale_prose = io.finale_prose

            exp = p.expeditions_completed
            p.save_profile(pf)
            profile = Apocrysis.load_profile(pf)

    # ---- arc complete ----
    print(f"\n\n{'=' * 70}")
    print(" CAMPAIGN COMPLETE")
    print(f"{'=' * 70}")
    kn = _known(_wi_status())
    print(f" world facts established: {len(kn)}/{len(_FACTS)}   "
          f"(milestones {len(kn & {i for i, f in _FACTS.items() if f.milestone})}/9)")
    missing = [i for i in _FACTS if i not in kn]
    if missing:
        print(f" never established: {', '.join(missing)}")
    print(f" total expedition attempts: {total_attempts}")
    _rec = getattr(Apocrysis, "_campaign_ending", None)
    print(f" finale choice recorded in-game: {_rec!r}"
          f"{'  (bot-driven, matches --ending)' if _rec == ending else '  !! MISMATCH'}")
    print(f"\n ENDING - {ending.upper()}\n")
    lead, body = campaign_ending.__globals__["ENDINGS"].get(
        ending, campaign_ending.__globals__["ENDINGS"]["protect"])
    for para in (lead, "", body):
        print("   " + para if para else "")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--ending", choices=("protect", "broadcast"),
                    default="protect")
    ap.add_argument("--max-turns", type=int, default=600)
    ap.add_argument("--max-attempts", type=int, default=60)
    args = ap.parse_args()
    play(args.seed, args.ending, args.max_turns, args.max_attempts)


if __name__ == "__main__":
    main()
