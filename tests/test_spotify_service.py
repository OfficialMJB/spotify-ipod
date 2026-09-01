import time

import pytest

from app.spotify.errors import AppError
from app.spotify.service import normalize_track_items, validate_search_query
from app.spotify.tokens import TokenRecord


def test_track_normalization_handles_null_local_and_missing_fields():
    result = normalize_track_items(
        [
            {"item": None},
            {"item": {"type": "episode", "name": "Podcast"}},
            {"item": {"type": "track", "is_local": True, "name": "Local"}},
            {
                "item": {
                    "type": "track",
                    "id": None,
                    "name": None,
                    "uri": None,
                    "artists": None,
                    "album": None,
                    "duration_ms": None,
                }
            },
        ]
    )

    assert len(result) == 1
    assert result[0]["name"] == "Unavailable track"
    assert result[0]["available"] is False
    assert result[0]["artists"] == []
    assert result[0]["album"]["image_url"] is None


def test_track_normalization_accepts_saved_and_search_shapes():
    track = {
        "type": "track",
        "id": "track123",
        "uri": "spotify:track:track123",
        "name": "Track name",
        "artists": [],
        "album": {},
    }

    result = normalize_track_items([
        {"added_at": "2026-09-01T00:00:00Z", "track": track},
        track,
    ])

    assert [item["id"] for item in result] == ["track123", "track123"]


@pytest.mark.parametrize("query", [None, "", "   ", "x" * 101])
def test_search_query_validation_rejects_invalid_values(query):
    with pytest.raises(AppError) as raised:
        validate_search_query(query)

    assert raised.value.code == "invalid_request"


def test_search_query_validation_normalizes_whitespace():
    assert validate_search_query("  Miles   Davis  ") == "Miles Davis"


def test_invalid_playlist_id_does_not_reach_spotify(
    authenticated_client, fake_spotify
):
    response = authenticated_client.get("/api/playlists/not%20valid/tracks")

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_request"


def test_collaborative_playlist_is_eligible(authenticated_client, fake_spotify):
    fake_spotify.playlist_payload["owner"] = {"id": "someone-else"}
    fake_spotify.playlist_payload["collaborative"] = True

    response = authenticated_client.get("/api/playlists/collab123/tracks")

    assert response.status_code == 200


def test_refresh_failure_clears_server_record(
    client, token_store, fake_oauth
):
    from app.spotify.errors import SpotifyError

    expired = TokenRecord(
        access_token="expired",
        refresh_token="expired-refresh",
        expires_at=int(time.time()) - 1,
        scopes=frozenset(),
        spotify_user_id="user123",
    )
    session_id = token_store.create(expired)

    def fail_refresh(refresh_token: str):
        raise SpotifyError(
            "authorization_expired", "Authorization expired.", 401, True
        )

    fake_oauth.refresh_token = fail_refresh
    with client.session_transaction() as browser_session:
        browser_session["session_id"] = session_id
        browser_session["csrf_token"] = "csrf"

    response = client.get("/api/player-token")

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "authentication_required"
    assert token_store.get(session_id) is None
