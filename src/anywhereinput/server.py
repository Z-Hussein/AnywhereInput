"""Main aiohttp WebSocket server with screen capture and input handling."""

import os
import sys
import json
import asyncio
import base64
import argparse
import signal
import threading
import queue
import platform
import time
from pathlib import Path
from typing import Optional, Set

import aiohttp
from aiohttp import web
import pyautogui

from anywhereinput import __version__

from .auth import TokenManager
from .screen_capture import ScreenCapture
from .tunnel_manager import TunnelManager
from .qr_display import display_qr
from .client import ClientHandler

# Optimize pyautogui for minimum latency
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0


class MouseWorker(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.queue = queue.Queue(maxsize=200)
        self.lock = threading.Lock()
        self.running = True
        self.screen_w, self.screen_h = pyautogui.size()
        self.target_x = self.screen_w / 2
        self.target_y = self.screen_h / 2
        self.current_x = self.screen_w / 2
        self.current_y = self.screen_h / 2
        self.smoothing = 0.95
        self.min_step = 1.0
        self.mouse_down_state = {}

    def enqueue(self, item):
        """Thread-safe enqueue with drop-on-full to prevent memory explosion."""
        try:
            self.queue.put_nowait(item)
        except queue.Full:
            print("[MouseWorker] Queue full, dropping input")

    def run(self):
        while self.running:
            try:
                dx_total = dy_total = 0
                mode = None

                # Batch process up to 20 items per tick to prevent lag buildup
                items = []
                try:
                    while len(items) < 20:
                        items.append(self.queue.get_nowait())
                except queue.Empty:
                    pass

                with self.lock:
                    for item in items:
                        t = item.get("type")
                        if t == "move_relative":
                            dx_total += item.get("dx", 0)
                            dy_total += item.get("dy", 0)
                            mode = "relative"
                        elif t == "move_absolute":
                            self.target_x = item.get("x", self.target_x)
                            self.target_y = item.get("y", self.target_y)
                            mode = "absolute"
                        elif t == "click":
                            pyautogui.click(
                                button=item.get("button", "left"),
                                clicks=item.get("clicks", 1)
                            )
                        elif t == "mouse_down":
                            btn = item.get("button", "left")
                            if not self.mouse_down_state.get(btn, False):
                                pyautogui.mouseDown(button=btn)
                                self.mouse_down_state[btn] = True
                        elif t == "mouse_up":
                            btn = item.get("button", "left")
                            if self.mouse_down_state.get(btn, False):
                                pyautogui.mouseUp(button=btn)
                                self.mouse_down_state[btn] = False
                        elif t == "scroll":
                            pyautogui.scroll(item.get("amount", 0))
                        elif t == "key":
                            pyautogui.press(item.get("key", ""))
                        elif t == "type":
                            text = item.get("text", "")
                            if text:
                                pyautogui.typewrite(text, interval=0.01)
                        elif t == "hotkey":
                            keys = item.get("keys", "")
                            if keys:
                                if isinstance(keys, str):
                                    keys = [k.strip().lower() for k in keys.split(",") if k.strip()]

                                if platform.system() == "Darwin":
                                    keys = ["cmd" if k == "win" else k for k in keys]
                                keys = ["del" if k == "delete" else k for k in keys]

                                if keys:
                                    try:
                                        print(f"[Hotkey] Executing: {'+'.join(k.upper() for k in keys)}")
                                        for key in keys[:-1]:
                                            pyautogui.keyDown(key)
                                        time.sleep(0.05)
                                        pyautogui.press(keys[-1])
                                        time.sleep(0.05)
                                        for key in reversed(keys[:-1]):
                                            pyautogui.keyUp(key)
                                        print(f"Hotkey executed: {'+'.join(k.upper() for k in keys)}")
                                    except Exception as e:
                                        print(f"Hotkey {keys} failed: {e}")

                if mode == "relative" and (dx_total != 0 or dy_total != 0):
                    self.target_x += dx_total
                    self.target_y += dy_total
                    self.target_x = max(0, min(self.screen_w, self.target_x))
                    self.target_y = max(0, min(self.screen_h, self.target_y))
                    self.current_x = self.target_x
                    self.current_y = self.target_y
                    pyautogui.moveTo(int(self.current_x), int(self.current_y), duration=0)
                elif mode == "absolute":
                    self.current_x = self.target_x
                    self.current_y = self.target_y
                    pyautogui.moveTo(int(self.current_x), int(self.current_y), duration=0)

                threading.Event().wait(0.008)
            except Exception as e:
                print(f"[MouseWorker] Error: {e}")
                threading.Event().wait(0.1)

    def stop(self):
        self.running = False
        with self.lock:
            for btn, held in self.mouse_down_state.items():
                if held:
                    try:
                        pyautogui.mouseUp(button=btn)
                    except Exception:
                        pass


class AnywhereInputServer:
    def __init__(self, host="127.0.0.1", port=8008, fps=30, quality=95, scale=1.0, no_capture=False, monitor=0):
        self.host = host
        self.port = port
        self.token_manager = TokenManager()
        self.screen = ScreenCapture(fps=fps, quality=quality, scale=scale, monitor_index=monitor if monitor > 0 else None)
        self.screen.enabled = not no_capture
        self.tunnel_manager = TunnelManager()
        self.client_handler = ClientHandler()
        self.clients: Set[web.WebSocketResponse] = set()
        self.clients_lock = asyncio.Lock()
        self.app = web.Application()
        self.runner: Optional[web.AppRunner] = None
        self._setup_routes()
        self._running = False
        self._capture_task: Optional[asyncio.Task] = None
        self.mouse_worker = MouseWorker()

    def _setup_routes(self):
        self.app.router.add_get("/", self.client_handler.index)
        self.app.router.add_get("/static/{filename}", self.client_handler.static_file)
        self.app.router.add_get("/ws", self.websocket_handler)
        self.app.router.add_get("/api/screen", self.screen_info)
        self.app.router.add_get("/api/monitors", self.monitors_info)
        self.app.router.add_post("/api/monitor/{index}", self.set_monitor)

    def _authenticate(self, request) -> bool:
        """Validate the session token for HTTP API requests.

        Accepts the token via `Authorization: Bearer <token>` header, with a
        `?token=` query param fallback for callers that can't set headers.
        """
        auth_header = request.headers.get("Authorization", "")
        token = ""
        if auth_header.startswith("Bearer "):
            token = auth_header[len("Bearer "):].strip()
        if not token:
            token = request.query.get("token", "")
        return self.token_manager.validate(token)

    async def screen_info(self, request):
        if not self._authenticate(request):
            return web.json_response({"error": "Unauthorized"}, status=401)
        w, h = self.screen.dimensions
        return web.json_response({"width": w, "height": h})

    async def monitors_info(self, request):
        if not self._authenticate(request):
            return web.json_response({"error": "Unauthorized"}, status=401)
        return web.json_response({
            "monitors": self.screen.get_monitor_info(),
            "current": self.screen.current_monitor_index,
            "auto_track": self.screen._monitor_index is None,
        })

    async def set_monitor(self, request):
        if not self._authenticate(request):
            return web.json_response({"error": "Unauthorized"}, status=401)
        try:
            idx = int(request.match_info["index"])
            ok = self.screen.set_monitor(idx)
            return web.json_response({
                "success": ok,
                "monitor": self.screen.current_monitor_index,
                "auto_track": self.screen._monitor_index is None
            })
        except ValueError:
            return web.json_response({"success": False, "error": "Invalid monitor index"}, status=400)

    async def websocket_handler(self, request):
        # Origin validation to prevent CSRF on WebSocket.
        # Default-deny: a missing/empty Origin header is treated as NOT
        # allowed, not as "skip the check." Browsers always send Origin for
        # WebSocket upgrade requests, so this only blocks non-browser
        # clients that omit it -- which is the point.
        origin = request.headers.get('Origin', '')
        allowed = False
        if origin:
            host = request.headers.get('Host', '')
            if origin == f"http://{host}" or origin == f"https://{host}":
                allowed = True
            elif 'trycloudflare.com' in origin or 'ngrok-free' in origin or 'pinggy' in origin or 'zrok' in origin:
                allowed = True
            elif origin in ('http://localhost:8008', 'https://localhost:8008',
                             'http://127.0.0.1:8008', 'https://127.0.0.1:8008'):
                allowed = True
        if not allowed:
            return web.Response(status=403, text="Origin not allowed")

        ws = web.WebSocketResponse(heartbeat=30.0, timeout=5.0)
        await ws.prepare(request)
        try:
            msg = await ws.receive_json(timeout=10)
            token = msg.get("token", "")
            msg_type = msg.get("type", "")
            if msg_type not in ("auth", "handshake") or not self.token_manager.validate(token):
                await ws.send_json({"type": "error", "message": "Invalid token"})
                await ws.close()
                return ws
            await ws.send_json({"type": "auth_ok"})
        except Exception:
            await ws.close()
            return ws

        async with self.clients_lock:
            self.clients.add(ws)
        print(f"[WS] Client connected. Total: {len(self.clients)}")
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    await self._handle_message(ws, msg.json())
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    print(f"[WS] Error: {ws.exception()}")
        except asyncio.CancelledError:
            pass
        finally:
            try:
                await ws.close()
            except Exception:
                pass
            async with self.clients_lock:
                self.clients.discard(ws)
            print(f"[WS] Client disconnected. Total: {len(self.clients)}")
        return ws

    async def _handle_message(self, ws, data):
        t = data.get("type")
        if t == "ping":
            await ws.send_json({"type": "pong"})
        elif t == "move":
            mode = data.get("mode", "relative")
            if mode == "relative":
                self.mouse_worker.enqueue({
                    "type": "move_relative",
                    "dx": data.get("dx", 0),
                    "dy": data.get("dy", 0)
                })
            else:
                sw, sh = self.screen.dimensions
                self.mouse_worker.enqueue({
                    "type": "move_absolute",
                    "x": data.get("dx", 0) * sw,
                    "y": data.get("dy", 0) * sh
                })
        elif t == "click":
            self.mouse_worker.enqueue({
                "type": "click",
                "button": data.get("button", "left"),
                "clicks": data.get("clicks", 1)
            })
        elif t == "double_click":
            self.mouse_worker.enqueue({"type": "click", "button": "left", "clicks": 2})
        elif t == "mouse_down":
            self.mouse_worker.enqueue({"type": "mouse_down", "button": data.get("button", "left")})
        elif t == "mouse_up":
            self.mouse_worker.enqueue({"type": "mouse_up", "button": data.get("button", "left")})
        elif t == "scroll":
            self.mouse_worker.enqueue({"type": "scroll", "amount": data.get("amount", 0)})
        elif t == "key" and data.get("key"):
            self.mouse_worker.enqueue({"type": "key", "key": data["key"]})
        elif t == "type" and data.get("text"):
            self.mouse_worker.enqueue({"type": "type", "text": data["text"]})
        elif t == "hotkey" and data.get("keys"):
            self.mouse_worker.enqueue({"type": "hotkey", "keys": data["keys"]})
        elif t == "screen_toggle":
            self.screen.enabled = data.get("enabled", True)

    async def _broadcast_screen(self):
        frame_interval = 1.0 / self.screen.fps
        loop = asyncio.get_event_loop()
        while self._running:
            try:
                if self.clients and self.screen.enabled:
                    # Run capture in thread pool to avoid blocking event loop
                    frame = await loop.run_in_executor(None, self.screen.capture)
                    if frame:
                        b64 = base64.b64encode(frame).decode('utf-8')
                        msg = json.dumps({"type": "screen", "data": b64})
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
                                self.clients -= dead
                await asyncio.sleep(frame_interval)
            except Exception as e:
                print(f"[Screen] Error: {e}")
                await asyncio.sleep(1)

    async def start(self, tunnel_provider=None):
        self._running = True
        self.mouse_worker.start()
        token = self.token_manager.generate_token()

        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, self.host, self.port)
        await site.start()

        local_url = f"http://{self.host}:{self.port}"
        print(f"\n🚀 AnywhereInput Server Started")
        print(f"  Local: {local_url}")
        print(f"  Token: {token}")
        print(f"  Monitors: {self.screen.monitor_count}")
        print(f"  Stream Quality: {self.screen.quality}/95 | Scale: {self.screen.scale:.1%} | FPS: {self.screen.fps}")
        if self.screen.monitor_count > 1:
            print(f"  Mode: Auto-tracking cursor across {self.screen.monitor_count} monitors")

        if tunnel_provider:
            def on_url(url):
                full_link = f"{url}/static/client.html?token={token}"
                print(f"\n🌐 Access Link (click to open):")
                print(f"  {full_link}")
                display_qr(url, token)
            ok = self.tunnel_manager.start(tunnel_provider, self.port, on_url)
            if not ok:
                print(f"⚠️ Failed to start {tunnel_provider} tunnel")
                local_link = f"{local_url}/static/client.html?token={token}"
                print(f"\n📱 Local Access Link:")
                print(f"  {local_link}")
                display_qr(local_url, token)
        else:
            local_link = f"{local_url}/static/client.html?token={token}"
            print(f"\n📱 Local Access Link:")
            print(f"  {local_link}")
            display_qr(local_url, token)

        self._capture_task = asyncio.create_task(self._broadcast_screen())
        print("\n📋 Commands:")
        print("  Press n to rotate token")
        print("  Press Ctrl+C to stop server")
        print("=" * 50)

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
                            ready, _, _ = _select.select([fd], [], [], 0)
                            if ready:
                                raw = os.read(fd, 1)
                                if raw == b'n':
                                    current_loop.call_soon_threadsafe(
                                        lambda srv=self_ref: asyncio.ensure_future(_do_rotate(srv))
                                    )
                        except (OSError, ValueError):
                            time.sleep(0.1)
                except (BlockingIOError, OSError):
                    time.sleep(0.1)
                except Exception:
                    break

        threading.Thread(target=_rotate_loop, daemon=True).start()
        await asyncio.Event().wait()


