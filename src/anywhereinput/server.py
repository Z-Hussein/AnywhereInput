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
import shutil
import subprocess
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

TUNNEL_CHOICES = ["cloudflare", "tailscale", "pinggy", "zrok2", "ngrok", "local"]

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
        self.max_queue_age_seconds = 2.0
        self.base_recovery_backoff_seconds = 0.05
        self.max_recovery_backoff_seconds = 1.0
        self.max_failures_before_long_backoff = 5
        self.max_failures_before_offline = 12
        self.consecutive_failures = 0
        self.recovering_until = 0.0
        self.last_error = ""

    def get_engine_state(self) -> str:
        now = time.monotonic()
        if self.consecutive_failures >= self.max_failures_before_offline:
            return "offline"
        if now < self.recovering_until:
            return "recovering"
        if self.consecutive_failures > 0:
            return "degraded"
        return "healthy"

    def get_engine_status(self) -> dict:
        now = time.monotonic()
        return {
            "state": self.get_engine_state(),
            "consecutive_failures": self.consecutive_failures,
            "recovering_for_seconds": max(0.0, self.recovering_until - now),
            "last_error": self.last_error,
        }

    def _current_backoff(self) -> float:
        backoff = self.base_recovery_backoff_seconds * (2 ** max(0, self.consecutive_failures - 1))
        if self.consecutive_failures >= self.max_failures_before_long_backoff:
            backoff = max(backoff, 0.5)
        return min(backoff, self.max_recovery_backoff_seconds)

    @staticmethod
    def _classify_input_error(err: Exception) -> str:
        e = str(err).lower()
        if any(k in e for k in ("access denied", "permission", "blocked", "uac", "privilege")):
            return "degraded"
        if any(k in e for k in ("display", "screen", "monitor", "rdp", "disconnect")):
            return "failed"
        return "transient"

    def enqueue(self, item):
        """Thread-safe enqueue with drop-on-full to prevent memory explosion."""
        queued_item = dict(item)
        queued_item["_enqueued_at"] = time.monotonic()
        try:
            self.queue.put_nowait(queued_item)
        except queue.Full:
            print("[MouseWorker] Queue full, dropping input")

    def run(self):
        while self.running:
            try:
                now = time.monotonic()
                if now < self.recovering_until:
                    threading.Event().wait(self.recovering_until - now)
                    continue

                dx_total = dy_total = 0
                mode = None
                handled_any = False

                # Batch process up to 20 items per tick to prevent lag buildup
                items = []
                try:
                    while len(items) < 20:
                        items.append(self.queue.get_nowait())
                except queue.Empty:
                    pass

                with self.lock:
                    for item in items:
                        age = time.monotonic() - item.get("_enqueued_at", time.monotonic())
                        if age > self.max_queue_age_seconds:
                            continue

                        t = item.get("type")
                        if t == "move_relative":
                            dx_total += item.get("dx", 0)
                            dy_total += item.get("dy", 0)
                            mode = "relative"
                            handled_any = True
                        elif t == "move_absolute":
                            self.target_x = item.get("x", self.target_x)
                            self.target_y = item.get("y", self.target_y)
                            mode = "absolute"
                            handled_any = True
                        elif t == "click":
                            pyautogui.click(
                                button=item.get("button", "left"),
                                clicks=item.get("clicks", 1)
                            )
                            handled_any = True
                        elif t == "mouse_down":
                            btn = item.get("button", "left")
                            if not self.mouse_down_state.get(btn, False):
                                pyautogui.mouseDown(button=btn)
                                self.mouse_down_state[btn] = True
                            handled_any = True
                        elif t == "mouse_up":
                            btn = item.get("button", "left")
                            if self.mouse_down_state.get(btn, False):
                                pyautogui.mouseUp(button=btn)
                                self.mouse_down_state[btn] = False
                            handled_any = True
                        elif t == "scroll":
                            pyautogui.scroll(item.get("amount", 0))
                            handled_any = True
                        elif t == "key":
                            pyautogui.press(item.get("key", ""))
                            handled_any = True
                        elif t == "type":
                            text = item.get("text", "")
                            if text:
                                pyautogui.typewrite(text, interval=0.01)
                                handled_any = True
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
                                        handled_any = True
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
                    handled_any = True

                if handled_any and self.consecutive_failures:
                    self.consecutive_failures = 0
                    self.recovering_until = 0.0

                threading.Event().wait(0.008)
            except Exception as e:
                self.consecutive_failures += 1
                state = self._classify_input_error(e)
                backoff = self._current_backoff()
                self.recovering_until = time.monotonic() + backoff
                self.last_error = str(e)
                print(
                    f"[MouseWorker] {state} input error: {e} | "
                    f"failures={self.consecutive_failures} backoff={backoff:.2f}s"
                )
                threading.Event().wait(backoff)

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
        self.tunnel_manager = TunnelManager()
        self.client_handler = ClientHandler()
        self.clients: Set[web.WebSocketResponse] = set()
        self.clients_lock = asyncio.Lock()
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None

        self.screen = ScreenCapture(
            fps=fps,
            quality=quality,
            scale=scale,
            monitor_index=monitor if monitor > 0 else None,
            on_state_change=self._on_screen_state_change,
        )
        self.screen.enabled = not no_capture

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
        self.app.router.add_get("/api/engine", self.engine_info)
        self.app.router.add_get("/api/monitors", self.monitors_info)
        self.app.router.add_post("/api/monitor/{index}", self.set_monitor)

    async def screen_info(self, request):
        w, h = self.screen.dimensions
        return web.json_response({"width": w, "height": h})

    async def engine_info(self, request):
        status = self.mouse_worker.get_engine_status()
        screen_state = getattr(getattr(self.screen, "state", None), "name", "HEALTHY").lower()
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

    def _on_screen_state_change(self, state):
        if not self.clients:
            return
        if not self._event_loop or self._event_loop.is_closed():
            return

        message = self._screen_status_message()
        msg = json.dumps({
            "type": "screen_status",
            "status": state.name.lower(),
            "message": message,
        })

        def _schedule_broadcast():
            asyncio.create_task(self._broadcast_to_all(msg))

        self._event_loop.call_soon_threadsafe(_schedule_broadcast)

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
            return web.json_response({
                "success": ok,
                "monitor": self.screen.current_monitor_index,
                "auto_track": self.screen._monitor_index is None
            })
        except ValueError:
            return web.json_response({"success": False, "error": "Invalid monitor index"}, status=400)

    async def websocket_handler(self, request):
        # Origin validation to prevent CSRF on WebSocket
        origin = request.headers.get('Origin', '')
        if origin:
            allowed = False
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

        guarded_input_types = {
            "move", "click", "double_click", "mouse_down", "mouse_up", "scroll", "key", "type", "hotkey"
        }
        if t in guarded_input_types:
            engine_state = self.mouse_worker.get_engine_state()
            if engine_state == "offline":
                await ws.send_json({
                    "error": "capture_engine_offline",
                    "message": "Input engine is offline. Retry shortly.",
                })
                return
            if engine_state in {"recovering", "degraded"}:
                await ws.send_json({
                    "error": "capture_error",
                    "message": "Input engine is recovering.",
                    "recovering": engine_state == "recovering",
                })

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
        last_state = None
        empty_frame_count = 0
        while self._running:
            try:
                if self.clients and self.screen.enabled:
                    # Run capture in thread pool to avoid blocking event loop
                    frame = await loop.run_in_executor(None, self.screen.capture)
                    if frame:
                        empty_frame_count = 0
                        b64 = base64.b64encode(frame).decode('utf-8')
                        msg = json.dumps({"type": "screen", "data": b64})
                        await self._broadcast_to_all(msg)
                    else:
                        empty_frame_count += 1
                        if empty_frame_count >= 5:
                            status_name = getattr(getattr(self.screen, "state", None), "name", "HEALTHY").lower()
                            notify = json.dumps({
                                "type": "screen_status",
                                "status": status_name,
                                "message": self._screen_status_message(),
                            })
                            await self._broadcast_to_all(notify)
                            empty_frame_count = 0

                    current_state = getattr(getattr(self.screen, "state", None), "name", "HEALTHY")
                    if current_state != last_state:
                        last_state = current_state
                        print(f"[Screen] State: {current_state}")
                await asyncio.sleep(frame_interval)
            except Exception as e:
                print(f"[Screen] Error: {e}")
                await asyncio.sleep(1)

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

        local_display_host = "127.0.0.1" if bind_host in ("0.0.0.0", "::") else bind_host
        local_url = f"http://{local_display_host}:{self.port}"
        print(f"\n🚀 AnywhereInput Server Started")
        if bind_host != self.host:
            print(f"  Bind Host: {bind_host} (auto-selected for {tunnel_provider})")
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
            ok = self.tunnel_manager.start(tunnel_provider, bind_host, self.port, on_url)
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


