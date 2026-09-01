# Liked Songs and Track Search

- **Status:** Implemented and manually verified
- **Branch:** `feature/liked-songs-search`
- **Date:** 2026-09-01

## Goal

Make the compact player convenient for everyday use by opening Library on the
user's Liked Songs and providing a focused Spotify track search without
recreating the full Spotify application.

## User stories

- As a listener, I want Library to show my recently liked songs first so I can
  play familiar music quickly.
- As a listener, I want to switch back to my eligible playlists without leaving
  the player.
- As a listener, I want to search Spotify for a track and start it from the
  result list.
- As a listener with more than 50 liked songs, I want to load another page
  without losing the songs already displayed.

## Interface scope

The Library panel will have three views:

1. **Liked Songs** — the default view, newest saved tracks first.
2. **Playlists** — the existing owned/collaborative playlist browser.
3. **Search** — an explicit text submission that returns track results.

Search will not run on every keystroke. The user submits a non-empty query,
which limits unnecessary requests and makes rate-limit behavior predictable.

## API boundary

The browser will call only same-origin application endpoints:

- `GET /api/library/tracks?offset=0&limit=50`
- `GET /api/search/tracks?q=QUERY&offset=0&limit=10`

Flask validates pagination and search input, refreshes tokens through the
existing service boundary, calls Spotify, and returns normalized track objects.
The frontend never receives the long-lived refresh token.

## Authorization

Liked Songs requires the Spotify `user-library-read` scope. Search uses the
existing `user-read-private` authorization. Existing in-memory sessions will be
cleared by restarting the app, and the next authorization will request the new
scope.

## Playback behavior

Playlist tracks retain context playback so Spotify can continue within the
playlist. Liked and searched tracks use direct URI playback because they do not
have a playlist context.

## Acceptance criteria

1. Opening Library loads Liked Songs by default.
2. Empty, loading, error, and populated Liked Songs states are understandable.
3. A Load More action appends the next page when Spotify reports one.
4. Playlists remain accessible and retain their current behavior.
5. Search rejects blank or excessively long input before contacting Spotify.
6. Search returns no more than Spotify's current maximum of 10 tracks per page.
7. Selecting a liked or searched track starts direct playback on the active
   Web Playback SDK device.
8. Selecting a playlist track continues to use playlist context playback.
9. Spotify IDs, URIs, query text, pagination, and errors are validated or
   normalized at existing trust boundaries.
10. Python and JavaScript automated tests cover the new behavior without real
    credentials or Spotify network calls.

## Non-goals

- Albums, artists, podcasts, audiobooks, or playlist search
- Editing playlists or changing the user's Liked Songs
- Downloading or offline playback
- Search history or recommendations
- Replacing the official Spotify application feature-for-feature

## Current Spotify constraints

- Saved tracks use `GET /me/tracks` and require `user-library-read`.
- Saved tracks allow at most 50 items per request.
- Search uses `GET /search` with `type=track`.
- Search allows at most 10 results per item type per request as of the February
  2026 Web API changes.

## Verification results

Automated verification completed on 2026-09-01:

- 63 Python tests passed.
- 20 JavaScript tests passed.
- `pip check`, Python bytecode compilation, and `git diff --check` passed.

Manual desktop verification confirmed:

- A fresh authorization requested the added library permission.
- Library opened on Liked Songs by default.
- Selecting a liked song started direct playback.
- The Playlists view and playlist-context playback still worked.
- Track search returned results and direct playback worked from those results.
- The content-fitting desktop window continued to behave correctly.

The Liked Songs **Load More** action was not manually exercised during this
verification. Its pagination and append behavior are covered by automated tests,
but it remains a manual follow-up item for an account with more than 50 saved
tracks.

## References

- [Get User's Saved Tracks](https://developer.spotify.com/documentation/web-api/reference/get-users-saved-tracks)
- [Search for Item](https://developer.spotify.com/documentation/web-api/reference/search)
- [Spotify authorization scopes](https://developer.spotify.com/documentation/web-api/concepts/scopes)
- [February 2026 Web API changes](https://developer.spotify.com/documentation/web-api/references/changes/february-2026)
