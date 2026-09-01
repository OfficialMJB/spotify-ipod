"""Desktop launcher for the existing Flask application."""

from __future__ import annotations

from collections.abc import Callable
from importlib import import_module
from math import isfinite
from threading import Thread
from typing import Any

from dotenv import load_dotenv
from werkzeug.serving import BaseWSGIServer, WSGIRequestHandler, make_server

from . import create_app

DESKTOP_HOST = "127.0.0.1"
DESKTOP_PORT = 5050
DESKTOP_URL = f"http://{DESKTOP_HOST}:{DESKTOP_PORT}"
WINDOW_TITLE = "Spotify Pocket Player"
WINDOW_WIDTH = 580
WINDOW_HEIGHT = 640
WINDOW_MINIMUM_SIZE = (360, 260)
WINDOW_MAXIMUM_SIZE = (1100, 850)
WINDOW_CHROME_HEIGHT = 28
WINDOW_BACKGROUND_COLOR = "#111613"


class DesktopDependencyError(RuntimeError):
    """Raised when the optional desktop runtime is not installed."""


def _redacted_request_path(path: str) -> str:
    """Keep one-time Spotify authorization codes out of request logs."""

    if path.startswith("/auth/callback?"):
        return "/auth/callback?[query redacted]"
    return path


class DesktopRequestHandler(WSGIRequestHandler):
    """Use normal request logging without printing OAuth callback parameters."""

    def log_request(self, code: int | str = "-", size: int | str = "-") -> None:
        original_path = getattr(self, "path", None)
        if isinstance(original_path, str):
            self.path = _redacted_request_path(original_path)
        try:
            super().log_request(code, size)
        finally:
            if isinstance(original_path, str):
                self.path = original_path


def _finite_integer(value: object) -> int | None:
    """Return a positive finite integer or reject an unsafe dimension."""

    try:
        numeric_value = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if not isfinite(numeric_value) or numeric_value <= 0:
        return None
    return round(numeric_value)


class DesktopWindowController:
    """Expose the smallest safe native-window API needed by the frontend."""

    def __init__(self) -> None:
        self._window: Any | None = None
        self._last_size: tuple[int, int] | None = None

    def attach(self, window: Any) -> None:
        """Attach the pywebview window after it has been created."""

        self._window = window

    def resize_window(self, content_width: object, content_height: object) -> None:
        """Fit the native window to validated frontend content dimensions."""

        width = _finite_integer(content_width)
        height = _finite_integer(content_height)
        if self._window is None or width is None or height is None:
            return

        outer_width = min(max(width, WINDOW_MINIMUM_SIZE[0]), WINDOW_MAXIMUM_SIZE[0])
        outer_height = min(
            max(height + WINDOW_CHROME_HEIGHT, WINDOW_MINIMUM_SIZE[1]),
            WINDOW_MAXIMUM_SIZE[1],
        )
        size = (outer_width, outer_height)
        if size == self._last_size:
            return
        self._last_size = size
        self._window.resize(*size)


class DesktopServer:
    """Run a loopback-only WSGI server in a managed background thread."""

    def __init__(
        self,
        application: Any,
        *,
        host: str = DESKTOP_HOST,
        port: int = DESKTOP_PORT,
        server_factory: Callable[..., BaseWSGIServer] = make_server,
    ) -> None:
        self._host = host
        self._server = server_factory(
            host,
            port,
            application,
            threaded=True,
            request_handler=DesktopRequestHandler,
        )
        self._thread: Thread | None = None

    @property
    def url(self) -> str:
        """Return the loopback URL using the server's actual bound port."""

        return f"http://{self._host}:{self._server.server_port}"

    def start(self) -> None:
        """Start serving in a daemon thread."""

        if self._thread is not None:
            raise RuntimeError("The desktop server can only be started once.")
        self._thread = Thread(
            target=self._server.serve_forever,
            name="spotify-pocket-player-server",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop serving and release the loopback port."""

        if self._thread is not None:
            self._server.shutdown()
            self._thread.join(timeout=5)
        self._server.server_close()


def load_webview() -> Any:
    """Load pywebview lazily so browser-only development stays lightweight."""

    try:
        return import_module("webview")
    except ImportError as error:
        raise DesktopDependencyError(
            'Desktop support is not installed. Run: python -m pip install -e ".[dev,desktop]"'
        ) from error


def run_desktop(
    *,
    application_factory: Callable[[], Any] = create_app,
    webview_module: Any | None = None,
    server_factory: Callable[..., BaseWSGIServer] = make_server,
) -> None:
    """Open the Flask application in a compact native desktop window."""

    webview = webview_module or load_webview()
    window_controller = DesktopWindowController()
    server = DesktopServer(
        application_factory(),
        server_factory=server_factory,
    )
    server.start()
    try:
        window = webview.create_window(
            WINDOW_TITLE,
            server.url,
            js_api=window_controller,
            width=WINDOW_WIDTH,
            height=WINDOW_HEIGHT,
            min_size=WINDOW_MINIMUM_SIZE,
            resizable=True,
            background_color=WINDOW_BACKGROUND_COLOR,
        )
        if window is None:
            raise RuntimeError("The desktop window could not be created.")
        window_controller.attach(window)
        webview.start()
    finally:
        server.stop()


def main() -> None:
    """Run the desktop application from the installed console command."""

    load_dotenv()
    try:
        run_desktop()
    except DesktopDependencyError as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()
