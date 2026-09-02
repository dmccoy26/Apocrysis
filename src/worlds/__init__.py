"""World definitions. The engine takes a World; see src/worlds/base.py.

Phase F: the registry. The engine looks worlds up by id here and never
imports a concrete world package. Add a world by importing it and
listing it in WORLDS - no engine change.
"""
from src.worlds.silence import SILENCE
from src.worlds.the_wake import THE_WAKE
from src.worlds.the_deep import THE_DEEP

WORLDS = {w.id: w for w in (SILENCE, THE_WAKE, THE_DEEP)}

DEFAULT_WORLD_ID = SILENCE.id


def get_world(world_id=None):
    """The World for `world_id`, or the default. Unknown id -> default
    (a stale profile naming a removed world still loads)."""
    if world_id is None:
        return WORLDS[DEFAULT_WORLD_ID]
    return WORLDS.get(world_id, WORLDS[DEFAULT_WORLD_ID])


def world_ids():
    return list(WORLDS)
