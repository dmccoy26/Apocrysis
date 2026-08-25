# Auto-extracted from the original monolithic apocrysis.py during
# the src/ restructuring - see README.md for the project layout.

import os

from src.game import Apocrysis
from src.items import Backpack, MeleeWeapon, RangedWeapon
from src.player import PlayerClass
from src.zombies import FreshZombie, RegularZombie, HeavyZombie


def main():
    while True:
        player = None
        # List available save files for convenience
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
            name = input("Enter your name: ")
            
            class_list = [
                "husband", "grandpa", "gamer", "office worker", "engineer", 
                "student", "teacher", "chef", "artist", "prepper", 
                "survivalist", "army ranger", "medic", "hunter", "farmer", 
                "mechanic", "pro gamer", "scavenger", "soldier", "police officer", 
                "doctor", "scientist"
            ]
            
            print("\nAvailable Classes:")
            for i, cls in enumerate(class_list, 1):
                print(f"{i}. {cls}")
                
            while True:
                selection = input("Choose your class (number or name): ").strip().lower()
                if not selection:
                    continue
                    
                try:
                    idx = int(selection)
                    if 1 <= idx <= len(class_list):
                        player_class = class_list[idx - 1]
                        break
                    else:
                        print(f"Please enter a number between 1 and {len(class_list)}.")
                except ValueError:
                    if selection in class_list:
                        player_class = selection
                        break
                    else:
                        print("Invalid selection. Please try again.")

            map_size = 25
            while True:
                try:
                    map_size_input = input(f"Enter the size of the game board (default {map_size}): ")
                    if not map_size_input.strip():
                        break
                    new_map_size = int(map_size_input)
                    if new_map_size <= 0 or new_map_size > 50:
                        raise ValueError
                    map_size = new_map_size
                    break
                except ValueError:
                    print("Invalid input. Please enter a positive integer for the game board size (max 50).")

            player = Apocrysis(name, player_class, map_size)
            
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
    ap = Apocrysis("TestPlayer", "gamer", 10)
    assert ap.map_size == 10
    assert len(ap.map) == 10
    assert ap.player_class is not None
    assert ap.health > 0
    assert hasattr(ap, 'status_effects')
    
    # NEW TEST: Battle, Inventory Management, and Stat Modifications
    print("\nRunning advanced feature tests...")
    
    # Test stat modifications (eat/drink/medicine)
    ap_stats = Apocrysis("StatTest", "gamer", 5)
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
    
    # Test weapon equipping and battle logic
    ap_battle = Apocrysis("BattleTest", "engineer", 5)
    # Engineer starts with a crossbow. Add a melee weapon to test equip swap.
    ap_battle.backpack.weapons.append(MeleeWeapon("Axe", 8, 50))
    
    assert len(ap_battle.backpack.weapons) == 1, "Backpack should contain the added Axe"
    assert isinstance(ap_battle.equipped_weapon, RangedWeapon), "Engineer should start equipped with a ranged weapon"
    
    # Equip the axe
    ap_battle.equip_weapon("axe")
    assert ap_battle.equipped_weapon.name.lower() == "axe", "Equipped weapon should be Axe after command"
    assert len(ap_battle.backpack.weapons) == 1, "Crossbow should return to backpack when equipping new weapon"
    
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
    ap_tasks = Apocrysis("TaskTest", "gamer", 5)
    ap_tasks.add_task("Clear Camp", "Defeat nearby threats.", task_type="combat")
    assert len(ap_tasks.tasks) == 1
    assert ap_tasks.tasks[0].title == "Clear Camp"
    
    print("All tests passed!")
