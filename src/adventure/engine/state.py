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
BIRD = 8
DOOR = 9
PILLOW = 10
SNAKE = 11
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
VASE = 58
EMERALD = 59
MESSAGE = 36  # "message in a bottle" object (pirate hint item)
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

# Dwarf starting positions (rooms)
DWARF_START_LOCATIONS = [19, 27, 33, 44, 64]

# Pirate stash locations
CHEST_ROOM = 64  # Dead end where pirate deposits stolen treasures
PIRATE_MSG_ROOM = 140  # Room for pirate message/hint object


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

    # Dwarf state: stage 0=dormant, 1=armed, 2=active, 3=aggressive
    dwarf_stage: int = 0
    dwarf_locations: list[int] = field(default_factory=list)
    dwarf_old_locations: list[int] = field(default_factory=list)
    dwarf_seen: list[bool] = field(default_factory=list)
    dwarf_killed: int = 0
    knife_location: int = 0

    # Pirate state
    pirate_location: int = 0
    pirate_old_location: int = 0
    pirate_seen: bool = False

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

    # Fee-fi-fo-fum sequence: turn number of last valid word in sequence
    foobar: int = 0

    # Endgame blast bonus code (0=not blasted, 133/134/135=blast variants)
    bonus: int = 0

    # Count of treasures not yet seen (prop still < 0 / not in object_props)
    treasures_not_found: int = 15

    @property
    def dwarves_active(self) -> bool:
        """Backward-compatible alias: True when dwarf_stage > 0."""
        return self.dwarf_stage > 0


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
    state.dwarf_locations = DWARF_START_LOCATIONS.copy()
    state.dwarf_old_locations = DWARF_START_LOCATIONS.copy()
    state.dwarf_seen = [False] * len(DWARF_START_LOCATIONS)
    state.pirate_location = CHEST_ROOM
    state.pirate_old_location = CHEST_ROOM

    return state
