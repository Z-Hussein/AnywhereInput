"""WelcomeWizard - first-run setup dialog."""

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    QStackedWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from anywhereinput._constants import DEFAULT_PORT


def _step_indicator(current: int, total: int) -> QHBoxLayout:
    """Build a row of step dots."""
    row = QHBoxLayout()
    row.setSpacing(6)
    row.addStretch()
    for i in range(1, total + 1):
        dot = QLabel()
        dot.setFixedSize(8, 8)
        if i <= current:
            dot.setStyleSheet("background: #3b82f6; border-radius: 4px; border: none;")
        else:
            dot.setStyleSheet("background: #334155; border-radius: 4px; border: none;")
        row.addWidget(dot)
    row.addStretch()
    return row


class WelcomeWizard(QDialog):
    """Step-by-step first-run wizard."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Welcome to AnywhereInput")
        self.setFixedSize(440, 380)
        self.result_port = DEFAULT_PORT
        self.result_tunnel = "local"
        self._step = 0
        self._total_steps = 3
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.setSpacing(12)

        # Step dots
        self._dots_row = _step_indicator(1, self._total_steps)
        layout.addLayout(self._dots_row)

        # Stacked pages
        self._stack = QStackedWidget()
        self._stack.addWidget(self._page_welcome())
        self._stack.addWidget(self._page_port())
        self._stack.addWidget(self._page_tunnel())
        self._stack.addWidget(self._page_done())
        layout.addWidget(self._stack, 1)

        # Navigation buttons
        nav = QHBoxLayout()
        nav.addStretch()

        self._back_btn = QPushButton("Back")
        self._back_btn.setFixedWidth(70)
        self._back_btn.setStyleSheet(
            "QPushButton {"
            "  background: #1e293b;"
            "  border: 1px solid #334155;"
            "  border-radius: 4px;"
            "  color: #94a3b8;"
            "  padding: 6px;"
            "}"
            "QPushButton:hover { background: #334155; }"
            "QPushButton:disabled { color: #475569; }"
        )
        self._back_btn.clicked.connect(self._prev_step)
        nav.addWidget(self._back_btn)

        self._next_btn = QPushButton("Next")
        self._next_btn.setFixedWidth(90)
        self._next_btn.setStyleSheet(
            "QPushButton {"
            "  background: #2563eb;"
            "  color: white;"
            "  font-weight: bold;"
            "  border: none;"
            "  border-radius: 4px;"
            "  padding: 6px;"
            "}"
            "QPushButton:hover { background: #3b82f6; }"
        )
        self._next_btn.clicked.connect(self._next_step)
        nav.addWidget(self._next_btn)

        layout.addLayout(nav)

        self._update_nav()

    # ── Pages ─────────────────────────────────────────────────────────────

    def _page_welcome(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 24, 16, 0)
        layout.setSpacing(8)

        title = QLabel("Welcome to AnywhereInput")
        title.setFont(QFont("Sans", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #e2e8f0;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        layout.addSpacing(8)

        subtitle = QLabel(
            "This quick setup will get your remote desktop server running in under a minute."
        )
        subtitle.setFont(QFont("Sans", 10))
        subtitle.setStyleSheet("color: #94a3b8;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        layout.addSpacing(16)

        # Preview steps
        steps = [
            ("1", "Choose a port for the server"),
            ("2", "Select a tunnel for remote access"),
            ("3", "Start and connect"),
        ]
        for num, text in steps:
            row = QHBoxLayout()
            row.setSpacing(10)
            badge = QLabel(num)
            badge.setFixedSize(24, 24)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setFont(QFont("Sans", 10, QFont.Weight.Bold))
            badge.setStyleSheet(
                "background: #1e293b; color: #3b82f6; border: 1px solid #334155;"
                "border-radius: 12px;"
            )
            row.addWidget(badge)
            lbl = QLabel(text)
            lbl.setFont(QFont("Sans", 10))
            lbl.setStyleSheet("color: #cbd5e1;")
            row.addWidget(lbl)
            row.addStretch()
            layout.addLayout(row)

        layout.addStretch()
        return page

    def _page_port(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 24, 16, 0)
        layout.setSpacing(8)

        title = QLabel("Choose a Port")
        title.setFont(QFont("Sans", 13, QFont.Weight.Bold))
        title.setStyleSheet("color: #e2e8f0;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        desc = QLabel(
            "The server listens on this port. Default is fine for most users."
        )
        desc.setFont(QFont("Sans", 10))
        desc.setStyleSheet("color: #94a3b8;")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addSpacing(12)

        form = QFormLayout()
        form.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._port_spin = QSpinBox()
        self._port_spin.setRange(1024, 65535)
        self._port_spin.setValue(DEFAULT_PORT)
        self._port_spin.setFixedWidth(120)
        self._port_spin.setStyleSheet(
            "QSpinBox {"
            "  background: #1e293b;"
            "  border: 1px solid #334155;"
            "  border-radius: 4px;"
            "  color: #e2e8f0;"
            "  padding: 4px 8px;"
            "  font-size: 12px;"
            "}"
        )
        form.addRow("Port:", self._port_spin)
        layout.addLayout(form)

        layout.addStretch()
        return page

    def _page_tunnel(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 24, 16, 0)
        layout.setSpacing(8)

        title = QLabel("Select a Tunnel")
        title.setFont(QFont("Sans", 13, QFont.Weight.Bold))
        title.setStyleSheet("color: #e2e8f0;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        desc = QLabel(
            "A tunnel gives you a public URL to access the server from anywhere.\n"
            "You can change this later in Settings."
        )
        desc.setFont(QFont("Sans", 10))
        desc.setStyleSheet("color: #94a3b8;")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addSpacing(12)

        form = QFormLayout()
        form.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._tunnel_combo = QComboBox()
        self._tunnel_combo.setFixedWidth(200)
        self._tunnel_combo.setStyleSheet(
            "QComboBox {"
            "  background: #1e293b;"
            "  border: 1px solid #334155;"
            "  border-radius: 4px;"
            "  color: #e2e8f0;"
            "  padding: 4px 8px;"
            "  font-size: 12px;"
            "}"
        )
        tunnel_opts = [
            ("Local (no tunnel)", "local"),
            ("Cloudflare (free)", "cloudflare"),
            ("Tailscale", "tailscale"),
            ("Pinggy.io", "pinggy"),
            ("Zrok2", "zrok2"),
        ]
        for label, val in tunnel_opts:
            self._tunnel_combo.addItem(label, val)
        form.addRow("Tunnel:", self._tunnel_combo)
        layout.addLayout(form)

        # Hint for Cloudflare
        hint = QLabel("Cloudflare is recommended -- free, no account needed.")
        hint.setFont(QFont("Sans", 9))
        hint.setStyleSheet("color: #64748b;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        layout.addStretch()
        return page

    def _page_done(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 24, 16, 0)
        layout.setSpacing(8)

        title = QLabel("You're All Set")
        title.setFont(QFont("Sans", 13, QFont.Weight.Bold))
        title.setStyleSheet("color: #e2e8f0;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        desc = QLabel(
            "The server will start with your chosen settings.\n"
            "Open the browser URL to connect your device."
        )
        desc.setFont(QFont("Sans", 10))
        desc.setStyleSheet("color: #94a3b8;")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addSpacing(12)

        # Summary
        self._summary_lbl = QLabel()
        self._summary_lbl.setFont(QFont("Monospace", 10))
        self._summary_lbl.setStyleSheet(
            "color: #94a3b8;"
            "background: #0f172a;"
            "border: 1px solid #1e293b;"
            "border-radius: 4px;"
            "padding: 8px;"
        )
        self._summary_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._summary_lbl)

        layout.addStretch()
        return page

    # ── Navigation ────────────────────────────────────────────────────────

    def _update_nav(self):
        self._back_btn.setEnabled(self._step > 0)
        if self._step == self._total_steps:
            self._next_btn.setText("Start")
        else:
            self._next_btn.setText("Next")
        # Update dots
        for i in range(self._dots_row.count()):
            widget = self._dots_row.itemAt(i).widget()
            if widget and widget != self._dots_row.itemAt(0).spacerItem():
                pass  # dots are recreated below

    def _next_step(self):
        if self._step == 0:
            self._step = 1
        elif self._step == 1:
            self.result_port = self._port_spin.value()
            self._step = 2
        elif self._step == 2:
            self.result_tunnel = self._tunnel_combo.currentData()
            self._update_summary()
            self._step = 3
        elif self._step == 3:
            self.accept()
            return

        self._stack.setCurrentIndex(self._step)
        self._update_nav()

    def _prev_step(self):
        if self._step > 0:
            self._step -= 1
            self._stack.setCurrentIndex(self._step)
            self._update_nav()

    def _update_summary(self):
        tunnel_name = self._tunnel_combo.currentText()
        self._summary_lbl.setText(
            f"Port: {self.result_port}\n"
            f"Tunnel: {tunnel_name}\n\n"
            f"Click Start to launch the server."
        )
