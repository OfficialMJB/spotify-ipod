from app.spotify.tokens import MemoryTokenStore, TokenRecord


def test_unexpired_record_does_not_refresh():
    store = MemoryTokenStore(refresh_skew_seconds=60)
    record = _record(expires_at=500)
    session_id = store.create(record)
    calls: list[str] = []

    result = store.valid_record(
        session_id,
        lambda refresh_token: calls.append(refresh_token),
        now=lambda: 100,
    )

    assert result == record
    assert calls == []


def test_refresh_preserves_refresh_token_when_omitted():
    store = MemoryTokenStore(refresh_skew_seconds=60)
    session_id = store.create(_record(expires_at=120))

    result = store.valid_record(
        session_id,
        lambda refresh_token: {"access_token": "new-access", "expires_in": 300},
        now=lambda: 100,
    )

    assert result.access_token == "new-access"
    assert result.refresh_token == "old-refresh"
    assert result.expires_at == 400


def test_delete_unknown_session_is_safe():
    store = MemoryTokenStore()

    store.delete("does-not-exist")
    store.delete(None)

    assert store.get("does-not-exist") is None


def _record(*, expires_at: int) -> TokenRecord:
    return TokenRecord(
        access_token="old-access",
        refresh_token="old-refresh",
        expires_at=expires_at,
        scopes=frozenset({"streaming"}),
        spotify_user_id="user123",
    )
