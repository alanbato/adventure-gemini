"""Command dispatch and handler functions.

handle_command(world, state, raw_input) -> str is the main entry point.
It tokenizes, resolves vocabulary, and dispatches to handler functions.
All handlers mutate state in place and return descriptive text.
"""

import random
from collections.abc import Callable

from .loader import LONG_WORDS
from .state import (
    AXE,
    BEAR,
    BIRD,
    BOTTLE,
    CAGE,
    CARRIED,
    CHAIN,
    CHASM,
    CHEST,
    CLAM,
    DESTROYED,
    DOOR,
    DRAGON,
    EGGS,
    EMERALD,
    FISSURE,
    FOOD,
    GRATE,
    KEYS,
    LAMP,
    MAGAZINE,
    OIL,
    OYSTER,
    PILLOW,
    PLANT,
    PLANT2,
    ROD,
    ROD2,
    SNAKE,
    TABLET,
    TROLL,
    VASE,
    WATER,
    GameState,
)
from .world import World

# The original game only considers the first 5 characters of each word.
WORD_LENGTH = 5


def _normalize_word(word: str) -> str:
    """Truncate a word to the significant prefix length."""
    return word[:WORD_LENGTH]


# Special verb number for "back" (checked explicitly in _cmd_go)
BACK_VERB = 8
# Special verb number for "look" (checked explicitly in _cmd_go)
LOOK_VERB = 57

# Action verbs
ACTION_VERBS = {
    "take",
    "get",
    "carry",
    "drop",
    "release",
    "discard",
    "open",
    "unlock",
    "close",
    "lock",
    "on",
    "light",
    "off",
    "extinguish",
    "wave",
    "calm",
    "go",
    "walk",
    "nothing",
    "pour",
    "eat",
    "drink",
    "rub",
    "throw",
    "quit",
    "score",
    "inventory",
    "fee",
    "fie",
    "foe",
    "foo",
    "fum",
    "brief",
    "read",
    "break",
    "wake",
    "save",
    "blast",
    "find",
    "where",
    "kill",
    "attack",
    "fight",
    "feed",
    "fill",
    "say",
    "help",
    "info",
    "swim",
}


def _tick_lamp(world: World, state: GameState) -> str | None:
    """Tick the lamp and return a message if it ran out, else None."""
    if not state.lamp_on:
        return None
    state.lamp_turns -= 1
    if state.lamp_turns > 0:
        return None
    state.lamp_on = False
    state.object_props[LAMP] = 0
    if _is_dark(world, state):
        return (
            "Your lamp has run out of power.\n\n"
            "It is now pitch dark. If you proceed you will "
            "likely fall into a pit."
        )
    return "Your lamp has run out of power."


def _count_treasures_found(world: World, state: GameState) -> int:
    """Count treasures that have been seen (have a prop value set)."""
    count = 0
    for obj_id, obj in world.objects.items():
        if obj.is_treasure and obj_id in state.object_props:
            count += 1
    return count


def _tick_closing(world: World, state: GameState) -> str | None:
    """Tick the cave closing clocks. Returns message if cave event triggered."""
    if state.is_closed or state.is_finished:
        return None

    # Only start counting when all 15 treasures have been found and player
    # is in a deep room (>=15) that isn't the building approaches
    if not state.is_closing:
        # Check if all treasures have been found
        treasures_found = _count_treasures_found(world, state)
        if treasures_found < 15:
            return None
        if state.current_room < 15 or state.current_room == 33:
            return None

        state.clock1 -= 1
        if state.clock1 > 0:
            return None

        # Start closing!
        return _start_closing(world, state)

    # Already closing — tick clock2
    state.clock2 -= 1
    if state.clock2 > 0:
        return None

    # Close the cave!
    return _close_cave(world, state)


def _start_closing(world: World, state: GameState) -> str:
    """Begin cave closing sequence."""
    state.is_closing = True
    # Lock grate, destroy fissure bridge, remove dwarves/troll/bear
    state.object_props[GRATE] = 0  # locked
    state.object_props[FISSURE] = 0  # bridge gone
    state.object_locations[TROLL] = DESTROYED
    state.object_locations[BEAR] = DESTROYED
    state.dwarf_locations = []
    state.pirate_location = 0
    return world.messages.get(129, "A sepulchral voice says, \"Cave closing soon.\"")


def _close_cave(world: World, state: GameState) -> str:
    """Close the cave — teleport to endgame repository."""
    state.is_closed = True
    state.is_closing = False

    # Drop everything the player is carrying
    for obj_id in list(state.object_locations):
        if state.object_locations[obj_id] == CARRIED:
            state.object_locations[obj_id] = state.current_room

    # Place specific objects in the repository rooms
    state.object_locations[LAMP] = 115
    state.object_props[LAMP] = 1  # on
    state.lamp_on = True
    state.lamp_turns = 50  # enough for endgame
    if ROD2 in state.object_locations:
        state.object_locations[ROD2] = 115

    state.object_locations[GRATE] = 116
    state.object_locations[SNAKE] = 116
    state.object_locations[BIRD] = 116

    # Teleport player to NE end of repository (room 115)
    state.old_room = state.current_room
    state.current_room = 115
    state.visited_rooms.add(115)

    return world.messages.get(132, "The cave is now closed.")


