"""EngineStatusWidget - live status polling widget."""

import json

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget
from PyQt6.QtGui import QFont


class EngineStatusWidget(QWidget):
    """Live engine status panel (heartbeat polling via /api/engine)."""

    def __init__(self, port: int = 8008, parent=None):
        super().__init__(parent)
        self._port = port
        self._state = "unknown"
        self._timer_id = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        row = QHBoxLayout()
        self.indicator = QLabel("●")
        self.indicator.setStyleSheet("font-size: 18px; color: gray;")
        self.lbl_state = QLabel("Unknown")
        self.lbl_state.setFont(QFont("Sans", 10, QFont.Weight.Bold))
        row.addWidget(self.indicator)
        row.addWidget(self.lbl_state)
        row.addStretch()
        layout.addLayout(row)

    def poll_engine_status(self):
        """Try to reach /api/engine; update UI on success."""
        try:
            import urllib.request as urq

            req = urq.Request(f"http://127.0.0.1:{self._port}/api/engine")
            with urq.urlopen(req, timeout=1) as resp:
                data = json.loads(resp.read())
            state = data.get("state", "unknown").lower()
            self.set_state(state, data)
        except Exception:
            if self._state != "offline":
                self._state = "offline"
                self.indicator.setStyleSheet("font-size: 18px; color: gray;")
                self.lbl_state.setText("Offline")

    def set_state(self, state: str, data: dict | None = None):
        self._state = state
        colors = {
            "healthy": "#22c55e",
            "degraded": "#f59e0b",
            "recovering": "#3b82f6",
            "offline": "#ef4444",
        }
        color = colors.get(state, "#6b7280")
        self.indicator.setStyleSheet(f"font-size: 18px; color: {color};")
        labels = {
            "healthy": "Healthy",
            "degraded": "Degraded",
            "recovering": "Recovering",
            "offline": "Offline",
        }
        self.lbl_state.setText(labels.get(state, state.title()))

    def start_polling(self):
        pass
