"""Desktop notification widget for incoming connection requests."""

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
)


class ConnectionNotificationWidget(QFrame):
    """Floating notification with Approve/Decline buttons for incoming requests."""

    approved = pyqtSignal()
    declined = pyqtSignal()
    dismissed = pyqtSignal()

    def __init__(self, client_name: str, client_ip: str, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(320)
        self._build_ui(client_name, client_ip)
        self._auto_dismiss_timer = QTimer(self)
        self._auto_dismiss_timer.setSingleShot(True)
        self._auto_dismiss_timer.timeout.connect(self._on_dismiss)
        self._auto_dismiss_timer.start(15000)
        self.show()
        self._position_in_corner()

    def _build_ui(self, client_name: str, client_ip: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        container = QFrame()
        container.setStyleSheet(
            "QFrame {"
            "  background: #1e293b;"
            "  border: 1px solid #334155;"
            "  border-radius: 8px;"
            "}"
        )
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(14, 12, 14, 12)
        container_layout.setSpacing(6)

        header = QLabel("🔔 Incoming Connection")
        header.setFont(QFont("Sans", 11, QFont.Weight.Bold))
        header.setStyleSheet("color: #f1f5f9; background: transparent;")
        container_layout.addWidget(header)

        name_lbl = QLabel(client_name or "Unknown Device")
        name_lbl.setFont(QFont("Sans", 10))
        name_lbl.setStyleSheet("color: #e2e8f0; background: transparent;")
        container_layout.addWidget(name_lbl)

        ip_lbl = QLabel(client_ip or "unknown")
        ip_lbl.setFont(QFont("Monospace", 9))
        ip_lbl.setStyleSheet("color: #94a3b8; background: transparent;")
        container_layout.addWidget(ip_lbl)

        container_layout.addSpacing(6)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        approve_btn = QPushButton("Approve")
        approve_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        approve_btn.setStyleSheet(
            "QPushButton {"
            "  background: #16a34a; color: white; border: none;"
            "  border-radius: 4px; padding: 6px 16px; font-weight: bold;"
            "}"
            "QPushButton:hover { background: #15803d; }"
        )
        approve_btn.clicked.connect(self._on_approve)
        btn_row.addWidget(approve_btn)

        decline_btn = QPushButton("Decline")
        decline_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        decline_btn.setStyleSheet(
            "QPushButton {"
            "  background: #dc2626; color: white; border: none;"
            "  border-radius: 4px; padding: 6px 16px; font-weight: bold;"
            "}"
            "QPushButton:hover { background: #b91c1c; }"
        )
        decline_btn.clicked.connect(self._on_decline)
        btn_row.addWidget(decline_btn)

        container_layout.addLayout(btn_row)
        layout.addWidget(container)

    def _position_in_corner(self):
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.right() - self.width() - 20
            y = geo.bottom() - self.height() - 20
            self.move(x, y)

    def _on_approve(self):
        self._auto_dismiss_timer.stop()
        self.approved.emit()
        self.dismissed.emit()
        self.close()

    def _on_decline(self):
        self._auto_dismiss_timer.stop()
        self.declined.emit()
        self.dismissed.emit()
        self.close()

    def _on_dismiss(self):
        self.dismissed.emit()
        self.close()
