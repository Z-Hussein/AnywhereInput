"""ClientListDialog - connected clients viewer."""

import json
import threading
import urllib.request as urq

from anywhereinput import safe_print
from PyQt6.QtCore import Qt, QMetaObject, Q_ARG, pyqtSlot
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


class ClientListDialog(QDialog):
    """Shows currently connected WebSocket clients with kick option."""

    def __init__(self, port: int = 8008, parent=None):
        super().__init__(parent)
        self._port = port
        self.setWindowTitle("Connected Clients")
        self.setFixedWidth(550)
        self.setMinimumHeight(400)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Table for clients
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["IP Address", "Token", "Action"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        # Buttons
        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton("Refresh", clicked=self._refresh)
        close_btn = QPushButton("Close", clicked=self.close)
        btn_layout.addWidget(refresh_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _refresh(self):
        def fetch():
            try:
                req = urq.Request(f"http://127.0.0.1:{self._port}/api/clients")
                with urq.urlopen(req, timeout=2) as resp:
                    data = json.loads(resp.read())

                clients = data.get("clients", [])
                # Schedule UI update on main thread
                QMetaObject.invokeMethod(
                    self,
                    "_update_table",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(list, clients),
                )
            except Exception as e:
                # Schedule empty table update on main thread
                QMetaObject.invokeMethod(
                    self,
                    "_update_table",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(list, []),
                )
                safe_print(f"Error fetching clients: {e}")

        # Run in background thread to avoid blocking UI
        threading.Thread(target=fetch, daemon=True).start()

    @pyqtSlot(list)
    def _update_table(self, clients):
        """Update the client table - must be called on main thread."""
        self.table.setRowCount(len(clients))
        for row, c in enumerate(clients):
            # IP Address
            ip_item = QTableWidgetItem(c.get("ip", "unknown"))
            self.table.setItem(row, 0, ip_item)

            # Token (masked)
            token = c.get("token", "unknown")
            token_item = QTableWidgetItem(token)
            token_item.setToolTip(c.get("full_token", ""))
            self.table.setItem(row, 1, token_item)

            # Validate client_id - must be a non-empty string, not a WebSocket object repr
            client_id = c.get("id", "")
            if not client_id or not isinstance(client_id, str) or "WebSocketResponse" in client_id or "<" in client_id or ">" in client_id:
                # Invalid client_id (likely a WebSocket object string repr), show disabled button
                kick_btn = QPushButton("🚫 Kick")
                kick_btn.setFixedWidth(80)
                kick_btn.setToolTip("Invalid client ID - cannot kick")
                kick_btn.setEnabled(False)
            else:
                # Kick button
                kick_btn = QPushButton("🚫 Kick")
                kick_btn.setFixedWidth(80)
                kick_btn.setToolTip("Kick client and add IP to block list")
                kick_btn.clicked.connect(
                    lambda _, cid=client_id, ip=c.get("ip"): self._kick_client(cid, ip)
                )
            self.table.setCellWidget(row, 2, kick_btn)

    def _kick_client(self, client_id, client_ip):
        # Validate client_id before making request
        if not client_id or not isinstance(client_id, str) or "WebSocketResponse" in client_id or "<" in client_id or ">" in client_id:
            safe_print(f"Kick failed: invalid client_id: {client_id!r}")
            return

        def do_kick():
            try:
                req = urq.Request(
                    f"http://127.0.0.1:{self._port}/api/clients/{client_id}/kick",
                    method="POST",
                    headers={"Content-Type": "application/json"},
                )
                with urq.urlopen(req, timeout=5) as resp:
                    result = json.loads(resp.read())
                safe_print(f"Kick result: {result}")
                # Refresh after kick
                self._refresh()
            except Exception as e:
                safe_print(f"Kick failed: {e}")
                # Show error to user on main thread
                QMetaObject.invokeMethod(
                    self,
                    "_show_kick_error",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(str, str(e)),
                )

    @pyqtSlot(str)
    def _show_kick_error(self, error_msg):
        QMessageBox.warning(self, "Kick Failed", f"Failed to kick client:\n{error_msg}")
