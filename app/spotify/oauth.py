"""Spotify Authorization Code flow adapter."""

from __future__ import annotations

from urllib.parse import urlencode

import httpx

from .errors import SpotifyError


class SpotifyOAuthClient:
    """Perform OAuth URL construction and token requests."""

    def __init__(
        self,
        *,
        client_id: str | None,
        client_secret: str | None,
        redirect_uri: str,
        scopes: tuple[str, ...],
        accounts_base_url: str,
        http_client: httpx.Client,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scopes = scopes
        self.accounts_base_url = accounts_base_url.rstrip("/")
        self._http_client = http_client

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret and self.redirect_uri)

    def authorization_url(self, state: str) -> str:
        if not self.configured:
            raise configuration_error()
        query = urlencode(
            {
                "client_id": self.client_id,
                "response_type": "code",
                "redirect_uri": self.redirect_uri,
                "state": state,
                "scope": " ".join(self.scopes),
                "show_dialog": "false",
            }
        )
        return f"{self.accounts_base_url}/authorize?{query}"

    def exchange_code(self, code: str) -> dict[str, object]:
        return self._token_request(
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.redirect_uri,
            }
        )

    def refresh_token(self, refresh_token: str) -> dict[str, object]:
        return self._token_request(
            {"grant_type": "refresh_token", "refresh_token": refresh_token}
        )

    def _token_request(self, form: dict[str, str]) -> dict[str, object]:
        if not self.configured:
            raise configuration_error()
        try:
            response = self._http_client.post(
                f"{self.accounts_base_url}/api/token",
                data=form,
                auth=httpx.BasicAuth(self.client_id or "", self.client_secret or ""),
                headers={"Accept": "application/json"},
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
            oauth_error = _oauth_error_code(response)
            if oauth_error == "invalid_grant":
                raise SpotifyError(
                    "authorization_expired",
                    "Your Spotify authorization expired. Please sign in again.",
                    401,
                    True,
                )
            raise SpotifyError(
                "spotify_authorization_failed",
                "Spotify could not complete authorization. Please try again.",
                502,
                True,
            )
        try:
            payload = response.json()
        except ValueError as error:
            raise _bad_token_response() from error
        if not isinstance(payload, dict):
            raise _bad_token_response()
        return payload


def configuration_error() -> SpotifyError:
    return SpotifyError(
        "spotify_not_configured",
        "Spotify credentials are not configured. Add them to your local .env file.",
        503,
        False,
    )


def _oauth_error_code(response: httpx.Response) -> str | None:
    try:
        payload = response.json()
    except ValueError:
        return None
    value = payload.get("error") if isinstance(payload, dict) else None
    return value if isinstance(value, str) else None


def _bad_token_response() -> SpotifyError:
    return SpotifyError(
        "spotify_bad_response",
        "Spotify returned an invalid token response.",
        502,
        True,
    )
