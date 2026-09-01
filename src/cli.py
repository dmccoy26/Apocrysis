# Auto-extracted from the original monolithic apocrysis.py during
# the src/ restructuring - see README.md for the project layout.

import os

from src.game import Apocrysis
from src.items import Backpack, MeleeWeapon, RangedWeapon
from src.mixins.persistence_mixin import (
    profile_filename_for_name, _profile_flat, clean_display_name,
)
from src.zombies import FreshZombie, RegularZombie, HeavyZombie


def _resolve_player_identity():
    """
    Shared by main() and main_tui(): the one piece of profile
    selection that must happen in the plain terminal, before Textual
    (if any) takes the screen. Offers existing profile names to pick
    from and prompts for hardcore mode only when the name is brand
    new - an existing profile's hardcore flag was already decided at
    creation and is never re-asked. Returns (name, hardcore, profile)
    where profile is the loaded profile dict, or None for a new name.
    """
    existing_names = Apocrysis.list_profile_names()
    if existing_names:
        print("Existing survivors:", ", ".join(existing_names))
        name = input("Continue a survivor by typing their exact name, or type a new name to start fresh: ").strip()
    else:
        name = input("Enter your name: ").strip()

    # The name becomes self.name, which flows into Rich markup (HUD),
    # play logs and profile-filename slugs - sanitise it once, here, at
    # the only point a human types it.
    name = clean_display_name(name)

    if name in existing_names:
        profile = Apocrysis.load_profile_by_name(name)
        # hardcore lives under "campaign" in a Phase-B profile; flatten
        # so an existing hardcore campaign isn't silently read as soft.
        hardcore = bool(_profile_flat(profile).get("hardcore", False)) if profile else False
    else:
        profile = None
        hardcore_choice = input(
            "Play in hardcore mode? Death is permanent - no reloading "
            "this character. (y/n): "
        ).strip().lower()
        hardcore = hardcore_choice in ("y", "yes")

    return name, hardcore, profile


def _dev_main(start_log=False, dev=None):
    """`--dev` classic path: fresh survivor at a synthetic narrative
    point, sandboxed persistence. See src/dev.py / docs/DEV_PLAYTEST.md."""
    from src.dev import (synthetic_state, banner, reset_sandbox,
                         equip_for_depth)
    from src.runtime_paths import dev_profile_path
    reset_sandbox()
    _dev_profile = dev_profile_path()
    depth, wi_status = synthetic_state(dev)
    print(banner(dev, depth))

    _log_path = None
    while True:
        Apocrysis._world_investigation = dict(wi_status)
        Apocrysis._survivor_knowledge = []
        player = Apocrysis("Dev", level=1, seed=dev.seed, hardcore=False,
                           expeditions_completed=depth, io=None)
        equip_for_depth(player, depth)
        from src.campaign import chapter_intro
        _ms = len(player.world_investigation.milestones_known())
        print(chapter_intro(player.expeditions_completed, _ms, player.world))
        print(" ")
        if start_log:
            _p = player.start_playlog(path=_log_path)
            if _p:
                _log_path = _p
                print(f"Play logging on -> {_p}")
        player.run_game_loop()

        if player.health <= 0:
            # a death mid-inspection: hand to a fresh survivor at the
            # same depth (the campaign lifecycle, sandboxed) and carry
            # on, so the section is still playable through a death.
            Apocrysis._survivors_lost = int(getattr(Apocrysis, "_survivors_lost", 0)) + 1
            Apocrysis.persist_new_survivor(
                _dev_profile, "Dev", False, player.expeditions_completed)
            wi_status = dict(Apocrysis._world_investigation)
            depth = player.expeditions_completed
            print("\n(dev: survivor lost - a fresh one takes up the same point)\n")
            continue
        player.save_profile(_dev_profile)   # sandbox only
        if player.expeditions_completed >= player.world.manifest.campaign_length:
            break   # finished the arc from this drop-in point
        cont = input("\n(dev) continue to the next expedition? (y/n): ").strip().lower()
        if cont not in ("y", "yes"):
            break
        from src.mixins.persistence_mixin import _profile_flat
        _f = _profile_flat(Apocrysis.load_profile(_dev_profile) or {})
        wi_status = dict(_f.get("world_investigation", {}) or {})
        depth = _f.get("expeditions_completed", depth)


