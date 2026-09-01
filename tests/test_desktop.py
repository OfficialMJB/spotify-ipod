from __future__ import annotations

from threading import Event
from typing import Any

import pytest

import app.desktop as desktop
from app.desktop import (
    DESKTOP_HOST,
    DESKTOP_PORT,
    WINDOW_BACKGROUND_COLOR,
    WINDOW_CHROME_HEIGHT,
    WINDOW_HEIGHT,
    WINDOW_MAXIMUM_SIZE,
    WINDOW_MINIMUM_SIZE,
    WINDOW_TITLE,
    WINDOW_WIDTH,
    _redacted_request_path,
    DesktopServer,
    DesktopWindowController,
    run_desktop,
)


class FakeServer:
    server_port = DESKTOP_PORT

    def __init__(self) -> None:
        self.started = Event()
        self.shutdown_requested = Event()
        self.closed = False

    def serve_forever(self) -> None:
        self.started.set()
        self.shutdown_requested.wait(timeout=1)

    def shutdown(self) -> None:
        self.shutdown_requested.set()

    def server_close(self) -> None:
        self.closed = True


class FakeWebview:
    def __init__(self, server: FakeServer, *, fail_on_start: bool = False) -> None:
        self.server = server
        self.fail_on_start = fail_on_start
        self.window_arguments: tuple[tuple[Any, ...], dict[str, Any]] | None = None
        self.start_calls = 0
        self.window = FakeWindow()

    def create_window(self, *args: Any, **kwargs: Any):
        self.window_arguments = (args, kwargs)
        return self.window

    def start(self) -> None:
        assert self.server.started.wait(timeout=1)
        self.start_calls += 1
        if self.fail_on_start:
            raise RuntimeError("GUI failed")


def fake_server_factory(server: FakeServer):
    def factory(host, port, application, *, threaded, request_handler):
        assert host == DESKTOP_HOST
        assert port == DESKTOP_PORT
        assert application is sentinel_application
        assert threaded is True
        assert request_handler is desktop.DesktopRequestHandler
        return server

    return factory


sentinel_application = object()


class FakeWindow:
    def __init__(self) -> None:
        self.resize_calls: list[tuple[int, int]] = []

    def resize(self, width: int, height: int) -> None:
        self.resize_calls.append((width, height))


def test_desktop_server_reports_loopback_url_and_stops_cleanly():
    server = FakeServer()
    desktop_server = DesktopServer(
        sentinel_application,
        server_factory=fake_server_factory(server),
    )

    assert desktop_server.url == "http://127.0.0.1:5050"

    desktop_server.start()
    assert server.started.wait(timeout=1)

    desktop_server.stop()

    assert server.shutdown_requested.is_set()
    assert server.closed is True


def test_desktop_server_cannot_be_started_twice():
    server = FakeServer()
    desktop_server = DesktopServer(
        sentinel_application,
        server_factory=fake_server_factory(server),
    )
    desktop_server.start()

    with pytest.raises(RuntimeError, match="only be started once"):
        desktop_server.start()

    desktop_server.stop()


def test_run_desktop_creates_compact_window_and_releases_server():
    server = FakeServer()
    webview = FakeWebview(server)

    run_desktop(
        application_factory=lambda: sentinel_application,
        webview_module=webview,
        server_factory=fake_server_factory(server),
    )

    assert webview.window_arguments is not None
    args, kwargs = webview.window_arguments
    assert args == (WINDOW_TITLE, "http://127.0.0.1:5050")
    assert isinstance(kwargs.pop("js_api"), DesktopWindowController)
    assert kwargs == {
        "width": WINDOW_WIDTH,
        "height": WINDOW_HEIGHT,
        "min_size": WINDOW_MINIMUM_SIZE,
        "resizable": True,
        "background_color": WINDOW_BACKGROUND_COLOR,
    }
    assert webview.start_calls == 1
    assert server.closed is True


def test_window_controller_resizes_valid_content_and_ignores_duplicates():
    window = FakeWindow()
    controller = DesktopWindowController()
    controller.attach(window)

    controller.resize_window(448, 300)
    controller.resize_window(448, 300)

    assert window.resize_calls == [(448, 300 + WINDOW_CHROME_HEIGHT)]


def test_window_controller_clamps_dimensions_and_rejects_invalid_values():
    window = FakeWindow()
    controller = DesktopWindowController()
    controller.attach(window)

    controller.resize_window(1, 1)
    controller.resize_window(99999, 99999)
    controller.resize_window("not-a-number", None)

    assert window.resize_calls == [WINDOW_MINIMUM_SIZE, WINDOW_MAXIMUM_SIZE]


def test_run_desktop_releases_server_when_gui_fails():
    server = FakeServer()
    webview = FakeWebview(server, fail_on_start=True)

    with pytest.raises(RuntimeError, match="GUI failed"):
        run_desktop(
            application_factory=lambda: sentinel_application,
            webview_module=webview,
            server_factory=fake_server_factory(server),
        )

    assert server.shutdown_requested.is_set()
    assert server.closed is True


def test_main_loads_environment_before_starting_desktop(monkeypatch):
    calls = []

    monkeypatch.setattr(desktop, "load_dotenv", lambda: calls.append("load_dotenv"))
    monkeypatch.setattr(desktop, "run_desktop", lambda: calls.append("run_desktop"))

    desktop.main()

    assert calls == ["load_dotenv", "run_desktop"]


def test_desktop_request_logs_redact_oauth_callback_query():
    assert _redacted_request_path(
        "/auth/callback?code=one-time-code&state=state-value"
    ) == "/auth/callback?[query redacted]"
    assert _redacted_request_path("/api/playlists?offset=0") == (
        "/api/playlists?offset=0"
    )
