"""Shared test fixtures for Adventure."""

from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine

from adventure.app import _get_data_path, create_app
from adventure.config import Config
from adventure.engine.loader import load_world
from adventure.engine.world import World
from adventure.models import Player


@pytest.fixture
def world() -> World:
    return load_world(_get_data_path())


@pytest.fixture
def db_engine(tmp_path: Path):
    db_url = f"sqlite:///{tmp_path}/test.db"
    engine = create_engine(db_url)
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(db_engine):
    with Session(db_engine) as session:
        yield session


@pytest.fixture
def test_player(db_session: Session) -> Player:
    player = Player(fingerprint="test-fingerprint-abc123")
    db_session.add(player)
    db_session.commit()
    db_session.refresh(player)
    return player


@pytest.fixture
def test_config(tmp_path: Path) -> Config:
    return Config(database_url=f"sqlite:///{tmp_path}/test.db")


@pytest.fixture
def app(test_config: Config):
    return create_app(test_config)


@pytest.fixture
def client(app):
    from xitzin.testing import test_app

    with test_app(app) as client:
        yield client


@pytest.fixture
def auth_client(client):
    return client.with_certificate("test-fingerprint-abc123")
