"""Mutable per-player game state.

All values are ints/bools/sets/dicts — no World references — so this
can be safely pickled for per-player persistence.
"""

from dataclasses import dataclass, field

from .world import World

# Special location values for objects
CARRIED = 0
DESTROYED = -1

# Starting room
START_ROOM = 1

# Key object numbers
KEYS = 1
LAMP = 2
GRATE = 3
CAGE = 4
ROD = 5
ROD2 = 6
BIRD = 7
DOOR = 8
PILLOW = 9
SNAKE = 10
FISSURE = 12
TABLET = 13
CLAM = 14
OYSTER = 15
MAGAZINE = 16
DWARF = 17
FOOD = 19
BOTTLE = 20
WATER = 21
OIL = 22
AXE = 28
DRAGON = 31
CHASM = 32
TROLL = 33
BEAR = 35
CHAIN = 64
VASE = 56
EMERALD = 59
PLANT = 24
PLANT2 = 25
BATTERIES = 39
NUGGET = 50
COINS = 54
CHEST = 55
EGGS = 56
TRIDENT = 57

# Maximum lamp turns
LAMP_LIFE = 330


@dataclass
class GameState:
    """All mutable per-player state. Holds only primitive types."""

    current_room: int = START_ROOM
    old_room: int = START_ROOM
    old_old_room: int = START_ROOM

    # Object locations: obj_id → room_id (0=carried, -1=destroyed)
    object_locations: dict[int, int] = field(default_factory=dict)
    # Object properties: obj_id → int state
    object_props: dict[int, int] = field(default_factory=dict)

    turns: int = 0
    score: int = 0
    lamp_turns: int = LAMP_LIFE
    lamp_on: bool = False

    # Cave closure sequence
    clock1: int = 15  # turns until warning
    clock2: int = 30  # turns until close
    is_closing: bool = False
    is_closed: bool = False
    panic: bool = False

    # Death/resurrection
    deaths: int = 0
    max_deaths: int = 3

    visited_rooms: set[int] = field(default_factory=set)
    is_finished: bool = False

    # Dwarf state
    dwarf_locations: list[int] = field(default_factory=list)
    dwarf_old_locations: list[int] = field(default_factory=list)
    pirate_location: int = 0
    dwarf_killed: int = 0
    knife_location: int = 0
    dwarves_active: bool = False

    # Hint tracking
    hint_turns: dict[int, int] = field(default_factory=dict)
    hints_given: set[int] = field(default_factory=set)

    # Misc flags
    gave_up: bool = False
    treasures_found: int = 0
    said_west: bool = False
    detail_level: int = 0  # how many times LOOK has been used

    # Special flags
    bear_tame: bool = False


def new_game_state(world: World) -> GameState:
    """Create a fresh game state with objects in their starting positions."""
    state = GameState()

    # Place objects in their initial rooms
    for obj_id, obj in world.objects.items():
        if obj.initial_rooms:
            state.object_locations[obj_id] = obj.initial_rooms[0]
        else:
            state.object_locations[obj_id] = DESTROYED

    # Set initial object properties
    state.object_props[GRATE] = 0  # locked
    state.object_props[LAMP] = 0  # off

    # Initialize dwarves at their starting locations
    state.dwarf_locations = [19, 27, 33, 44, 64]
    state.dwarf_old_locations = [19, 27, 33, 44, 64]
    state.pirate_location = 0  # pirate not yet active

    return state
