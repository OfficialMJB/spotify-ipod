# Spotify Pocket Player architecture

## Purpose

Spotify Pocket Player is a local, single-user Flask application with a vanilla-JavaScript interface. Flask owns OAuth, token refresh, input validation, and Spotify Web API calls. The browser owns presentation state and the Spotify Web Playback SDK player.

The first complete user path is:

```text
Welcome
  -> authorize with Spotify
  -> browse eligible playlists
  -> open a playlist
  -> select a track
  -> play it through the browser player
```

## System boundary

```text
+---------------------------+
| Browser                   |
|                           |
| HTML/CSS/JavaScript       |
| Web Playback SDK          |
| local display preferences |
+-------------+-------------+
              |
              | same-origin HTTP/JSON
              v
+-------------+-------------+
| Flask application         |
|                           |
| routes and validation     |
| OAuth state and CSRF      |
| in-memory token store     |
| Spotify adapters          |
+-------------+-------------+
              |
              | HTTPS
              v
+-------------+-------------+
| Spotify                   |
| Accounts service          |
| Web API                   |
+---------------------------+
```

## Responsibility split

### Flask

- Starts and completes Spotify's Authorization Code flow.
- Stores access and refresh tokens in server memory.
- Gives the browser only the short-lived token required by the Web Playback SDK.
- Refreshes expired access tokens.
- Fetches and normalizes playlists and tracks.
- Validates playback requests before forwarding them to Spotify.
- Converts upstream failures into a stable JSON error format.

### Browser

- Renders welcome, playlist, track, player, loading, empty, and error states.
- Keeps compact/expanded mode, theme, and accent preferences in local storage.
- Connects to the Web Playback SDK after authentication.
- Uses SDK events as the source of truth for the current track and playback state.
- Never stores Spotify access tokens in local storage.

## Session and token design

Flask's standard session cookie is signed but not encrypted, so Spotify tokens do not belong in it. The cookie contains only an opaque local session identifier, OAuth state, and a CSRF value. The corresponding Spotify tokens live in an in-process memory store.

This is an intentional MVP tradeoff:

- Restarting the Flask server signs the user out.
- Multiple Flask processes would not share sessions.
- No database or application-owned user account is required.

If the application is deployed later, replace the memory store with encrypted server-side persistence before adding multiple processes or users.

## Spotify adapter boundary

Spotify-specific HTTP behavior is isolated from Flask routes:

- The OAuth adapter builds authorization URLs and exchanges or refreshes tokens.
- The API adapter owns authenticated requests, timeouts, JSON decoding, and status translation.
- The service layer validates application inputs and normalizes Spotify response fields.

Tests inject fake or mock HTTP clients at this boundary. The normal automated suite must never require credentials or contact Spotify.

## Security decisions

- Generate OAuth state, CSRF tokens, and local session identifiers with a cryptographically secure generator.
- Compare OAuth state values safely and allow each value to be used only once.
- Keep client secrets and Spotify tokens out of Git, templates, URLs, fixtures, and logs.
- Require CSRF validation for logout and starting playback.
- Apply `HttpOnly` and `SameSite=Lax` to the local session cookie.
- Return `Cache-Control: no-store` on session- and token-sensitive responses.
- Whitelist Spotify identifiers, device identifiers, themes, and accent values instead of forwarding arbitrary input.

## Deliberate non-goals

The MVP has no database, search, recommendations, playlist editing, downloads, lyrics, queue editor, arbitrary themes, React frontend, or production deployment. These features should be considered only after the complete vertical path is usable and tested.
