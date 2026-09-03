"""The World seam. The engine reads a World; a World is data, never
behaviour. No imports from src.mixins or src.game.

Phase F (docs/PHASE_F_MULTI_WORLD_SEAM.md): a World now carries
everything the engine needs to run a campaign in it - manifest
(campaign length / chapters / mechanism subset), terrain vocabulary,
population, and the finale. The engine must never import a concrete
world package; it reads all of this off the World it was handed.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class DiscoveryTemplate:
    """Binds one authored WorldFact to an escape mechanism that can
    carry it. NOT the mystery's answer - the player still solves the
    escape mystery by its own evidence; solving it is what surfaces the
    fact (A.3). See docs/PHASE_A2_DISCOVERY.md."""
    world_fact_id: str
    mechanism: str            # a key of escape.MECHANISMS


@dataclass(frozen=True)
class SurvivorLore:
    """One concrete thing survivors of this campaign have figured out.
    ALL FOUR FIELDS ARE DATA. The engine reads exactly one thing:
    survivor_knowledge.has(<id>). `effect` is player-facing / doc text
    with no runtime meaning. See PHASE_B_SPEC.md invariant 3."""
    id: str
    learned_when: str      # doc-only description of the trigger
    blurb: str             # player-facing: what you now know
    effect: str            # player-facing / doc text ONLY - never parsed


@dataclass(frozen=True)
class WorldManifest:
    """The metadata the engine's campaign framing and (later) the Player
    Shell need - the numbers that used to be module globals in
    constants.py / campaign.py. Phase F §2.

    supported_mechanisms: the subset of escape.MECHANISMS this world
    uses. Empty tuple = all of them (World 1's historical behaviour).

    map_transit: the expedition reads as moving THROUGH the place -
    spawn against one side wall, the way out carved in the opposite
    wall, roughly level. A ship you traverse bow-to-stern, not a valley
    you wander. False (the default) = the historical random-interior
    spawn + nearest-edge gap. Silence leaves it False -> generator RNG
    and the golden fixture are untouched."""
    id: str
    title: str
    subtitle: str = ""
    campaign_length: int = 25
    difficulty_ramp_length: int = 10
    chapter_bounds: tuple = (0,)          # lowest expeditions_completed per chapter
    chapter_titles: tuple = ()
    supported_mechanisms: tuple = ()
    map_transit: bool = False
    # The spatial spine (The Wake, WAKE_SPINE_INVESTIGATION.md §5).
    # section_bounds: lowest expeditions_completed per section - a step
    # function, parallel to chapter_bounds but a SEPARATE axis (sections
    # are spatial: HUD label + terrain archetype + "N sections ahead";
    # chapters stay the narrative arc). section_names / section_archetypes
    # run parallel to section_bounds. Empty = no spine (The Silence): the
    # generator keeps its RNG archetype roll and every HUD slot it has.
    section_bounds: tuple = ()
    section_names: tuple = ()
    section_archetypes: tuple = ()
    # H1 (WAKE_DEVICE_PASS.md): this world's site markers are gated on
    # an information device. Before the survivor finds it the world
    # plays contact-only (like Hardcore) - bearing + distance + physical
    # landmarks, no `!`. After: learned leads mark `!` again, and
    # detected-but-unidentified sites show `?`. The Silence leaves this
    # False - markers work exactly as they always have.
    markers_need_device: bool = False
    # Per pre-finale level (index == expeditions_completed), the level's
    # TYPE: "" / "fact" -> the ordinary escape-mystery level carrying a
    # WorldFact (today's only kind); "traversal" / "discovery" /
    # "encounter" / "quiet" -> a section-transit level: no mystery, a
    # carved far-wall exit the player crosses to finish, with its own
    # framing. Requires map_transit. Empty tuple -> every level is a
    # fact level (The Silence). WAKE_SPINE_INVESTIGATION.md §5.1.
    level_types: tuple = ()


@dataclass(frozen=True)
class WorldTerrain:
    """The world's tile vocabulary + presentation + per-tile move cost.
    Terrain *mechanics* stay in the engine, keyed to the semantic role
    (`impassable` etc.), never to the name - so a world may rename
    'forest' to 'pine' freely. Phase F §4 rows 3-4."""
    symbols: dict              # terrain name -> map glyph
    legend: str               # the printed legend block
    archetypes: dict           # per-expedition terrain-weight presets
    move_minutes: dict         # terrain name -> minutes to cross
    impassable: frozenset = frozenset({'mountain', 'river'})
    # generator's positional terrain roll order (worldgen/generator.py).
    generator_terrain_order: tuple = ('forest', 'building', 'water', 'plain', 'swamp')
    # §F.11: the player-facing fiction of MOVING through this world -
    # entry lines, the "can't cross" lines, the swim/gap crossing, the
    # distant-sighting lines, the HUD location label + travel-drag
    # note. Keyed by semantic slot, not raw terrain name. None -> the
    # engine's bland generic set (src/loot.py-style fallback, in
    # world_mixin._TERRAIN_PROSE). "You push through deep forest" is a
    # claim about the physical world; it belongs here, not in the
    # engine.
    prose: dict = None
    # Settlement block glyphs: (centre, *feature letters). The generator
    # stamps a cluster of these where a settlement stands; the legend
    # names them. Default = The Silence's valley town (Town centre /
    # House / Road / Shop / Building). A world on a ship wants its own
    # (The Wake: Muster / Hab / Run / Store / Bay) so a deck doesn't
    # render a suburban block.
    settlement_glyphs: tuple = ('T', 'H', 'R', 'S', 'B')


@dataclass(frozen=True)
class WorldFinale:
    """The bespoke last expedition + the one binary choice. Phase F: the
    finale *shape* (converge the investigation -> a bespoke last
    expedition -> a binary choice at a location) stays in the engine;
    this fills that shape in. Binary-choice-only for now.

    endings: {choice_id: (lead, body)}  - choice_id is option_a[0] /
    option_b[0] lowercased.
    """
    converge_fact: str                    # the WorldFact expedition N targets
    also_establishes: tuple = ()          # facts the finale marks known alongside
    escape_kind: str = "checkpoint"       # how the finale map's way-out reads
    # {mystery role -> label} stamped onto the bespoke finale map.
    site_labels: dict = field(default_factory=dict)
    arrival_title: str = ""               # the "MYSTERY SOLVED" banner headline
    arrival_prose: str = ""               # the paragraph after it
    choice_title: str = ""
    choice_intro: str = ""                # one line under the title
    option_a: tuple = ()                  # (id, prompt_line)
    option_b: tuple = ()
    endings: dict = field(default_factory=dict)
    # doc-only: the question this choice poses.
    question: str = ""


@dataclass(frozen=True)
class WorldLoot:
    """The world's equipment VOCABULARY (Phase F §F.10). The engine
    owns the GRAMMAR - expedition bands, min_expedition gating, the
    melee/ranged split, drop RNG, crafting ingredient costs + level
    gates, the drop-on-full-slots behaviour. A world supplies only the
    names and their stat values.

    weapons / armor : name -> spec, same shape as the historical
        constants.LOOT_WEAPON_TABLE / ARMOR_TABLE. Key ORDER matters
        (the loot RNG picks by index), so a world that wants the
        current balance keeps the same number of entries per band.
    crafting : recipe_key -> {ingredients, min_level, result} where
        result is {"kind": "melee"|"ranged", "name", "damage",
        "durability", ["max_ammo"]} or None (a utility recipe like the
        repair kit). Keys are shared across worlds (the `craft <key>`
        command, tests); only the result vocabulary changes.
    starter : {"name", "damage", "durability", "variants": (...)} - the
        weapon a fresh survivor comes in with, replacing the vestigial
        class weapon.

    None on any field -> the engine falls back to The Silence's table
    (src/worlds/silence/loot.py), so a partial / fixture world still
    runs (mirrors mechanism_prose's fallback)."""
    weapons: dict = None
    armor: dict = None
    crafting: dict = None
    starter: dict = None


@dataclass(frozen=True)
class World:
    id: str
    name: str
    description: str
    terrain_symbols: dict
    terrain_legend: str
    map_archetypes: dict
    prose: dict = field(default_factory=dict)
    encounters: dict = field(default_factory=dict)
    # { world_fact_id: (DiscoveryTemplate, ...) } - >=1 route per fact
    discovery_templates: dict = field(default_factory=dict)
    # the authored WorldFact DAG (worlds/<w>/truth.py). WorldInvestigation
    # reads this; the facts themselves know nothing about gameplay.
    world_facts: tuple = ()
    # SurvivorLore this world can teach (worlds/<w>/lore.py). B.2.
    survivor_lore: tuple = ()
    # { mechanism_key: lore_id } - solving that mystery teaches that lore.
    lore_triggers: dict = field(default_factory=dict)
    # the wrong-assumptions ladder (worlds/<w>/hypotheses.py). Phase E.1 -
    # WorldInvestigation.current_hypothesis() derives the held rung from
    # milestone state; each rung breaks on a specific milestone.
    regional_hypotheses: tuple = ()
    # --- Phase F additions ---------------------------------------------
    manifest: WorldManifest = None
    terrain: WorldTerrain = None
    finale: WorldFinale = None
    # worlds/<w>/population.py - the module (or any object) exposing
    # pick_identity / pick_situation / confidence / describe / loot_pool.
    population: object = None
    # {mechanism_key: {prose fields}} - the FICTION of each escape
    # mechanism (name / closed / route / obstacle / require / item /
    # roles / evidence templates). The GRAMMAR (family, discovery
    # logic, placement, RNG) stays in escape.MECHANISMS. Required for
    # an authored world; optional for a fixture world (escape.py has a
    # generic fallback so a partial world still runs). Phase F §10.1.
    mechanism_prose: dict = None
    # chapter intro lines + retrospective text: {"chapters": (...),
    # "retro_lead": str, "retro_tail": str}
    chapters: dict = field(default_factory=dict)
    # equipment vocabulary (Phase F §F.10). None -> the engine uses
    # The Silence's tables (src/loot.py's fallback).
    loot: WorldLoot = None
    # Deep Phase 6 / kill-test A (docs/WORLD_3_THE_DEEP.md §5B.8):
    # {"systems": {...}, "extraction_path": (...), "restores":
    # {fact_id|"discovery:<n>" -> system_id}, "restart_fact": id}.
    # None -> this world has no persistent facility state; the engine's
    # restoration hook is a total no-op (The Silence / The Wake).
    facility_systems: dict = None
    # Deep Phase 6 / kill-test B (docs/WORLD_3_THE_DEEP.md §5B.7):
    # {"contested_fact": id, "resolved_by": id, "by_level": {lvl_idx ->
    # contact dict}, "stances_fact": id, "stances_needed": (...)}.
    # A contact is a person on an encounter crossing whose testimony
    # marks a WorldFact SUSPECTED (not KNOWN) and records a stance.
    # None -> no contacts; the engine's contact path is a total no-op.
    contacts: dict = None

    # A World is immutable shared content (it may hold un-copyable
    # references, e.g. the population module). Copying it is always a
    # no-op - callers that deepcopy a game for a private simulation
    # (combat_forecast) must keep pointing at the one real World.
    def __copy__(self):
        return self

    def __deepcopy__(self, memo):
        return self
