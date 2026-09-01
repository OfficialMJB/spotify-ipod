"""Low-level, testable Spotify Web API adapter."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from .errors import SpotifyError


class SpotifyApiClient:
    """Make authenticated requests to the narrow API surface used by the MVP."""

    def __init__(self, *, api_base_url: str, http_client: httpx.Client) -> None:
        self.api_base_url = api_base_url.rstrip("/")
        self._http_client = http_client

    def current_user(self, access_token: str) -> dict[str, Any]:
        return self._json_request("GET", "/me", access_token)

    def playlists(
        self, access_token: str, *, offset: int, limit: int
    ) -> dict[str, Any]:
        return self._json_request(
            "GET",
            "/me/playlists",
            access_token,
            params={"offset": offset, "limit": limit},
        )

    def playlist(self, access_token: str, playlist_id: str) -> dict[str, Any]:
        return self._json_request("GET", f"/playlists/{playlist_id}", access_token)

    def playlist_items(
        self, access_token: str, playlist_id: str, *, offset: int, limit: int
    ) -> dict[str, Any]:
        return self._json_request(
            "GET",
            f"/playlists/{playlist_id}/items",
            access_token,
            params={"offset": offset, "limit": limit},
        )

    def saved_tracks(
        self, access_token: str, *, offset: int, limit: int
    ) -> dict[str, Any]:
        return self._json_request(
            "GET",
            "/me/tracks",
            access_token,
            params={"offset": offset, "limit": limit},
        )

    def search_tracks(
        self,
        access_token: str,
        *,
        query: str,
        offset: int,
        limit: int,
    ) -> dict[str, Any]:
        return self._json_request(
            "GET",
            "/search",
            access_token,
            params={
                "q": query,
                "type": "track",
                "offset": offset,
                "limit": limit,
            },
        )

    def start_playback(
        self,
        access_token: str,
        *,
        device_id: str,
        context_uri: str | None,
        track_uri: str,
    ) -> None:
        if context_uri is None:
            playback_body: dict[str, Any] = {
                "uris": [track_uri],
                "position_ms": 0,
            }
        else:
            playback_body = {
                "context_uri": context_uri,
                "offset": {"uri": track_uri},
                "position_ms": 0,
            }
        self._request(
            "PUT",
            "/me/player/play",
            access_token,
            params={"device_id": device_id},
            json=playback_body,
        )

    def _json_request(
        self,
        method: str,
        path: str,
        access_token: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        response = self._request(method, path, access_token, **kwargs)
        try:
            payload = response.json()
        except ValueError as error:
            raise malformed_response() from error
        if not isinstance(payload, dict):
            raise malformed_response()
        return payload

    def _request(
        self,
        method: str,
        path: str,
        access_token: str,
        **kwargs: Any,
    ) -> httpx.Response:
        headers = dict(kwargs.pop("headers", {}))
        headers.update(
            {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
        )
        try:
            response = self._http_client.request(
                method,
                f"{self.api_base_url}{path}",
                headers=headers,
                **kwargs,
            )
        except httpx.TimeoutException as error:
            raise SpotifyError(
                "spotify_unavailable",
                "Spotify did not respond in time. Please try again.",
                503,
                True,
            ) from error
        except httpx.HTTPError as error:
            raise SpotifyError(
                "spotify_unavailable",
                "Spotify is temporarily unavailable. Please try again.",
                503,
                True,
            ) from error

        if response.status_code >= 400:
            raise response_error(response)
        return response


def response_error(response: httpx.Response) -> SpotifyError:
    status = response.status_code
    if status == 401:
        return SpotifyError(
            "authorization_expired",
            "Your Spotify authorization expired. Please sign in again.",
            401,
            True,
        )
    if status == 403:
        return SpotifyError(
            "spotify_forbidden",
            "Spotify cannot provide this content or playback action for this account.",
            403,
            False,
        )
    if status == 429:
        return SpotifyError(
            "rate_limited",
            "Spotify asked the player to wait before retrying.",
            429,
            True,
            _retry_after(response.headers),
        )
    if status >= 500:
        return SpotifyError(
            "spotify_unavailable",
            "Spotify is temporarily unavailable. Please try again.",
            503,
            True,
        )
    return SpotifyError(
        "spotify_request_failed",
        "Spotify could not complete that request.",
        502,
        True,
    )


def malformed_response() -> SpotifyError:
    return SpotifyError(
        "spotify_bad_response",
        "Spotify returned an invalid response.",
        502,
        True,
    )


def _retry_after(headers: Mapping[str, str]) -> int | None:
    value = headers.get("Retry-After")
    try:
        parsed = int(value) if value is not None else None
    except ValueError:
        return None
    return parsed if parsed is not None and parsed >= 0 else None