def _dispatch_verb(
    world: World, state: GameState, verb: str, noun: str | None,
) -> str | None:
    """Try to dispatch verb as a motion word, action verb, or noun shortcut."""
    if _is_motion_word(world, verb):
        return _cmd_go(world, state, verb)

    handler = _VERB_DISPATCH.get(verb)
    if handler is not None:
        return handler(world, state, noun)

    if noun is None and verb in world.object_names:
        obj_n = world.object_names[verb]
        if state.object_locations.get(obj_n) == CARRIED:
            return "You're already carrying it!"
        if state.object_locations.get(obj_n) == state.current_room:
            return _cmd_take(world, state, verb)

    return None


def handle_command(world: World, state: GameState, raw_input: str) -> str:
    """Process a command and return the response text."""
    state.turns += 1

    lamp_msg = _tick_lamp(world, state)
    if lamp_msg:
        return lamp_msg

    # Cave closing clock tick
    closing_msg = _tick_closing(world, state)

    words = raw_input.strip().lower().split()
    if not words:
        return "I beg your pardon?"

    verb = _normalize_word(words[0])
    noun = _normalize_word(words[1]) if len(words) > 1 else None

    # Fee/fie/foe/foo/fum are special words dispatched by name
    if verb in ("fee", "fie", "foe", "foo", "fum"):
        result = _cmd_fee_word(world, state, verb)
        if closing_msg:
            return closing_msg + "\n\n" + result
        return result

    result = _dispatch_verb(world, state, verb, noun) or (
        "I don't understand that command."
    )

    if closing_msg:
        return closing_msg + "\n\n" + result
    return result


def _is_motion_word(world: World, word: str) -> bool:
    """Check if a word is a motion verb in the vocabulary."""
    entry = _vocab_lookup(world, word)
    return entry is not None and entry.kind == "motion"


def _resolve_noun(world: World, state: GameState, noun: str | None) -> int | None:
    """Resolve a noun string to an object number.

    When multiple objects share a name (e.g. two rods), prefer the one
    that is at the current location or carried by the player.
    """
    if noun is None:
        return None
    noun = _normalize_word(noun)
    default = world.object_names.get(noun)
    if default is None:
        return None
    if _is_here(state, default):
        return default
    # Check all objects for a same-name match that IS here.
    for obj_id, obj in world.objects.items():
        if obj_id == default:
            continue
        if noun in (n[:WORD_LENGTH] for n in obj.names) and _is_here(state, obj_id):
            return obj_id
    return default


def _is_here(state: GameState, obj_n: int) -> bool:
    """Check if an object is at the current location or carried."""
    loc = state.object_locations.get(obj_n, DESTROYED)
    return loc == state.current_room or loc == CARRIED


def _is_carrying(state: GameState, obj_n: int) -> bool:
    """Check if the player is carrying an object."""
    return state.object_locations.get(obj_n) == CARRIED


def _is_at(state: GameState, obj_n: int, room: int) -> bool:
    """Check if an object is at a specific room."""
    return state.object_locations.get(obj_n) == room


def _is_dark(world: World, state: GameState) -> bool:
    """Check if the current location is dark."""
    room = world.rooms.get(state.current_room)
    if room and room.is_light:
        return False
    if state.lamp_on and _is_here(state, LAMP):
        return False
    return True


def _carried_count(state: GameState) -> int:
    """Count how many objects the player is carrying."""
    return sum(1 for loc in state.object_locations.values() if loc == CARRIED)


def get_room_description(world: World, state: GameState) -> str:
    """Get the description for the current room."""
    room = world.rooms.get(state.current_room)
    if room is None:
        return "You are in a mysterious place."

    if _is_dark(world, state):
        return (
            "It is now pitch dark. If you proceed you will "
            "likely fall into a pit."
        )

    if (
        state.current_room in state.visited_rooms
        and room.short_description
        and state.detail_level == 0
    ):
        return room.short_description.strip()

    desc = room.long_description or room.short_description or "You are somewhere."
    return desc.strip()


def get_visible_objects(world: World, state: GameState) -> list[str]:
    """Get descriptions of objects visible in the current room."""
    if _is_dark(world, state):
        return []

    descriptions = []
    for obj_id, loc in state.object_locations.items():
        if loc == state.current_room:
            obj = world.objects.get(obj_id)
            if obj is None:
                continue
            prop = state.object_props.get(obj_id, 0)
            msg = obj.messages.get(prop, "")
            if msg:
                descriptions.append(msg.strip())
            elif obj.inventory_message:
                # Use inventory message as fallback for ground description
                if obj.names:
                    descriptions.append(f"There is a {obj.names[0]} here.")
    return descriptions


def _direction_verb_map(world: World) -> dict[int, str]:
    """Map vocabulary verb numbers to display names for compass directions."""
    labels = {
        "n": "North", "s": "South", "e": "East", "w": "West",
        "u": "Up", "d": "Down", "in": "In", "out": "Out",
        "ne": "NE", "se": "SE", "sw": "SW", "nw": "NW",
    }
    result: dict[int, str] = {}
    for short, label in labels.items():
        entry = _vocab_lookup(world, short)
        if entry is not None:
            result[entry.number] = label
    return result


def get_exits(world: World, state: GameState) -> list[str]:
    """Get available exit directions for the current room."""
    if _is_dark(world, state):
        return []

    room = world.rooms.get(state.current_room)
    if room is None:
        return []

    verb_to_name = _direction_verb_map(world)

    exits = []
    seen_names: set[str] = set()
    for move in room.travel_table:
        if move.is_forced:
            continue
        # Only show moves that go to rooms (positive destinations)
        if move.destination <= 0 or move.destination > 300:
            continue
        for verb_n in move.verbs:
            if verb_n in verb_to_name:
                name = verb_to_name[verb_n]
                if name not in seen_names:
                    exits.append(name)
                    seen_names.add(name)
    return exits


