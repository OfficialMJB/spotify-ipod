# Spotify Pocket Player

A local, non-commercial portfolio MVP that explores a compact, customizable interface for browsing and playing a user's Spotify music.

> "Spotify Pocket Player" and the repository name `spotify-ipod` are working development names, not claims of affiliation with or endorsement by Spotify. A distinct public-facing name should be chosen before publishing the application.

## Project status

The first local MVP is implemented on `feature/pocket-player-mvp`:

- Spotify Authorization Code sign-in with server-side token storage and refresh
- Eligible playlist and track browsing
- Browser playback integration through the Spotify Web Playback SDK
- Compact and expanded player modes
- Pocket, Minimal, and Retro themes with three controlled accent choices
- Offline Python and JavaScript tests for the application-owned behavior

The automated suite does not use Spotify credentials or make Spotify network calls. Real OAuth and audio playback still require the manual Premium-account verification documented in [docs/testing/manual-spotify-verification.md](docs/testing/manual-spotify-verification.md).

The revised MVP, user flow, architecture boundary, acceptance criteria, implementation slices, and API draft are documented in [docs/planning/mvp.md](docs/planning/mvp.md). The shift from a literal iPod-style interface to a customizable pocket player is recorded in [ADR 0001](docs/decisions/0001-customizable-pocket-player.md).

## Chosen stack

- Python and Flask for OAuth, session handling, and a small API boundary
- HTTPX for narrow, timeout-protected Spotify HTTP adapters
- HTML, CSS, and vanilla JavaScript for the interface
- Spotify Web API for library metadata
- Spotify Web Playback SDK for in-browser playback
- pytest for backend tests and browser-oriented tests for critical UI behavior
- Node's built-in test runner for framework-free JavaScript module tests

This stack keeps the backend Python-first and the browser code small while still supporting Spotify's JavaScript playback SDK.

## Product direction

The MVP is a small Spotify-connected player with:

- A compact mode for essential track information and playback controls
- An expanded mode for artwork, progress, library access, and customization
- A focused playlist and track browser
- Three predefined visual themes and one accent-color preference
- Locally remembered display preferences

The project may borrow ideas from pocket music players, but it will develop its own layout and visual identity rather than reproduce an iPod body or click wheel.

## Local development setup

### Requirements

- Git
- Python 3.14
- Node.js when running the JavaScript tests; it is not required to run the application
- pywebview and its platform dependencies when running the desktop application
- A Spotify Premium account and Spotify developer application for real OAuth and playback; neither is required for the offline tests or welcome screen

### Create the environment

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Include the optional desktop runtime when working on the native-window build:

```bash
python -m pip install -e ".[dev,desktop]"
```

The editable installation uses `pyproject.toml` as the source of truth for runtime and development dependencies. The `.venv/` directory and generated packaging metadata are local artifacts and must not be committed.

### Verify the environment

```bash
python --version
command -v python
python -c "from importlib.metadata import version; print('Flask', version('Flask'))"
python -m pytest --version
python -m pip check
```

The Python path should end in `.venv/bin/python`, and `pip check` should report that no requirements are broken.

### Reactivate after opening a new terminal

The environment directory persists, but activation applies only to the current terminal session:

```bash
source .venv/bin/activate
```

Use `deactivate` when you want to leave the environment.

### Configure local secrets

Copy the configuration template if `.env` does not already exist:

```bash
cp .env.example .env
```

Fill in the real values only in `.env`. Never add credentials or tokens to `.env.example`, source code, logs, or Git. A development-only Flask secret can be generated with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Set all four variables. The Spotify redirect URI in `.env` and in the Spotify Developer Dashboard must be exactly:

```text
http://127.0.0.1:5050/auth/callback
```

Do not replace `127.0.0.1` with `localhost`.

### Run the application

```bash
python -m flask --app app run
```

Open [http://127.0.0.1:5050](http://127.0.0.1:5050). Port 5050 avoids the AirPlay Receiver service that commonly occupies port 5000 on macOS. The welcome screen works without Spotify credentials and explains when local configuration is incomplete.

The MVP uses an in-memory server-side token store. Restarting Flask intentionally signs the user out.

### Run the desktop application

Install the desktop extra, stop any separate Flask process using port 5050, then run:

```bash
spotify-pocket-player
```

The equivalent module command is:

```bash
python -m app.desktop
```

The launcher starts Flask on the loopback interface, opens the existing UI in a
content-fitting native window, and stops the server when the window closes.

## Tests

Run the offline Python suite:

```bash
python -m pytest
```

If Node.js is installed, run the framework-free JavaScript suite:

```bash
node --test tests/js/*.test.mjs
```

Finish a local checkpoint with:

```bash
python -m pip check
git diff --check
git status --short --branch
```

## Development workflow

1. Keep `main` in a working state.
2. Create a focused branch such as `chore/development-environment` or `feature/spotify-authentication`.
3. Make one logical change at a time.
4. Review `git status` and `git diff` before staging.
5. Run the relevant verification and tests before committing.
6. Use a concise commit message and merge through a pull request when the repository is connected to GitHub.

## Important feasibility constraints

- The first release is a local, single-user prototype.
- The developer account and playback user need Spotify Premium under the current development-mode and Web Playback SDK requirements.
- A new development-mode app supports up to five allowlisted users.
- In development mode, playlist contents are available only for playlists the user owns or collaborates on.
- Spotify content must retain required metadata, links, artwork treatment, and Spotify attribution.
- Streaming integrations using the Spotify Platform cannot be commercialized under the current platform policy.

These constraints should be rechecked against Spotify's official documentation before implementation or release because platform rules can change.

## Repository shape

The implementation uses only the directories needed by the current vertical slice:

```text
spotify-ipod/
├── app/
│   ├── routes/          # Page, OAuth, and same-origin API routes
│   ├── spotify/         # OAuth, Web API, service, errors, and token store
│   ├── static/          # CSS and vanilla JavaScript modules
│   └── templates/       # Accessible HTML application shell
├── tests/               # Offline Python and JavaScript behavior tests
├── docs/design/         # Reviewed UX artifacts
├── docs/decisions/      # Architecture and product decision records
├── docs/planning/       # Product and technical planning
├── .env.example         # Variable names only; never real credentials
├── .gitignore
├── pyproject.toml        # Project metadata and dependency declarations
└── README.md
```

## Known MVP limitations

- This is a local, single-user, single-process application.
- Restarting Flask clears the in-memory Spotify session.
- Real OAuth, playback, responsive layout, and screen-reader behavior remain manual verification items until tested with credentials and browsers.
- Revised pocket-player wireframes are still being documented, so later visual polish may change without changing the architecture.
- The working product and repository names should be reconsidered before public release.

No credentials, tokens, generated local databases, or `.env` file should be committed.
