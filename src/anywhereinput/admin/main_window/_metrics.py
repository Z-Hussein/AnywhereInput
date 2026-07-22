"""Dashboard, status changes, auto-refresh."""

import json
import logging
import time as _time

log = logging.getLogger("anywhereinput.admin")


def format_uptime(seconds: float) -> str:
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours}h {minutes}m"


def on_status_changed(window, status: str) -> None:
    if status == "running":
        window.status_bar.set_server_state("healthy")
        window._status_indicator.setText("Running")
        window._status_indicator.setStyleSheet(
            "color: #22c55e; background: transparent; border: none; padding: 0 4px;"
        )
        window.start_btn.setEnabled(False)
        window.stop_btn.setEnabled(True)
        window._server_start_time = _time.time()
        window.copy_url_btn.setEnabled(True)
        # Update overview tunnel card
        if hasattr(window, "_overview_tunnel_lbl") and window._tunnel_url:
            window._overview_tunnel_lbl.setText(window._tunnel_url)
    elif status == "stopped":
        window.status_bar.set_server_state("offline", message="Process exited")
        window.status_bar.set_tunnel_disconnected("Offline")
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
        window._server_start_time = None
        window._tunnel_url = None
        window.url_lbl.setText("-")
        window.copy_url_btn.setEnabled(False)
        window.uptime_lbl.setText("-")
        window.dash_clients_lbl.setText("0")
        window.dash_pending_lbl.setText("0")
        window.dash_fps_lbl.setText("-")
        window.dash_bw_lbl.setText("-")


def update_dashboard(window) -> None:
    """Fetch engine + client data and update dashboard labels."""
    if not (window._server_thread and window._server_thread.isRunning()):
        return
    try:
        import urllib.request as urq

        port = window.settings_panel.get_params()["port"]

        # Engine status
        try:
            eng_req = urq.Request(f"http://127.0.0.1:{port}/api/engine")
            with urq.urlopen(eng_req, timeout=2) as resp:
                eng = json.loads(resp.read())
            state = eng.get("state", "unknown").lower()
            msg = eng.get("message")
            window.status_bar.set_server_state(state, message=msg or "")

            # FPS: try top-level "fps" first (real-time estimate), then fall back
            fps = eng.get("fps")
            if fps is None:
                screen = eng.get("screen_engine", {})
                fps = screen.get("fps")
            window.status_bar.set_fps(fps)
            if fps is not None and fps > 0:
                window.dash_fps_lbl.setText(f"{fps} fps")
            else:
                window.dash_fps_lbl.setText("-")
        except Exception:
            window.dash_fps_lbl.setText("-")

        # Clients
        try:
            cli_req = urq.Request(f"http://127.0.0.1:{port}/api/clients")
            with urq.urlopen(cli_req, timeout=2) as resp:
                cli = json.loads(resp.read())
            clients_list = cli.get("clients", [])
            count = len(clients_list)
            window.status_bar.set_clients(count)
            window.dash_clients_lbl.setText(str(count))
        except Exception:
            window.dash_clients_lbl.setText("?")

        # Pending requests
        window.dash_pending_lbl.setText(str(window._pending_count))

        # Uptime
        if window._server_start_time:
            elapsed = _time.time() - window._server_start_time
            window.status_bar.set_uptime(elapsed)
            window.uptime_lbl.setText(format_uptime(elapsed))

        # Bandwidth
        try:
            bw_req = urq.Request(f"http://127.0.0.1:{port}/api/engine")
            with urq.urlopen(bw_req, timeout=2) as resp:
                eng = json.loads(resp.read())
            bandwidth = eng.get("bandwidth_bytes_sec")
            if bandwidth is not None:
                mb = bandwidth / (1024 * 1024)
                window.dash_bw_lbl.setText(f"{mb:.1f} MB/s")
            else:
                window.dash_bw_lbl.setText("-")
        except Exception:
            window.dash_bw_lbl.setText("-")

    except Exception:
        window.status_bar.set_server_state("error", message="Connection lost")
