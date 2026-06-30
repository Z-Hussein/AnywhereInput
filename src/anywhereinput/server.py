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
from pathlib import Path
from typing import Optional, Set

import aiohttp
from aiohttp import web
import pyautogui

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
        self.queue = queue.Queue()
        self.running = True
        self.screen_w, self.screen_h = pyautogui.size()
        self.target_x = self.screen_w / 2
        self.target_y = self.screen_h / 2
        self.current_x = self.screen_w / 2
        self.current_y = self.screen_h / 2
        self.smoothing = 0.95  # Nearly 1.0 for near-instant movement (minimal smoothing)
        self.min_step = 1.0
        self.mouse_down_state = {}

    def run(self):
        while self.running:
            try:
                dx_total = dy_total = 0
                mode = None
                while not self.queue.empty():
                    item = self.queue.get_nowait()
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
                        pyautogui.click(button=item.get("button", "left"), clicks=item.get("clicks", 1))
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
                            # Parse comma-separated keys and clean them
                            if isinstance(keys, str):
                                keys = [k.strip().lower() for k in keys.split(",") if k.strip()]
                            
                            # Map Windows "win" to macOS "cmd"
                            if platform.system() == "Darwin":
                                keys = ["cmd" if k == "win" else k for k in keys]
                            
                            # Map "delete" to proper key name
                            keys = ["del" if k == "delete" else k for k in keys]
                            
                            # Execute hotkey with explicit key press/release for better compatibility
                            if keys:
                                try:
                                    print(f"[Hotkey] Executing: {'+'.join(k.upper() for k in keys)}")
                                    # Press all modifier keys first
                                    for key in keys[:-1]:
                                        pyautogui.keyDown(key)
                                    import time
                                    time.sleep(0.05)
                                    # Press and release the main key
                                    pyautogui.press(keys[-1])
                                    time.sleep(0.05)
                                    # Release all modifier keys
                                    for key in reversed(keys[:-1]):
                                        pyautogui.keyUp(key)
                                    print(f"✅ Hotkey executed: {'+'.join(k.upper() for k in keys)}")
                                except Exception as e:
                                    print(f"❌ Hotkey {keys} failed: {e}")

                if mode == "relative" and (dx_total != 0 or dy_total != 0):
                    self.target_x += dx_total
                    self.target_y += dy_total
                    self.target_x = max(0, min(self.screen_w, self.target_x))
                    self.target_y = max(0, min(self.screen_h, self.target_y))
                    
                    # Direct move without smoothing to eliminate lag
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
        for btn, held in self.mouse_down_state.items():
            if held:
                try:
                    pyautogui.mouseUp(button=btn)
                except Exception:
                    pass


