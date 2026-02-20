"""Gameplay routes."""

from contextlib import contextmanager

from sqlmodel import Session
from xitzin import Redirect, Request, Xitzin
from xitzin.auth import get_identity, require_certificate

from ..session import AdventureSession
from ..users import get_or_create_player


@contextmanager
def _game_session(request: Request):
    """Load the player's game session with auto-close."""
    identity = get_identity(request)
    db_session = Session(request.app.state.engine)
    try:
        player = get_or_create_player(
            db_session, identity.fingerprint,
        )
        world = request.app.state.world
        yield AdventureSession.load_or_create(
            db_session, player, world,
        )
    finally:
        db_session.close()


def _render_play(app: Xitzin, game: AdventureSession, message: str = ""):
    """Render the main play view."""
    return app.template(
        "play.gmi",
        description=game.get_room_description(),
        objects=game.get_visible_objects(),
        exits=game.get_exits(),
        message=message,
        turns=game.state.turns,
        is_finished=game.state.is_finished,
    )


def _register_action_routes(app: Xitzin) -> None:
    """Register command and movement routes."""

    @app.gemini("/play", name="play")
    @require_certificate
    def play(request: Request):
        """Main game view."""
        with _game_session(request) as game:
            game.save()
            return _render_play(app, game)

    @app.gemini("/go/{direction}", name="go")
    @require_certificate
    def go(request: Request, direction: str):
        """Movement via clickable link."""
        with _game_session(request) as game:
            if game.state.is_finished:
                return _render_play(app, game, message="The game is over.")
            message = game.process_command(direction)
            game.save()
            return _render_play(app, game, message=message)

    @app.input("/cmd", prompt="What do you want to do?", name="cmd")
    @require_certificate
    def cmd(request: Request, query: str):
        """Freeform command entry."""
        with _game_session(request) as game:
            if game.state.is_finished:
                return _render_play(app, game, message="The game is over.")
            message = game.process_command(query)
            game.save()
            return _render_play(app, game, message=message)

    @app.gemini("/look", name="look")
    @require_certificate
    def look(request: Request):
        """Look around."""
        with _game_session(request) as game:
            message = game.process_command("look")
            game.save()
            return _render_play(app, game, message=message)


def _register_info_routes(app: Xitzin) -> None:
    """Register inventory, score, and game management routes."""

    @app.gemini("/inventory", name="inventory")
    @require_certificate
    def inventory(request: Request):
        """Show carried items."""
        with _game_session(request) as game:
            items = game.get_inventory()
            if not items:
                message = "You're not carrying anything."
            else:
                message = "You are currently holding:\n" + "\n".join(
                    f"  {item}" for item in items
                )
            return _render_play(app, game, message=message)

    @app.gemini("/score", name="score")
    @require_certificate
    def score(request: Request):
        """Show score."""
        with _game_session(request) as game:
            from ..engine.commands import calculate_score

            s = calculate_score(game.world, game.state)
            msg = f"Your current score is {s} out of a possible 350."
            return _render_play(app, game, message=msg)

    @app.input(
        "/new",
        prompt="Are you sure you want to start over? Type YES to confirm:",
        name="new_game",
    )
    @require_certificate
    def new_game(request: Request, query: str):
        """Reset game with confirmation."""
        with _game_session(request) as game:
            if query.strip().upper() == "YES":
                game.reset()
                game.save()
                return _render_play(
                    app, game, message="A new adventure begins!",
                )
            return Redirect("/play")


def register_routes(app: Xitzin) -> None:
    """Register gameplay routes."""
    _register_action_routes(app)
    _register_info_routes(app)
