"""Capture mode presets and custom mode persistence."""

import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional

log = logging.getLogger("anywhereinput.admin")

_MODES_FILE = Path(__file__).resolve().parent.parent.parent / "capture_modes.json"


@dataclass
class CaptureMode:
    name: str
    fps: int
    quality: int
    scale: float
    built_in: bool = False

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("built_in", None)
        return d


# ── Built-in presets ──────────────────────────────────────────────────────────

BUILT_IN_MODES: List[CaptureMode] = [
    CaptureMode("Balanced", fps=60, quality=70, scale=0.8, built_in=True),
    CaptureMode("Quality", fps=60, quality=90, scale=1.0, built_in=True),
    CaptureMode("Performance", fps=30, quality=55, scale=0.6, built_in=True),
    CaptureMode("Low Bandwidth", fps=15, quality=60, scale=0.5, built_in=True),
]


class CaptureModeManager:
    """Manages built-in and user-created capture modes."""

    def __init__(self, path: Optional[Path] = None):
        self._path = path or _MODES_FILE
        self._modes: List[CaptureMode] = list(BUILT_IN_MODES)
        self._load()

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def modes(self) -> List[CaptureMode]:
        return list(self._modes)

    def get(self, name: str) -> Optional[CaptureMode]:
        for m in self._modes:
            if m.name == name:
                return m
        return None

    def save_custom(self, name: str, fps: int, quality: int, scale: float) -> bool:
        """Save or overwrite a custom mode. Returns False if name is a built-in."""
        existing = self.get(name)
        if existing and existing.built_in:
            return False

        mode = CaptureMode(name=name, fps=fps, quality=quality, scale=scale)
        # Remove old entry with same name
        self._modes = [m for m in self._modes if m.name != name]
        self._modes.append(mode)
        self._persist()
        return True

    def delete(self, name: str) -> bool:
        """Delete a custom mode. Built-in modes cannot be deleted."""
        existing = self.get(name)
        if not existing or existing.built_in:
            return False
        self._modes = [m for m in self._modes if m.name != name]
        self._persist()
        return True

    def is_custom(self, name: str) -> bool:
        m = self.get(name)
        return m is not None and not m.built_in

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self):
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text())
            for d in data.get("custom_modes", []):
                mode = CaptureMode(
                    name=d["name"],
                    fps=d["fps"],
                    quality=d["quality"],
                    scale=d["scale"],
                    built_in=False,
                )
                # Don't duplicate if name collides with built-in
                if not any(m.name == mode.name for m in self._modes):
                    self._modes.append(mode)
        except Exception as e:
            log.warning("Failed to load capture modes: %s", e)

    def _persist(self):
        custom = [m.to_dict() for m in self._modes if not m.built_in]
        try:
            self._path.write_text(json.dumps({"custom_modes": custom}, indent=2))
        except Exception as e:
            log.warning("Failed to save capture modes: %s", e)
