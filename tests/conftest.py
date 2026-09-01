from __future__ import annotations

import time
from typing import Any

import pytest

from app import create_app
from app.spotify.tokens import MemoryTokenStore, TokenRecord


class FakeOAuthClient:
    configured = True

    def __init__(self) -> None:
        self.exchange_calls: list[str] = []
        self.refresh_calls: list[str] = []
        self.exchange_payload: dict[str, object] = {
            "access_token": "access-from-exchange",
            "refresh_token": "refresh-from-exchange",
            "expires_in": 3600,
            "scope": "streaming playlist-read-private",
        }
        self.refresh_payload: dict[str, object] = {
            "access_token": "refreshed-access",
            "expires_in": 3600,
        }

    def authorization_url(self, state: str) -> str:
        return f"https://accounts.spotify.test/authorize?state={state}"

    def exchange_code(self, code: str) -> dict[str, object]:
        self.exchange_calls.append(code)
        return self.exchange_payload

    def refresh_token(self, refresh_token: str) -> dict[str, object]:
        self.refresh_calls.append(refresh_token)
        return self.refresh_payload


class FakeSpotifyApiClient:
    def __init__(self) -> None:
        self.playback_calls: list[dict[str, str]] = []
        self.user_payload: dict[str, Any] = {
            "id": "user123",
            "display_name": "Test Listener",
        }
        self.playlists_payload: dict[str, Any] = {
            "items": [
                {
                    "id": "owned123",
                    "uri": "spotify:playlist:owned123",
                    "name": "Owned playlist",
                    "collaborative": False,
                    "owner": {"id": "user123"},
                    "images": [{"url": "https://images.test/playlist.jpg"}],
                    "external_urls": {
                        "spotify": "https://open.spotify.com/playlist/owned123"
                    },
                },
                {
                    "id": "followed123",
                    "name": "Followed playlist",
                    "collaborative": False,
                    "owner": {"id": "another-user"},
                },
            ],
            "offset": 0,
            "limit": 20,
            "total": 2,
            "next": None,
        }
        self.playlist_payload: dict[str, Any] = {
            "id": "owned123",
            "uri": "spotify:playlist:owned123",
            "name": "Owned playlist",
            "collaborative": False,
            "owner": {"id": "user123"},
        }
        self.items_payload: dict[str, Any] = {
            "items": [
                {
                    "item": {
                        "id": "track123",
                        "uri": "spotify:track:track123",
                        "type": "track",
                        "name": "Track name",
                        "duration_ms": 180000,
                        "is_local": False,
                        "is_playable": True,
                        "artists": [
                            {
                                "name": "Artist name",
                                "external_urls": {
                                    "spotify": "https://open.spotify.com/artist/artist123"
                                },
                            }
                        ],
                        "album": {
                            "name": "Album name",
                            "images": [{"url": "https://images.test/album.jpg"}],
                            "external_urls": {
                                "spotify": "https://open.spotify.com/album/album123"
                            },
                        },
                        "external_urls": {
                            "spotify": "https://open.spotify.com/track/track123"
                        },
                    }
                }
            ],
            "offset": 0,
            "limit": 50,
            "total": 1,
            "next": None,
        }

    def current_user(self, access_token: str) -> dict[str, Any]:
        return self.user_payload

    def playlists(
        self, access_token: str, *, offset: int, limit: int
    ) -> dict[str, Any]:
        return self.playlists_payload

    def playlist(self, access_token: str, playlist_id: str) -> dict[str, Any]:
        return self.playlist_payload

    def playlist_items(
        self, access_token: str, playlist_id: str, *, offset: int, limit: int
    ) -> dict[str, Any]:
        return self.items_payload

    def start_playback(
        self,
        access_token: str,
        *,
        device_id: str,
        context_uri: str,
        track_uri: str,
    ) -> None:
        self.playback_calls.append(
            {
                "access_token": access_token,
                "device_id": device_id,
                "context_uri": context_uri,
                "track_uri": track_uri,
            }
        )


@pytest.fixture
def fake_oauth() -> FakeOAuthClient:
    return FakeOAuthClient()


@pytest.fixture
def fake_spotify() -> FakeSpotifyApiClient:
    return FakeSpotifyApiClient()


@pytest.fixture
def token_store() -> MemoryTokenStore:
    return MemoryTokenStore(refresh_skew_seconds=60)


@pytest.fixture
def app(fake_oauth, fake_spotify, token_store):
    return create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-only-secret",
            "SESSION_COOKIE_SECURE": False,
        },
        oauth_client=fake_oauth,
        spotify_client=fake_spotify,
        token_store=token_store,
    )


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def authenticated_client(client, token_store):
    record = TokenRecord(
        access_token="server-only-access",
        refresh_token="server-only-refresh",
        expires_at=int(time.time()) + 3600,
        scopes=frozenset({"streaming"}),
        spotify_user_id="user123",
    )
    session_id = token_store.create(record)
    with client.session_transaction() as browser_session:
        browser_session["session_id"] = session_id
        browser_session["csrf_token"] = "csrf-value"
    return client
