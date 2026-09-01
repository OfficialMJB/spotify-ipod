# Manual Spotify verification checklist

## Why this checklist exists

Automated tests use injected fakes and sanitized fixtures so they remain fast, deterministic, and credential-free. They can verify our logic, but they cannot prove that a real Spotify account, browser, network, or current Spotify service behaves correctly.

Complete this checklist with a Spotify Premium account after the automated suite passes. Record the date, browser versions, and any failures. Do not mark an item complete unless it was observed with a real account.

## Prerequisites

- [ ] A Spotify developer application exists.
- [ ] The exact redirect URI `http://127.0.0.1:5050/auth/callback` is registered.
- [ ] The developer account and test user meet Spotify's current Premium and allowlist requirements.
- [ ] `.env` contains a unique Flask secret and the real Spotify application values.
- [ ] `.env` is untracked and `git status` shows no credentials.
- [ ] The virtual environment is active and dependencies are installed.

## Authorization and session

- [ ] Opening the application while signed out shows the welcome state.
- [ ] The sign-in action opens Spotify's authorization page.
- [ ] Approving access returns to the application and shows playlists.
- [ ] Denying access returns a useful, non-sensitive error.
- [ ] Refreshing the page keeps the local session while the Flask process is running.
- [ ] Restarting Flask signs the user out, as documented for the in-memory MVP store.
- [ ] Signing out clears the session and returns to the welcome state.

## Library browsing

- [ ] Owned playlists appear.
- [ ] Collaborative playlists appear when available.
- [ ] Ineligible playlists are disabled with an explanation.
- [ ] Opening an eligible playlist shows its available tracks.
- [ ] Empty playlists, unavailable tracks, and missing artwork do not break the interface.
- [ ] Spotify metadata and artwork include appropriate Spotify links or attribution.

## Browser playback

- [ ] The Web Playback SDK connects and reports a device identifier.
- [ ] The first user playback gesture succeeds without a hidden autoplay failure.
- [ ] Selecting a track starts that track in its playlist context.
- [ ] Pause/resume works.
- [ ] Previous and next work.
- [ ] Track title, artist, artwork, duration, and paused/playing state follow SDK events.
- [ ] Progress stops while paused and resynchronizes after a state update.
- [ ] A visible recovery message appears if the device goes offline.

## Appearance and accessibility

- [ ] Compact and expanded modes preserve the selected playlist and player state.
- [ ] Pocket, Minimal, and Retro themes remain readable.
- [ ] Green, blue, and orange accent choices have visible focus states.
- [ ] Appearance choices survive a page refresh.
- [ ] Reset restores the documented defaults.
- [ ] All essential actions can be reached and used with a keyboard.
- [ ] Touch targets are usable on a narrow viewport.
- [ ] Reduced-motion preference disables unnecessary animation.

## Failure paths

- [ ] An expired access token refreshes without exposing a token in the UI or URL.
- [ ] An invalid refresh token returns the user to sign-in.
- [ ] A Spotify rate-limit response shows a retry message instead of retrying rapidly.
- [ ] A Premium/account error is distinguishable from a general playback error.
- [ ] An offline or failed Spotify request leaves a usable retry or sign-in action.

## Verification record

```text
Date:
Tester:
Operating system:
Browsers and versions:
Spotify account type:
Result:
Notes or issue links:
```