def _check_cloudflare() -> bool:
    return Path("./cloudflared").is_file() or shutil.which("cloudflared") is not None


def _check_tailscale() -> bool:
    tailscale = shutil.which("tailscale")
    if not tailscale:
        return False
    try:
        result = subprocess.run(
            [tailscale, "status", "--json"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=2,
        )
        return result.returncode == 0
    except Exception:
        return False


def _check_pinggy() -> bool:
    return shutil.which("ssh") is not None


def _check_zrok() -> bool:
    return shutil.which("zrok") is not None or shutil.which("zrok2") is not None


def _check_ngrok() -> bool:
    return shutil.which("ngrok") is not None


def _status_mark(ok: bool, uncertain: bool = False) -> str:
    if ok:
        return "[OK]"
    return "[?]" if uncertain else "[X]"


def _print_launcher_banner() -> None:
    print()
    print("░█▀█░█▀█░█░█░█ ░ █░█░█░█▀▀░█▀▄░█▀▀░▀█▀░█▀█░█▀█░█░█░▀█▀")
    print("░█▀█░█░█░░█░░█▄▀▄█░█▀█░█▀▀░█▀▄░█▀▀░░█░░█░█░█▀▀░█░█░░█░")
    print("░▀░▀░▀░▀░░▀░░▀░ ░▀ ▀░▀░▀▀▀░▀░▀░▀▀▀░▀▀▀░▀░▀░▀░░░▀▀▀░░▀░.com")
    print(f"  AnywhereInput v{__version__} - Remote Control Your PC")
    print("        by AnywhereInput.com Github: @Z-Hussein")


def _print_start_menu() -> str:
    cf_ok = _status_mark(_check_cloudflare())
    ts_ok = _status_mark(_check_tailscale(), uncertain=True)
    pg_ok = _status_mark(_check_pinggy(), uncertain=True)
    zr_ok = _status_mark(_check_zrok(), uncertain=True)
    ng_ok = _status_mark(_check_ngrok(), uncertain=True)

    while True:
        _print_launcher_banner()
        print("\nSelect tunnel provider:")
        print(f"  [1] Cloudflare Tunnel (Recommended) {cf_ok}")
        print(f"  [2] Tailscale (tailnet P2P) {ts_ok}")
        print(f"  [3] Pinggy.io (SSH tunnel) {pg_ok}")
        print(f"  [4] Zrok2 {zr_ok}")
        print(f"  [5] ngrok {ng_ok}")
        print("  [6] Local only")
        print("  [S] Setup / Repair")
        print("  [Q] Quit")
        choice = input("\nEnter choice (1-6, S, Q): ").strip()

        mapping = {
            "1": "cloudflare",
            "2": "tailscale",
            "3": "pinggy",
            "4": "zrok2",
            "5": "ngrok",
            "6": "local",
        }
        if choice in mapping:
            return mapping[choice]
        if choice.lower() == "s":
            return "setup"
        if choice.lower() == "q":
            return "quit"
        print("\nInvalid choice. Please try again.")


def _run_setup_repair() -> int:
    project_root = Path(__file__).resolve().parents[2]
    if platform.system() == "Windows":
        setup_script = project_root / "scripts" / "windows" / "setup.bat"
    else:
        setup_script = project_root / "scripts" / "unix" / "setup.sh"

    if setup_script.exists():
        print(f"\n[Setup] Running: {setup_script}")
        cmd = [str(setup_script)] if setup_script.suffix != ".bat" else ["cmd", "/c", str(setup_script)]
        try:
            return subprocess.call(cmd, cwd=str(project_root))
        except Exception as e:
            print(f"[Setup] Failed to run setup script: {e}")
            return 1

    print("\n[Setup] No setup script found in this installation.")
    print("Try one of these:")
    print("  pip install --upgrade anywhereinput")
    print("  pipx upgrade anywhereinput")
    return 1


def _print_tunnel_help() -> None:
    print("\nTunnel Quick Help")
    print("  cloudflare  Free, no account, random URL each run")
    print("  tailscale   Tailnet P2P, account + same tailnet required")
    print("  pinggy      SSH-based tunnel, good behind strict firewalls")
    print("  zrok2       Open-source tunnel with free-tier limits")
    print("  ngrok       Reliable free tier with account")
    print("  local       No tunnel, same network only (--tunnel local)")


def main():
    class ModernHelpFormatter(argparse.RawDescriptionHelpFormatter):
        def __init__(self, prog):
            super().__init__(prog, max_help_position=34, width=100)

    parser = argparse.ArgumentParser(
        prog="anywhereinput",
        usage=(
            "anywhereinput [--tunnel {cloudflare,tailscale,pinggy,zrok2,ngrok,local}] [--host HOST] [--port PORT]\n"
            "              [--fps FPS] [--quality QUALITY] [--scale SCALE]\n"
            "              [--monitor MONITOR] [--no-capture] [--help-tunnels] [--version]\n\n"
            "Quick Start:\n"
            "  anywhereinput                      Start interactive launcher\n"
            "  anywhereinput --tunnel cloudflare Start immediately with Cloudflare\n"
            "  anywhereinput --tunnel local      Start local-only mode (no tunnel)\n"
            "  anywhereinput --help-tunnels      Show tunnel provider quick help"
        ),
        description="Control your PC from any browser. No app install, no account, no cloud dependency.",
        epilog="\n".join([
            "EXAMPLES:",
            "  anywhereinput",
            "    → (interactive menu)",
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
            "  anywhereinput --tunnel local",
            "    → Run on local network only (no tunnel)",
            "",
            "OTHER COMMANDS:",
            "  anywhereinput --help",
            "    → Show all options and examples",
            "",
            "  anywhereinput --help-tunnels",
            "    → Show tunnel-specific quick help",
            "",
            "  anywhereinput --version",
            "    → Show installed version",
            "",
            "TUNNEL PROVIDERS:",
            "  cloudflare  → Free, no account, auto-downloaded, random URL per session",
            "  tailscale   → Free tailnet P2P (requires account + same tailnet on both devices)",
            "  pinggy      → Free SSH tunnel (60 min timeout, behind firewalls OK)",
            "  zrok2       → Free with limits (5 GB/day, open-source)",
            "  ngrok       → Free tier available (reliable, large ecosystem)",
            "  local       → Local network only (same WiFi/LAN, no tunnel)",
            "",
            "PROJECT:",
            "  GitHub: https://github.com/Z-Hussein/AnywhereInput",
            "  PyPI: https://pypi.org/project/anywhereinput/",
            "  Docs: https://github.com/Z-Hussein/AnywhereInput/tree/main/docs",
        ]),
        formatter_class=ModernHelpFormatter,
    )
    network = parser.add_argument_group("Network")
    network.add_argument("--host", default="127.0.0.1", help="Bind address")
    network.add_argument("--port", type=int, default=8008, help="Server port")

    streaming = parser.add_argument_group("Streaming")
    streaming.add_argument("--fps", type=int, default=120, help="Capture FPS (1-120)")
    streaming.add_argument("--quality", type=int, default=85, help="JPEG quality (1-95)")
    streaming.add_argument("--scale", type=float, default=1.0, help="Scale factor (0.1-1.0)")
    streaming.add_argument("--monitor", type=int, default=0, help="Monitor index: 0=auto, 1+=fixed")
    streaming.add_argument("--no-capture", action="store_true", help="Disable screen capture")

    connectivity = parser.add_argument_group("Connectivity")
    connectivity.add_argument("--tunnel", choices=TUNNEL_CHOICES, help="Tunnel provider (default: interactive menu)")
    connectivity.add_argument("--help-tunnels", action="store_true", help="Show tunnel quick help and exit")

    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    args = parser.parse_args()

    if args.help_tunnels:
        _print_tunnel_help()
        return

    argv = sys.argv[1:]
    if not argv:
        if sys.stdin and sys.stdin.isatty():
            while True:
                selected = _print_start_menu()
                if selected == "quit":
                    return
                if selected == "setup":
                    _run_setup_repair()
                    continue
                args.tunnel = None if selected == "local" else selected
                break
        else:
            _print_launcher_banner()
            print("No interactive terminal detected; defaulting to Cloudflare Tunnel.")
            args.tunnel = "cloudflare"

    server = AnywhereInputServer(
        host=args.host, port=args.port, fps=args.fps,
        quality=args.quality, scale=args.scale,
        no_capture=args.no_capture, monitor=args.monitor
    )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def _run():
        selected_tunnel = None if args.tunnel == "local" else args.tunnel
        await server.start(tunnel_provider=selected_tunnel)

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
                    except BaseException:
                        pass
                server.clients.clear()

        try:
            loop.run_until_complete(asyncio.wait_for(_cleanup_clients(), timeout=2))
        except BaseException:
            pass

        if server.runner:
            try:
                loop.run_until_complete(server.runner.cleanup())
            except Exception:
                pass

        try:
            pending = [t for t in asyncio.all_tasks(loop) if not t.done()]
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception:
            pass

        server.screen.close()
        print("\n✅ Server stopped")
        loop.close()


if __name__ == "__main__":
    main()
