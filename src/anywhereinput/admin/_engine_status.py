"""EngineStatusWidget - colored status banner with useful messages."""

import json
import logging

from anywhereinput._constants import DEFAULT_PORT
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QFont

log = logging.getLogger("anywhereinput.admin")

_STATUS_CONFIG = {
    "healthy": {
        "icon": "🟢",
        "title": "Server Running",
        "bg": "#14532d",
        "border": "#166534",
        "text": "#dcfce7",
        "sub": "Ready to accept browser connections.",
    },
    "degraded": {
        "icon": "🟠",
        "title": "Degraded",
        "bg": "#451a03",
        "border": "#92400e",
        "text": "#fef3c7",
        "sub": "Engine running with reduced performance.",
    },
    "recovering": {
        "icon": "🟠",
        "title": "Starting...",
        "bg": "#451a03",
        "border": "#92400e",
        "text": "#fef3c7",
        "sub": "Waiting for server to initialize.",
    },
    "offline": {
        "icon": "🔴",
        "title": "Offline",
        "bg": "#450a0a",
        "border": "#991b1b",
        "text": "#fecaca",
        "sub": "Server is not running.",
    },
    "error": {
        "icon": "🔴",
        "title": "Error",
        "bg": "#450a0a",
        "border": "#991b1b",
        "text": "#fecaca",
        "sub": "An error occurred.",
    },
    "unknown": {
        "icon": "⚪",
        "title": "Unknown",
        "bg": "#1e293b",
        "border": "#334155",
        "text": "#94a3b8",
        "sub": "Checking status...",
    },
}


class EngineStatusWidget(QWidget):
    """Colored status banner showing server state and a helpful message."""

    def __init__(self, port: int = DEFAULT_PORT, parent=None):
        super().__init__(parent)
        self._port = port
        self._state = "unknown"
        self._timer: QTimer | None = None
        self._custom_sub = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._banner = QWidget()
        banner_layout = QHBoxLayout(self._banner)
        banner_layout.setContentsMargins(10, 8, 10, 8)
        banner_layout.setSpacing(8)

        self._icon_lbl = QLabel("⚪")
        self._icon_lbl.setFont(QFont("Sans", 16))
        banner_layout.addWidget(self._icon_lbl)

        text_col = QVBoxLayout()
        text_col.setSpacing(0)

        self._title_lbl = QLabel("Unknown")
        self._title_lbl.setFont(QFont("Sans", 11, QFont.Weight.Bold))
        text_col.addWidget(self._title_lbl)

        self._sub_lbl = QLabel("Checking status...")
        self._sub_lbl.setFont(QFont("Sans", 9))
        text_col.addWidget(self._sub_lbl)

        banner_layout.addLayout(text_col, 1)
        layout.addWidget(self._banner)

        self._apply_style("unknown")

    def _apply_style(self, state: str):
        cfg = _STATUS_CONFIG.get(state, _STATUS_CONFIG["unknown"])
        self._banner.setStyleSheet(
            f"QWidget {{"
            f"  background: {cfg['bg']};"
            f"  border: 1px solid {cfg['border']};"
            f"  border-radius: 6px;"
            f"}}"
        )
        self._title_lbl.setStyleSheet(f"color: {cfg['text']}; background: transparent;")
        self._sub_lbl.setStyleSheet(
            f"color: {cfg['text']}; background: transparent; opacity: 0.8;"
        )

    def set_state(
        self, state: str, data: dict | None = None, message: str | None = None
    ):
        self._state = state
        cfg = _STATUS_CONFIG.get(state, _STATUS_CONFIG["unknown"])
        self._icon_lbl.setText(cfg["icon"])
        self._title_lbl.setText(cfg["title"])
        if message:
            self._sub_lbl.setText(message)
        else:
            self._sub_lbl.setText(cfg["sub"])
        self._apply_style(state)

    def set_message(self, message: str):
        self._sub_lbl.setText(message)

    def poll_engine_status(self):
        try:
            import urllib.request as urq

            req = urq.Request(f"http://127.0.0.1:{self._port}/api/engine")
            with urq.urlopen(req, timeout=1) as resp:
                data = json.loads(resp.read())
            state = data.get("state", "unknown").lower()
            self.set_state(state, data)
        except Exception as e:
            log.debug("Engine status poll failed: %s", e)
            if self._state not in ("offline", "error", "recovering"):
                self.set_state("offline", message="Server is not running.")

    def start_polling(self, interval_ms: int = 3000):
        if self._timer is None:
            self._timer = QTimer(self)
            self._timer.timeout.connect(self.poll_engine_status)
        self._timer.start(interval_ms)
        self.poll_engine_status()

    def stop_polling(self):
        if self._timer is not None:
            self._timer.stop()