def main_tui(start_log=False, dev=None):
    # G3.2: no pre-Textual identity prompt. The shell owns identity
    # selection now - ApocrysisApp lands on MenuScreen, and CONTINUE /
    # NEW CAMPAIGN (name entry as a real in-TUI interaction) take it
    # from there. The old terminal name picker is gone from this path
    # (it stays for --classic, cli.main() below).
    from src.tui import ApocrysisApp

    if dev is not None:
        from src.dev import synthetic_state, banner, reset_sandbox
        reset_sandbox()
        depth, _ = synthetic_state(dev)
        print(banner(dev, depth))
        input("Press Enter to start the dev playtest... ")
        app = ApocrysisApp(name="Dev", hardcore=False, start_log=start_log,
                           dev=dev)
        app.run()
        return

    ApocrysisApp(start_log=start_log).run()


_SURVIVOR_POOL = (
    "Ada", "Cole", "Nadia", "Rourke", "Iris", "Bex", "Yusuf", "Wren",
    "Halloran", "Sim", "Petra", "Osei", "Vann", "Dill", "Marsh", "Okonkwo",
)


def _next_survivor_name(n):
    """The n-th survivor to take up the search. Cycles the pool; adds a
    numeral once it wraps so names never silently repeat."""
    base = _SURVIVOR_POOL[(n - 1) % len(_SURVIVOR_POOL)]
    wrap = (n - 1) // len(_SURVIVOR_POOL)
    return base if wrap == 0 else f"{base} ({wrap + 1})"


