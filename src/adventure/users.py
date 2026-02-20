"""User management utilities."""

import datetime as dt

from sqlmodel import Session, select

from .logging import get_logger
from .models import Player

logger = get_logger(__name__)


def get_or_create_player(session: Session, fingerprint: str) -> Player:
    """Get existing player or create new one from certificate fingerprint."""
    statement = select(Player).where(Player.fingerprint == fingerprint)
    player = session.exec(statement).first()

    if player:
        player.last_seen = dt.datetime.now(dt.UTC)
        logger.debug("player_accessed", fingerprint=fingerprint)
    else:
        player = Player(fingerprint=fingerprint)
        session.add(player)
        logger.info("player_created", fingerprint=fingerprint)

    session.commit()
    session.refresh(player)
    return player
