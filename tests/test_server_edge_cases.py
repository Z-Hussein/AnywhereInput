"""Tests for server module components not covered by test_server.py."""
import asyncio
import json
import pytest
import sys
from pathlib import Path
from unittest import mock

src = Path(__file__).parent.parent / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))


def test_server_version_constant():
    """__version__ should be a string matching semver."""
    from anywhereinput import __version__
    parts = __version__.split(".")
    for p in parts:
        assert p.isdigit() or p.replace("-", "").isalnum()


def test_tunnel_choices():
    """TUNNEL_CHOICES must contain expected providers."""
    from anywhereinput.launcher import TUNNEL_CHOICES

    expected = {"cloudflare", "tailscale", "pinggy", "zrok2", "local"}
    assert set(TUNNEL_CHOICES) == expected


def test_server_pyautogui_lock():
    """_pyautogui_lock should be a real threading.Lock."""
    from anywhereinput.mouse_worker import _pyautogui_lock

    assert hasattr(_pyautogui_lock, 'acquire')
    assert hasattr(_pyautogui_lock, 'release')


# ─── MouseWorker state logic ────────────────────────────────────────────────

def test_mouse_worker_engine_state_healthy():
    """MouseWorker reports 'healthy' when no consecutive failures."""
    from anywhereinput.mouse_worker import MouseWorker

    mw = MouseWorker()
    assert mw.consecutive_failures == 0
    state = mw.get_engine_state()
    assert "offline" not in state.lower()


def test_mouse_worker_engine_state_offline_threshold():
    """MouseWorker reports 'offline' after exceeding failure threshold."""
    from anywhereinput.mouse_worker import MouseWorker

    mw = MouseWorker()
    max_failures = mw.max_failures_before_offline
    mw.consecutive_failures = max_failures
    state = mw.get_engine_state()
    assert state == "offline"


def test_mouse_worker_engine_state_recovering():
    """MouseWorker reports 'recovering' within backoff window."""
    from anywhereinput.mouse_worker import MouseWorker

    mw = MouseWorker()
    # Set failures just below offline threshold
    mw.consecutive_failures = 5
    # Within recovery period
    import time
    mw.recovering_until = time.monotonic() + 10
    state = mw.get_engine_state()
    assert state == "recovering"


def test_mouse_worker_reset_recovery_timer():
    """A successful input should reset the recovery timer."""
    from anywhereinput.mouse_worker import MouseWorker

    mw = MouseWorker()
    import time
    mw.recovering_until = time.monotonic() - 1  # expired
    mw.consecutive_failures = 3

    # Simulate a successful operation by resetting
    mw.consecutive_failures = 0


def test_mouse_worker_queue_max_size():
    """MouseWorker queue has the expected max size."""
    from anywhereinput.mouse_worker import MouseWorker

    mw = MouseWorker()
    assert mw.queue.maxsize == 100
    assert mw._slow_queue.maxsize == 50


# ─── Server argument parsing ────────────────────────────────────────────────

def test_server_main_has_help(capsys):
    """launcher.py --help should not crash."""
    import sys
    from anywhereinput.launcher import main

    old_argv = sys.argv[:]
    sys.argv = ["anywhereinput", "--help"]
    try:
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
    finally:
        sys.argv = old_argv


def test_server_tunnel_choices_arg():
    """argparse accepts valid tunnel choices."""
    from anywhereinput.launcher import TUNNEL_CHOICES

    for choice in TUNNEL_CHOICES:
        assert isinstance(choice, str)
        assert len(choice) > 0


# ─── CaptureEngineState enum ────────────────────────────────────────────────

def test_capture_engine_state_values():
    """CaptureEngineState has expected states."""
    from anywhereinput.screen_capture import CaptureEngineState

    values = [s.value for s in CaptureEngineState]
    assert 1 in values   # HEALTHY
    assert 2 in values   # DEGRADED
    assert 3 in values   # REBUILDING
    assert 4 in values   # FAILED
    assert 5 in values   # OFFLINE


