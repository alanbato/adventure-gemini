"""Command dispatch and handler functions.

handle_command(world, state, raw_input) -> str is the main entry point.
It tokenizes, resolves vocabulary, and dispatches to handler functions.
All handlers mutate state in place and return descriptive text.
"""

import random

from .state import (
    AXE,
    BEAR,
    BIRD,
    BOTTLE,
    CAGE,
    CARRIED,
    CHAIN,
    CLAM,
    DESTROYED,
    DOOR,
    DRAGON,
    FOOD,
    GRATE,
    KEYS,
    LAMP,
    MAGAZINE,
    OIL,
    OYSTER,
    PILLOW,
    PLANT,
    ROD,
    SNAKE,
    TABLET,
    TROLL,
    VASE,
    WATER,
    GameState,
)
from .world import World

# Motion word numbers (from section 4 of advent.dat)
# These map to verb numbers in the vocabulary
MOTION_WORDS = {
    "north": 43,
    "south": 44,
    "east": 45,
    "west": 46,
    "ne": 47,
    "se": 48,
    "sw": 49,
    "nw": 50,
    "up": 29,
    "down": 30,
    "left": 36,
    "right": 37,
    "in": 19,
    "out": 11,
    "back": 8,
    "look": 57,
    "cross": 39,
    "climb": 56,
    "jump": 39,
    "xyzzy": 62,
    "plugh": 63,
    "plover": 65,
    "n": 43,
    "s": 44,
    "e": 45,
    "w": 46,
    "u": 29,
    "d": 30,
}

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


def _dispatch_verb(
    world: World, state: GameState, verb: str, noun: str | None,
) -> str | None:
    """Try to dispatch verb as a motion word, action verb, or noun shortcut."""
    if verb in MOTION_WORDS or _is_motion_word(world, verb):
        return _cmd_go(world, state, verb)

    handler = _VERB_DISPATCH.get(verb)
    if handler is not None:
        return handler(world, state, noun)

    if verb in world.vocabulary and world.vocabulary[verb].kind == "motion":
        return _cmd_go(world, state, verb)

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

    words = raw_input.strip().lower().split()
    if not words:
        return "I beg your pardon?"

    verb = words[0][:5]
    noun = words[1][:5] if len(words) > 1 else None

    return _dispatch_verb(world, state, verb, noun) or (
        "I don't understand that command."
    )


def _is_motion_word(world: World, word: str) -> bool:
    """Check if a word is a motion verb in the vocabulary."""
    if word in world.vocabulary:
        return world.vocabulary[word].kind == "motion"
    return False


def _resolve_noun(world: World, state: GameState, noun: str | None) -> int | None:
    """Resolve a noun string to an object number."""
    if noun is None:
        return None
    noun = noun[:5]
    if noun in world.object_names:
        return world.object_names[noun]
    return None


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
    return [d for d in descriptions if d]


def get_exits(world: World, state: GameState) -> list[str]:
    """Get available exit directions for the current room."""
    if _is_dark(world, state):
        return []

    room = world.rooms.get(state.current_room)
    if room is None:
        return []

    # Map verb numbers to direction names
    verb_to_name = {
        43: "North",
        44: "South",
        45: "East",
        46: "West",
        29: "Up",
        30: "Down",
        19: "In",
        11: "Out",
        47: "NE",
        48: "SE",
        49: "SW",
        50: "NW",
    }

    exits = []
    seen_names = set()
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


def _resolve_direction(world: World, direction: str) -> int | None:
    """Resolve a direction string to a verb number."""
    direction = direction[:5].lower()
    verb_n = MOTION_WORDS.get(direction)
    if verb_n is not None:
        return verb_n
    if direction in world.vocabulary:
        word = world.vocabulary[direction]
        if word.kind == "motion":
            return word.number
    return None


