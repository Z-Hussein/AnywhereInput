"""Log capture, filtering, and export."""

import re

from ._ui_helpers import escape_html

LOG_COLORS = {
    "INFO": "#58a6ff",
    "WARN": "#d29922",
    "ERROR": "#f85149",
    "CLIENT": "#3fb950",
    "TOKEN": "#bc8cff",
}


def detect_log_level(text: str) -> str:
    upper = text.upper()
    if "[ERR" in upper or "ERROR" in upper or "FAIL" in upper:
        return "ERROR"
    if "[WARN" in upper or "WARNING" in upper:
        return "WARN"
    if "CLIENT" in upper or "CONNECT" in upper:
        return "CLIENT"
    if "TOKEN" in upper or "CREATED" in upper:
        return "TOKEN"
    return "INFO"


def on_log(window, text: str) -> None:
    window._log_lines.append((text, detect_log_level(text)))
    apply_log_filters(window)

    # Detect tunnel URL first (takes priority over local URL)
    tunnel_match = re.search(
        r"https://[a-zA-Z0-9-]+\.trycloudflare\.com"
        r"|https://[a-zA-Z0-9._-]+\.(?:pinggy-free\.link|free\.pinggy\.net|free\.pinggy\.io)"
        r"|https://[a-zA-Z0-9._-]+\.zrok\.(?:io|net)",
        text,
    )
    if tunnel_match:
        url = tunnel_match.group(0)
        window._tunnel_url = url
        window.url_lbl.setText(url)
        window.copy_url_btn.setEnabled(True)
        window.status_bar.set_tunnel_connected(url)
        window._overview_tunnel_lbl.setText(url[:40] + "..." if len(url) > 40 else url)
        window._overview_tunnel_lbl.setStyleSheet(
            "color: #22c55e; background: transparent; border: none;"
        )
        if "trycloudflare" in url:
            window.activity_log.log_tunnel_connected("Cloudflare", url)
        elif "pinggy" in url:
            window.activity_log.log_tunnel_connected("Pinggy", url)
        elif "zrok" in url:
            window.activity_log.log_tunnel_connected("Zrok", url)
        else:
            window.activity_log.log_tunnel_connected("Tunnel", url)
    elif not window._tunnel_url:
        if "Local:" in text or "http://" in text.lower():
            match = re.search(r"(https?://[^\s]+)", text)
            if match:
                url = match.group(1)
                window.url_lbl.setText(url)
                window.copy_url_btn.setEnabled(True)

    # Detect tunnel failure
    if "tunnel" in text.lower() and (
        "fail" in text.lower()
        or "error" in text.lower()
        or "exited" in text.lower()
        or "offline" in text.lower()
    ):
        window.status_bar.set_tunnel_disconnected("Offline")
        window._overview_tunnel_lbl.setText("Offline")
        window._overview_tunnel_lbl.setStyleSheet(
            "color: #ef4444; background: transparent; border: none;"
        )
        window.activity_log.log_tunnel_disconnected("Tunnel")

    # Detect client events
    if "client" in text.lower() and "connect" in text.lower():
        ip_match = re.search(r"(\d+\.\d+\.\d+\.\d+)", text)
        if ip_match:
            window.activity_log.log_client_connected(ip_match.group(1))

    if "client" in text.lower() and (
        "disconnect" in text.lower() or "lost" in text.lower()
    ):
        ip_match = re.search(r"(\d+\.\d+\.\d+\.\d+)", text)
        if ip_match:
            window.activity_log.log_client_disconnected(ip_match.group(1))

    # Detect token events
    if "token" in text.lower() and "created" in text.lower():
        name_match = re.search(
            r'(?:name|token)\s*[:=]?\s*["\']?(\w+)', text, re.IGNORECASE
        )
        if name_match:
            window.activity_log.log_token_created(name_match.group(1))

    if "token" in text.lower() and (
        "revoked" in text.lower()
        or "deleted" in text.lower()
        or "removed" in text.lower()
    ):
        name_match = re.search(
            r'(?:name|token)\s*[:=]?\s*["\']?(\w+)', text, re.IGNORECASE
        )
        if name_match:
            window.activity_log.log_token_revoked(name_match.group(1))


def apply_log_filters(window) -> None:
    search = window.log_filter_input.text().lower()
    level = window.log_level_combo.currentText()

    window.log_text.clear()
    for text, detected_level in window._log_lines:
        if level != "All" and detected_level != level:
            continue
        if search and search not in text.lower():
            continue
        color = LOG_COLORS.get(detected_level, "#c9d1d9")
        prefix = detected_level.ljust(6)
        html = (
            f'<span style="color: {color}; font-weight: bold;">{prefix}</span>'
            f'  <span style="color: #c9d1d9;">{escape_html(text)}</span>'
        )
        window.log_text.append(html)

    if window.auto_scroll_cb.isChecked():
        sb = window.log_text.verticalScrollBar()
        sb.setValue(sb.maximum())


def filter_logs(window, _text=None) -> None:
    apply_log_filters(window)


def clear_logs(window) -> None:
    window.log_text.clear()
    window._log_lines = []


def export_logs(window) -> None:
    from PyQt6.QtWidgets import QFileDialog, QMessageBox

    path, _ = QFileDialog.getSaveFileName(
        window, "Export Logs", "anywhereinput_logs.txt", "Text Files (*.txt)"
    )
    if path:
        try:
            with open(path, "w") as f:
                for text, _level in window._log_lines:
                    f.write(text + "\n")
            QMessageBox.information(window, "Exported", f"Logs saved to:\n{path}")
        except Exception as e:
            QMessageBox.warning(window, "Error", f"Failed to export logs: {e}")
