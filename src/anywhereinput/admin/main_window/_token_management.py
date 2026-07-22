"""Token CRUD, table, filtering, context menu."""

import json
import logging

from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QTableWidgetItem,
    QWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from anywhereinput._constants import DEFAULT_PORT
from .._token_dialog import TokenManagerDialog

log = logging.getLogger("anywhereinput.admin")


def refresh_tokens(window) -> None:
    try:
        import urllib.request as urq

        req = urq.Request(
            f"http://127.0.0.1:{window.settings_panel.get_params()['port']}/api/tokens"
        )
        with urq.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read())
        tokens = data.get("tokens", [])
    except Exception as e:
        log.debug("Token list fetch failed, using local store: %s", e)
        tokens = window._store.list_all()
    window._current_tokens = tokens
    populate_token_table(window, tokens)


def populate_token_table(window, tokens) -> None:
    window.token_table.setRowCount(len(tokens))
    has_tokens = len(tokens) > 0
    window.token_table.setVisible(has_tokens)
    window.token_empty_state.setVisible(not has_tokens)
    for i, t in enumerate(tokens):
        cb = window.token_table.item(i, 0)
        if cb is None:
            cb = QTableWidgetItem()
            window.token_table.setItem(i, 0, cb)
        cb.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
        cb.setCheckState(Qt.CheckState.Unchecked)

        window.token_table.setItem(i, 1, QTableWidgetItem(t["name"]))

        token_item = QTableWidgetItem(t.get("token", "?"))
        token_item.setToolTip(t.get("full_token", "N/A"))
        window.token_table.setItem(i, 2, token_item)

        window.token_table.setCellWidget(
            i, 3, make_permission_badges(t.get("permissions", []))
        )

        ips = t.get("allowed_ips", [])
        ip_text = "Allow All" if not ips else "\n".join(ips)
        ip_item = QTableWidgetItem(ip_text)
        if not ips:
            ip_item.setForeground(QColor("#64748b"))
        window.token_table.setItem(i, 4, ip_item)
        window.token_table.setCellWidget(
            i, 5, make_action_widget(window, i, t.get("full_token", ""))
        )


def filter_token_table(window, text: str) -> None:
    text = text.lower()
    if not text:
        populate_token_table(window, window._current_tokens)
        return
    filtered = [
        t
        for t in window._current_tokens
        if text in t.get("name", "").lower()
        or text in t.get("token", "").lower()
        or text in " ".join(t.get("permissions", [])).lower()
        or text in " ".join(t.get("allowed_ips", [])).lower()
    ]
    populate_token_table(window, filtered)


def make_permission_badges(perms: list) -> QWidget:
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(4, 2, 4, 2)
    layout.setSpacing(3)
    layout.addStretch()

    badge_colors = {
        "move": ("#1e3a5f", "#93c5fd"),
        "click": ("#1e3a5f", "#93c5fd"),
        "scroll": ("#1e3a5f", "#93c5fd"),
        "keyboard": ("#3b1f4e", "#c084fc"),
        "screen_toggle": ("#1a3a2a", "#6ee7b7"),
        "ping": ("#3b3b1a", "#fde68a"),
    }

    for perm in perms:
        bg, fg = badge_colors.get(perm, ("#334155", "#cbd5e1"))
        label = QLabel(perm.replace("_", " "))
        label.setStyleSheet(
            f"background: {bg}; color: {fg}; border-radius: 3px;"
            f"padding: 1px 6px; font-size: 10px;"
        )
        layout.addWidget(label)

    return widget


def make_action_widget(window, row, full_token) -> QWidget:
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(2)

    btn_style = (
        "QPushButton {"
        "  background: #1e293b;"
        "  border: 1px solid #334155;"
        "  border-radius: 3px;"
        "  color: #94a3b8;"
        "  font-size: 10px;"
        "  font-weight: bold;"
        "}"
        "QPushButton:hover { background: #334155; border-color: #475569; }"
    )

    edit_btn = QPushButton("Edit")
    edit_btn.setFixedSize(36, 22)
    edit_btn.setStyleSheet(btn_style)
    edit_btn.setToolTip("Edit token")

    revoke_btn = QPushButton("Del")
    revoke_btn.setFixedSize(30, 22)
    revoke_btn.setStyleSheet(btn_style.replace("color: #94a3b8;", "color: #f87171;"))
    revoke_btn.setToolTip("Revoke this token")

    copy_btn = QPushButton("Copy")
    copy_btn.setFixedSize(38, 22)
    copy_btn.setStyleSheet(btn_style)
    copy_btn.setToolTip("Copy token to clipboard")

    edit_btn.clicked.connect(lambda _, r=row: edit_token_by_row(window, r))
    revoke_btn.clicked.connect(lambda _, t=full_token: revoke_token(window, t))
    copy_btn.clicked.connect(lambda _, t=full_token: copy_token(window, t))

    layout.addWidget(edit_btn)
    layout.addWidget(revoke_btn)
    layout.addWidget(copy_btn)
    return widget


def new_token(window) -> None:
    port = window.settings_panel.get_params()["port"]
    dlg = TokenManagerDialog(window._store, port=port)
    if dlg.exec() == 1:
        refresh_tokens(window)
        name = dlg.name_input.text().strip() if dlg.name_input.text() else "unnamed"
        window.activity_log.log_token_created(name)


def edit_token_by_row(window, row: int, port: int = DEFAULT_PORT) -> None:
    from PyQt6.QtWidgets import QMessageBox

    full_tok = (
        window.token_table.item(row, 2).toolTip()
        if window.token_table.item(row, 2)
        else None
    )
    if not full_tok or full_tok.endswith("..."):
        QMessageBox.information(
            window,
            "Info",
            "Cannot edit from masked display. Delete and create a new token.",
        )
        return
    name = (
        window.token_table.item(row, 1).text()
        if window.token_table.item(row, 1)
        else ""
    )
    dlg = TokenManagerDialog(window._store, port=port, existing_token=full_tok)
    dlg.name_input.setText(name)
    if dlg.exec() == 1:
        refresh_tokens(window)