def get_inventory(world: World, state: GameState) -> list[str]:
    """Get list of carried items."""
    items = []
    for obj_id, loc in state.object_locations.items():
        if loc == CARRIED:
            obj = world.objects.get(obj_id)
            if obj and obj.inventory_message:
                items.append(obj.inventory_message)
            elif obj and obj.names:
                items.append(obj.names[0].capitalize())
    return items


def _vocab_lookup(world: World, word: str):
    """Look up a word in the vocabulary, trying both the truncated
    and LONG_WORDS-expanded forms so that 5-char input like 'plove'
    finds the vocabulary entry stored under 'plover'.
    """
    entry = world.vocabulary.get(word)
    if entry is not None:
        return entry
    expanded = LONG_WORDS.get(word)
    if expanded is not None:
        return world.vocabulary.get(expanded)
    return None


def _resolve_direction(world: World, direction: str) -> int | None:
    """Resolve a direction string to a verb number via the vocabulary."""
    direction = _normalize_word(direction.lower())
    entry = _vocab_lookup(world, direction)
    if entry is not None and entry.kind == "motion":
        return entry.number
    return None


def _move_to(world: World, state: GameState, dest: int) -> str:
    """Move the player to dest and handle forced movement / dark death."""
    state.old_old_room = state.old_room
    state.old_room = state.current_room
    state.current_room = dest
    state.visited_rooms.add(dest)

    new_room = world.rooms.get(dest)
    if new_room and new_room.travel_table and new_room.travel_table[0].is_forced:
        return _handle_forced(world, state, new_room)

    if _is_dark(world, state) and random.random() < 0.35:
        return _cmd_die(world, state)

    return get_room_description(world, state)


def _handle_forced(world: World, state: GameState, room) -> str:
    """Walk forced movement entries with condition checking."""
    msg = get_room_description(world, state)
    for move in room.travel_table:
        if not move.is_forced:
            continue
        if not _check_condition(world, state, move.condition):
            continue
        dest = move.destination
        if 0 < dest <= 300:
            state.old_room = state.current_room
            state.current_room = dest
            state.visited_rooms.add(dest)
            next_room = world.rooms.get(dest)
            if (
                next_room
                and next_room.travel_table
                and next_room.travel_table[0].is_forced
            ):
                return msg + "\n\n" + _handle_forced(
                    world, state, next_room,
                )
            return msg + "\n\n" + get_room_description(world, state)
        if dest < 0:
            return world.messages.get(-dest, "")
        if 301 <= dest <= 500:
            return msg + "\n\n" + _handle_special_movement(
                world, state, dest,
            )
        break
    return msg


def _check_closing_block(
    state: GameState, direction: str,
) -> str | None:
    """Block magic words during cave closing."""
    if not state.is_closing:
        return None
    norm = _normalize_word(direction.lower())
    if norm in ("xyzzy", "plugh"):
        return (
            'A mysterious recorded voice groans into life '
            'and announces:\n'
            '   "This exit is closed.  Please leave via '
            'main office."'
        )
    return None


def _walk_travel_table(
    world: World, state: GameState, room, verb_n: int,
) -> str | None:
    """Walk the travel table for the given verb and return response."""
    for move in room.travel_table:
        if verb_n not in move.verbs and not move.is_forced:
            continue
        if not _check_condition(world, state, move.condition):
            continue
        dest = move.destination
        if dest < 0:
            return world.messages.get(-dest, "You can't go that way.")
        if 301 <= dest <= 500:
            return _handle_special_movement(world, state, dest)
        return _move_to(world, state, dest)
    return None


def _cmd_go(world: World, state: GameState, direction: str) -> str:
    """Handle movement commands."""
    room = world.rooms.get(state.current_room)
    if room is None:
        return "You can't go that way."

    verb_n = _resolve_direction(world, direction)
    if verb_n is None:
        return "I don't know that direction."

    # Special: "back"
    if verb_n == BACK_VERB:
        return _move_to(world, state, state.old_room)

    # Special: "look"
    if verb_n == LOOK_VERB:
        return _cmd_look(world, state)

    # During cave closing, block magic words that go to building
    blocked = _check_closing_block(state, direction)
    if blocked:
        return blocked

    return _walk_travel_table(world, state, room, verb_n) or (
        "You can't go that way."
    )


def _check_condition(world: World, state: GameState, condition: tuple) -> bool:
    """Check if a travel table condition is satisfied."""
    match condition:
        case (None,):
            return True
        case ("%", chance):
            return random.randint(1, 100) <= chance
        case ("not_dwarf",):
            return True  # Simplified: always true for non-dwarves
        case ("carrying", obj_n):
            return _is_carrying(state, obj_n)
        case ("carrying_or_in_room_with", obj_n):
            return _is_carrying(state, obj_n) or _is_at(
                state, obj_n, state.current_room
            )
        case ("prop!=", obj_n, val):
            return state.object_props.get(obj_n, 0) != val
        case _:
            return True


def _handle_special_movement(world: World, state: GameState, dest: int) -> str:
    """Handle special movement codes 301-500."""
    if dest == 301:
        return _cmd_die(world, state)
    if dest == 302:
        # Plover room teleport — drop emerald if carrying
        if _is_carrying(state, EMERALD):
            state.object_locations[EMERALD] = state.current_room
        return _move_to(world, state, 33)
    if dest == 303:
        return _cross_troll_bridge(world, state)
    return "Something strange happens..."


