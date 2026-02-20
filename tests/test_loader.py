"""Tests for the advent.dat parser."""

from adventure.engine.world import World


def test_loads_rooms(world: World):
    """Parser loads rooms from sections 1 and 2."""
    assert len(world.rooms) > 0
    room_1 = world.rooms[1]
    assert (
        "ROAD" in room_1.short_description.upper()
        or "END OF A ROAD" in room_1.long_description.upper()
    )
    assert room_1.long_description


def test_loads_vocabulary(world: World):
    """Parser loads vocabulary from section 4."""
    assert len(world.vocabulary) > 0
    assert "north" in world.vocabulary or "n" in world.vocabulary


def test_loads_objects(world: World):
    """Parser loads objects from sections 5 and 7."""
    # Object 2 is the lamp
    assert 2 in world.objects
    lamp = world.objects[2]
    assert lamp.inventory_message
    assert lamp.initial_rooms  # lamp starts somewhere


def test_loads_messages(world: World):
    """Parser loads arbitrary messages from section 6."""
    assert len(world.messages) > 0
    assert 1 in world.messages  # Message 1 is the intro


def test_loads_travel_table(world: World):
    """Parser loads travel table entries from section 3."""
    room_1 = world.rooms[1]
    assert len(room_1.travel_table) > 0


def test_loads_class_messages(world: World):
    """Parser loads class messages from section 10."""
    assert len(world.class_messages) > 0


def test_loads_hints(world: World):
    """Parser loads hints from section 11."""
    assert len(world.hints) > 0


def test_loads_magic_messages(world: World):
    """Parser loads magic messages from section 12."""
    assert len(world.magic_messages) > 0


def test_room_light_flags(world: World):
    """Room light flags are set from section 9."""
    room_1 = world.rooms[1]
    assert room_1.is_light  # above ground rooms are lit


def test_object_names_index(world: World):
    """Object names are indexed for quick lookup."""
    assert "lamp" in world.object_names or "lante" in world.object_names
    assert "keys" in world.object_names


def test_treasure_flag(world: World):
    """Objects with number >= 50 are treasures."""
    for obj_id, obj in world.objects.items():
        if isinstance(obj_id, int) and obj_id >= 50:
            assert obj.is_treasure
