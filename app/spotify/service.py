"""Application-specific Spotify behavior and response normalization."""

from __future__ import annotations

import re
from typing import Any, Callable

from .client import SpotifyApiClient, malformed_response
from .errors import AppError, SpotifyError
from .oauth import SpotifyOAuthClient
from .tokens import MemoryTokenStore, TokenRecord

SPOTIFY_ID_PATTERN = re.compile(r"^[A-Za-z0-9]{1,128}$")
DEVICE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
SEARCH_QUERY_MAX_LENGTH = 100


class SpotifyService:
    """Coordinate token refresh, validation, and Spotify payload normalization."""

    def __init__(
        self,
        *,
        oauth_client: SpotifyOAuthClient,
        api_client: SpotifyApiClient,
        token_store: MemoryTokenStore,
    ) -> None:
        self.oauth_client = oauth_client
        self.api_client = api_client
        self.token_store = token_store

    def current_record(self, session_id: str | None) -> TokenRecord:
        return self.token_store.valid_record(
            session_id, self.oauth_client.refresh_token
        )

    def current_user(self, access_token: str) -> dict[str, str]:
        payload = self.api_client.current_user(access_token)
        user_id = _required_text(payload.get("id"))
        if not user_id:
            raise malformed_response()
        return {
            "id": user_id,
            "display_name": _text(payload.get("display_name")) or "Spotify listener",
        }

    def list_playlists(
        self, session_id: str | None, *, offset: int, limit: int
    ) -> dict[str, Any]:
        return self._with_record(
            session_id,
            lambda record: self._normalize_playlists(
                self.api_client.playlists(
                    record.access_token, offset=offset, limit=limit
                ),
                user_id=record.spotify_user_id,
                offset=offset,
                limit=limit,
            ),
        )

    def list_tracks(
        self,
        session_id: str | None,
        *,
        playlist_id: str,
        offset: int,
        limit: int,
    ) -> dict[str, Any]:
        validate_spotify_id(playlist_id, "playlist_id")

        def fetch(record: TokenRecord) -> dict[str, Any]:
            playlist_payload = self.api_client.playlist(
                record.access_token, playlist_id
            )
            owner = playlist_payload.get("owner")
            owner_id = _text(owner.get("id")) if isinstance(owner, dict) else None
            collaborative = playlist_payload.get("collaborative") is True
            if owner_id != record.spotify_user_id and not collaborative:
                raise AppError(
                    "playlist_unavailable",
                    "This playlist is not owned by you or collaborative in Spotify development mode.",
                    403,
                    False,
                )
            items_payload = self.api_client.playlist_items(
                record.access_token,
                playlist_id,
                offset=offset,
                limit=limit,
            )
            return {
                "playlist": {
                    "id": playlist_id,
                    "uri": _text(playlist_payload.get("uri"))
                    or f"spotify:playlist:{playlist_id}",
                    "name": _text(playlist_payload.get("name")) or "Untitled playlist",
                },
                "items": normalize_track_items(items_payload.get("items")),
                "pagination": normalize_pagination(
                    items_payload, offset=offset, limit=limit
                ),
            }

        return self._with_record(session_id, fetch)

    def list_saved_tracks(
        self, session_id: str | None, *, offset: int, limit: int
    ) -> dict[str, Any]:
        def fetch(record: TokenRecord) -> dict[str, Any]:
            payload = self.api_client.saved_tracks(
                record.access_token, offset=offset, limit=limit
            )
            return {
                "items": normalize_track_items(payload.get("items")),
                "pagination": normalize_pagination(
                    payload, offset=offset, limit=limit
                ),
            }

        return self._with_record(session_id, fetch)

    def search_tracks(
        self,
        session_id: str | None,
        *,
        query: object,
        offset: int,
        limit: int,
    ) -> dict[str, Any]:
        valid_query = validate_search_query(query)

        def fetch(record: TokenRecord) -> dict[str, Any]:
            payload = self.api_client.search_tracks(
                record.access_token,
                query=valid_query,
                offset=offset,
                limit=limit,
            )
            tracks = payload.get("tracks")
            if not isinstance(tracks, dict):
                raise malformed_response()
            return {
                "query": valid_query,
                "items": normalize_track_items(tracks.get("items")),
                "pagination": normalize_pagination(
                    tracks, offset=offset, limit=limit
                ),
            }

        return self._with_record(session_id, fetch)

    def start_playback(
        self,
        session_id: str | None,
        *,
        device_id: object,
        context_uri: object,
        track_uri: object,
    ) -> None:
        valid_device_id = validate_device_id(device_id)
        valid_context_uri = (
            None
            if context_uri is None
            else validate_uri(context_uri, "playlist", "context_uri")
        )
        valid_track_uri = validate_uri(track_uri, "track", "track_uri")

        def start(record: TokenRecord) -> None:
            self.api_client.start_playback(
                record.access_token,
                device_id=valid_device_id,
                context_uri=valid_context_uri,
                track_uri=valid_track_uri,
            )

        self._with_record(session_id, start)

    def _with_record(
        self, session_id: str | None, operation: Callable[[TokenRecord], Any]
    ) -> Any:
        record = self.current_record(session_id)
        try:
            return operation(record)
        except SpotifyError as error:
            if error.status_code == 401 or error.code == "authorization_expired":
                self.token_store.delete(session_id)
                raise AppError(
                    "authentication_required",
                    "Your Spotify session expired. Please sign in again.",
                    401,
                    True,
                ) from error
            raise

    @staticmethod
    def _normalize_playlists(
        payload: dict[str, Any],
        *,
        user_id: str | None,
        offset: int,
        limit: int,
    ) -> dict[str, Any]:
        raw_items = payload.get("items")
        if not isinstance(raw_items, list):
            raise malformed_response()
        items: list[dict[str, Any]] = []
        for raw in raw_items:
            if not isinstance(raw, dict):
                continue
            playlist_id = _text(raw.get("id"))
            if not playlist_id:
                continue
            owner = raw.get("owner")
            owner_id = _text(owner.get("id")) if isinstance(owner, dict) else None
            eligible = owner_id == user_id or raw.get("collaborative") is True
            items.append(
                {
                    "id": playlist_id,
                    "uri": _text(raw.get("uri"))
                    or f"spotify:playlist:{playlist_id}",
                    "name": _text(raw.get("name")) or "Untitled playlist",
                    "image_url": first_image_url(raw.get("images")),
                    "spotify_url": external_spotify_url(raw.get("external_urls")),
                    "eligible": eligible,
                    "unavailable_reason": None
                    if eligible
                    else "Only playlists you own or collaborate on are available in development mode.",
                }
            )
        return {
            "items": items,
            "pagination": normalize_pagination(payload, offset=offset, limit=limit),
        }


