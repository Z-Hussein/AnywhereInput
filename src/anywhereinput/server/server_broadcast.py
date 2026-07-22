"""Screen frame broadcast management for AnywhereInput server."""

from __future__ import annotations

import asyncio
import json
import time
from typing import TYPE_CHECKING

from anywhereinput.logging_config import get_logger
from .._constants import WS_CLOSE_SERVER_ERROR

if TYPE_CHECKING:
    from .server_core import AnywhereInputServer

log = get_logger(__name__)


class BroadcastManager:
    """Manages screen frame broadcasting and client state notifications."""

    def __init__(self, server: "AnywhereInputServer") -> None:
        self.server = server

    async def broadcast_to_all(self, msg: str) -> None:
        """Send a JSON message to all connected WebSocket clients."""
        dead = set()
        async with self.server.clients_lock:
            client_list = list(self.server.clients)
        for ws in client_list:
            try:
                await ws.send_str(msg)
            except Exception as e:
                log.debug("send_str failed: %s", e)
                dead.add(ws)
        if dead:
            async with self.server.clients_lock:
                for ws in dead:
                    try:
                        await ws.close(
                            code=WS_CLOSE_SERVER_ERROR, message=b"Send failed"
                        )
                    except Exception as e:
                        log.debug("close failed: %s", e)
                for ws in dead:
                    self.server._client_tokens.pop(ws, None)
                    self.server._client_meta.pop(ws, None)
                self.server._clients -= dead

    async def broadcast_to_all_bytes(self, msg: bytes) -> None:
        """Send binary message to all connected WebSocket clients."""
        dead = set()
        async with self.server.clients_lock:
            client_list = list(self.server.clients)
        for ws in client_list:
            try:
                await ws.send_bytes(msg)
            except Exception as e:
                log.debug("send_bytes failed: %s", e)
                dead.add(ws)
        if dead:
            async with self.server.clients_lock:
                for ws in dead:
                    try:
                        await ws.close(
                            code=WS_CLOSE_SERVER_ERROR, message=b"Send failed"
                        )
                    except Exception as e:
                        log.debug("close failed: %s", e)
                for ws in dead:
                    self.server._client_tokens.pop(ws, None)
                    self.server._client_meta.pop(ws, None)
                self.server._clients -= dead

    def on_screen_state_change(self, state) -> None:
        """Callback from screen capture engine on state change."""
        if not self.server._clients:
            return
        if not self.server._event_loop or self.server._event_loop.is_closed():
            return

        message = self._screen_status_message()
        msg = json.dumps(
            {
                "type": "screen_status",
                "status": state.name.lower(),
                "message": message,
            }
        )

        def _schedule_broadcast() -> None:
            asyncio.create_task(self.broadcast_to_all(msg))

        self.server._event_loop.call_soon_threadsafe(_schedule_broadcast)

    def _screen_status_message(self) -> str:
        """Return human-readable status message for current screen state."""
        state_name = getattr(
            getattr(self.server.screen, "state", None), "name", "HEALTHY"
        )
        if state_name == "REBUILDING":
            return "Reconnecting to display..."
        if state_name == "DEGRADED":
            return "Screen stream reduced quality"
        if state_name == "FAILED":
            return "Screen capture failed - retrying"
        if state_name == "OFFLINE":
            return "Screen capture unavailable"
        return ""

    def get_bandwidth_bytes_per_sec(self) -> float:
        """Compute estimated bandwidth in bytes/sec over the last 5-second window.

        Returns 0 if no frames have been sent recently.
        """
        now = time.time()
        cutoff = now - 5.0
        self.server._bw_bytes_window = [
            (t, s) for t, s in self.server._bw_bytes_window if t > cutoff
        ]
        if not self.server._bw_bytes_window:
            return 0.0
        total_bytes = sum(s for _, s in self.server._bw_bytes_window)
        # Time span of window
        first_ts = self.server._bw_bytes_window[0][0]
        last_ts = self.server._bw_bytes_window[-1][0]
        span = last_ts - first_ts
        if span > 0:
            return total_bytes / span
        # If all in same timestamp, estimate based on number of frames
        return float(len(self.server._bw_bytes_window)) * (
            total_bytes / len(self.server._bw_bytes_window)
        )

    def get_fps_estimate(self) -> int:
        """Get real-time FPS estimate from screen capturer stats."""
        try:
            return self.server.screen.fps_estimate  # type: ignore[attr-defined]
        except (AttributeError, Exception):
            return 0

    async def run(self) -> None:
        """Main broadcast loop: capture frames and broadcast to clients."""
        loop = asyncio.get_event_loop()
        last_state = None
        consecutive_empty_frames = 0
        max_empty_frames = 10
        last_heartbeat = time.time()
        frame_timestamp = 0.0

        # Adaptive FPS: track delays and auto-reduce frame rate
        self.server._adaptive_delay_count = 0
        self.server._adaptive_skip_ratio = (
            0  # 0=none, 1=skip every 2nd, 2=every 3rd, etc.
        )
        self.server._adaptive_last_reduce = time.time()

        # Bandwidth tracking: rolling window of bytes sent over last 5 seconds
        self.server._bw_bytes_window: list = []  # list of (timestamp, size) tuples

        while self.server._running:
            try:
                frame = None
                base_fps = self.server.screen.fps  # type: ignore[attr-defined]
                # Apply adaptive skip: if network is slow, effectively halve the frame rate
                effective_fps = max(
                    5, base_fps // (1 + self.server._adaptive_skip_ratio)
                )
                target_interval = 1.0 / effective_fps
                capture_start = time.time()

                if self.server.screen.enabled:  # type: ignore[attr-defined]
                    frame = await loop.run_in_executor(None, self.server.screen.capture)  # type: ignore[attr-defined]
                    frame_timestamp = time.time()

                if frame and self.server.clients:
                    # Send with per-client backpressure — skip slow clients
                    dead = set()
                    skipped = 0
                    async with self.server.clients_lock:
                        client_list = list(self.server.clients)
                    for ws in client_list:
                        # Backpressure: if previous send hasn't completed, skip frame
                        if getattr(ws, "_send_pending", False):
                            skipped += 1
                            continue
                        try:
                            ws._send_pending = True  # type: ignore[attr-defined]
                            await ws.send_bytes(frame)
                            ws._send_pending = False  # type: ignore[attr-defined]
                            ws._last_frame_time = time.time()  # type: ignore[attr-defined]
                            # Track bandwidth for this successful send
                            if self.server:
                                self.server._bw_bytes_window.append((time.time(), len(frame)))
                        except Exception as e:
                            log.debug("send_bytes failed: %s", e)
                            dead.add(ws)
                    if dead:
                        async with self.server.clients_lock:
                            for ws in dead:
                                try:
                                    await ws.close(
                                        code=WS_CLOSE_SERVER_ERROR,
                                        message=b"Send failed",
                                    )
                                except Exception:
                                    pass
                            for ws in dead:
                                self.server._client_tokens.pop(ws, None)
                                self.server._client_meta.pop(ws, None)
                            self.server._clients -= dead

                    # Adaptive FPS: if too many clients are behind, reduce frame rate
                    now = time.time()
                    interval = now - frame_timestamp
                    if interval > target_interval * 1.5:
                        self.server._adaptive_delay_count += 1
                        # Reduce FPS after 5 consecutive delays (but not more than every 2s)
                        if (
                            self.server._adaptive_delay_count >= 5
                            and self.server._adaptive_skip_ratio < 4
                            and (now - self.server._adaptive_last_reduce) > 2.0
                        ):
                            self.server._adaptive_skip_ratio += 1
                            self.server._adaptive_last_reduce = now
                            self.server._adaptive_delay_count = 0
                            log.info(
                                "[Stream] Adaptive: reducing effective FPS to %d "
                                "(skip_ratio=%d, %d clients, %d skipped)",
                                effective_fps,
                                self.server._adaptive_skip_ratio,
                                len(client_list),
                                skipped,
                            )
                    else:
                        # Reset delay count on good frames, recover FPS slowly
                        if self.server._adaptive_delay_count > 0:
                            self.server._adaptive_delay_count -= 1
                        elif self.server._adaptive_skip_ratio > 0 and skipped == 0:
                            # No delays and no skips for a while — try recovering
                            if (now - self.server._adaptive_last_reduce) > 5.0:
                                self.server._adaptive_skip_ratio -= 1
                                self.server._adaptive_last_reduce = now
                                log.info(
                                    "[Stream] Adaptive: recovering FPS to %d",
                                    effective_fps,
                                )

                elif frame:
                    pass

                elif not frame and self.server.screen.enabled:  # type: ignore[attr-defined]
                    consecutive_empty_frames += 1

                    time_since_success = time.time() - last_heartbeat
                    from anywhereinput.screen_capture import CaptureEngineState

                    if (
                        time_since_success > 5.0
                        and self.server.screen.state  # type: ignore[attr-defined]
                        in (
                            CaptureEngineState.FAILED,
                            CaptureEngineState.DEGRADED,
                        )
                    ):
                        log.warning(
                            "[Stream] No frames for %.0fs in %s - forcing rebuild",
                            time_since_success,
                            self.server.screen.state.name,  # type: ignore[attr-defined]
                        )
                        await loop.run_in_executor(
                            None, self.server.screen.force_rebuild  # type: ignore[attr-defined]
                        )
                        last_heartbeat = time.time()
                    elif consecutive_empty_frames >= max_empty_frames:
                        status_name = getattr(
                            getattr(self.server.screen, "state", None),
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
                        await self.broadcast_to_all(notify)
                        consecutive_empty_frames = 0

                current_state = getattr(
                    getattr(self.server.screen, "state", None), "name", "HEALTHY"
                )
                if current_state != last_state:
                    last_state = current_state
                    log.info("[Stream] State: %s", current_state)

                elapsed = time.time() - capture_start
                if elapsed > target_interval:
                    remaining = 0
                else:
                    remaining = target_interval - elapsed
                await asyncio.sleep(max(0, remaining))

            except Exception as e:
                log.exception("[Stream] Critical error: %s", e)
                await asyncio.sleep(0.05)
