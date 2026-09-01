# Desktop Runtime Feasibility Spike

- **Status:** Phase 1 validated
- **Branch:** `spike/desktop-runtime`
- **Date:** 2026-08-31

## Purpose

Determine the smallest reliable way to ship Spotify Pocket Player as a compact
desktop application while preserving the working Flask, HTML, CSS, and
JavaScript MVP.

This spike must answer the playback question before the project commits to a
desktop framework or packaging tool.

## Current architecture

The existing application has two runtime responsibilities:

- Flask handles Spotify OAuth, server-side token storage, API requests, input
  validation, and session security.
- The browser renders the interface and uses Spotify's Web Playback SDK as the
  local audio device.

The desktop build should reuse these boundaries unless the spike demonstrates
that a boundary cannot work inside a packaged window.

## Candidate under test

Use pywebview as the first candidate because it can display an existing Flask
application in a native desktop window without rewriting the interface. On
macOS, pywebview uses the operating system's `WKWebView` renderer.

The first prototype will be a development launcher, not a distributable app.

## Primary unknown

Spotify documents Web Playback SDK support for full browsers, including
Safari, but does not explicitly guarantee support inside embedded webviews.
The spike must test playback in pywebview rather than infer compatibility from
Safari support.

## Fallback architecture

If the Web Playback SDK cannot initialize or play audio reliably in pywebview,
the desktop application will become a Spotify Connect controller:

```text
Pocket Player desktop window
        |
        | Spotify Web API playback commands
        v
Official Spotify desktop app or another Connect device
        |
        v
Audio output
```

This fallback preserves the custom interface while letting an official Spotify
client own audio playback. It will require reading available devices and the
current playback state in addition to sending playback commands.

## Acceptance criteria

The spike succeeds when it produces evidence for each item below:

1. A Python command opens the existing interface in a compact desktop window.
2. The welcome and configuration-error states work without Spotify credentials.
3. Closing the window stops the local application cleanly.
4. OAuth opens in the system browser and returns to the explicit loopback
   callback without exposing credentials or tokens.
5. The Web Playback SDK either plays a track in the desktop window or fails
   with a captured, documented reason.
6. If embedded playback fails, the application can discover an eligible
   Spotify Connect device and control playback on it.
7. Existing Python and JavaScript tests continue to pass.

## Security requirements

- Bind the local server only to `127.0.0.1`, never all network interfaces.
- Keep the existing OAuth state and CSRF protections.
- Open Spotify authorization in the user's system browser.
- Keep the client secret and Spotify tokens out of the packaged frontend,
  source control, URLs, and logs.
- Continue using an exact allowlisted loopback redirect URI.

## Spike sequence

### Phase 1: Desktop window

- Add pywebview as a development dependency.
- Add a small desktop launcher with no duplicated Flask configuration.
- Load the welcome screen in a compact, resizable window.
- Verify clean startup and shutdown.

### Phase 2: Authentication

- Open the authorization URL in the system browser.
- Complete the existing loopback callback.
- Refresh the desktop interface after authorization succeeds.

### Phase 3: Embedded playback

- Initialize the Web Playback SDK inside the desktop window.
- Attempt an explicitly user-initiated playback action.
- Record the renderer, behavior, and any SDK error.

### Phase 4: Connect fallback

Run this phase only if embedded playback is unsupported or unreliable:

- Add the minimum playback-state authorization scope.
- List available Spotify Connect devices.
- Select or clearly identify the active device.
- Play, pause, skip, and refresh current playback state through the Web API.

## Decision rules

- Choose embedded playback only if authorization, initialization, audio, and
  state updates work reliably in the packaged renderer.
- Choose the Connect-controller design if embedded audio fails or requires
  unsupported renderer modifications.
- Do not change frameworks merely to force embedded playback.
- Record the result in a new architecture decision record before building the
  production desktop shell.

## Non-goals

This spike will not add:

- An installer or signed macOS application bundle
- Windows packaging
- Automatic updates
- Menu-bar or system-tray behavior
- Background startup
- A rewritten native-widget interface
- New library, search, queue, or customization features

## Expected deliverables

- A minimal desktop launcher and focused automated tests
- Manual verification notes for authentication and playback
- An accepted desktop-runtime architecture decision record
- Updated setup documentation after the runtime decision is made

## Phase 1 result

Validated on macOS with Python 3.14 and pywebview 6.2.1:

- The existing Flask UI opened in a native `WKWebView` window.
- The window resized to the welcome screen, compact player, expanded player,
  and side-panel layouts without leaving a large unused viewport.
- Closing the window stopped the loopback server and released port 5050.
- The existing `.env` configuration loaded through the desktop entry point.
- Spotify authorization completed in the embedded window.
- The Web Playback SDK initialized, playlists loaded, and a playback-start
  request completed successfully during the manual smoke test.

The prototype demonstrates that pywebview is a viable shell for this macOS
portfolio application. External-system-browser OAuth remains a pre-packaging
security improvement; the current local prototype uses the working embedded
flow.

## References

- [pywebview application architecture](https://pywebview.idepy.com/en/guide/architecture)
- [pywebview web engines](https://pywebview.idepy.com/en/guide/web_engine)
- [Spotify Web Playback SDK](https://developer.spotify.com/documentation/web-playback-sdk)
- [Spotify available devices endpoint](https://developer.spotify.com/documentation/web-api/reference/get-a-users-available-devices)
- [Spotify transfer playback endpoint](https://developer.spotify.com/documentation/web-api/reference/transfer-a-users-playback)
- [Spotify redirect URI requirements](https://developer.spotify.com/documentation/web-api/concepts/redirect_uri)
