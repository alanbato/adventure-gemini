"""Tests for game state."""

import pickle
import zlib

from adventure.engine.state import CARRIED, KEYS, LAMP, START_ROOM, new_game_state
from adventure.engine.world import World


def test_new_game_state(world: World):
    """Fresh game state places objects correctly."""
    state = new_game_state(world)
    assert state.current_room == START_ROOM
    assert state.turns == 0
    assert not state.is_finished
    # Lamp and keys should be placed somewhere
    assert LAMP in state.object_locations
    assert KEYS in state.object_locations


def test_pickle_roundtrip(world: World):
    """GameState survives pickle/unpickle cycle."""
    state = new_game_state(world)
    state.current_room = 15
    state.turns = 42
    state.visited_rooms.add(15)
    state.object_locations[LAMP] = CARRIED

    blob = zlib.compress(pickle.dumps(state))
    restored = pickle.loads(zlib.decompress(blob))

    assert restored.current_room == 15
    assert restored.turns == 42
    assert 15 in restored.visited_rooms
    assert restored.object_locations[LAMP] == CARRIED
