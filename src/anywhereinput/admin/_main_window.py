"""MainWindow - main admin window with tabs."""

import json
import re

from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QIcon

from ._token_store import TokenStore
from ._server_worker import ServerProcessWorker
from ._settings_panel import SettingsPanel
from ._token_dialog import TokenManagerDialog
from ._approval_dialog import ApprovalDialog


def _get_icon_path() -> str:
    """Get path to the favicon.ico for use as app icon."""
    from pathlib import Path
    # When installed, static files are in package
    pkg_static = Path(__file__).resolve().parent.parent / "static" / "favicon.ico"
    if pkg_static.exists():
        return str(pkg_static)
    # Development: project root/static
    dev_static = Path(__file__).resolve().parents[3] / "src" / "anywhereinput" / "static" / "favicon.ico"
    if dev_static.exists():
        return str(dev_static)
    return ""


class MainWindow(QMainWindow):
    """Main admin window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AnywhereInput - Admin")
        self.setMinimumSize(700, 550)
        # Set window icon from favicon.ico
        icon_path = _get_icon_path()
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))
        self._store = TokenStore()
        self._server_thread = None
        self._info_dialog = None
        self.init_ui()

    def init_ui(self):
        # Set window icon for taskbar/dock
        icon_path = _get_icon_path()
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        # Left panel - status + controls
        left = QVBoxLayout()

        # Info button - top-left corner above engine status
        info_btn = QPushButton("\u2139\ufe0f", clicked=self._show_info)
        info_btn.setFixedSize(32, 32)
        info_btn.setToolTip("App Guide & Info")
        info_btn.setStyleSheet(
            "QPushButton {"
            "  background: #1e293b;"
            "  border: 1px solid #334155;"
            "  border-radius: 6px;"
            "  font-size: 16px;"
            "}"
            "QPushButton:hover { background: #334155; }"
        )
        left.addWidget(info_btn)

        # Engine status
        status_group = QGroupBox("Engine Status")
        status_ly = QVBoxLayout(status_group)
        self.status_lbl = QLabel("● Offline")
        self.status_lbl.setFont(QFont("Sans", 12, QFont.Weight.Bold))
        self.status_lbl.setStyleSheet("color: gray;")
        self.url_lbl = QLabel("Server URL: -")
        self.url_lbl.setFont(QFont("Monospace", 9))
        status_ly.addWidget(self.status_lbl)
        status_ly.addWidget(self.url_lbl)
        left.addWidget(status_group)

        # Server controls
        ctrl_group = QGroupBox("Server Control")
        ctrl_ly = QVBoxLayout(ctrl_group)
        self.start_btn = QPushButton("▶ Start Server", clicked=self._start_server)
        self.stop_btn = QPushButton("■ Stop Server", clicked=self._stop_server)
        self.stop_btn.setEnabled(False)
        ctrl_ly.addWidget(self.start_btn)
        ctrl_ly.addWidget(self.stop_btn)
        left.addWidget(ctrl_group)

        # Server settings
        self.settings_panel = SettingsPanel()
        left.addWidget(self.settings_panel)

        left.addStretch()
        main_layout.addLayout(left, 1)

        # Right panel - tabs for tokens + logs
        right_tabs = QTabWidget()

        # -- Tokens tab --------------------------------------------------------
        token_tab = QWidget()
        token_ly = QVBoxLayout(token_tab)

        self.token_table = QTableWidget()
        self.token_table.setColumnCount(6)
        self.token_table.setHorizontalHeaderLabels(
            ["Select", "Name", "Token", "Permissions", "IPs", "Actions"]
        )
        self.token_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        for col in range(self.token_table.columnCount()):
            header_item = self.token_table.horizontalHeaderItem(col)
            if header_item:
                header_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        header = self.token_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        token_ly.addWidget(self.token_table)

        token_btns = QHBoxLayout()
        token_btns.addWidget(QPushButton("+ New Token", clicked=self._new_token))
        token_btns.addWidget(QPushButton("Select All", clicked=self._select_all_tokens))
        token_btns.addWidget(QPushButton("Clear Select", clicked=self._clear_selection))
        token_btns.addWidget(
            QPushButton("Remove Selected", clicked=self._remove_selected_multi)
        )
        token_btns.addWidget(QPushButton("🔄 Refresh", clicked=self._refresh_tokens))
        token_btns.addStretch()
        token_ly.addLayout(token_btns)

        right_tabs.addTab(token_tab, "🔑 Tokens")

        # -- Clients tab -------------------------------------------------------
        clients_tab = QWidget()
        clients_ly = QVBoxLayout(clients_tab)

        # Pending requests section
        pending_group = QGroupBox("🔒 Pending Connection Requests")
        pending_ly = QVBoxLayout(pending_group)
        self.pending_lbl = QLabel("Loading...")
        self.pending_lbl.setWordWrap(True)
        pending_ly.addWidget(self.pending_lbl)

        self.pending_table = QTableWidget()
        self.pending_table.setColumnCount(6)
        self.pending_table.setHorizontalHeaderLabels(
            ["Name", "IP", "Status", "Age", "Token", "Actions"]
        )
        header = self.pending_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.pending_table.setMinimumHeight(120)
        pending_ly.addWidget(self.pending_table)

        req_btns = QHBoxLayout()
        req_btns.addWidget(
            QPushButton("🔄 Refresh Requests", clicked=self._refresh_requests)
        )
        req_btns.addStretch()
        pending_ly.addLayout(req_btns)
        clients_ly.addWidget(pending_group)

        # Separator
        spacer = QFrame()
        spacer.setFrameShape(QFrame.Shape.HLine)
        spacer.setFrameShadow(QFrame.Shadow.Sunken)
        clients_ly.addWidget(spacer)

        # Connected clients section
        clients_header = QHBoxLayout()
        self.clients_lbl = QLabel("Click 'Refresh' to check connected clients...")
        self.clients_lbl.setWordWrap(True)
        clients_header.addWidget(self.clients_lbl)
        clients_header.addStretch()
        manage_btn = QPushButton("👥 Manage Clients", clicked=self._open_client_dialog)
        manage_btn.setToolTip("Open client manager with kick/block options")
        clients_header.addWidget(manage_btn)
        clients_ly.addLayout(clients_header)
        refresh_btn = QPushButton("Refresh", clicked=self._refresh_clients)
        clients_ly.addWidget(refresh_btn)

        right_tabs.addTab(clients_tab, "👥 Clients")

        # -- Logs tab ------------------------------------------------------------
        logs_tab = QWidget()
        logs_ly = QVBoxLayout(logs_tab)
        self.log_text = QTextEdit()
        self.log_text.setFont(QFont("Monospace", 9))
        self.log_text.setReadOnly(True)
        logs_ly.addWidget(self.log_text)

        clear_btn = QPushButton("Clear Logs", clicked=self.log_text.clear)
        logs_ly.addWidget(clear_btn)

        right_tabs.addTab(logs_tab, "📋 Logs")

        main_layout.addWidget(right_tabs, 2)

    # -- Guide / Info panel -------------------------------------------------

    def _show_info(self):
        """Show/hide the info/guide panel."""
        if self._info_dialog is None:
            self._info_dialog = QDialog(self)
            self._info_dialog.setWindowTitle("AnywhereInput - Guide")
            self._info_dialog.setMinimumSize(520, 620)
            layout = QVBoxLayout(self._info_dialog)
            from ._info_panel import InfoPanel

            self.info_text = InfoPanel()
            layout.addWidget(self.info_text)
            close_btn = QPushButton("Close", clicked=self._info_dialog.accept)
            layout.addWidget(close_btn)
        self._info_dialog.show()
        self._info_dialog.raise_()
        self._info_dialog.activateWindow()

    # -- Server controls -----------------------------------------------------

    def _start_server(self):
        params = self.settings_panel.get_params()
        port = params["port"]
        tunnel = params["tunnel"]

        if self._server_thread and self._server_thread.isRunning():
            QMessageBox.warning(self, "Warning", "Server is already running!")
            return

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_lbl.setText(f"● Starting (tunnel: {tunnel})...")
        self.status_lbl.setStyleSheet("color: orange;")

        self._server_thread = ServerProcessWorker(
            port=port,
            tunnel=tunnel,
            fps=params["fps"],
            quality=params["quality"],
            scale=params["scale"],
        )
        self._server_thread.log_signal.connect(self._on_log)
        self._server_thread.status_signal.connect(self._on_status_changed)
        self._server_thread.start()

    def _stop_server(self):
        if self._server_thread and self._server_thread.isRunning():
            self._server_thread.stop()
            self._server_thread.wait(10)
            self._server_thread = None

        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_lbl.setText("● Offline")
        self.status_lbl.setStyleSheet("color: gray;")
        self.url_lbl.setText("Server URL: -")
        self.log_text.append("[INFO] Server stopped manually.")

    def _on_log(self, text: str):
        self.log_text.append(text)
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
        if "Local:" in text or "http://" in text.lower():
            match = re.search(r"(https?://[^\s]+)", text)
            if match:
                url = match.group(1)
                self.url_lbl.setText(f"Server URL: {url}")

    def _on_status_changed(self, status: str):
        if status == "running":
            self.status_lbl.setText("● Running")
            self.status_lbl.setStyleSheet("color: #22c55e;")
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
        elif status == "stopped":
            self.status_lbl.setText("● Stopped")
            self.status_lbl.setStyleSheet("color: gray;")
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

    # -- Token management ----------------------------------------------------

    def _refresh_tokens(self):
        try:
            import urllib.request as urq

            req = urq.Request(
                f"http://127.0.0.1:{self.settings_panel.get_params()['port']}/api/tokens"
            )
            with urq.urlopen(req, timeout=2) as resp:
                data = json.loads(resp.read())
            tokens = data.get("tokens", [])
        except Exception:
            tokens = self._store.list_all()
        self.token_table.setRowCount(len(tokens))
        for i, t in enumerate(tokens):
            cb = QTableWidgetItem()
            cb.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            cb.setCheckState(Qt.CheckState.Unchecked)
            self.token_table.setItem(i, 0, cb)
            self.token_table.setItem(i, 1, QTableWidgetItem(t["name"]))
            token_item = QTableWidgetItem(t.get("token", "?"))
            token_item.setToolTip(t.get("full_token", "N/A"))
            self.token_table.setItem(i, 2, token_item)
            self.token_table.setItem(
                i, 3, QTableWidgetItem(", ".join(t.get("permissions", [])))
            )
            ips = t.get("allowed_ips", [])
            ip_text = "\n".join(ips) if ips else "(allow all)"
            self.token_table.setItem(i, 4, QTableWidgetItem(ip_text))
            self.token_table.setCellWidget(
                i, 5, self._make_action_widget(i, t.get("full_token", ""))
            )

    def _make_action_widget(self, row, full_token):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        edit_btn = QPushButton("✏️")
        edit_btn.setFixedSize(24, 24)
        edit_btn.setToolTip("Edit")
        revoke_btn = QPushButton("🗑️")
        revoke_btn.setFixedSize(24, 24)
        revoke_btn.setToolTip("Revoke this token")
        copy_btn = QPushButton("📋")
        copy_btn.setFixedSize(24, 24)
        copy_btn.setToolTip("Copy token")

        edit_btn.clicked.connect(lambda _, r=row: self._edit_token_by_row(r))
        revoke_btn.clicked.connect(lambda _, t=full_token: self._revoke_token(t))
        copy_btn.clicked.connect(lambda _, t=full_token: self._copy_token(t))

        layout.addWidget(edit_btn)
        layout.addWidget(revoke_btn)
        layout.addWidget(copy_btn)
        return widget

    def _new_token(self):
        port = self.settings_panel.get_params()["port"]
        dlg = TokenManagerDialog(self._store, port=port)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._refresh_tokens()

    def _edit_token_by_row(self, row: int, port: int = 8008):
        full_tok = (
            self.token_table.item(row, 2).toolTip()
            if self.token_table.item(row, 2)
            else None
        )
        if not full_tok or full_tok.endswith("..."):
            QMessageBox.information(
                self,
                "Info",
                "Cannot edit from masked display. Delete and create a new token.",
            )
            return
        name = (
            self.token_table.item(row, 1).text()
            if self.token_table.item(row, 1)
            else ""
        )
        dlg = TokenManagerDialog(self._store, port=port, existing_token=full_tok)
        dlg.name_input.setText(name)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._refresh_tokens()

    def _revoke_token(self, full_token: str):
        name = None
        for row in range(self.token_table.rowCount()):
            item = self.token_table.item(row, 2)
            if item and item.toolTip() == full_token:
                name = self.token_table.item(row, 1).text()
                break
        ok = QMessageBox.question(
            self,
            "Confirm Revoke",
            f'Remove token "{name}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ok == QMessageBox.StandardButton.Yes:
            try:
                import urllib.request as urq

                port = self.settings_panel.get_params()["port"]
                req = urq.Request(
                    f"http://127.0.0.1:{port}/api/tokens/{full_token}",
                    method="DELETE",
                )
                with urq.urlopen(req, timeout=5) as resp:
                    json.loads(resp.read())
                self._refresh_tokens()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to revoke token: {e}")

    def _copy_token(self, full_token: str):
        qapp = QApplication.instance()
        cb = qapp.clipboard()  # type: ignore[union-attr]
        cb.setText(full_token)
        QMessageBox.information(self, "Copied", "Token copied to clipboard.")

    # -- Multi-select helpers --------------------------------------------------

    def _select_all_tokens(self):
        for row in range(self.token_table.rowCount()):
            item = self.token_table.item(row, 0)
            if item:
                item.setCheckState(Qt.CheckState.Checked)

    def _clear_selection(self):
        for row in range(self.token_table.rowCount()):
            item = self.token_table.item(row, 0)
            if item:
                item.setCheckState(Qt.CheckState.Unchecked)

    def _remove_selected_multi(self):
        checked_rows = []
        for row in range(self.token_table.rowCount()):
            item = self.token_table.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                token_item = self.token_table.item(row, 2)
                full_tok = token_item.toolTip() if token_item else None
                name = (
                    self.token_table.item(row, 1).text()
                    if self.token_table.item(row, 1)
                    else "?"
                )
                if full_tok and not full_tok.endswith("..."):
                    checked_rows.append((row, full_tok, name))

        if not checked_rows:
            QMessageBox.warning(self, "Warning", "No tokens selected.")
            return

        count = len(checked_rows)
        plural = "s" if count > 1 else ""
        token_list = "\n".join(f"  - {name}" for _, _, name in checked_rows)
        ok = QMessageBox.question(
            self,
            "Confirm Remove",
            f"Remove {count} token{plural}?\n\n{token_list}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ok != QMessageBox.StandardButton.Yes:
            return

        port = self.settings_panel.get_params()["port"]
        import urllib.request as urq

        success_count = 0
        errors = []
        for row, full_tok, name in checked_rows:
            try:
                req = urq.Request(
                    f"http://127.0.0.1:{port}/api/tokens/{full_tok}",
                    method="DELETE",
                )
                with urq.urlopen(req, timeout=5) as resp:
                    json.loads(resp.read())
                success_count += 1
            except Exception as e:
                errors.append(f"  - {name}: {e}")

        for row, _, _ in checked_rows:
            item = self.token_table.item(row, 0)
            if item:
                item.setCheckState(Qt.CheckState.Unchecked)

        self._refresh_tokens()

        if success_count > 0:
            plural = "s" if success_count > 1 else ""
            msg = f"Removed {success_count} token{plural}."
            if errors:
                msg += f"\n\nFailed:\n{chr(10).join(errors)}"
            QMessageBox.information(self, "Done", msg)
        elif errors:
            QMessageBox.warning(
                self, "Error", "All removals failed:\n" + "\n".join(errors)
            )

    # -- Client monitoring ---------------------------------------------------

    def _refresh_clients(self):
        try:
            import urllib.request as urq

            port = self.settings_panel.get_params()["port"]
            req = urq.Request(f"http://127.0.0.1:{port}/api/clients")
            with urq.urlopen(req, timeout=2) as resp:
                data = json.loads(resp.read())

            count = data.get("count", 0)
            clients = data.get("clients", [])

            lines = [f"Connected Clients: {count}"]
            if clients:
                for c in clients:
                    lines.append(f"  - IP: {c.get('ip', 'unknown')}")
            else:
                lines.append("  (no clients connected)")

            eng_req = urq.Request(f"http://127.0.0.1:{port}/api/engine")
            with urq.urlopen(eng_req, timeout=2) as resp:
                eng_data = json.loads(resp.read())
            lines.append("")
            lines.append(f"Engine: {eng_data.get('state', '?')}")
            screen = eng_data.get("screen_engine", {})
            lines.append(
                f"Screen: {screen.get('state', '?')} "
                f"({'enabled' if screen.get('enabled') else 'disabled'})"
            )

            self.clients_lbl.setText("\n".join(lines))
        except Exception as e:
            self.clients_lbl.setText(f"Server is not running:\n{e}")

    def _open_client_dialog(self):
        from ._client_dialog import ClientListDialog

        dlg = ClientListDialog(
            port=self.settings_panel.get_params()["port"], parent=self
        )
        dlg.exec()

    def _refresh_requests(self):
        """Fetch and display pending connection requests."""
        try:
            import urllib.request as urq

            port = self.settings_panel.get_params()["port"]
            req = urq.Request(f"http://127.0.0.1:{port}/api/requests")
            with urq.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read())

            requests_list = data.get("requests", [])
            self.pending_table.setRowCount(len(requests_list))
            for i, req_item in enumerate(requests_list):
                name_item = QTableWidgetItem(req_item.get("client_name", "?"))
                name_item.setData(
                    Qt.ItemDataRole.UserRole, req_item.get("request_id", "")
                )
                self.pending_table.setItem(i, 0, name_item)
                self.pending_table.setItem(
                    i, 1, QTableWidgetItem(req_item.get("ip", "?"))
                )
                status = req_item.get("status", "pending")
                status_item = QTableWidgetItem(status)
                if status == "approved":
                    status_item.setForeground(QColor("#22c55e"))
                elif status == "declined":
                    status_item.setForeground(QColor("#ef4444"))
                else:
                    status_item.setForeground(QColor("#f59e0b"))
                self.pending_table.setItem(i, 2, status_item)
                age = req_item.get("age_seconds", 0)
                if age < 60:
                    age_str = f"{int(age)}s"
                elif age < 3600:
                    age_str = f"{int(age) // 60}m {int(age) % 60}s"
                else:
                    age_str = f"{int(age) // 3600}h"
                self.pending_table.setItem(i, 3, QTableWidgetItem(age_str))
                token = req_item.get("token", "")
                if token:
                    tok_item = QTableWidgetItem(token[:16] + "...")
                    tok_item.setToolTip(token)
                    self.pending_table.setItem(i, 4, tok_item)
                else:
                    self.pending_table.setItem(i, 4, QTableWidgetItem("(pending)"))
                self.pending_table.setCellWidget(
                    i, 5, self._make_request_action_widget(i, req_item)
                )

            if not requests_list:
                self.pending_lbl.setText("No pending requests.")
        except Exception as e:
            self.pending_lbl.setText(f"Server is not running:\n{e}")

    def _make_request_action_widget(self, row, req):
        """Create approve/decline/copy buttons for a request row."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        if req.get("status") == "pending":
            approve_btn = QPushButton(
                "✅", clicked=lambda _, r=row: self._approve_request(r)
            )
            approve_btn.setFixedSize(28, 28)
            approve_btn.setToolTip("Approve connection")
            decline_btn = QPushButton(
                "❌", clicked=lambda _, r=row: self._decline_request(r)
            )
            decline_btn.setFixedSize(28, 28)
            decline_btn.setToolTip("Decline connection")
            layout.addWidget(approve_btn)
            layout.addWidget(decline_btn)
        elif req.get("status") == "approved" and req.get("token"):
            copy_btn = QPushButton(
                "📋", clicked=lambda _, t=req["token"]: self._copy_token(t)
            )
            copy_btn.setFixedSize(28, 28)
            copy_btn.setToolTip("Copy token to clipboard")
            layout.addWidget(copy_btn)

        return widget

    def _approve_request(self, row):
        """Approve a pending connection request with optional custom token."""
        name_item = self.pending_table.item(row, 0)
        req_id = name_item.data(Qt.ItemDataRole.UserRole) if name_item else None
        client_name = name_item.text() if name_item else "?"

        if not req_id:
            QMessageBox.warning(self, "Error", "Could not find request ID.")
            return

        port = self.settings_panel.get_params()["port"]

        auto_token = None
        try:
            import urllib.request as urq

            req_urq = urq.Request(f"http://127.0.0.1:{port}/api/requests")
            with urq.urlopen(req_urq, timeout=3) as resp:
                data = json.loads(resp.read())
            for r in data.get("requests", []):
                if r.get("request_id") == req_id and r.get("status") == "pending":
                    auto_token = self._get_request_token(req_id)
                    break
        except Exception:
            pass

        dlg = ApprovalDialog(self, client_name, port, req_id, auto_token or "")
        if dlg.exec() == QDialog.DialogCode.Accepted:
            use_custom = dlg.custom_mode()  # noqa: F841
            custom_token = dlg.get_custom_token()
            permissions = dlg.get_permissions()

            try:
                import urllib.request as urq

                body = {}
                if custom_token:
                    body["token"] = custom_token
                body["permissions"] = permissions
                data = json.dumps(body).encode()
                req_urq = urq.Request(
                    f"http://127.0.0.1:{port}/api/requests/{req_id}/approve",
                    data=data,
                    headers={"Content-Type": "application/json"},
                    method="PATCH",
                )
                with urq.urlopen(req_urq, timeout=5) as resp:
                    result = json.loads(resp.read())
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to approve: {e}")
                return

            self._refresh_requests()

            token_val = result.get("token", "")
            QMessageBox.information(
                self,
                "Connection Approved",
                f"Approved for: {client_name}\n\nToken:\n{token_val}\n\n"
                "This token will not be shown again. Save it!",
            )

    def _get_request_token(self, req_id):
        """Helper to fetch pending request details including auto-token preview."""
        try:
            import urllib.request as urq

            port = self.settings_panel.get_params()["port"]
            req_urq = urq.Request(f"http://127.0.0.1:{port}/api/requests")
            with urq.urlopen(req_urq, timeout=3) as resp:
                data = json.loads(resp.read())
            for r in data.get("requests", []):
                if r.get("request_id") == req_id:
                    return r.get("token_preview", "") or ""
        except Exception:
            pass
        return ""

    def _decline_request(self, row):
        """Decline a pending connection request."""
        req_id = self.pending_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        client_name = self.pending_table.item(row, 0).text()

        ok = QMessageBox.question(
            self,
            "Confirm Decline",
            f'Decline connection request from "{client_name}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ok != QMessageBox.StandardButton.Yes:
            return

        try:
            import urllib.request as urq

            port = self.settings_panel.get_params()["port"]
            req_urq = urq.Request(
                f"http://127.0.0.1:{port}/api/requests/{req_id}/decline",
                method="PATCH",
            )
            with urq.urlopen(req_urq, timeout=5) as resp:
                json.loads(resp.read())
            self._refresh_requests()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to decline: {e}")