def _cross_troll_bridge(world: World, state: GameState) -> str:
    """Handle crossing the troll bridge (special movement 303)."""
    # Determine which side we're on and the destination
    if state.current_room == 117:
        other_side = 122
    else:
        other_side = 117

    # If carrying bear, bridge collapses
    if _is_carrying(state, BEAR):
        # Bridge collapses, bear and troll fall
        msg = (
            "Just as you reach the other side, the bridge buckles beneath the "
            "weight of the bear and you. You scrabble desperately for support, "
            "but as the bridge collapses you stumble back and fall into the chasm."
        )
        state.object_props[CHASM] = 1  # wrecked bridge
        state.object_props[TROLL] = 2  # troll gone
        state.object_locations[BEAR] = DESTROYED
        state.object_locations[TROLL] = DESTROYED
        return msg + "\n\n" + _cmd_die(world, state)

    # Normal crossing
    result = _move_to(world, state, other_side)
    # After crossing, troll returns to block bridge again
    if state.object_props.get(TROLL, 0) == 0:
        state.object_props[TROLL] = 1
    return result


def _cmd_die(world: World, state: GameState) -> str:
    """Handle player death."""
    state.deaths += 1
    if state.deaths >= state.max_deaths:
        state.is_finished = True
        return (
            "You have died.\n\n"
            "You have used all your resurrections. "
            "The game is over.\n\n"
            f"Your score: {calculate_score(world, state)}"
        )
    state.current_room = 3  # building
    state.old_room = 3
    # Drop all carried items at the building
    for obj_id in list(state.object_locations):
        if state.object_locations[obj_id] == CARRIED:
            state.object_locations[obj_id] = 3  # drop in building
    state.lamp_on = False
    return (
        "You have died.\n\n"
        "I seem to recall you owe me a resurrection. "
        "Very well, you're alive again."
    )


def _take_bear(state: GameState) -> str:
    """Handle taking the bear."""
    if not state.bear_tame:
        return "It is fixed in place."
    state.object_locations[BEAR] = CARRIED
    return "OK."


def _take_special(state: GameState, obj_n: int) -> str | None:
    """Handle special take logic for bird and liquids. Returns message or None."""
    if obj_n == BIRD:
        if _is_carrying(state, ROD):
            return "The bird is frightened by the rod and you cannot catch it."
        if not _is_carrying(state, CAGE):
            return "You can catch the bird, but you cannot carry it."
        state.object_locations[BIRD] = CARRIED
        state.object_props[BIRD] = 1  # in cage
        return "You catch the bird in the cage."

    if obj_n in (WATER, OIL):
        if not _is_carrying(state, BOTTLE):
            return "You have nothing in which to carry it."
        state.object_locations[obj_n] = CARRIED
        state.object_props[BOTTLE] = 1 if obj_n == WATER else 2
        return "Your bottle is now full."

    return None


def _take_from_liquid_source(
    world: World, state: GameState, obj_n: int,
) -> str | None:
    """Take water/oil from a room liquid source. Returns message or None."""
    if obj_n not in (WATER, OIL):
        return None
    room = world.rooms.get(state.current_room)
    if room and room.liquid == obj_n:
        return _take_special(state, obj_n)
    return None


def _is_takeable(state: GameState, obj_n: int, obj) -> bool:
    """Check if an object can be picked up (not fixed in place)."""
    if not obj or not obj.is_fixed:
        return True
    # Chain is takeable when unlocked (prop 0)
    return obj_n == CHAIN and state.object_props.get(CHAIN, 1) == 0


def _do_take(world: World, state: GameState, obj_n: int) -> str:
    """Perform the take after validation (object resolved and located)."""
    obj = world.objects.get(obj_n)

    if obj_n == BEAR:
        return _take_bear(state)

    if not _is_takeable(state, obj_n, obj):
        return "It is fixed in place."

    if _is_dark(world, state):
        return "It's too dark to see!"

    special = _take_special(state, obj_n)
    if special:
        return special

    if _carried_count(state) >= 7:
        return "You can't carry any more. Try dropping something first."

    state.object_locations[obj_n] = CARRIED
    # Mark treasure as "found" for scoring when first picked up
    if obj and obj.is_treasure and obj_n not in state.object_props:
        state.object_props[obj_n] = 0
    return "OK."


def _cmd_take(world: World, state: GameState, noun: str | None = None) -> str:
    """Handle TAKE/GET commands."""
    if noun is None:
        return "What do you want to take?"

    obj_n = _resolve_noun(world, state, noun)
    if obj_n is None:
        return f"I don't know what '{noun}' is."

    if _is_carrying(state, obj_n):
        return "You're already carrying it!"

    if not _is_at(state, obj_n, state.current_room):
        return _take_from_liquid_source(world, state, obj_n) or (
            "I don't see that here."
        )

    return _do_take(world, state, obj_n)


