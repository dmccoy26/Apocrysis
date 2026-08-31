# Auto-extracted from the original monolithic apocrysis.py during
# the src/ restructuring - see README.md for the project layout.
#
# v3 SPRINT step 2: map generation redesign - map size/town distance/
# obstacle density all scale with the player's level (self.level, set
# by game.py's __init__ before generate_map() runs - see the
# governing invariant in the sprint plan: this only ever happens at
# NEW-game creation, never a mid-game resize). Uses self.rng (a
# per-instance, seedable random.Random - game.py's __init__) instead
# of the bare random module, so map generation is reproducible in
# tests.

from collections import deque

import random

from src.constants import (
    BOLD, GREEN, RESET,
    IMPASSABLE_TERRAIN as _DEFAULT_IMPASSABLE,
    MAX_DAY_DIFFICULTY_FACTOR, ELITE_MIN_EXPEDITION, ELITE_STAT_MULTIPLIER,
    TERRAIN_MOVE_MINUTES as _DEFAULT_MOVE_MINUTES, LOOT_WEAPON_TABLE, ARMOR_TABLE,
    ZOMBIE_MAP_DENSITY, ENCOUNTER_CHANCE_DAY, ENCOUNTER_CHANCE_NIGHT,
)
from src.items import MeleeWeapon, RangedWeapon, Armor
from src.zombies import (
    Zombie, FreshZombie, RegularZombie, HeavyZombie,
    SwiftZombie, ToxicZombie, ArmoredZombie,
)


