"""Screen capture engine with MSS and Pillow — with auto-rebuild recovery."""

import io
import asyncio
import logging
import threading
import time
import traceback
from typing import Optional, Tuple, List, Callable
from enum import Enum, auto
from dataclasses import dataclass

import mss
from PIL import Image, ImageDraw
import pyautogui

logger = logging.getLogger(__name__)


class CaptureEngineState(Enum):
    HEALTHY = auto()
    DEGRADED = auto()      # Working but reduced quality/fallback
    REBUILDING = auto()    # Actively rebuilding
    FAILED = auto()        # Multiple rebuild failures, using fallback
    OFFLINE = auto()       # Permanently failed, not attempting


@dataclass
class CaptureStats:
    frames_captured: int = 0
    frames_failed: int = 0
    rebuilds_attempted: int = 0
    rebuilds_succeeded: int = 0
    last_success_time: float = 0.0
    last_error: Optional[str] = None
    consecutive_failures: int = 0


class ScreenCaptureEngine:
    """
    Hardened screen capture with automatic fault detection and rebuild.
    
    Rebuild triggers:
    - mss.grab() raises (display disconnected, GPU reset, session lock)
    - pyautogui.position() raises (input hooks lost)
    - Monitor configuration changes (resolution change, monitor disconnect)
    - Black/empty frames (indicates capture pipeline failure)
    """

    # Rebuild thresholds
    MAX_CONSECUTIVE_FAILURES = 3
    REBUILD_BACKOFF_BASE = 0.5  # seconds
    REBUILD_BACKOFF_MAX = 8.0
    BLACK_FRAME_THRESHOLD = 0.98  # % of pixels identical = likely black frame

    def __init__(
        self,
        fps: int = 10,
        quality: int = 60,
        scale: float = 0.5,
        monitor_index: int = None,
        on_state_change: Optional[Callable[[CaptureEngineState], None]] = None,
    ):
        self.fps = max(1, min(120, fps))
        self.quality = max(1, min(95, quality))
        self.scale = max(0.1, min(1.0, scale))
        self.enabled = True
        self._monitor_index = monitor_index
        self._on_state_change = on_state_change

        # Engine state
        self._state = CaptureEngineState.HEALTHY
        self._state_lock = threading.Lock()
        self._stats = CaptureStats()
        self._rebuild_backoff = self.REBUILD_BACKOFF_BASE
        self._last_rebuild_time = 0.0

        # The actual capture resources
        self._sct: Optional[mss.mss] = None
        self._sct_thread_id: Optional[int] = None
        self._monitors: List[dict] = []
        self._current_monitor = 1

        # Fallback: when mss is dead, try PIL ImageGrab
        self._fallback_mode = False

        # Initialize
        self._build_engine()

    # ─── Properties ──────────────────────────────────────────────────────

    @property
    def state(self) -> CaptureEngineState:
        with self._state_lock:
            return self._state

    @state.setter
    def state(self, value: CaptureEngineState):
        changed = False
        old = None
        with self._state_lock:
            if self._state != value:
                old = self._state
                self._state = value
                changed = True

        if changed:
            logger.warning(f"ScreenCapture state: {old.name} → {value.name}")
            if self._on_state_change:
                try:
                    self._on_state_change(value)
                except Exception:
                    pass

    @property
    def monitor_count(self) -> int:
        return max(0, len(self._monitors) - 1)

    @property
    def current_monitor_index(self) -> int:
        return self._current_monitor

    @property
    def dimensions(self) -> Tuple[int, int]:
        mon = self._get_active_monitor()
        return (mon.get("width", 1920), mon.get("height", 1080))

    @property
    def stats(self) -> CaptureStats:
        return self._stats

    # ─── Core Build/Rebuild ──────────────────────────────────────────────

    def _build_engine(self) -> bool:
        """
        Build or rebuild the entire capture pipeline from scratch.
        This is the "auto-rebuild path" — called after faults or on init.
        """
        self.state = CaptureEngineState.REBUILDING
        self._stats.rebuilds_attempted += 1

        try:
            # 1. Tear down old resources
            self._teardown()

            # 2. Re-initialize mss (this re-detects all monitors)
            self._sct = mss.mss()
            self._sct_thread_id = threading.get_ident()
            self._monitors = list(self._sct.monitors)  # Copy to avoid reference issues
            self._current_monitor = 1 if len(self._monitors) > 1 else 0

            # 3. Validate with a test capture
            if not self._validate_engine():
                raise RuntimeError("Engine validation failed: test capture returned invalid data")

            # 4. Reset failure tracking
            self._stats.consecutive_failures = 0
            self._stats.rebuilds_succeeded += 1
            self._rebuild_backoff = self.REBUILD_BACKOFF_BASE
            self._fallback_mode = False
            self.state = CaptureEngineState.HEALTHY

            logger.info(
                f"ScreenCapture rebuilt OK: {self.monitor_count} monitor(s), "
                f"primary={self.dimensions[0]}x{self.dimensions[1]}"
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
                logger.error(f"ScreenCapture FAILED after {self._stats.consecutive_failures} rebuild attempts")
            else:
                self.state = CaptureEngineState.DEGRADED
                logger.warning(f"ScreenCapture rebuild failed, backing off {self._rebuild_backoff}s: {e}")

            return False

    def _teardown(self):
        """Safely release all capture resources."""
        if self._sct:
            try:
                self._sct.close()
            except Exception:
                pass
            self._sct = None
        self._sct_thread_id = None
        self._monitors = []
        self._fallback_mode = False

    def _validate_engine(self) -> bool:
        """Run a test capture to verify the engine is actually working."""
        if not self._sct or not self._monitors:
            return False

        try:
            test_mon = self._monitors[1] if len(self._monitors) > 1 else self._monitors[0]
            screenshot = self._sct.grab(test_mon)

            # Check for black/empty frame (common after GPU reset)
            if hasattr(screenshot, 'raw') and len(screenshot.raw) > 0:
                # Quick check: if all first 1000 pixels are zero, likely black
                sample = bytes(screenshot.raw[:4000])  # 1000 RGBA pixels
                if sample.count(b'\x00') / len(sample) > self.BLACK_FRAME_THRESHOLD:
                    logger.warning("Validation detected black frame — possible GPU reset")
                    return False

            # Verify pyautogui can read position
            _ = pyautogui.position()

            return True

        except Exception as e:
            logger.debug(f"Validation failed: {e}")
            return False

    def _should_rebuild(self, error: Exception) -> bool:
        """Determine if an error warrants a full rebuild vs. transient retry."""
        error_msg = str(error).lower()

        rebuild_triggers = [
            'display', 'screen', 'monitor', 'resolution',
            'grab', 'mss', 'bitmap', 'gdi', 'desktop',
            'session', 'rdp', 'disconnect', 'access denied',
            'invalid handle', 'device', 'context', 'dc',
        ]

        for trigger in rebuild_triggers:
            if trigger in error_msg:
                return True

        # Also rebuild on repeated failures even if error message is generic
        if self._stats.consecutive_failures >= 2:
            return True

        return False

    def _attempt_rebuild(self) -> bool:
        """Public rebuild entry point with backoff enforcement."""
        now = time.time()
        time_since_last = now - self._last_rebuild_time

        if time_since_last < self._rebuild_backoff and self.state != CaptureEngineState.REBUILDING:
            logger.debug(f"Rebuild skipped: {self._rebuild_backoff - time_since_last:.1f}s remaining")
            return False

        self._last_rebuild_time = now
        return self._build_engine()

    # ─── Fallback Capture (PIL ImageGrab) ────────────────────────────────

    def _fallback_capture(self) -> Optional[bytes]:
        """Use PIL ImageGrab when mss is dead. Slower but more resilient."""
        try:
            from PIL import ImageGrab

            # Get the active monitor region
            mon = self._get_active_monitor()
            bbox = (
                mon.get("left", 0),
                mon.get("top", 0),
                mon.get("left", 0) + mon.get("width", 1920),
                mon.get("top", 0) + mon.get("height", 1080),
            )

            img = ImageGrab.grab(bbox=bbox)

            # Overlay cursor
            try:
                cursor_x, cursor_y = pyautogui.position()
                rel_x = cursor_x - mon.get("left", 0)
                rel_y = cursor_y - mon.get("top", 0)
                if 0 <= rel_x < mon.get("width", 1920) and 0 <= rel_y < mon.get("height", 1080):
                    draw = ImageDraw.Draw(img)
                    self._draw_cursor(draw, rel_x, rel_y)
            except Exception:
                pass

            # Scale
            if self.scale != 1.0:
                new_size = (int(img.width * self.scale), int(img.height * self.scale))
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=max(20, self.quality - 20), optimize=True)
            return buffer.getvalue()

        except Exception as e:
            logger.error(f"Fallback capture also failed: {e}")
            return None

    # ─── Monitor Detection ───────────────────────────────────────────────

    def _get_active_monitor(self) -> dict:
        """Get the monitor to capture from, with safe fallbacks."""
        if self._monitor_index is not None:
            idx = max(1, min(self._monitor_index, len(self._monitors) - 1)) if self._monitors else 1
            return self._monitors[idx] if idx < len(self._monitors) else {
                "left": 0, "top": 0, "width": 1920, "height": 1080,
            }

        # Auto-track cursor
        try:
            cursor_x, cursor_y = pyautogui.position()
        except Exception:
            # pyautogui also failed — return last known or primary
            if self._monitors and self._current_monitor < len(self._monitors):
                return self._monitors[self._current_monitor]
            return {"left": 0, "top": 0, "width": 1920, "height": 1080}

        # Find monitor containing cursor
        for i, mon in enumerate(self._monitors[1:], start=1):
            if (mon.get("left", 0) <= cursor_x < mon.get("left", 0) + mon.get("width", 0) and
                mon.get("top", 0) <= cursor_y < mon.get("top", 0) + mon.get("height", 0)):
                self._current_monitor = i
                return mon

        # Fallback to primary
        if len(self._monitors) > 1:
            return self._monitors[1]
        if self._monitors:
            return self._monitors[0]
        return {"left": 0, "top": 0, "width": 1920, "height": 1080}

    def get_monitor_info(self) -> List[dict]:
        """Return info about all monitors, rebuilding if list is stale."""
        if not self._monitors and self.state != CaptureEngineState.REBUILDING:
            self._attempt_rebuild()

        info = []
        for i, mon in enumerate(self._monitors[1:], start=1):
            info.append({
                "index": i,
                "left": mon.get("left", 0),
                "top": mon.get("top", 0),
                "width": mon.get("width", 1920),
                "height": mon.get("height", 1080),
                "primary": i == 1,
            })
        return info

    # ─── Main Capture ────────────────────────────────────────────────────

    def capture(self) -> Optional[bytes]:
        """
        Capture screen with full fault tolerance.
        Returns JPEG bytes, or None if completely unrecoverable.
        """
        if not self.enabled:
            return None

        # If in FAILED state, try periodic rebuild
        if self.state == CaptureEngineState.FAILED:
            if self._attempt_rebuild():
                logger.info("ScreenCapture recovered from FAILED state")
            else:
                # Use fallback
                return self._fallback_capture()

        # If rebuilding, don't attempt capture
        if self.state == CaptureEngineState.REBUILDING:
            return None

        # MSS internals are thread-affine on some platforms. If the capture
        # handle was created in a different thread (for example, startup thread
        # vs executor worker thread), rebuild before first grab to prevent
        # '_thread._local' display attribute errors.
        current_tid = threading.get_ident()
        if self._sct is not None and self._sct_thread_id is not None and self._sct_thread_id != current_tid:
            logger.info(
                "Capture handle thread changed (%s -> %s), rebuilding engine",
                self._sct_thread_id,
                current_tid,
            )
            if not self._attempt_rebuild():
                self._fallback_mode = True
                return self._fallback_capture()

        try:
            mon = self._get_active_monitor()
            screenshot = self._sct.grab(mon)
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

            # Overlay cursor
            try:
                cursor_x, cursor_y = pyautogui.position()
                rel_x = cursor_x - mon.get("left", 0)
                rel_y = cursor_y - mon.get("top", 0)
                if 0 <= rel_x < mon.get("width", 1920) and 0 <= rel_y < mon.get("height", 1080):
                    draw = ImageDraw.Draw(img)
                    self._draw_cursor(draw, rel_x, rel_y)
            except Exception:
                pass  # Cursor overlay failed, but image is still valid

            # Scale
            if self.scale != 1.0:
                new_size = (int(img.width * self.scale), int(img.height * self.scale))
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            # Compress
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=self.quality, optimize=True)
            data = buffer.getvalue()

            # Success tracking
            self._stats.frames_captured += 1
            self._stats.last_success_time = time.time()
            if self._stats.consecutive_failures > 0:
                self._stats.consecutive_failures = 0
                if self.state != CaptureEngineState.HEALTHY:
                    self.state = CaptureEngineState.HEALTHY

            return data

        except Exception as e:
            self._stats.frames_failed += 1
            self._stats.consecutive_failures += 1
            self._stats.last_error = f"{type(e).__name__}: {e}"

            logger.warning(
                f"Capture failed ({self._stats.consecutive_failures}/"
                f"{self.MAX_CONSECUTIVE_FAILURES}): {e}"
            )

            # Decide: rebuild or just return None?
            if self._should_rebuild(e):
                logger.info("Triggering capture engine rebuild")
                if self._attempt_rebuild():
                    # Try one more capture immediately after rebuild
                    return self._retry_capture_once()
                else:
                    # Rebuild failed — enter fallback mode
                    self._fallback_mode = True
                    return self._fallback_capture()

            # Transient error, just return None this frame
            return None

    def _retry_capture_once(self) -> Optional[bytes]:
        """Single retry after successful rebuild."""
        try:
            mon = self._get_active_monitor()
            screenshot = self._sct.grab(mon)
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            if self.scale != 1.0:
                new_size = (int(img.width * self.scale), int(img.height * self.scale))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=self.quality, optimize=True)
            self._stats.frames_captured += 1
            return buffer.getvalue()
        except Exception:
            return None

    def _draw_cursor(self, draw: ImageDraw.Draw, x: int, y: int) -> None:
        """Draw a highly visible cursor overlay."""
        size_h = 35
        size_w = 25
        draw.line([(x - size_w, y), (x + size_w, y)], fill="white", width=4)
        draw.line([(x, y - size_h), (x, y + size_h)], fill="white", width=4)
        draw.line([(x - size_w, y), (x + size_w, y)], fill="red", width=2)
        draw.line([(x, y - size_h), (x, y + size_h)], fill="red", width=2)
        draw.ellipse([(x - 5, y - 5), (x + 5, y + 5)], fill="yellow", outline="red", width=2)

    # ─── Monitor Switching ───────────────────────────────────────────────

    def set_monitor(self, index: int = 0) -> bool:
        """Switch to a specific monitor (0 = auto-track, 1+ = fixed)."""
        if index == 0:
            self._monitor_index = None
            return True
        if self._monitors and 1 <= index < len(self._monitors):
            self._monitor_index = index
            self._current_monitor = index
            return True
        # Monitor not in current list — try rebuild
        if self._attempt_rebuild():
            if 1 <= index < len(self._monitors):
                self._monitor_index = index
                self._current_monitor = index
                return True
        return False

    # ─── Lifecycle ───────────────────────────────────────────────────────

    def close(self) -> None:
        """Release all resources."""
        self.enabled = False
        self._teardown()
        self.state = CaptureEngineState.OFFLINE
        logger.info("ScreenCapture engine closed")


# ─── Backward-compatible alias ─────────────────────────────────────────

class ScreenCapture(ScreenCaptureEngine):
    """
    Drop-in replacement for the original ScreenCapture class.
    All original methods preserved, new recovery features added transparently.
    """
    pass
