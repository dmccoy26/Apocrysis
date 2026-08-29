"""The World seam. The engine reads a World; a World is data, never
behaviour. No imports from src.mixins or src.game."""
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
