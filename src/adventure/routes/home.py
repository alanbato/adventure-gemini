"""Home, help, and about routes."""

from xitzin import Redirect, Request, Xitzin
from xitzin.auth import require_certificate


def register_routes(app: Xitzin) -> None:
    """Register home routes."""

    @app.gemini("/", name="home")
    def home(request: Request):
        if request.query == "register":
            # Activate the client certificate at root scope, then redirect.
            return _activate_cert(request)
        return app.template("home.gmi")

    @require_certificate
    def _activate_cert(request: Request):
        return Redirect("/play")

    @app.gemini("/help", name="help")
    def help_page(request: Request):
        return app.template("help.gmi")

    @app.gemini("/about", name="about")
    def about(request: Request):
        return app.template("about.gmi")
