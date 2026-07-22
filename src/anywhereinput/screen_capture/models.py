"""Data models for screen capture backends."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional


class CaptureEngineState(Enum):
    HEALTHY = auto()
    DEGRADED = auto()  # Working but reduced quality/fallback
    REBUILDING = auto()  # Actively rebuilding
    FAILED = auto()  # Multiple rebuild failures, using fallback
    OFFLINE = auto()  # Permanently failed, not attempting


@dataclass
class CaptureStats:
    frames_captured: int = 0
    frames_failed: int = 0
    rebuilds_attempted: int = 0
    rebuilds_succeeded: int = 0
    last_success_time: float = 0.0
    last_error: Optional[str] = None
    consecutive_failures: int = 0
    # Real-time FPS tracking (exponential moving average)
    _fps_frame_times: list = None  # mutable default; set lazily

    def _ensure_fps_buffer(self):
        if self._fps_frame_times is None:
            self._fps_frame_times = []

    def record_frame_time(self, timestamp: float) -> float:
        """Record a frame capture timestamp and return current FPS estimate.
        Uses exponential moving average with recent 5 seconds of data."""
        self._ensure_fps_buffer()
        self._fps_frame_times.append(timestamp)
        # Prune old timestamps
        cutoff = timestamp - 5.0
        self._fps_frame_times = [t for t in self._fps_frame_times if t > cutoff]
        if len(self._fps_frame_times) >= 2:
            duration = self._fps_frame_times[-1] - self._fps_frame_times[0]
            if duration > 0:
                return len(self._fps_frame_times) / duration
        return 0.0


class MonitorInfo:
    """Platform-agnostic monitor information."""

    def __init__(
        self,
        index: int,
        left: int,
        top: int,
        width: int,
        height: int,
        primary: bool = False,
    ):
        self.index = index
        self.left = left
        self.top = top
        self.width = width
        self.height = height
        self.primary = primary

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "left": self.left,
            "top": self.top,
            "width": self.width,
            "height": self.height,
            "primary": self.primary,
        }

    def __repr__(self) -> str:
        return (
            f"MonitorInfo(index={self.index}, left={self.left}, top={self.top}, "
            f"width={self.width}, height={self.height}, primary={self.primary})"
        )
