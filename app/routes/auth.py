"""OAuth sign-in, callback, and local sign-out routes."""

from __future__ import annotations

from dataclasses import replace
import secrets

from flask import Blueprint, current_app, redirect, request, session, url_for

from app.spotify.errors import AppError, SpotifyError
from app.spotify.service import SpotifyService
from app.spotify.tokens import MemoryTokenStore, token_record_from_payload

auth_blueprint = Blueprint("auth", __name__, url_prefix="/auth")

SPOTIFY_AUTH_ERROR_CODES = {
    "access_denied": "access_denied",
    "invalid_scope": "invalid_scope",
    "server_error": "spotify_temporarily_unavailable",
    "temporarily_unavailable": "spotify_temporarily_unavailable",
    "invalid_request": "authorization_request_invalid",
    "unauthorized_client": "authorization_request_invalid",
    "unsupported_response_type": "authorization_request_invalid",
}


@auth_blueprint.get("/login")
def login():
    if not current_app.config.get("SECRET_KEY"):
        raise AppError(
            "application_not_configured",
            "FLASK_SECRET_KEY is not configured. Add it to your local .env file.",
            503,
            False,
        )
    service = _service()
    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state
    return redirect(service.oauth_client.authorization_url(state), code=302)


@auth_blueprint.get("/callback")
def callback():
    expected_state = session.pop("oauth_state", None)
    returned_state = request.args.get("state")
    if (
        not expected_state
        or not returned_state
        or not secrets.compare_digest(expected_state, returned_state)
    ):
        return redirect(url_for("pages.index", auth_error="invalid_state"))

    spotify_error = request.args.get("error")
    if spotify_error:
        auth_error = SPOTIFY_AUTH_ERROR_CODES.get(
            spotify_error, "authorization_failed"
        )
        return redirect(url_for("pages.index", auth_error=auth_error))
    code = request.args.get("code")
    if not code:
        return redirect(url_for("pages.index", auth_error="missing_code"))

    service = _service()
    try:
        token_payload = service.oauth_client.exchange_code(code)
        record = token_record_from_payload(token_payload)
        user = service.current_user(record.access_token)
    except SpotifyError:
        return redirect(url_for("pages.index", auth_error="authorization_failed"))

    prior_session_id = session.get("session_id")
    _token_store().delete(prior_session_id)
    session.clear()
    record = replace(record, spotify_user_id=user["id"])
    session["session_id"] = _token_store().create(record)
    session["csrf_token"] = secrets.token_urlsafe(32)
    return redirect(url_for("pages.index"))


@auth_blueprint.post("/logout")
def logout():
    validate_csrf()
    _token_store().delete(session.get("session_id"))
    session.clear()
    return "", 204


def validate_csrf() -> None:
    expected = session.get("csrf_token")
    provided = request.headers.get("X-CSRF-Token")
    if (
        not isinstance(expected, str)
        or not provided
        or not secrets.compare_digest(expected, provided)
    ):
        raise AppError(
            "csrf_failed",
            "The request could not be verified. Refresh the page and try again.",
            400,
            True,
        )


def _service() -> SpotifyService:
    return current_app.extensions["spotify_service"]


def _token_store() -> MemoryTokenStore:
    return current_app.extensions["token_store"]