def _cmd_drop(world: World, state: GameState, noun: str | None = None) -> str:
    """Handle DROP commands."""
    if noun is None:
        return "What do you want to drop?"

    obj_n = _resolve_noun(world, state, noun)
    if obj_n is None:
        return f"I don't know what '{noun}' is."

    if not _is_carrying(state, obj_n):
        return "You aren't carrying it!"

    # Special: dropping bird releases it
    if obj_n == BIRD:
        state.object_props[BIRD] = 0
        # Bird scares snake away
        if _is_at(state, SNAKE, state.current_room):
            state.object_locations[SNAKE] = DESTROYED
            state.object_props[SNAKE] = 1
            state.object_locations[BIRD] = state.current_room
            return "The little bird attacks the green snake, which flees."

    # Special: dropping bear at troll
    if obj_n == BEAR:
        if _is_at(state, TROLL, state.current_room) or (
            state.current_room in (117, 122)
            and state.object_props.get(TROLL, 0) == 1
        ):
            # Bear scares troll away
            state.object_locations[BEAR] = state.current_room
            state.object_props[BEAR] = 3  # bear wanders off
            state.object_props[TROLL] = 2  # troll gone
            state.object_locations[TROLL] = DESTROYED
            state.object_props[CHASM] = 0  # bridge open
            return (
                "The bear lumbers toward the troll, who lets out a startled shriek and "
                "scurries away. The bear soon gives up the pursuit and wanders back."
            )
        state.object_locations[BEAR] = state.current_room
        return "OK."

    # Special: vase breaks if dropped without pillow
    if obj_n == VASE:
        if _is_at(state, PILLOW, state.current_room):
            state.object_props[VASE] = 0
            state.object_locations[VASE] = state.current_room
            return "The vase is now resting, delicately, on a velvet pillow."
        state.object_props[VASE] = 2  # broken
        state.object_locations[VASE] = state.current_room
        return (
            "The vase drops with a delicate crash and shatters into "
            "a thousand pieces."
        )

    state.object_locations[obj_n] = state.current_room
    return "OK."


def _open_grate(state: GameState) -> str:
    if not _is_here(state, KEYS):
        return "You have no keys!"
    state.object_props[GRATE] = 1
    return "The grate is now open."


def _open_clam(state: GameState) -> str:
    if _is_carrying(state, CLAM):
        return "I advise you to put down the clam before opening it. >STRAIN!<"
    state.object_locations[CLAM] = DESTROYED
    state.object_locations[OYSTER] = state.current_room
    # Pearl rolls to cul-de-sac (room 105)
    state.object_locations[61] = 105  # pearl
    state.object_props[61] = 0
    return "A glistening pearl falls out of the clam and rolls away!"


def _open_chain(state: GameState) -> str:
    if not _is_here(state, KEYS):
        return "You have no keys!"
    state.object_props[CHAIN] = 0
    state.object_locations[CHAIN] = state.current_room
    if _is_here(state, BEAR):
        state.object_props[BEAR] = 1
        state.bear_tame = True
    return "The chain is now unlocked."


def _open_door(state: GameState) -> str:
    if state.object_props.get(DOOR, 0) == 1:
        return "The door is open."
    return "The door is extremely rusty and refuses to open."


_OPEN_HANDLERS: dict[int, Callable] = {
    DOOR: _open_door,
    OYSTER: lambda _: "The oyster creaks open, revealing nothing inside.",
    GRATE: lambda s: _open_grate(s),
    CLAM: lambda s: _open_clam(s),
    CHAIN: lambda s: _open_chain(s),
}


def _cmd_open(world: World, state: GameState, noun: str | None = None) -> str:
    """Handle OPEN/UNLOCK commands."""
    if noun is None:
        return "What do you want to open?"

    obj_n = _resolve_noun(world, state, noun)
    if obj_n is None:
        return f"I don't know what '{noun}' is."

    handler = _OPEN_HANDLERS.get(obj_n)
    if handler:
        return handler(state)

    return "I don't know how to open that."


def _cmd_close(world: World, state: GameState, noun: str | None = None) -> str:
    """Handle CLOSE/LOCK commands."""
    if noun is None:
        return "What do you want to close?"

    obj_n = _resolve_noun(world, state, noun)
    if obj_n is None:
        return f"I don't know what '{noun}' is."

    if obj_n == GRATE:
        state.object_props[GRATE] = 0  # locked
        return "The grate is now locked."

    return "I don't know how to close that."


def _cmd_on(world: World, state: GameState, noun: str | None = None) -> str:
    """Handle ON/LIGHT commands."""
    if not _is_here(state, LAMP):
        return "You have no source of light."
    if state.lamp_turns <= 0:
        return "Your lamp has run out of power."
    state.lamp_on = True
    state.object_props[LAMP] = 1
    if _is_dark(world, state):
        return "Your lamp is now on."
    return "Your lamp is now on.\n\n" + get_room_description(world, state)


def _cmd_off(world: World, state: GameState, noun: str | None = None) -> str:
    """Handle OFF/EXTINGUISH commands."""
    if not _is_here(state, LAMP):
        return "You have no source of light."
    state.lamp_on = False
    state.object_props[LAMP] = 0
    return "Your lamp is now off."


def _cmd_look(world: World, state: GameState, noun: str | None = None) -> str:
    """Handle LOOK command."""
    state.detail_level += 1
    room = world.rooms.get(state.current_room)
    if room is None:
        return "You are in a mysterious place."

    if _is_dark(world, state):
        return "It is now pitch dark. If you proceed you will likely fall into a pit."

    desc = room.long_description or room.short_description or "You are somewhere."
    return desc.strip()


def _cmd_inventory(world: World, state: GameState, noun: str | None = None) -> str:
    """Handle INVENTORY command."""
    items = get_inventory(world, state)
    if not items:
        return "You're not carrying anything."
    result = "You are currently holding:\n"
    for item in items:
        result += f"  {item}\n"
    return result.strip()


def _cmd_score(world: World, state: GameState, noun: str | None = None) -> str:
    """Handle SCORE command."""
    score = calculate_score(world, state)
    return f"Your current score is {score} out of a possible 350."


