"""Client tracking and ping check management for AnywhereInput server."""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .server_core import AnywhereInputServer

from .._constants import WS_PONG_TIMEOUT, WS_CLOSE_GOING_AWAY
from anywhereinput.logging_config import get_logger

log = get_logger(__name__)


class ClientManager:
    """Manages WebSocket client lifecycle, ping checks, and pruning."""

    def __init__(self, server: AnywhereInputServer):
        self.server = server

    async def ping_check_loop(self) -> None:
        """Periodically check all connected clients for dead connections.

        Closes WebSocket connections that haven't sent a pong within timeout.
        Runs every 15 seconds.
        """
        while True:
            await asyncio.sleep(15)
            now = time.time()
            stale_threshold = float(WS_PONG_TIMEOUT)
            async with self.server.clients_lock:
                dead = []
                for ws in list(self.server.clients):
                    if ws.closed:
                        dead.append(ws)
                        continue
                    last_pong = self.server._pong_timestamps.get(ws, 0)
                    if last_pong > 0 and (now - last_pong) > stale_threshold:
                        dead.append(ws)

                for ws in dead:
                    try:
                        await ws.close(
                            code=WS_CLOSE_GOING_AWAY, message=b"Stale connection"
                        )
                    except Exception as e:
                        log.debug("close stale client failed: %s", e)
                    self.server._client_tokens.pop(ws, None)
                    self.server._client_meta.pop(ws, None)
                    self.server._pong_timestamps.pop(ws, None)
                    self.server.clients.discard(ws)

                if dead:
                    log.info(
                        "[WS] Pruned %d stale client(s) (no pong / closed)", len(dead)
                    )

    async def prune_stale_clients(self) -> None:
        """Prune stale clients - union of conditions from HTTP and ping check.

        Conditions: closed OR no-token OR stale-pong (>60s).
        Called from both list_clients and ping_check_loop.
        """
        now = time.time()
        stale_threshold = float(WS_PONG_TIMEOUT)
        async with self.server.clients_lock:
            for ws in list(self.server.clients):
                if ws.closed:
                    self.server._client_meta.pop(ws, None)
                    self.server._pong_timestamps.pop(ws, None)
                    self.server._client_tokens.pop(ws, None)
                    self.server.clients.discard(ws)
                elif ws not in self.server._client_tokens:
                    self.server._client_meta.pop(ws, None)
                    self.server._pong_timestamps.pop(ws, None)
                    self.server._client_tokens.pop(ws, None)
                    self.server.clients.discard(ws)
                elif (now - self.server._pong_timestamps.get(ws, 0)) > stale_threshold:
                    self.server._client_meta.pop(ws, None)
                    self.server._pong_timestamps.pop(ws, None)
                    self.server._client_tokens.pop(ws, None)
                    self.server.clients.discard(ws)

    async def get_active_clients(self) -> list[dict]:
        """Return pruned list of active clients for HTTP endpoint.

        Returns:
            List of dicts with id, ip, connected.
        """
        await self.prune_stale_clients()
        client_list = []
        async with self.server.clients_lock:
            for ws in list(self.server.clients):
                meta = self.server._client_meta.get(ws, {})
                client_list.append(
                    {
                        "id": f"{ws}",
                        "ip": meta.get("ip", "unknown"),
                        "connected": True,
                    }
                )
        return client_list

    async def unregister(self, ws) -> None:
        """Immediate cleanup for WS disconnect - called from websocket_handler finally block."""
        self.server._client_tokens.pop(ws, None)
        self.server._client_meta.pop(ws, None)
        self.server._pong_timestamps.pop(ws, None)
        async with self.server.clients_lock:
            self.server.clients.discard(ws)
