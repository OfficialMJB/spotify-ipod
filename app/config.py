"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from typing import Any

DISPLAY_NAME = "Spotify Pocket Player"
SPOTIFY_ACCOUNTS_BASE_URL = "https://accounts.spotify.com"
SPOTIFY_API_BASE_URL = "https://api.spotify.com/v1"
SPOTIFY_SCOPES = (
    "streaming",
    "playlist-read-private",
    "playlist-read-collaborative",
    "user-read-email",
    "user-read-private",
    "user-modify-playback-state",
)
HTTP_TIMEOUT_SECONDS = 10.0
TOKEN_REFRESH_SKEW_SECONDS = 60


def load_config() -> dict[str, Any]:
    """Return the default Flask configuration without contacting Spotify."""

    environment = os.getenv("FLASK_ENV", "development").lower()
    return {
        "SECRET_KEY": os.getenv("FLASK_SECRET_KEY"),
        "SPOTIFY_CLIENT_ID": os.getenv("SPOTIFY_CLIENT_ID"),
        "SPOTIFY_CLIENT_SECRET": os.getenv("SPOTIFY_CLIENT_SECRET"),
        "SPOTIFY_REDIRECT_URI": os.getenv(
            "SPOTIFY_REDIRECT_URI", "http://127.0.0.1:5050/auth/callback"
        ),
        "SPOTIFY_ACCOUNTS_BASE_URL": SPOTIFY_ACCOUNTS_BASE_URL,
        "SPOTIFY_API_BASE_URL": SPOTIFY_API_BASE_URL,
        "SPOTIFY_SCOPES": SPOTIFY_SCOPES,
        "SPOTIFY_HTTP_TIMEOUT": HTTP_TIMEOUT_SECONDS,
        "TOKEN_REFRESH_SKEW_SECONDS": TOKEN_REFRESH_SKEW_SECONDS,
        "DISPLAY_NAME": DISPLAY_NAME,
        "SESSION_COOKIE_NAME": "pocket_player_session",
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_SECURE": environment not in {"development", "testing"},
    }
