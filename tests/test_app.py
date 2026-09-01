def test_health_is_available_without_credentials(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_page_uses_the_central_display_name(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"<title>Spotify Pocket Player</title>" in response.data
    assert b'data-app-name="Spotify Pocket Player"' in response.data


def test_oauth_scopes_cover_library_sdk_and_playback(app):
    assert app.config["SPOTIFY_SCOPES"] == (
        "streaming",
        "playlist-read-private",
        "playlist-read-collaborative",
        "user-read-email",
        "user-read-private",
        "user-modify-playback-state",
    )


def test_security_headers_are_added(client):
    response = client.get("/health")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert "https://sdk.scdn.co" in response.headers["Content-Security-Policy"]


def test_sensitive_endpoints_are_not_cached(client):
    response = client.get("/api/session")

    assert response.headers["Cache-Control"] == "no-store"


def test_unknown_api_route_uses_safe_error_envelope(client):
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    assert response.get_json() == {
        "error": {
            "code": "not_found",
            "message": "That API request is not available.",
            "recoverable": False,
        }
    }
