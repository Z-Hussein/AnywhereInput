"""WebSocket connection handler for AnywhereInput server."""

import asyncio
import time
import uuid
from typing import TYPE_CHECKING

import aiohttp
from aiohttp import web

if TYPE_CHECKING:
    from .server_core import AnywhereInputServer

from .._connection_requests import _connection_requests
from anywhereinput.logging_config import get_audit_logger, get_logger
from anywhereinput.screen_capture import CaptureEngineState
from .._constants import (
    WS_CLOSE_NORMAL,
    WS_CLOSE_AUTH_FAILED,
)

log = get_logger(__name__)
audit = get_audit_logger()


class WebSocketHandler:
    """Handles WebSocket connections, authentication, and message dispatch."""

    def __init__(self, server: "AnywhereInputServer") -> None:
        self.server = server

    async def handle(self, request) -> web.WebSocketResponse:
        """Main WebSocket connection handler.

        Performs origin validation, token authentication, then dispatches
        input messages to MessageHandler and broadcasts screen frames.

        Args:
            request: aiohttp WebSocket request.

        Returns:
            WebSocketResponse for the established connection.
        """
        # Origin validation to prevent CSRF on WebSocket
        origin = request.headers.get("Origin", "")
        host_header = request.headers.get("Host", "")
        if origin:
            allowed = False

            if any(
                t in origin.lower() for t in ("trycloudflare.com", "pinggy", "zrok")
            ):
                allowed = True
            elif origin.startswith(
                (
                    "http://localhost",
                    "http://127.0.0.1",
                    "https://localhost",
                    "https://127.0.0.1",
                )
            ):
                allowed = True
            elif host_header:
                base_host = host_header.split(":")[0]
                origin_host = (
                    origin.split("://")[1].split(":")[0] if "://" in origin else ""
                )
                if origin_host == base_host:
                    allowed = True
            elif not request.scheme or request.scheme != "https":
                allowed = True

            if not allowed:
                return web.Response(status=403, text="Origin not allowed")  # type: ignore[return-value]

        client_ip, client_port = self.server._get_client_ip(request)
        log.info(
            "[WS] Incoming connection from %s (origin=%s, host=%s)",
            client_ip,
            origin or "none",
            host_header or "none",
        )

        ws = web.WebSocketResponse(heartbeat=30.0)
        await ws.prepare(request)
        try:
            msg = await ws.receive_json(timeout=10)
            token = msg.get("token", "")
            msg_type = msg.get("type", "")

            log.info(
                "[WS] Auth: type=%s, token_len=%d, client_ip=%s",
                msg_type,
                len(token),
                client_ip,
            )

            validated = False

            parts = token.split("://")
            if len(parts) == 2:
                req_id, client_name = parts
                if req_id in _connection_requests:
                    info = _connection_requests[req_id]
                    if (
                        info["client_name"] == client_name
                        and info["status"] == "approved"
                    ):
                        existing = self.server.token_manager.tokens.get(info["token"])
                        if existing is None:
                            saved_perms = info.get(
                                "permissions",
                                self.server.token_manager.DEFAULT_PERMISSIONS(),
                            )
                            self.server.token_manager.tokens[info["token"]] = {
                                "name": info["client_name"],
                                "created": info.get("created_at", ""),
                                "permissions": saved_perms,
                                "allowed_ips": [],
                            }
                        token = info["token"]
                        validated = True

            if not validated:
                if msg_type not in (
                    "auth",
                    "handshake",
                ) or not self.server.token_manager.validate(token, client_ip=client_ip):
                    await ws.send_json({"type": "error", "message": "Invalid token"})
                    # Audit log: token validation failed
                    audit.token_validated(
                        token, client_ip, success=False, reason="invalid_token_or_type"
                    )
                    await ws.close(code=WS_CLOSE_AUTH_FAILED, message=b"Invalid token")
                    return ws

            # Audit log: token validated successfully
            audit.token_validated(token, client_ip, success=True)

            self.server._client_tokens[ws] = token
            self.server._pong_timestamps[ws] = time.time()

            client_id = uuid.uuid4().hex[:12]
            if client_port:
                if ":" in client_ip and not client_ip.startswith("["):
                    ip_str = f"[{client_ip}]:{client_port}"
                else:
                    ip_str = f"{client_ip}:{client_port}"
            else:
                ip_str = client_ip
            self.server._client_meta[ws] = {
                "ip": ip_str,
                "token": token,
                "client_id": client_id,
            }
            # Track concurrent WS connections for this IP
            from platform import system as _platform_system

            server_os = _platform_system().lower()
            await ws.send_json({"type": "auth_ok", "server_os": server_os})
        except Exception as e:
            try:
                await ws.send_json(
                    {
                        "type": "error",
                        "message": f"Authentication failed: {e}",
                    }
                )
            except Exception as e2:
                log.debug("send_json failed during auth error: %s", e2)
            await ws.close(code=WS_CLOSE_AUTH_FAILED, message=b"Authentication failed")
            return ws

        async with self.server.clients_lock:
            old_count = len(self.server.clients)
            self.server.clients.add(ws)
            new_clients = len(self.server.clients) - old_count
        if (
            new_clients > 0
            and self.server.screen.state  # type: ignore[attr-defined]
            in (
                CaptureEngineState.DEGRADED,
                CaptureEngineState.FAILED,
                CaptureEngineState.REBUILDING,
            )
        ):
            log.info("[Server] Clients reconnected - forcing screen capture recovery")
            if self.server._event_loop is not None:
                self.server._event_loop.call_soon_threadsafe(
                    lambda: self.server.screen.force_rebuild()  # type: ignore[attr-defined]
                )

        # Audit log: client connected
        audit.client_connected(client_ip, token, client_id)

        log.info("[WS] Client connected. Total: %d", len(self.server.clients))
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = msg.json()
                    except Exception as json_err:
                        log.warning("[WS] Malformed JSON from client: %s", json_err)
                        await ws.send_json(
                            {
                                "type": "error",
                                "message": f"Invalid message format: {json_err}",
                            }
                        )
                        continue
                    self.server._pong_timestamps[ws] = time.time()
                    self.server.messages.handle(ws, data)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    log.warning("[WS] Error: %s", ws.exception())
        except asyncio.CancelledError:
            pass
        finally:
            await self._cleanup_client(ws)
        return ws

    async def _cleanup_client(self, ws) -> None:
        """Clean up client state on disconnect - called from finally block.

        Ensures consistent cleanup across all exit paths (disconnect, error, auth failure).
        """
        # Get client info before cleanup
        token = self.server._client_tokens.get(ws, "")
        meta = self.server._client_meta.get(ws, {})
        client_ip = meta.get("ip", "unknown")
        client_id = meta.get("client_id", "")

        try:
            if not ws.closed:
                close_code = ws.close_code or WS_CLOSE_NORMAL
                await ws.close(code=close_code, message=b"Server closing")
        except Exception as e:
            log.debug("close failed: %s", e)
        await self.server.clients_mgr.unregister(ws)

        # Audit log: client disconnected
        audit.client_disconnected(client_ip, token, client_id, reason=ws.exception())

        log.info(
            "[WS] Client disconnected (%s). Total: %d",
            ws.exception(),
            len(self.server.clients),
        )
