"""Linux/X11 screen capture backend using mss."""

import io
import logging
import threading
import time
from typing import Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import mss
    from PIL import Image, ImageDraw
    import pyautogui  # type: ignore[import-untyped]
else:
    try:
        import mss
    except ImportError:
        mss = None  # type: ignore[assignment]
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        Image = None  # type: ignore[assignment]
        ImageDraw = None  # type: ignore[assignment]
    try:
        import pyautogui  # type: ignore[import-untyped]
    except ImportError:
        pyautogui = None

from ..base import ScreenCaptureBackend
from ..models import CaptureEngineState, MonitorInfo
from ..utils import _draw_cursor

logger = logging.getLogger(__name__)


class X11ScreenCapture(ScreenCaptureBackend):
    """Linux/X11 screen capture using mss (X11 backend)."""

    _sct: Any
    _sct_thread_id: Optional[int]
    _monitors: list["MonitorInfo"]

    def _build_engine(self) -> bool:
        self.state = CaptureEngineState.REBUILDING
        self._stats.rebuilds_attempted += 1
        try:
            self._teardown()
            self._sct = mss.mss()
            self._sct_thread_id = threading.get_ident()
            raw_monitors = list(self._sct.monitors)

            # Validate and normalize monitors
            valid = []
            for m in raw_monitors:
                left, top, w, h = (
                    m.get("left"),
                    m.get("top"),
                    m.get("width"),
                    m.get("height"),
                )
                if any(v is None for v in (left, top, w, h)):
                    continue
                if not isinstance(w, (int, float)) or not isinstance(h, (int, float)):
                    continue
                if w <= 0 or h <= 0:
                    continue
                assert (
                    left is not None
                    and top is not None
                    and w is not None
                    and h is not None
                )
                m["left"], m["top"], m["width"], m["height"] = (
                    int(left),
                    int(top),
                    int(w),
                    int(h),
                )
                valid.append(m)

            # Deduplicate
            seen = set()
            unique = []
            for m in valid:
                key = (m["left"], m["top"], m["width"], m["height"])
                if key not in seen and m["width"] >= 100 and m["height"] >= 100:
                    seen.add(key)
                    unique.append(m)

            self._monitors = [
                MonitorInfo(
                    i, m["left"], m["top"], m["width"], m["height"], primary=(i == 1)
                )
                for i, m in enumerate(unique)
                if unique
            ] or [MonitorInfo(0, 0, 0, 1920, 1080, primary=True)]
            self._current_monitor = 1 if len(self._monitors) > 1 else 0

            if not self._validate_engine():
                raise RuntimeError("Engine validation failed")

            self._stats.consecutive_failures = 0
            self._stats.rebuilds_succeeded += 1
            self._rebuild_backoff = self.REBUILD_BACKOFF_BASE
            self._fallback_mode = False
            self._handle_cross_thread_verified = False
            self._sct_thread_id = threading.get_ident()
            self.state = CaptureEngineState.HEALTHY
            logger.info(
                f"X11 ScreenCapture rebuilt OK: {self.monitor_count} monitor(s)"
            )
            return True
        except Exception as e:
            self._stats.last_error = f"{type(e).__name__}: {e}"
            self._stats.consecutive_failures += 1
            self._rebuild_backoff = min(
                self._rebuild_backoff * 2, self.REBUILD_BACKOFF_MAX
            )
            if self._stats.consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
                self.state = CaptureEngineState.FAILED
            else:
                self.state = CaptureEngineState.DEGRADED
            return False

    def _teardown(self) -> None:
        if hasattr(self, "_sct") and self._sct:
            try:
                self._sct.close()
            except Exception as e:
                logger.debug("mss close failed: %s", e)
            self._sct = None
        self._sct_thread_id = None
        self._monitors = []
        self._fallback_mode = False
        self._handle_cross_thread_verified = False

    def _validate_engine(self) -> bool:
        if not self._sct or not self._monitors:
            return False
        try:
            test_mon = (
                self._monitors[1] if len(self._monitors) > 1 else self._monitors[0]
            )
            screenshot = self._sct.grab(
                {
                    "left": test_mon.left,
                    "top": test_mon.top,
                    "width": test_mon.width,
                    "height": test_mon.height,
                }
            )
            if hasattr(screenshot, "raw") and len(screenshot.raw) > 0:
                sample = bytes(screenshot.raw[:4000])
                if sample.count(b"\x00") / len(sample) > self.BLACK_FRAME_THRESHOLD:
                    logger.warning("Validation detected black frame")
                    return False
            if pyautogui is not None:
                try:
                    if self._pyautogui_lock is not None:
                        with self._pyautogui_lock:
                            pyautogui.position()
                    else:
                        pyautogui.position()
                    return True
                except Exception as e:
                    logger.debug("pyautogui position check failed: %s", e)
                    return False
            return True
        except Exception as e:
            logger.debug(f"Validation failed: {e}")
            return False

    def _capture_frame(self) -> Optional[bytes]:
        if not self._sct:
            return None
        current_tid = threading.get_ident()
        if self._sct_thread_id is None:
            if not self._attempt_rebuild():
                return None
        elif (
            not self._handle_cross_thread_verified
            and self._sct_thread_id != current_tid
        ):
            if not self._attempt_rebuild():
                return None
            if self._sct is None:
                return None

        try:
            mon = self._get_active_monitor()
            if not mon.width or not mon.height:
                logger.warning("Capture target has invalid geometry")
                if not self._attempt_rebuild():
                    return self._fallback_capture()
                return None

            screenshot = self._sct.grab(
                {
                    "left": mon.left,
                    "top": mon.top,
                    "width": mon.width,
                    "height": mon.height,
                }
            )

            raw_bytes = bytes(screenshot.raw[:4000])
            is_headless = len(screenshot.raw) < 100000
            if (
                not is_headless
                and len(raw_bytes) > 0
                and raw_bytes.count(b"\x00") / len(raw_bytes)
                > self.BLACK_FRAME_THRESHOLD
            ):
                logger.warning("Post-capture detected black frame")
                self._stats.consecutive_failures += 1
                if self._should_rebuild(RuntimeError("Black frame")):
                    self._attempt_rebuild()
                return None

            img = Image.frombytes(
                "RGB", screenshot.size, screenshot.bgra, "raw", "BGRX"
            )

            try:
                if pyautogui is not None:
                    if self._pyautogui_lock is not None:
                        with self._pyautogui_lock:
                            cpx, cpy = pyautogui.position()
                    else:
                        cpx, cpy = pyautogui.position()
                    rel_x = int(cpx - mon.left)
                    rel_y = int(cpy - mon.top)
                    if 0 <= rel_x < mon.width and rel_y < mon.height:
                        draw = ImageDraw.Draw(img)
                        _draw_cursor(draw, rel_x, rel_y)
            except Exception as e:
                logger.debug("cursor drawing failed: %s", e)

            if self.scale != 1.0:
                new_size = (int(img.width * self.scale), int(img.height * self.scale))
                img = img.resize(new_size, Image.Resampling.NEAREST)

            buffer = io.BytesIO()
            img.save(
                buffer,
                format="JPEG",
                quality=self.quality,
                progressive=False,
                subsampling=1,
                optimize=False,
            )
            data = buffer.getvalue()

            self._stats.frames_captured += 1
            now = time.time()
            self._stats.last_success_time = now
            self._record_frame_time(now)
            if self._stats.consecutive_failures > 0:
                self._stats.consecutive_failures = 0
                if self.state != CaptureEngineState.HEALTHY:
                    self.state = CaptureEngineState.HEALTHY
            if self.state == CaptureEngineState.HEALTHY:
                self._handle_cross_thread_verified = True
            return data
        except Exception as e:
            self._stats.frames_failed += 1
            self._stats.consecutive_failures += 1
            self._stats.last_error = f"{type(e).__name__}: {e}"
            logger.warning(f"Capture failed: {e}")
            self._sct = None
            self._sct_thread_id = None
            if self._should_rebuild(e):
                self._attempt_rebuild()
            return None

    def _record_frame_time(self, ts: float) -> float:
        """Delegate real-time FPS tracking to CaptureStats."""
        return self._stats.record_frame_time(ts)

    def _get_active_monitor(self) -> MonitorInfo:
        if self._monitor_index is not None:
            idx = (
                max(1, min(self._monitor_index, len(self._monitors) - 1))
                if self._monitors
                else 1
            )
            return (
                self._monitors[idx]
                if idx < len(self._monitors)
                else MonitorInfo(0, 0, 0, 1920, 1080)
            )

        try:
            if pyautogui is not None:
                if self._pyautogui_lock is not None:
                    with self._pyautogui_lock:
                        cursor_x, cursor_y = pyautogui.position()
                else:
                    cursor_x, cursor_y = pyautogui.position()
            else:
                raise RuntimeError("pyautogui not available")
        except Exception as e:
            logger.debug("pyautogui position failed, using fallback: %s", e)
            if self._monitors and self._current_monitor < len(self._monitors):
                return self._monitors[self._current_monitor]
            return MonitorInfo(0, 0, 0, 1920, 1080)

        for i, mon in enumerate(self._monitors[1:], start=1):
            if (
                mon.left <= cursor_x < mon.left + mon.width
                and mon.top <= cursor_y < mon.top + mon.height
            ):
                self._current_monitor = i
                return mon

        if len(self._monitors) > 1:
            return self._monitors[1]
        if self._monitors:
            return self._monitors[0]
        return MonitorInfo(0, 0, 0, 1920, 1080)

    def get_monitor_info(self) -> List[MonitorInfo]:
        if not self._monitors and self.state != CaptureEngineState.REBUILDING:
            self._attempt_rebuild()
        return self._monitors

    def set_monitor(self, index: int = 0) -> bool:
        if index == 0:
            self._monitor_index = None
            return True
        if not self._monitors or len(self._monitors) <= max(1, index):
            if self.state != CaptureEngineState.REBUILDING:
                self._attempt_rebuild()
        if self._monitors and 1 <= index < len(self._monitors):
            self._monitor_index = index
            self._current_monitor = index
            return True
        if (
            self._attempt_rebuild()
            and self._monitors
            and 1 <= index < len(self._monitors)
        ):
            self._monitor_index = index
            self._current_monitor = index
            return True
        return False
