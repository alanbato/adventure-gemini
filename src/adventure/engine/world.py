"""Immutable data structures for the Adventure game world.

These are loaded once from advent.dat at startup and shared across all players.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Move:
    """A travel table entry: verbs + condition → destination."""

    verbs: tuple[int, ...]
    condition: tuple
    destination: int
    is_forced: bool = False


@dataclass
class Room:
    """A location in the game world."""

    number: int
    long_description: str = ""
    short_description: str = ""
    travel_table: list[Move] = field(default_factory=list)
    is_light: bool = False
    liquid: int | None = None
    is_forbidden_to_pirate: bool = False
    hint_number: int | None = None


@dataclass
class Obj:
    """An object in the game world."""

    number: int
    names: list[str] = field(default_factory=list)
    inventory_message: str = ""
    messages: dict[int, str] = field(default_factory=dict)
    initial_rooms: list[int] = field(default_factory=list)
    is_treasure: bool = False
    is_fixed: bool = False


@dataclass(frozen=True)
class Word:
    """A vocabulary word."""

    text: str
    kind: str  # "motion", "noun", "verb", "special"
    number: int


@dataclass
class Hint:
    """A hint offered when the player lingers in an area."""

    number: int
    turns_needed: int = 0
    penalty: int = 0
    question: str = ""
    answer: str = ""
    rooms: list[int] = field(default_factory=list)


@dataclass
class World:
    """The complete immutable game world, loaded from advent.dat."""

    rooms: dict[int, Room] = field(default_factory=dict)
    objects: dict[int, Obj] = field(default_factory=dict)
    vocabulary: dict[str, Word] = field(default_factory=dict)
    messages: dict[int, str] = field(default_factory=dict)
    class_messages: list[tuple[int, str]] = field(default_factory=list)
    hints: dict[int, Hint] = field(default_factory=dict)
    magic_messages: dict[int, str] = field(default_factory=dict)
    object_names: dict[str, int] = field(default_factory=dict)
