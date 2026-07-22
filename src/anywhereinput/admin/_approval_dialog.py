"""ApprovalDialog - approve/decline connection request dialog."""

import json
import logging
import secrets
from typing import Dict

from anywhereinput._constants import DEFAULT_PORT
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)


class ApprovalDialog(QDialog):
    """Dialog for approving a connection request with options for auto or custom token."""

    log = logging.getLogger("anywhereinput.admin.approval")

    def __init__(
        self,
        parent,
        client_name: str,
        port: int = DEFAULT_PORT,
        req_id: str = "",
        auto_token_preview: str = "",
    ):
        super().__init__(parent)
        self._client_name = client_name
        self._port = port
        self._req_id = req_id
        self._auto_token_preview = auto_token_preview
        self._custom_mode = False
        self._custom_token = ""
        self._permissions: list = []
        self.setWindowTitle(f"Approve: {client_name}")
        self.setFixedWidth(460)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Info about the request
        info_box = QGroupBox("Client Request")
        info_ly = QVBoxLayout(info_box)
        info_ly.addWidget(QLabel(f"Name: {self._client_name}"))
        info_ly.addWidget(QLabel(f"Request ID: {self._req_id[:16]}..."))
        layout.addWidget(info_box)

        # Token choice radio buttons
        choice_group = QGroupBox("Token Options")
        choice_ly = QVBoxLayout(choice_group)

        self.auto_radio = QRadioButton("Use auto-generated session token (recommended)")
        self.auto_radio.setChecked(True)
        self.auto_radio.toggled.connect(self._on_mode_changed)
        choice_ly.addWidget(self.auto_radio)

        self.custom_radio = QRadioButton(
            "Create new custom token with specific permissions"
        )
        self.custom_radio.toggled.connect(self._on_mode_changed)
        choice_ly.addWidget(self.custom_radio)

        # Permission checkboxes
        perm_group = QGroupBox("Permissions")
        perm_ly = QVBoxLayout(perm_group)
        default_perms = ["move", "click", "scroll", "keyboard", "screen_toggle"]
        self.perm_checks: Dict[str, QCheckBox] = {}
        for p in default_perms:
            cb = QCheckBox(p)
            cb.setChecked(True)
            self.perm_checks[p] = cb
            perm_ly.addWidget(cb)

        perm_btns = QHBoxLayout()
        perm_btns.addWidget(QPushButton("All", clicked=self._check_all))
        perm_btns.addWidget(QPushButton("None", clicked=self._uncheck_all))
        perm_btns.addStretch()
        perm_ly.addLayout(perm_btns)
        choice_ly.addWidget(perm_group)

        # Custom token input (hidden unless custom mode selected)
        custom_group = QGroupBox("Custom Token Details (hidden unless selected)")
        custom_ly = QFormLayout(custom_group)
        custom_group.hide()

        self.token_name_input = QLineEdit()
        self.token_name_input.setPlaceholderText("My colleague - full access")
        custom_ly.addRow("Name:", self.token_name_input)

        self.custom_token_input = QLineEdit()
        self.custom_token_input.setPlaceholderText(
            "Auto-generate or paste your own (min 8 chars)"
        )
        custom_ly.addRow("Token Value:", self.custom_token_input)

        gen_btn = QPushButton("Generate Random")
        gen_btn.clicked.connect(self._generate_token)
        custom_ly.addRow("", gen_btn)

        choice_ly.addWidget(custom_group)
        layout.addWidget(choice_group)

        # Buttons
        approve_btn = QPushButton("Approve Connection")
        cancel_btn = QPushButton("Cancel")
        approve_btn.setStyleSheet(
            "background-color: #22c55e; color: white; font-weight: bold;"
            " padding: 8px; border-radius: 4px;"
        )
        cancel_btn.setStyleSheet("padding: 8px; border-radius: 4px;")
        approve_btn.clicked.connect(self._on_ok)
        cancel_btn.clicked.connect(self.reject)
        btn_ly = QHBoxLayout()
        btn_ly.addStretch()
        btn_ly.addWidget(approve_btn)
        btn_ly.addWidget(cancel_btn)
        layout.addLayout(btn_ly)

    def _generate_token(self):
        self.custom_token_input.setText(secrets.token_urlsafe(16))

    def _check_all(self):
        for cb in self.perm_checks.values():
            cb.setChecked(True)

    def _uncheck_all(self):
        for cb in self.perm_checks.values():
            cb.setChecked(False)

    def _on_mode_changed(self):
        self._custom_mode = self.custom_radio.isChecked()
        for child in self.findChildren(QGroupBox):
            if "Custom Token" in child.title():
                child.setVisible(self._custom_mode)
                break

    def _on_ok(self):
        if self._custom_mode:
            name = self.token_name_input.text().strip() or f"{self._client_name}_access"
            perms = [p for p, cb in self.perm_checks.items() if cb.isChecked()]
            tok_val = self.custom_token_input.text().strip()

            if not tok_val:
                try:
                    import urllib.request as urq

                    data = json.dumps({"name": name, "permissions": perms}).encode()
                    req_urq = urq.Request(
                        f"http://127.0.0.1:{self._port}/api/tokens",
                        data=data,
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    with urq.urlopen(req_urq, timeout=5) as resp:
                        result = json.loads(resp.read())
                    self._custom_token = result.get("token", "")
                except Exception as e:
                    QMessageBox.warning(
                        self, "Error", f"Failed to create custom token: {e}"
                    )
                    return
            else:
                if len(tok_val) < 8:
                    QMessageBox.warning(
                        self,
                        "Error",
                        "Custom token must be at least 8 characters.",
                    )
                    return
                self._custom_token = tok_val
                try:
                    import urllib.request as urq

                    data = json.dumps({"name": name, "permissions": perms}).encode()
                    req_urq = urq.Request(
                        f"http://127.0.0.1:{self._port}/api/tokens",
                        data=data,
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    with urq.urlopen(req_urq, timeout=5) as resp:
                        json.loads(resp.read())
                except Exception as e:
                    self.log.debug("Create token for approval failed: %s", e)
            self._permissions = perms if not tok_val else perms
        else:
            self._custom_token = ""
            self._permissions = []
        self.accept()

    def custom_mode(self) -> bool:
        return self._custom_mode

    def get_custom_token(self) -> str:
        return self._custom_token

    def get_permissions(self) -> list:
        """Return checked permissions - always available regardless of token mode."""
        return [p for p, cb in self.perm_checks.items() if cb.isChecked()]