def _cmd_quit(world: World, state: GameState, noun: str | None = None) -> str:
    """Handle QUIT command."""
    state.is_finished = True
    state.gave_up = True
    score = calculate_score(world, state)
    return f"You scored {score} out of a possible 350. Thanks for playing!"


def _cmd_eat(world: World, state: GameState, noun: str | None = None) -> str:
    """Handle EAT command."""
    if noun is None:
        return "What do you want to eat?"
    obj_n = _resolve_noun(world, state, noun)
    if obj_n == FOOD:
        state.object_locations[FOOD] = DESTROYED
        return "Thank you, it was delicious!"
    if obj_n in (BIRD, SNAKE):
        return "I think I just lost my appetite."
    return "That's not something I'd want to eat."


def _cmd_drink(world: World, state: GameState, noun: str | None = None) -> str:
    """Handle DRINK command."""
    if noun is None or _normalize_word(noun) == "water":
        if _is_carrying(state, WATER):
            state.object_locations[WATER] = DESTROYED
            state.object_props[BOTTLE] = 0
            return "The water is refreshing."
        room = world.rooms.get(state.current_room)
        if room and room.liquid == WATER:
            return "You take a drink from the stream."
        return "There is nothing here to drink."
    return "That's not something you can drink."


def _cmd_pour(world: World, state: GameState, noun: str | None = None) -> str:
    """Handle POUR command."""
    if not _is_carrying(state, BOTTLE):
        return "You aren't carrying it!"

    if _is_carrying(state, WATER):
        state.object_locations[WATER] = DESTROYED
        state.object_props[BOTTLE] = 0
        # Watering plant
        if _is_at(state, PLANT, state.current_room):
            prop = state.object_props.get(PLANT, 0)
            state.object_props[PLANT] = prop + 2
            state.object_props[PLANT2] = prop + 2  # mirror plant2 state
            if prop == 0:
                return (
                    "The plant spurts into furious growth for a few seconds."
                )
            return "The plant grows explosively."
        return "Your bottle is now empty."

    if _is_carrying(state, OIL):
        state.object_locations[OIL] = DESTROYED
        state.object_props[BOTTLE] = 0
        if _is_at(state, DOOR, state.current_room):
            state.object_props[DOOR] = 1
            return "The oil has freed up the hinges so that the door will now open."
        return "Your bottle is now empty."

    return "Your bottle is empty."


def _cmd_fill(world: World, state: GameState, noun: str | None = None) -> str:
    """Handle FILL command."""
    if noun and _normalize_word(noun) == "bottl":
        if not _is_carrying(state, BOTTLE):
            return "You aren't carrying it!"
        if _is_carrying(state, WATER) or _is_carrying(state, OIL):
            return "Your bottle is already full."
        room = world.rooms.get(state.current_room)
        if room and room.liquid:
            liquid = room.liquid
            state.object_locations[liquid] = CARRIED
            state.object_props[BOTTLE] = 1 if liquid == WATER else 2
            return "Your bottle is now full."
        return "There is nothing here with which to fill the bottle."
    return "You can't fill that."


def _cmd_wave(world: World, state: GameState, noun: str | None = None) -> str:
    """Handle WAVE command."""
    obj_n = _resolve_noun(world, state, noun)
    if obj_n == ROD and _is_carrying(state, ROD):
        # Waving rod at fissure
        if state.current_room == 17 or state.current_room == 27:
            prop = state.object_props.get(12, 0)  # fissure
            state.object_props[12] = 1 - prop  # toggle
            if state.object_props[12] == 1:
                return "A crystal bridge now spans the fissure."
            return "The crystal bridge vanishes!"
        return "Nothing happens."
    return "Nothing happens."


def _cmd_throw(world: World, state: GameState, noun: str | None = None) -> str:
    """Handle THROW command."""
    if noun is None:
        return "What do you want to throw?"
    obj_n = _resolve_noun(world, state, noun)
    if obj_n is None:
        return f"I don't know what '{noun}' is."
    if not _is_carrying(state, obj_n):
        return "You aren't carrying it!"

    # Throwing axe at dwarf
    if obj_n == AXE:
        state.object_locations[AXE] = state.current_room
        return "The axe bounces harmlessly off a wall and falls to the ground."

    # Throwing treasure at troll
    troll_here = (
        _is_at(state, TROLL, state.current_room)
        or (
            _is_at(state, TROLL, 117)
            and state.current_room in (117, 122)
        )
    )
    if troll_here:
        obj = world.objects.get(obj_n)
        if obj and obj.is_treasure:
            state.object_locations[obj_n] = DESTROYED
            state.object_props[TROLL] = 2
            state.object_locations[TROLL] = DESTROYED
            state.object_props[CHASM] = 0
            fallback = (
                "The troll catches your treasure "
                "and scurries away out of sight."
            )
            return world.messages.get(159, fallback)

    # Default: just drop it
    return _cmd_drop(world, state, noun)


def _attack_dragon(state: GameState) -> str:
    if state.object_props.get(DRAGON, 0) != 0:
        return "The dragon is already dead."
    state.object_props[DRAGON] = 1  # dead
    state.object_props[DRAGON + 100] = 0
    # Rug is no longer pinned under dragon — make it takeable at player's room
    state.object_locations[62] = state.current_room  # rug
    state.object_props[62] = 0  # rug is free
    return (
        "With what? Your bare hands?\n\n"
        "Congratulations! You have just vanquished a dragon "
        "with your bare hands! (Strstrstr...)"
    )


