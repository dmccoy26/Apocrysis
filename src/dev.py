"""`--dev` — the story-inspection harness. See docs/DEV_PLAYTEST.md.

NOT a second way to play. It puts a fresh survivor at a chosen
narrative point in a coherent WorldInvestigation state, then hands off
to the *normal* game - no alternate story logic, no special rendering,
no bypass inside the game itself, and NO balance change (combat power,
inventory, survivor progression, loot, hunger/thirst, map-gen rules,
encounter rates, difficulty are all untouched - the C.3.2a-7 supply
floor applies exactly as it would at that real depth).

Persistence is sandboxed to DEV_PROFILE_PATH and wiped each run, so a
dev session can never read or overwrite a real campaign profile.
"""
import os
from collections import namedtuple

from src.campaign import _CHAPTER_BOUNDS, CHAPTER_TITLES
from src.worlds.silence import SILENCE

DevConfig = namedtuple("DevConfig", "seed chapter finale")

DEV_PROFILE_PATH = os.path.join(os.getcwd(), ".dev_playtest_profile.json")

# The finale expedition establishes these itself - never pre-mark them.
_FINALE_FACTS = {"RESP_THE_ORDER", "RESP_THE_CHOICE"}


def _dev_level(depth):
    # Calibrated to balance_autoplay telemetry: exp 3 -> L~3.3, exp 6 ->
    # L~5.7, exp 9 -> L~7.6. A survivor who actually reached this depth.
    return max(1, min(12, round(1 + 0.78 * depth)))


def synthetic_state(cfg):
    """(expeditions_completed, world_investigation_status) for a coherent
    drop-in at the START of the requested chapter (1-6), or the finale.
    Every WorldFact in an EARLIER chapter is marked known, so
    next_target() points at the first fact of the requested chapter."""
    facts = SILENCE.world_facts
    if cfg.finale:
        depth = _CHAPTER_BOUNDS[-1]                    # expedition 25
        known = {f.id for f in facts if f.id not in _FINALE_FACTS}
    else:
        ch = max(1, min(6, cfg.chapter or 1))
        depth = _CHAPTER_BOUNDS[ch - 1]
        known = {f.id for f in facts if f.chapter < ch}
    return depth, {fid: "known" for fid in known}


def entry_label(cfg):
    if cfg.finale:
        return "the finale (expedition 25) - THE TRUTH"
    ch = max(1, min(6, cfg.chapter or 1))
    return f"Chapter {ch} - {CHAPTER_TITLES[ch - 1]}"


def banner(cfg, depth):
    return (
        "\n==================== DEV PLAYTEST ====================\n"
        f" Seed:           {cfg.seed}\n"
        f" Entry:          {entry_label(cfg)}\n"
        f" Expedition:     {depth + 1} of 25\n"
        " Campaign state: SYNTHETIC (sandboxed - no real profile touched)\n"
        f" Survivor:       L{_dev_level(depth)} + depth-appropriate gear "
        "(what a real run produces)\n"
        " Balance:        unchanged - combat/encounter/loot/curve untouched\n"
        "=====================================================\n"
        " This inspects a single story section. It is NOT a substitute\n"
        " for a straight-through campaign - the finale's weight needs\n"
        " the accumulated run.\n"
    )


def reset_sandbox():
    try:
        os.path.exists(DEV_PROFILE_PATH) and os.remove(DEV_PROFILE_PATH)
    except OSError:
        pass


def equip_for_depth(player, depth):
    """Put the synthetic survivor at the level + gear a real survivor
    would have at `depth`. SURVIVOR STATE ONLY - combat formulas,
    encounter rates, loot rates, the difficulty curve and hunger/thirst
    are untouched. Without this, a fresh L1 body can't survive the
    depth-N difficulty curve long enough to reach any story content
    (playtest 2026-08-30: CH3 jump-in died turn 32, zero sites)."""
    from src.constants import LOOT_WEAPON_TABLE, ARMOR_TABLE
    from src.items import MeleeWeapon, RangedWeapon, Armor

    lvl = _dev_level(depth)
    bump = lvl - player.level
    if bump > 0:
        player.level = lvl
        player.strength += bump
        player.dexterity += bump
        player.intelligence += bump
        player.wisdom += bump
        player.max_health += 5 * bump
    player.health = player.max_health

    # Assigned DIRECTLY (not via equip_weapon / equip_armor) - those
    # print through self.io, which raises from on_mount's thread. The
    # survivor comes in with these already worn.
    _melee = [(n, s) for n, s in LOOT_WEAPON_TABLE.items()
              if s["type"] == "melee" and s.get("min_expedition", 0) <= depth]
    if _melee:
        n, s = max(_melee, key=lambda kv: kv[1]["damage"])
        player.equipped_weapon = MeleeWeapon(n, s["damage"], s["durability"])

    for slot in ("body", "head"):
        cands = [(n, s) for n, s in ARMOR_TABLE.items()
                 if s["slot"] == slot and s.get("min_expedition", 0) <= depth]
        if cands:
            n, s = max(cands, key=lambda kv: kv[1]["reduction"])
            player.equipped_armor[slot] = Armor(
                n, s["reduction"], s["durability"], slot)
