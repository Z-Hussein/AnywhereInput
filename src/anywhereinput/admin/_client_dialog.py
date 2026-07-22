"""ClientListDialog - connected clients viewer."""

import json
import threading
import urllib.request as urq

from anywhereinput._constants import DEFAULT_PORT
from anywhereinput.logging_config import get_logger
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

log = get_logger(__name__)


class ClientListDialog(QDialog):
    """Shows currently connected WebSocket clients with kick option."""

    def __init__(self, port: int = DEFAULT_PORT, parent=None):
        super().__init__(parent)
        self._port = port
        self.setWindowTitle("Connected Clients")
        self.setFixedWidth(550)
        self.setMinimumHeight(400)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["IP Address", "Token", "Action"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(refresh_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    @pyqtSlot()
    def _refresh(self):
        def fetch():
            try:
                req = urq.Request(f"http://127.0.0.1:{self._port}/api/clients")
                with urq.urlopen(req, timeout=2) as resp:
                    data = json.loads(resp.read())

                clients = data.get("clients", [])
                QMetaObject.invokeMethod(
                    self,
                    "_update_table",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(list, clients),
                )
            except Exception as e:
                QMetaObject.invokeMethod(
                    self,
                    "_update_table",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(list, []),
                )
                log.error("Error fetching clients: %s", e)

        threading.Thread(target=fetch, daemon=True).start()

    @pyqtSlot(list)
    def _update_table(self, clients):
        """Update the client table - must be called on main thread."""
        self.table.setRowCount(len(clients))
        for row, c in enumerate(clients):
            ip_item = QTableWidgetItem(c.get("ip", "unknown"))
            self.table.setItem(row, 0, ip_item)

            token = c.get("token", "unknown")
            token_item = QTableWidgetItem(token)
            token_item.setToolTip(c.get("full_token", ""))
            self.table.setItem(row, 1, token_item)

            client_id = c.get("id", "")
            if (
                not client_id
                or not isinstance(client_id, str)
                or "WebSocketResponse" in client_id
                or "<" in client_id
                or ">" in client_id
            ):
                kick_btn = QPushButton("Kick")
                kick_btn.setFixedWidth(60)
                kick_btn.setStyleSheet(
                    "QPushButton {"
                    "  background: #334155;"
                    "  color: #64748b;"
                    "  border: 1px solid #475569;"
                    "  border-radius: 3px;"
                    "  font-size: 11px;"
                    "}"
                )
                kick_btn.setToolTip("Invalid client ID - cannot kick")
                kick_btn.setEnabled(False)
            else:
                kick_btn = QPushButton("Kick")
                kick_btn.setFixedWidth(60)
                kick_btn.setStyleSheet(
                    "QPushButton {"
                    "  background: #991b1b;"
                    "  color: white;"
                    "  border: none;"
                    "  border-radius: 3px;"
                    "  font-size: 11px;"
                    "  font-weight: bold;"
                    "}"
                    "QPushButton:hover { background: #b91c1c; }"
                )
                kick_btn.setToolTip("Kick client")
                kick_btn.clicked.connect(
                    lambda _, cid=client_id, ip=c.get("ip"): self._kick_client(cid, ip)
                )
            self.table.setCellWidget(row, 2, kick_btn)

    def _kick_client(self, client_id, client_ip):
        if (
            not client_id
            or not isinstance(client_id, str)
            or "WebSocketResponse" in client_id
            or "<" in client_id
            or ">" in client_id
        ):
            log.error("Kick failed: invalid client_id: %r", client_id)
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
                log.info("Kick result: %s", result)
                if result.get("ok"):
                    QMetaObject.invokeMethod(
                        self, "_refresh", Qt.ConnectionType.QueuedConnection
                    )
            except urq.HTTPError as http_err:
                # 404 means the client already disconnected between list and kick
                status = http_err.code if hasattr(http_err, "code") else ""
                msg = f"Client already disconnected (was no longer connected)" if status == 404 else f"Kick failed (HTTP {status})"
                log.warning("Kick HTTP error: %s", http_err)
                QMetaObject.invokeMethod(
                    self,
                    "_show_kick_error",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(str, msg),
                )
            except Exception as e:
                log.error("Kick failed: %s", e)
                QMetaObject.invokeMethod(
                    self,
                    "_show_kick_error",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(str, str(e)),
                )

        threading.Thread(target=do_kick, daemon=True).start()

    @pyqtSlot(str)
    def _show_kick_error(self, error_msg):
        QMessageBox.warning(self, "Kick Failed", f"Failed to kick client:\n{error_msg}")
