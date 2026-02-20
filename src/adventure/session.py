"""Session layer bridging the game engine and database."""

import datetime as dt
import pickle
import zlib

from sqlmodel import Session, select

from .engine.commands import (
    calculate_score,
    get_exits,
    get_inventory,
    get_room_description,
    get_visible_objects,
    handle_command,
)
from .engine.state import GameState, new_game_state
from .engine.world import World
from .logging import get_logger
from .models import Player, SavedGame

logger = get_logger(__name__)


class AdventureSession:
    """Wraps a Player + SavedGame + in-memory GameState."""

    def __init__(
        self,
        db_session: Session,
        player: Player,
        saved_game: SavedGame | None,
        game_state: GameState,
        world: World,
    ):
        self.db_session = db_session
        self.player = player
        self.saved_game = saved_game
        self.state = game_state
        self.world = world

    @classmethod
    def load_or_create(
        cls,
        db_session: Session,
        player: Player,
        world: World,
    ) -> "AdventureSession":
        """Load existing save or create a fresh game."""
        statement = select(SavedGame).where(SavedGame.player_id == player.id)
        saved_game = db_session.exec(statement).first()

        if saved_game and not saved_game.is_finished:
            game_state = pickle.loads(zlib.decompress(saved_game.state_blob))
            logger.debug(
                "game_loaded",
                fingerprint=player.fingerprint,
                turns=saved_game.turns,
            )
        else:
            game_state = new_game_state(world)
            saved_game = None
            logger.info("new_game_started", fingerprint=player.fingerprint)

        return cls(db_session, player, saved_game, game_state, world)

    def process_command(self, raw_input: str) -> str:
        """Delegate to the engine and return response text."""
        return handle_command(self.world, self.state, raw_input)

    def save(self) -> None:
        """Serialize state back to the database."""
        now = dt.datetime.now(dt.UTC)
        blob = zlib.compress(pickle.dumps(self.state))
        score = calculate_score(self.world, self.state)

        if self.saved_game is None:
            self.saved_game = SavedGame(
                player_id=self.player.id,
                state_blob=blob,
                turns=self.state.turns,
                score=score,
                is_finished=self.state.is_finished,
                started_at=now,
                last_played=now,
            )
            self.db_session.add(self.saved_game)
        else:
            self.saved_game.state_blob = blob
            self.saved_game.turns = self.state.turns
            self.saved_game.score = score
            self.saved_game.is_finished = self.state.is_finished
            self.saved_game.last_played = now

        self.db_session.commit()
        logger.debug(
            "game_saved",
            fingerprint=self.player.fingerprint,
            turns=self.state.turns,
            score=score,
        )

    def get_room_description(self) -> str:
        return get_room_description(self.world, self.state)

    def get_exits(self) -> list[str]:
        return get_exits(self.world, self.state)

    def get_visible_objects(self) -> list[str]:
        return get_visible_objects(self.world, self.state)

    def get_inventory(self) -> list[str]:
        return get_inventory(self.world, self.state)

    def reset(self) -> None:
        """Reset to a fresh game."""
        self.state = new_game_state(self.world)
        if self.saved_game:
            self.db_session.delete(self.saved_game)
            self.db_session.commit()
            self.saved_game = None
        logger.info("game_reset", fingerprint=self.player.fingerprint)
