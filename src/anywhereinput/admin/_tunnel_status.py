"""TunnelStatusWidget - rich tunnel connection status display."""

import logging
import time

from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

log = logging.getLogger("anywhereinput.admin")


class TunnelStatusWidget(QWidget):
    """Displays tunnel connection status with provider name, indicator, URL, latency, and reconnect."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._connected = False
        self._provider = ""
        self._tunnel_url = ""
        self._latency_ms = None
        self._latency_timer = None
        self._on_reconnect = None
        self.init_ui()

    def init_ui(self):
        self._banner = QFrame()
        self._banner.setFrameShape(QFrame.Shape.StyledPanel)
        self._banner.setStyleSheet(
            "QFrame {"
            "  background: #1e293b;"
            "  border: 1px solid #334155;"
            "  border-radius: 6px;"
            "}"
        )
        banner_layout = QVBoxLayout(self._banner)
        banner_layout.setContentsMargins(10, 8, 10, 8)
        banner_layout.setSpacing(4)

        # Row 1: Provider + status indicator
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        self._provider_lbl = QLabel("")
        self._provider_lbl.setFont(QFont("Sans", 11, QFont.Weight.Bold))
        self._provider_lbl.setStyleSheet("color: #e2e8f0; background: transparent;")
        top_row.addWidget(self._provider_lbl)

        self._status_lbl = QLabel("")
        self._status_lbl.setFont(QFont("Sans", 10))
        top_row.addWidget(self._status_lbl)

        top_row.addStretch()

        self._reconnect_btn = QPushButton("Reconnect")
        self._reconnect_btn.setFixedHeight(24)
        self._reconnect_btn.setStyleSheet(
            "QPushButton {"
            "  background: #1e293b;"
            "  border: 1px solid #475569;"
            "  border-radius: 3px;"
            "  color: #94a3b8;"
            "  font-size: 11px;"
            "  padding: 2px 10px;"
            "}"
            "QPushButton:hover { background: #334155; border-color: #64748b; }"
        )
        self._reconnect_btn.setVisible(False)
        self._reconnect_btn.clicked.connect(self._on_reconnect_clicked)
        top_row.addWidget(self._reconnect_btn)

        banner_layout.addLayout(top_row)

        # Row 2: Public URL
        url_row = QHBoxLayout()
        url_row.setSpacing(6)

        url_title = QLabel("Public URL")
        url_title.setFont(QFont("Sans", 9))
        url_title.setStyleSheet("color: #64748b; background: transparent;")
        url_row.addWidget(url_title)

        self._url_lbl = QLabel("-")
        self._url_lbl.setFont(QFont("Monospace", 9))
        self._url_lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._url_lbl.setStyleSheet("color: #94a3b8; background: transparent;")
        url_row.addWidget(self._url_lbl, 1)

        self._copy_btn = QPushButton("Copy")
        self._copy_btn.setFixedHeight(20)
        self._copy_btn.setStyleSheet(
            "QPushButton {"
            "  background: #0f172a;"
            "  border: 1px solid #334155;"
            "  border-radius: 3px;"
            "  color: #64748b;"
            "  font-size: 10px;"
            "  padding: 1px 6px;"
            "}"
            "QPushButton:hover { background: #1e293b; color: #94a3b8; }"
        )
        self._copy_btn.setVisible(False)
        self._copy_btn.clicked.connect(self._copy_url)
        url_row.addWidget(self._copy_btn)

        banner_layout.addLayout(url_row)

        # Row 3: Latency
        latency_row = QHBoxLayout()
        latency_row.setSpacing(6)

        latency_title = QLabel("Latency")
        latency_title.setFont(QFont("Sans", 9))
        latency_title.setStyleSheet("color: #64748b; background: transparent;")
        latency_row.addWidget(latency_title)

        self._latency_lbl = QLabel("-")
        self._latency_lbl.setFont(QFont("Monospace", 9))
        self._latency_lbl.setStyleSheet("color: #94a3b8; background: transparent;")
        latency_row.addWidget(self._latency_lbl)

        latency_row.addStretch()

        banner_layout.addLayout(latency_row)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self._banner)

        self._apply_disconnected_style()

    def set_provider(self, provider: str):
        self._provider = provider
        display_names = {
            "cloudflare": "Cloudflare",
            "tailscale": "Tailscale",
            "pinggy": "Pinggy",
            "zrok2": "Zrok2",
            "local": "Local",
        }
        self._provider_lbl.setText(display_names.get(provider, provider.title()))

    def set_connected(self, url: str = ""):
        self._connected = True
        self._tunnel_url = url
        self._status_lbl.setText("Connected")
        self._status_lbl.setStyleSheet(
            "color: #22c55e; background: transparent; font-weight: bold;"
        )
        self._url_lbl.setText(url if url else "-")
        self._copy_btn.setVisible(bool(url))
        self._reconnect_btn.setVisible(False)
        self._apply_connected_style()
        self._start_latency_check()

    def set_disconnected(self, reason: str = "Tunnel Offline"):
        self._connected = False
        self._tunnel_url = ""
        self._status_lbl.setText(reason)
        self._status_lbl.setStyleSheet(
            "color: #ef4444; background: transparent; font-weight: bold;"
        )
        self._url_lbl.setText("-")
        self._copy_btn.setVisible(False)
        self._reconnect_btn.setVisible(True)
        self._latency_lbl.setText("-")
        self._apply_disconnected_style()
        self._stop_latency_check()

    def set_connecting(self):
        self._connected = False
        self._status_lbl.setText("Connecting...")
        self._status_lbl.setStyleSheet(
            "color: #f59e0b; background: transparent; font-weight: bold;"
        )
        self._reconnect_btn.setVisible(False)
        self._apply_connecting_style()

    def set_reconnect_callback(self, callback):
        self._on_reconnect = callback

    def _apply_connected_style(self):
        self._banner.setStyleSheet(
            "QFrame {"
            "  background: #052e16;"
            "  border: 1px solid #166534;"
            "  border-radius: 6px;"
            "}"
        )

    def _apply_disconnected_style(self):
        self._banner.setStyleSheet(
            "QFrame {"
            "  background: #1e293b;"
            "  border: 1px solid #334155;"
            "  border-radius: 6px;"
            "}"
        )

    def _apply_connecting_style(self):
        self._banner.setStyleSheet(
            "QFrame {"
            "  background: #451a03;"
            "  border: 1px solid #92400e;"
            "  border-radius: 6px;"
            "}"
        )

    def _copy_url(self):
        if self._tunnel_url:
            from PyQt6.QtWidgets import QApplication

            qapp = QApplication.instance()
            if qapp:
                cb = qapp.clipboard()
                cb.setText(self._tunnel_url)
                self._copy_btn.setText("Copied!")
                QTimer.singleShot(1500, lambda: self._copy_btn.setText("Copy"))

    def _on_reconnect_clicked(self):
        if self._on_reconnect:
            self._on_reconnect()

    def _start_latency_check(self):
        if self._latency_timer is None:
            self._latency_timer = QTimer(self)
            self._latency_timer.timeout.connect(self._check_latency)
        self._latency_timer.start(10000)
        self._check_latency()

    def _stop_latency_check(self):
        if self._latency_timer is not None:
            self._latency_timer.stop()

    def _check_latency(self):
        if not self._connected or not self._tunnel_url:
            return
        import threading

        def measure():
            try:
                import urllib.request as urq

                url = self._tunnel_url
                if not url.startswith("http"):
                    url = f"http://{url}"
                start = time.monotonic()
                req = urq.Request(url, method="HEAD")
                urq.urlopen(req, timeout=5)
                elapsed = (time.monotonic() - start) * 1000
                QTimer.singleShot(
                    0, lambda: self._latency_lbl.setText(f"{elapsed:.0f} ms")
                )
            except Exception:
                QTimer.singleShot(0, lambda: self._latency_lbl.setText("N/A"))

        threading.Thread(target=measure, daemon=True).start()
