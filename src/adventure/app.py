"""Xitzin application factory for Adventure."""

from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine
from xitzin import Xitzin

from .config import Config
from .engine.loader import load_world
from .logging import get_logger

logger = get_logger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "data"


def create_app(config: Config | None = None) -> Xitzin:
    """Create and configure the Xitzin application."""
    config = config or Config.from_env()

    templates_dir = Path(__file__).parent / "templates"

    app = Xitzin(
        title="Colossal Cave Adventure",
        version="0.1.0",
        templates_dir=templates_dir,
    )

    engine = create_engine(config.database_url)
    app.state.engine = engine
    app.state.config = config

    @app.on_startup
    async def startup():
        """Initialize database and load game world."""
        SQLModel.metadata.create_all(engine)
        logger.debug("database_setup_complete")

        data_path = DATA_DIR / "advent.dat"
        app.state.world = load_world(data_path)
        logger.info(
            "world_loaded",
            rooms=len(app.state.world.rooms),
            objects=len(
                {k: v for k, v in app.state.world.objects.items() if isinstance(k, int)}
            ),
            vocabulary=len(app.state.world.vocabulary),
        )
        logger.info("startup_complete")

    from .routes import home, play

    home.register_routes(app)
    play.register_routes(app)

    return app


def get_session(app: Xitzin) -> Session:
    """Get a database session from the app."""
    return Session(app.state.engine)
