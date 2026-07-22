"""Base screen capture backend with shared fault-tolerance logic."""

import io
import logging
import os
import threading
import time
from abc import ABC, abstractmethod
from typing import Callable, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image, ImageDraw
    import pyautogui  # type: ignore[import-untyped]
else:
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        Image = None  # type: ignore[assignment]
        ImageDraw = None  # type: ignore[assignment]
    try:
        import pyautogui  # type: ignore[import-untyped]
    except ImportError:
        pyautogui = None

from .models import CaptureEngineState, CaptureStats, MonitorInfo
from .utils import _draw_cursor, _windows_dpi_scale

logger = logging.getLogger(__name__)


class ScreenCaptureBackend(ABC):
    """
    Abstract base class for platform-specific screen capture backends.

    All backends inherit shared fault-tolerance logic:
    - State machine (HEALTHY/DEGRADED/REBUILDING/FAILED/OFFLINE)
    - Auto-rebuild with exponential backoff
    - PIL ImageGrab fallback when primary backend fails
    - Cursor overlay drawing
    - Monitor tracking with auto-switching
    """

    # Rebuild thresholds
    MAX_CONSECUTIVE_FAILURES = 3
    REBUILD_BACKOFF_BASE = 0.5  # seconds
    REBUILD_BACKOFF_MAX = 4.0
    BLACK_FRAME_THRESHOLD = 0.95  # % of pixels identical = likely black frame

    _HEADLESS_MODE = os.environ.get("ANYWHEREINPUT_HEADLESS", "").lower() in (
        "1",
        "true",
        "yes",
    )

    def __init__(
        self,
        fps: int = 60,
        quality: int = 95,
        scale: float = 0.9,
        monitor_index: Optional[int] = None,
        on_state_change: Optional[Callable[[CaptureEngineState], None]] = None,
    ) -> None:
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

        # Capture resources
        self._current_monitor = 1
        self._fallback_mode = False
        self._handle_cross_thread_verified = False
        self._pyautogui_lock: Optional[threading.Lock] = None

        # Platform-specific init
        self._build_engine()

    # ─── Abstract Methods (implemented by each backend) ─────────────────

    @abstractmethod
    def _build_engine(self) -> bool:
        """Build or rebuild the capture pipeline. Return True on success."""
        pass

    @abstractmethod
    def _teardown(self) -> None:
        """Release all capture resources."""
        pass

    @abstractmethod
    def _validate_engine(self) -> bool:
        """Run a test capture to verify the engine works."""
        pass

    @abstractmethod
    def _capture_frame(self) -> Optional[bytes]:
        """Capture a single frame. Return JPEG bytes or None on failure."""
        pass

    @abstractmethod
    def _get_active_monitor(self) -> MonitorInfo:
        """Get the monitor to capture from (with auto-tracking)."""
        pass

    @abstractmethod
    def get_monitor_info(self) -> List[MonitorInfo]:
        """Return info about all monitors."""
        pass

    @abstractmethod
    def set_monitor(self, index: int = 0) -> bool:
        """Switch to a specific monitor (0 = auto-track)."""
        pass

    # ─── Properties ──────────────────────────────────────────────────────

    @property
    def state(self) -> CaptureEngineState:
        with self._state_lock:
            return self._state

    @state.setter
    def state(self, value: CaptureEngineState) -> None:
        changed = False
        old = None
        with self._state_lock:
            if self._state != value:
                old = self._state
                self._state = value
                changed = True
        if changed:
            logger.warning(
                f"ScreenCapture state: {old.name if old else 'None'} → {value.name}"
            )
            if self._on_state_change:
                try:
                    self._on_state_change(value)
                except Exception as e:
                    logger.warning("State change callback failed: %s", e)

    @property
    def monitor_count(self) -> int:
        monitors = getattr(self, "_monitors", None)
        if monitors:
            return max(0, len(monitors) - 1)
        return 0

    @property
    def current_monitor_index(self) -> int:
        return self._current_monitor

    @property
    def dimensions(self) -> tuple[int, int]:
        mon = self._get_active_monitor()
        return (mon.width, mon.height)

    @property
    def stats(self) -> CaptureStats:
        return self._stats

    @property
    def fps_estimate(self) -> float:
        """Get real-time FPS estimate from recent capture timestamps.
        Returns 0.0 if no frames captured in the last 5 seconds."""
        fps = self._stats.record_frame_time(time.time())
        # If we have a valid estimate, return it rounded
        if fps > 0:
            return round(fps)
        return 0.0

    # ─── Shared Fault-Tolerance Logic ────────────────────────────────────

    def _should_rebuild(self, error: Exception) -> bool:
        """Determine if an error warrants a full rebuild vs. transient retry."""
        error_msg = str(error).lower()
        rebuild_triggers = [
            "display",
            "screen",
            "monitor",
            "resolution",
            "grab",
            "mss",
            "bitmap",
            "gdi",
            "desktop",
            "session",
            "rdp",
            "disconnect",
            "access denied",
            "invalid handle",
            "device",
            "context",
            "dc",
        ]
        for trigger in rebuild_triggers:
            if trigger in error_msg:
                return True

        exception_type = type(error).__name__.lower()
        if any(
            k in exception_type
            for k in (
                "gdi",
                "displayconfig",
                "graphics",
                "pywintypes",
                "windowserror",
                "handle",
                "device not found",
            )
        ):
            return True
        if isinstance(error, OSError) and getattr(error, "winerror", None) in (
            6,
            2450,
            107375,
        ):
            return True
        if self._stats.consecutive_failures >= 2:
            return True
        return False

    def _attempt_rebuild(self) -> bool:
        """Public rebuild entry point with backoff enforcement."""
        now = time.time()
        time_since_last = now - self._last_rebuild_time
        if (
            time_since_last < self._rebuild_backoff
            and self.state != CaptureEngineState.REBUILDING
        ):
            logger.debug(
                f"Rebuild skipped: {self._rebuild_backoff - time_since_last:.1f}s remaining"
            )
            return False
        self._last_rebuild_time = now
        return self._build_engine()

    def force_rebuild(self) -> bool:
        """Force an immediate rebuild, bypassing backoff. Used on client reconnect."""
        self._last_rebuild_time = 0.0
        self._rebuild_backoff = self.REBUILD_BACKOFF_BASE
        return self._build_engine()

    def _fallback_capture(self) -> Optional[bytes]:
        """Use PIL ImageGrab when primary backend is dead. Slower but more resilient."""
        try:
            from PIL import ImageGrab

            mon = self._get_active_monitor()
            bbox = (
                mon.left,
                mon.top,
                mon.left + mon.width,
                mon.top + mon.height,
            )
            img = ImageGrab.grab(bbox=bbox)

            # Overlay cursor - serialized to avoid race with MouseWorker
            try:
                if pyautogui is not None:
                    if self._pyautogui_lock is not None:
                        with self._pyautogui_lock:
                            cpx, cpy = pyautogui.position()
                    else:
                        cpx, cpy = pyautogui.position()
                    # DPI-aware: convert physical coords to logical
                    rel_x = int((cpx - mon.left) / _windows_dpi_scale)
                    rel_y = int((cpy - mon.top) / _windows_dpi_scale)
                    if 0 <= rel_x < mon.width and 0 <= rel_y < mon.height:
                        draw = ImageDraw.Draw(img)
                        _draw_cursor(draw, rel_x, rel_y)
            except Exception as e:
                logger.debug("fallback cursor draw failed: %s", e)

            if self.scale != 1.0:
                new_size = (int(img.width * self.scale), int(img.height * self.scale))
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            buffer = io.BytesIO()
            img.save(
                buffer, format="JPEG", quality=max(20, self.quality - 20), optimize=True
            )
            return buffer.getvalue()
        except Exception as e:
            logger.error(f"Fallback capture also failed: {e}")
            return None

    # ─── Main Capture Entry Point ────────────────────────────────────────

    def capture(self) -> Optional[bytes]:
        """Capture screen with full fault tolerance. Returns JPEG bytes or None."""
        if not self.enabled:
            return None

        # If in FAILED state, try periodic rebuild
        if self.state == CaptureEngineState.FAILED:
            if self._attempt_rebuild():
                logger.info("ScreenCapture recovered from FAILED state")
            else:
                return self._fallback_capture()

        # If rebuilding, don't attempt capture
        if self.state == CaptureEngineState.REBUILDING:
            return None

        # Delegate to platform-specific capture
        return self._capture_frame()

    # ─── Lifecycle ───────────────────────────────────────────────────────

    def close(self) -> None:
        """Release all resources."""
        self.enabled = False
        self._teardown()
        self.state = CaptureEngineState.OFFLINE
        logger.info("ScreenCapture engine closed")
