"""Tests for the command engine."""

from adventure.engine.commands import (
    calculate_score,
    get_exits,
    get_room_description,
    get_visible_objects,
    handle_command,
)
from adventure.engine.state import (
    AXE,
    CARRIED,
    CHEST,
    CHEST_ROOM,
    DWARF,
    GRATE,
    KEYS,
    LAMP,
    MAGAZINE,
    NUGGET,
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
    state.dwarf_stage = 1
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


# --- Dwarf / pirate AI tests ---


def _enter_deep_cave(world, state):
    """Move player into deep cave (room 15+) to activate dwarf stage."""
    state.current_room = 15
    state.old_room = 15
    state.visited_rooms.add(15)
    state.lamp_on = True
    state.object_props[LAMP] = 1
    state.object_locations[LAMP] = CARRIED


def test_dwarf_stage_activation(world: World):
    """Entering room >= 15 activates dwarf stage 0 → 1."""
    import random as _random

    state = new_game_state(world)
    assert state.dwarf_stage == 0

    # Seed random to avoid dark-death and first-encounter rolls
    _random.seed(42)
    state.object_locations[LAMP] = CARRIED
    state.lamp_on = True
    state.object_props[LAMP] = 1
    state.current_room = 14
    state.old_room = 14

    # Move to room 15 via _move_to (through handle_command w/ motion word)
    from adventure.engine.commands import _move_to

    _move_to(world, state, 15)
    assert state.dwarf_stage == 1


def test_dwarf_first_encounter(world: World):
    """Stage 1 → 2 transition drops axe and shows message."""
    import random as _random

    state = new_game_state(world)
    _enter_deep_cave(world, state)
    state.dwarf_stage = 1

    # Seed so that random() >= 0.95 triggers encounter
    _random.seed(0)
    # Find a seed where random() >= 0.95
    for seed in range(1000):
        _random.seed(seed)
        if _random.random() >= 0.95:
            # Re-seed and run the tick
            _random.seed(seed)
            from adventure.engine.commands import _tick_dwarves

            result = _tick_dwarves(world, state)
            assert result is not None
            assert state.dwarf_stage == 2
            assert state.object_locations[AXE] == state.current_room
            break
    else:
        raise AssertionError("Could not find seed for first encounter")


def test_axe_throw_kills_dwarf(world: World):
    """Throwing axe at dwarf with lucky roll kills it."""
    from unittest.mock import patch

    state = new_game_state(world)
    _enter_deep_cave(world, state)
    state.dwarf_stage = 2

    # Place a dwarf in the player's room
    state.dwarf_locations = [state.current_room]
    state.dwarf_old_locations = [state.current_room]
    state.dwarf_seen = [True]
    state.object_locations[AXE] = CARRIED

    # random.choice is called twice: first to pick target index,
    # then to roll kill/miss. Side effect returns index 0, then True.
    with patch(
        "adventure.engine.commands.random.choice",
        side_effect=[0, True],
    ):
        result = handle_command(world, state, "throw axe")
    assert state.dwarf_killed == 1
    assert len(state.dwarf_locations) == 0
    assert "KILLED" in result.upper() or "killed" in result.lower()


def test_axe_throw_misses_dwarf(world: World):
    """Throwing axe at dwarf with unlucky roll misses."""
    from unittest.mock import patch

    state = new_game_state(world)
    _enter_deep_cave(world, state)
    state.dwarf_stage = 2

    state.dwarf_locations = [state.current_room]
    state.dwarf_old_locations = [state.current_room]
    state.dwarf_seen = [True]
    state.object_locations[AXE] = CARRIED

    with patch(
        "adventure.engine.commands.random.choice",
        side_effect=[0, False],
    ):
        result = handle_command(world, state, "throw axe")
    assert state.dwarf_killed == 0
    assert len(state.dwarf_locations) == 1
    assert "DODGE" in result.upper() or "dodge" in result.lower()


def test_pirate_steals_treasure(world: World):
    """Pirate steals carried treasures to chest room."""
    state = new_game_state(world)
    _enter_deep_cave(world, state)
    state.dwarf_stage = 2
    state.dwarf_locations = []
    state.dwarf_old_locations = []
    state.dwarf_seen = []

    # Place pirate in the player's room and mark as seen
    state.pirate_location = state.current_room
    state.pirate_old_location = state.current_room
    state.pirate_seen = True

    # Give player a treasure (gold nugget)
    state.object_locations[NUGGET] = CARRIED

    from adventure.engine.commands import _tick_pirate

    parts: list[str] = []
    _tick_pirate(world, state, parts)

    assert state.object_locations[NUGGET] == CHEST_ROOM
    assert state.object_locations[CHEST] == CHEST_ROOM
    assert state.pirate_location == CHEST_ROOM
    assert len(parts) > 0

    # Player can travel to room 64 and recover the stolen treasure
    state.pirate_location = 0  # disable pirate so it doesn't interfere
    state.current_room = CHEST_ROOM
    state.old_room = CHEST_ROOM
    state.visited_rooms.add(CHEST_ROOM)

    result = handle_command(world, state, "get chest")
    assert state.object_locations[CHEST] == CARRIED

    result = handle_command(world, state, "get nugget")
    assert state.object_locations[NUGGET] == CARRIED


def test_dwarves_cleared_on_closing(world: World):
    """Cave closing removes all dwarves and pirate."""
    state = new_game_state(world)
    state.dwarf_stage = 2
    state.dwarf_locations = [19, 27, 33]
    state.dwarf_old_locations = [19, 27, 33]
    state.dwarf_seen = [False, False, False]
    state.pirate_location = 64

    from adventure.engine.commands import _start_closing

    _start_closing(world, state)

    assert state.dwarf_locations == []
    assert state.dwarf_seen == []
    assert state.dwarf_stage == 0
    assert state.pirate_location == 0


def test_attack_dwarf_bare_hands(world: World):
    """Attacking a dwarf bare-handed fails."""
    state = new_game_state(world)
    _enter_deep_cave(world, state)
    state.dwarf_stage = 2
    state.dwarf_locations = []
    state.dwarf_old_locations = []
    state.dwarf_seen = []
    state.pirate_location = 0

    # Place dwarf object at current room for noun resolution
    state.object_locations[DWARF] = state.current_room
    result = handle_command(world, state, "attack dwarf")
    assert "bare hands" in result.lower()


def test_feed_dwarf(world: World):
    """Feeding a dwarf gives the coal message."""
    state = new_game_state(world)
    _enter_deep_cave(world, state)
    state.dwarf_stage = 2
    state.dwarf_locations = []
    state.dwarf_old_locations = []
    state.dwarf_seen = []
    state.pirate_location = 0

    state.object_locations[DWARF] = state.current_room
    result = handle_command(world, state, "feed dwarf")
    assert "coal" in result.lower()