def _attack_bird(state: GameState) -> str:
    if _is_here(state, BIRD):
        state.object_locations[BIRD] = DESTROYED
        return "The little bird is now dead. Its body disappears."
    return "I see no bird here."


def _attack_bear(state: GameState) -> str:
    if state.bear_tame:
        return "The bear is confused. He only wants to be your friend."
    return "With what? Your bare hands? Against HIS bare hands?"


_ATTACK_HANDLERS: dict[int, Callable] = {
    DRAGON: _attack_dragon,
    SNAKE: lambda _: "Attacking the snake both doesn't work and is very dangerous.",
    BIRD: _attack_bird,
    TROLL: lambda _: (
        "Trolls are close relatives with the rocks "
        "and have skin as tough as stone."
    ),
    BEAR: _attack_bear,
}


def _cmd_attack(world: World, state: GameState, noun: str | None = None) -> str:
    """Handle KILL/ATTACK commands."""
    if noun is None:
        return "What do you want to attack?"
    obj_n = _resolve_noun(world, state, noun)
    handler = _ATTACK_HANDLERS.get(obj_n)
    if handler:
        return handler(state)
    return "I'm game. Would you care to explain how?"


def _feed_snake(state: GameState) -> str:
    if _is_carrying(state, BIRD):
        state.object_locations[BIRD] = DESTROYED
        return "The snake devours your bird!"
    return "There's nothing here it wants to eat."


def _feed_bear(state: GameState) -> str:
    if _is_carrying(state, FOOD):
        state.object_locations[FOOD] = DESTROYED
        state.object_props[BEAR] = 1
        state.bear_tame = True
        return "The bear eagerly wolfs down your food."
    return "There's nothing here it wants to eat."


_FEED_HANDLERS: dict[int, Callable] = {
    BIRD: lambda _: "It's not hungry (it's merely pstrp).",
    DRAGON: lambda _: "There's nothing here it wants to eat (strstrstr...).",
    SNAKE: _feed_snake,
    TROLL: lambda _: "Gluttony is not one of the tstrstrstr...",
    BEAR: _feed_bear,
}


def _cmd_feed(world: World, state: GameState, noun: str | None = None) -> str:
    """Handle FEED command."""
    if noun is None:
        return "What do you want to feed?"
    obj_n = _resolve_noun(world, state, noun)
    handler = _FEED_HANDLERS.get(obj_n)
    if handler:
        return handler(state)
    return "I'm not sure what you want me to do."


_READABLE_MESSAGES: dict[int, str] = {
    MAGAZINE: (
        "The magazine is written in dwarvish. "
        'The only thing you can make out is "STRSTRSTR".'
    ),
    TABLET: '"CONGRATULATIONS ON BRINGING LIGHT INTO THE DARK-ROOM!"',
    OYSTER: "It says the same thing it did before.",
}


def _cmd_read(world: World, state: GameState, noun: str | None = None) -> str:
    """Handle READ command."""
    if _is_dark(world, state):
        return "It's too dark to read!"
    if noun is None:
        return "What do you want to read?"
    obj_n = _resolve_noun(world, state, noun)

    message = _READABLE_MESSAGES.get(obj_n)
    if message and _is_here(state, obj_n):
        return message

    return "I see nothing to read here."


def _cmd_break(world: World, state: GameState, noun: str | None = None) -> str:
    """Handle BREAK command."""
    obj_n = _resolve_noun(world, state, noun)
    if obj_n == VASE and _is_here(state, VASE):
        state.object_props[VASE] = 2
        state.object_locations[VASE] = state.current_room
        return "You have taken the vase and hurled it delicately to the ground."
    return "It is beyond your power to do that."


def _cmd_find(world: World, state: GameState, noun: str | None = None) -> str:
    """Handle FIND/WHERE command."""
    if noun is None:
        return "What do you want to find?"
    obj_n = _resolve_noun(world, state, noun)
    if obj_n is None:
        return f"I don't know what '{noun}' is."
    if _is_carrying(state, obj_n):
        return "You're carrying it!"
    if _is_at(state, obj_n, state.current_room):
        return "I believe it's right here."
    return "I have no idea where it is."


def _cmd_say(world: World, state: GameState, noun: str | None = None) -> str:
    """Handle SAY command."""
    if not noun:
        return "What do you want to say?"
    word = _normalize_word(noun.lower())
    if word in ("xyzzy", "plugh", "plove"):
        return _cmd_go(world, state, word)
    return f'OK, "{word}".'


def _cmd_brief(world: World, state: GameState, noun: str | None = None) -> str:
    """Handle BRIEF command."""
    state.detail_level = 0
    return "OK, I'll only describe a place in full the first time you come to it."


def _cmd_help(world: World, state: GameState, noun: str | None = None) -> str:
    """Handle HELP command."""
    return (
        "I know of places, actions, and things. Most of my vocabulary\n"
        "describes places and is used to move you there. To move, try\n"
        "words like NORTH, IN, WEST, UP, etc. I know about a few special\n"
        "objects and can be told to manipulate them using one of the action\n"
        "words I know. I have a strstrstrstricted vocabulary; usually a\n"
        "word or two will suffice."
    )


