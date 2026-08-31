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
    uses. Empty tuple = all of them (World 1's historical behaviour)."""
    id: str
    title: str
    subtitle: str = ""
    campaign_length: int = 25
    difficulty_ramp_length: int = 10
    chapter_bounds: tuple = (0,)          # lowest expeditions_completed per chapter
    chapter_titles: tuple = ()
    supported_mechanisms: tuple = ()


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
    # chapter intro lines + retrospective text: {"chapters": (...),
    # "retro_lead": str, "retro_tail": str}
    chapters: dict = field(default_factory=dict)

    # A World is immutable shared content (it may hold un-copyable
    # references, e.g. the population module). Copying it is always a
    # no-op - callers that deepcopy a game for a private simulation
    # (combat_forecast) must keep pointing at the one real World.
    def __copy__(self):
        return self

    def __deepcopy__(self, memo):
        return self
