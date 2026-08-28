# Auto-extracted from the original monolithic apocrysis.py during
# the src/ restructuring - see README.md for the project layout.

import os

from src.game import Apocrysis
from src.items import Backpack, MeleeWeapon, RangedWeapon
from src.mixins.persistence_mixin import profile_filename_for_name
from src.player import PlayerClass
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
        name = input("Enter your name (existing or new): ").strip()
    else:
        name = input("Enter your name: ").strip()

    if name in existing_names:
        profile = Apocrysis.load_profile_by_name(name)
        hardcore = bool(profile.get("hardcore", False)) if profile else False
    else:
        profile = None
        hardcore_choice = input(
            "Play in hardcore mode? Death is permanent - no reloading "
            "this character. (y/n): "
        ).strip().lower()
        hardcore = hardcore_choice in ("y", "yes")

    return name, hardcore, profile


def main_tui():
    # v3 SPRINT step 6: the TUI (src/tui.py's ApocrysisApp) owns its
    # own profile-loading/game construction in on_mount() - the only
    # thing that must happen HERE, in the plain terminal before
    # Textual takes over the screen, is resolving name/hardcore via
    # the picker above (on_mount() re-checks load_profile_by_name()
    # itself for everything else - stats/backpack/weapon - so this
    # isn't duplicating that logic, just the one piece that can't
    # happen inside the TUI without it needing its own terminal
    # prompt before Textual starts).
    from src.tui import ApocrysisApp

    name, hardcore, _profile = _resolve_player_identity()

    app = ApocrysisApp(name=name, hardcore=hardcore)
    app.run()


def main_slice():
    """v4 vertical-slice runner: the hand-authored 'Dam Service Road'
    investigation map, classic print loop, no profiles or story
    preamble. Throwaway experimental scaffolding - see
    docs/ESCAPE_WORLD_DESIGN_ASSESSMENT.md, 'Vertical slice prototype'."""
    player = Apocrysis("Surveyor", slice_mode=True)
    print()
    print("You came in along the reservoir highway. Then the road went")
    print("under water and did not come back. You need to find another")
    print("way out of this valley.")
    print()
    print("Commands: n/s/e/w move, m map, search, journal (j), remember,")
    print("inspect <thing>, i inventory, 'open gate', escape, q quit.")
    print()
    player.run_game_loop()
    if getattr(player, "won", False):
        print("\nYou made it out.")
    elif player.health <= 0:
        print("\nYou didn't make it.")


def main():
    # v3 SPRINT step 1: no class prompt (classes are level-based now -
    # src/player.py's CLASS_TIERS, combat_mixin.py's level_up()) and
    # no re-entering your name/starting-over every launch. A profile
    # (name/level/xp/stats/backpack/weapon - PersistenceMixin's
    # save_profile()/load_profile(), distinct from the full-state
    # named save slots below) auto-loads if one exists; map size is
    # always derived from the carried-forward level
    # (game.py's __init__), not a manual prompt, since v3's whole
    # point is that the map grows with you automatically.
    name, hardcore, profile = _resolve_player_identity()

    while True:
        player = None

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
                level = profile.get("level", 1)
                expeditions_completed = profile.get("expeditions_completed", 0)
                print(f"\nWelcome back, {name} - level {level}.")
            else:
                level = 1
                expeditions_completed = 0

            player = Apocrysis(name, level=level, hardcore=hardcore, expeditions_completed=expeditions_completed)

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
        player.run_game_loop()

        # v3 SPRINT step 1 / hardcore-mode follow-up: save the profile
        # on every way a playthrough ends EXCEPT a hardcore death -
        # "automatic" means the player's name/level/stats are never
        # re-asked for, regardless of why a non-hardcore game ended.
        # A hardcore character who died instead has their profile
        # permanently deleted (delete_profile()), so the next launch
        # can't reload a dead hardcore run under this name - that's
        # the entire point of choosing hardcore. Re-read immediately
        # after so the top of the next loop iteration (or the next
        # process launch) sees the exact same state either way.
        if player.hardcore and player.health <= 0:
            player.delete_profile()
        else:
            player.save_profile(profile_filename_for_name(player.name))

        profile = Apocrysis.load_profile_by_name(name)

        if getattr(player, 'won', False):
            # Real bug found live: winning used to hit the same
            # "break" as quitting/dying, ending the whole program
            # before Apocrysis.prize_for_next_game (set on win) could
            # ever be consumed - it's only checked in __init__, which
            # never ran again once the process exited. Looping back
            # instead of breaking lets the outer while True create a
            # fresh Apocrysis() next, which is exactly what actually
            # grants the earned bonus.
            print("Starting a new game with your earned supplies...\n")
            continue

        if getattr(player, 'quit', False) or player.health <= 0:
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
    
    # Test PlayerClass & Apocrysis initialization
    pc = PlayerClass(100, 100, 100, 0, 10, 10, 10, 10, MeleeWeapon("Knife", 5, 10))
    assert pc.health == 100
    
    # Test Apocrysis map size and player setup
    ap = Apocrysis("TestPlayer", map_size=10, seed=1)
    assert ap.map_size == 10
    assert len(ap.map) == 10
    assert ap.player_class is not None
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
    
    # Test weapon equipping and battle logic. v3: no class choice, so
    # the starting weapon is whatever STARTER_CLASS_NAME's PlayerClass
    # gives (src/player.py) - test the equip-swap mechanic generically
    # rather than assuming a specific starting weapon type.
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
    
    # Test Task System Integration
    ap_tasks = Apocrysis("TaskTest", map_size=5, seed=1)
    ap_tasks.add_task("Clear Camp", "Defeat nearby threats.", task_type="combat")
    assert len(ap_tasks.tasks) == 1
    assert ap_tasks.tasks[0].title == "Clear Camp"
    
    print("All tests passed!")
