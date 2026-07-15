"""Backward-compatibility shim - all logic lives in submodules."""

import logging

from anywhereinput import safe_print  # noqa: F401

from .server_core import AnywhereInputServer  # noqa: F401
from .mouse_worker import MouseWorker, _pyautogui_lock  # noqa: F401
from .launcher import main, TUNNEL_CHOICES  # noqa: F401

logger = logging.getLogger(__name__)