def _move_to(world: World, state: GameState, dest: int) -> str:
    """Move the player to dest and handle forced movement / dark death."""
    state.old_old_room = state.old_room
    state.old_room = state.current_room
    state.current_room = dest
    state.visited_rooms.add(dest)

    new_room = world.rooms.get(dest)
    if new_room and new_room.travel_table and new_room.travel_table[0].is_forced:
        forced = new_room.travel_table[0]
        if 0 < forced.destination <= 300:
            msg = get_room_description(world, state)
            state.old_room = state.current_room
            state.current_room = forced.destination
            state.visited_rooms.add(forced.destination)
            return msg + "\n\n" + get_room_description(world, state)
        if forced.destination < 0:
            return world.messages.get(-forced.destination, "")

    if _is_dark(world, state) and random.random() < 0.35:
        return _cmd_die(world, state)

    return get_room_description(world, state)


def _cmd_go(world: World, state: GameState, direction: str) -> str:
    """Handle movement commands."""
    room = world.rooms.get(state.current_room)
    if room is None:
        return "You can't go that way."

    verb_n = _resolve_direction(world, direction)
    if verb_n is None:
        return "I don't know that direction."

    # Special: "back"
    if verb_n == 8:
        return _move_to(world, state, state.old_room)

    # Special: "look"
    if verb_n == 57:
        return _cmd_look(world, state)

    # Walk the travel table
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

    return "You can't go that way."


def _check_condition(world: World, state: GameState, condition: tuple) -> bool:
    """Check if a travel table condition is satisfied."""
    c = condition[0]
    if c is None:
        return True
    if c == "%":
        return random.randint(1, 100) <= condition[1]
    if c == "not_dwarf":
        return True  # Simplified: always true for non-dwarves
    if c == "carrying":
        return _is_carrying(state, condition[1])
    if c == "carrying_or_in_room_with":
        return _is_carrying(state, condition[1]) or _is_at(
            state, condition[1], state.current_room
        )
    if c == "prop!=":
        obj_n, val = condition[1], condition[2]
        return state.object_props.get(obj_n, 0) != val
    return True


def _handle_special_movement(world: World, state: GameState, dest: int) -> str:
    """Handle special movement codes 301-500."""
    # These are mostly death and special location handling
    if dest == 301:
        return _cmd_die(world, state)
    return "Something strange happens..."


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
    for obj_id in list(state.object_locations.keys()):
        if state.object_locations[obj_id] == CARRIED:
            state.object_locations[obj_id] = 3  # drop in building
    state.lamp_on = False
    return (
        "You have died.\n\n"
        "I seem to recall you owe me a resurrection. "
        "Very well, you're alive again."
    )


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


def _cmd_take(world: World, state: GameState, noun: str | None) -> str:
    """Handle TAKE/GET commands."""
    if noun is None:
        return "What do you want to take?"

    obj_n = _resolve_noun(world, state, noun)
    if obj_n is None:
        return f"I don't know what '{noun}' is."

    if _is_carrying(state, obj_n):
        return "You're already carrying it!"

    if not _is_at(state, obj_n, state.current_room):
        return "I don't see that here."

    obj = world.objects.get(obj_n)
    if obj and obj.is_fixed:
        return "It is fixed in place."

    if _is_dark(world, state):
        return "It's too dark to see!"

    special = _take_special(state, obj_n)
    if special:
        return special

    if _carried_count(state) >= 7:
        return "You can't carry any more. Try dropping something first."

    state.object_locations[obj_n] = CARRIED
    return "OK."


def _cmd_drop(world: World, state: GameState, noun: str | None) -> str:
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
            state.object_locations[BIRD] = state.current_room
            return "The little bird attacks the green snake, which flees."

    # Special: vase breaks if dropped without pillow
    if obj_n == VASE:
        if not _is_at(state, PILLOW, state.current_room):
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
    if not _is_carrying(state, CLAM):
        return "I advise you to put down the clam before opening it. >STRAIN!<"
    state.object_locations[CLAM] = DESTROYED
    state.object_locations[OYSTER] = state.current_room
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


