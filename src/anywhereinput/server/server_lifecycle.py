"""Server lifecycle management - start/stop, tunnels, token rotation."""

import asyncio
import logging
import os
import sys
import threading
import time
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .server_core import AnywhereInputServer

from aiohttp import web

from ..qr_display import display_qr
from anywhereinput.logging_config import get_logger, get_audit_logger
from anywhereinput.screen_capture import CaptureEngineState

log = get_logger(__name__)
audit_log = get_audit_logger()


class ServerLifecycle:
    """Manages server start/stop, tunnels, and token rotation."""

    def __init__(self, server: "AnywhereInputServer") -> None:
        self.server = server
        # Tunnel circuit breaker: prevent repeated failures when upstream is down.
        self._tunnel_circuit_state: str = "closed"  # closed | open | half-open
        self._tunnel_failures: int = 0
        self._tunnel_fail_threshold: int = 3
        self._tunnel_cooldown_ms: float = 60_000
        self._tunnel_last_failure: float = 0.0
        self._tunnel_provider: Optional[str] = None

    async def start(self, tunnel_provider: Optional[str] = None) -> None:
        """Start the server with optional tunnel provider.

        Args:
            tunnel_provider: One of "cloudflare", "tailscale", "pinggy", "zrok2",
                or None for local-only mode.
        """
        self.server._running = True
        self.server._event_loop = asyncio.get_running_loop()
        self.server.mouse_worker.start()
        token = self.server.token_manager.generate_token()

        bind_host = self.server.tunnel_manager.resolve_bind_host(
            tunnel_provider, self.server.host
        )

        self.server.runner = web.AppRunner(self.server.app)
        await self.server.runner.setup()
        site = web.TCPSite(self.server.runner, bind_host, self.server.port)
        await site.start()

        if self.server.screen.enabled:  # type: ignore[attr-defined]
            valid_frames = 0
            for _i in range(3):
                test_frame = await asyncio.get_event_loop().run_in_executor(
                    None, self.server.screen.capture  # type: ignore[attr-defined]
                )
                if test_frame is not None and len(test_frame) > 100:
                    valid_frames += 1
                else:
                    logger = logging.getLogger(__name__)
                    logger.debug(
                        "Screen capture init attempt %d returned invalid frame",
                        _i + 1,
                    )
                await asyncio.sleep(0.5)

            if valid_frames == 0:
                logger = logging.getLogger(__name__)
                logger.error(
                    "Screen capture initialization FAILED - "
                    "no valid frames after 3 attempts. Screen will be disabled."
                )
                self.server.screen.enabled = False  # type: ignore[attr-defined]
                self.server.screen.state = CaptureEngineState.FAILED  # type: ignore[attr-defined]
            else:
                logger = logging.getLogger(__name__)
                logger.info("Screen capture init OK (%d/3 valid frames)", valid_frames)

        local_display_host = (
            "127.0.0.1" if bind_host in ("0.0.0.0", "::") else bind_host
        )
        local_url = f"http://{local_display_host}:{self.server.port}"
        log.info("\nAnywhereInput Server Started")
        if bind_host != self.server.host:
            log.info(
                "  Bind Host: %s (auto-selected for %s)", bind_host, tunnel_provider
            )
        log.info("  Local: %s", local_url)
        log.info("  Token: %s", token)
        log.info("  Monitors: %s", self.server.screen.monitor_count)  # type: ignore[attr-defined]
        log.info(
            "  Stream Quality: %d/95 | Scale: %.1f%% | FPS: %d",
            self.server.screen.quality,  # type: ignore[attr-defined]
            self.server.screen.scale * 100,  # type: ignore[attr-defined]
            self.server.screen.fps,  # type: ignore[attr-defined]
        )
        if self.server.screen.monitor_count > 1:  # type: ignore[attr-defined]
            log.info(
                "  Mode: Auto-tracking cursor across %d monitors",
                self.server.screen.monitor_count,  # type: ignore[attr-defined]
            )

        if tunnel_provider:
            # --- Circuit breaker for tunnel failures ---
            now = time.time()
            if self._tunnel_circuit_state == "open":
                elapsed_ms = (now - self._tunnel_last_failure) * 1000
                if elapsed_ms < self._tunnel_cooldown_ms:
                    remaining_s = int((self._tunnel_cooldown_ms - elapsed_ms) / 1000)
                    log.warning(
                        "⚡ Tunnel circuit breaker OPEN — cooldown %ds remaining. "
                        "Falling back to local-only mode.",
                        remaining_s,
                    )
                else:
                    self._tunnel_circuit_state = "half-open"
                    log.info(
                        "⚡ Tunnel circuit breaker entering half-open — retrying..."
                    )
            elif self._tunnel_circuit_state == "half-open":
                log.info(
                    "⚡ Tunnel circuit breaker in half-open — allowing single retry attempt"
                )

            max_attempts = 2 if self._tunnel_circuit_state == "half-open" else 1
            tunnel_ok = False

            def on_url(url: str) -> None:
                log.info("\n  Tunnel URL: %s", url)
                tunnel_link = f"{url}/static/client.html?token={token}"
                log.info("  Remote Access Link: %s", tunnel_link)
                display_qr(url, token)

            for attempt in range(1, max_attempts + 1):
                ok = self.server.tunnel_manager.start(
                    tunnel_provider, bind_host, self.server.port, on_url
                )
                if ok:
                    self._tunnel_circuit_state = "closed"
                    self._tunnel_failures = 0
                    tunnel_ok = True
                    break
                else:
                    self._tunnel_failures += 1
                    self._tunnel_last_failure = now
                    log.warning(
                        "⚠️ Attempt %d/%d: Failed to start %s tunnel",
                        attempt,
                        max_attempts,
                        tunnel_provider,
                    )
                    if attempt < max_attempts:
                        await asyncio.sleep(2)

            # If we've crossed the failure threshold, open the circuit breaker.
            if (
                self._tunnel_failures >= self._tunnel_fail_threshold
                and self._tunnel_circuit_state != "open"
            ):
                self._tunnel_circuit_state = "open"
                log.error(
                    "❌ Tunnel failure threshold (%d) reached — opening circuit breaker. "
                    "Tunnels will be blocked for %ds.",
                    self._tunnel_fail_threshold,
                    int(self._tunnel_cooldown_ms / 1000),
                )

            if not tunnel_ok:
                local_link = f"{local_url}/static/client.html?token={token}"
                log.info("\nLocal Access Link (no tunnel available):")
                log.info("  %s", local_link)
                display_qr(local_url, token)
        else:
            local_link = f"{local_url}/static/client.html?token={token}"
            log.info("\nLocal Access Link:")
            log.info("  %s", local_link)
            display_qr(local_url, token)

        log.info("\nCommands:")
        log.info("  Press n to rotate token")
        log.info("  Press Ctrl+C to stop server")
        log.info("=" * 50)

        self.server._capture_task = asyncio.create_task(self.server.broadcast.run())
        self.server._ping_check_task = asyncio.create_task(
            self.server.clients_mgr.ping_check_loop()
        )

        # Token rotation via background thread
        self_ref = self.server
        current_loop = asyncio.get_event_loop()

        def _rotate_loop() -> None:
            """Poll stdin for token rotation request.

            Falls back to checking an environment variable (AITOKEN_ROTATE) every 5 s
            so daemon / systemd / non-TTY deployments can still trigger rotation.
            """
            while self_ref._running:
                triggered = False
                try:
                    # --- TTY path: character 'n' on stdin ---
                    if sys.stdin and not sys.stdin.closed:
                        try:
                            fd = sys.stdin.fileno()
                            ready, _, _ = __import__("select").select([fd], [], [], 0.5)
                            if ready:
                                raw = os.read(fd, 1)
                                if raw == b"n":
                                    triggered = True
                        except (OSError, ValueError):
                            time.sleep(0.5)

                    # --- Non-TTY fallback: env var AITOKEN_ROTATE ---
                    trigger_env = (
                        os.environ.pop("AITOKEN_ROTATE", "") if not triggered else ""
                    )
                    if trigger_env == "1" and not triggered:
                        log.info("[Token] Rotation requested via AITOKEN_ROTATE=1")
                        triggered = True
                except Exception as e:
                    log.debug("Token rotation poll error: %s", e)

                if triggered:
                    current_loop.call_soon_threadsafe(
                        lambda: asyncio.ensure_future(_do_rotate(self_ref))
                    )
                    time.sleep(0.5)  # debounce

        if sys.stdin and sys.stdin.isatty():
            log.info("\nCommands:")
            log.info("  Press n to rotate token")
        else:
            log.info("\nToken rotation: set env AITOKEN_ROTATE=1 on any connected node")

        threading.Thread(target=_rotate_loop, daemon=True).start()

        await asyncio.Event().wait()

    async def stop(self, restart: bool = False) -> None:
        """Stop the server gracefully.

        Args:
            restart: If True, notify clients that server is restarting.
        """
        self.server._running = False

        # Notify connected clients before tearing down
        if restart and self.server.clients:
            import json as _json

            notice = _json.dumps(
                {"type": "server_restarting", "message": "Server is restarting..."}
            )
            await self.server.broadcast.broadcast_to_all(notice)
            # Give clients a moment to receive the message
            await asyncio.sleep(0.2)
            # Close all clients with WS_CLOSE_SERVER_RESTART (1012)
            from .._constants import WS_CLOSE_SERVER_RESTART

            async with self.server.clients_lock:
                for ws in list(self.server.clients):
                    try:
                        if not ws.closed:
                            await ws.close(
                                code=WS_CLOSE_SERVER_RESTART,
                                message=b"Server restarting",
                            )
                    except Exception:
                        pass
                self.server.clients.clear()
            self.server._client_tokens.clear()
            self.server._client_meta.clear()
            self.server._pong_timestamps.clear()

        self.server.mouse_worker.stop()
        if self.server._capture_task:
            self.server._capture_task.cancel()
            self.server._capture_task = None
        if self.server._ping_check_task:
            self.server._ping_check_task.cancel()
            self.server._ping_check_task = None
        self.server.token_manager.clear_tokens()
        self.server.tunnel_manager.stop()
        if self.server.runner:
            await self.server.runner.cleanup()
        self.server.screen.close()  # type: ignore[attr-defined]


async def _do_rotate(server: "AnywhereInputServer") -> None:
    """Rotate token - called from token rotation thread."""
    # Guard against shutdown race: server.stop() may have already cleared tokens.
    if not server._running:
        log.debug("Token rotation skipped — server is stopping")
        return
    old_token = ""
    try:
        old_token = (
            next(iter(server.token_manager.tokens.keys()))
            if server.token_manager.tokens
            else ""
        )
    except StopIteration:
        log.warning("Token rotation skipped — no tokens to rotate")
        return

    new_token = server.token_manager.rotate()
    log.info("\nToken rotated!")
    log.info("  New token: %s", new_token)
    log.info("=" * 50)

    # Audit log
    audit_log.token_rotated(old_token, new_token, "console_user")
