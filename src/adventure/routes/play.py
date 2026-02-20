"""Gameplay routes."""

from sqlmodel import Session
from xitzin import Redirect, Request, Xitzin
from xitzin.auth import get_identity, require_certificate

from ..session import AdventureSession
from ..users import get_or_create_player


def register_routes(app: Xitzin) -> None:
    """Register gameplay routes."""

    def get_game(request: Request) -> tuple[AdventureSession, Session]:
        """Load the player's game session."""
        identity = get_identity(request)
        db_session = Session(request.app.state.engine)
        player = get_or_create_player(db_session, identity.fingerprint)
        world = request.app.state.world
        game = AdventureSession.load_or_create(db_session, player, world)
        return game, db_session

    def render_play(game: AdventureSession, message: str = ""):
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

    @app.gemini("/play", name="play")
    @require_certificate
    def play(request: Request):
        """Main game view."""
        game, db_session = get_game(request)
        try:
            game.save()
            return render_play(game)
        finally:
            db_session.close()

    @app.gemini("/go/{direction}", name="go")
    @require_certificate
    def go(request: Request, direction: str):
        """Movement via clickable link."""
        game, db_session = get_game(request)
        try:
            if game.state.is_finished:
                return render_play(game, message="The game is over.")

            message = game.process_command(direction)
            game.save()
            return render_play(game, message=message)
        finally:
            db_session.close()

    @app.input("/cmd", prompt="What do you want to do?", name="cmd")
    @require_certificate
    def cmd(request: Request, query: str):
        """Freeform command entry."""
        game, db_session = get_game(request)
        try:
            if game.state.is_finished:
                return render_play(game, message="The game is over.")

            message = game.process_command(query)
            game.save()
            return render_play(game, message=message)
        finally:
            db_session.close()

    @app.gemini("/inventory", name="inventory")
    @require_certificate
    def inventory(request: Request):
        """Show carried items."""
        game, db_session = get_game(request)
        try:
            items = game.get_inventory()
            if not items:
                message = "You're not carrying anything."
            else:
                message = "You are currently holding:\n" + "\n".join(
                    f"  {item}" for item in items
                )
            return render_play(game, message=message)
        finally:
            db_session.close()

    @app.gemini("/score", name="score")
    @require_certificate
    def score(request: Request):
        """Show score."""
        game, db_session = get_game(request)
        try:
            from ..engine.commands import calculate_score

            s = calculate_score(game.world, game.state)
            message = f"Your current score is {s} out of a possible 350."
            return render_play(game, message=message)
        finally:
            db_session.close()

    @app.gemini("/look", name="look")
    @require_certificate
    def look(request: Request):
        """Look around."""
        game, db_session = get_game(request)
        try:
            message = game.process_command("look")
            game.save()
            return render_play(game, message=message)
        finally:
            db_session.close()

    @app.input(
        "/new",
        prompt="Are you sure you want to start over? Type YES to confirm:",
        name="new_game",
    )
    @require_certificate
    def new_game(request: Request, query: str):
        """Reset game with confirmation."""
        game, db_session = get_game(request)
        try:
            if query.strip().upper() == "YES":
                game.reset()
                game.save()
                return render_play(game, message="A new adventure begins!")
            return Redirect("/play")
        finally:
            db_session.close()
