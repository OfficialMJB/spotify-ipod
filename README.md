# Spotify iPod

A planned, non-commercial portfolio project that explores an iPod-inspired interface for browsing and playing a user's Spotify music.

> The repository name is a working development name, not a claim of affiliation with or endorsement by Spotify or Apple. A distinct public-facing name should be chosen before publishing the application.

## Project status

Planning and repository setup only. No application code or dependencies have been added yet.

The agreed MVP, user flow, architecture boundary, acceptance criteria, implementation slices, and API draft are documented in [docs/planning/mvp.md](docs/planning/mvp.md).

## Proposed stack

- Python and Flask for OAuth, session handling, and a small API boundary
- HTML, CSS, and vanilla JavaScript for the interface
- Spotify Web API for library metadata
- Spotify Web Playback SDK for in-browser playback
- pytest for backend tests and browser-oriented tests for critical UI behavior

This stack keeps the backend Python-first and the browser code small while still supporting Spotify's JavaScript playback SDK.

## Important feasibility constraints

- The first release is a local, single-user prototype.
- The developer account and playback user need Spotify Premium under the current development-mode and Web Playback SDK requirements.
- A new development-mode app supports up to five allowlisted users.
- In development mode, playlist contents are available only for playlists the user owns or collaborates on.
- Spotify content must retain required metadata, links, artwork treatment, and Spotify attribution.
- Streaming integrations using the Spotify Platform cannot be commercialized under the current platform policy.

These constraints should be rechecked against Spotify's official documentation before implementation or release because platform rules can change.

## Planned repository shape

The implementation should add only the directories needed by each vertical slice. The likely shape is:

```text
spotify-ipod/
├── app/                 # Flask application and Spotify integration
├── static/              # CSS, JavaScript, and local UI assets
├── templates/           # Accessible HTML templates
├── tests/               # Behavior-focused automated tests
├── docs/planning/       # Product and technical planning
├── .env.example         # Variable names only; never real credentials
├── .gitignore
└── README.md
```

## Before implementation

1. Review and accept the MVP boundaries in the planning document.
2. Confirm access to a Spotify Premium account.
3. Create one application in the Spotify Developer Dashboard and register an exact local redirect URI.
4. Create a feature branch for the first implementation slice.
5. Add configuration and a minimal Flask health page before building Spotify features.

No credentials, tokens, or generated local databases should be committed.
