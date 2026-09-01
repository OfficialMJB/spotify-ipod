"""In-process storage for Spotify tokens used by the local MVP."""

from __future__ import annotations

from dataclasses import dataclass, replace
import secrets
from threading import RLock
import time
from typing import Callable

from .errors import AppError, SpotifyError


@dataclass(frozen=True, slots=True)
class TokenRecord:
    """Spotify token data that must remain on the server."""

    access_token: str
    refresh_token: str
    expires_at: int
    scopes: frozenset[str]
    spotify_user_id: str | None = None


class MemoryTokenStore:
    """Thread-safe token storage for a single-process local application."""

    def __init__(self, *, refresh_skew_seconds: int = 60) -> None:
        self._records: dict[str, TokenRecord] = {}
        self._lock = RLock()
        self._refresh_skew_seconds = refresh_skew_seconds

    def create(self, record: TokenRecord) -> str:
        session_id = secrets.token_urlsafe(32)
        with self._lock:
            self._records[session_id] = record
        return session_id

    def get(self, session_id: str | None) -> TokenRecord | None:
        if not session_id:
            return None
        with self._lock:
            return self._records.get(session_id)

    def delete(self, session_id: str | None) -> None:
        if not session_id:
            return
        with self._lock:
            self._records.pop(session_id, None)

    def valid_record(
        self,
        session_id: str | None,
        refresh: Callable[[str], dict[str, object]],
        *,
        now: Callable[[], float] = time.time,
    ) -> TokenRecord:
        """Return a usable record, refreshing once under the store lock if needed."""

        if not session_id:
            raise authentication_required()

        with self._lock:
            record = self._records.get(session_id)
            if record is None:
                raise authentication_required()

            if record.expires_at > int(now()) + self._refresh_skew_seconds:
                return record

            try:
                payload = refresh(record.refresh_token)
                access_token = _required_string(payload, "access_token")
                expires_in = _positive_integer(payload, "expires_in")
                refresh_token = payload.get("refresh_token") or record.refresh_token
                if not isinstance(refresh_token, str):
                    raise SpotifyError(
                        "spotify_bad_response",
                        "Spotify returned an invalid token response.",
                        502,
                        True,
                    )
                scope_value = payload.get("scope")
                scopes = (
                    frozenset(scope_value.split())
                    if isinstance(scope_value, str)
                    else record.scopes
                )
                refreshed = replace(
                    record,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_at=int(now()) + expires_in,
                    scopes=scopes,
                )
            except SpotifyError as error:
                if error.status_code == 401 or error.code == "authorization_expired":
                    self._records.pop(session_id, None)
                    raise authentication_required() from error
                raise

            self._records[session_id] = refreshed
            return refreshed


def token_record_from_payload(
    payload: dict[str, object],
    *,
    spotify_user_id: str | None = None,
    now: Callable[[], float] = time.time,
) -> TokenRecord:
    """Validate a token response and convert it to server-side storage."""

    access_token = _required_string(payload, "access_token")
    refresh_token = _required_string(payload, "refresh_token")
    expires_in = _positive_integer(payload, "expires_in")
    scope = payload.get("scope", "")
    if not isinstance(scope, str):
        raise SpotifyError(
            "spotify_bad_response",
            "Spotify returned an invalid token response.",
            502,
            True,
        )
    return TokenRecord(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=int(now()) + expires_in,
        scopes=frozenset(scope.split()),
        spotify_user_id=spotify_user_id,
    )


def authentication_required() -> AppError:
    return AppError(
        "authentication_required",
        "Sign in with Spotify to continue.",
        401,
        True,
    )


def _required_string(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise SpotifyError(
            "spotify_bad_response",
            "Spotify returned an invalid token response.",
            502,
            True,
        )
    return value


def _positive_integer(payload: dict[str, object], key: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise SpotifyError(
            "spotify_bad_response",
            "Spotify returned an invalid token response.",
            502,
            True,
        )
    return value
