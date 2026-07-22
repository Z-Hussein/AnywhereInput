"""Desktop notification with approve/decline."""

import json
import logging

from .._connection_notification import ConnectionNotificationWidget

log = logging.getLogger("anywhereinput.admin")


def show_connection_notification(window, req_item: dict) -> None:
    """Show a desktop notification with Approve/Decline buttons."""
    client_name = req_item.get("client_name", "Unknown Device")
    client_ip = req_item.get("ip", "unknown")
    req_id = req_item.get("id")

    notification = ConnectionNotificationWidget(
        client_name=client_name,
        client_ip=client_ip,
    )
    window._active_notifications.append(notification)

    def on_approve():
        approve_request_by_id(window, req_id)

    def on_decline():
        decline_request_by_id(window, req_id)

    def on_dismissed():
        if notification in window._active_notifications:
            window._active_notifications.remove(notification)

    notification.approved.connect(on_approve)
    notification.declined.connect(on_decline)
    notification.dismissed.connect(on_dismissed)


def approve_request_by_id(window, req_id: str) -> None:
    """Approve a pending connection request via API."""
    try:
        import urllib.request as urq

        port = window.settings_panel.get_params()["port"]
        payload = json.dumps({"action": "approve"}).encode()
        req = urq.Request(
            f"http://127.0.0.1:{port}/api/requests/{req_id}",
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urq.urlopen(req, timeout=5) as resp:
            json.loads(resp.read())
        window.statusBar().showMessage("Request approved", 3000)
        from ._request_management import refresh_requests

        refresh_requests(window)
    except Exception as e:
        log.error("Failed to approve request: %s", e)
        window.statusBar().showMessage(f"Approve failed: {e}", 5000)


def decline_request_by_id(window, req_id: str) -> None:
    """Decline a pending connection request via API."""
    try:
        import urllib.request as urq

        port = window.settings_panel.get_params()["port"]
        payload = json.dumps({"action": "decline"}).encode()
        req = urq.Request(
            f"http://127.0.0.1:{port}/api/requests/{req_id}",
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urq.urlopen(req, timeout=5) as resp:
            json.loads(resp.read())
        window.statusBar().showMessage("Request declined", 3000)
        from ._request_management import refresh_requests

        refresh_requests(window)
    except Exception as e:
        log.error("Failed to decline request: %s", e)
        window.statusBar().showMessage(f"Decline failed: {e}", 5000)
