# Spotify iPod

A planned, non-commercial portfolio project that explores an iPod-inspired interface for browsing and playing a user's Spotify music.

> The repository name is a working development name, not a claim of affiliation with or endorsement by Spotify or Apple. A distinct public-facing name should be chosen before publishing the application.

## Project status

Planning and development-environment setup only. Python dependencies are declared, but no application code has been added yet.

The agreed MVP, user flow, architecture boundary, acceptance criteria, implementation slices, and API draft are documented in [docs/planning/mvp.md](docs/planning/mvp.md).

## Chosen stack

- Python and Flask for OAuth, session handling, and a small API boundary
- HTML, CSS, and vanilla JavaScript for the interface
- Spotify Web API for library metadata
- Spotify Web Playback SDK for in-browser playback
- pytest for backend tests and browser-oriented tests for critical UI behavior

This stack keeps the backend Python-first and the browser code small while still supporting Spotify's JavaScript playback SDK.

## Local development setup

### Requirements

- Git
- Python 3.14
- A Spotify Premium account and Spotify developer application before OAuth integration begins

### Create the environment

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
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

When Spotify integration begins, copy the configuration template:

```bash
cp .env.example .env
```

Fill in the real values only in `.env`. Never add credentials or tokens to `.env.example`, source code, logs, or Git. A development-only Flask secret can be generated with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

The Spotify redirect URI in `.env` must exactly match the URI registered in the Spotify Developer Dashboard.

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
├── pyproject.toml        # Project metadata and dependency declarations
└── README.md
```

## Before implementation

1. Review and accept the MVP boundaries in the planning document.
2. Confirm access to a Spotify Premium account.
3. Create one application in the Spotify Developer Dashboard and register an exact local redirect URI.
4. Finish and review the development-environment setup branch.
5. Add configuration and a minimal Flask health page before building Spotify features.

No credentials, tokens, or generated local databases should be committed.
