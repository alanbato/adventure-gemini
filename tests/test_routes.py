"""Integration tests for routes."""


def test_home_page(client):
    """Home page is accessible without certificate."""
    response = client.get("/")
    assert response.is_success
    assert "Adventure" in response.body


def test_play_requires_cert(client):
    """Play page requires a client certificate."""
    response = client.get("/play")
    assert response.is_certificate_required


def test_play_with_cert(auth_client):
    """Play page works with a certificate."""
    response = auth_client.get("/play")
    assert response.is_success
    assert "ROAD" in response.body.upper() or "BUILDING" in response.body.upper()


def test_go_direction(auth_client):
    """Going a direction via /go/ route works."""
    response = auth_client.get("/go/south")
    assert response.is_success


def test_cmd_input_prompt(auth_client):
    """The /cmd route prompts for input when no query."""
    response = auth_client.get("/cmd")
    assert response.is_input_required


def test_cmd_with_input(auth_client):
    """The /cmd route processes commands."""
    response = auth_client.get_input("/cmd", "look")
    assert response.is_success
    assert len(response.body) > 0


def test_inventory_route(auth_client):
    """The /inventory route shows inventory."""
    response = auth_client.get("/inventory")
    assert response.is_success
    assert "carrying" in response.body.lower() or "holding" in response.body.lower()


def test_score_route(auth_client):
    """The /score route shows score."""
    response = auth_client.get("/score")
    assert response.is_success
    assert "score" in response.body.lower()


def test_help_page(client):
    """Help page is accessible."""
    response = client.get("/help")
    assert response.is_success
    assert "command" in response.body.lower() or "play" in response.body.lower()


def test_about_page(client):
    """About page is accessible."""
    response = client.get("/about")
    assert response.is_success
    assert "Crowther" in response.body or "Adventure" in response.body


def test_new_game_prompt(auth_client):
    """The /new route prompts for confirmation."""
    response = auth_client.get("/new")
    assert response.is_input_required


def test_look_route(auth_client):
    """The /look route works."""
    response = auth_client.get("/look")
    assert response.is_success