def main(start_log=False, dev=None):
    if dev is not None:
        return _dev_main(start_log=start_log, dev=dev)
    # v3 SPRINT step 1: no class prompt (v5: no player classes at all -
    # stat growth is level-based, src/player.py + combat_mixin.level_up())
    # and no re-entering your name/starting-over every launch. A profile
    # (name/level/xp/stats/backpack/weapon - PersistenceMixin's
    # save_profile()/load_profile(), distinct from the full-state
    # named save slots below) auto-loads if one exists; map size is
    # always derived from the carried-forward level
    # (game.py's __init__), not a manual prompt, since v3's whole
    # point is that the map grows with you automatically.
    name, hardcore, profile = _resolve_player_identity()
    # Phase B: the profile file is the CAMPAIGN's identity. The survivor
    # who carries it can change (they die; a new one takes over) without
    # the file key changing.
    campaign_file = profile_filename_for_name(name)

    # One transcript file for the whole session; each expedition after
    # the first appends to it (run_game_loop closes it on win, we
    # reopen the same path) instead of a new timestamped file per run.
    _log_path = None

    while True:
        player = None
        flat = _profile_flat(profile) if profile is not None else {}

        # Named-slot manual load - kept as a fallback for an exact
        # full-state resume (map/position/day included), only offered
        # when no profile exists yet to auto-continue from.
        if profile is None:
            try:
                save_files = [f for f in os.listdir(".") if f.endswith(".json")]
            except OSError:
                save_files = []

            if save_files:
                print("Available save files:", ", ".join(save_files))
                load_choice = input("Load saved game? (y/n): ").lower()
                if load_choice == 'y':
                    filename = input("Enter save file name (e.g., 'apocrysis_save.json'): ")
                    player = Apocrysis.load_game(filename)

        if player is None:
            if profile is not None:
                level = flat.get("level", 1)
                expeditions_completed = flat.get("expeditions_completed", 0)
                who = flat.get("name", name)
                print(f"\n{who} takes up the search - level {level}, "
                      f"the search {expeditions_completed} expeditions deep.")
                # A.5: seed the campaign class-vars BEFORE construction so
                # the first expedition's mystery targets the right
                # WorldFact (generate_map runs in __init__, before
                # apply_profile).
                Apocrysis._world_investigation = dict(
                    flat.get("world_investigation", {}) or {})
                Apocrysis._survivor_knowledge = list(
                    flat.get("survivor_knowledge", []) or [])
            else:
                level = 1
                expeditions_completed = 0
                who = name

            player = Apocrysis(who, level=level, hardcore=hardcore, expeditions_completed=expeditions_completed)

            if profile is not None:
                player.apply_profile(profile)

        print(" ")
        print(" ")
        print("In the twilight years of the 21st century, the world as we knew it teetered on the brink of an abyss, ")
        print("brought to its knees by a catastrophic blend of environmental disasters, political turmoil, and ")
        print("unchecked scientific experimentation. Amidst this chaos, a virulent pathogen, born from the reckless ")
        print("ambition of a clandestine biotech firm, was unleashed upon an unsuspecting populace. The outbreak was ")
        print("swift and merciless, ravaging cities, decimating communities, and transforming the afflicted into ")
        print("voracious, undead beings. ")
        print(" ")
        print(f"{player.name}, a once unassuming person with a knack for survival and a heart brimming ")
        print("with resilience, found himself cast into the heart of this apocalyptic nightmare. While the world around him ")
        print(f"succumbed to despair and ruin, {player.name}'s resolve to endure, to fight, and to carve out a semblance of hope amid ")
        print("the desolation became the beacon that guided his every step. As society crumbled and the vestiges of humanity ")
        print(f"dwindled, {player.name}'s journey through this dystopian world became a testament to the indomitable spirit of those who ")
        print("refuse to be extinguished, even in the darkest of times.")
        print(" ")

        # v4 (todo 55df661d): campaign-as-chapters. A short framing line
        # for this expedition, keyed to how far in you are.
        from src.campaign import chapter_intro
        _ms = len(player.world_investigation.milestones_known()) if getattr(
            player, "world_investigation", None) else 0
        print(chapter_intro(player.expeditions_completed, _ms, player.world))
        print(" ")

        if start_log:
            _p = player.start_playlog(path=_log_path)
            if _p:
                _log_path = _p
                print(f"Play logging on -> {_p}")
        player.run_game_loop()

        _died = player.health <= 0

        if player.hardcore and _died:
            # hardcore = one survivor, one shot. The campaign dies too.
            player.delete_profile()
            print("\nThat's the end of it. No reload.\n")
            break

        if _died:
            # Phase B: the roguelite loop. This survivor is gone; the
            # campaign - everything that's been figured out - stands.
            # The game lifecycle (not save_profile) replaces the
            # survivor: the campaign class-vars still hold this run's
            # progress, so a fresh Apocrysis picks them up; we only
            # bump the depth and the lost-survivor count, then persist.
            Apocrysis._survivors_lost = int(
                getattr(Apocrysis, "_survivors_lost", 0)) + 1
            heir_name = _next_survivor_name(Apocrysis._survivors_lost)
            print(f"\n{player.name} did not make it back.")
            print(f"A NEW SURVIVOR TAKES UP THE SEARCH — {heir_name}.\n")
            Apocrysis.persist_new_survivor(
                campaign_file, heir_name, hardcore, player.expeditions_completed)
            profile = Apocrysis.load_profile(campaign_file)
            continue

        # survived - win or quit. Save and carry on / stop.
        player.save_profile(campaign_file)
        profile = Apocrysis.load_profile(campaign_file)

        if getattr(player, 'won', False):
            # Loop back (don't break) so the outer while True builds a
            # fresh Apocrysis() and Apocrysis.prize_for_next_game (set
            # on win, consumed only in __init__) is actually granted.
            print("Starting the next expedition with your earned supplies...\n")
            continue

        if getattr(player, 'quit', False):
            print("Thanks for playing!")
            break



