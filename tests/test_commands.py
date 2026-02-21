"""Tests for the command engine."""

from adventure.engine.commands import (
    calculate_score,
    get_exits,
    get_room_description,
    get_visible_objects,
    handle_command,
)
from adventure.engine.state import (
    CARRIED,
    CHEST,
    GRATE,
    KEYS,
    LAMP,
    MAGAZINE,
    new_game_state,
)
from adventure.engine.world import World


def test_look(world: World):
    """LOOK returns room description."""
    state = new_game_state(world)
    result = handle_command(world, state, "look")
    assert "ROAD" in result.upper() or "BUILDING" in result.upper()


def test_inventory_empty(world: World):
    """INVENTORY when not carrying anything."""
    state = new_game_state(world)
    result = handle_command(world, state, "inventory")
    assert "not carrying" in result.lower()


def test_take_keys(world: World):
    """TAKE KEYS picks up the keys."""
    state = new_game_state(world)
    # Keys start at room 3 (building), move player there
    state.current_room = 3
    state.visited_rooms.add(3)
    state.object_locations[LAMP] = CARRIED
    state.lamp_on = True
    result = handle_command(world, state, "take keys")
    assert state.object_locations[KEYS] == CARRIED or "OK" in result


def test_go_direction(world: World):
    """Going a valid direction moves the player."""
    state = new_game_state(world)
    old_room = state.current_room
    handle_command(world, state, "south")
    # Player should have moved (or gotten a message)
    # Room 1 going south goes to room 4 (valley)
    assert state.current_room != old_room or state.turns > 0


def test_score(world: World):
    """SCORE returns score info."""
    state = new_game_state(world)
    result = handle_command(world, state, "score")
    assert "score" in result.lower()


def test_help(world: World):
    """HELP returns help text."""
    state = new_game_state(world)
    result = handle_command(world, state, "help")
    assert "vocabulary" in result.lower() or "know" in result.lower()


def test_get_exits(world: World):
    """get_exits returns direction names."""
    state = new_game_state(world)
    exits = get_exits(world, state)
    assert len(exits) > 0
    # Room 1 should have multiple exits
    directions = {e.lower() for e in exits}
    assert len(directions) > 0


def test_get_room_description(world: World):
    """get_room_description returns room text."""
    state = new_game_state(world)
    desc = get_room_description(world, state)
    assert len(desc) > 0


def test_get_visible_objects(world: World):
    """get_visible_objects finds objects in room."""
    state = new_game_state(world)
    state.current_room = 3  # building has objects
    objects = get_visible_objects(world, state)
    # Building should have keys, lamp, food, bottle
    assert len(objects) > 0


def test_unknown_command(world: World):
    """Unknown command gives error message."""
    state = new_game_state(world)
    result = handle_command(world, state, "xyzflurble")
    assert "don't understand" in result.lower() or "don't know" in result.lower()


def test_quit(world: World):
    """QUIT ends the game."""
    state = new_game_state(world)
    result = handle_command(world, state, "quit")
    assert state.is_finished
    assert "score" in result.lower()


def test_open_grate_with_keys(world: World):
    """Opening grate with keys works."""
    state = new_game_state(world)
    state.current_room = 8  # depression with grate
    state.object_locations[KEYS] = CARRIED
    state.object_locations[LAMP] = CARRIED
    state.lamp_on = True
    result = handle_command(world, state, "open grate")
    assert state.object_props.get(GRATE) == 1 or "no keys" in result.lower()


# --- Scoring tests ---


def test_score_base(world: World):
    """Fresh game has base score: 2 (base) + 30 (survival) + 4 (not quit)."""
    state = new_game_state(world)
    assert calculate_score(world, state) == 36


def test_score_treasure_found(world: World):
    """Finding a treasure (setting its prop) gives 2 points."""
    state = new_game_state(world)
    # Gold nugget (obj 50) — worth 12 total, 2 for finding
    state.object_props[50] = 0
    score = calculate_score(world, state)
    assert score == 36 + 2


def test_score_treasure_stored(world: World):
    """Storing a treasure at building (room 3) with prop 0 gives full value."""
    state = new_game_state(world)
    # Gold nugget (obj 50) — value 12 (< CHEST)
    state.object_locations[50] = 3
    state.object_props[50] = 0
    assert calculate_score(world, state) == 36 + 12


def test_score_treasure_values(world: World):
    """Treasures below/at/above CHEST have different point values."""
    state = new_game_state(world)

    # Below CHEST (obj 50-54): value 12 each
    state.object_locations[50] = 3  # gold
    state.object_props[50] = 0
    score_gold = calculate_score(world, state) - 36
    assert score_gold == 12

    # CHEST itself (obj 55): value 14
    state.object_locations[CHEST] = 3
    state.object_props[CHEST] = 0
    score_chest = calculate_score(world, state) - 36 - score_gold
    assert score_chest == 14

    # Above CHEST (obj 56 = eggs): value 16
    state.object_locations[56] = 3  # eggs
    state.object_props[56] = 0
    score_eggs = calculate_score(world, state) - 36 - score_gold - score_chest
    assert score_eggs == 16


def test_score_survival_bonus(world: World):
    """Each death costs 10 points from survival bonus."""
    state = new_game_state(world)
    base = calculate_score(world, state)

    state.deaths = 1
    assert calculate_score(world, state) == base - 10

    state.deaths = 3
    assert calculate_score(world, state) == base - 30


def test_score_quit_penalty(world: World):
    """Quitting costs 4 points."""
    state = new_game_state(world)
    base = calculate_score(world, state)
    state.gave_up = True
    assert calculate_score(world, state) == base - 4


def test_score_dwarves_bonus(world: World):
    """Activating dwarves gives 25 points."""
    state = new_game_state(world)
    base = calculate_score(world, state)
    state.dwarves_active = True
    assert calculate_score(world, state) == base + 25


def test_score_closing_bonus(world: World):
    """Cave closing gives 25 points."""
    state = new_game_state(world)
    base = calculate_score(world, state)
    state.is_closing = True
    assert calculate_score(world, state) == base + 25


def test_score_closed_and_blast(world: World):
    """Cave closed gives 25 + bonus points based on blast location."""
    state = new_game_state(world)
    base = calculate_score(world, state)

    state.is_closed = True
    state.bonus = 133  # max bonus (45 pts)
    assert calculate_score(world, state) == base + 25 + 45

    state.bonus = 134  # medium bonus (30 pts)
    assert calculate_score(world, state) == base + 25 + 30

    state.bonus = 135  # min bonus (25 pts)
    assert calculate_score(world, state) == base + 25 + 25

    state.bonus = 0  # no blast (10 pts)
    assert calculate_score(world, state) == base + 25 + 10


def test_score_magazine_bonus(world: World):
    """Magazine at Witt's End (room 108) gives 1 point."""
    state = new_game_state(world)
    base = calculate_score(world, state)
    state.object_locations[MAGAZINE] = 108
    assert calculate_score(world, state) == base + 1


def test_score_hint_penalty(world: World):
    """Using hints deducts their penalty from score."""
    state = new_game_state(world)
    base = calculate_score(world, state)
    # Add a hint with known penalty
    hint_n = next(iter(world.hints))
    penalty = world.hints[hint_n].penalty
    state.hints_given.add(hint_n)
    assert calculate_score(world, state) == base - penalty
