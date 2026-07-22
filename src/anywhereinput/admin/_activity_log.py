"""ActivityLog - audit timeline of important events."""

from datetime import datetime

from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

_EVENT_COLORS = {
    "connect": ("#22c55e", "#052e16"),
    "disconnect": ("#ef4444", "#450a0a"),
    "token": ("#a78bfa", "#2e1065"),
    "tunnel": ("#38bdf8", "#0c4a6e"),
    "server": ("#facc15", "#422006"),
    "settings": ("#94a3b8", "#1e293b"),
    "error": ("#ef4444", "#450a0a"),
}

_EVENT_ICONS = {
    "connect": "connected",
    "disconnect": "disconnected",
    "token": "token",
    "tunnel": "tunnel",
    "server": "server",
    "settings": "settings",
    "error": "error",
}


class ActivityLog(QWidget):
    """Scrollable timeline of important events."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._events = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(8, 4, 8, 4)
        toolbar.setSpacing(6)

        title = QLabel("Activity")
        title.setFont(QFont("Sans", 10, QFont.Weight.Bold))
        title.setStyleSheet("color: #64748b;")
        toolbar.addWidget(title)

        toolbar.addStretch()

        self._clear_btn = QPushButton("Clear")
        self._clear_btn.setFixedHeight(22)
        self._clear_btn.setStyleSheet(
            "QPushButton {"
            "  background: #1e293b;"
            "  border: 1px solid #334155;"
            "  border-radius: 3px;"
            "  color: #94a3b8;"
            "  font-size: 10px;"
            "  padding: 1px 8px;"
            "}"
            "QPushButton:hover { background: #334155; }"
        )
        self._clear_btn.clicked.connect(self.clear)
        toolbar.addWidget(self._clear_btn)

        layout.addLayout(toolbar)

        # Scroll area with events
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet("QScrollArea { background: transparent; }")

        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._events_layout = QVBoxLayout(self._container)
        self._events_layout.setContentsMargins(8, 4, 8, 4)
        self._events_layout.setSpacing(2)
        self._events_layout.addStretch()

        self._scroll.setWidget(self._container)
        layout.addWidget(self._scroll, 1)

        # Empty state
        self._empty_lbl = QLabel(
            "No activity yet. Events will appear here as they happen."
        )
        self._empty_lbl.setStyleSheet("color: #475569; font-size: 11px; padding: 20px;")
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_lbl.setWordWrap(True)
        layout.addWidget(self._empty_lbl)

    def add_event(self, category: str, text: str, detail: str = ""):
        """Add an event to the timeline.

        category: connect, disconnect, token, tunnel, server, settings, error
        text: short description (e.g. "John connected")
        detail: optional extra info (e.g. IP address, token name)
        """
        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")

        self._empty_lbl.setVisible(False)

        # Event text
        text_col = QVBoxLayout()
        text_col.setSpacing(0)

        text_lbl = QLabel(text)
        text_lbl.setFont(QFont("Sans", 10))
        text_lbl.setStyleSheet("color: #e2e8f0; background: transparent;")
        text_col.addWidget(text_lbl)

        if detail:
            detail_lbl = QLabel(detail)
            detail_lbl.setFont(QFont("Monospace", 8))
            detail_lbl.setStyleSheet("color: #64748b; background: transparent;")
            text_col.addWidget(detail_lbl)

        # Build the row widget
        item_widget = QWidget()
        item_widget.setStyleSheet("background: transparent;")
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(0, 3, 0, 3)
        item_layout.setSpacing(8)

        # Time
        time_lbl = QLabel(time_str)
        time_lbl.setFont(QFont("Monospace", 9))
        time_lbl.setStyleSheet("color: #475569; background: transparent;")
        time_lbl.setFixedWidth(60)
        item_layout.addWidget(time_lbl)

        # Category badge
        bg, fg = _EVENT_COLORS.get(category, _EVENT_COLORS["settings"])
        badge = QLabel(category.upper())
        badge.setFont(QFont("Sans", 8, QFont.Weight.Bold))
        badge.setStyleSheet(
            f"background: {bg}; color: {fg}; border-radius: 3px;"
            f"padding: 1px 6px; font-size: 8px;"
        )
        badge.setFixedWidth(60)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        item_layout.addWidget(badge)

        item_layout.addLayout(text_col, 1)

        self._events_layout.insertWidget(self._events_layout.count() - 1, item_widget)

        # Auto-scroll to bottom
        sb = self._scroll.verticalScrollBar()
        sb.setValue(sb.maximum())

        # Keep last 200 events
        if self._events_layout.count() > 202:  # 200 + empty stretch + empty state
            old = self._events_layout.takeAt(0)
            if old and old.widget():
                old.widget().deleteLater()

        self._events.append((category, text, detail, time_str))

    def log_server_start(self, port: int, tunnel: str):
        self.add_event("server", "Server started", f"Port {port} | Tunnel: {tunnel}")

    def log_server_stop(self):
        self.add_event("server", "Server stopped")

    def log_tunnel_connected(self, provider: str, url: str):
        self.add_event("tunnel", f"{provider} connected", url)

    def log_tunnel_disconnected(self, provider: str):
        self.add_event("tunnel", f"{provider} disconnected")

    def log_client_connected(self, ip: str, token: str = ""):
        detail = f"IP: {ip}" if not token else f"IP: {ip} | Token: {token}"
        self.add_event("connect", "Client connected", detail)

    def log_client_disconnected(self, ip: str):
        self.add_event("disconnect", "Client disconnected", f"IP: {ip}")

    def log_token_created(self, name: str):
        self.add_event("token", f"Token created: {name}")

    def log_token_revoked(self, name: str):
        self.add_event("token", f"Token revoked: {name}")

    def log_error(self, message: str):
        self.add_event("error", message)

    def clear(self):
        while self._events_layout.count():
            item = self._events_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        self._events_layout.addStretch()
        self._events.clear()
        self._empty_lbl.setVisible(True)