def revoke_token(window, full_token: str) -> None:
    from PyQt6.QtWidgets import QMessageBox

    name = None
    for row in range(window.token_table.rowCount()):
        item = window.token_table.item(row, 2)
        if item and item.toolTip() == full_token:
            name = window.token_table.item(row, 1).text()
            break
    ok = QMessageBox.question(
        window,
        "Confirm Revoke",
        f'Remove token "{name}"?',
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    if ok == QMessageBox.StandardButton.Yes:
        try:
            import urllib.request as urq

            port = window.settings_panel.get_params()["port"]
            req = urq.Request(
                f"http://127.0.0.1:{port}/api/tokens/{full_token}",
                method="DELETE",
            )
            with urq.urlopen(req, timeout=5) as resp:
                json.loads(resp.read())
            refresh_tokens(window)
            window.activity_log.log_token_revoked(name or "unknown")
        except Exception as e:
            QMessageBox.warning(window, "Error", f"Failed to revoke token: {e}")


def copy_token(window, full_token: str) -> None:
    qapp = QApplication.instance()
    if qapp is None:
        return
    cb = qapp.clipboard()  # type: ignore[attr-defined]
    if cb is None:
        return
    cb.setText(full_token)
    window.statusBar().showMessage("Token copied to clipboard", 2000)


def token_context_menu(window, pos) -> None:
    row = window.token_table.rowAt(pos.y())
    if row < 0:
        return
    token_item = window.token_table.item(row, 2)
    full_token = token_item.toolTip() if token_item else ""

    menu = QMenu(window)
    menu.setStyleSheet(
        "QMenu { background: #1e293b; border: 1px solid #334155; border-radius: 4px; padding: 4px; }"
        "QMenu::item { color: #cbd5e1; padding: 4px 16px; border-radius: 3px; }"
        "QMenu::item:selected { background: #334155; }"
    )

    copy_act = menu.addAction("Copy Token")
    if copy_act:
        copy_act.triggered.connect(lambda: copy_token(window, full_token))

    edit_act = menu.addAction("Edit")
    if edit_act:
        edit_act.triggered.connect(lambda: edit_token_by_row(window, row))

    dup_act = menu.addAction("Duplicate")
    if dup_act:
        dup_act.triggered.connect(lambda: duplicate_token(window, row))

    menu.addSeparator()

    revoke_act = menu.addAction("Revoke")
    if revoke_act:
        revoke_act.triggered.connect(lambda: revoke_token(window, full_token))

    menu.exec(window.token_table.viewport().mapToGlobal(pos))


def duplicate_token(window, row: int) -> None:
    from PyQt6.QtWidgets import QMessageBox

    full_tok = (
        window.token_table.item(row, 2).toolTip()
        if window.token_table.item(row, 2)
        else None
    )
    if not full_tok or full_tok.endswith("..."):
        QMessageBox.information(window, "Info", "Cannot duplicate from masked display.")
        return
    name = (
        window.token_table.item(row, 1).text()
        if window.token_table.item(row, 1)
        else ""
    )
    port = window.settings_panel.get_params()["port"]
    dlg = TokenManagerDialog(window._store, port=port)
    dlg.name_input.setText(f"{name} (copy)")
    if dlg.exec() == 1:
        refresh_tokens(window)


def select_all_tokens(window) -> None:
    from PyQt6.QtCore import Qt

    for row in range(window.token_table.rowCount()):
        item = window.token_table.item(row, 0)
        if item:
            item.setCheckState(Qt.CheckState.Checked)


def clear_selection(window) -> None:
    from PyQt6.QtCore import Qt

    for row in range(window.token_table.rowCount()):
        item = window.token_table.item(row, 0)
        if item:
            item.setCheckState(Qt.CheckState.Unchecked)


def remove_selected_multi(window) -> None:
    from PyQt6.QtWidgets import QMessageBox

    checked_rows = []
    for row in range(window.token_table.rowCount()):
        item = window.token_table.item(row, 0)
        if item and item.checkState() == Qt.CheckState.Checked:
            token_item = window.token_table.item(row, 2)
            full_tok = token_item.toolTip() if token_item else None
            name = (
                window.token_table.item(row, 1).text()
                if window.token_table.item(row, 1)
                else "?"
            )
            if full_tok and not full_tok.endswith("..."):
                checked_rows.append((row, full_tok, name))

    if not checked_rows:
        QMessageBox.warning(window, "Warning", "No tokens selected.")
        return

    count = len(checked_rows)
    plural = "s" if count > 1 else ""
    token_list = "\n".join(f"  - {name}" for _, _, name in checked_rows)
    ok = QMessageBox.question(
        window,
        "Confirm Remove",
        f"Remove {count} token{plural}?\n\n{token_list}",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    if ok != QMessageBox.StandardButton.Yes:
        return

    port = window.settings_panel.get_params()["port"]
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
        item = window.token_table.item(row, 0)
        if item:
            item.setCheckState(Qt.CheckState.Unchecked)

    refresh_tokens(window)

    if success_count > 0:
        plural = "s" if success_count > 1 else ""
        msg = f"Removed {success_count} token{plural}."
        if errors:
            msg += f"\n\nFailed:\n{chr(10).join(errors)}"
        QMessageBox.information(window, "Done", msg)
    elif errors:
        QMessageBox.warning(
            window, "Error", "All removals failed:\n" + "\n".join(errors)
        )