_OPEN_HANDLERS: dict[int, callable] = {
    DOOR: lambda _: "The door is extremely rusty and refuses to open.",
    OYSTER: lambda _: "The oyster creaks open, revealing nothing inside.",
    GRATE: lambda s: _open_grate(s),
    CLAM: lambda s: _open_clam(s),
    CHAIN: lambda s: _open_chain(s),
}


def _cmd_open(world: World, state: GameState, noun: str | None) -> str:
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


def _cmd_close(world: World, state: GameState, noun: str | None) -> str:
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


def _cmd_eat(world: World, state: GameState, noun: str | None) -> str:
    """Handle EAT command."""
    if noun is None:
        return "What do you want to eat?"
    obj_n = _resolve_noun(world, state, noun)
    if obj_n == FOOD:
        state.object_locations[FOOD] = DESTROYED
        return "Thank you, it was delicious!"
    if obj_n == BIRD or obj_n == SNAKE:
        return "I think I just lost my appetite."
    return "That's not something I'd want to eat."


def _cmd_drink(world: World, state: GameState, noun: str | None) -> str:
    """Handle DRINK command."""
    if noun is None or noun[:5] == "water":
        if _is_carrying(state, WATER):
            state.object_locations[WATER] = DESTROYED
            state.object_props[BOTTLE] = 0
            return "The water is refreshing."
        room = world.rooms.get(state.current_room)
        if room and room.liquid == 22:
            return "You take a drink from the stream."
        return "There is nothing here to drink."
    return "That's not something you can drink."


def _cmd_pour(world: World, state: GameState, noun: str | None) -> str:
    """Handle POUR command."""
    if not _is_carrying(state, BOTTLE):
        return "You aren't carrying it!"

    if _is_carrying(state, WATER):
        state.object_locations[WATER] = DESTROYED
        state.object_props[BOTTLE] = 0
        # Watering plant
        if _is_at(state, PLANT, state.current_room):
            prop = state.object_props.get(PLANT, 0)
            state.object_props[PLANT] = prop + 1
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


def _cmd_fill(world: World, state: GameState, noun: str | None) -> str:
    """Handle FILL command."""
    if noun and noun[:5] == "bottl":
        if not _is_carrying(state, BOTTLE):
            return "You aren't carrying it!"
        if _is_carrying(state, WATER) or _is_carrying(state, OIL):
            return "Your bottle is already full."
        room = world.rooms.get(state.current_room)
        if room and room.liquid:
            liquid = room.liquid
            state.object_locations[liquid] = CARRIED
            state.object_props[BOTTLE] = 1 if liquid == 22 else 2
            return "Your bottle is now full."
        return "There is nothing here with which to fill the bottle."
    return "You can't fill that."


def _cmd_wave(world: World, state: GameState, noun: str | None) -> str:
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


def _cmd_throw(world: World, state: GameState, noun: str | None) -> str:
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

    # Default: just drop it
    return _cmd_drop(world, state, noun)


def _cmd_attack(world: World, state: GameState, noun: str | None) -> str:
    """Handle KILL/ATTACK commands."""
    if noun is None:
        return "What do you want to attack?"
    obj_n = _resolve_noun(world, state, noun)

    if obj_n == DRAGON:
        if state.object_props.get(DRAGON, 0) != 0:
            return "The dragon is already dead."
        state.object_props[DRAGON] = 1  # dead
        state.object_props[DRAGON + 100] = 0
        return (
            "With what? Your bare hands?\n\n"
            "Congratulations! You have just vanquished a dragon "
            "with your bare hands! (Strstrstr...)"
        )

    if obj_n == SNAKE:
        return "Attacking the snake both doesn't work and is very dangerous."

    if obj_n == BIRD:
        if _is_here(state, BIRD):
            state.object_locations[BIRD] = DESTROYED
            return "The little bird is now dead. Its body disappears."
        return "I see no bird here."

    if obj_n == TROLL:
        return (
            "Trolls are close relatives with the rocks "
            "and have skin as tough as stone."
        )

    if obj_n == BEAR:
        if state.bear_tame:
            return "The bear is confused. He only wants to be your friend."
        return "With what? Your bare hands? Against HIS bare hands?"

    return "I'm game. Would you care to explain how?"


