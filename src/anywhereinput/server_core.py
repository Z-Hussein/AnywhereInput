"""AnywhereInputServer - HTTP/WebSocket server core."""

import asyncio
import base64
import json
import logging
import os
import queue
import sys
import threading
import time
from platform import system as _platform_system
from typing import Optional, Set

import aiohttp
from aiohttp import web

from anywhereinput import safe_print

from .auth import TokenManager
from .screen_capture import ScreenCapture, CaptureEngineState
from .tunnel_manager import TunnelManager
from .qr_display import display_qr
from .client import ClientHandler
from .mouse_worker import MouseWorker, _pyautogui_lock
from ._connection_requests import _connection_requests
from .server_api import TokenAPI, RequestAPI

logger = logging.getLogger(__name__)


class AnywhereInputServer:
    def __init__(
        self,
        host="127.0.0.1",
        port=8008,
        fps=120,
        quality=40,
        scale=0.7,
        no_capture=False,
        monitor=0,
    ):
        self.host = host
        self.port = port
        self.token_manager = TokenManager()
        self.tunnel_manager = TunnelManager()
        self.client_handler = ClientHandler()
        self.clients: Set[web.WebSocketResponse] = set()
        self.clients_lock = asyncio.Lock()
        self._client_tokens: dict = {}
        self._client_meta: dict = {}
        self._pong_timestamps: dict[web.WebSocketResponse, float] = (
            {}
        )  # track last pong per WS
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._ping_check_task: Optional[asyncio.Task] = None

        self.screen = ScreenCapture(
            fps=fps,
            quality=quality,
            scale=scale,
            monitor_index=monitor if monitor > 0 else None,
            on_state_change=self._on_screen_state_change,
        )
        self.screen._pyautogui_lock = _pyautogui_lock
        self.screen.enabled = not no_capture

        # Verify screen capture is actually functional after init
        if not no_capture:
            valid_frames = 0
            for _i in range(3):
                test_frame = self.screen.capture()
                if test_frame is not None and len(test_frame) > 100:
                    valid_frames += 1
                else:
                    logger.debug(
                        "Screen capture init attempt %d returned invalid frame",
                        _i + 1,
                    )
                time.sleep(0.5)

            if valid_frames == 0:
                logger.error(
                    "Screen capture initialization FAILED - "
                    "no valid frames after 3 attempts. Screen will be disabled."
                )
                self.screen.enabled = False
                self.screen.state = CaptureEngineState.FAILED
            else:
                logger.info("Screen capture init OK (%d/3 valid frames)", valid_frames)

        self.app = web.Application()
        self.runner: Optional[web.AppRunner] = None
        self._running = False
        self._capture_task: Optional[asyncio.Task] = None
        self.mouse_worker = MouseWorker()

        # Composition: API handler objects
        self._token_api = TokenAPI(self)
        self._request_api = RequestAPI(self)

        self._setup_routes()

    def _get_client_ip(self, request):
        """Extract real client IP and port from a request."""
        xff = request.headers.get("X-Forwarded-For")
        if xff:
            first_ip = xff.split(",")[0].strip()
            if first_ip and first_ip != "unknown":
                return self._parse_ip_str(first_ip)
        peer = request.remote
        if isinstance(peer, str):
            return self._parse_ip_str(peer)
        return (getattr(peer, "host", "unknown") or "unknown"), getattr(
            peer, "port", 0
        ) or 0

    @staticmethod
    def _parse_ip_str(addr):
        """Parse 'host:port' or bare host from aiohttp request.remote."""
        addr = addr.strip()
        if not addr or addr == "unknown":
            return ("unknown", 0)
        if addr.startswith("["):
            bracket_end = addr.rfind("]")
            if (
                bracket_end != -1
                and bracket_end + 1 < len(addr)
                and addr[bracket_end + 1] == ":"
            ):
                host = addr[1:bracket_end]
                port_str = addr[bracket_end + 2 :]  # noqa: E203
                port = int(port_str) if port_str.isdigit() else 0
                return (host, port)
            return (addr[1:-1] if addr.endswith("]") else addr, 0)
        last_colon = addr.rfind(":")
        if last_colon > 0:
            potential_port = addr[last_colon + 1 :]  # noqa: E203
            if potential_port.isdigit():
                return (addr[:last_colon], int(potential_port))
        return (addr, 0)

    def _setup_routes(self):
        self.app.router.add_get("/", self.client_handler.index)
        self.app.router.add_get("/favicon.ico", self.client_handler.favicon_handler)
        self.app.router.add_static(
            "/static/", path=str(self.client_handler.static_dir), name="static"
        )
        self.app.router.add_get("/ws", self.websocket_handler)
        # Non-API routes
        self.app.router.add_get("/api/screen", self.screen_info)
        self.app.router.add_get("/api/engine", self.engine_info)
        self.app.router.add_get("/api/monitors", self.monitors_info)
        self.app.router.add_post("/api/monitor/{index}", self.set_monitor)
        # Delegate API routes to handler objects
        self._token_api.register_routes(self.app.router)
        self._request_api.register_routes(self.app.router)

    async def screen_info(self, request):
        w, h = self.screen.dimensions
        return web.json_response({"width": w, "height": h})

    async def engine_info(self, request):
        status = self.mouse_worker.get_engine_status()
        screen_state = getattr(
            getattr(self.screen, "state", None), "name", "HEALTHY"
        ).lower()
        status["screen_engine"] = {
            "state": screen_state,
            "enabled": self.screen.enabled,
        }
        return web.json_response(status)

    def _screen_status_message(self) -> str:
        state_name = getattr(getattr(self.screen, "state", None), "name", "HEALTHY")
        if state_name == "REBUILDING":
            return "Reconnecting to display..."
        if state_name == "DEGRADED":
            return "Screen stream reduced quality"
        if state_name == "FAILED":
            return "Screen capture failed - retrying"
        if state_name == "OFFLINE":
            return "Screen capture unavailable"
        return ""

    async def _broadcast_to_all(self, msg: str):
        """Send a JSON message to all connected WebSocket clients."""
        dead = set()
        async with self.clients_lock:
            client_list = list(self.clients)
        for ws in client_list:
            try:
                await ws.send_str(msg)
            except Exception:
                dead.add(ws)
        if dead:
            async with self.clients_lock:
                for ws in dead:
                    try:
                        await ws.close()
                    except Exception:
                        pass
                for ws in dead:
                    self._client_tokens.pop(ws, None)
                    self._client_meta.pop(ws, None)
                self.clients -= dead

    async def _broadcast_to_all_bytes(self, msg: bytes):
        """Send binary message to all connected WebSocket clients for optimal performance."""
        dead = set()
        async with self.clients_lock:
            client_list = list(self.clients)
        for ws in client_list:
            try:
                await ws.send_bytes(msg)
            except Exception:
                dead.add(ws)
        if dead:
            async with self.clients_lock:
                for ws in dead:
                    try:
                        await ws.close()
                    except Exception:
                        pass
                for ws in dead:
                    self._client_tokens.pop(ws, None)
                    self._client_meta.pop(ws, None)
                self.clients -= dead

    def _on_screen_state_change(self, state):
        if not self.clients:
            return
        if not self._event_loop or self._event_loop.is_closed():
            return

        message = self._screen_status_message()
        msg = json.dumps(
            {
                "type": "screen_status",
                "status": state.name.lower(),
                "message": message,
            }
        )

        def _schedule_broadcast():
            asyncio.create_task(self._broadcast_to_all(msg))

        self._event_loop.call_soon_threadsafe(_schedule_broadcast)

    async def monitors_info(self, request):
        return web.json_response(
            {
                "monitors": self.screen.get_monitor_info(),
                "current": self.screen.current_monitor_index,
                "auto_track": self.screen._monitor_index is None,
            }
        )

    async def set_monitor(self, request):
        try:
            idx = int(request.match_info["index"])
            ok = self.screen.set_monitor(idx)
            return web.json_response(
                {
                    "success": ok,
                    "monitor": self.screen.current_monitor_index,
                    "auto_track": self.screen._monitor_index is None,
                }
            )
        except ValueError:
            return web.json_response(
                {"success": False, "error": "Invalid monitor index"}, status=400
            )

    # ── Client monitoring endpoint ────────────────────────────────────────

    async def list_clients(self, request):
        """Return currently connected WebSocket clients.

        Filters out stale entries by cross-referencing _client_tokens and checking
        ws.closed state. Also prunes any pong-timestamp-stale entries (>60s).
        """
        now = time.time()
        client_list = []
        async with self.clients_lock:
            # Prune stale dead/abandoned entries first
            for ws in list(self.clients):
                if ws.closed:
                    self._client_meta.pop(ws, None)
                    self._pong_timestamps.pop(ws, None)
                    self._client_tokens.pop(ws, None)
                    self.clients.discard(ws)
                elif ws not in self._client_tokens:
                    # ws in clients but has no token mapping - aborted connection
                    self._client_meta.pop(ws, None)
                    self._pong_timestamps.pop(ws, None)
                    self._client_tokens.pop(ws, None)
                    self.clients.discard(ws)
                elif (now - self._pong_timestamps.get(ws, 0)) > 60:
                    # No keepalive within timeout - likely zombie
                    self._client_meta.pop(ws, None)
                    self._pong_timestamps.pop(ws, None)
                    self._client_tokens.pop(ws, None)
                    self.clients.discard(ws)
                else:
                    meta = self._client_meta.get(ws, {})
                    client_list.append(
                        {
                            "id": f"{ws}",
                            "ip": meta.get("ip", "unknown"),
                            "connected": True,
                        }
                    )
        return web.json_response({"count": len(client_list), "clients": client_list})

    async def _ping_check_loop(self):
        """Periodically check all connected clients for dead connections.

        If a client hasn't sent a pong within the timeout, close it.
        """
        while True:
            await asyncio.sleep(15)
            now = time.time()
            stale_threshold = 60.0  # seconds before considering a client dead
            async with self.clients_lock:
                dead = []
                for ws in list(self.clients):
                    # If ws is already closed, prune it
                    if ws.closed:
                        dead.append(ws)
                        continue
                    # Check pong timestamp
                    last_pong = self._pong_timestamps.get(ws, 0)
                    if last_pong > 0 and (now - last_pong) > stale_threshold:
                        # No pong received - client is likely dead
                        dead.append(ws)

                for ws in dead:
                    try:
                        await ws.close()
                    except Exception:
                        pass
                    self._client_tokens.pop(ws, None)
                    self._client_meta.pop(ws, None)
                    self._pong_timestamps.pop(ws, None)
                    self.clients.discard(ws)

                if dead:
                    safe_print(
                        f"[WS] Pruned {len(dead)} stale client(s) (no pong / closed)"
                    )

    async def websocket_handler(self, request):
        # Origin validation to prevent CSRF on WebSocket
        origin = request.headers.get("Origin", "")
        if origin:
            allowed = False
            host_header = request.headers.get("Host", "")

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
                return web.Response(status=403, text="Origin not allowed")

        client_ip, client_port = self._get_client_ip(request)

        ws = web.WebSocketResponse(heartbeat=30.0)  # aiohttp ping/pong every 30s
        await ws.prepare(request)
        try:
            msg = await ws.receive_json(timeout=10)
            token = msg.get("token", "")
            msg_type = msg.get("type", "")

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
                        existing = self.token_manager.tokens.get(info["token"])
                        if existing is None:
                            saved_perms = info.get(
                                "permissions",
                                self.token_manager.DEFAULT_PERMISSIONS(),
                            )
                            self.token_manager.tokens[info["token"]] = {
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
                ) or not self.token_manager.validate(token, client_ip=client_ip):
                    await ws.send_json({"type": "error", "message": "Invalid token"})
                    await ws.close()
                    return ws
            self._client_tokens[ws] = token
            self._pong_timestamps[ws] = time.time()  # initial pong timestamp on connect
            import uuid

            client_id = uuid.uuid4().hex[:12]
            # Store IP in standard format: [::1]:port for IPv6, IP:port for IPv4
            if client_port:
                if ":" in client_ip and not client_ip.startswith("["):
                    # IPv6 address - wrap in brackets
                    ip_str = f"[{client_ip}]:{client_port}"
                else:
                    # IPv4 address
                    ip_str = f"{client_ip}:{client_port}"
            else:
                ip_str = client_ip
            self._client_meta[ws] = {
                "ip": ip_str,
                "token": token,
                "client_id": client_id,
            }
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
            except Exception:
                pass
            await ws.close()
            return ws

        async with self.clients_lock:
            old_count = len(self.clients)
            self.clients.add(ws)
            new_clients = len(self.clients) - old_count
        if new_clients > 0 and self.screen.state in (
            CaptureEngineState.DEGRADED,
            CaptureEngineState.FAILED,
            CaptureEngineState.REBUILDING,
        ):
            safe_print(
                "[Server] Clients reconnected - forcing screen capture" " recovery"
            )
            self._event_loop.call_soon_threadsafe(lambda: self.screen.force_rebuild())
        safe_print(f"[WS] Client connected. Total: {len(self.clients)}")
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = msg.json()
                    except Exception as json_err:
                        logger.warning(f"[WS] Malformed JSON from client: {json_err}")
                        await ws.send_json(
                            {
                                "type": "error",
                                "message": f"Invalid message format: {json_err}",
                            }
                        )
                        continue
                    # Update pong timestamp on any received message (counts as keepalive)
                    self._pong_timestamps[ws] = time.time()
                    self._handle_message_sync(ws, data)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    safe_print(f"[WS] Error: {ws.exception()}")
        except asyncio.CancelledError:
            pass
        finally:
            try:
                await ws.close()
            except Exception:
                pass
            self._client_tokens.pop(ws, None)
            self._client_meta.pop(ws, None)
            self._pong_timestamps.pop(ws, None)
            async with self.clients_lock:
                self.clients.discard(ws)
            safe_print(
                f"[WS] Client disconnected ({ws.exception()})."
                f" Total: {len(self.clients)}"
            )
        return ws

    def _handle_message_sync(self, ws, data):
        """Non-blocking handler for client input messages."""
        t = data.get("type")

        guarded_input_types = {
            "move",
            "click",
            "double_click",
            "mouse_down",
            "mouse_up",
            "scroll",
            "key",
            "type",
            "hotkey",
        }
        guarded_special_types = {"screen_toggle", "screen_restart"}

        allowed_perms = self.token_manager.DEFAULT_PERMISSIONS()
        if ws in self._client_tokens:
            token_val = self._client_tokens[ws]
            if token_val in self.token_manager.tokens:
                allowed_perms = self.token_manager.tokens[token_val].get(
                    "permissions", self.token_manager.DEFAULT_PERMISSIONS()
                )

        perm_map = {
            "move": "move",
            "click": "click",
            "double_click": "click",
            "mouse_down": "click",
            "mouse_up": "click",
            "scroll": "scroll",
            "key": "keyboard",
            "type": "keyboard",
            "hotkey": "keyboard",
            "screen_restart": "screen_toggle",
            "ping": None,  # ping bypasses permission checks
        }

        if t in guarded_input_types:
            required_perm = perm_map.get(t, t)
            if required_perm not in allowed_perms:
                asyncio.create_task(
                    ws.send_json(
                        {
                            "error": "permission_denied",
                            "message": f"Token lacks '{required_perm}' permission.",
                        }
                    )
                )
                return

            engine_state = self.mouse_worker.get_engine_state()
            if engine_state == "offline":
                asyncio.create_task(
                    ws.send_json(
                        {
                            "error": "capture_engine_offline",
                            "message": "Input engine is offline. Retry shortly.",
                        }
                    )
                )
                return
            if engine_state in {"recovering", "degraded"}:
                asyncio.create_task(
                    ws.send_json(
                        {
                            "error": "capture_error",
                            "message": "Input engine is recovering.",
                            "recovering": engine_state == "recovering",
                        }
                    )
                )

        if t in guarded_special_types:
            required_perm = perm_map.get(t, t)
            if required_perm not in allowed_perms:
                asyncio.create_task(
                    ws.send_json(
                        {
                            "error": "permission_denied",
                            "message": f"Token lacks '{required_perm}' permission.",
                        }
                    )
                )
                return

        # --- Non-blocking input dispatch ---
        if t == "ping":
            pass
        elif t == "move":
            mode = data.get("mode", "relative")
            if mode == "relative":
                self.mouse_worker.enqueue(
                    {
                        "type": "move_relative",
                        "dx": data.get("dx", 0),
                        "dy": data.get("dy", 0),
                    }
                )
            else:
                sw, sh = self.screen.dimensions
                self.mouse_worker.enqueue(
                    {
                        "type": "move_absolute",
                        "x": data.get("dx", 0) * sw,
                        "y": data.get("dy", 0) * sh,
                    }
                )
        elif t == "click":
            self.mouse_worker.enqueue(
                {
                    "type": "click",
                    "button": data.get("button", "left"),
                    "clicks": data.get("clicks", 1),
                }
            )
        elif t == "double_click":
            self.mouse_worker.enqueue({"type": "click", "button": "left", "clicks": 2})
        elif t == "mouse_down":
            self.mouse_worker.enqueue(
                {"type": "mouse_down", "button": data.get("button", "left")}
            )
        elif t == "mouse_up":
            self.mouse_worker.enqueue(
                {"type": "mouse_up", "button": data.get("button", "left")}
            )
        elif t == "scroll":
            self.mouse_worker.enqueue(
                {"type": "scroll", "amount": data.get("amount", 0)}
            )
        elif t == "key":
            self.mouse_worker.enqueue({"type": "key", "key": data["key"]})
        elif t == "type":
            self._enqueue_slow_op("type", data["text"])
        elif t == "hotkey":
            self._enqueue_slow_op("hotkey", data.get("keys", []))
        elif t == "screen_toggle":
            self.screen.enabled = data.get("enabled", True)
        elif t == "screen_restart":
            safe_print("[Screen] Manual restart triggered by client")
            if hasattr(self, "_event_loop"):
                self._event_loop.call_soon_threadsafe(self._manual_screen_restart)
            notify = json.dumps(
                {
                    "type": "screen_status",
                    "status": "rebuilding",
                    "message": "Restarting stream...",
                }
            )
            asyncio.create_task(self._broadcast_to_all(notify))

    def _manual_screen_restart(self):
        """Force a full teardown + rebuild of the capture engine."""
        self.screen.enabled = False
        self.screen._rebuild_backoff = 0
        loop = getattr(self, "_event_loop", None)
        if loop and loop.is_running():
            loop.call_soon_threadsafe(
                lambda: setattr(self.screen, "_rebuild_backoff", 4)
            )
        else:
            self.screen._rebuild_backoff = 4
        if loop and loop.is_running():

            def reenable():
                self.screen.enabled = True
                self.screen._attempt_rebuild()

            loop.call_soon_threadsafe(reenable)
        else:
            self.screen.enabled = True
            self.screen._attempt_rebuild()

    def _enqueue_slow_op(self, op_type, data):
        """Enqueue slow operations (typewrite/hotkey) that must not block."""
        try:
            self.mouse_worker._slow_queue.put_nowait((op_type, data))
        except queue.Full:
            pass

    async def _broadcast_screen(self):
        loop = asyncio.get_event_loop()
        last_state = None
        consecutive_empty_frames = 0
        max_empty_frames = 10  # Allow more empty frames before forcing rebuild
        last_heartbeat = time.time()
        frame_timestamp = 0

        while self._running:
            try:
                frame = None
                # Fixed frame interval calculation for precise timing
                target_interval = 1.0 / self.screen.fps
                capture_start = time.time()

                if self.screen.enabled:
                    # Use dedicated executor for screen capture - better isolation
                    frame = await loop.run_in_executor(None, self.screen.capture)
                    frame_timestamp = time.time()

                # Frame streaming with optimized payload structure
                if frame and self.clients:
                    # Pre-allocate bytearray for base64 encoding
                    b64 = base64.b64encode(frame).decode("utf-8")

                    # Optimized JSON structure - minimal overhead
                    msg = f'{{"type":"screen","data":"{b64}","ts":{int(frame_timestamp * 1000)}}}'
                    await self._broadcast_to_all(msg)

                    # Rate-based statistics - log delayed frames at most once per 10 minutes
                    interval = time.time() - frame_timestamp
                    if (
                        interval > target_interval * 1.5
                    ):  # Only log significantly delayed frames (>150% of target)
                        now = time.time()
                        if (
                            not hasattr(self, "_last_delay_log")
                            or (now - self._last_delay_log) > 600
                        ):
                            self._last_delay_log = now
                            safe_print(
                                f"[Stream] Frame delayed: {interval * 1000:.1f}ms (target {target_interval * 1000:.1f}ms)"
                            )

                elif frame:
                    # Frame captured but no clients - still working fine
                    pass

                elif not frame and self.screen.enabled:
                    consecutive_empty_frames += 1

                    # Force rebuild if engine has been failing for >5 seconds
                    time_since_success = time.time() - last_heartbeat
                    if time_since_success > 5.0 and self.screen.state in (
                        CaptureEngineState.FAILED,
                        CaptureEngineState.DEGRADED,
                    ):
                        safe_print(
                            f"[Stream] No frames for {time_since_success:.0f}s"
                            f" in {self.screen.state.name} - forcing rebuild"
                        )
                        await loop.run_in_executor(None, self.screen.force_rebuild)
                        last_heartbeat = time.time()
                    elif consecutive_empty_frames >= max_empty_frames:
                        status_name = getattr(
                            getattr(self.screen, "state", None),
                            "name",
                            "HEALTHY",
                        ).lower()
                        notify = json.dumps(
                            {
                                "type": "screen_status",
                                "status": status_name,
                                "message": self._screen_status_message(),
                                "empty_frames": consecutive_empty_frames,
                            }
                        )
                        await self._broadcast_to_all(notify)
                        consecutive_empty_frames = 0

                current_state = getattr(
                    getattr(self.screen, "state", None), "name", "HEALTHY"
                )
                if current_state != last_state:
                    last_state = current_state
                    safe_print(f"[Stream] State: {current_state}")

                # Precise sleep with remainder compensation for accurate FPS
                elapsed = time.time() - capture_start
                if elapsed > target_interval:
                    # Ran longer than interval - next iteration should start now
                    remaining = 0
                else:
                    # Schedule next frame at precise time
                    remaining = target_interval - elapsed
                await asyncio.sleep(max(0, remaining))

            except Exception as e:
                safe_print(f"[Stream] Critical error: {e}")
                # Faster recovery with aggressive backoff for critical errors
                await asyncio.sleep(0.05)

    async def start(self, tunnel_provider=None):
        self._running = True
        self._event_loop = asyncio.get_running_loop()
        self.mouse_worker.start()
        token = self.token_manager.generate_token()

        bind_host = self.tunnel_manager.resolve_bind_host(tunnel_provider, self.host)

        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, bind_host, self.port)
        await site.start()

        local_display_host = (
            "127.0.0.1" if bind_host in ("0.0.0.0", "::") else bind_host
        )
        local_url = f"http://{local_display_host}:{self.port}"
        safe_print("\n🚀 AnywhereInput Server Started")
        if bind_host != self.host:
            safe_print(
                f"  Bind Host: {bind_host}" f" (auto-selected for {tunnel_provider})"
            )
        safe_print(f"  Local: {local_url}")
        safe_print(f"  Token: {token}")
        safe_print(f"  Monitors: {self.screen.monitor_count}")
        safe_print(
            f"  Stream Quality: {self.screen.quality}/95"
            f" | Scale: {self.screen.scale:.1%}"
            f" | FPS: {self.screen.fps}"
        )
        if self.screen.monitor_count > 1:
            safe_print(
                f"  Mode: Auto-tracking cursor across"
                f" {self.screen.monitor_count} monitors"
            )

        if tunnel_provider:

            def on_url(url):
                full_link = f"{url}/static/client.html?token={token}"
                safe_print("\n🌐 Access Link (click to open):")
                safe_print(f"  {full_link}")
                display_qr(url, token)

            ok = self.tunnel_manager.start(
                tunnel_provider, bind_host, self.port, on_url
            )
            if not ok:
                safe_print(f"⚠️ Failed to start {tunnel_provider} tunnel")
                local_link = f"{local_url}/static/client.html?token={token}"
                safe_print("\n📱 Local Access Link:")
                safe_print(f"  {local_link}")
                display_qr(local_url, token)
        else:
            local_link = f"{local_url}/static/client.html?token={token}"
            safe_print("\n📱 Local Access Link:")
            safe_print(f"  {local_link}")
            display_qr(local_url, token)

        self._capture_task = asyncio.create_task(self._broadcast_screen())
        # Start the background ping/pong zombie detection loop
        self._ping_check_task = asyncio.create_task(self._ping_check_loop())
        safe_print("\n📋 Commands:")
        safe_print("  Press n to rotate token")
        safe_print("  Press Ctrl+C to stop server")
        safe_print("=" * 50)

        # Token rotation via background thread
        self_ref = self
        current_loop = asyncio.get_event_loop()

        def _rotate_loop():
            while self_ref._running:
                try:
                    import select as _select

                    s_in = sys.stdin
                    if s_in and not s_in.closed:
                        try:
                            fd = s_in.fileno()
                            ready, _, _ = _select.select([fd], [], [], 0.5)
                            if ready:
                                raw = os.read(fd, 1)
                                if raw == b"n":
                                    current_loop.call_soon_threadsafe(
                                        lambda srv=self_ref: asyncio.ensure_future(
                                            _do_rotate(srv)
                                        )
                                    )
                        except (OSError, ValueError):
                            time.sleep(0.5)
                except (BlockingIOError, OSError):
                    time.sleep(0.5)
                except Exception:
                    break

        if sys.stdin and sys.stdin.isatty():
            threading.Thread(target=_rotate_loop, daemon=True).start()
        await asyncio.Event().wait()


async def _do_rotate(server):
    new_token = server.token_manager.rotate()
    safe_print("\n🔄 Token rotated!")
    safe_print(f"  New token: {new_token}")
    safe_print("=" * 50)
