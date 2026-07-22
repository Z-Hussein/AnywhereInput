"""Pending requests, approve/decline cards."""

import json
import logging

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from .._approval_dialog import ApprovalDialog
from ._ui_helpers import make_empty_state

log = logging.getLogger("anywhereinput.admin")


def refresh_requests(window) -> None:
    """Fetch and display pending connection requests as cards."""
    try:
        import urllib.request as urq

        port = window.settings_panel.get_params()["port"]
        req = urq.Request(f"http://127.0.0.1:{port}/api/requests")
        with urq.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())

        requests_list = data.get("requests", [])
        window._current_requests = requests_list

        new_pending = [r for r in requests_list if r.get("status") == "pending"]
        window._pending_count = len(new_pending)
        window.pending_count_lbl.setText(str(len(new_pending)))

        for req_item in new_pending:
            req_id = req_item.get("id")
            if req_id and req_id not in window._notified_request_ids:
                window._notified_request_ids.add(req_id)
                if window._tray_icon:
                    from ._notifications import show_connection_notification

                    show_connection_notification(window, req_item)

        populate_pending_cards(window, requests_list)

    except Exception as e:
        while window.pending_layout.count():
            item = window.pending_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        err = QLabel(f"Server not running: {e}")
        err.setStyleSheet("color: #ef4444; padding: 12px; font-size: 11px;")
        err.setAlignment(Qt.AlignmentFlag.AlignCenter)
        window.pending_layout.addWidget(err)


def populate_pending_cards(window, requests_list) -> None:
    while window.pending_layout.count():
        item = window.pending_layout.takeAt(0)
        w = item.widget()
        if w:
            w.deleteLater()

    if not requests_list:
        empty = make_empty_state(
            icon="",
            title="No pending requests",
            description="When a new device connects, its approval request will appear here.",
        )
        window.pending_layout.addWidget(empty)
    else:
        for i, req_item in enumerate(requests_list):
            window.pending_layout.addWidget(make_request_card(window, i, req_item))
        window.pending_layout.addStretch()


def filter_pending(window, text: str) -> None:
    text = text.lower()
    if not text:
        populate_pending_cards(window, window._current_requests)
        return
    filtered = [
        r
        for r in window._current_requests
        if text in r.get("client_name", "").lower()
        or text in r.get("ip", "").lower()
        or text in r.get("status", "").lower()
    ]
    populate_pending_cards(window, filtered)


def make_request_card(window, row, req) -> QWidget:
    status = req.get("status", "pending")
    card = QWidget()
    card.setStyleSheet(
        "QWidget {"
        "  background: #1e293b;"
        "  border: 1px solid #334155;"
        "  border-radius: 6px;"
        "}"
    )
    card_layout = QHBoxLayout(card)
    card_layout.setContentsMargins(10, 8, 10, 8)
    card_layout.setSpacing(10)

    icons = {"pending": "🟠", "approved": "🟢", "declined": "🔴"}
    icon = QLabel(icons.get(status, "⚪"))
    icon.setFont(QFont("Sans", 16))
    card_layout.addWidget(icon)

    info = QVBoxLayout()
    info.setSpacing(1)
    name_lbl = QLabel(req.get("client_name", "?"))
    name_lbl.setFont(QFont("Sans", 11, QFont.Weight.Bold))
    name_lbl.setStyleSheet("color: #e2e8f0; background: transparent;")
    info.addWidget(name_lbl)

    ip = req.get("ip", "?")
    age = req.get("age_seconds", 0)
    if age < 60:
        age_str = f"{int(age)}s ago"
    elif age < 3600:
        age_str = f"{int(age) // 60}m {int(age) % 60}s ago"
    else:
        age_str = f"{int(age) // 3600}h ago"

    status_labels = {
        "pending": "Waiting approval",
        "approved": "Connected",
        "declined": "Declined",
    }
    status_colors = {"pending": "#f59e0b", "approved": "#22c55e", "declined": "#ef4444"}

    detail = QLabel(f"{ip}  ·  {age_str}")
    detail.setStyleSheet("color: #94a3b8; font-size: 10px; background: transparent;")
    info.addWidget(detail)

    status_lbl = QLabel(f"{status_labels.get(status, status)}  ·  {age_str}")
    status_lbl.setStyleSheet(
        f"color: {status_colors.get(status, '#94a3b8')}; font-size: 10px; background: transparent;"
    )
    info.addWidget(status_lbl)

    card_layout.addLayout(info, 1)

    token = req.get("token", "")
    if token:
        tok_lbl = QLabel(f"••••{token[-4:]}")
        tok_lbl.setFont(QFont("Monospace", 9))
        tok_lbl.setStyleSheet("color: #64748b; background: transparent;")
        tok_lbl.setToolTip(token)
        card_layout.addWidget(tok_lbl)

    if status == "pending":
        approve_btn = QPushButton("Approve")
        approve_btn.setFixedSize(64, 24)
        approve_btn.setToolTip("Approve connection")
        approve_btn.setStyleSheet(
            "QPushButton {"
            "  background: #166534;"
            "  color: white;"
            "  border-radius: 4px;"
            "  font-size: 10px;"
            "  font-weight: bold;"
            "}"
            "QPushButton:hover { background: #15803d; }"
        )
        approve_btn.clicked.connect(lambda _, r=row: approve_request(window, r))
        card_layout.addWidget(approve_btn)

        decline_btn = QPushButton("Decline")
        decline_btn.setFixedSize(56, 24)
        decline_btn.setToolTip("Decline connection")
        decline_btn.setStyleSheet(
            "QPushButton {"
            "  background: #991b1b;"
            "  color: white;"
            "  border-radius: 4px;"
            "  font-size: 10px;"
            "  font-weight: bold;"
            "}"
            "QPushButton:hover { background: #b91c1c; }"
        )
        decline_btn.clicked.connect(lambda _, r=row: decline_request(window, r))
        card_layout.addWidget(decline_btn)
    elif status == "approved" and token:
        from ._token_management import copy_token

        copy_btn = QPushButton("Copy")
        copy_btn.setFixedSize(44, 24)
        copy_btn.setToolTip("Copy token")
        copy_btn.setStyleSheet(
            "QPushButton {"
            "  background: #1e293b;"
            "  border: 1px solid #334155;"
            "  border-radius: 3px;"
            "  color: #94a3b8;"
            "  font-size: 10px;"
            "}"
            "QPushButton:hover { background: #334155; }"
        )
        copy_btn.clicked.connect(lambda _, t=token: copy_token(window, t))
        card_layout.addWidget(copy_btn)

    return card


