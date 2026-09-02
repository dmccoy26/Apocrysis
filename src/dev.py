"""`--dev` — the story-inspection harness. See docs/DEV_PLAYTEST.md.

NOT a second way to play. It puts a fresh survivor at a chosen
narrative point in a coherent WorldInvestigation state, then hands off
to the *normal* game - no alternate story logic, no special rendering,
no bypass inside the game itself, and NO balance change (combat power,
inventory, survivor progression, loot, hunger/thirst, map-gen rules,
encounter rates, difficulty are all untouched - the C.3.2a-7 supply
floor applies exactly as it would at that real depth).

Persistence is sandboxed to dev_profile_path() and wiped each run, so a
dev session can never read or overwrite a real campaign profile.
"""
import os
from collections import namedtuple

from src.runtime_paths import dev_profile_path
from src.worlds import get_world

# Back-compat re-exports (this harness began as World-1-only).
_WORLD = get_world("silence")
SILENCE = _WORLD

# DevConfig gained `world` + `expedition` when the harness went
# multi-world (2026-09-02). `world` defaults to silence so every old
# `--dev` command still resolves; `expedition` (1-based level number)
# overrides `chapter` for a finer drop-in.
DevConfig = namedtuple("DevConfig", "seed chapter finale world expedition")
DevConfig.__new__.__defaults__ = (None, False, "silence", None)

# The `--dev` sandbox profile - wiped each run (reset_sandbox), never a
# real campaign file. Lives under the runtime-data root like everything
# else Apocrysis writes. Call dev_profile_path() (re-exported here) at
# use time so an APOCRYSIS_HOME override is always honoured.


def _dev_world(cfg):
    return get_world(getattr(cfg, "world", None) or "silence")


def _finale_facts(world):
    """Facts the finale expedition establishes itself - never pre-mark
    them. The converge fact plus whatever the finale also_establishes."""
    fin = getattr(world, "finale", None)
    if fin is None:
        return set()
    out = set(getattr(fin, "also_establishes", ()) or ())
    cf = getattr(fin, "converge_fact", None)
    if cf:
        out.add(cf)
    return out


def _dev_level(depth):
    # Calibrated to balance_autoplay telemetry: exp 3 -> L~3.3, exp 6 ->
    # L~5.7, exp 9 -> L~7.6. A survivor who actually reached this depth.
    return max(1, min(12, round(1 + 0.78 * depth)))


def synthetic_state(cfg):
    """(expeditions_completed, world_investigation_status) for a coherent
    drop-in. Every WorldFact in an EARLIER chapter than the drop-in
    point is marked known, so next_target() points at the first
    still-open fact. `--expedition N` (1-based) drops mid-chapter;
    `--chapter C` drops at that chapter's first expedition; `--finale`
    drops at the last."""
    world = _dev_world(cfg)
    facts = world.world_facts
    bounds = world.manifest.chapter_bounds
    n_ch = len(bounds)
    length = world.manifest.campaign_length

    if getattr(cfg, "expedition", None):
        depth = max(0, min(length - 1, int(cfg.expedition) - 1))
        # the chapter this expedition falls in
        ch = 1
        for i, lo in enumerate(bounds):
            if depth >= lo:
                ch = i + 1
        known = {f.id for f in facts if f.chapter < ch}
    elif cfg.finale:
        depth = length - 1                      # the LAST expedition, not the last chapter
        known = {f.id for f in facts if f.id not in _finale_facts(world)}
    else:
        ch = max(1, min(n_ch, cfg.chapter or 1))
        depth = bounds[ch - 1]
        known = {f.id for f in facts if f.chapter < ch}
    return depth, {fid: "known" for fid in known}


def entry_label(cfg):
    world = _dev_world(cfg)
    titles = world.manifest.chapter_titles
    length = world.manifest.campaign_length
    if getattr(cfg, "expedition", None):
        n = max(1, min(length, int(cfg.expedition)))
        return f"expedition {n} of {length}"
    if cfg.finale:
        return f"the finale (expedition {length}) - THE TRUTH"
    ch = max(1, min(len(titles) or 1, cfg.chapter or 1))
    t = titles[ch - 1] if ch - 1 < len(titles) else ""
    return f"Chapter {ch} - {t}"


def banner(cfg, depth):
    world = _dev_world(cfg)
    return (
        "\n==================== DEV PLAYTEST ====================\n"
        f" World:          {world.manifest.title}  ({world.id})\n"
        f" Seed:           {cfg.seed}\n"
        f" Entry:          {entry_label(cfg)}\n"
        f" Expedition:     {depth + 1} of {world.manifest.campaign_length}\n"
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
        _p = dev_profile_path()
        os.path.exists(_p) and os.remove(_p)
    except OSError:
        pass


def equip_for_depth(player, depth):
    """Put the synthetic survivor at the level + gear a real survivor
    would have at `depth`. SURVIVOR STATE ONLY - combat formulas,
    encounter rates, loot rates, the difficulty curve and hunger/thirst
    are untouched. Without this, a fresh L1 body can't survive the
    depth-N difficulty curve long enough to reach any story content
    (playtest 2026-08-30: CH3 jump-in died turn 32, zero sites)."""
    from src import loot as _loot
    from src.items import MeleeWeapon, RangedWeapon, Armor

    # world-owned loot tables (F.10) - so a dev drop into The Wake comes
    # in with ship kit, not valley weapon names.
    _world = getattr(player, "world", None)
    LOOT_WEAPON_TABLE = _loot.weapon_table(_world)
    ARMOR_TABLE = _loot.armor_table(_world)

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

    # A survivor this deep has a pantry from ~N wins of inheritance +
    # the scaled prize each time - not the thin starter ration. Without
    # this a jump-in starves mid-expedition on a 34x34 map before the
    # story pays off (playtest 2026-08-30 run 2: died turn 160, food 0).
    player.backpack.food = max(player.backpack.food, 40 + depth)
    player.backpack.water = max(player.backpack.water, 40 + depth)
    player.backpack.ammo = max(player.backpack.ammo, 30)

    # Persistent kit a real survivor at this depth would already hold -
    # so a mid-campaign drop-in isn't missing the one-time discoverables.
    # Presentation state only; no balance number moves.
    if depth >= 2:
        player.has_flashlight = True
    _mf = getattr(_world, "manifest", None)
    if _mf is not None and getattr(_mf, "markers_need_device", False):
        # H1: the tactical helmet is the first `discovery` crossing.
        _lts = getattr(_mf, "level_types", ()) or ()
        _first_disc = next((i for i, t in enumerate(_lts) if t == "discovery"), None)
        if _first_disc is not None and depth > _first_disc:
            player.has_scanner = True
