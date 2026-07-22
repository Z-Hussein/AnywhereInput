"""Tests for Linux/X11 screen capture backend."""

import platform
import pytest

# Skip on non-Linux
pytestmark = pytest.mark.skipif(
    platform.system() != "Linux",
    reason="X11 backend tests only run on Linux"
)

from anywhereinput.screen_capture.backends.x11 import X11ScreenCapture
from anywhereinput.screen_capture.models import CaptureEngineState


class TestX11Backend:
    """Test X11/Linux-specific backend."""

    def test_instantiation(self):
        """Test backend can be instantiated."""
        backend = X11ScreenCapture(fps=30, quality=80, scale=0.5)
        assert backend.monitor_count >= 0
        backend.close()

    def test_capture_returns_bytes_or_none(self):
        """Test capture returns bytes or None."""
        backend = X11ScreenCapture(fps=10)
        result = backend.capture()
        assert result is None or isinstance(result, bytes)
        backend.close()

    def test_set_monitor(self):
        """Test monitor switching."""
        backend = X11ScreenCapture(fps=10)

        # Test auto-track (index 0)
        assert backend.set_monitor(0) is True
        assert backend._monitor_index is None

        # Test specific monitor
        if backend.monitor_count > 0:
            result = backend.set_monitor(1)
            assert isinstance(result, bool)

        backend.close()

    def test_get_monitor_info(self):
        """Test monitor info retrieval."""
        backend = X11ScreenCapture(fps=10)
        monitors = backend.get_monitor_info()
        assert isinstance(monitors, list)
        backend.close()

    def test_state_transitions(self):
        """Test state machine transitions."""
        backend = X11ScreenCapture(fps=10)

        assert backend.state == CaptureEngineState.HEALTHY

        backend.state = CaptureEngineState.DEGRADED
        assert backend.state == CaptureEngineState.DEGRADED

        backend.state = CaptureEngineState.FAILED
        assert backend.state == CaptureEngineState.FAILED

        backend.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
