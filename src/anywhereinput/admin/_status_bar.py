"""StatusBar - compact bottom bar combining server, tunnel, and metric status."""

from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

_STATUS_COLORS = {
    "healthy": ("#22c55e", "#052e16"),
    "degraded": ("#f59e0b", "#451a03"),
    "recovering": ("#f59e0b", "#451a03"),
    "offline": ("#ef4444", "#450a0a"),
    "error": ("#ef4444", "#450a0a"),
    "unknown": ("#64748b", "#1e293b"),
}


class StatusBar(QWidget):
    """Compact horizontal status bar at the bottom of the main window."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tunnel_url = ""
        self._on_reconnect = None
        self._latency_timer = None
        self._connected = False
        self._server_start_time = None
        self.init_ui()

    def init_ui(self):
        self.setFixedHeight(36)
        self.setStyleSheet(
            "QWidget { background: #0f172a; border-top: 1px solid #1e293b; }"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(12)

        # ── Server status dot ─────────────────────────────────────────────
        self._dot = QLabel()
        self._dot.setFixedSize(8, 8)
        self._dot.setStyleSheet(
            "background: #64748b; border-radius: 4px; border: none;"
        )
        layout.addWidget(self._dot)

        # ── Server state text ─────────────────────────────────────────────
        self._state_lbl = QLabel("Offline")
        self._state_lbl.setFont(QFont("Sans", 9))
        self._state_lbl.setStyleSheet(
            "color: #94a3b8; background: transparent; border: none;"
        )
        layout.addWidget(self._state_lbl)

        # ── Separator ─────────────────────────────────────────────────────
        layout.addWidget(self._make_sep())

        # ── Tunnel indicator ──────────────────────────────────────────────
        self._tunnel_dot = QLabel()
        self._tunnel_dot.setFixedSize(6, 6)
        self._tunnel_dot.setStyleSheet(
            "background: #334155; border-radius: 3px; border: none;"
        )
        layout.addWidget(self._tunnel_dot)

        self._tunnel_lbl = QLabel("")
        self._tunnel_lbl.setFont(QFont("Sans", 9))
        self._tunnel_lbl.setStyleSheet(
            "color: #64748b; background: transparent; border: none;"
        )
        layout.addWidget(self._tunnel_lbl)

        # ── Separator ─────────────────────────────────────────────────────
        layout.addWidget(self._make_sep())

        # ── Uptime ────────────────────────────────────────────────────────
        self._uptime_lbl = QLabel("")
        self._uptime_lbl.setFont(QFont("Monospace", 9))
        self._uptime_lbl.setStyleSheet(
            "color: #64748b; background: transparent; border: none;"
        )
        layout.addWidget(self._uptime_lbl)

        # ── Separator ─────────────────────────────────────────────────────
        layout.addWidget(self._make_sep())

        # ── Clients ───────────────────────────────────────────────────────
        self._clients_lbl = QLabel("")
        self._clients_lbl.setFont(QFont("Monospace", 9))
        self._clients_lbl.setStyleSheet(
            "color: #64748b; background: transparent; border: none;"
        )
        layout.addWidget(self._clients_lbl)

        # ── Separator ─────────────────────────────────────────────────────
        layout.addWidget(self._make_sep())

        # ── FPS ───────────────────────────────────────────────────────────
        self._fps_lbl = QLabel("")
        self._fps_lbl.setFont(QFont("Monospace", 9))
        self._fps_lbl.setStyleSheet(
            "color: #64748b; background: transparent; border: none;"
        )
        layout.addWidget(self._fps_lbl)

        layout.addStretch()

        # ── Tunnel URL ────────────────────────────────────────────────────
        self._url_lbl = QLabel("")
        self._url_lbl.setFont(QFont("Monospace", 8))
        self._url_lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._url_lbl.setStyleSheet(
            "color: #64748b; background: transparent; border: none;"
        )
        self._url_lbl.setMaximumWidth(280)
        layout.addWidget(self._url_lbl)

        self._copy_btn = QPushButton("Copy")
        self._copy_btn.setFixedSize(40, 18)
        self._copy_btn.setStyleSheet(
            "QPushButton {"
            "  background: #1e293b;"
            "  border: 1px solid #334155;"
            "  border-radius: 3px;"
            "  color: #64748b;"
            "  font-size: 9px;"
            "  padding: 0px;"
            "}"
            "QPushButton:hover { background: #334155; color: #94a3b8; }"
        )
        self._copy_btn.setVisible(False)
        self._copy_btn.clicked.connect(self._copy_url)
        layout.addWidget(self._copy_btn)

        # ── Reconnect button ──────────────────────────────────────────────
        self._reconnect_btn = QPushButton("Retry")
        self._reconnect_btn.setFixedSize(48, 18)
        self._reconnect_btn.setStyleSheet(
            "QPushButton {"
            "  background: #450a0a;"
            "  border: 1px solid #991b1b;"
            "  border-radius: 3px;"
            "  color: #fca5a5;"
            "  font-size: 9px;"
            "  padding: 0px;"
            "}"
            "QPushButton:hover { background: #991b1b; color: white; }"
        )
        self._reconnect_btn.setVisible(False)
        self._reconnect_btn.clicked.connect(self._on_reconnect_clicked)
        layout.addWidget(self._reconnect_btn)

    def _make_sep(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        sep.setFixedHeight(16)
        sep.setStyleSheet("color: #1e293b; border: none;")
        return sep

    # ── Server status ─────────────────────────────────────────────────────

    def set_server_state(self, state: str, message: str = ""):
        color, bg = _STATUS_COLORS.get(state, _STATUS_COLORS["unknown"])
        self._dot.setStyleSheet(
            f"background: {color}; border-radius: 4px; border: none;"
        )
        labels = {
            "healthy": "Running",
            "degraded": "Degraded",
            "recovering": "Starting",
            "offline": "Offline",
            "error": "Error",
            "unknown": "Unknown",
        }
        text = labels.get(state, state.title())
        if message:
            text = f"{text} - {message}"
        self._state_lbl.setText(text)

    # ── Tunnel status ─────────────────────────────────────────────────────

    def set_tunnel_provider(self, provider: str):
        display = {
            "cloudflare": "Cloudflare",
            "tailscale": "Tailscale",
            "pinggy": "Pinggy",
            "zrok2": "Zrok2",
        }
        name = display.get(provider, provider.title())
        self._tunnel_lbl.setText(name)

    def set_tunnel_connected(self, url: str = ""):
        self._connected = True
        self._tunnel_url = url
        self._tunnel_dot.setStyleSheet(
            "background: #22c55e; border-radius: 3px; border: none;"
        )
        state_text = (
            self._tunnel_lbl.text().split(" - ")[0] if self._tunnel_lbl.text() else ""
        )
        self._tunnel_lbl.setText(
            f"{state_text} - Connected" if state_text else "Connected"
        )
        self._tunnel_lbl.setStyleSheet(
            "color: #22c55e; background: transparent; border: none;"
        )
        if url:
            self._url_lbl.setText(url)
            self._copy_btn.setVisible(True)
        self._reconnect_btn.setVisible(False)
        self._start_latency_timer()

    def set_tunnel_disconnected(self, reason: str = "Offline"):
        self._connected = False
        self._tunnel_url = ""
        self._tunnel_dot.setStyleSheet(
            "background: #ef4444; border-radius: 3px; border: none;"
        )
        state_text = (
            self._tunnel_lbl.text().split(" - ")[0] if self._tunnel_lbl.text() else ""
        )
        self._tunnel_lbl.setText(f"{state_text} - {reason}" if state_text else reason)
        self._tunnel_lbl.setStyleSheet(
            "color: #ef4444; background: transparent; border: none;"
        )
        self._url_lbl.setText("")
        self._copy_btn.setVisible(False)
        self._reconnect_btn.setVisible(True)
        self._stop_latency_timer()

    def set_tunnel_connecting(self):
        self._connected = False
        self._tunnel_dot.setStyleSheet(
            "background: #f59e0b; border-radius: 3px; border: none;"
        )
        state_text = (
            self._tunnel_lbl.text().split(" - ")[0] if self._tunnel_lbl.text() else ""
        )
        self._tunnel_lbl.setText(
            f"{state_text} - Connecting" if state_text else "Connecting"
        )
        self._tunnel_lbl.setStyleSheet(
            "color: #f59e0b; background: transparent; border: none;"
        )
        self._reconnect_btn.setVisible(False)

    def set_tunnel_hidden(self):
        self._tunnel_dot.setStyleSheet(
            "background: #334155; border-radius: 3px; border: none;"
        )
        self._tunnel_lbl.setText("")
        self._url_lbl.setText("")
        self._copy_btn.setVisible(False)
        self._reconnect_btn.setVisible(False)
        self._stop_latency_timer()

    def set_reconnect_callback(self, callback):
        self._on_reconnect = callback

    def _on_reconnect_clicked(self):
        if self._on_reconnect:
            self._on_reconnect()

    # ── Metrics ───────────────────────────────────────────────────────────

    def set_uptime(self, seconds: float):
        s = int(seconds)
        if s < 60:
            text = f"{s}s"
        elif s < 3600:
            text = f"{s // 60}m {s % 60}s"
        else:
            h = s // 3600
            m = (s % 3600) // 60
            text = f"{h}h {m}m"
        self._uptime_lbl.setText(f"Up {text}")

    def set_clients(self, count: int):
        self._clients_lbl.setText(f"{count} client{'s' if count != 1 else ''}")

    def set_fps(self, fps):
        if fps is not None:
            self._fps_lbl.setText(f"{fps} fps")
        else:
            self._fps_lbl.setText("")

    def clear_metrics(self):
        self._uptime_lbl.setText("")
        self._clients_lbl.setText("")
        self._fps_lbl.setText("")

    def set_server_start_time(self, t):
        self._server_start_time = t

    # ── URL copy ──────────────────────────────────────────────────────────

    def _copy_url(self):
        if self._tunnel_url:
            from PyQt6.QtWidgets import QApplication

            qapp = QApplication.instance()
            if qapp:
                cb = qapp.clipboard()
                cb.setText(self._tunnel_url)
                self._copy_btn.setText("Copied!")
                QTimer.singleShot(1500, lambda: self._copy_btn.setText("Copy"))

    # ── Latency ───────────────────────────────────────────────────────────

    def _start_latency_timer(self):
        if self._latency_timer is None:
            self._latency_timer = QTimer(self)
            self._latency_timer.timeout.connect(self._measure_latency)
        self._latency_timer.start(15000)
        self._measure_latency()

    def _stop_latency_timer(self):
        if self._latency_timer is not None:
            self._latency_timer.stop()

    def _measure_latency(self):
        if not self._connected or not self._tunnel_url:
            return
        import threading

        def _do():
            try:
                import urllib.request as urq

                url = self._tunnel_url
                if not url.startswith("http"):
                    url = f"http://{url}"
                req = urq.Request(url, method="HEAD")
                urq.urlopen(req, timeout=5)
                QTimer.singleShot(0, lambda: self._uptime_lbl.parentWidget() and None)
            except Exception:
                pass

        threading.Thread(target=_do, daemon=True).start()
