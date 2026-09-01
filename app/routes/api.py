"""Same-origin JSON API for the browser application."""

from __future__ import annotations

from flask import Blueprint, current_app, request, session

from app.routes.auth import validate_csrf
from app.spotify.errors import AppError
from app.spotify.service import SpotifyService, invalid_request
from app.spotify.tokens import MemoryTokenStore

api_blueprint = Blueprint("api", __name__, url_prefix="/api")


@api_blueprint.get("/session")
def session_status():
    configured = bool(current_app.config.get("SECRET_KEY")) and bool(
        getattr(current_app.extensions["oauth_client"], "configured", False)
    )
    record = _token_store().get(session.get("session_id"))
    if record is None:
        return {"authenticated": False, "configured": configured}
    csrf_token = session.get("csrf_token")
    if not isinstance(csrf_token, str):
        session.clear()
        return {"authenticated": False, "configured": configured}
    return {
        "authenticated": True,
        "configured": configured,
        "csrf_token": csrf_token,
    }


@api_blueprint.get("/player-token")
def player_token():
    record = _service().current_record(session.get("session_id"))
    return {"access_token": record.access_token, "expires_at": record.expires_at}


@api_blueprint.get("/playlists")
def playlists():
    offset, limit = parse_pagination(default_limit=20, maximum_limit=50)
    return _service().list_playlists(
        session.get("session_id"), offset=offset, limit=limit
    )


@api_blueprint.get("/playlists/<playlist_id>/tracks")
def playlist_tracks(playlist_id: str):
    offset, limit = parse_pagination(default_limit=50, maximum_limit=50)
    return _service().list_tracks(
        session.get("session_id"),
        playlist_id=playlist_id,
        offset=offset,
        limit=limit,
    )


@api_blueprint.get("/library/tracks")
def saved_tracks():
    offset, limit = parse_pagination(default_limit=50, maximum_limit=50)
    return _service().list_saved_tracks(
        session.get("session_id"), offset=offset, limit=limit
    )


@api_blueprint.get("/search/tracks")
def search_tracks():
    offset, limit = parse_pagination(
        default_limit=10,
        maximum_limit=10,
        maximum_offset=1000,
    )
    return _service().search_tracks(
        session.get("session_id"),
        query=request.args.get("q"),
        offset=offset,
        limit=limit,
    )


@api_blueprint.put("/playback/start")
def start_playback():
    validate_csrf()
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise invalid_request("A JSON request body is required.")
    _service().start_playback(
        session.get("session_id"),
        device_id=payload.get("device_id"),
        context_uri=payload.get("context_uri"),
        track_uri=payload.get("track_uri"),
    )
    return "", 204


def parse_pagination(
    *,
    default_limit: int,
    maximum_limit: int,
    maximum_offset: int | None = None,
) -> tuple[int, int]:
    offset_text = request.args.get("offset", "0")
    limit_text = request.args.get("limit", str(default_limit))
    try:
        offset = int(offset_text)
        limit = int(limit_text)
    except (TypeError, ValueError) as error:
        raise invalid_request("offset and limit must be integers.") from error
    if offset < 0:
        raise invalid_request("offset must be zero or greater.")
    if maximum_offset is not None and offset > maximum_offset:
        raise invalid_request(f"offset must be {maximum_offset} or less.")
    if limit < 1 or limit > maximum_limit:
        raise invalid_request(f"limit must be between 1 and {maximum_limit}.")
    return offset, limit


def _service() -> SpotifyService:
    return current_app.extensions["spotify_service"]


def _token_store() -> MemoryTokenStore:
    return current_app.extensions["token_store"]
