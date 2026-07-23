"""Connection request API endpoints (admin-controlled client access)."""

import secrets
import time
from datetime import datetime, timezone

from aiohttp import web

from .._connection_requests import _connection_requests
from anywhereinput.logging_config import get_audit_logger, get_logger

audit_log = get_audit_logger()
log = get_logger(__name__)


class RequestAPI:
    """Connection request endpoints - registered as aiohttp routes."""

    def __init__(self, server):
        self._srv = server

    def _require_localhost(self, request) -> bool:
        ip, _ = self._srv._get_client_ip(request)
        return str(ip) in ("127.0.0.1", "::1", "localhost")

    async def request_connect(self, request):
        """Client sends their name + optional info; server creates a pending request."""
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON"}, status=400)

        client_name = (body.get("name") or body.get("client_name") or "").strip()
        if not client_name:
            return web.json_response({"error": "Name is required"}, status=400)

        request_id = secrets.token_urlsafe(12)
        token = self._srv.token_manager.generate_token(
            name=f"auto-{request_id[:8]}", length=16
        )

        # Use server's _get_client_ip to properly handle X-Forwarded-For headers
        client_ip, client_port = self._srv._get_client_ip(request)
        ip_addr = f"{client_ip}:{client_port}" if client_port else str(client_ip)

        _connection_requests[request_id] = {
            "client_name": client_name,
            "ip": ip_addr,
            "token": token,
            "status": "pending",
            "timestamp": time.monotonic(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Audit log
        audit_log.connection_requested(client_ip, client_name, request_id)

        return web.json_response(
            {
                "request_id": request_id,
                "message": "Request sent. Waiting for admin approval...",
                "token_preview": token[:8] + "...",
            },
            status=201,
        )

    async def list_requests(self, request):
        """Return all connection requests (admin endpoint)."""
        if not self._require_localhost(request):
            return web.json_response({"error": "unauthorized"}, status=403)
        now = time.monotonic()
        results = []
        for req_id, info in list(_connection_requests.items()):
            age_sec = now - info["timestamp"]
            results.append(
                {
                    "request_id": req_id,
                    "client_name": info["client_name"],
                    "ip": info["ip"],
                    "status": info["status"],
                    "created_at": info.get("created_at", ""),
                    "age_seconds": round(age_sec, 1),
                    "token": (info["token"] if info["status"] == "approved" else None),
                    "token_preview": (
                        info["token"][:8] + "..."
                        if info.get("token") and info["status"] != "approved"
                        else None
                    ),
                }
            )
        return web.json_response({"requests": results})

    async def approve_request(self, request):
        """Approve a pending connection request."""
        if not self._require_localhost(request):
            return web.json_response({"error": "unauthorized"}, status=403)
        req_id = request.match_info.get("request_id", "")
        if req_id not in _connection_requests:
            return web.json_response({"error": "Request not found"}, status=404)

        info = _connection_requests[req_id]
        if info["status"] != "pending":
            return web.json_response(
                {"error": f"Request already {info['status']}d"}, status=400
            )

        info["status"] = "approved"

        body = {}
        try:
            body = await request.json()
        except Exception as e:
            log.debug("approve_request JSON parse failed: %s", e)

        custom_token = (body or {}).get("token", "").strip()
        admin_permissions = (body or {}).get("permissions", None)
        if custom_token:
            if len(custom_token) < 8:
                custom_token = self._srv.token_manager.generate_token(
                    name=f"custom-{req_id[:8]}", length=32
                )
                self._srv.token_manager.tokens[custom_token]["permissions"] = (
                    admin_permissions
                    if admin_permissions is not None
                    else (body or {}).get(
                        "permissions",
                        self._srv.token_manager.DEFAULT_PERMISSIONS(),
                    )
                )
                self._srv.token_manager._save_tokens()
            else:
                token_info = {
                    "name": f"manual-{info['client_name']}",
                    "created": datetime.now(timezone.utc).isoformat(),
                    "permissions": (
                        admin_permissions
                        if admin_permissions is not None
                        else (body or {}).get(
                            "permissions",
                            self._srv.token_manager.DEFAULT_PERMISSIONS(),
                        )
                    ),
                    "allowed_ips": [],
                }
                self._srv.token_manager.tokens[custom_token] = token_info
                self._srv.token_manager._save_tokens()
            info["permissions"] = (
                admin_permissions
                if admin_permissions is not None
                else (body or {}).get(
                    "permissions", self._srv.token_manager.DEFAULT_PERMISSIONS()
                )
            )
            token = custom_token
        else:
            token = info["token"]
            info["permissions"] = (
                admin_permissions
                if admin_permissions is not None
                else self._srv.token_manager.DEFAULT_PERMISSIONS()
            )
            if token not in self._srv.token_manager.tokens:
                self._srv.token_manager.tokens[token] = {
                    "name": f"auto-{info['client_name']}",
                    "created": datetime.now(timezone.utc).isoformat(),
                    "permissions": (
                        admin_permissions
                        if admin_permissions is not None
                        else self._srv.token_manager.DEFAULT_PERMISSIONS()
                    ),
                    "allowed_ips": [],
                }
            else:
                self._srv.token_manager.tokens[token]["permissions"] = (
                    admin_permissions
                    if admin_permissions is not None
                    else self._srv.token_manager.DEFAULT_PERMISSIONS()
                )
            self._srv.token_manager._save_tokens()

        # Audit log
        approver_ip, _ = self._srv._get_client_ip(request)
        perms = info.get("permissions", self._srv.token_manager.DEFAULT_PERMISSIONS())
        audit_log.connection_approved(req_id, approver_ip, token, perms)

        return web.json_response(
            {
                "ok": True,
                "client_name": info["client_name"],
                "token": token,
                "message": f"Connection approved for {info['client_name']}",
            }
        )

    async def decline_request(self, request):
        """Decline a pending connection request."""
        if not self._require_localhost(request):
            return web.json_response({"error": "unauthorized"}, status=403)
        req_id = request.match_info.get("request_id", "")
        if req_id not in _connection_requests:
            return web.json_response({"error": "Request not found"}, status=404)

        info = _connection_requests[req_id]
        if info["status"] != "pending":
            return web.json_response(
                {"error": f"Request already {info['status']}d"}, status=400
            )

        info["status"] = "declined"

        # Audit log
        decliner_ip, _ = self._srv._get_client_ip(request)
        audit_log.connection_declined(req_id, decliner_ip)

        return web.json_response(
            {
                "ok": True,
                "message": f"Connection declined for {info['client_name']}",
            }
        )

    async def check_request_status(self, request):
        """Client polls to check if their request was approved/declined."""
        req_id = request.query.get("request_id", "")
        if not req_id or req_id not in _connection_requests:
            return web.json_response({"error": "Invalid request ID"}, status=404)

        info = _connection_requests[req_id]
        resp = {"status": info["status"], "request_id": req_id}
        if info["status"] == "approved":
            resp["token"] = info["token"]
        elif info["status"] == "declined":
            resp["message"] = "Your connection request was declined."
        return web.json_response(resp)

    def register_routes(self, router):
        """Register connection request routes on the aiohttp router."""
        router.add_post("/api/request-connect", self.request_connect)
        router.add_get("/api/requests", self.list_requests)
        router.add_patch("/api/requests/{request_id}/approve", self.approve_request)
        router.add_patch("/api/requests/{request_id}/decline", self.decline_request)
        router.add_get("/api/requests/status", self.check_request_status)
