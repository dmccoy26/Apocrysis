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
from src import escape_model


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
            self.io.say(f"You punch the infected for {damage} damage.")
            
            if zombie.health <= 0:
                self.io.say(f"The infected has been defeated!")
                self.award_xp(25)
                self.handle_loot(zombie.loot_table, zombie)
                self._clear_defeated_zombie_tile(zombie)
            else:
                # Zombie's turn to attack
                dodge_chance = min(0.5, self.dexterity / 150)
                if random.random() < dodge_chance:
                    self.io.say(f"You deftly dodged the infected's attack!")
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
            # Zombie Identity Pass: a random-encounter infected gets its
            # identity here (placed ones got theirs at generation).
            if not getattr(zombie, "identity", "") and hasattr(self, "_attach_infected"):
                self._attach_infected(zombie, ("enc", getattr(self, "turns", 0)))

        # Zombie Identity Pass - behaviour flags. Not every infected is
        # a pursuing threat.
        _flags = getattr(zombie, "flags", ())
        if "skittish" in _flags:
            self.announce_event(
                getattr(zombie, "identity_label", "INFECTED"),
                getattr(zombie, "identity_line", "")
                or "It bolts before you get near.",
                "It's gone before you can decide anything.",
                kind="info", level=1)
            self._clear_defeated_zombie_tile(zombie)   # it ran off
            return
        if "passive" in _flags:
            self.announce_event(
                getattr(zombie, "identity_label", "INFECTED"),
                getattr(zombie, "identity_line", ""),
                "It barely reacts. You step around it.",
                kind="info", level=1)
            return   # move_and_search's tile cooldown stops a re-trigger

        terrain = self._encounter_terrain(current_tile)

        # docs/DESIGN_ATTENTION_LANGUAGE.md — GRADE the encounter banner
        # by its actual consequence, not a fixed DANGER flare. Run 7:
        # ~8 identical `‼ ZOMBIE` banners for trivial fights trained the
        # player to auto-fight the one that killed him. A LOW fight now
        # barely interrupts; an EXTREME one stops the game.
        # Only the interactive path can grade (the bot path must not
        # touch the forecast - it draws from `random` and the balance
        # harness must stay byte-identical).
        interactive = hasattr(self.io, "ask_combat_letter")
        outcome = None
        if interactive:
            from src import combat_forecast as cf
            outcome = cf.fight_outcome(self, zombie)
            hp_frac = self.health / max(1, self.max_health)
            lvl = self._encounter_attention_level(outcome, hp_frac)
        else:
            lvl = 2   # unchanged non-interactive behaviour
        _ident = getattr(zombie, "identity_label", "INFECTED")
        self.announce_event(
            _ident,
            *((getattr(zombie, "identity_line", ""),) if getattr(zombie, "identity_line", "") else ()),
            *(("Stop. This is a decision.",) if lvl >= 2 else ()),
            kind="danger", level=lvl)

        # The encounter information card (docs/COMBAT_INFO_SPEC.md).
        # PLAYER-INFORMATION only - changes NO combat / escape / XP /
        # loot math. Interactive ios get [f]/[e]/[w]; a bot io falls
        # through to the old yes/no, so the balance harness is unchanged.
        will_fight = (self._encounter_card(zombie, terrain, outcome) == "fight")

        if not will_fight:
            # docs/DESIGN_ESCAPE_MODEL.md: P(escape) is derived from the
            # encounter (zombie speed class) + the survivor's state
            # (Dex / fatigue / HP) + whether the terrain gives room to
            # run - never a flat constant. The forecast card shows this
            # same number (combat_forecast.escape_pct reads the same
            # function). A slow Armored on open ground is highly
            # escapable; the same Armored in a building is not.
            if random.random() < escape_model.escape_chance_for(self, zombie, terrain):
                self.announce_event(f"You got away from the infected.",
                                    kind="success")
                return  # Exit the method to avoid the fight
            else:
                self.announce_event("Couldn't get away - you have to fight.",
                                    kind="danger")

        self.io.say(f"Preparing for battle against the infected...")
        self.hunger = max(0, self.hunger - zombie.hunger_cost)
        self.thirst = max(0, self.thirst - zombie.thirst_cost)
        self.fatigue = min(100, self.fatigue + zombie.fatigue_cost)
        _combat_round = 0
        while self.health > 0 and zombie.health > 0:
            _combat_round += 1
            # Process status effects at start of turn
            if self.status_effects.get("Stun", 0) > 0:
                self.io.say(f"You are stunned! Turn skipped.")
                self.status_effects["Stun"] -= 1
            elif self.equipped_weapon:
                _dur_before = getattr(self.equipped_weapon, 'durability', None)
                _wdmg = self.equipped_weapon.use(self.io)
                if _wdmg > 0:
                    # strength only helps when the weapon actually
                    # connected - firing an empty gun / swinging a
                    # broken blade must NOT deal a phantom str//3 hit
                    # (playtest: "you can still fire the broken rifle").
                    damage = round((_wdmg + max(0, self.strength // 3)) * self._condition_penalty())
                    crit_chance = min(0.25, self.dexterity / 200)
                    if random.random() < crit_chance:
                        damage *= 2
                        self.io.say("Critical Hit!")
                    zombie.take_damage(damage)
                    self.io.say(f"The infected takes {damage} damage.")
                else:
                    # empty / broken - use() already said why. Fall back
                    # to a bare-hands hit so the turn isn't a pure whiff.
                    _bare = round(2 * self._condition_penalty())
                    zombie.take_damage(_bare)
                    self.io.say(f"You club at it with the {self.equipped_weapon.name} "
                                f"for {_bare} damage.")
                self._weapon_condition_check(_dur_before)
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
            # 1d: skip this round's tick if the move that walked into
            # this fight already ticked status effects this game-turn
            # (_tick_status_effects stamps self._status_tick_turn). Only
            # round 1 can collide; rounds 2+ always tick.
            _pre_ticked = (_combat_round == 1
                           and getattr(self, "_status_tick_turn", None)
                               == getattr(self, "turns", 0))
            if not _pre_ticked:
                for effect in list(self.status_effects.keys()):
                    damage = STATUS_EFFECT_DAMAGE.get(effect)
                    if damage:
                        self.health -= damage
                        self.io.say(f"You are affected by {effect}! Lost {damage} health.")
                    self.status_effects[effect] -= 1
                    if self.status_effects[effect] <= 0:
                        del self.status_effects[effect]
            # this game-turn's status tick is now accounted for - stop
            # the end-of-turn loop pass double-counting it
            self._status_tick_turn = getattr(self, "turns", 0)

            # Check if the zombie has been defeated
            if zombie.health <= 0:
                self.io.say(f"The infected has been defeated!")
                self.award_xp(25)
                self.handle_loot(zombie.loot_table, zombie)
                self._clear_defeated_zombie_tile(zombie)
                return

            # Zombie's turn to attack if it is still alive
            if zombie.health > 0:
                dodge_chance = min(0.5, self.dexterity / 150)
                if random.random() < dodge_chance:
                    self.io.say(f"You deftly dodged the infected's attack!")
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

    def _encounter_attention_level(self, outcome, hp_frac):
        """docs/DESIGN_ATTENTION_LANGUAGE.md — the danger-row mapping:
        (P(win), cost, HP) -> interruption level 0..3."""
        from src import combat_forecast as cf
        fp = outcome["win_pct"]
        p90 = outcome["p90_frac"]
        if fp < 15:
            return 3                                   # ~unwinnable
        tier = cf.threat_tier(fp, p90)
        if fp < 35 or tier == "SEVERE":
            return 3 if hp_frac < 0.35 else 2
        if fp < 65 or tier == "HIGH":
            return 2                                   # a real decision
        if tier == "MODERATE":
            return 2 if hp_frac < 0.40 else 1
        return 0 if hp_frac > 0.55 else 1              # LOW / trivial

    def _encounter_terrain(self, current_tile=None):
        """Terrain name at the encounter, for the escape model. A
        map-placed zombie has overwritten its tile dict, so fall back to
        None (escape_model treats an unknown terrain as 'reduced')."""
        cell = current_tile
        if not isinstance(cell, dict):
            x, y = self.current_position
            cell = self.map[y][x]
        return cell.get('terrain') if isinstance(cell, dict) else None

    def _encounter_card(self, zombie, terrain=None, outcome=None):
        """Show the encounter information card; return 'fight' | 'escape'.
        [w] opens the weapon stats window and re-shows the card - no turn
        passes. docs/COMBAT_INFO_SPEC.md. Changes no combat math.

        A bot io has no `ask_combat_letter`; it falls through to the
        pre-existing yes/no so the balance harness is unchanged."""
        if not hasattr(self.io, "ask_combat_letter"):
            # bot / non-interactive: the old path exactly, no forecast
            # (the forecast draws from `random` and would perturb the
            # combat RNG stream - balance harness must be untouched).
            return "fight" if self.io.ask_yes_no("Do you want to fight?") else "escape"

        from src import combat_forecast as cf
        interactive = True
        while True:
            w = self.equipped_weapon
            wname = w.name if w else "bare hands"
            wdmg = getattr(w, "damage", 0) if w else 0
            oc = outcome if outcome is not None else cf.fight_outcome(self, zombie)
            fp = oc["win_pct"]
            ep = cf.escape_pct(self, zombie, terrain)
            tier = cf.threat_tier(fp, oc["p90_frac"])
            self.io.say("")
            self.io.say(f"  --- {getattr(zombie, 'identity_label', 'INFECTED').upper()} ---")
            _line = getattr(zombie, "identity_line", "")
            if _line:
                self.io.say(f"  {_line}")
            self.io.say(f"  {cf.danger_note(zombie)}")
            self.io.say(f"  Threat:  {tier}")
            self.io.say(f"  With your {wname} ({wdmg} dmg):   "
                        f"Fight ~{fp}%    Escape ~{ep}%")
            if oc["p90_frac"] is not None and fp >= 65 and oc["p90_frac"] >= 0.45:
                self.io.say("  You'll probably win this - but expect to be "
                            "near death by the end.")
            if fp < 50:
                self.io.say("  If the escape fails, you're fighting it anyway.")
            self.io.say(f"  Your weapon is {cf.weapon_verdict(fp, oc['p50_frac'])}.")
            bw = cf.better_weapon(self, zombie)
            if bw is not None:
                self.io.say(f"  In your pack: {bw[0].name} (~{bw[1]}%) would help"
                            + (" - press w." if interactive else "."))
            if not interactive:
                return "fight" if self.io.ask_yes_no("Do you want to fight?") else "escape"
            letter = self.io.ask_combat_letter()
            if letter == "w":
                self._weapon_stats_window(zombie)
                continue
            return "fight" if letter == "f" else "escape"

    def _weapon_stats_window(self, zombie):
        """[w] from the encounter card: fight chance for every weapon the
        survivor is carrying, and equip one before the fight."""
        from src import combat_forecast as cf
        rows = cf.all_weapon_forecasts(self, zombie)
        self.io.say("")
        self.io.say("  WEAPONS - estimated fight chance vs this target:")
        for i, (wpn, pct, verdict) in enumerate(rows, 1):
            tag = "  (equipped)" if wpn is self.equipped_weapon else ""
            self.io.say(f"   [{i}] {wpn.name} ({wpn.damage} dmg){tag}   ~{pct}%   {verdict}")
        pick = (self.io.ask("  Equip which? (number, or Enter to keep): ") or "").strip()
        if pick.isdigit() and 1 <= int(pick) <= len(rows):
            self.equip_weapon(rows[int(pick) - 1][0].name)

    def _weapon_condition_check(self, dur_before):
        """React to the equipped weapon wearing down mid-fight. A worn
        warning once at the threshold; a loud break + auto-swap to the
        best usable backpack weapon when it hits 0. Playtest: a Steel
        Sword broke silently and the player fought on with a dead
        weapon without noticing."""
        w = self.equipped_weapon
        # A ranged weapon that just ran dry is as useless as a broken
        # one - swap to a spare rather than "Out of ammo!" every turn.
        if isinstance(w, RangedWeapon) and w.ammo <= 0:
            spare = max(
                (b for b in self.backpack.weapons
                 if getattr(b, 'durability', 1) > 0
                 and not (isinstance(b, RangedWeapon) and b.ammo <= 0)),
                key=lambda b: b.damage, default=None,
            )
            if spare is not None:
                self.backpack.weapons.remove(spare)
                self.backpack.weapons.append(w)
                self.equipped_weapon = spare
                self.announce_event(
                    "Out of ammo.",
                    f"Your {w.name} is empty - you switch to your {spare.name} ({spare.damage} dmg).",
                    kind="warn",
                )
            return

        dur = getattr(w, 'durability', None) if w is not None else None
        if w is None or dur is None or dur_before is None:
            return
        if dur <= 0 < dur_before:
            spare = max(
                (b for b in self.backpack.weapons if getattr(b, 'durability', 1) > 0),
                key=lambda b: b.damage, default=None,
            )
            if spare is not None:
                self.backpack.weapons.remove(spare)
                self.backpack.weapons.append(w)
                self.equipped_weapon = spare
                self.announce_event(
                    "Weapon broken.",
                    f"Your {w.name} is done - you switch to your {spare.name} ({spare.damage} dmg).",
                    kind="warn",
                )
            else:
                self.equipped_weapon = None
                self.announce_event(
                    "Weapon broken.",
                    f"Your {w.name} is done and you have nothing else. Fighting with your hands.",
                    kind="warn",
                )
        elif 0 < dur <= 5 and not getattr(w, '_worn_warned', False):
            w._worn_warned = True
            self.io.say(f"⚠ Your {w.name} is badly worn - {dur}/{w.max_durability} left.")

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
        # 1d playtest: this used to read "The Cole takes 14 damage. Its
        # current health is 83." - definite-article + name + "Its",
        # identical phrasing to a zombie taking a hit, so mid-fight you
        # couldn't tell who was winning. Player-voiced now.
        self.io.say(f"You take {damage} damage.  ({max(0, self.health)} HP left)")
        if self.health <= 0:
            self.io.say("You go down.")

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

    # Zombie Identity Pass: lore loot-categories -> the game's concrete
    # loot outcomes. A bias, not a rule - the archetype's own table
    # stays in the pool so a nurse can still turn up nothing.
    _LEAN_TO_LOOT = {
        "food": ("food", "food"), "water": ("water", "water"),
        "medical": ("medicine", "medicine"), "outdoor": ("water", "food"),
        "ammo": ("ammo", "ammo"), "tactical": ("ammo", "weapon"),
        "tools": ("weapon",), "household": ("food", "medicine"),
        "occupational": (), "personal": (), "light": (), "radio": (),
        "fuel": (), "spent": (), "damaged": (), "nothing": (),
    }

    def handle_loot(self, loot_table, zombie=None):
        # Intelligence increases number of items found from loot tables
        extra_items = max(0, self.intelligence // 25)

        # the rare, uncomfortable tier (child / elderly) carries next to
        # nothing of use - the point is what they had, not a reward.
        if getattr(zombie, "_loot_poor", False):
            if random.random() < 0.4:
                self.io.say("A small pack. Inside: a crushed snack, half a "
                            "water bottle, a few things that meant something "
                            "to someone.")
                self.backpack.water += 1
            else:
                self.io.say("Whatever they had on them isn't any use to you.")
            return

        pool = list(loot_table)
        for _cat in getattr(zombie, "_loot_lean", ()):
            pool.extend(self._LEAN_TO_LOOT.get(_cat, ()))
        if not pool:
            pool = list(loot_table) or ["food"]

        if getattr(zombie, "situation", "") == "last_stand":
            k = min(2, random.randint(0, 2) + extra_items)
        else:
            k = min(4, random.randint(1, 3) + extra_items)
        dropped_loot = random.choices(pool, k=k) if k else []
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
