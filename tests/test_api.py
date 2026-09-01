def test_anonymous_session_contract(client):
    assert client.get("/api/session").get_json() == {
        "authenticated": False,
        "configured": True,
    }


def test_authenticated_session_contract(authenticated_client):
    assert authenticated_client.get("/api/session").get_json() == {
        "authenticated": True,
        "configured": True,
        "csrf_token": "csrf-value",
    }


def test_player_token_is_short_lived_token_only(authenticated_client):
    response = authenticated_client.get("/api/player-token")

    assert response.status_code == 200
    assert response.get_json()["access_token"] == "server-only-access"
    assert "refresh" not in response.get_data(as_text=True)
    assert response.headers["Cache-Control"] == "no-store"


def test_playlists_include_eligibility(authenticated_client):
    response = authenticated_client.get("/api/playlists")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["items"][0]["eligible"] is True
    assert payload["items"][1]["eligible"] is False
    assert "development mode" in payload["items"][1]["unavailable_reason"]
    assert payload["pagination"] == {
        "offset": 0,
        "limit": 20,
        "total": 2,
        "next_offset": None,
    }


def test_tracks_use_current_items_item_shape(authenticated_client):
    response = authenticated_client.get(
        "/api/playlists/owned123/tracks?offset=0&limit=50"
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["playlist"]["name"] == "Owned playlist"
    assert payload["items"][0] == {
        "id": "track123",
        "uri": "spotify:track:track123",
        "name": "Track name",
        "artists": [
            {
                "name": "Artist name",
                "spotify_url": "https://open.spotify.com/artist/artist123",
            }
        ],
        "album": {
            "name": "Album name",
            "image_url": "https://images.test/album.jpg",
            "spotify_url": "https://open.spotify.com/album/album123",
        },
        "duration_ms": 180000,
        "available": True,
        "spotify_url": "https://open.spotify.com/track/track123",
    }


def test_ineligible_playlist_is_rejected(authenticated_client, fake_spotify):
    fake_spotify.playlist_payload["owner"] = {"id": "another-user"}

    response = authenticated_client.get("/api/playlists/followed123/tracks")

    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "playlist_unavailable"


def test_liked_songs_return_normalized_tracks_and_pagination(authenticated_client):
    response = authenticated_client.get("/api/library/tracks?offset=0&limit=50")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["items"][0]["id"] == "track123"
    assert payload["items"][0]["name"] == "Track name"
    assert payload["pagination"] == {
        "offset": 0,
        "limit": 50,
        "total": 1,
        "next_offset": None,
    }


def test_track_search_normalizes_query_and_limits_results(
    authenticated_client, fake_spotify
):
    response = authenticated_client.get(
        "/api/search/tracks?q=%20Miles%20%20Davis%20&limit=10"
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["query"] == "Miles Davis"
    assert payload["items"][0]["id"] == "track123"


def test_track_search_rejects_blank_query_and_excessive_pagination(
    authenticated_client
):
    blank = authenticated_client.get("/api/search/tracks?q=%20%20")
    excessive_limit = authenticated_client.get(
        "/api/search/tracks?q=test&limit=11"
    )
    excessive_offset = authenticated_client.get(
        "/api/search/tracks?q=test&offset=1001"
    )

    assert blank.status_code == 400
    assert excessive_limit.status_code == 400
    assert excessive_offset.status_code == 400


def test_pagination_validation_is_strict(authenticated_client):
    response = authenticated_client.get("/api/playlists?offset=-1&limit=500")

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_request"


def test_playback_start_requires_json_and_csrf(authenticated_client):
    no_csrf = authenticated_client.put("/api/playback/start", json={})
    no_json = authenticated_client.put(
        "/api/playback/start", headers={"X-CSRF-Token": "csrf-value"}
    )

    assert no_csrf.status_code == 400
    assert no_csrf.get_json()["error"]["code"] == "csrf_failed"
    assert no_json.status_code == 400
    assert no_json.get_json()["error"]["code"] == "invalid_request"


def test_playback_start_validates_and_forwards_only_expected_fields(
    authenticated_client, fake_spotify
):
    response = authenticated_client.put(
        "/api/playback/start",
        headers={"X-CSRF-Token": "csrf-value"},
        json={
            "device_id": "device_123",
            "context_uri": "spotify:playlist:owned123",
            "track_uri": "spotify:track:track123",
            "unexpected": "ignored",
        },
    )

    assert response.status_code == 204
    assert fake_spotify.playback_calls == [
        {
            "access_token": "server-only-access",
            "device_id": "device_123",
            "context_uri": "spotify:playlist:owned123",
            "track_uri": "spotify:track:track123",
        }
    ]


def test_playback_start_supports_direct_track_without_context(
    authenticated_client, fake_spotify
):
    response = authenticated_client.put(
        "/api/playback/start",
        headers={"X-CSRF-Token": "csrf-value"},
        json={
            "device_id": "device_123",
            "context_uri": None,
            "track_uri": "spotify:track:track123",
        },
    )

    assert response.status_code == 204
    assert fake_spotify.playback_calls == [
        {
            "access_token": "server-only-access",
            "device_id": "device_123",
            "context_uri": None,
            "track_uri": "spotify:track:track123",
        }
    ]


def test_playback_rejects_arbitrary_uri(authenticated_client, fake_spotify):
    response = authenticated_client.put(
        "/api/playback/start",
        headers={"X-CSRF-Token": "csrf-value"},
        json={
            "device_id": "device_123",
            "context_uri": "https://attacker.test/playlist",
            "track_uri": "spotify:track:track123",
        },
    )

    assert response.status_code == 400
    assert fake_spotify.playback_calls == []
