"""TokenManagerDialog - create/edit token dialog."""

import json
import threading
import urllib.request as urq
from typing import Dict, Optional

from anywhereinput import safe_print
from PyQt6.QtCore import QMetaObject, Q_ARG, Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)
from PyQt6.QtGui import QFont


class TokenManagerDialog(QDialog):
    """Create / edit a token with IP allowlist and input permissions."""

    def __init__(
        self,
        store,
        port: int = 8008,
        existing_token: Optional[str] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.store = store
        self._port = port
        self._existing = existing_token
        self.setWindowTitle("Token Manager" if not existing_token else "Edit Token")
        self.setFixedWidth(420)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        self.name_input = QLineEdit(
            self._existing_data["name"] if self._existing else ""
        )
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)

        # Permissions checkboxes
        perm_group = QGroupBox("Permissions")
        perm_layout = QVBoxLayout(perm_group)
        default_perms = ["move", "click", "scroll", "keyboard", "screen_toggle"]
        self.perm_checks: Dict[str, QCheckBox] = {}
        for p in default_perms:
            cb = QCheckBox(p)
            if self._existing and p in self._existing_data.get("permissions", []):
                cb.setChecked(True)
            else:
                cb.setChecked(False)
            self.perm_checks[p] = cb
            perm_layout.addWidget(cb)

        btns = QHBoxLayout()
        btns.addWidget(QPushButton("All", clicked=self._check_all))
        btns.addWidget(QPushButton("None", clicked=self._uncheck_all))
        btns.addStretch()
        perm_layout.addLayout(btns)
        layout.addWidget(perm_group)

        # IP Allowlist
        ip_group = QGroupBox("IP Allowlist (leave empty = allow all)")
        ip_layout = QVBoxLayout(ip_group)
        self.ip_input = QTextEdit()
        self.ip_input.setPlaceholderText("192.168.1.0/24\n10.0.0.1")
        if self._existing:
            self.ip_input.setText("\n".join(self._existing_data.get("allowed_ips", [])))
        ip_layout.addWidget(self.ip_input)
        layout.addWidget(ip_group)

        # Show full token section (view-only during edit)
        if self._existing:
            show_box = QGroupBox("Token Value")
            show_layout = QVBoxLayout(show_box)  # noqa: F841
            self.token_display = QLineEdit(self._existing)
            self.token_display.setReadOnly(True)
            self.token_display.setFont(QFont("Monospace", 9))
            layout.addWidget(show_box)

        # Blocked IPs section (only for existing tokens)
        if self._existing:
            blocked_group = QGroupBox("Blocked IPs (kicked clients)")
            blocked_layout = QVBoxLayout(blocked_group)
            self.blocked_table = QTableWidget()
            self.blocked_table.setColumnCount(2)
            self.blocked_table.setHorizontalHeaderLabels(["Blocked IP", "Action"])
            self.blocked_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            self.blocked_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            self.blocked_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            blocked_layout.addWidget(self.blocked_table)
            # Refresh button
            blocked_btn_layout = QHBoxLayout()
            refresh_blocked = QPushButton("Refresh", clicked=self._refresh_blocked)
            blocked_btn_layout.addWidget(refresh_blocked)
            blocked_btn_layout.addStretch()
            blocked_layout.addLayout(blocked_btn_layout)
            layout.addWidget(blocked_group)

        # Buttons
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        btn_box.accepted.connect(self._on_ok)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _check_all(self):
        for cb in self.perm_checks.values():
            cb.setChecked(True)

    def _uncheck_all(self):
        for cb in self.perm_checks.values():
            cb.setChecked(False)

    def _refresh_blocked(self):
        """Fetch and display blocked IPs for this token."""
        if not self._existing:
            return
        threading.Thread(target=self._fetch_blocked, daemon=True).start()

    def _fetch_blocked(self):
        try:
            req = urq.Request(f"http://127.0.0.1:{self._port}/api/tokens/{self._existing}/blocked-ips")
            with urq.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
            blocked_ips = data.get("blocked_ips", [])
            QMetaObject.invokeMethod(
                self,
                "_update_blocked_table",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(list, blocked_ips),
            )
        except Exception as e:
            safe_print(f"Error fetching blocked IPs: {e}")
            QMetaObject.invokeMethod(
                self,
                "_show_blocked_error",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, f"Failed to fetch blocked IPs: {e}"),
            )

    @pyqtSlot(str)
    def _show_blocked_error(self, error_msg):
        QMessageBox.warning(self, "Blocked IPs Error", error_msg)

    @pyqtSlot(list)
    def _update_blocked_table(self, blocked_ips):
        """Update the blocked IPs table - must be called on main thread."""
        self.blocked_table.setRowCount(len(blocked_ips))
        for row, ip in enumerate(blocked_ips):
            ip_item = QTableWidgetItem(ip)
            self.blocked_table.setItem(row, 0, ip_item)

            # Unblock button
            unblock_btn = QPushButton("Unblock")
            unblock_btn.setFixedWidth(80)
            unblock_btn.clicked.connect(
                lambda _, i=ip: self._unblock_ip(i)
            )
            self.blocked_table.setCellWidget(row, 1, unblock_btn)

    def _unblock_ip(self, ip):
        """Remove an IP from the token's blocked list."""
        def do_unblock():
            try:
                req = urq.Request(
                    f"http://127.0.0.1:{self._port}/api/tokens/{self._existing}/blocked-ips/{ip}",
                    method="DELETE",
                )
                with urq.urlopen(req, timeout=5) as resp:
                    json.loads(resp.read())
                # Refresh the table
                QMetaObject.invokeMethod(
                    self,
                    "_refresh_blocked",
                    Qt.ConnectionType.QueuedConnection,
                )
            except Exception as e:
                safe_print(f"Error unblocking IP: {e}")
                QMetaObject.invokeMethod(
                    self,
                    "_show_unblock_error",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(str, f"Failed to unblock IP {ip}: {e}"),
                )

    @pyqtSlot(str)
    def _show_unblock_error(self, error_msg):
        QMessageBox.warning(self, "Unblock Failed", error_msg)

    @property
    def _existing_data(self) -> dict:
        if not self._existing:
            return {}
        try:
            import urllib.request as urq

            req = urq.Request(f"http://127.0.0.1:{self._port}/api/tokens")
            with urq.urlopen(req, timeout=2) as resp:
                data = json.loads(resp.read())
            for t in data.get("tokens", []):
                if t.get("full_token") == self._existing:
                    return t
        except Exception:
            pass
        return {}

    def _on_ok(self):
        name = self.name_input.text().strip() or "unnamed"
        perms = [p for p, cb in self.perm_checks.items() if cb.isChecked()]

        if self._existing:
            try:
                import urllib.request as urq

                data = json.dumps({"name": name, "permissions": perms}).encode()
                req = urq.Request(
                    f"http://127.0.0.1:{self._port}/api/tokens/{self._existing}",
                    data=data,
                    headers={"Content-Type": "application/json"},
                    method="PATCH",
                )
                with urq.urlopen(req, timeout=5) as resp:
                    json.loads(resp.read())
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to update token: {e}")
                return
        else:
            try:
                import urllib.request as urq

                data = json.dumps({"name": name, "permissions": perms}).encode()
                req = urq.Request(
                    f"http://127.0.0.1:{self._port}/api/tokens",
                    data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urq.urlopen(req, timeout=5) as resp:
                    result = json.loads(resp.read())

                new_token_val = result.get("token", "")
                QMessageBox.information(
                    self,
                    "New Token Created on Server",
                    f"Token created:\n\n{new_token_val}\n\n"
                    "Copy and save it now - it won't be shown again!",
                )
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to create token: {e}")
                return

        self.accept()
