"""Input message processing for AnywhereInput server."""

import asyncio
import queue
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aiohttp import web
    from .server_core import AnywhereInputServer

from .._permissions import MESSAGE_PERMISSION_MAP, get_default_permissions
from anywhereinput.logging_config import get_logger

log = get_logger(__name__)


class MessageHandler:
    """Processes WebSocket messages - validates permissions and dispatches input."""

    def __init__(self, server: "AnywhereInputServer") -> None:
        self.server = server

    def handle(self, ws: "web.WebSocketResponse", data: dict) -> None:
        """Process a single WebSocket message from client.

        Validates permissions and engine state, then dispatches input
        commands to MouseWorker or toggles screen capture.

        Args:
            ws: The WebSocket connection.
            data: Parsed JSON message with "type" and payload.
        """
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

        allowed_perms = get_default_permissions()
        if ws in self.server._client_tokens:
            token_val = self.server._client_tokens[ws]
            if token_val in self.server.token_manager.tokens:
                allowed_perms = self.server.token_manager.tokens[token_val].get(
                    "permissions", get_default_permissions()
                )

        perm_map = MESSAGE_PERMISSION_MAP

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

            engine_state = self.server.mouse_worker.get_engine_state()
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
                return

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
                self.server.mouse_worker.enqueue(
                    {
                        "type": "move_relative",
                        "dx": data.get("dx", 0),
                        "dy": data.get("dy", 0),
                    }
                )
            else:
                sw, sh = self.server.screen.dimensions  # type: ignore[attr-defined]
                self.server.mouse_worker.enqueue(
                    {
                        "type": "move_absolute",
                        "x": data.get("dx", 0) * sw,
                        "y": data.get("dy", 0) * sh,
                    }
                )
        elif t == "click":
            self.server.mouse_worker.enqueue(
                {
                    "type": "click",
                    "button": data.get("button", "left"),
                    "clicks": data.get("clicks", 1),
                }
            )
        elif t == "double_click":
            self.server.mouse_worker.enqueue(
                {"type": "click", "button": "left", "clicks": 2}
            )
        elif t == "mouse_down":
            self.server.mouse_worker.enqueue(
                {"type": "mouse_down", "button": data.get("button", "left")}
            )
        elif t == "mouse_up":
            self.server.mouse_worker.enqueue(
                {"type": "mouse_up", "button": data.get("button", "left")}
            )
        elif t == "scroll":
            self.server.mouse_worker.enqueue(
                {"type": "scroll", "amount": data.get("amount", 0)}
            )
        elif t == "key":
            self.server.mouse_worker.enqueue({"type": "key", "key": data["key"]})
        elif t == "type":
            self._enqueue_slow_op("type", data["text"])
        elif t == "hotkey":
            self._enqueue_slow_op("hotkey", data.get("keys", []))
        elif t == "screen_toggle":
            self.server.screen.enabled = data.get("enabled", True)  # type: ignore[attr-defined]
        elif t == "screen_restart":
            log.info("[Screen] Manual restart triggered by client")
            if (
                hasattr(self.server, "_event_loop")
                and self.server._event_loop is not None
            ):
                self.server._event_loop.call_soon_threadsafe(
                    self._manual_screen_restart
                )
            asyncio.create_task(
                self.server.broadcast.broadcast_to_all(
                    '{"type":"screen_status","status":"rebuilding","message":"Restarting stream..."}'
                )
            )

    def _manual_screen_restart(self) -> None:
        """Force a full teardown and rebuild of the capture engine.

        Called when client requests stream restart.
        """
        self.server.screen.enabled = False  # type: ignore[attr-defined]
        self.server.screen._rebuild_backoff = 0  # type: ignore[attr-defined]
        loop = getattr(self.server, "_event_loop", None)
        if loop and loop.is_running():
            loop.call_soon_threadsafe(
                lambda: setattr(self.server.screen, "_rebuild_backoff", 4)  # type: ignore[attr-defined]
            )
        else:
            self.server.screen._rebuild_backoff = 4  # type: ignore[attr-defined]
        if loop and loop.is_running():

            def reenable() -> None:
                self.server.screen.enabled = True  # type: ignore[attr-defined]
                self.server.screen._attempt_rebuild()  # type: ignore[attr-defined]

            loop.call_soon_threadsafe(reenable)
        else:
            self.server.screen.enabled = True  # type: ignore[attr-defined]
            self.server.screen._attempt_rebuild()  # type: ignore[attr-defined]

    def _enqueue_slow_op(self, op_type: str, data) -> None:
        """Enqueue slow operations (typewrite/hotkey) that must not block.

        Args:
            op_type: "type" or "hotkey".
            data: Text string for typing, or list of keys for hotkey.
        """
        try:
            self.server.mouse_worker._slow_queue.put_nowait((op_type, data))
        except queue.Full:
            pass