def approve_request(window, row) -> None:
    if row >= len(window._current_requests):
        return
    req = window._current_requests[row]
    req_id = req.get("request_id")
    client_name = req.get("client_name", "?")

    if not req_id:
        QMessageBox.warning(window, "Error", "Could not find request ID.")
        return

    port = window.settings_panel.get_params()["port"]

    auto_token = None
    try:
        import urllib.request as urq

        req_urq = urq.Request(f"http://127.0.0.1:{port}/api/requests")
        with urq.urlopen(req_urq, timeout=3) as resp:
            data = json.loads(resp.read())
        for r in data.get("requests", []):
            if r.get("request_id") == req_id and r.get("status") == "pending":
                auto_token = get_request_token(window, req_id)
                break
    except Exception as e:
        log.debug("Fetch auto token failed: %s", e)

    dlg = ApprovalDialog(window, client_name, port, req_id, auto_token or "")
    if dlg.exec() == 1:
        custom_token = dlg.get_custom_token()
        permissions = dlg.get_permissions()

        try:
            import urllib.request as urq

            body: dict = {}
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
            QMessageBox.warning(window, "Error", f"Failed to approve: {e}")
            return

        refresh_requests(window)

        token_val = result.get("token", "")
        QMessageBox.information(
            window,
            "Connection Approved",
            f"Approved for: {client_name}\n\nToken:\n{token_val}\n\n"
            "This token will not be shown again. Save it!",
        )


def get_request_token(window, req_id) -> str:
    try:
        import urllib.request as urq

        port = window.settings_panel.get_params()["port"]
        req_urq = urq.Request(f"http://127.0.0.1:{port}/api/requests")
        with urq.urlopen(req_urq, timeout=3) as resp:
            data = json.loads(resp.read())
        for r in data.get("requests", []):
            if r.get("request_id") == req_id:
                return r.get("token_preview", "") or ""
    except Exception as e:
        log.debug("Fetch request token failed: %s", e)
    return ""


def decline_request(window, row) -> None:
    if row >= len(window._current_requests):
        return
    req = window._current_requests[row]
    req_id = req.get("request_id")
    client_name = req.get("client_name", "?")

    ok = QMessageBox.question(
        window,
        "Confirm Decline",
        f'Decline connection request from "{client_name}"?',
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    if ok != QMessageBox.StandardButton.Yes:
        return

    try:
        import urllib.request as urq

        port = window.settings_panel.get_params()["port"]
        req_urq = urq.Request(
            f"http://127.0.0.1:{port}/api/requests/{req_id}/decline",
            method="PATCH",
        )
        with urq.urlopen(req_urq, timeout=5) as resp:
            json.loads(resp.read())
        refresh_requests(window)
    except Exception as e:
        QMessageBox.warning(window, "Error", f"Failed to decline: {e}")
