"""HTTP REST endpoints for AnywhereInput server."""

from typing import TYPE_CHECKING

from aiohttp import web

if TYPE_CHECKING:
    from .server_core import AnywhereInputServer


class HTTPHandlers:
    """Stateless HTTP request handlers - takes server reference for state access."""

    def __init__(self, server: "AnywhereInputServer") -> None:
        self.server = server

    def register_routes(self, router) -> None:
        """Register HTTP routes on the aiohttp router."""
        router.add_get("/health", self.health_check)
        router.add_get("/api/screen", self.screen_info)
        router.add_get("/api/engine", self.engine_info)
        router.add_get("/api/monitors", self.monitors_info)
        router.add_post("/api/monitor/{index}", self.set_monitor)

    async def health_check(self, request) -> web.Response:
        """Unauthenticated health endpoint for load balancers and monitoring.

        Returns:
            JSON response with server status, uptime, and connected clients.
        """
        import time as _time

        uptime = (
            _time.time() - self.server._start_time
            if hasattr(self.server, "_start_time")
            else 0
        )
        screen_state = getattr(
            getattr(self.server.screen, "state", None), "name", "UNKNOWN"
        ).lower()
        return web.json_response(
            {
                "status": "ok",
                "uptime_s": round(uptime, 1),
                "clients": len(self.server.clients),
                "screen": screen_state,
                "tunnel": self.server.tunnel_manager.url,
            }
        )

    async def screen_info(self, request) -> web.Response:
        """Return screen dimensions as JSON.

        Returns:
            JSON response with {"width": int, "height": int}.
        """
        w, h = self.server.screen.dimensions  # type: ignore[attr-defined]
        return web.json_response({"width": w, "height": h})

    async def engine_info(self, request) -> web.Response:
        """Return input engine and screen engine health status.

        Returns:
            JSON response with engine state, screen engine status,
            real-time FPS estimate, and bandwidth in bytes/sec.
        """
        import time as _time

        status = self.server.mouse_worker.get_engine_status()
        screen_state = getattr(
            getattr(self.server.screen, "state", None), "name", "HEALTHY"
        ).lower()
        status["screen_engine"] = {
            "state": screen_state,
            "enabled": self.server.screen.enabled,  # type: ignore[attr-defined]
        }

        # Real-time FPS from capturer stats (moving average over last 5s)
        fps_estimate = getattr(self.server.screen, "fps_estimate", 0)  # type: ignore[attr-defined]
        status["fps"] = fps_estimate
        # Also include base target FPS and effective FPS for debugging
        try:
            base_fps = self.server.screen.fps  # type: ignore[attr-defined]
            status["screen_engine"]["target_fps"] = base_fps
            adaptive_ratio = getattr(self.server, "_adaptive_skip_ratio", 0)
            if adaptive_ratio > 0:
                effective = max(5, base_fps // (1 + adaptive_ratio))
                status["screen_engine"]["effective_fps"] = effective
        except Exception:
            pass

        # Bandwidth: bytes/sec sent to all clients over last 5s window
        bw_bytes_sec = 0.0
        try:
            bm = getattr(self.server, "_broadcast_manager", None)
            if bm is not None:
                bw_bytes_sec = bm.get_bandwidth_bytes_per_sec()
        except Exception:
            pass
        status["bandwidth_bytes_sec"] = round(bw_bytes_sec, 1) if bw_bytes_sec else 0.0

        return web.json_response(status)

    async def monitors_info(self, request) -> web.Response:
        """Return list of monitors and current capture target.

        Returns:
            JSON response with monitors list, current monitor index, and auto_track flag.
        """
        monitors = self.server.screen.get_monitor_info()  # type: ignore[attr-defined]
        return web.json_response(
            {
                "monitors": [m.to_dict() for m in monitors],
                "current": self.server.screen.current_monitor_index,  # type: ignore[attr-defined]
                "auto_track": self.server.screen._monitor_index is None,  # type: ignore[attr-defined]
            }
        )

    async def set_monitor(self, request) -> web.Response:
        """Switch capture monitor.

        Args:
            request: aiohttp request with monitor index in path.

        Returns:
            JSON response with success flag and current monitor info.
        """
        try:
            idx = int(request.match_info["index"])
            ok = self.server.screen.set_monitor(idx)  # type: ignore[attr-defined]
            return web.json_response(
                {
                    "success": ok,
                    "monitor": self.server.screen.current_monitor_index,  # type: ignore[attr-defined]
                    "auto_track": self.server.screen._monitor_index is None,  # type: ignore[attr-defined]
                }
            )
        except ValueError:
            return web.json_response(
                {"success": False, "error": "Invalid monitor index"}, status=400
            )
