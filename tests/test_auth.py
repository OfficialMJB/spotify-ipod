from urllib.parse import parse_qs, urlparse

from app import create_app


def test_login_redirects_with_unpredictable_state(client):
    response = client.get("/auth/login")

    assert response.status_code == 302
    parsed = urlparse(response.location)
    state = parse_qs(parsed.query)["state"][0]
    assert parsed.netloc == "accounts.spotify.test"
    assert len(state) >= 32
    with client.session_transaction() as browser_session:
        assert browser_session["oauth_state"] == state


def test_callback_rejects_mismatched_state(client, fake_oauth):
    with client.session_transaction() as browser_session:
        browser_session["oauth_state"] = "expected"

    response = client.get("/auth/callback?code=code123&state=wrong")

    assert response.status_code == 302
    assert response.location.endswith("/?auth_error=invalid_state")
    assert fake_oauth.exchange_calls == []
    with client.session_transaction() as browser_session:
        assert "oauth_state" not in browser_session


def test_denied_callback_is_safe_and_does_not_exchange_code(client, fake_oauth):
    with client.session_transaction() as browser_session:
        browser_session["oauth_state"] = "expected"

    response = client.get("/auth/callback?error=access_denied&state=expected")

    assert response.location.endswith("/?auth_error=access_denied")
    assert fake_oauth.exchange_calls == []


def test_callback_preserves_invalid_scope_error(client, fake_oauth):
    with client.session_transaction() as browser_session:
        browser_session["oauth_state"] = "expected"

    response = client.get("/auth/callback?error=invalid_scope&state=expected")

    assert response.location.endswith("/?auth_error=invalid_scope")
    assert fake_oauth.exchange_calls == []


def test_callback_maps_spotify_server_error_to_retryable_message(
    client, fake_oauth
):
    with client.session_transaction() as browser_session:
        browser_session["oauth_state"] = "expected"

    response = client.get("/auth/callback?error=server_error&state=expected")

    assert response.location.endswith(
        "/?auth_error=spotify_temporarily_unavailable"
    )
    assert fake_oauth.exchange_calls == []


def test_callback_does_not_expose_unknown_spotify_error(client, fake_oauth):
    with client.session_transaction() as browser_session:
        browser_session["oauth_state"] = "expected"

    response = client.get("/auth/callback?error=unexpected&state=expected")

    assert response.location.endswith("/?auth_error=authorization_failed")
    assert fake_oauth.exchange_calls == []


def test_successful_callback_creates_opaque_session(
    client, fake_oauth, token_store
):
    with client.session_transaction() as browser_session:
        browser_session["oauth_state"] = "expected"

    response = client.get("/auth/callback?code=code123&state=expected")

    assert response.status_code == 302
    assert response.location == "/"
    assert fake_oauth.exchange_calls == ["code123"]
    with client.session_transaction() as browser_session:
        assert "oauth_state" not in browser_session
        assert browser_session["csrf_token"]
        record = token_store.get(browser_session["session_id"])
    assert record is not None
    assert record.access_token == "access-from-exchange"
    assert record.spotify_user_id == "user123"
    assert "access-from-exchange" not in response.headers.get("Set-Cookie", "")
    assert "refresh-from-exchange" not in response.headers.get("Set-Cookie", "")


def test_oauth_state_is_single_use(client, fake_oauth):
    with client.session_transaction() as browser_session:
        browser_session["oauth_state"] = "expected"

    first = client.get("/auth/callback?code=first&state=expected")
    second = client.get("/auth/callback?code=second&state=expected")

    assert first.location == "/"
    assert second.location.endswith("/?auth_error=invalid_state")
    assert fake_oauth.exchange_calls == ["first"]


def test_logout_requires_csrf(authenticated_client):
    response = authenticated_client.post("/auth/logout")

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "csrf_failed"


def test_logout_deletes_server_session(authenticated_client, token_store):
    with authenticated_client.session_transaction() as browser_session:
        session_id = browser_session["session_id"]

    response = authenticated_client.post(
        "/auth/logout", headers={"X-CSRF-Token": "csrf-value"}
    )

    assert response.status_code == 204
    assert token_store.get(session_id) is None
    assert authenticated_client.get("/api/session").get_json() == {
        "authenticated": False,
        "configured": True,
    }


def test_login_reports_missing_flask_secret(fake_oauth, fake_spotify, token_store):
    app = create_app(
        {"TESTING": True, "SECRET_KEY": None},
        oauth_client=fake_oauth,
        spotify_client=fake_spotify,
        token_store=token_store,
    )

    response = app.test_client().get("/auth/login")

    assert response.status_code == 503
    assert response.get_json()["error"]["code"] == "application_not_configured"
    assert app.test_client().get("/api/session").get_json() == {
        "authenticated": False,
        "configured": False,
    }


def test_login_reports_missing_spotify_configuration_without_network_calls():
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-only-secret",
            "SPOTIFY_CLIENT_ID": None,
            "SPOTIFY_CLIENT_SECRET": None,
        }
    )

    response = app.test_client().get("/auth/login")

    assert response.status_code == 503
    assert response.get_json()["error"]["code"] == "spotify_not_configured"
    assert app.test_client().get("/api/session").get_json() == {
        "authenticated": False,
        "configured": False,
    }
