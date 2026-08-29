"""The World seam. The engine reads a World; a World is data, never
behaviour. No imports from src.mixins or src.game."""
from dataclasses import dataclass, field


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
