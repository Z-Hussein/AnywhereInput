"""AnywhereInputServer - HTTP/WebSocket server core (composition root)."""

import asyncio
import time
from typing import Optional, Set

from aiohttp import web

from anywhereinput.logging_config import get_logger

from ..auth import TokenManager
from anywhereinput.screen_capture import ScreenCapture
from ..tunnel_manager import TunnelManager
from ..client import ClientHandler
from ..mouse_worker import MouseWorker, _pyautogui_lock
from ._token_handlers import TokenAPI
from ._request_handlers import RequestAPI
from .._ip import parse_ip_str
from ._rate_limiter import create_rate_limiter_middleware

log = get_logger(__name__)
logger = log  # Alias for test compatibility
from .server_http import HTTPHandlers
from .server_ws import WebSocketHandler
from .server_messages import MessageHandler
from .server_broadcast import BroadcastManager
from .server_clients import ClientManager
from .server_lifecycle import ServerLifecycle


@web.middleware
async def latency_middleware(request, handler):
    """Middleware to track request latency."""
    start_time = time.perf_counter()
    try:
        response = await handler(request)
        return response
    finally:
        duration_ms = (time.perf_counter() - start_time) * 1000
        # Log slow requests (>100ms) at WARNING, others at DEBUG
        if duration_ms > 100:
            log.warning(
                "Request latency: %s %s - %.2fms",
                request.method,
                request.path,
                duration_ms,
            )
        else:
            log.debug(
                "Request latency: %s %s - %.2fms",
                request.method,
                request.path,
                duration_ms,
            )