def normalize_track_items(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise malformed_response()
    normalized: list[dict[str, Any]] = []
    for entry in value:
        if not isinstance(entry, dict):
            continue
        track = entry.get("item")
        if not isinstance(track, dict):
            track = entry.get("track")
        if not isinstance(track, dict) and entry.get("type") == "track":
            track = entry
        if not isinstance(track, dict) or track.get("type", "track") != "track":
            continue
        if track.get("is_local") is True:
            continue
        artists_value = track.get("artists")
        artists: list[dict[str, str | None]] = []
        if isinstance(artists_value, list):
            for artist in artists_value:
                if not isinstance(artist, dict):
                    continue
                name = _text(artist.get("name"))
                if name:
                    artists.append(
                        {
                            "name": name,
                            "spotify_url": external_spotify_url(
                                artist.get("external_urls")
                            ),
                        }
                    )
        album_value = track.get("album")
        album = album_value if isinstance(album_value, dict) else {}
        uri = _text(track.get("uri"))
        restrictions = track.get("restrictions")
        restricted = isinstance(restrictions, dict) and bool(restrictions.get("reason"))
        available = bool(uri) and track.get("is_playable") is not False and not restricted
        duration = track.get("duration_ms")
        normalized.append(
            {
                "id": _text(track.get("id")),
                "uri": uri,
                "name": _text(track.get("name")) or "Unavailable track",
                "artists": artists,
                "album": {
                    "name": _text(album.get("name")) or "Unknown album",
                    "image_url": first_image_url(album.get("images")),
                    "spotify_url": external_spotify_url(album.get("external_urls")),
                },
                "duration_ms": duration
                if isinstance(duration, int) and not isinstance(duration, bool) and duration >= 0
                else 0,
                "available": available,
                "spotify_url": external_spotify_url(track.get("external_urls")),
            }
        )
    return normalized


def normalize_pagination(
    payload: dict[str, Any], *, offset: int, limit: int
) -> dict[str, int | None]:
    total = payload.get("total")
    if isinstance(total, bool) or not isinstance(total, int) or total < 0:
        total = 0
    raw_items = payload.get("items")
    count = len(raw_items) if isinstance(raw_items, list) else 0
    next_offset = offset + count if payload.get("next") and count else None
    return {
        "offset": offset,
        "limit": limit,
        "total": total,
        "next_offset": next_offset,
    }


def validate_spotify_id(value: object, field: str) -> str:
    if not isinstance(value, str) or not SPOTIFY_ID_PATTERN.fullmatch(value):
        raise invalid_request(f"{field} is invalid.")
    return value


def validate_device_id(value: object) -> str:
    if not isinstance(value, str) or not DEVICE_ID_PATTERN.fullmatch(value):
        raise invalid_request("device_id is invalid.")
    return value


def validate_search_query(value: object) -> str:
    if not isinstance(value, str):
        raise invalid_request("q is required.")
    query = " ".join(value.split())
    if not query:
        raise invalid_request("q must not be blank.")
    if len(query) > SEARCH_QUERY_MAX_LENGTH:
        raise invalid_request(
            f"q must be {SEARCH_QUERY_MAX_LENGTH} characters or fewer."
        )
    return query


def validate_uri(value: object, kind: str, field: str) -> str:
    if not isinstance(value, str):
        raise invalid_request(f"{field} is invalid.")
    prefix = f"spotify:{kind}:"
    if not value.startswith(prefix):
        raise invalid_request(f"{field} is invalid.")
    validate_spotify_id(value.removeprefix(prefix), field)
    return value


def invalid_request(message: str) -> AppError:
    return AppError("invalid_request", message, 400, False)


def first_image_url(value: object) -> str | None:
    if not isinstance(value, list):
        return None
    for image in value:
        if isinstance(image, dict):
            url = _text(image.get("url"))
            if url and url.startswith("https://"):
                return url
    return None


def external_spotify_url(value: object) -> str | None:
    if not isinstance(value, dict):
        return None
    url = _text(value.get("spotify"))
    return url if url and url.startswith("https://open.spotify.com/") else None


def _text(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _required_text(value: object) -> str | None:
    return _text(value)
