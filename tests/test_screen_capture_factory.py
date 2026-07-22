"""Tests for screen capture factory, registry, and import completeness."""

import platform
import pytest
from unittest.mock import patch

from anywhereinput.screen_capture import (
    ScreenCapture,
    ScreenCaptureBackend,
    CaptureEngineState,
    CaptureStats,
    MonitorInfo,
    create_backend,
    get_backend_class,
)


class TestFactory:
    """Test factory auto-dispatch and registry."""

    def test_factory_returns_correct_backend(self):
        """Test factory returns platform-appropriate backend."""
        backend = create_backend(fps=10, quality=80, scale=0.5)
        system = platform.system()

        expected = {
            "Windows": "PyGetWindowScreenCapture",
            "Darwin": "QuartzScreenCapture",
            "Linux": "X11ScreenCapture",
        }.get(system)

        assert expected is not None, f"Unexpected platform: {system}"
        assert type(backend).__name__ == expected
        backend.close()

    def test_get_backend_class(self):
        """Test get_backend_class returns correct class."""
        cls = get_backend_class()
        assert cls is not None
        assert issubclass(cls, ScreenCaptureBackend)

    def test_screen_capture_proxy(self):
        """Test ScreenCapture factory returns proxy with delegation."""
        sc = ScreenCapture(fps=10, quality=80, scale=0.5)

        # Test proxy has all expected attributes (delegated via __getattr__)
        assert hasattr(sc, 'capture')
        assert hasattr(sc, 'state')
        assert hasattr(sc, 'monitor_count')
        assert hasattr(sc, 'dimensions')
        assert hasattr(sc, 'set_monitor')
        assert hasattr(sc, 'get_monitor_info')
        assert hasattr(sc, 'force_rebuild')
        assert hasattr(sc, 'close')

        # Test attribute delegation (proxy forwards to backend)
        sc.fps = 30
        assert sc._backend.fps == 30

        sc.close()

    def test_unsupported_platform_raises(self):
        """Test unsupported platform raises RuntimeError."""
        with patch('platform.system', return_value='UnknownOS'):
            with pytest.raises(RuntimeError, match="Unsupported platform"):
                get_backend_class()

    def test_backend_registry(self):
        """Test backend registry has expected entries."""
        from anywhereinput.screen_capture.backends import _BACKEND_REGISTRY

        assert "Windows" in _BACKEND_REGISTRY
        assert "Darwin" in _BACKEND_REGISTRY
        assert "Linux" in _BACKEND_REGISTRY


class TestImports:
    """Test all exports are importable and backwards-compatible."""

    def test_import_all_exports(self):
        """Test all __all__ exports are importable."""
        from anywhereinput.screen_capture import (
            CaptureEngineState,
            CaptureStats,
            MonitorInfo,
            ScreenCaptureBackend,
            ScreenCapture,
            create_backend,
            get_backend_class,
        )
        assert CaptureEngineState
        assert CaptureStats
        assert MonitorInfo
        assert ScreenCaptureBackend
        assert ScreenCapture
        assert create_backend
        assert get_backend_class

    def test_backwards_compatibility(self):
        """Test old import style still works."""
        sc = ScreenCapture(fps=10)
        assert hasattr(sc, 'capture')
        assert hasattr(sc, 'state')
        sc.close()

    def test_capture_in_headless(self):
        """Test capture in headless environment returns bytes or None."""
        sc = ScreenCapture(fps=10)
        result = sc.capture()
        assert result is None or isinstance(result, bytes)
        sc.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