class WorldMixin:

    # Phase F: terrain vocabulary is world-owned (world.terrain). A world
    # that doesn't set it falls back to the default world's tables.
    @property
    def _impassable_terrain(self):
        t = getattr(self.world, "terrain", None)
        return t.impassable if t is not None else _DEFAULT_IMPASSABLE

    @property
    def _terrain_move_minutes(self):
        t = getattr(self.world, "terrain", None)
        return t.move_minutes if t is not None else _DEFAULT_MOVE_MINUTES

    # v4 (todo 7db3c4b5): why a place is empty, one line on the way in.
    # The KEYS are the engine's abandonment-cause vocabulary (a per-tile
    # RNG draw in generate_map - do not change them). The TEXT is
    # world-owned: a world supplies world.prose["abandonment_flavour"]
    # with the same keys; this generic set is the fallback.
    _ABANDONMENT_FLAVOUR = {
        'evacuated': "Chairs pushed back, things half-done, a door left open. People left here fast.",
        'barricaded': "Sealed from the inside. Whoever did it isn't here now.",
        'burned': "Scorched and sagging. Something burned here, a while ago.",
        'looted': "Everything open, pulled out and dropped. Someone stripped this place.",
        'occupied_recently': "Signs of use - warmer than the dust says. Someone was here.",
        'sealed': "Shut from the outside. Someone made a decision about this space.",
        'flooded': "Standing water and a tide line up the wall. Something here holds water and lets it go.",
        'quiet': "Undisturbed. Dust on every surface. It was just left.",
    }

    # v4 (todo 457c93a6): zone types. rural/suburban/industrial/
    # downtown are civilisation; wilderness is the untouched land.
    _ZONE_TYPES = ('rural', 'suburban', 'industrial', 'downtown', 'wilderness')

    # 2D.1: per-zone multipliers on the expedition-scaled zombie weight
    # vector (order: Fresh, Regular, Heavy, Swift, Toxic, Armored).
    _ZONE_ZOMBIE_BIAS = {
        'rural':      (1.3, 1.1, 0.7, 0.8, 0.9, 0.6),
        'suburban':   (1.1, 1.2, 0.9, 1.4, 0.9, 0.8),
        'industrial': (0.8, 1.0, 1.4, 0.9, 1.1, 1.6),
        'downtown':   (0.9, 1.1, 1.2, 1.5, 1.2, 1.1),
        'wilderness': (1.5, 1.2, 0.8, 1.0, 0.6, 0.5),
    }

    # 2D.2: contextual loot weights per zone (over the base loot pool
    # food/water/medicine/ammo/weapon/armor). Identity of what a place
    # has, not just rarity - a rural building leans food/tools, a
    # downtown one leans medicine/weapons.
    _ZONE_LOOT_BIAS = {
        # armor: the rural/wilderness 0.5x penalty was removed (was
        # directly fighting the intended armor progression - see
        # docs/ARMOR_INVESTIGATION_RESULTS.md: acquisition, not the
        # ARMOR_TABLE bands, is the T0-6 bottleneck, and early maps are
        # rural). Armor strength is unchanged; this only changes how
        # often the player gets a chance to assemble the loadout.
        'rural':      {'food': 2.0, 'water': 1.6, 'medicine': 0.7, 'ammo': 0.6, 'weapon': 0.8, 'armor': 1.0},
        'suburban':   {'food': 1.3, 'water': 1.3, 'medicine': 1.1, 'ammo': 0.8, 'weapon': 1.0, 'armor': 1.0},
        'industrial': {'food': 0.7, 'water': 0.8, 'medicine': 0.7, 'ammo': 1.4, 'weapon': 1.5, 'armor': 1.6},
        'downtown':   {'food': 0.9, 'water': 0.9, 'medicine': 1.6, 'ammo': 1.3, 'weapon': 1.4, 'armor': 1.2},
        'wilderness': {'food': 1.4, 'water': 1.4, 'medicine': 0.6, 'ammo': 0.9, 'weapon': 0.9, 'armor': 1.0},
    }


    def _current_zone(self):
        cell = self.map[self.current_position[1]][self.current_position[0]]
        return cell.get('zone', 'rural') if isinstance(cell, dict) else 'rural'

    # --------------------------------------------------
    # Map Generation
    # --------------------------------------------------

    """Tier 6-9 expedition design summary (closes open questions):
    - Contiguous terrain biomes via chunk clustering instead of per-tile rolls.
    - Slow/exhausting swamp terrain type, with waders mitigating water/swamp slowdown.
    - Location-aware resting in buildings (heals/fatigue recovery).
    - repair_kit crafting recipe (level 8+) for sustained gear upkeep.
    - Diagnosed real cause of the tier 6-9 wall: weapon/armor power plateaus while zombie composition keeps escalating (see _select_zombie_for_encounter()).

    Explicitly out of scope for this pass: per-settlement discovery so decoy settlements genuinely differ from the real objective (currently settlement_explored is one global flag set by entering ANY settlement). That remains a separate, not-yet-implemented change.
    """
    def generate_map(self):
        # Phase C (C.1): the base-map pipeline lives in src/worldgen now.
        # This method is the orchestrator: worldgen builds terrain /
        # boundary / spawn / settlements, then the engine embeds the
        # mystery, guarantees reachability, and places zombies. RNG
        # order is unchanged from pre-C.1.
        from src.worldgen import MapGenerator
        gen = MapGenerator(self, variant=getattr(self, '_mapgen', 'v1'))
        town_center = gen.generate()

        # v4 Phase C: build this expedition's escape mystery onto the
        # generated map, and point self.knowledge at its catalogue.
        from src.escape import build_mystery
        # A.4.2: each expedition targets the next un-known WorldFact.
        _target = None
        _wi = getattr(self, 'world_investigation', None)
        if _wi is not None:
            _target = _wi.next_target()
        # E.2: the last expedition is the bespoke finale - it always
        # targets the world's finale.converge_fact (converging the whole
        # investigation), never the random roll.
        _fin = self.world.finale
        _converge = _fin.converge_fact if _fin is not None else None
        _finale = (_converge is not None
                   and self.expeditions_completed >= self.world.manifest.campaign_length - 1
                   and _wi is not None
                   and _wi.fact(_converge) is not None)
        if _finale:
            _target = _converge

        # C.3.1: guarantee a mystery instead of tuning toward one. v2's
        # irregular valley can occasionally grow too cramped for the
        # three building sites a mystery needs (~1.3% pre-fix); when that
        # happens, regenerate the base map and try again rather than
        # shipping a story-less "reach the town" expedition. v1 is frozen
        # and never hits the degenerate path, so the loop runs exactly
        # once for v1 - RNG consumption and byte-identity are unchanged.
        _max_map_tries = 12 if getattr(self, '_mapgen', 'v1') in ('v2', 'landscape') else 1
        self.mystery = None
        _mystery_exc = None
        for _try in range(_max_map_tries):
            if _try > 0:
                town_center = gen.generate()
            try:
                _candidate = build_mystery(self, target_fact=_target)
            except RuntimeError as exc:
                _candidate, _mystery_exc = None, exc
            if _candidate is not None:
                self.mystery = _candidate
                break
        if self.mystery is None and _mystery_exc is not None:
            if getattr(self, '_strict_mystery', False):
                raise _mystery_exc
            self.io.say(f"(world generation note: {_mystery_exc})")
        if self.mystery is not None:
            self.knowledge = self.mystery.knowledge

        # E.2: stamp the finale onto the built mystery - a distinct
        # frame over the same generated map. The command compound, the
        # antenna mast, the checkpoint road out (no mountain gap here).
        if _finale and self.mystery is not None:
            m = self.mystery
            m.is_finale = True
            m.escape_kind = _fin.escape_kind
            for _role, _lab in _fin.site_labels.items():
                if _role in m.sites:
                    m.site_labels[_role] = _lab
                    _sx, _sy = m.sites[_role]
                    _c = self.map[_sy][_sx]
                    if isinstance(_c, dict):
                        _c['site_label'] = _lab

        # v4 (todo 7db3c4b5): variable abandonment - a generated CAUSE
        # for every building/settlement tile being empty.
        causes = list(self._ABANDONMENT_FLAVOUR)
        for row in self.map:
            for cell in row:
                if isinstance(cell, dict) and cell.get('terrain') in ('building', 'town'):
                    cell['abandonment'] = self.rng.choice(causes)

        # Connectivity guarantee (#7) - never ship an unreachable REAL
        # Town Center. Decoy settlements are best-effort only.
        gen.ensure_reachable(self.current_position, town_center)

        # C.2: the connectivity graph. Nodes = spawn, the exit, every
        # mystery site, the real town centre. Reachability becomes a
        # property we assert, not one we hope for, and the zombie-free
        # corridor is a graph query.
        spawn = self.current_position
        from src.worldgen.graph import MapGraph
        _nodes = {'spawn': spawn}
        if town_center is not None:
            _nodes['town'] = tuple(town_center)
        _mystery_nodes = []
        if self.mystery is not None:
            _nodes['exit'] = self.mystery.escape_tile
            _mystery_nodes.append('exit')
            for _role, _xy in self.mystery.sites.items():
                _nodes[f'site_{_role}'] = _xy
                _mystery_nodes.append(f'site_{_role}')
        _required = list(_mystery_nodes) + (['town'] if 'town' in _nodes else [])
        self._map_graph = MapGraph(self.map, (self.map_w, self.map_h), _nodes)
        _blocked = [nm for nm in self._map_graph.unreachable_from('spawn')
                    if nm in _required]
        if _blocked:
            raise RuntimeError(
                "generate_map(): connectivity graph - unreachable required "
                f"node(s): {_blocked}"
            )

        # Zombie placement (frozen balance) - unchanged shape.
        total_tiles = self.map_w * self.map_h
        num_zombies = int(total_tiles * ZOMBIE_MAP_DENSITY)

        placed_zombies = 0
        attempts = 0
        max_attempts = max(200, num_zombies * 20)

        # v4: never bury a mystery site / obstacle / escape tile - OR the
        # zombie-free corridor to one - under a zombie. Same BFS tiles as
        # the old N-separate-walks approach, now one graph query.
        protected = set()
        if self.mystery is not None:
            protected = set(self.mystery.sites.values()) | {self.mystery.escape_tile}
            protected |= self._map_graph.critical_path_tiles('spawn', *_mystery_nodes)

        def _passable_neighbours(x, y):
            n = 0
            for ax, ay in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if not (0 <= ax < self.map_w and 0 <= ay < self.map_h):
                    continue
                c = self.map[ay][ax]
                t = c.get('terrain') if isinstance(c, dict) else None
                if isinstance(c, Zombie) or (t is not None and t not in self._impassable_terrain):
                    n += 1
            return n

        while placed_zombies < num_zombies and attempts < max_attempts:
            attempts += 1
            x = self.rng.randint(0, self.map_w - 1)
            y = self.rng.randint(0, self.map_h - 1)
            cell = self.map[y][x]
            if (
                isinstance(cell, dict)
                and cell.get('terrain') not in self._impassable_terrain
                and cell.get('terrain') not in ('town', 'water')
                and (x, y) != spawn and abs(x - spawn[0]) + abs(y - spawn[1]) > 1
                and (x, y) not in protected
            ):
                z = self._select_zombie_for_encounter()
                # docs/DESIGN_ESCAPE_MODEL.md §2: an avoid-tier (slow)
                # zombie must not be walked into blind in a dead end or
                # inside a building - "evade" needs somewhere to go. If
                # the tile can't support a disengage, downgrade the
                # SUBCLASS to a Regular (keeping the rolled difficulty
                # scaling and elite flag) rather than re-rolling - so
                # this consumes no extra RNG and the map stays
                # seed-deterministic.
                from src.zombies import speed_class_of as _sc
                from src.zombies import RegularZombie as _Reg
                if _sc(z) == 'slow' and (
                    cell.get('terrain') == 'building'
                    or _passable_neighbours(x, y) < 3
                ):
                    _elite = z.name.startswith("Elite ")
                    _h, _a = z.health, z.attack
                    z = _Reg()
                    z.health, z.attack = _h, _a
                    if _elite:
                        z.name = "Elite " + z.name
                # Zombie Identity Pass: attach who this was, from a
                # dedicated RNG keyed on the tile - never self.rng, so
                # the map (and the golden fixture) is untouched.
                self._attach_infected(z, (x, y), anchor=self._infected_anchor_at(x, y))
                self.map[y][x] = z
                placed_zombies += 1

        return self.map

    # -- Zombie Identity Pass (docs/ZOMBIE_IDENTITY_PASS.md) ----------

    def _infected_anchor_at(self, x, y):
        """A soft anchor tag for an infected placed at (x, y): the
        building content letter, or the zone. Mechanism-specific tags
        (clinic / school / airfield / …) come later with building
        content tags; until then those identities just spawn thinner
        everywhere."""
        cell = self.map[y][x] if 0 <= y < self.map_h and 0 <= x < self.map_w else None
        if isinstance(cell, dict):
            c = cell.get("content")
            if c in ("R", "S"):
                return c
            z = cell.get("zone")
            if z == "wilderness":
                return "wilderness"
        return None

    def _attach_infected(self, z, key, anchor=None):
        import random as _r
        _pop = self.world.population
        if _pop is None:
            return
        arch = getattr(z, "ARCHETYPE", None) or "common"
        rng = _r.Random(hash(("infected", getattr(self, "_seed", 0),
                              getattr(self, "name", ""), key, arch,
                              z.name)))
        exp = getattr(self, "expeditions_completed", 0)
        v = _pop.pick_identity(arch, exp, rng, anchor=anchor)
        sit = _pop.pick_situation(v, exp, rng)
        conf = _pop.confidence(exp, rng)
        z.identity = v.id
        # Phase F §10.2: the world's population module may use what the
        # player has established about the hostiles to shift how they
        # read (The Wake: "a security officer" -> "one of the changed").
        # World 1 ignores the hint. Pass known-milestone ids.
        _wi = getattr(self, "world_investigation", None)
        _hint = tuple(_wi.milestones_known()) if _wi is not None else ()
        try:
            z.identity_label, z.identity_line = _pop.describe(v, conf, _hint)
        except TypeError:
            z.identity_label, z.identity_line = _pop.describe(v, conf)
        z.situation = sit
        z.flags = tuple(v.flags)
        z._loot_lean = _pop.loot_pool(v, sit)
        z._loot_poor = v.rare   # the child / elderly tier carries ~nothing useful

    # v4 Phase B stopgap: until Stage 4's generator produces real
    # Escape Proofs, this surfaces occasional flavour "clues" in
    # buildings so the journal/remember/inspect interface (KnowledgeMixin)
    # has real content to render. These are standalone Known facts with
    # no deduction chain - NOT loot, they route to self.knowledge, never
    # the backpack (design doc: evidence must not be "just another loot
    # roll"). Phase F: the text is world-owned (world.prose["ambient_
    # clues"], list of (blurb, journal_line)); WORLD_1_LORE_PASS
    # replaces this whole path with authored per-band lore.

    def _maybe_surface_clue(self):
        clues = self.world.prose.get("ambient_clues", ())
        if not clues:
            return
        seen = getattr(self, '_clue_tiles', None)
        if seen is None:
            seen = self._clue_tiles = set()
        pos = self.current_position
        if pos in seen:
            return
        seen.add(pos)
        # A dedicated per-tile RNG, NOT self.rng - cosmetic flavour
        # must not perturb the seeded map-generation / loot sequence
        # tests depend on, and must not flake tests that assert on
        # find_loot output. Deterministic given (game, tile).
        clue_rng = random.Random(hash(('phase-b-clue', self.name, pos)))
        if clue_rng.random() >= 0.18:
            return
        available = [c for c in clues
                     if c[0] not in getattr(self, '_clue_texts_used', set())]
        if not available:
            return
        blurb, statement = clue_rng.choice(available)
        used = getattr(self, '_clue_texts_used', None)
        if used is None:
            used = self._clue_texts_used = set()
        used.add(blurb)
        self.io.say(blurb)
        self.knowledge.add_clue(statement, evidence_text=blurb)





    def _spot_landmarks(self):
        """v4 Phase A (todo 7ecd39cc): the first time an unvisited
        building/settlement tile comes into view, say so once - a
        distant sighting, distinct from the 'You enter a building'
        message on actually reaching one. This is also the
        discover-before-understand beat (2C.3): you see a structure
        before you know what's in it."""
        seen = getattr(self, '_landmarks_spotted', None)
        if seen is None:
            seen = self._landmarks_spotted = set()
        px, py = self.current_position
        r = self.visibility_radius
        new_here = []
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                x, y = px + dx, py + dy
                if not (0 <= x < self.map_w and 0 <= y < self.map_h):
                    continue
                if abs(dx) + abs(dy) > r or (x, y) in seen or (x, y) in self.visited:
                    continue
                cell = self.map[y][x]
                if not isinstance(cell, dict):
                    continue
                is_building = cell.get('terrain') == 'building'
                is_settlement = cell.get('terrain') == 'town'
                if is_building or is_settlement:
                    seen.add((x, y))
                    new_here.append('settlement' if is_settlement else 'building')
        if not new_here:
            return
        if 'settlement' in new_here:
            self.io.say("Rooftops in the distance - there's a settlement out there.")
        elif getattr(self, '_building_sightings', 0) < 3:
            # After a few, the player has the idea - a building-dense map
            # would otherwise fire this almost every move (playtest:
            # reading fatigue). Settlements always announce.
            self._building_sightings = getattr(self, '_building_sightings', 0) + 1
            self.io.say("You spot a building standing alone in the distance.")

    def _spot_threats(self):
        """docs/DESIGN_ESCAPE_MODEL.md §2 - warning before contact for an
        avoid-tier threat. When a map-placed slow zombie (Heavy /
        Armored) first comes into view, say so once, BEFORE the player
        walks onto its tile - so "recognise -> assess -> disengage" has
        somewhere to happen. Random encounters have no pre-contact
        phase; this only covers the placed guardians."""
        from src.zombies import speed_class_of as _sc
        seen = getattr(self, '_threats_spotted', None)
        if seen is None:
            seen = self._threats_spotted = set()
        px, py = self.current_position
        r = self.visibility_radius
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if abs(dx) + abs(dy) > r or (dx == 0 and dy == 0):
                    continue
                x, y = px + dx, py + dy
                if not (0 <= x < self.map_w and 0 <= y < self.map_h):
                    continue
                cell = self.map[y][x]
                if not isinstance(cell, Zombie) or (x, y) in seen:
                    continue
                seen.add((x, y))
                if _sc(cell) == 'slow':
                    self.announce_event(
                        f"something heavy is moving up ahead",
                        "Big, slow, armoured - not a fight you want on bad "
                        "ground. Keep the open country at your back.",
                        kind="warning")

    def _spot_route_landmark(self):
        """audit 1b (docs/DESIGN_SPATIAL_LANGUAGE.md) - the physical
        landmark beat. The route out of the valley is a real feature -
        a dam, a mast, a tunnel mouth - visible from a distance, BEFORE
        the player knows it is the way out and independent of the '!'
        marker. Names the feature and the direction to it, once, on
        line of sight. The marker (once earned) is confirmation; this
        is what the eyes find first (design principle 2 /
        discover-before-understand)."""
        m = getattr(self, 'mystery', None)
        if m is None or getattr(self, '_route_landmark_spotted', False):
            return
        from src.escape import MECHANISMS
        feature = getattr(m, 'mech_landmark', '')   # Phase F §10.1: world-owned
        route = m.sites.get('route')
        if not feature or not route:
            return
        known = 'F_ROUTE' in m.knowledge.facts_known()
        # a reveals_route mechanism deliberately withholds the route
        # until the RESPONSE names it - don't point at it early.
        if MECHANISMS.get(m.mechanism, {}).get('reveals_route') and not known:
            return
        px, py = self.current_position
        if abs(route[0] - px) + abs(route[1] - py) > self.visibility_radius + 4:
            return  # a tall landmark carries a little further than sight
        self._route_landmark_spotted = True
        from src.nav import bearing
        b = bearing(self.current_position, route)
        title = f"a landmark to the {b}" if b else "a landmark nearby"
        body = feature + ("." if b else ", close by.")
        _rn = self.world.prose.get("region_noun", "here")
        self.announce_event(
            title, body,
            *((f"That's the way out of {_rn}.",) if known else ()),
            kind="discovery", level=1)

    def _spot_leads(self):
        """docs/DESIGN_SPATIAL_LANGUAGE.md - the approach beat. When a
        mystery site you've LEARNED about (its '!' marker is already on
        the map) first comes within sight, name it in the event stream -
        "you can make out the ranger station ahead" - so the marker on
        the map connects to a thing you're walking toward. One line per
        site. 'route' is handled by _spot_route_landmark (1b) instead."""
        m = getattr(self, 'mystery', None)
        if m is None:
            return
        seen = getattr(self, '_leads_spotted', None)
        if seen is None:
            seen = self._leads_spotted = set()
        px, py = self.current_position
        r = self.visibility_radius
        named = getattr(self, '_mystery_named', set())
        for role, xy in m.sites.items():
            if role == 'route' or role in seen or xy is None:
                continue  # 'route' -> _spot_route_landmark (audit 1b)
            if abs(xy[0] - px) + abs(xy[1] - py) > r:
                continue
            # only if the player already has the marker (knows the fact
            # / has been there) - _mystery_site_mark decides that; reuse
            # its answer rather than re-deriving.
            if not self._mystery_site_mark(*xy):
                continue
            seen.add(role)
            label = m.site_labels.get(role)
            if label and role not in named:
                self.announce_event(f"you can make out {label} ahead",
                                    "It's the marked spot - head for it.",
                                    kind="discovery", level=1)


    def finish_expedition(self, reason="found the way out"):
        """Shared win finalisation for BOTH v4 win paths - the
        generated-mystery escape (mystery_try_escape) and the
        no-mystery fallback (reaching the Town Center). Increments the
        expedition counter, prints the ordinary/campaign-complete
        message, and stages the next-game supply prize."""
        self.won = True
        self.expeditions_completed += 1
        self.__class__.prize_for_next_game = True
        if self.expeditions_completed >= self.world.manifest.campaign_length:
            self.io.say(
                f"\n{BOLD}{GREEN}You {reason} after {self.expeditions_completed} "
                f"expeditions - the outbreak is finally behind you. "
                f"CAMPAIGN COMPLETE!{RESET}\n"
            )
            # E.3: the finale (mystery_mixin._finale_choice) already
            # printed the chosen ending + the retrospective. Otherwise
            # (the bot / a non-finale completion) print the plain one.
            if not getattr(self.__class__, '_campaign_ending', None):
                from src.campaign import campaign_retrospective
                self.io.say(campaign_retrospective(
                    getattr(self.__class__, '_used_mechanisms', []), self.world))
            self.io.say(f"\n{BOLD}Your story in this outbreak ends here.{RESET}\n")
            self.backpack.food += 10
            self.backpack.water += 10
            self.backpack.medicine += 5
            self.backpack.ammo += 20
        else:
            self.io.say(
                f"\n{BOLD}{GREEN}You {reason}. You WIN this expedition!{RESET}\n"
            )
            self.io.say(f"{BOLD}A stash of supplies awaits your next game.{RESET}\n")





    _ZOMBIE_BASE_STATS = {
        FreshZombie: (30, 5),
        RegularZombie: (50, 10),
        HeavyZombie: (100, 20),
        SwiftZombie: (25, 15),
        ToxicZombie: (40, 8),
        ArmoredZombie: (120, 15),
    }

    # Campaign-difficulty diagnosis (resolves open question of WHY the 
    # campaign difficulty curve breaks at tiers 6-9): a 15-campaign run 
    # (tools/balance_autoplay.py --campaign, seed 11, 30-attempt cap) with 
    # the newer failure-reason and player-power-vs-expedition-power telemetry 
    # shows 100% of every failed attempt at EVERY expedition tier (0 through 9) 
    # is 'died: zombie combat' - zero timeouts, zero environmental deaths. So 
    # the tier 6-9 wall is not a navigation/exploration/pacing problem, it's 
    # purely a combat-power problem. The real cause: best weapon damage plateaus 
    # around 20-26 starting at roughly expedition tier 3 and never grows further 
    # through tier 9 (LOOT_WEAPON_TABLE's highest-damage entries and the crafting 
    # system's higher-tier recipes require levels the player rarely reaches within 
    # a single campaign - final level averages only ~8.5-9), and best armor reduction 
    # stays near 0-1 for almost the entire campaign (armor essentially never develops 
    # meaningfully). Meanwhile zombie composition/elite chance (this function, via the 
    # t = expeditions_completed / CAMPAIGN_LENGTH interpolation) keeps escalating all 
    # way through tier 9. So player combat power flatlines around tier 3-5 while the 
    # difficulty curve keeps climbing for 5 more tiers - that gap is the wall, not 
    # exploration or player level stalling out.
    def _select_zombie_for_encounter(self):
        # Combat difficulty scaling investigation: composition (which
        # zombie types can appear, and whether an elite variant rolls)
        # is now the primary difficulty lever, keyed to
        # expeditions_completed (the same map-level axis that already
        # drives map size/obstacle density) - not raw player level,
        # and not an unbounded flat stat multiplier. A player who
        # grinds one map indefinitely no longer faces ever-scarier
        # zombies from that alone; finishing expeditions is what
        # brings in tougher composition.
        # Continuous interpolation between the early (t=0) and late
        # (t=1, reached at DIFFICULTY_RAMP_LENGTH) weight vectors,
        # replacing the three hard brackets this used to jump between -
        # see the campaign-simulation finding above for why a hard jump
        # was a real problem. The ramp is capped at DIFFICULTY_RAMP_LENGTH
        # (not CAMPAIGN_LENGTH) so lengthening the arc doesn't soften the
        # frozen curve (docs/PHASE_C3_2_7_SUPPORTED_DEPTH.md).
        t = min(1.0, self.expeditions_completed / self.world.manifest.difficulty_ramp_length)
        # Order: Fresh, Regular, Heavy, Swift, Toxic, Armored.
        # v4: Heavy (100 HP) and Armored (120 HP) start at ZERO -
        # meeting one on expedition 0 with a 6-damage starter weapon
        # was an unavoidable death (player-reported: died to an
        # armored zombie on day 5 of map 1). They phase in as the
        # campaign progresses.
        early_weights = [0.62, 0.26, 0.00, 0.10, 0.02, 0.00]
        late_weights = [0.10, 0.15, 0.25, 0.15, 0.15, 0.20]
        weights = [
            early + (late - early) * t
            for early, late in zip(early_weights, late_weights)
        ]

        # 2D.1: bias composition by the player's current zone. Both
        # axes matter - how far into the campaign, AND what kind of
        # place this tile is.
        bias = self._ZONE_ZOMBIE_BIAS.get(self._current_zone())
        if bias:
            weights = [w * b for w, b in zip(weights, bias)]

        zombie_classes = list(self._ZOMBIE_BASE_STATS.keys())
        zombie_class = self.rng.choices(zombie_classes, weights=weights)[0]
        choice = zombie_class()

        # Day still gives a mild in-run ramp - capped now (was
        # unbounded: day * 0.2, ~3x by day 15) so it's a secondary
        # effect rather than the main way zombies get tougher.
        difficulty_factor = min(MAX_DAY_DIFFICULTY_FACTOR, max(1.0, self.day * 0.1))

        # Elite variant: same subclass, boosted stats - gated behind
        # expeditions_completed so they don't show up before the
        # player's had any chance to gear up. This is the "harder
        # without inflating every zombie forever" lever: elites are a
        # composition choice (this roll), not a universal multiplier.
        is_elite = (
            self.expeditions_completed >= ELITE_MIN_EXPEDITION
            and self.rng.random() < min(0.3, self.expeditions_completed * 0.03)
        )
        if is_elite:
            difficulty_factor *= ELITE_STAT_MULTIPLIER
            choice.name = f"Elite {choice.name}"

        base_health, base_attack = self._ZOMBIE_BASE_STATS[zombie_class]
        choice.health = int(base_health * difficulty_factor)
        choice.attack = max(1, int(base_attack * difficulty_factor))

        return choice

    # --------------------------------------------------
    # Movement
    # --------------------------------------------------

    def _swim_odds(self):
        """Estimated chance a swim across succeeds. Derived (not raw):
        base 55%, + dexterity, - fatigue, - low health, waders a big
        plus. MAP_REALISM_SPEC 3b."""
        p = 0.55 + (self.dexterity - 10) * 0.02
        if self.fatigue > 80:
            p -= 0.20
        elif self.fatigue > 50:
            p -= 0.10
        if self.health < self.max_health * 0.3:
            p -= 0.15
        if getattr(self, 'has_waders', False):
            p += 0.30
        return max(0.10, min(0.95, p))

    def _try_swim_river(self, rx, ry):
        """Offer the swim, show the odds + cost, and resolve it. Returns
        True if the survivor is now across. Only the landscape generator
        makes rivers a real boundary - elsewhere a river stays a wall."""
        if getattr(self, '_mapgen', 'v1') != 'landscape':
            self.io.say("You can't cross the river here.")
            return False
        pct = round(self._swim_odds() * 100)
        self.announce_event(
            "THE RIVER",
            f"Swim across?  ~{pct}% you make it clean.",
            "Fail and you're swept back to this bank - a hard knock and "
            "you may lose something loose from your pack. Waders help a lot.",
            kind="warning")
        if not self.io.ask_yes_no("Swim for it?"):
            return False
        import random as _r
        self._update_time(45)
        self.fatigue = min(100, self.fatigue + 15)
        if _r.random() < self._swim_odds():
            self.io.say("You get across, soaked and cold but on the far bank.")
            self.health = max(1, self.health - 3)
            self.current_position = (rx, ry)
            self.visited.add((rx, ry))
            return True
        # failure - swept back, a knock, maybe a dropped item
        self.io.say("The current takes you and dumps you back where you started.")
        self.health = max(1, self.health - _r.randint(8, 16))
        loose = [k for k in ("medicine", "ammo") if getattr(self.backpack, k, 0) > 0]
        if loose and _r.random() < 0.4:
            k = _r.choice(loose)
            lost = min(getattr(self.backpack, k), _r.randint(1, 3))
            setattr(self.backpack, k, getattr(self.backpack, k) - lost)
            self.io.say(f"You lost some {k} to the water.")
        return False

    def move_and_search(self, direction):
        directions = {"n": (0, -1), "s": (0, 1), "e": (1, 0), "w": (-1, 0)}
        dx, dy = directions.get(direction, (0, 0))
        new_x, new_y = self.current_position[0] + dx, self.current_position[1] + dy

        if not (0 <= new_x < self.map_w and 0 <= new_y < self.map_h):
            self.io.say("Can't move in that direction.")
            return

        destination = self.map[new_y][new_x]
        dest_terrain = destination.get('terrain') if isinstance(destination, dict) else None

        # MAP_REALISM_SPEC 3b: a river is crossable by swimming - a real
        # choice with a real cost, shown before you commit. Returns True
        # if the survivor is now across (fall through to the move),
        # False if they stayed / declined.
        if dest_terrain == 'river':
            if not self._try_swim_river(new_x, new_y):
                return

        # Mountains stay a hard wall.
        elif dest_terrain == 'mountain':
            last_x, last_y = self.map_w - 1, self.map_h - 1
            on_boundary = new_x in (0, last_x) or new_y in (0, last_y)
            if on_boundary:
                # v4: the edge of the world is a moment, not a wall.
                seen = getattr(self, '_edge_seen', None)
                if seen is None:
                    seen = self._edge_seen = set()
                if direction not in seen:
                    seen.add(direction)
                    self.io.say(
                        "The mountains rise up sheer and impossibly high. "
                        "There's no way through here - and looking along "
                        "them, no obvious way through anywhere."
                    )
                else:
                    self.io.say("The mountains block the way. There's no crossing them.")
            else:
                self.io.say("You can't cross the mountain here.")
            return

        # v4 Phase C: the generated mystery's obstacle blocks the way
        # to the escape route until it's cleared with the requirement
        # item. Walking into it with the item clears it in place.
        m = getattr(self, 'mystery', None)
        if m is not None and m.obstacle_tile == (new_x, new_y) and not m.obstacle_open:
            if self._mystery_obstacle_ready():
                self.mystery_clear_obstacle()
            else:
                self.mystery_bump_obstacle()
            return

        # Update the current position
        self.current_position = (new_x, new_y)
        self.visited.add(self.current_position)  # Mark the new position as visited
        # 1d HUD: cumulative distance walked (~a valley mile every ~30 tiles)
        self._distance_walked = getattr(self, "_distance_walked", 0.0) + 0.033
        self._expedition_distance = getattr(self, "_expedition_distance", 0.0) + 0.033

        # v4 (todo 6c9a4ca6): anything dropped here earlier is still here.
        self.pick_up_ground_items()

        # Per-move time cost is now terrain-dependent (v3 #11) rather
        # than a flat 15 minutes - see constants.py's
        # TERRAIN_MOVE_MINUTES.
        move_cost = 15 if (self.has_waders and dest_terrain in ('water', 'swamp')) else self._terrain_move_minutes.get(dest_terrain, 15)
        self._update_time(move_cost)
        self._apply_decay()
        # v4 time-pressure family (tidal_causeway): advance the tide
        # clock. No-op for every other mystery / no mystery.
        if getattr(self, 'mystery', None) is not None:
            self._mystery_tide_tick()

        # Fatigue increases with movement. 1d playtest: +5/move
        # saturated fatigue to 100 inside the first ~15-20 moves on
        # every map (maps are 24-30 tiles, an expedition is 40-80
        # moves), so fatigue was a permanent combat tax, not a resource
        # to manage. +2/move moves exhaustion out to ~40 moves - the
        # back half of a long expedition - where one rest can still buy
        # a fresh stretch. Nothing else changed (see
        # docs/FATIGUE_INVESTIGATION_RESULTS.md, 1d section).
        self.fatigue = min(100, self.fatigue + 2)

        self.io.say(f"Moved {direction}.")

        # Check tile contents for placed zombies
        current_tile = self.map[self.current_position[1]][self.current_position[0]]

        # v4 Phase C: when there's a generated mystery, the Town Center
        # is an information-rich location, NOT a win tile - winning is
        # working out the escape route and taking it (mystery_try_
        # escape). The reach-the-Town-Center win only applies to the
        # fallback (no mystery on this map).
        _mystery = getattr(self, 'mystery', None)

        if (
            _mystery is None
            and isinstance(current_tile, dict)
            and current_tile.get('content') == 'T'
            and not self.settlement_explored
        ):
            self.io.say(
                "The Town Center looks quiet - too quiet. You should "
                "search the settlement's buildings and streets before "
                "assuming it's safe to call this home."
            )
            return

        if _mystery is not None and isinstance(current_tile, dict) and current_tile.get('content') == 'T':
            self.io.say(
                "The Town Center. Records, notices, a wall of missing-person "
                "photos - the most information in one place you've found. "
                "But no one's here, and this isn't the way out."
            )
            self.mystery_arrive(*self.current_position)
            self._maybe_surface_clue()
            return

        if _mystery is None and isinstance(current_tile, dict) and current_tile.get('content') == 'T':
            self.finish_expedition(reason="reached the Town Center")
            return

        # Apply terrain-specific effects
        if isinstance(current_tile, dict):
            terrain = current_tile.get('terrain')

            if terrain != 'town':
                self._last_district = None  # so re-entering a settlement re-announces

            if terrain == 'town' and current_tile.get('content') != 'T':
                # Objective-driven win condition / organic-settlement
                # investigations: stepping into any non-Town-Center
                # settlement tile satisfies the exploration gate above
                # (any settlement, decoy or real - see generate_map()'s
                # own known-limitation note on this simplification),
                # and surfaces the tile's district (the actual ask
                # behind the organic-settlement investigation: "I'm
                # entering the residential district", not a uniform
                # block of letters).
                if not self.settlement_explored:
                    self.settlement_explored = True
                    self.io.say("You've found a settlement - it's worth exploring before moving on.")
                district = current_tile.get('district')
                # Only when it changes - not on every tile of the same
                # district (playtest: repeated identical lines).
                if district and district != getattr(self, '_last_district', None):
                    self._last_district = district
                    self.io.say(f"You're in the {district} district.")

            _first_visit = not current_tile.get('_seen_desc')
            current_tile['_seen_desc'] = True

            if terrain == 'building':
                cause = current_tile.get('abandonment')
                if _first_visit and cause and not current_tile.get('_ab_told'):
                    current_tile['_ab_told'] = True
                    _ab = (self.world.prose.get("abandonment_flavour")
                           or self._ABANDONMENT_FLAVOUR)
                    self.io.say(_ab.get(
                        cause, "You step inside. It's been empty a while."))
                heal_amount = self.rng.randint(5, 10)
                self.health = min(100, max(0, self.health + heal_amount))
                fatigue_recovery = max(0, self.wisdom // 4)
                self.fatigue = max(0, self.fatigue - fatigue_recovery - 5)
                # First time here: the full beat. Revisit: one terse line
                # (playtest: re-reading the same paragraph while pacing
                # an area is what trains the eye to stop reading).
                if _first_visit:
                    self.io.say("You enter a building. It's a safe zone.")
                    self.io.say(f"Restored {heal_amount} health and recovered some fatigue.")
                else:
                    self.io.say(f"Back inside - safe for now. (+{heal_amount} health)")

            elif terrain == 'water':
                self.io.say("You wade through water. Movement is difficult."
                            if _first_visit else "More water. Slow going.")
                self.fatigue = min(100, self.fatigue + 4) # slow-movement penalty (1d: 10 -> 4, so a water tile is ~+6 total not +15)
                if self.rng.random() < 0.2:
                    self.health -= 5
                    self.io.say("The cold water chills you. You lost some health.")

            elif terrain == 'forest':
                if _first_visit:
                    self.io.say("You move through dense forest.")

        self._spot_landmarks()
        self._spot_threats()
        self._spot_route_landmark()
        self._spot_leads()

        # v4 Phase C: generated-mystery site arrival (blurb + observe
        # evidence). Runs alongside normal loot/encounters, not instead.
        if getattr(self, 'mystery', None) is not None:
            self.mystery_arrive(*self.current_position)
            # P1-b (spec §3.3): reassert ESCAPE READY only when the
            # profile that actually dies - ready to leave, worn down,
            # walking away from the exit.
            self._escape_ready_reassert()

        # docs/DESIGN_INTERACTION_INFERENCE.md - once this move has won
        # the expedition (auto-escape / reaching the way out), the
        # expedition is over; nothing on this tile still prompts a
        # combat decision (run 7: a fight fired in the same turn as the
        # win).
        if getattr(self, 'won', False):
            return

        if self.current_position in self.tile_event_cooldowns and self.day < self.tile_event_cooldowns[self.current_position]:
            return

        encounter_chance = ENCOUNTER_CHANCE_NIGHT if self.is_night else ENCOUNTER_CHANCE_DAY

        # Forest increases encounter rate
        if isinstance(current_tile, dict) and current_tile.get('terrain') == 'forest':
            encounter_chance = min(1.0, encounter_chance * 1.5)

        if isinstance(current_tile, Zombie):
            self.encounter_zombie(current_tile)
        elif self.rng.random() < encounter_chance:  # Chance encounter when moving around the map
            self.encounter_zombie()
        else:
            self.find_loot()

        self.tile_event_cooldowns[self.current_position] = self.day + 3

    def find_loot(self):
        current_tile = self.map[self.current_position[1]][self.current_position[0]]
        terrain = current_tile.get('terrain') if isinstance(current_tile, dict) else None
        content = current_tile.get('content') if isinstance(current_tile, dict) else None
        if terrain != 'building' and content not in ('H', 'R', 'S', 'B', 'T'):
            return

        self._maybe_surface_clue()

        # Intelligence increases chance of finding loot and better items
        find_chance = min(1.0, 0.2 + self.intelligence / 250)
        if self.rng.random() < find_chance:
            loot_types = ["food", "water", "medicine", "ammo", "weapon", "armor"]
            # Only a live possibility until it's actually been found -
            # once town_known is True there's nothing left to reveal,
            # so it drops out of the pool instead of wasting a roll.
            # Same pattern for the flashlight (day/night granularity
            # investigation) - once owned, it drops out too.
            if not getattr(self, 'map_revealed', False):
                loot_types.append("map")
            if not self.has_flashlight:
                loot_types.append("flashlight")
            if not self.has_waders:
                loot_types.append('waders')

            # 2D.2: weight the roll by the current zone's loot ecology
            # (a medicine-heavy downtown vs. a food-heavy farmstead)
            # rather than a flat uniform pick. Implemented as list
            # repetition + rng.choice (not rng.choices) so the pick
            # stays a single choice() call - the loot tests patch
            # rng.choice directly and assert on the options it sees.
            # Discoverables not in the bias table (map/flashlight/
            # waders) keep weight 1.0.
            zbias = self._ZONE_LOOT_BIAS.get(self._current_zone(), {})
            weighted_pool = []
            for lt in loot_types:
                weighted_pool.extend([lt] * max(1, round(zbias.get(lt, 1.0) * 4)))
            loot_type = self.rng.choice(weighted_pool)

            # The old `intelligence > 10 -> rewrite the roll to "weapon"`
            # override was removed (docs/ARMOR_INVESTIGATION_RESULTS.md):
            # weapons are already abundant, armor is the acquisition
            # bottleneck, and it was silently converting armor rolls to
            # weapons exactly as the player levelled. Intelligence still
            # raises `find_chance` (above) - it just no longer biases
            # *what* you find toward weapons.

            self.io.say(f"You found {loot_type}!")
            self.award_xp(10)

            if loot_type == "weapon":
                # Real stat variance per name, and the correct weapon
                # type (melee vs ranged) - see LOOT_WEAPON_TABLE's own
                # comment in constants.py for the bug this replaced.
                eligible_weapons = {
                    name: spec for name, spec in LOOT_WEAPON_TABLE.items()
                    if spec.get('min_expedition', 0) <= self.expeditions_completed
                }
                new_weapon_name = self.rng.choice(list(eligible_weapons.keys()))
                spec = eligible_weapons[new_weapon_name]
                if spec["type"] == "ranged":
                    new_weapon = RangedWeapon(
                        new_weapon_name, spec["damage"],
                        spec["max_ammo"], spec["durability"],
                    )
                else:
                    new_weapon = MeleeWeapon(
                        new_weapon_name, spec["damage"], spec["durability"],
                    )
                if self.backpack.add_weapon(new_weapon):
                    self.io.say(f"You obtained a {new_weapon.name}.")
                else:
                    # Real bug found live: an over-capacity weapon was
                    # just discarded, so "drop something, then take it"
                    # had nothing to take. Leave it on the tile.
                    self._drop_to_ground(new_weapon)
                    self.io.say(
                        f"You found a {new_weapon.name}, but your weapon slots are "
                        f"full. It's on the ground here - drop a weapon, then `take`."
                    )
            elif loot_type == "armor":
                # Equipment-slot investigation: same expedition-banding
                # pattern as weapons above.
                eligible_armor = {
                    name: spec for name, spec in ARMOR_TABLE.items()
                    if spec.get('min_expedition', 0) <= self.expeditions_completed
                }
                new_armor_name = self.rng.choice(list(eligible_armor.keys()))
                spec = eligible_armor[new_armor_name]
                new_armor = Armor(new_armor_name, spec["reduction"], spec["durability"], spec["slot"])
                if self.backpack.add_armor(new_armor):
                    self.io.say(f"You obtained {new_armor.name}.")
                else:
                    self._drop_to_ground(new_armor)
                    self.io.say(
                        f"You found {new_armor.name}, but your armor slots are full. "
                        f"It's on the ground here - drop a piece, then `take`."
                    )
            elif loot_type == "food":
                # v4: a find is a haul, not a single ration - hunger/
                # thirst decay ~2-3/turn and a full expedition runs
                # 30-50 turns, so +1 never kept up (balance report:
                # food/water were net-negative every game).
                amount = self.rng.randint(2, 4)
                self.backpack.food += amount
                self.io.say(f"You found food - enough for a while. (+{amount})")
            elif loot_type == "water":
                amount = self.rng.randint(2, 4)
                self.backpack.water += amount
                self.io.say(f"You found water - enough for a while. (+{amount})")
            elif loot_type == "medicine":
                # Increase medicine in the backpack
                self.backpack.medicine += 1
                self.io.say("You found some medicine. Medicine stock increased.")
            elif loot_type == "ammo":
                # Increase ammo in the backpack to support ranged crafting recipes
                self.backpack.ammo += self.rng.randint(1, 3)
                self.io.say("You found some ammo! Ammo stock increased.")
            elif loot_type == "map":
                self.map_revealed = True
                self.town_known = True
                _mi = self.world.prose.get("map_item")
                if _mi:
                    self.io.say(f"You found {_mi[0]}! {_mi[1]}")
                else:
                    self.io.say("You found a map of the whole place! It's all "
                                "laid out now - though not what's moving out there.")
            elif loot_type == "flashlight":
                self.has_flashlight = True
                self._update_time(0)  # refresh visibility_radius immediately, without advancing time
                self.io.say(
                    "You found a working flashlight! Visibility at "
                    "dawn, dusk, and night is now much better."
                )
            elif loot_type == 'waders':
                self.has_waders = True
                self.io.say(
                    'You found a sturdy pair of waders! Water and swamp '
                    'terrain no longer slow you down as much.'
                )