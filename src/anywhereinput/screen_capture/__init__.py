"""Screen capture package - cross-platform screen streaming."""

from .models import CaptureEngineState, CaptureStats, MonitorInfo
from .base import ScreenCaptureBackend
from .backends import create_backend, get_backend_class


class _ScreenCaptureProxy:
    """Proxy that delegates all attribute access to the backend instance."""

    __slots__ = ("_backend",)

    def __init__(self, backend):
        object.__setattr__(self, "_backend", backend)

    def __getattr__(self, name):
        return getattr(self._backend, name)

    def __setattr__(self, name, value):
        if name == "_backend":
            object.__setattr__(self, name, value)
        else:
            setattr(self._backend, name, value)

    def __delattr__(self, name):
        if name == "_backend":
            object.__delattr__(self, name)
        else:
            delattr(self._backend, name)


class ScreenCapture:
    """
    Drop-in replacement for original ScreenCapture class.

    Factory that auto-dispatches to the correct platform backend:
    - Windows: PyGetWindowScreenCapture (mss + pygetwindow)
    - macOS: QuartzScreenCapture (mss via CGDisplayStream)
    - Linux/BSD: X11ScreenCapture (mss X11 backend)
    """

    def __new__(cls, *args, **kwargs):
        try:
            backend = create_backend(*args, **kwargs)
        except ImportError as exc:
            raise RuntimeError(
                f"Screen capture is not available: {exc}. "
                "Install required dependencies with: pip install mss Pillow pyautogui"
            ) from exc
        return _ScreenCaptureProxy(backend)


__all__ = [
    "CaptureEngineState",
    "CaptureStats",
    "MonitorInfo",
    "ScreenCaptureBackend",
    "ScreenCapture",
    "create_backend",
    "get_backend_class",
]