class AnywhereInputServer:
    def __init__(self, host="0.0.0.0", port=8008, fps=30, quality=95, scale=1.0, no_capture=False, monitor=0):
        self.host = host
        self.port = port
        self.token_manager = TokenManager()
        self.screen = ScreenCapture(fps=fps, quality=quality, scale=scale, monitor_index=monitor if monitor > 0 else None)
        self.screen.enabled = not no_capture
        self.tunnel_manager = TunnelManager()
        self.client_handler = ClientHandler()
        self.clients: Set[web.WebSocketResponse] = set()
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
        self.app.router.add_get("/api/token", self.get_token)

    async def screen_info(self, request):
        w, h = self.screen.dimensions
        return web.json_response({"width": w, "height": h})

    async def monitors_info(self, request):
        return web.json_response({
            "monitors": self.screen.get_monitor_info(),
            "current": self.screen.current_monitor_index,
            "auto_track": self.screen._monitor_index is None,
        })

    async def set_monitor(self, request):
        try:
            idx = int(request.match_info["index"])
            ok = self.screen.set_monitor(idx)
            return web.json_response({"success": ok, "monitor": self.screen.current_monitor_index, "auto_track": self.screen._monitor_index is None})
        except ValueError:
            return web.json_response({"success": False, "error": "Invalid monitor index"}, status=400)

    async def get_token(self, request):
        active = None
        if hasattr(self.token_manager, 'tokens') and self.token_manager.tokens:
            active = list(self.token_manager.tokens.keys())[-1]
        return web.json_response({"token": active})

    async def websocket_handler(self, request):
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
                self.mouse_worker.queue.put({"type": "move_relative", "dx": data.get("dx", 0), "dy": data.get("dy", 0)})
            else:
                sw, sh = self.screen.dimensions
                self.mouse_worker.queue.put({"type": "move_absolute", "x": data.get("dx", 0) * sw, "y": data.get("dy", 0) * sh})
        elif t == "click":
            self.mouse_worker.queue.put({"type": "click", "button": data.get("button", "left"), "clicks": data.get("clicks", 1)})
        elif t == "double_click":
            self.mouse_worker.queue.put({"type": "click", "button": "left", "clicks": 2})
        elif t == "mouse_down":
            self.mouse_worker.queue.put({"type": "mouse_down", "button": data.get("button", "left")})
        elif t == "mouse_up":
            self.mouse_worker.queue.put({"type": "mouse_up", "button": data.get("button", "left")})
        elif t == "scroll":
            self.mouse_worker.queue.put({"type": "scroll", "amount": data.get("amount", 0)})
        elif t == "key" and data.get("key"):
            self.mouse_worker.queue.put({"type": "key", "key": data["key"]})
        elif t == "type" and data.get("text"):
            self.mouse_worker.queue.put({"type": "type", "text": data["text"]})
        elif t == "hotkey" and data.get("keys"):
            self.mouse_worker.queue.put({"type": "hotkey", "keys": data["keys"]})
        elif t == "screen_toggle":
            self.screen.enabled = data.get("enabled", True)

    async def _broadcast_screen(self):
        frame_interval = 1.0 / self.screen.fps
        while self._running:
            try:
                if self.clients and self.screen.enabled:
                    frame = self.screen.capture()
                    if frame:
                        b64 = base64.b64encode(frame).decode('utf-8')
                        msg = json.dumps({"type": "screen", "data": b64})
                        dead = set()
                        for ws in list(self.clients):
                            try:
                                await ws.send_str(msg)
                            except Exception:
                                dead.add(ws)
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
        print(f"   Local: {local_url}")
        print(f"   Token: {token}")
        print(f"   Monitors: {self.screen.monitor_count}")
        print(f"   Stream Quality: {self.screen.quality}/95 | Scale: {self.screen.scale:.1%} | FPS: {self.screen.fps}")
        if self.screen.monitor_count > 1:
            print(f"   Mode: Auto-tracking cursor across {self.screen.monitor_count} monitors")

        if tunnel_provider:
            def on_url(url):
                full_link = f"{url}/static/client.html?token={token}"
                print(f"\n🌐 Access Link (click to open):")
                print(f"   {full_link}")
                display_qr(url, token)
            ok = self.tunnel_manager.start(tunnel_provider, self.port, on_url)
            if not ok:
                print(f"⚠️  Failed to start {tunnel_provider} tunnel")
                local_link = f"{local_url}/static/client.html?token={token}"
                print(f"\n📱 Local Access Link:")
                print(f"   {local_link}")
                display_qr(local_url, token)
        else:
            local_link = f"{local_url}/static/client.html?token={token}"
            print(f"\n📱 Local Access Link:")
            print(f"   {local_link}")
            display_qr(local_url, token)

        self._capture_task = asyncio.create_task(self._broadcast_screen())
        print("\n\U0001f4cb Commands:")
        print("   Press n to rotate token")
        print("   Press Ctrl+C to stop server")
        print("=" * 50)

        # Token rotation via background thread (reads stdin, works on all platforms)
        self_ref = self
        current_loop = asyncio.get_event_loop()

        def _rotate_loop():
            while self_ref._running:
                try:
                    # Try platform-specific select (Unix/Linux/macOS)
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
                            # OSError/ValueError on Windows when select not supported on stdin
                            # Just skip token rotation - server still works fine
                            import time
                            time.sleep(0.1)
                except (BlockingIOError, OSError):
                    import time
                    time.sleep(0.1)
                except Exception:
                    break

        threading.Thread(target=_rotate_loop, daemon=True).start()
        await asyncio.Event().wait()


async def _do_rotate(server):
    new_token = server.token_manager.rotate()
    print(f"\n\U0001f504 Token rotated!")
    print(f"   New token: {new_token}")
    print("=" * 50)


def main():
    parser = argparse.ArgumentParser(description="AnywhereInput Server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8008)
    parser.add_argument("--fps", type=int, default=120, help="Frame rate: 1-120 (default: 120 for minimum latency)")
    parser.add_argument("--quality", type=int, default=85, help="JPEG quality: 1-95 (default: 85 for balance of speed and clarity)")
    parser.add_argument("--scale", type=float, default=1.0, help="Scale factor: 0.1-1.0 (default: 1.0 for full native resolution)")
    parser.add_argument("--no-capture", action="store_true")
    parser.add_argument("--monitor", type=int, default=0)
    parser.add_argument("--tunnel", choices=["cloudflare", "tailscale", "pinggy", "zrok2", "ngrok"])

    args = parser.parse_args()
    server = AnywhereInputServer(host=args.host, port=args.port, fps=args.fps, quality=args.quality, scale=args.scale, no_capture=args.no_capture, monitor=args.monitor)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def _run():
        await server.start(tunnel_provider=args.tunnel)
        # start() blocks on Event().wait(); shutdown breaks it out

    try:
        loop.run_until_complete(_run())
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        # --- Shutdown (best-effort synchronous, then exit) ---
        server._running = False
        server.mouse_worker.stop()
        if server._capture_task:
            server._capture_task.cancel()

        server.tunnel_manager.stop()

        for ws in list(server.clients):
            try:
                ws.close()  # best-effort, ignore warnings
            except Exception:
                pass
        server.clients.clear()

        if server.runner:
            try:
                server.runner.finalize()
            except AttributeError:
                pass

        server.screen.close()
        print("\u2705 Server stopped")

        os._exit(0)


if __name__ == "__main__":
    main()
