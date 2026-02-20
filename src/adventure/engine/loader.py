"""Parse the original advent.dat data file into a World object.

The file has 12 sections separated by -1 lines. A final 0 ends the file.
Section format reference: Brandon Rhodes' python-adventure data.py.
"""

from collections.abc import Callable
from pathlib import Path

from .world import Hint, Move, Obj, Room, Word, World

LONG_WORDS = {
    w[:5]: w
    for w in """upstream downstream forest forward continue onward return
    retreat valley staircase outside building stream cobble inward inside
    surface nowhere passage tunnel canyon awkward upward ascend downward
    descend outdoors barren across debris broken examine describe slabroom
    depression entrance secret bedquilt plover oriental cavern reservoir
    office headlamp lantern pillow velvet fissure tablet oyster magazine
    spelunker dwarves knives rations bottle mirror beanstalk stalactite
    shadow figure drawings pirate dragon message volcano geyser machine
    vending batteries carpet nuggets diamonds silver jewelry treasure
    trident shards pottery emerald platinum pyramid pearl persian spices
    capture release discard mumble unlock nothing extinguish placate travel
    proceed continue explore follow attack strike devour inventory detonate
    ignite blowup peruse shatter disturb suspend sesame opensesame
    abracadabra shazam excavate information""".split()
}

WORD_KINDS = ["motion", "noun", "verb", "special"]


def _expand_tabs(segments: list[str]) -> str:
    """Expand tabs like the original FORTRAN."""
    it = iter(segments)
    line = next(it)
    for segment in it:
        spaces = 8 - len(line) % 8
        line += " " * spaces + segment
    return line


def _ensure_room(rooms: dict[int, Room], n: int) -> Room:
    if n not in rooms:
        rooms[n] = Room(number=n)
    return rooms[n]


def _ensure_obj(objects: dict[int, Obj], n: int) -> Obj:
    if n not in objects:
        objects[n] = Obj(number=n)
    return objects[n]


def _ensure_hint(hints: dict[int, Hint], n: int) -> Hint:
    if n not in hints:
        hints[n] = Hint(number=n)
    return hints[n]


def _parse_section1(world: World, fields: list) -> None:
    """Long descriptions for rooms."""
    n = fields[0]
    room = _ensure_room(world.rooms, n)
    text = _expand_tabs(fields[1:])
    if not text.startswith(">$<"):
        if room.long_description:
            room.long_description += "\n"
        room.long_description += text


def _parse_section2(world: World, fields: list) -> None:
    """Short descriptions for rooms."""
    n = fields[0]
    room = _ensure_room(world.rooms, n)
    if room.short_description:
        room.short_description += "\n"
    room.short_description += fields[1]


def _parse_section3(world: World, fields: list, last_travel: list) -> None:
    """Travel table entries.

    Format: room_number destination verb1 verb2 ...
    destination encodes both condition and target via integer arithmetic.
    """
    x = fields[0]
    y = fields[1]
    verbs = tuple(fields[2:])

    if last_travel[0] == x and last_travel[1][0] == verbs[0]:
        verbs = last_travel[1]
    else:
        last_travel[0] = x
        last_travel[1] = verbs

    m, n = divmod(y, 1000)
    mh, mm = divmod(m, 100)

    match m:
        case 0:
            condition = (None,)
        case _ if 0 < m < 100:
            condition = ("%", m)
        case 100:
            condition = ("not_dwarf",)
        case _ if 100 < m <= 200:
            condition = ("carrying", mm)
        case _ if 200 < m <= 300:
            condition = ("carrying_or_in_room_with", mm)
        case _:
            condition = ("prop!=", mm, mh - 3)

    is_forced = len(verbs) == 1 and verbs[0] == 1

    _ensure_room(world.rooms, x)

    move = Move(
        verbs=verbs,
        condition=condition,
        destination=n if n <= 500 else -(n - 500),
        is_forced=is_forced,
    )
    world.rooms[x].travel_table.append(move)