def _score_treasures(world: World, state: GameState) -> int:
    """Score points for treasures found and stored."""
    score = 0
    for obj_id, obj in world.objects.items():
        if not obj.is_treasure:
            continue
        if obj_id < CHEST:
            value = 12
        elif obj_id == CHEST:
            value = 14
        else:
            value = 16
        if obj_id in state.object_props:
            score += 2
        in_building = state.object_locations.get(obj_id) == 3
        prop_zero = state.object_props.get(obj_id, -1) == 0
        if in_building and prop_zero:
            score += value - 2
    return score


def calculate_score(world: World, state: GameState) -> int:
    """Calculate the current score using the original 350-point formula."""
    score = 2 + _score_treasures(world, state)

    # Survival bonus: 10 per unused death
    score += (state.max_deaths - state.deaths) * 10

    # Not quitting
    if not state.gave_up:
        score += 4

    # Getting into cave (dwarves activated)
    if state.dwarves_active:
        score += 25

    # Cave closing started
    if state.is_closing:
        score += 25

    # Cave closed + endgame bonus
    if state.is_closed:
        score += 25
        bonus_scores = {133: 45, 134: 30, 135: 25, 0: 10}
        score += bonus_scores.get(state.bonus, 10)

    # Magazine in Witt's End (room 108)
    if state.object_locations.get(MAGAZINE) == 108:
        score += 1

    # Hint penalties
    for hint_n in state.hints_given:
        hint = world.hints.get(hint_n)
        if hint:
            score -= hint.penalty

    return score


def _cmd_fee_word(world: World, state: GameState, word: str) -> str:
    """Handle a specific fee/fie/foe/foo word."""
    sequence = ["fee", "fie", "foe", "foo"]
    if word == "fum":
        word = "fee"  # fum is a synonym for fee
    idx = sequence.index(word) if word in sequence else -1
    if idx < 0:
        return "I don't understand that."

    if idx == 0:
        # Starting the sequence
        state.foobar = state.turns
        return "OK."

    # Check that previous word was said on the previous turn
    expected_gap = idx  # fee at turn T, fie at T+1, foe at T+2, foo at T+3
    if state.turns - state.foobar != expected_gap:
        state.foobar = 0
        return "What's the matter, can't you read?  Now you'd best start over."

    if idx < 3:
        # fie or foe — just continue the sequence
        return "OK."

    # idx == 3: FOO — teleport eggs back to giant room (92)
    if _is_at(state, EGGS, 92) and _is_at(state, TROLL, DESTROYED):
        # Eggs already there, nothing special
        pass
    elif _is_at(state, EGGS, 92):
        # Eggs already in giant room — just describe
        return "Nothing happens."

    # Move eggs to room 92 (giant room)
    state.object_locations[EGGS] = 92
    state.object_props[EGGS] = 0

    # If troll was killed (prop==2) and eggs were used to pay, troll comes back
    if state.object_props.get(TROLL, 0) == 2:
        state.object_props[TROLL] = 0
        state.object_locations[TROLL] = 117
        state.object_props[CHASM] = 0

    if state.current_room == 92:
        return get_room_description(world, state)
    return "Done!"


def _cmd_blast(world: World, state: GameState, noun: str | None = None) -> str:
    """Handle BLAST command — endgame only."""
    if not state.is_closed:
        return "Blasting requires dynamite."

    has_rod2 = _is_carrying(state, ROD2) or _is_here(state, ROD2)
    if not has_rod2:
        return "Blasting requires dynamite."

    state.is_finished = True

    if state.current_room == 116:
        state.bonus = 133  # 45 points — maximum
        return world.messages.get(133, "")
    if state.current_room == 115:
        state.bonus = 134  # 30 points
        return world.messages.get(134, "")
    state.bonus = 135  # 25 points
    return world.messages.get(135, "")


def _static_response(msg: str):
    """Return a handler that ignores all arguments and returns a fixed message."""
    def handler(world: World, state: GameState, noun: str | None = None) -> str:
        return msg
    return handler


_VERB_DISPATCH: dict[str, Callable] = {
    **dict.fromkeys(("take", "get", "carry", "catch", "steal", "captu"), _cmd_take),
    **dict.fromkeys(("drop", "relea", "disca"), _cmd_drop),
    **dict.fromkeys(("open", "unloc"), _cmd_open),
    **dict.fromkeys(("close", "lock"), _cmd_close),
    **dict.fromkeys(("on", "light"), _cmd_on),
    **dict.fromkeys(("off", "extin"), _cmd_off),
    **dict.fromkeys(("look", "l"), _cmd_look),
    **dict.fromkeys(("inven", "i"), _cmd_inventory),
    **dict.fromkeys(("quit", "q"), _cmd_quit),
    **dict.fromkeys(("throw", "toss"), _cmd_throw),
    **dict.fromkeys(("kill", "attac", "fight"), _cmd_attack),
    **dict.fromkeys(("read", "perus"), _cmd_read),
    **dict.fromkeys(("break", "shatt"), _cmd_break),
    **dict.fromkeys(("find", "where"), _cmd_find),
    **dict.fromkeys(("help", "info"), _cmd_help),
    "score": _cmd_score,
    "eat": _cmd_eat,
    "drink": _cmd_drink,
    "pour": _cmd_pour,
    "fill": _cmd_fill,
    **dict.fromkeys(("wave", "swing"), _cmd_wave),
    "feed": _cmd_feed,
    "say": _cmd_say,
    "brief": _cmd_brief,
    **dict.fromkeys(("blast", "deton", "ignit", "blowu"), _cmd_blast),
    "swim": _static_response("I don't know how."),
    "nothi": _static_response("OK."),
    "save": _static_response(
        "Your game is automatically saved after each move."
    ),
}
