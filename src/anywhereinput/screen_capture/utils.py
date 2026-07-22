"""Utilities for screen capture backends."""

import io
import logging
import os
import platform
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import ctypes
    from PIL import Image, ImageDraw
else:
    import ctypes

    try:
        from PIL import Image, ImageDraw
    except ImportError:
        Image = None  # type: ignore[assignment]
        ImageDraw = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


def _get_windows_dpi_scale() -> float:
    """Return the Windows DPI scaling factor, or 1.0 on non-Windows / failure."""
    try:
        if platform.system() != "Windows":
            return 1.0
    except Exception as e:
        logger.debug("platform check failed: %s", e)
        return 1.0
    try:
        shcore = ctypes.windll.shcore  # type: ignore[attr-defined]
        dpi = shcore.GetDpiForSystem()
        if dpi is not None and 96 <= dpi < 960:
            return max(dpi / 96.0, 0.5)
    except Exception as e:
        logger.debug("GetDpiForSystem failed: %s", e)
    try:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        hwnd = user32.GetDesktopWindow()
        hdc = user32.GetDC(hwnd)
        dpi = user32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX = 88
        user32.ReleaseDC(hwnd, hdc)
        if dpi is not None and 96 <= dpi < 960:
            return max(dpi / 96.0, 0.5)
    except Exception as e:
        logger.debug("GetDeviceCaps failed: %s", e)
    return 1.0


_windows_dpi_scale: float = _get_windows_dpi_scale()


def _draw_cursor(draw: "ImageDraw.ImageDraw", x: int, y: int) -> None:
    """Draw a highly visible cursor overlay."""
    size_h = 35
    size_w = 25
    draw.line([(x - size_w, y), (x + size_w, y)], fill="white", width=4)
    draw.line([(x, y - size_h), (x, y + size_h)], fill="white", width=4)
    draw.line([(x - size_w, y), (x + size_w, y)], fill="red", width=2)
    draw.line([(x, y - size_h), (x, y + size_h)], fill="red", width=2)
    draw.ellipse(
        [(x - 5, y - 5), (x + 5, y + 5)], fill="yellow", outline="red", width=2
    )


_HEADLESS_MODE = os.environ.get("ANYWHEREINPUT_HEADLESS", "").lower() in (
    "1",
    "true",
    "yes",
)

_headless_frame_counter: int = 0


def generate_headless_frame(
    quality: int = 95,
    scale: float = 1.0,
    frame_num: Optional[int] = None,
) -> bytes:
    """Generate a test pattern frame for headless environments."""
    global _headless_frame_counter
    if frame_num is None:
        _headless_frame_counter += 1
        frame_num = _headless_frame_counter

    if not hasattr(Image, "new"):
        # Minimal valid JPEG for test mocks
        return b"\xff\xd8\xff\xe0" + b"\x00" * 20

    img = Image.new("RGB", (1920, 1080), (20, 20, 40))
    draw = ImageDraw.Draw(img)

    # Draw grid pattern
    for x in range(0, 1920, 50):
        draw.line([(x, 0), (x, 1080)], fill=(40, 40, 60), width=1)
    for y in range(0, 1080, 50):
        draw.line([(0, y), (1920, y)], fill=(40, 40, 60), width=1)

    # Draw moving indicator
    cx = (frame_num * 10) % 1920
    cy = 540
    draw.ellipse(
        [cx - 20, cy - 20, cx + 20, cy + 20],
        fill=(0, 200, 100),
        outline=(0, 255, 150),
        width=3,
    )

    # Draw text
    try:
        draw.text(
            (20, 20),
            f"AnywhereInput Headless Mode - Frame {frame_num}",
            fill=(200, 200, 200),
        )
        draw.text((20, 50), "Resolution: 1920x1080", fill=(150, 150, 150))
        draw.text((20, 80), "Connect a display for live capture", fill=(100, 100, 150))
    except Exception as e:
        logger.debug("headless text draw failed: %s", e)

    # Scale if needed
    if scale != 1.0:
        new_size = (int(img.width * scale), int(img.height * scale))
        img = img.resize(new_size, Image.Resampling.NEAREST)

    buffer = io.BytesIO()
    img.save(
        buffer,
        format="JPEG",
        quality=quality,
        optimize=False,
        progressive=False,
    )
    return buffer.getvalue()


def get_windows_dpi_scale() -> float:
    """Public accessor for Windows DPI scale."""
    return _windows_dpi_scale


def is_headless_mode() -> bool:
    """Check if running in headless mode."""
    return _HEADLESS_MODE
