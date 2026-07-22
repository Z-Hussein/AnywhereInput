"""Tests for macOS screen capture backend."""

import platform
import pytest

# Skip on non-macOS
pytestmark = pytest.mark.skipif(
    platform.system() != "Darwin",
    reason="macOS backend tests only run on macOS"
)

from anywhereinput.screen_capture.backends.macos import QuartzScreenCapture
from anywhereinput.screen_capture.models import CaptureEngineState


class TestMacOSBackend:
    """Test macOS-specific backend."""

    def test_instantiation(self):
        """Test backend can be instantiated."""
        backend = QuartzScreenCapture(fps=30, quality=80, scale=0.5)
        assert backend.monitor_count >= 0
        backend.close()

    def test_capture_returns_bytes_or_none(self):
        """Test capture returns bytes or None."""
        backend = QuartzScreenCapture(fps=10)
        result = backend.capture()
        assert result is None or isinstance(result, bytes)
        backend.close()

    def test_set_monitor(self):
        """Test monitor switching."""
        backend = QuartzScreenCapture(fps=10)

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
        backend = QuartzScreenCapture(fps=10)
        monitors = backend.get_monitor_info()
        assert isinstance(monitors, list)
        backend.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
