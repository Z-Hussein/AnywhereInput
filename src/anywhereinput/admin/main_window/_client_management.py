"""Client cards, filtering, kick/block, context menu."""

import json
import logging

from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMenu,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ._ui_helpers import make_empty_state

log = logging.getLogger("anywhereinput.admin")


def refresh_clients(window) -> None:
    try:
        import urllib.request as urq

        port = window.settings_panel.get_params()["port"]
        req = urq.Request(f"http://127.0.0.1:{port}/api/clients")
        with urq.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read())

        clients = data.get("clients", [])
        window._current_clients = clients
        populate_client_cards(window, clients)

    except Exception as e:
        window._current_clients = []
        populate_client_cards_error(window, e)


def populate_client_cards(window, clients) -> None:
    while window.clients_layout.count():
        item = window.clients_layout.takeAt(0)
        w = item.widget()
        if w:
            w.deleteLater()

    if not clients:
        from ._server_control import copy_server_url

        empty = make_empty_state(
            icon="",
            title="No connected clients",
            description="Start the server and open the browser URL to connect.",
            button_text="Copy URL",
            button_callback=lambda: copy_server_url(window),
        )
        window.clients_layout.addWidget(empty)
    else:
        for c in clients:
            window.clients_layout.addWidget(make_client_card(window, c))
        window.clients_layout.addStretch()


def populate_client_cards_error(window, e) -> None:
    while window.clients_layout.count():
        item = window.clients_layout.takeAt(0)
        w = item.widget()
        if w:
            w.deleteLater()
    err = QLabel(f"Server not running: {e}")
    err.setStyleSheet("color: #ef4444; padding: 12px; font-size: 11px;")
    err.setAlignment(Qt.AlignmentFlag.AlignCenter)
    window.clients_layout.addWidget(err)


def filter_clients(window, text: str) -> None:
    text = text.lower()
    if not text:
        populate_client_cards(window, window._current_clients)
        return
    filtered = [
        c
        for c in window._current_clients
        if text in c.get("ip", "").lower() or text in c.get("token", "").lower()
    ]
    populate_client_cards(window, filtered)


def make_client_card(window, client) -> QWidget:
    card = QWidget()
    card.setStyleSheet(
        "QWidget {"
        "  background: #1e293b;"
        "  border: 1px solid #334155;"
        "  border-radius: 6px;"
        "}"
    )
    card.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    card.customContextMenuRequested.connect(
        lambda pos, c=client: client_context_menu(window, pos, c)
    )
    card_layout = QHBoxLayout(card)
    card_layout.setContentsMargins(10, 8, 10, 8)
    card_layout.setSpacing(10)

    icon = QLabel("🟢")
    icon.setFont(QFont("Sans", 16))
    card_layout.addWidget(icon)

    info = QVBoxLayout()
    info.setSpacing(1)

    ip = client.get("ip", "unknown")
    ip_lbl = QLabel(ip)
    ip_lbl.setFont(QFont("Sans", 11, QFont.Weight.Bold))
    ip_lbl.setStyleSheet("color: #e2e8f0; background: transparent;")
    info.addWidget(ip_lbl)

    token = client.get("token", "unknown")
    tok_lbl = QLabel(f"Token: {token}")
    tok_lbl.setFont(QFont("Monospace", 9))
    tok_lbl.setStyleSheet("color: #64748b; background: transparent;")
    tok_lbl.setToolTip(client.get("full_token", ""))
    info.addWidget(tok_lbl)

    card_layout.addLayout(info, 1)

    status_lbl = QLabel("Connected")
    status_lbl.setStyleSheet(
        "color: #22c55e; font-size: 10px; background: transparent;"
    )
    card_layout.addWidget(status_lbl)

    return card


def client_context_menu(window, pos, client) -> None:
    menu = QMenu(window)
    menu.setStyleSheet(
        "QMenu { background: #1e293b; border: 1px solid #334155; border-radius: 4px; padding: 4px; }"
        "QMenu::item { color: #cbd5e1; padding: 4px 16px; border-radius: 3px; }"
        "QMenu::item:selected { background: #334155; }"
    )

    ip = client.get("ip", "")
    full_token = client.get("full_token", "")

    copy_ip_act = menu.addAction("Copy IP")
    if copy_ip_act:
        copy_ip_act.triggered.connect(lambda: copy_to_clipboard(window, ip, "IP"))

    if full_token:
        copy_tok_act = menu.addAction("Copy Token")
        if copy_tok_act:
            copy_tok_act.triggered.connect(
                lambda: copy_to_clipboard(window, full_token, "Token")
            )

    menu.addSeparator()

    kick_act = menu.addAction("Kick")
    if kick_act:
        kick_act.triggered.connect(lambda: kick_client(window, client))

    block_act = menu.addAction("Block IP")
    if block_act:
        block_act.triggered.connect(lambda: block_client_ip(window, client))

    menu.exec(window.clients_scroll.viewport().mapToGlobal(pos))


def copy_to_clipboard(window, text: str, label: str) -> None:
    qapp = QApplication.instance()
    if qapp is None:
        return
    cb = qapp.clipboard()  # type: ignore[attr-defined]
    if cb is None:
        return
    cb.setText(text)
    window.statusBar().showMessage(f"{label} copied to clipboard", 2000)


def kick_client(window, client: dict) -> None:
    from PyQt6.QtWidgets import QMessageBox

    ip = client.get("ip", "unknown")
    client_id = client.get("id", "")
    ok = QMessageBox.question(
        window,
        "Confirm Kick",
        f'Kick client "{ip}"?',
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    if ok != QMessageBox.StandardButton.Yes:
        return
    try:
        import urllib.request as urq

        port = window.settings_panel.get_params()["port"]
        req = urq.Request(
            f"http://127.0.0.1:{port}/api/clients/{client_id}/kick",
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urq.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read())
        window.statusBar().showMessage(f"Kicked {ip}", 3000)
        refresh_clients(window)
    except Exception as e:
        QMessageBox.warning(window, "Error", f"Failed to kick client: {e}")


def block_client_ip(window, client: dict) -> None:
    from PyQt6.QtWidgets import QMessageBox

    ip = client.get("ip", "unknown")
    ok = QMessageBox.question(
        window,
        "Confirm Block",
        f'Block IP "{ip}"?\n\nThis will revoke all tokens for this IP.',
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    if ok != QMessageBox.StandardButton.Yes:
        return
    try:
        import urllib.request as urq

        port = window.settings_panel.get_params()["port"]
        payload = json.dumps({"ip": ip}).encode()
        req = urq.Request(
            f"http://127.0.0.1:{port}/api/blocked-ips",
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urq.urlopen(req, timeout=5) as resp:
            json.loads(resp.read())
        window.statusBar().showMessage(f"Blocked {ip}", 3000)
        refresh_clients(window)
    except Exception as e:
        QMessageBox.warning(window, "Error", f"Failed to block IP: {e}")


def open_client_dialog(window) -> None:
    from .._client_dialog import ClientListDialog

    dlg = ClientListDialog(
        port=window.settings_panel.get_params()["port"], parent=window
    )
    dlg.exec()