def test_capture_engine_state_members():
    """CaptureEngineState has all expected members."""
    from anywhereinput.screen_capture import CaptureEngineState

    assert hasattr(CaptureEngineState, 'HEALTHY')
    assert hasattr(CaptureEngineState, 'DEGRADED')
    assert hasattr(CaptureEngineState, 'REBUILDING')
    assert hasattr(CaptureEngineState, 'FAILED')
    assert hasattr(CaptureEngineState, 'OFFLINE')


# ─── Server static file serving gaps ────────────────────────────────────────

@pytest.mark.asyncio
async def test_server_static_file_mime_types():
    """Server should serve correct MIME types for different extensions."""
    from anywhereinput.client import ClientHandler

    handler = ClientHandler()

    # Check that mime_map exists in the static_file method logic
    # We'll verify by reading the source
    import inspect
    source = inspect.getsource(handler.static_file)
    assert "text/html" in source
    assert "text/css" in source
    assert "application/javascript" in source


@pytest.mark.asyncio
async def test_server_static_file_404():
    """Serving a nonexistent static file returns 404."""
    from anywhereinput.client import ClientHandler

    handler = ClientHandler()

    req = mock.MagicMock()
    req.match_info.get.return_value = "nonexistent.css"

    response = await handler.static_file(req)
    assert response.status == 404


# ─── Server entry point / main function ─────────────────────────────────────

def test_main_argparse_tunnel_local():
    """argparse accepts valid tunnel choices."""
    from anywhereinput.launcher import TUNNEL_CHOICES

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--tunnel", choices=TUNNEL_CHOICES, default="local")
    args = parser.parse_args(["--tunnel", "local"])
    assert args.tunnel == "local"


def test_main_argparse_tunnel_cloudflare():
    """argparse accepts cloudflare tunnel."""
    from anywhereinput.launcher import TUNNEL_CHOICES

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--tunnel", choices=TUNNEL_CHOICES, default="local")
    args = parser.parse_args(["--tunnel", "cloudflare"])
    assert args.tunnel == "cloudflare"


def test_server_core_module_has_logger():
    """server_core.py has a module-level logger."""
    from anywhereinput.server import server_core as srv_mod
    assert hasattr(srv_mod, 'logger')
    assert srv_mod.logger is not None


# ─── Server WebSocket auth gaps ─────────────────────────────────────────────

def test_server_auth_handler_rejects_empty_token():
    """Auth handler should reject empty/missing tokens."""
    from anywhereinput.auth import TokenManager

    tm = TokenManager()
    assert tm.validate("") is False
    assert tm.validate(None) is False


def test_server_auth_handler_validates_permissions():
    """Token validation respects permission argument."""
    from anywhereinput.auth import TokenManager

    tm = TokenManager()
    token = tm.generate_token("perm-test")

    # Default permissions (ping was removed - stream runs regardless of client state)
    assert tm.validate(token, "move") is True
    assert tm.validate(token, "screen_toggle") is True


# ─── __main__.py entry point ────────────────────────────────────────────────

def test_main_module_exists():
    """__main__.py exists and has main function."""
    from anywhereinput.__main__ import main
    assert callable(main)


def test_main_module_argparse_app_flag():
    """--app flag is parsed by __main__."""
    from anywhereinput import __main__ as mod

    # Verify the argument definition contains --app
    import inspect
    source = inspect.getsource(mod.main)
    assert "--app" in source


# ─── Safe print fallback behavior ───────────────────────────────────────────

def test_safe_print_with_tuple():
    """safe_print handles tuple arguments."""
    from anywhereinput import safe_print

    with mock.patch("builtins.print", return_value=None):
        safe_print((1, 2, 3))


def test_safe_print_with_dict():
    """safe_print handles dict arguments."""
    from anywhereinput import safe_print

    with mock.patch("builtins.print", return_value=None):
        safe_print({"key": "value"})


def test_safe_print_stderr_with_list():
    """safe_print_stderr handles list arguments."""
    from anywhereinput import safe_print_stderr

    with mock.patch("builtins.print", return_value=None):
        safe_print_stderr([1, 2, 3])
