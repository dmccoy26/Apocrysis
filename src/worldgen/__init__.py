"""worldgen - map generation mechanics, extracted from world_mixin in
Phase C. Owns terrain, zones, the mountain boundary, spawn selection,
settlement placement, and reachability guarantees. Produces a base map;
the engine (world_mixin.generate_map) then embeds the mystery, places
zombies, and adds flavour. Nothing here imports src.game / src.mixins /
src.escape. See docs/PHASE_C_SPEC.md.
"""
from src.worldgen.generator import MapGenerator

__all__ = ["MapGenerator"]
