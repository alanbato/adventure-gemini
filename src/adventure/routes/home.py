"""Home, help, and about routes."""

from xitzin import Request, Xitzin


def register_routes(app: Xitzin) -> None:
    """Register home routes."""

    @app.gemini("/", name="home")
    def home(request: Request):
        return app.template("home.gmi")

    @app.gemini("/help", name="help")
    def help_page(request: Request):
        return app.template("help.gmi")

    @app.gemini("/about", name="about")
    def about(request: Request):
        return app.template("about.gmi")
