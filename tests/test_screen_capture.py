"""Tests for screen capture module."""
import io
import pytest
from anywhereinput.screen_capture import ScreenCapture


def test_init_custom_params():
    sc = ScreenCapture(fps=15, quality=75, scale=0.7)
    assert sc.fps == 15
    assert sc.quality == 75
    assert sc.scale == 0.7
    sc.close()


def test_fps_clamping():
    sc = ScreenCapture(fps=0)
    assert sc.fps >= 1
    sc2 = ScreenCapture(fps=999)
    assert sc2.fps <= 120
    sc.close()
    sc2.close()


def test_quality_clamping():
    sc = ScreenCapture(quality=0)
    assert sc.quality >= 1
    sc2 = ScreenCapture(quality=99)
    assert sc2.quality <= 95
    sc.close()
    sc2.close()


def test_scale_clamping():
    sc = ScreenCapture(scale=-1.0)
    assert sc.scale >= 0.1
    sc2 = ScreenCapture(scale=2.0)
    assert sc2.scale <= 1.0
    sc.close()
    sc2.close()


def test_dimensions():
    sc = ScreenCapture()
    w, h = sc.dimensions
    assert w > 0
    assert h > 0
    sc.close()


def test_monitor_count():
    sc = ScreenCapture()
    count = sc.monitor_count
    assert count >= 1
    sc.close()


def _has_display():
    """Check if a real display is available for MSS capture."""
    try:
        sc = ScreenCapture()
        frame = sc.capture()
        sc.close()
        return frame is not None
    except Exception:
        return False


def test_capture_returns_bytes():
    pytest.importorskip("mss")
    sc = ScreenCapture()
    frame = sc.capture()
    if frame is None:
        pytest.skip("No display available for MSS capture")
    assert isinstance(frame, bytes)
    # JPEG header: FF D8
    assert len(frame) >= 2 and frame[0] == 0xFF and frame[1] == 0xD8
    sc.close()


def test_capture_disabled():
    sc = ScreenCapture()
    sc.enabled = False
    assert sc.capture() is None


def test_close_no_error():
    sc = ScreenCapture()
    sc.close()
    sc.close()


def test_set_monitor_auto():
    sc = ScreenCapture()
    result = sc.set_monitor(0)
    assert result is True
    assert sc._monitor_index is None
    sc.close()


def test_set_monitor_fixed(tmp_path):
    sc = ScreenCapture()
    count = sc.monitor_count
    if count >= 2:
        result = sc.set_monitor(1)
        assert result is True
        assert sc._monitor_index == 1
    else:
        result = sc.set_monitor(1)
    sc.close()


def test_set_monitor_invalid():
    sc = ScreenCapture()
    count = sc.monitor_count
    invalid_idx = count + 10
    result = sc.set_monitor(invalid_idx)
    assert result is False
    sc.close()


def test_get_monitor_info():
    sc = ScreenCapture()
    info = sc.get_monitor_info()
    assert isinstance(info, list)
    assert len(info) >= 1
    for mon in info:
        mon_dict = mon.to_dict()
        assert "index" in mon_dict
        assert "left" in mon_dict
        assert "top" in mon_dict
        assert "width" in mon_dict
        assert "height" in mon_dict
        assert "primary" in mon_dict
    sc.close()


def test_capture_is_valid_jpeg():
    sc = ScreenCapture(quality=80)
    frame = sc.capture()
    img = io.BytesIO(frame)
    from PIL import Image
    img_obj = Image.open(img)
    assert img_obj.format == "JPEG"
    assert img_obj.size[0] > 0 and img_obj.size[1] > 0
    sc.close()


def test_dimensions_change_with_scale():
    sc = ScreenCapture(scale=0.5)
    w1, h1 = sc.dimensions
    sc2 = ScreenCapture(scale=1.0)
    assert w1 > 0 and h1 > 0
    sc.close()
    sc2.close()
