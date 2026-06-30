"""Screen capture engine with MSS and Pillow."""

import io
import asyncio
from typing import Optional, Tuple, List
import mss
from PIL import Image, ImageDraw
import pyautogui


class ScreenCapture:
    """Handles real-time screen capture with cursor overlay and multi-monitor support."""

    def __init__(self, fps: int = 10, quality: int = 60, scale: float = 0.5, monitor_index: int = None):
        self.fps = max(1, min(60, fps))
        self.quality = max(1, min(95, quality))
        self.scale = max(0.1, min(1.0, scale))
        self.enabled = True
        self._sct = mss.mss()
        self._monitors = self._sct.monitors  # [0] = all, [1+] = individual monitors
        self._monitor_index = monitor_index  # None = auto-track cursor
        self._current_monitor = 1 if len(self._monitors) > 1 else 0

    @property
    def monitor_count(self) -> int:
        """Return number of available monitors (excluding 'all')."""
        return len(self._monitors) - 1

    @property
    def current_monitor_index(self) -> int:
        return self._current_monitor

    @property
    def dimensions(self) -> Tuple[int, int]:
        """Return current screen dimensions."""
        mon = self._get_active_monitor()
        return (mon["width"], mon["height"])

    def _get_active_monitor(self) -> dict:
        """Get the monitor to capture from."""
        if self._monitor_index is not None:
            # Fixed monitor mode
            idx = max(1, min(self._monitor_index, len(self._monitors) - 1))
            return self._monitors[idx]

        # Auto-track cursor mode — always check cursor position
        try:
            cursor_x, cursor_y = pyautogui.position()
        except Exception:
            # Fallback to last known monitor if pyautogui fails
            return self._monitors[self._current_monitor]

        # Find the monitor containing the cursor
        for i, mon in enumerate(self._monitors[1:], start=1):
            if (mon["left"] <= cursor_x < mon["left"] + mon["width"] and
                mon["top"] <= cursor_y < mon["top"] + mon["height"]):
                self._current_monitor = i
                return mon

        # Cursor not on any known monitor — capture everything
        if len(self._monitors) > 1:
            return self._monitors[1]
        return self._monitors[0]

    def get_monitor_info(self) -> List[dict]:
        """Return info about all monitors."""
        info = []
        for i, mon in enumerate(self._monitors[1:], start=1):
            info.append({
                "index": i,
                "left": mon["left"],
                "top": mon["top"],
                "width": mon["width"],
                "height": mon["height"],
                "primary": i == 1,
            })
        return info

    def capture(self) -> Optional[bytes]:
        """Capture screen and return JPEG bytes."""
        if not self.enabled:
            return None

        try:
            mon = self._get_active_monitor()
            screenshot = self._sct.grab(mon)
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

            # Overlay cursor (relative to captured monitor)
            cursor_x, cursor_y = pyautogui.position()
            # Adjust cursor position to be relative to monitor
            rel_x = cursor_x - mon["left"]
            rel_y = cursor_y - mon["top"]

            # Only draw cursor if it's on the captured monitor
            if 0 <= rel_x < mon["width"] and 0 <= rel_y < mon["height"]:
                draw = ImageDraw.Draw(img)
                self._draw_cursor(draw, rel_x, rel_y)

            # Scale
            if self.scale != 1.0:
                new_size = (int(img.width * self.scale), int(img.height * self.scale))
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            # Compress to JPEG
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=self.quality, optimize=True)
            return buffer.getvalue()
        except Exception as e:
            print(f"[ScreenCapture] Error: {e}")
            return None

    def _draw_cursor(self, draw: ImageDraw.Draw, x: int, y: int) -> None:
        """Draw a highly visible cursor overlay."""
        size_h = 35  # Larger vertical reach for better visibility
        size_w = 25  # Horizontal reach
        # White outline cross
        draw.line([(x - size_w, y), (x + size_w, y)], fill="white", width=4)
        draw.line([(x, y - size_h), (x, y + size_h)], fill="white", width=4)
        # Red inner cross
        draw.line([(x - size_w, y), (x + size_w, y)], fill="red", width=2)
        draw.line([(x, y - size_h), (x, y + size_h)], fill="red", width=2)
        # Yellow center dot (larger)
        draw.ellipse([(x - 5, y - 5), (x + 5, y + 5)], fill="yellow", outline="red", width=2)

    def set_monitor(self, index: int = 0) -> bool:
        """Switch to a specific monitor (0 = auto-track, 1+ = fixed)."""
        if index == 0:
            self._monitor_index = None  # Auto-track
            return True
        if 1 <= index < len(self._monitors):
            self._monitor_index = index
            self._current_monitor = index
            return True
        return False

    def close(self) -> None:
        """Release resources."""
        self._sct.close()
