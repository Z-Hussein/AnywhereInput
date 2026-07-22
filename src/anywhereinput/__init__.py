"""
AnywhereInput - Remote control your PC from any browser.

Screen streaming, pixel-perfect touch mapping, keyboard input, and mouse control.
Zero-config tunnel support: Cloudflare, Tailscale, Pinggy, Zrok2.
"""

import sys as _sys  # noqa: F401 — used by run_admin_app
import logging
from pathlib import Path

try:
    from importlib.metadata import version as _importlib_version

    __version__ = _importlib_version("anywhereinput")
except Exception as e:
    logger = logging.getLogger(__name__)
    logger.debug("importlib.metadata version lookup failed: %s", e)
    # Fallback: read from pyproject.toml (works in editable/dev mode)
    try:
        _pyproject = Path(__file__).parent.parent.parent / "pyproject.toml"
        if _pyproject.exists():
            for line in _pyproject.read_text().splitlines():
                if line.strip().startswith("version"):
                    __version__ = line.split("=")[1].strip().strip('"').strip("'")
                    break
            else:
                __version__ = "0.0.0-dev"
        else:
            __version__ = "0.0.0-dev"
    except Exception as e:
        logger.debug("pyproject.toml version lookup failed: %s", e)
        __version__ = "0.0.0-dev"

__author__ = "Z-Hussein"
__license__ = "MIT"

# Expose safe_print first (before server imports)
from ._safe_print import safe_print, safe_print_stderr  # noqa: F401 — public API

# Lazy server imports — avoids requiring aiohttp at package-import time.
# Tests can import auth/screen_capture/logging without aiohttp installed.
_server_names = (
    "AnywhereInputServer",
    "HTTPHandlers",
    "WebSocketHandler",
    "MessageHandler",
    "BroadcastManager",
    "ClientManager",
    "ServerLifecycle",
    "TokenAPI",
    "RequestAPI",
    "main",
)


def __getattr__(name: str):
    if name in _server_names:
        # First access triggers the eager import (with clear error if aiohttp missing)
        from . import server

        return getattr(server, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# Keep __all__ for backward compat (e.g. linters/IDEs that scan it)
__all__ = [
    "__version__",
    "__author__",
    "__license__",
    "safe_print",
    "safe_print_stderr",
] + list(_server_names)
