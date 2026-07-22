"""Server start/stop, reconnect, URL copy, browser open."""

import logging

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QTimer

log = logging.getLogger("anywhereinput.admin")


def start_server(window) -> None:
    from .._server_worker import ServerProcessWorker

    params = window.settings_panel.get_params()

    if window._server_thread and window._server_thread.isRunning():
        if window._last_params and window._last_params != params:
            reply = QMessageBox.question(
                window,
                "Restart Server?",
                "Settings have changed. Restart server with new settings?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                stop_server(window)
            else:
                return
        else:
            QMessageBox.warning(window, "Warning", "Server is already running!")
            return

    window._last_params = params.copy()
    window.start_btn.setEnabled(False)
    window.stop_btn.setEnabled(True)
    tunnel = params["tunnel"]
    window.status_bar.set_server_state(
        "recovering",
        message=f"Starting on port {params['port']}",
    )

    if tunnel != "local":
        window.status_bar.set_tunnel_provider(tunnel)
        window.status_bar.set_tunnel_connecting()
    else:
        window.status_bar.set_tunnel_hidden()

    window._server_thread = ServerProcessWorker(
        port=params["port"],
        tunnel=params["tunnel"],
        fps=params["fps"],
        quality=params["quality"],
        scale=params["scale"],
    )
    window._server_thread.log_signal.connect(window._on_log)
    window._server_thread.status_signal.connect(window._on_status_changed)
    window._server_thread.start()
    start_auto_refresh(window)
    window.activity_log.log_server_start(params["port"], tunnel)


def stop_server(window) -> None:
    if window._server_thread and window._server_thread.isRunning():
        window._server_thread.stop()
        window._server_thread.quit()
        window._server_thread.wait(5000)
        window._server_thread = None

    stop_auto_refresh(window)
    window.status_bar.set_server_state("offline", message="Stopped")
    window.status_bar.set_tunnel_hidden()
    window.status_bar.clear_metrics()
    window._status_indicator.setText("Offline")
    window._status_indicator.setStyleSheet(
        "color: #ef4444; background: transparent; border: none; padding: 0 4px;"
    )
    window._overview_tunnel_lbl.setText("-")
    window._overview_tunnel_lbl.setStyleSheet(
        "color: #64748b; background: transparent; border: none;"
    )
    window.start_btn.setEnabled(True)
    window.stop_btn.setEnabled(False)
    window.url_lbl.setText("-")
    window.copy_url_btn.setEnabled(False)
    window._server_start_time = None
    window._tunnel_url = None
    window.uptime_lbl.setText("-")
    window.dash_clients_lbl.setText("0")
    window.dash_pending_lbl.setText("0")
    window.dash_fps_lbl.setText("-")
    window.dash_bw_lbl.setText("-")
    window.log_text.append("[INFO] Server stopped manually.")
    window.activity_log.log_server_stop()
    window._last_params = None


def reconnect_tunnel(window) -> None:
    """Restart the server to reconnect the tunnel."""
    if window._server_thread and window._server_thread.isRunning():
        stop_server(window)
    start_server(window)


def copy_server_url(window) -> None:
    url = window.url_lbl.text()
    if url and url != "-":
        qapp = QApplication.instance()
        if qapp is None:
            return
        cb = qapp.clipboard()  # type: ignore[attr-defined]
        if cb is None:
            return
        cb.setText(url)
        window.copy_url_btn.setText("Copied!")
        window.statusBar().showMessage("URL copied to clipboard", 2000)
        QTimer.singleShot(2000, lambda: reset_copy_button(window))


def reset_copy_button(window) -> None:
    window.copy_url_btn.setText("Copy")
    if window._server_thread and window._server_thread.isRunning():
        window.copy_url_btn.setEnabled(True)


def open_in_browser(window) -> None:
    url = window.url_lbl.text()
    if url and url != "-":
        import webbrowser

        webbrowser.open(url)
    else:
        QMessageBox.information(
            window, "No URL", "Server is not running. Start the server first."
        )


def start_auto_refresh(window) -> None:
    """Start periodic auto-refresh of tabs."""
    if window._auto_refresh_timer is None:
        from PyQt6.QtCore import QTimer

        window._auto_refresh_timer = QTimer(window)
        window._auto_refresh_timer.timeout.connect(lambda: auto_refresh_tick(window))
    window._auto_refresh_timer.start(4000)


def stop_auto_refresh(window) -> None:
    """Stop periodic auto-refresh."""
    if window._auto_refresh_timer:
        window._auto_refresh_timer.stop()


def auto_refresh_tick(window) -> None:
    """Refresh all data tabs and dashboard periodically."""
    from ._token_management import refresh_tokens
    from ._request_management import refresh_requests
    from ._client_management import refresh_clients
    from ._metrics import update_dashboard

    refresh_tokens(window)
    refresh_requests(window)
    refresh_clients(window)
    update_dashboard(window)
