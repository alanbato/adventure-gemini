"""Database models for Adventure."""

import datetime as dt

from sqlmodel import Field, SQLModel


class Player(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    fingerprint: str = Field(unique=True, index=True)
    created_at: dt.datetime = Field(
        default_factory=lambda: dt.datetime.now(dt.UTC)
    )
    last_seen: dt.datetime = Field(
        default_factory=lambda: dt.datetime.now(dt.UTC)
    )


class SavedGame(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    player_id: int = Field(foreign_key="player.id", unique=True, index=True)
    state_blob: bytes  # zlib-compressed pickle of GameState
    turns: int = 0
    score: int = 0
    is_finished: bool = False
    started_at: dt.datetime = Field(
        default_factory=lambda: dt.datetime.now(dt.UTC)
    )
    last_played: dt.datetime = Field(
        default_factory=lambda: dt.datetime.now(dt.UTC)
    )
