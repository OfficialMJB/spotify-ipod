import httpx
import pytest

from app.spotify.client import SpotifyApiClient
from app.spotify.errors import SpotifyError
from app.spotify.oauth import SpotifyOAuthClient


def test_oauth_authorization_url_has_exact_required_parameters():
    oauth = SpotifyOAuthClient(
        client_id="client-id",
        client_secret="client-secret",
        redirect_uri="http://127.0.0.1:5050/auth/callback",
        scopes=("streaming", "playlist-read-private"),
        accounts_base_url="https://accounts.spotify.com",
        http_client=httpx.Client(transport=httpx.MockTransport(lambda request: None)),
    )

    url = oauth.authorization_url("state-value")

    assert "response_type=code" in url
    assert "client_id=client-id" in url
    assert "redirect_uri=http%3A%2F%2F127.0.0.1%3A5050%2Fauth%2Fcallback" in url
    assert "scope=streaming+playlist-read-private" in url
    assert "state=state-value" in url


def test_oauth_exchange_uses_basic_auth_and_form_body():
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers["Authorization"]
        captured["body"] = request.content.decode()
        return httpx.Response(
            200,
            json={
                "access_token": "access",
                "refresh_token": "refresh",
                "expires_in": 3600,
            },
        )

    oauth = _oauth(handler)

    payload = oauth.exchange_code("code-value")

    assert payload["access_token"] == "access"
    assert str(captured["authorization"]).startswith("Basic ")
    assert "grant_type=authorization_code" in str(captured["body"])
    assert "code=code-value" in str(captured["body"])


def test_invalid_grant_becomes_safe_reauthorization_error():
    oauth = _oauth(
        lambda request: httpx.Response(400, json={"error": "invalid_grant"})
    )

    with pytest.raises(SpotifyError) as raised:
        oauth.refresh_token("secret-refresh")

    assert raised.value.code == "authorization_expired"
    assert "secret-refresh" not in raised.value.message


def test_api_client_uses_bearer_and_current_items_endpoint():
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers["Authorization"]
        return httpx.Response(200, json={"items": [], "total": 0})

    client = _api(handler)

    client.playlist_items("access-value", "playlist123", offset=2, limit=10)

    assert captured["url"].startswith(
        "https://api.spotify.com/v1/playlists/playlist123/items"
    )
    assert "offset=2" in captured["url"]
    assert captured["authorization"] == "Bearer access-value"


def test_api_client_builds_exact_playback_body():
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = request.content.decode()
        return httpx.Response(204)

    client = _api(handler)

    client.start_playback(
        "access",
        device_id="device123",
        context_uri="spotify:playlist:playlist123",
        track_uri="spotify:track:track123",
    )

    assert captured["url"].endswith("/me/player/play?device_id=device123")
    assert captured["body"] == (
        '{"context_uri":"spotify:playlist:playlist123",'
        '"offset":{"uri":"spotify:track:track123"},"position_ms":0}'
    )


def test_api_client_builds_direct_track_playback_body_without_context():
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.content.decode()
        return httpx.Response(204)

    _api(handler).start_playback(
        "access",
        device_id="device123",
        context_uri=None,
        track_uri="spotify:track:track123",
    )

    assert captured["body"] == (
        '{"uris":["spotify:track:track123"],"position_ms":0}'
    )


def test_api_client_uses_saved_tracks_and_track_search_endpoints():
    captured: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(str(request.url))
        payload = {"tracks": {"items": []}} if request.url.path.endswith("/search") else {"items": []}
        return httpx.Response(200, json=payload)

    client = _api(handler)
    client.saved_tracks("access", offset=50, limit=50)
    client.search_tracks("access", query="Miles Davis", offset=0, limit=10)

    assert captured[0].endswith("/me/tracks?offset=50&limit=50")
    assert "/search?" in captured[1]
    assert "q=Miles+Davis" in captured[1]
    assert "type=track" in captured[1]
    assert "limit=10" in captured[1]


def test_rate_limit_preserves_retry_after_without_retrying():
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(429, headers={"Retry-After": "8"})

    with pytest.raises(SpotifyError) as raised:
        _api(handler).current_user("access")

    assert calls == 1
    assert raised.value.code == "rate_limited"
    assert raised.value.retry_after == 8


def test_timeout_becomes_recoverable_service_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("late", request=request)

    with pytest.raises(SpotifyError) as raised:
        _api(handler).current_user("access")

    assert raised.value.status_code == 503
    assert raised.value.recoverable is True


def test_malformed_json_is_rejected():
    client = _api(
        lambda request: httpx.Response(
            200, content=b"not-json", headers={"Content-Type": "application/json"}
        )
    )

    with pytest.raises(SpotifyError) as raised:
        client.current_user("access")

    assert raised.value.code == "spotify_bad_response"


def _oauth(handler) -> SpotifyOAuthClient:
    return SpotifyOAuthClient(
        client_id="client-id",
        client_secret="client-secret",
        redirect_uri="http://127.0.0.1:5050/auth/callback",
        scopes=("streaming",),
        accounts_base_url="https://accounts.spotify.com",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def _api(handler) -> SpotifyApiClient:
    return SpotifyApiClient(
        api_base_url="https://api.spotify.com/v1",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