def run_tests():
    print("Running tests for apocrysis.py...")
    
    # Test Backpack
    bp = Backpack()
    assert bp.food == 0 and bp.water == 0 and bp.medicine == 0 and bp.ammo == 0
    assert len(bp.weapons) == 0
    
    bp.add_item("food")
    assert bp.food == 1
    bp.add_item("water")
    assert bp.water == 1
    bp.add_item("medicine")
    assert bp.medicine == 1
    bp.add_item("ammo")
    assert bp.ammo == 1
    
    # Test MeleeWeapon
    mw = MeleeWeapon("Sword", 10, 5)
    assert mw.damage == 10 and mw.durability == 5
    dmg = mw.use()
    assert dmg == 10 and mw.durability == 4
    for _ in range(4):
        mw.use()
    assert mw.durability == 0
    dmg = mw.use()
    assert dmg == 0
    
    # Test RangedWeapon
    rw = RangedWeapon("Gun", 15, 3)
    assert rw.ammo == 3 and rw.max_ammo == 3 and rw.durability == 20
    dmg = rw.use()
    assert dmg == 15 and rw.ammo == 2 and rw.durability == 19
    dmg = rw.use()
    assert dmg == 15 and rw.ammo == 1 and rw.durability == 18
    dmg = rw.use()
    assert dmg == 15 and rw.ammo == 0 and rw.durability == 17
    dmg = rw.use()
    assert dmg == 0
    
    rw.reload(5)
    assert rw.ammo == 3 # capped at max_ammo
    
    # Test Zombies
    fz = FreshZombie()
    assert fz.name == "Fresh Zombie" and fz.health == 30
    fz.take_damage(10)
    assert fz.health == 20
    
    rz = RegularZombie()
    assert rz.name == "Regular Zombie" and rz.health == 50
    
    hz = HeavyZombie()
    assert hz.name == "Heavy Zombie" and hz.health == 100
    
    # Test Apocrysis map size and player setup
    ap = Apocrysis("TestPlayer", map_size=10, seed=1)
    assert ap.map_size == 10
    assert len(ap.map) == 10
    assert ap.strength > 0 and ap.dexterity > 0
    assert ap.health > 0
    assert hasattr(ap, 'status_effects')
    
    # NEW TEST: Battle, Inventory Management, and Stat Modifications
    print("\nRunning advanced feature tests...")
    
    # Test stat modifications (eat/drink/medicine)
    ap_stats = Apocrysis("StatTest", map_size=5, seed=1)
    initial_health = ap_stats.health
    
    ap_stats.backpack.food += 10
    ap_stats.eat()
    assert ap_stats.hunger > 0, "Hunger should increase after eating"
    assert ap_stats.health == min(100, initial_health + 5), "Health should increase by 5 after eating"
    
    ap_stats.backpack.water += 10
    ap_stats.drink()
    assert ap_stats.thirst > 0, "Thirst should increase after drinking"
    assert ap_stats.health == min(100, initial_health + 10), "Health should increase by another 5 after drinking"
    
    ap_stats.backpack.medicine += 1
    current_health = ap_stats.health
    ap_stats.use_medicine()
    assert ap_stats.health == min(100, current_health + 20), "Health should increase by 20 after using medicine"
    
    # Test weapon equipping and battle logic. The starting weapon is
    # the world's (src/loot.py's starter_spec) - test the equip-swap
    # mechanic generically rather than assuming a specific type.
    ap_battle = Apocrysis("BattleTest", map_size=5, seed=1)
    starting_weapon = ap_battle.equipped_weapon
    ap_battle.backpack.weapons.append(MeleeWeapon("Axe", 8, 50))

    assert len(ap_battle.backpack.weapons) == 1, "Backpack should contain the added Axe"
    assert starting_weapon is not None, "A starter class should always start with a weapon equipped"

    # Equip the axe
    ap_battle.equip_weapon("axe")
    assert ap_battle.equipped_weapon.name.lower() == "axe", "Equipped weapon should be Axe after command"
    assert len(ap_battle.backpack.weapons) == 1, "Starting weapon should return to backpack when equipping new weapon"
    assert ap_battle.backpack.weapons[0] is starting_weapon, "Returned weapon should be the original starting weapon"
    
    # Deal one attack round with the newly equipped axe. Not
    # ap_battle.battle(...) - that method was removed as dead code
    # (encounter_zombie() is the real, only combat path now), and
    # encounter_zombie() itself calls input() for the fight/flee
    # prompt, which would hang a non-interactive test run.
    test_zombie = FreshZombie()
    initial_z_health = test_zombie.health
    damage = ap_battle.equipped_weapon.use() + max(0, ap_battle.strength // 3)
    test_zombie.take_damage(damage)
    assert test_zombie.health < initial_z_health, "Zombie health should decrease after taking weapon damage"
    assert 0 <= ap_battle.health <= 100, "Player health must remain within valid bounds"

    print("All tests passed!")