async def _do_rotate(server):
    new_token = server.token_manager.rotate()
    print(f"\n🔄 Token rotated!")
    print(f"  New token: {new_token}")
    print("=" * 50)


def main():
    parser = argparse.ArgumentParser(
        prog="anywhereinput",
        description="Control your PC from any browser. No app install, no account, no cloud dependency.",
        epilog="\n".join([
            "EXAMPLES:",
            "  anywhereinput",
            "    → Start with Cloudflare Tunnel (interactive menu)",
            "",
            "  anywhereinput --tunnel cloudflare",
            "    → Start with Cloudflare directly",
            "",
            "  anywhereinput --fps 30 --quality 75 --scale 0.7",
            "    → Lower bandwidth (slower capture, lower quality, smaller stream)",
            "",
            "  anywhereinput --tunnel tailscale",
            "    → Use Tailscale for peer-to-peer control",
            "",
            "TUNNEL PROVIDERS:",
            "  cloudflare  → Free, no account, auto-downloaded, random URL per session",
            "  tailscale   → Free tailnet P2P (requires account + same tailnet on both devices)",
            "  pinggy      → Free SSH tunnel (60 min timeout, behind firewalls OK)",
            "  zrok2       → Free with limits (5 GB/day, open-source)",
            "  ngrok       → Free tier available (reliable, large ecosystem)",
            "  [none]      → Local network only (same WiFi/LAN)",
            "",
            "PROJECT:",
            "  GitHub: https://github.com/Z-Hussein/AnywhereInput",
            "  PyPI: https://pypi.org/project/anywhereinput/",
            "  Docs: https://github.com/Z-Hussein/AnywhereInput/tree/main/docs",
        ]),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--host", default="127.0.0.1", help="Server bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8008, help="Server port (default: 8008)")
    parser.add_argument("--fps", type=int, default=120, help="Screen capture FPS: 1-120 (default: 120)")
    parser.add_argument("--quality", type=int, default=85, help="JPEG quality: 1-95 (default: 85)")
    parser.add_argument("--scale", type=float, default=1.0, help="Screen scale factor: 0.1-1.0 (default: 1.0)")
    parser.add_argument("--no-capture", action="store_true", help="Disable screen capture entirely")
    parser.add_argument("--monitor", type=int, default=0, help="Monitor to capture: 0=auto, 1+=fixed (default: 0)")
    parser.add_argument("--tunnel", choices=["cloudflare", "tailscale", "pinggy", "zrok2", "ngrok"], help="Tunnel provider (default: interactive menu)")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    args = parser.parse_args()
    server = AnywhereInputServer(
        host=args.host, port=args.port, fps=args.fps,
        quality=args.quality, scale=args.scale,
        no_capture=args.no_capture, monitor=args.monitor
    )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def _run():
        await server.start(tunnel_provider=args.tunnel)

    try:
        loop.run_until_complete(_run())
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        server._running = False
        server.mouse_worker.stop()
        if server._capture_task:
            server._capture_task.cancel()

        server.tunnel_manager.stop()

        async def _cleanup_clients():
            async with server.clients_lock:
                for ws in list(server.clients):
                    try:
                        await ws.close()
                    except Exception:
                        pass
                server.clients.clear()

        try:
            loop.run_until_complete(asyncio.wait_for(_cleanup_clients(), timeout=2))
        except Exception:
            pass

        if server.runner:
            try:
                loop.run_until_complete(server.runner.cleanup())
            except Exception:
                pass

        server.screen.close()
        print("\n✅ Server stopped")
        loop.close()


if __name__ == "__main__":
    main()