@web.middleware
async def cors_middleware(request, handler):
    """Middleware to add CORS headers for cross-origin API access."""
    if request.method == "OPTIONS":
        response = web.Response(status=204)
    else:
        response = await handler(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Max-Age"] = "86400"
    return response


class AnywhereInputServer:
    """HTTP/WebSocket server for AnywhereInput remote control.

    Handles screen capture, WebSocket connections, input dispatch,
    authentication, and tunnel management.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8008,
        fps: int = 120,
        quality: int = 40,
        scale: float = 0.7,
        no_capture: bool = False,
        monitor: int = 0,
    ) -> None:
        """Initialize the server with capture and network settings.

        Args:
            host: Bind address for the HTTP/WebSocket server.
            port: Port to listen on.
            fps: Target screen capture frames per second (1-120).
            quality: JPEG quality for screen encoding (1-95).
            scale: Scale factor for captured frames (0.1-1.0).
            no_capture: Disable screen capture if True.
            monitor: Monitor index to capture (0 = auto-track cursor).
        """
        self.host = host
        self.port = port
        self.token_manager = TokenManager()
        self.tunnel_manager = TunnelManager()
        self.client_handler = ClientHandler()
        self._clients: Set[web.WebSocketResponse] = set()
        self.clients_lock = asyncio.Lock()
        self._client_tokens: dict = {}
        self._client_meta: dict = {}
        self._pong_timestamps: dict[web.WebSocketResponse, float] = {}
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._ping_check_task: Optional[asyncio.Task] = None
        self._running = False
        self._start_time: float = 0.0
        self._adaptive_delay_count: int = 0
        self._adaptive_skip_ratio: int = 0
        self._adaptive_last_reduce: float = 0.0

        self.screen = ScreenCapture(
            fps=fps,
            quality=quality,
            scale=scale,
            monitor_index=monitor if monitor > 0 else None,
            on_state_change=self._on_screen_state_change,
        )
        self.screen._pyautogui_lock = _pyautogui_lock  # type: ignore[attr-defined]
        self.screen.enabled = not no_capture  # type: ignore[attr-defined]

        self.app = web.Application(
            middlewares=[
                cors_middleware,
                latency_middleware,
                create_rate_limiter_middleware().middleware,
            ]
        )
        self.runner: Optional[web.AppRunner] = None
        self._capture_task: Optional[asyncio.Task] = None
        self.mouse_worker = MouseWorker()

        # Component composition
        self.http: HTTPHandlers = HTTPHandlers(self)
        self.ws: WebSocketHandler = WebSocketHandler(self)
        self.messages: MessageHandler = MessageHandler(self)
        self.broadcast: BroadcastManager = BroadcastManager(self)
        self.clients_mgr: ClientManager = ClientManager(self)
        self.lifecycle: ServerLifecycle = ServerLifecycle(self)

        self._setup_routes()

    @property
    def clients(self) -> Set[web.WebSocketResponse]:
        return self._clients

    def _on_screen_state_change(self, state) -> None:
        """Callback from screen capture engine on state change."""
        if not self.clients:
            return
        if not self._event_loop or self._event_loop.is_closed():
            return

        from anywhereinput.screen_capture import CaptureEngineState

        if state in (
            CaptureEngineState.DEGRADED,
            CaptureEngineState.FAILED,
            CaptureEngineState.REBUILDING,
        ):
            log.info(
                "[Server] Screen state changed to %s - notifying clients", state.name
            )
        self.broadcast.on_screen_state_change(state)

    def _get_client_ip(self, request):
        """Extract real client IP and port from a request."""
        xff = request.headers.get("X-Forwarded-For")
        if xff:
            first_ip = xff.split(",")[0].strip()
            if first_ip and first_ip != "unknown":
                return parse_ip_str(first_ip)
        peer = request.remote
        if isinstance(peer, str):
            return parse_ip_str(peer)
        return (getattr(peer, "host", "unknown") or "unknown"), getattr(
            peer, "port", 0
        ) or 0

    def _setup_routes(self):
        """Register all routes on the aiohttp application."""
        self.app.router.add_get("/", self.client_handler.index)
        self.app.router.add_get("/favicon.ico", self.client_handler.favicon_handler)
        self.app.router.add_static(
            "/static/", path=str(self.client_handler.static_dir), name="static"
        )
        # WebSocket endpoint
        self.app.router.add_get("/ws", self.ws.handle)
        # HTTP endpoints
        self.http.register_routes(self.app.router)
        # TokenAPI & RequestAPI routes
        self._token_api = TokenAPI(self)
        self._request_api = RequestAPI(self)
        self._token_api.register_routes(self.app.router)
        self._request_api.register_routes(self.app.router)

    async def start(self, tunnel_provider: Optional[str] = None) -> None:
        """Start the server with optional tunnel provider.

        Args:
            tunnel_provider: One of "cloudflare", "tailscale", "pinggy", "zrok2",
                or None for local-only mode.
        """
        import time as _time

        self._start_time = _time.time()
        await self.lifecycle.start(tunnel_provider)
        # Tasks are created by lifecycle.start(); no duplicate creation needed.

    async def stop(self, restart: bool = False) -> None:
        """Graceful shutdown.

        Args:
            restart: If True, notify clients that server is restarting.
        """
        await self.lifecycle.stop(restart=restart)


def main():
    """Entry point for `anywhereinput-server` - starts server directly with defaults.

    Supports graceful restart via SIGHUP (kill -HUP <pid>).
    On SIGHUP, clients are notified, the process re-execs with the same args,
    and a fresh server starts with updated config (if settings.yaml changed).
    """
    import argparse
    import asyncio
    import os
    import signal
    import sys

    from .._constants import (
        DEFAULT_HOST,
        DEFAULT_PORT,
        DEFAULT_FPS,
        DEFAULT_QUALITY,
        DEFAULT_SCALE,
        LOW_BW_FPS,
        LOW_BW_QUALITY,
        LOW_BW_SCALE,
    )
    from ..config_loader import load_settings, get_setting

    cfg = load_settings()

    parser = argparse.ArgumentParser(prog="anywhereinput-server", add_help=True)
    parser.add_argument(
        "--host",
        default=get_setting(cfg, "server", "host", default=DEFAULT_HOST),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=get_setting(cfg, "server", "port", default=DEFAULT_PORT),
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=get_setting(cfg, "screen_capture", "fps", default=DEFAULT_FPS),
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=get_setting(cfg, "screen_capture", "quality", default=DEFAULT_QUALITY),
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=get_setting(cfg, "screen_capture", "scale", default=DEFAULT_SCALE),
    )
    parser.add_argument("--monitor", type=int, default=0)
    parser.add_argument("--no-capture", action="store_true")
    parser.add_argument(
        "--low-bandwidth",
        action="store_true",
        help="Optimize for mobile data (15fps, q60, half scale)",
    )
    parser.add_argument(
        "--tunnel",
        choices=["cloudflare", "tailscale", "pinggy", "zrok2", "local"],
        default="cloudflare",
    )
    args = parser.parse_args()

    # Apply low-bandwidth preset
    if args.low_bandwidth:
        args.fps = LOW_BW_FPS
        args.quality = LOW_BW_QUALITY
        args.scale = LOW_BW_SCALE

    # SIGHUP triggers graceful restart (re-exec)
    _restart_requested = False

    def _on_sighup(signum, frame):
        nonlocal _restart_requested
        _restart_requested = True
        log.info("SIGHUP received — initiating graceful restart")

    if hasattr(signal, "SIGHUP"):
        signal.signal(signal.SIGHUP, _on_sighup)

    while True:
        _restart_requested = False
        server = AnywhereInputServer(
            host=args.host,
            port=args.port,
            fps=args.fps,
            quality=args.quality,
            scale=args.scale,
            monitor=args.monitor,
            no_capture=args.no_capture,
        )

        tunnel_provider = None if args.tunnel == "local" else args.tunnel

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        exit_reason = "unknown"
        try:
            loop.run_until_complete(server.start(tunnel_provider=tunnel_provider))
        except KeyboardInterrupt:
            exit_reason = "shutdown"
        except Exception as e:
            log.error("Server startup failed: %s", e)
            exit_reason = "error"

        # Stop the server (notify clients if restarting)
        try:
            loop.run_until_complete(
                server.stop(restart=_restart_requested and exit_reason != "error")
            )
        except Exception:
            pass
        loop.close()

        if exit_reason == "error":
            raise
        if exit_reason == "shutdown" or not _restart_requested:
            break

        # SIGHUP received — graceful restart via re-exec
        log.info("Graceful restart: re-executing server process...")
        os.execv(sys.executable, [sys.executable] + sys.argv)


if __name__ == "__main__":
    main()
