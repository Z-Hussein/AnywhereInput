"""Backend registry and factory."""

import platform
from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..base import ScreenCaptureBackend


_BACKEND_REGISTRY = {
    "Windows": (
        "anywhereinput.screen_capture.backends.windows",
        "PyGetWindowScreenCapture",
    ),
    "Darwin": ("anywhereinput.screen_capture.backends.macos", "QuartzScreenCapture"),
    "Linux": ("anywhereinput.screen_capture.backends.x11", "X11ScreenCapture"),
}


def get_backend_class():
    """Get the backend class for the current platform."""
    system = platform.system()
    if system not in _BACKEND_REGISTRY:
        raise RuntimeError(f"Unsupported platform: {system}")
    module_name, class_name = _BACKEND_REGISTRY[system]
    try:
        module = import_module(module_name)
    except ImportError as exc:
        raise ImportError(
            f"Screen capture backend '{module_name}' requires dependencies that are not installed: {exc}. "
            f"Install with: pip install mss Pillow pyautogui"
        ) from exc
    return getattr(module, class_name)


def create_backend(**kwargs) -> "ScreenCaptureBackend":
    """Factory function for creating platform-appropriate backend."""
    backend_cls = get_backend_class()
    return backend_cls(**kwargs)


__all__ = ["get_backend_class", "create_backend"]
