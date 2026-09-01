"""Flask application factory for Spotify Pocket Player."""

from __future__ import annotations

from typing import Any

from flask import Flask, jsonify, request
import httpx
from werkzeug.exceptions import HTTPException

from .config import load_config
from .routes import api_blueprint, auth_blueprint, pages_blueprint
from .spotify import (
    AppError,
    MemoryTokenStore,
    SpotifyApiClient,
    SpotifyOAuthClient,
    SpotifyService,
)


def create_app(
    test_config: dict[str, Any] | None = None,
    *,
    oauth_client: SpotifyOAuthClient | None = None,
    spotify_client: SpotifyApiClient | None = None,
    token_store: MemoryTokenStore | None = None,
) -> Flask:
    """Create the application with injectable Spotify boundaries for tests."""

    app = Flask(__name__)
    app.config.from_mapping(load_config())
    if test_config:
        app.config.from_mapping(test_config)

    timeout = httpx.Timeout(app.config["SPOTIFY_HTTP_TIMEOUT"])
    if oauth_client is None:
        oauth_http = httpx.Client(timeout=timeout)
        oauth_client = SpotifyOAuthClient(
            client_id=app.config.get("SPOTIFY_CLIENT_ID"),
            client_secret=app.config.get("SPOTIFY_CLIENT_SECRET"),
            redirect_uri=app.config["SPOTIFY_REDIRECT_URI"],
            scopes=tuple(app.config["SPOTIFY_SCOPES"]),
            accounts_base_url=app.config["SPOTIFY_ACCOUNTS_BASE_URL"],
            http_client=oauth_http,
        )
    if spotify_client is None:
        api_http = httpx.Client(timeout=timeout)
        spotify_client = SpotifyApiClient(
            api_base_url=app.config["SPOTIFY_API_BASE_URL"],
            http_client=api_http,
        )
    token_store = token_store or MemoryTokenStore(
        refresh_skew_seconds=app.config["TOKEN_REFRESH_SKEW_SECONDS"]
    )
    app.extensions["oauth_client"] = oauth_client
    app.extensions["spotify_client"] = spotify_client
    app.extensions["token_store"] = token_store
    app.extensions["spotify_service"] = SpotifyService(
        oauth_client=oauth_client,
        api_client=spotify_client,
        token_store=token_store,
    )

    app.register_blueprint(pages_blueprint)
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(api_blueprint)

    @app.errorhandler(AppError)
    def handle_app_error(error: AppError):
        return jsonify(error.to_dict()), error.status_code

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        if not request.path.startswith("/api/"):
            return error
        public_error = AppError(
            "invalid_request" if error.code in {400, 405} else "not_found",
            "That API request is not available.",
            error.code or 500,
            False,
        )
        return jsonify(public_error.to_dict()), public_error.status_code

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Content-Security-Policy",
            "; ".join(
                (
                    "default-src 'self'",
                    "script-src 'self' https://sdk.scdn.co",
                    "connect-src 'self' https://*.spotify.com wss://*.spotify.com",
                    "img-src 'self' data: https:",
                    "style-src 'self'",
                    "font-src 'self'",
                    "media-src https: blob:",
                    "frame-src https://sdk.scdn.co",
                    "frame-ancestors 'none'",
                    "base-uri 'self'",
                    "form-action 'self' https://accounts.spotify.com",
                )
            ),
        )
        if request.path.startswith(("/api/", "/auth/")):
            response.headers["Cache-Control"] = "no-store"
        return response

    return app


__all__ = ["create_app"]