def _cmd_feed(world: World, state: GameState, noun: str | None) -> str:
    """Handle FEED command."""
    if noun is None:
        return "What do you want to feed?"
    obj_n = _resolve_noun(world, state, noun)

    if obj_n == BIRD:
        return "It's not hungry (it's merely pstrp)."
    if obj_n == DRAGON:
        return "There's nothing here it wants to eat (strstrstr...)."
    if obj_n == SNAKE:
        if _is_carrying(state, BIRD):
            state.object_locations[BIRD] = DESTROYED
            return "The snake devours your bird!"
        return "There's nothing here it wants to eat."
    if obj_n == TROLL:
        return "Gluttony is not one of the tstrstrstr..."
    if obj_n == BEAR:
        if _is_carrying(state, FOOD):
            state.object_locations[FOOD] = DESTROYED
            state.object_props[BEAR] = 1
            state.bear_tame = True
            return "The bear eagerly wolfs down your food."
        return "There's nothing here it wants to eat."

    return "I'm not sure what you want me to do."


def _cmd_read(world: World, state: GameState, noun: str | None) -> str:
    """Handle READ command."""
    if _is_dark(world, state):
        return "It's too dark to read!"
    if noun is None:
        return "What do you want to read?"
    obj_n = _resolve_noun(world, state, noun)

    if obj_n == MAGAZINE and _is_here(state, MAGAZINE):
        return (
            "The magazine is written in dwarvish. "
            'The only thing you can make out is "STRSTRSTR".'
        )
    if obj_n == TABLET and _is_here(state, TABLET):
        return '"CONGRATULATIONS ON BRINGING LIGHT INTO THE DARK-ROOM!"'
    if obj_n == OYSTER and _is_here(state, OYSTER):
        return "It says the same thing it did before."

    return "I see nothing to read here."


def _cmd_break(world: World, state: GameState, noun: str | None) -> str:
    """Handle BREAK command."""
    obj_n = _resolve_noun(world, state, noun)
    if obj_n == VASE and _is_here(state, VASE):
        state.object_props[VASE] = 2
        state.object_locations[VASE] = state.current_room
        return "You have taken the vase and hurled it delicately to the ground."
    return "It is beyond your power to do that."


def _cmd_find(world: World, state: GameState, noun: str | None) -> str:
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
    word = noun.lower()[:5]
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


def calculate_score(world: World, state: GameState) -> int:
    """Calculate the current score."""
    score = 0

    # Points for treasures stored safely in building (room 3)
    for obj_id, obj in world.objects.items():
        if obj.is_treasure and state.object_locations.get(obj_id) == 3:
            score += 12
        elif obj.is_treasure and _is_carrying(state, obj_id):
            score += 2

    # Points for survival and exploration
    score += max(0, state.deaths * -10)

    # Points for visiting rooms beyond the hall of mists
    deep_rooms = sum(1 for r in state.visited_rooms if r >= 15)
    score += min(deep_rooms, 25)

    # Getting into cave
    if state.current_room >= 15 or any(
        r >= 15 for r in state.visited_rooms
    ):
        score += 25

    # Bonus for not quitting
    if not state.gave_up:
        score += 4

    return score


def _static_response(msg: str):
    """Return a handler that ignores all arguments and returns a fixed message."""
    def handler(world: World, state: GameState, noun: str | None = None) -> str:
        return msg
    return handler


_VERB_DISPATCH: dict[str, callable] = {
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
    "wave": _cmd_wave,
    "feed": _cmd_feed,
    "say": _cmd_say,
    "brief": _cmd_brief,
    "swim": _static_response("I don't know how."),
    "nothi": _static_response("OK."),
    "save": _static_response(
        "Your game is automatically saved after each move."
    ),
}
