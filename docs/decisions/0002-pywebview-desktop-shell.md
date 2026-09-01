# ADR 0002: Use pywebview for the first desktop shell

- **Status:** Accepted
- **Date:** 2026-09-01

## Context

The working MVP is a Flask application with an HTML, CSS, and vanilla-JavaScript
interface. Rewriting that interface with native widgets or adding a second
JavaScript application framework would duplicate tested behavior before desktop
feasibility was known.

The desktop spike tested pywebview on macOS. It successfully hosted the existing
application in a native window, loaded local configuration, completed Spotify
authorization, initialized the Web Playback SDK, and shut down its loopback
server with the window.

## Decision

Use pywebview 6.x as the first desktop shell for Spotify Pocket Player.

- Flask continues to own OAuth, tokens, validation, and Spotify Web API calls.
- The existing frontend remains the application interface.
- The desktop launcher binds only to `127.0.0.1:5050`.
- The native window follows the active player or panel content instead of
  presenting a browser-sized viewport.
- pywebview remains an optional dependency so browser development and CI do not
  require GUI libraries.

## Why

- It preserves the tested Python-first architecture.
- It produces a normal desktop window without bundling a second full browser
  runtime.
- It keeps the browser version available for debugging.
- The macOS smoke test resolved the primary playback-feasibility risk.

## Consequences

- macOS uses the operating system's `WKWebView`; other platforms will require
  separate verification.
- The current prototype performs Spotify authorization inside the desktop
  window. A system-browser OAuth handoff should be designed before packaging or
  broader distribution.
- Packaging, signing, installers, and automatic updates remain future work.
- If embedded playback becomes unreliable on another platform, the documented
  Spotify Connect controller fallback remains available.
