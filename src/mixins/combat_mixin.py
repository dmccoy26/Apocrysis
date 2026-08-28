# Auto-extracted from the original monolithic apocrysis.py during
# the src/ restructuring - see README.md for the project layout.

import random

from src.constants import BOLD, GREEN, RESET, STATUS_EFFECT_DAMAGE
from src.items import MeleeWeapon, RangedWeapon
from src.player import PLAYER_CLASSES, TIER_LEVEL_THRESHOLDS, tier_representative
from src.zombies import Zombie, ToxicZombie


# Auto-extracted from the original monolithic apocrysis.py during
# the src/ restructuring - see README.md for the project layout.

import random

from src.constants import BOLD, GREEN, RESET, STATUS_EFFECT_DAMAGE
from src.items import MeleeWeapon, RangedWeapon
from src.player import PLAYER_CLASSES, TIER_LEVEL_THRESHOLDS, tier_representative
from src.zombies import Zombie, ToxicZombie


class CombatMixin:

    def _condition_penalty(self):
        penalty = 0.0
        if self.health < 25:
            penalty += 0.2
        elif self.health < 50:
            penalty += 0.1

        if self.hunger < 20 or self.thirst < 20:
            penalty += 0.2
        elif self.hunger < 40 or self.thirst < 40:
            penalty += 0.1

        if self.fatigue > 80:
            penalty += 0.2
        elif self.fatigue > 50:
            penalty += 0.1

        return max(0.5, 1.0 - penalty)

    def punch(self):
        current_tile = self.map[self.current_position[1]][self.current_position[0]]
        if isinstance(current_tile, Zombie):
            zombie = current_tile
            damage = 2 + max(0, self.strength // 3)
            zombie.take_damage(damage)
            self.io.say(f"You punch the {zombie.name} for {damage} damage.")
            
            if zombie.health <= 0:
                self.io.say(f"The {zombie.name} has been defeated!")
                self.award_xp(25)
                self.handle_loot(zombie.loot_table)
                self._clear_defeated_zombie_tile(zombie)
                self._check_and_complete_goals("kill")
            else:
                # Zombie's turn to attack
                dodge_chance = min(0.5, self.dexterity / 150)
                if random.random() < dodge_chance:
                    self.io.say(f"You deftly dodged the {zombie.name}'s attack!")
                else:
                    self.take_damage(zombie.attack)

                    # ToxicZombie's bite is guaranteed to poison
                    if isinstance(zombie, ToxicZombie):
                        self.status_effects["Poison"] = 4
                        self.io.say("The toxic bite poisons you!")
                    else:
                        status_roll = random.random()
                        if status_roll < 0.15 and "Bleeding" not in self.status_effects:
                            self.status_effects["Bleeding"] = 3
                            self.io.say("You are bleeding! You will take damage each turn.")
                        elif status_roll < 0.25 and "Stun" not in self.status_effects:
                            self.status_effects["Stun"] = 1
                            self.io.say("You have been stunned!")
        else:
            self.io.say("There's nothing to punch here.")

    def encounter_zombie(self, current_tile=None):
        # Use passed tile if available and valid, otherwise generate a
        # random one. Checks the Zombie BASE class (v3 SPRINT step 3
        # fix) - this used to list only FreshZombie/RegularZombie/
        # HeavyZombie by name, so a real bug: SwiftZombie/ToxicZombie/
        # ArmoredZombie placed on the map (world_mixin.py's
        # generate_map()) would silently fail this check and get
        # discarded, replaced with a freshly-rolled random zombie
        # instead of the one actually standing on that tile.
        if current_tile and isinstance(current_tile, Zombie):
            zombie = current_tile
        else:
            zombie = self._select_zombie_for_encounter()
            
        self.io.say(f"Encountered a {zombie.name}! What will you do?")
        _eq_broken = bool(self.equipped_weapon) and getattr(self.equipped_weapon, 'durability', 1) <= 0
        _cur_dmg = 0 if (not self.equipped_weapon or _eq_broken) else self.equipped_weapon.damage
        _better = max(
            (w for w in self.backpack.weapons
             if w.damage > _cur_dmg + 2 and getattr(w, 'durability', 1) > 0),
            key=lambda w: w.damage, default=None,
        )
        if _better is not None:
            _held = ('bare hands' if not self.equipped_weapon
                     else f'broken {self.equipped_weapon.name}' if _eq_broken
                     else self.equipped_weapon.name)
            self.io.say(
                f"(You're carrying a {_better.name} ({_better.damage} dmg) - "
                f"stronger than your {_held}. Flee and 'eq {_better.name}' to switch.)"
            )

        # v3 SPRINT step 3/6: explicit yes/no, re-prompting on
        # anything else - the original "anything other than the
        # literal string 'flee' fights" meant a typo silently became
        # an intentional fight, and vice versa was never even
        # possible (there was no way to be UNCLEAR and get asked
        # again). self.io.ask_yes_no() (step 6's I/O seam) owns the
        # re-prompt loop now - ConsoleIO's version is byte-identical
        # to the loop this replaced; a TUI's TextualIO answers via a
        # real dialog instead of re-reading stdin.
        will_fight = self.io.ask_yes_no("Do you want to fight?")

        if not will_fight:
            # Implement fleeing logic with a certain chance of success
            if random.random() < 0.5:  # Assuming a 50% success rate for fleeing
                self.io.say("Successfully fled from the zombie.")
                return  # Exit the method to avoid the fight
            else:
                self.io.say("Failed to flee! You have to fight the zombie.")

        self.io.say(f"Preparing for battle against the {zombie.name}...")
        self.hunger = max(0, self.hunger - zombie.hunger_cost)
        self.thirst = max(0, self.thirst - zombie.thirst_cost)
        self.fatigue = min(100, self.fatigue + zombie.fatigue_cost)
        while self.health > 0 and zombie.health > 0:
            # Process status effects at start of turn
            if self.status_effects.get("Stun", 0) > 0:
                self.io.say(f"You are stunned! Turn skipped.")
                self.status_effects["Stun"] -= 1
            elif self.equipped_weapon:
                damage = round((self.equipped_weapon.use(self.io) + max(0, self.strength // 3)) * self._condition_penalty())
                
                # Critical hit chance scaled by dexterity
                crit_chance = min(0.25, self.dexterity / 200)
                if random.random() < crit_chance:
                    damage *= 2
                    self.io.say("Critical Hit!")
                    
                zombie.take_damage(damage)
                self.io.say(f"The {zombie.name} takes {damage} damage.")
            else:
                self.io.say("You have no weapon equipped and attempt to fight with your hands!")
                unarmed_damage = round(2 * self._condition_penalty())
                zombie.take_damage(unarmed_damage)
                self.io.say(f"You deal {unarmed_damage} damage with your bare hands.")

            # Process status effects - data-driven via
            # STATUS_EFFECT_DAMAGE (constants.py) so a new damaging
            # status (e.g. ToxicZombie's "Poison", v3 SPRINT step 3)
            # needs no new code path here, only a data entry. Also
            # fixes a real bug: effects previously never expired
            # (the countdown decremented but the key was never
            # removed at 0), so "Bleeding" could never be reapplied
            # after its first trigger and its damage never stopped -
            # contradicts the whole point of a duration.
            for effect in list(self.status_effects.keys()):
                damage = STATUS_EFFECT_DAMAGE.get(effect)
                if damage:
                    self.health -= damage
                    self.io.say(f"You are affected by {effect}! Lost {damage} health.")
                self.status_effects[effect] -= 1
                if self.status_effects[effect] <= 0:
                    del self.status_effects[effect]

            # Check if the zombie has been defeated
            if zombie.health <= 0:
                self.io.say(f"The {zombie.name} has been defeated!")
                self.award_xp(25)
                self.handle_loot(zombie.loot_table)
                self._clear_defeated_zombie_tile(zombie)
                self._check_and_complete_goals("kill")
                return

            # Zombie's turn to attack if it is still alive
            if zombie.health > 0:
                dodge_chance = min(0.5, self.dexterity / 150)
                if random.random() < dodge_chance:
                    self.io.say(f"You deftly dodged the {zombie.name}'s attack!")
                else:
                    self.take_damage(zombie.attack)

                    # ToxicZombie's bite is guaranteed to poison
                    # (v3 SPRINT step 3) - not a chance roll like
                    # Bleeding/Stun below, since resisting poison
                    # would defeat the point of fighting one. Flat
                    # assignment (not +=) refreshes the duration on
                    # a repeat hit rather than stacking simultaneous
                    # damage instances.
                    if isinstance(zombie, ToxicZombie):
                        self.status_effects["Poison"] = 4
                        self.io.say("The toxic bite poisons you!")
                    else:
                        # Chance to inflict status effect
                        status_roll = random.random()
                        if status_roll < 0.15 and "Bleeding" not in self.status_effects:
                            self.status_effects["Bleeding"] = 3
                            self.io.say("You are bleeding! You will take damage each turn.")
                        elif status_roll < 0.25 and "Stun" not in self.status_effects:
                            self.status_effects["Stun"] = 1
                            self.io.say("You have been stunned!")

            # Check for critical health condition for fleeing chance
            if 0 < self.health <= self.max_health * 0.1:
                self.io.say("You are critically wounded!")
                if random.random() < 0.1:  # 10% chance to flee successfully
                    self.io.say("In a desperate move, you managed to flee from the zombie.")
                    return
                else:
                    self.io.say("Unable to flee, you brace yourself for the zombie's attack.")

        if self.health <= 0:
            self.io.say("You are critically wounded and unable to continue the fight!")

    def award_xp(self, amount):
        if amount <= 0: return
        self.xp += amount
        while self.xp >= self.max_xp:
            self.xp -= self.max_xp
            self.level_up()
            self.max_xp = int(self.max_xp * 1.5)

    def level_up(self):
        self.level += 1
        self.strength += 1
        self.dexterity += 1
        self.intelligence += 1
        self.wisdom += 1
        self.max_health += 5
        self.health = min(100, self.health + 10)
        self.io.say(f"{BOLD}{GREEN}Level Up! You are now level {self.level}.{RESET}")
        self._apply_tier_blend_if_crossed()

    def _apply_tier_blend_if_crossed(self):
        # v3 SPRINT step 1: level_up() increments self.level by
        # exactly 1 per call and is already called once per XP-
        # overflow iteration in award_xp()'s while loop - so a big
        # XP gain that crosses multiple tier thresholds already
        # calls level_up() once per level, and this check runs fresh
        # each time. Multi-threshold crossing is correct by
        # construction as long as the check stays HERE (per level_up
        # call) rather than being computed once elsewhere from a
        # final level, which could skip intermediate crossings.
        if self.level not in TIER_LEVEL_THRESHOLDS:
            return

        tier_index = TIER_LEVEL_THRESHOLDS.index(self.level)

        if tier_index == 0:
            return  # tier 0 is the starting baseline, nothing to blend in

        new_rep = PLAYER_CLASSES[tier_representative(tier_index)]
        prev_rep = PLAYER_CLASSES[tier_representative(tier_index - 1)]

        # Additive, never a reset - equipped weapon untouched.
        strength_delta = max(0, new_rep.strength - prev_rep.strength)
        dexterity_delta = max(0, new_rep.dexterity - prev_rep.dexterity)
        intelligence_delta = max(0, new_rep.intelligence - prev_rep.intelligence)
        wisdom_delta = max(0, new_rep.wisdom - prev_rep.wisdom)
        self.strength += strength_delta
        self.dexterity += dexterity_delta
        self.intelligence += intelligence_delta
        self.wisdom += wisdom_delta
        self.max_health += new_rep.health - prev_rep.health
        self.health = min(self.max_health, self.health)

        self.player_class = tier_representative(tier_index)
        self.io.say(
            f"{BOLD}{GREEN}You've grown into a new class: "
            f"{self.player_class}!{RESET}"
        )

    def take_damage(self, damage):
        """
        Reduces the player's health by the specified damage amount,
        after every equipped armor piece absorbs its share in turn
        (equipment-slot investigation, multi-piece follow-up - each
        of the four slots contributes independently, all degrading
        one durability point per hit).
        """
        for piece in self.equipped_armor.values():
            if piece:
                damage = piece.absorb(damage)
        self.health -= damage
        self.io.say(f"The {self.name} takes {damage} damage. Its current health is {self.health}.")
        if self.health <= 0:
            self.io.say(f"The {self.name} has been defeated!")

    def _clear_defeated_zombie_tile(self, zombie):
        """v4 (todo 93edaf83): a tile-based zombie that's been defeated
        must leave the world - generate_map() replaces the tile's
        terrain dict with the Zombie object, and nothing ever restored
        it, so dead 0-HP zombies sat on the map forever. Reverts the
        tile to plain ground. No-op for random roaming encounters
        (no tile)."""
        x, y = self.current_position
        if self.map[y][x] is zombie:
            self.map[y][x] = {'terrain': 'plain', 'content': '-', 'explored': True}
            self.zombie_positions.discard((x, y))

    def handle_loot(self, loot_table):
        # Intelligence increases number of items found from loot tables
        extra_items = max(0, self.intelligence // 25)
        k = min(4, random.randint(1, 3) + extra_items)
        dropped_loot = random.choices(loot_table, k=k)  # Randomly choose items from loot table
        for item in dropped_loot:
            if item == "food":
                self.backpack.food += 1
                self.io.say("You found some food!")
            elif item == "water":
                self.backpack.water += 1
                self.io.say("You found some water!")
            elif item == "medicine":
                self.backpack.medicine += 1
                self.io.say("You found some medicine!")
            elif item == "weapon":
                # Corrected instantiation of MeleeWeapon and RangedWeapon
                weapon = random.choice([
                    MeleeWeapon("Sword", 15, 25),
                    RangedWeapon("Gun", 20, 5)  # Assuming the last number is the ammunition count
                ])

                self.backpack.weapons.append(weapon)
                self.io.say(f"You found a {weapon.name}!")
            elif item == "ammo":
                self.backpack.ammo += random.randint(1, 10)
                self.io.say("You found some ammo!")