def _parse_section4(world: World, fields: list) -> None:
    """Vocabulary words."""
    n = fields[0]
    text = str(fields[1]).lower()
    text = LONG_WORDS.get(text, text)

    kind = WORD_KINDS[n // 1000]
    word = Word(text=text, kind=kind, number=n)
    world.vocabulary[text] = word

    if kind == "noun":
        obj_n = n % 1000
        obj = _ensure_obj(world.objects, obj_n)
        if text not in obj.names:
            obj.names.append(text)
        obj.is_treasure = obj_n >= 50
        world.object_names[text] = obj_n
        truncated = text[:5]
        if truncated not in world.object_names:
            world.object_names[truncated] = obj_n


def _parse_section5(world: World, fields: list, current_obj: list) -> None:
    """Object descriptions (inventory messages and state messages)."""
    n = fields[0]
    text = _expand_tabs([str(f) for f in fields[1:]])

    if 1 <= n <= 99:
        obj = _ensure_obj(world.objects, n)
        obj.inventory_message = text
        current_obj[0] = n
    else:
        obj_n = current_obj[0]
        obj = _ensure_obj(world.objects, obj_n)
        state = n // 100
        if text.startswith(">$<"):
            text = ""
        if state in obj.messages:
            obj.messages[state] += "\n" + text
        else:
            obj.messages[state] = text


def _parse_section6(world: World, fields: list) -> None:
    """Arbitrary messages."""
    n = fields[0]
    text = _expand_tabs([str(f) for f in fields[1:]])
    if n in world.messages:
        world.messages[n] += "\n" + text
    else:
        world.messages[n] = text


def _parse_section7(world: World, fields: list) -> None:
    """Object locations."""
    n = fields[0]
    room_n = fields[1]
    obj = _ensure_obj(world.objects, n)

    if room_n:
        obj.initial_rooms.append(room_n)
        _ensure_room(world.rooms, room_n)

    if len(fields) > 2:
        fixed = fields[2]
        if fixed == -1:
            obj.is_fixed = True
        elif fixed > 0:
            obj.initial_rooms.append(fixed)
            _ensure_room(world.rooms, fixed)


def _parse_section8(world: World, fields: list) -> None:
    """Action verb default messages.

    Maps verb words to default messages when no object matches.
    """
    # We don't need this for our simplified engine


_BIT_FLAG_SETTERS: dict[int, Callable] = {
    0: lambda room: setattr(room, "is_light", True),
    1: lambda room: setattr(room, "liquid", 22),  # water object number
    2: lambda room: setattr(room, "liquid", 21),  # oil object number
    3: lambda room: setattr(room, "is_forbidden_to_pirate", True),
}


def _parse_section9(world: World, fields: list) -> None:
    """Room flags (light, liquid, pirate, hints)."""
    bit = fields[0]
    room_numbers = fields[1:]
    setter = _BIT_FLAG_SETTERS.get(bit)
    for room_n in room_numbers:
        room = _ensure_room(world.rooms, room_n)
        if setter:
            setter(room)
        else:
            hint = _ensure_hint(world.hints, bit)
            if room_n not in hint.rooms:
                hint.rooms.append(room_n)
            room.hint_number = bit


def _parse_section10(world: World, fields: list) -> None:
    """Class messages (score thresholds)."""
    score = fields[0]
    text = str(fields[1])
    world.class_messages.append((score, text))


def _parse_section11(world: World, fields: list) -> None:
    """Hint definitions."""
    n = fields[0]
    hint = _ensure_hint(world.hints, n)
    hint.turns_needed = fields[1]
    hint.penalty = fields[2]
    question_n = fields[3]
    answer_n = fields[4]
    hint.question = world.messages.get(question_n, "")
    hint.answer = world.messages.get(answer_n, "")


def _parse_section12(world: World, fields: list) -> None:
    """Magic messages."""
    n = fields[0]
    text = str(fields[1])
    if n in world.magic_messages:
        world.magic_messages[n] += "\n" + text
    else:
        world.magic_messages[n] = text


def _parse_fields(line: str) -> list:
    """Parse a tab-delimited line into typed fields (int or str)."""
    fields = []
    for field in line.split("\t"):
        stripped = field.strip()
        if stripped.lstrip("-").isdigit():
            fields.append(int(stripped))
        else:
            fields.append(field)
    return fields


def _read_section(f, parser) -> None:
    """Read lines until sentinel (-1) and dispatch each to parser."""
    while True:
        line = f.readline().rstrip("\n")
        fields = _parse_fields(line)
        if fields[0] == -1:
            break
        parser(fields)


def load_world(data_path: Path) -> World:
    """Parse advent.dat and return a populated World."""
    world = World()
    last_travel: list = [0, (0,)]
    current_obj: list = [0]

    section_parsers = {
        1: lambda f: _parse_section1(world, f),
        2: lambda f: _parse_section2(world, f),
        3: lambda f: _parse_section3(world, f, last_travel),
        4: lambda f: _parse_section4(world, f),
        5: lambda f: _parse_section5(world, f, current_obj),
        6: lambda f: _parse_section6(world, f),
        7: lambda f: _parse_section7(world, f),
        8: lambda f: _parse_section8(world, f),
        9: lambda f: _parse_section9(world, f),
        10: lambda f: _parse_section10(world, f),
        11: lambda f: _parse_section11(world, f),
        12: lambda f: _parse_section12(world, f),
    }

    with open(data_path) as fh:
        while True:
            line = fh.readline()
            if not line:
                break
            section_number = int(line.strip())
            if section_number == 0:
                break

            parser = section_parsers.get(section_number)
            if parser is None:
                continue

            _read_section(fh, parser)

    return world
