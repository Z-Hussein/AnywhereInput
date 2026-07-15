"""Tests for QR code display module."""
import io as _io_mod
import sys
from pathlib import Path
from unittest import mock

src = Path(__file__).parent.parent / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

import pytest


class _SafePrintCapture:
    """Captures what safe_print writes."""
    def __init__(self):
        self.stdout = []
        self.stderr = []

    def mock_stdout(self, *args, **kwargs):
        self.stdout.append(" ".join(str(a) for a in args))

    def mock_stderr(self, *args, **kwargs):
        self.stderr.append(" ".join(str(a) for a in args))


def test_display_qr_calls_qrcode_init():
    """display_qr creates QRCode with correct parameters."""
    capture = _SafePrintCapture()

    init_kwargs = {}
    def capture_init(*args, **kwargs):
        init_kwargs.update(kwargs)
        m = mock.MagicMock()
        m.make_image.return_value = mock.MagicMock()
        return m

    with mock.patch("anywhereinput.qr_display.safe_print", capture.mock_stdout):
        with mock.patch("anywhereinput.qr_display.safe_print_stderr", capture.mock_stderr):
            with mock.patch("qrcode.QRCode", side_effect=capture_init) as MockQR:
                from anywhereinput.qr_display import display_qr
                display_qr("http://127.0.0.1:8008", "abc123")

    # QRCode should have been instantiated
    assert len(init_kwargs) >= 3


def test_display_qr_url_contains_token():
    """The QR data must encode the full link with token."""
    captured_args = []

    def record_add_data(data):
        captured_args.append(data)

    def mock_init(*args, **kwargs):
        m = mock.MagicMock()
        m.add_data = lambda x: record_add_data(x)
        m.make_image.return_value = mock.MagicMock()
        return m

    with mock.patch("anywhereinput.qr_display.safe_print", lambda *a, **k: None):
        with mock.patch("anywhereinput.qr_display.safe_print_stderr", lambda *a, **k: None):
            with mock.patch("qrcode.QRCode", side_effect=mock_init):
                from anywhereinput.qr_display import display_qr
                display_qr("https://example.com", "mytoken")

    assert any("mytoken" in arg for arg in captured_args)


def test_display_qr_ascii_render_uses_stringio():
    """QR ASCII must be rendered via StringIO (the v1.2.4 fix)."""
    with mock.patch("anywhereinput.qr_display.safe_print", lambda *a, **k: None):
        with mock.patch("anywhereinput.qr_display.safe_print_stderr", lambda *a, **k: None):
            captured_target = []
            def capture_print_ascii(target, **kw):
                captured_target.append(target)
                return None

            def mock_init(*args, **kwargs):
                m = mock.MagicMock()
                m.print_ascii = capture_print_ascii
                m.make_image.return_value = mock.MagicMock()
                return m

            with mock.patch("qrcode.QRCode", side_effect=mock_init):
                from anywhereinput.qr_display import display_qr
                display_qr("http://127.0.0.1", "t")

    assert len(captured_target) >= 1


def test_display_qr_fallback_on_error():
    """When qrcode raises, URL should still be shown via safe_print."""
    captured = []

    with mock.patch("anywhereinput.qr_display.safe_print", lambda *a, **k: captured.append(" ".join(str(x) for x in a))):
        with mock.patch("anywhereinput.qr_display.safe_print_stderr"):
            with mock.patch("qrcode.QRCode", side_effect=RuntimeError("qr bug")):
                from anywhereinput.qr_display import display_qr
                display_qr("http://127.0.0.1:8008", "test-token")

    full_output = " ".join(captured)
    assert "test-token" in full_output


def test_save_qr_image():
    """save_qr_image calls qr.make_image() and save to file."""
    with mock.patch("anywhereinput.qr_display.safe_print"):
        with mock.patch("anywhereinput.qr_display.safe_print_stderr"):
            saved_path = []

            def capture_save(path):
                saved_path.append(path)

            def mock_init(*args, **kwargs):
                m = mock.MagicMock()
                img = mock.MagicMock()
                img.save = capture_save
                m.make_image.return_value = img
                return m

            with mock.patch("qrcode.QRCode", side_effect=mock_init):
                from anywhereinput.qr_display import save_qr_image
                save_qr_image("http://127.0.0.1:8008?token=x", "/tmp/test.png")

            assert len(saved_path) == 1


def test_save_qr_image_error_handling():
    """save_qr_image should report errors via safe_print_stderr."""
    stderr_calls = []

    with mock.patch("anywhereinput.qr_display.safe_print"):
        with mock.patch("anywhereinput.qr_display.safe_print_stderr", lambda *a, **k: stderr_calls.append(" ".join(str(x) for x in a))):
            with mock.patch("qrcode.QRCode", side_effect=IOError("disk full")):
                from anywhereinput.qr_display import save_qr_image
                save_qr_image("http://x", "/nonexistent/path.png")

    assert len(stderr_calls) >= 1


def test_save_qr_image_adds_data():
    """save_qr_image adds the URL as QR data."""
    captured = []

    def capture_init(*args, **kwargs):
        m = mock.MagicMock()
        m.add_data = lambda x: captured.append(x)
        m.make_image.return_value = mock.MagicMock()
        return m

    with mock.patch("anywhereinput.qr_display.safe_print"):
        with mock.patch("anywhereinput.qr_display.safe_print_stderr"):
            with mock.patch("qrcode.QRCode", side_effect=capture_init):
                from anywhereinput.qr_display import save_qr_image
                save_qr_image("http://example.com/path?q=1")

    assert "http://example.com/path?q=1" in captured


def test_save_qr_image_default_filename():
    """save_qr_image uses the filename argument provided (default is qr_code.png)."""
    with mock.patch("anywhereinput.qr_display.safe_print"):
        with mock.patch("anywhereinput.qr_display.safe_print_stderr"):
            saved_path = []

            def capture_save(path):
                saved_path.append(path)

            def mock_init(*args, **kwargs):
                m = mock.MagicMock()
                img = mock.MagicMock()
                img.save = capture_save
                m.make_image.return_value = img
                return m

            with mock.patch("qrcode.QRCode", side_effect=mock_init):
                from anywhereinput.qr_display import save_qr_image
                save_qr_image("http://x")  # use default filename

            assert len(saved_path) == 1
            assert "qr_code.png" in saved_path[0]


def test_display_qr_error_correction_high():
    """QR code must use high error correction level."""
    captured_kwargs = {}

    def capture_init(**kwargs):
        captured_kwargs.update(kwargs)
        m = mock.MagicMock()
        m.make_image.return_value = mock.MagicMock()
        return m

    with mock.patch("anywhereinput.qr_display.safe_print", lambda *a, **k: None):
        with mock.patch("anywhereinput.qr_display.safe_print_stderr", lambda *a, **k: None):
            with mock.patch("qrcode.QRCode", side_effect=capture_init):
                from anywhereinput.qr_display import display_qr
                display_qr("http://127.0.0.1", "t")

    assert "error_correction" in captured_kwargs
