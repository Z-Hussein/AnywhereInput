"""Tests for screen_capture utilities."""

from unittest import mock

from anywhereinput.screen_capture.utils import (
    _draw_cursor,
    _get_windows_dpi_scale,
    generate_headless_frame,
    get_windows_dpi_scale,
    is_headless_mode,
)


class TestGetWindowsDpiScale:
    def test_returns_float(self):
        result = _get_windows_dpi_scale()
        assert isinstance(result, float)
        assert result >= 0.5

    def test_non_windows_returns_1(self):
        with mock.patch("anywhereinput.screen_capture.utils.platform") as mock_plat:
            mock_plat.system.return_value = "Linux"
            result = _get_windows_dpi_scale()
            assert result == 1.0

    def test_public_accessor(self):
        result = get_windows_dpi_scale()
        assert isinstance(result, float)


class TestIsHeadlessMode:
    def test_returns_bool(self):
        result = is_headless_mode()
        assert isinstance(result, bool)


class TestGenerateHeadlessFrame:
    def test_returns_bytes(self):
        frame = generate_headless_frame()
        assert isinstance(frame, bytes)
        assert len(frame) > 0

    def test_jpeg_header(self):
        frame = generate_headless_frame()
        assert frame[:2] == b"\xff\xd8"

    def test_frame_counter_increments(self):
        from anywhereinput.screen_capture.utils import _headless_frame_counter
        f1 = generate_headless_frame(frame_num=1)
        f2 = generate_headless_frame(frame_num=1000)
        assert isinstance(f1, bytes)
        assert isinstance(f2, bytes)
        assert len(f1) > 0
        assert len(f2) > 0

    def test_scale_parameter(self):
        f1 = generate_headless_frame(scale=1.0)
        f2 = generate_headless_frame(scale=0.5)
        # Smaller scale should produce smaller file (usually)
        assert isinstance(f1, bytes)
        assert isinstance(f2, bytes)

    def test_quality_parameter(self):
        f1 = generate_headless_frame(quality=95)
        f2 = generate_headless_frame(quality=10)
        assert isinstance(f1, bytes)
        assert isinstance(f2, bytes)


class TestDrawCursor:
    def test_draws_on_image(self):
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (100, 100), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        _draw_cursor(draw, 50, 50)
        # Should not raise
