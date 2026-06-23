import asyncio
import json
import logging
import secrets
import socket
import argparse
import os
import io
import base64
import threading
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import re
from datetime import datetime
from aiohttp import web

from qr_display import generate_terminal_qr

pyautogui = None

# ─── Lazy imports for optional screen capture ─────────────────────────────
def _load_pyautogui():
    global pyautogui
    if pyautogui is not None:
        return pyautogui
    try:
        import pyautogui as p
        p.FAILSAFE = False
        p.PAUSE = 0
        p.POINT_NAMES = False
        pyautogui = p
        return pyautogui
    except Exception as exc:
        display = os.environ.get("DISPLAY")
        extra = f" DISPLAY={display}" if display else " DISPLAY is not set."
        raise RuntimeError(
            "Failed to initialize pyautogui. "
            "This program requires a working X11 display and permission to access it." +
            extra +
            "\nIf you are on Linux, run this from a logged-in desktop session or set XAUTHORITY to the correct X11 authority file."
            "\nFor example: export DISPLAY=:0 && export XAUTHORITY=$HOME/.Xauthority"
        ) from exc

# ─── CLI args (BACKWARD COMPATIBLE — all new args are optional) ───────────
parser = argparse.ArgumentParser(
    description="AnywhereInput Server",
    epilog="Example: python secure_server.py --port 9000 --token-file ./my_tokens.json -v"
)
parser.add_argument("--port", type=int, default=8080,
    help="HTTP port for the server (default: 8080)")
parser.add_argument("--bind", default="0.0.0.0",
    help="Bind address (default: 0.0.0.0, use :: for IPv6)")
parser.add_argument("--token-file", type=str, default=None,
    help="Custom path for token file (default: ./trusted_tokens.json)")
parser.add_argument("-v", "--verbose", action="store_true",
    help="Enable verbose (DEBUG) logging")
# NEW optional args for screen capture
parser.add_argument("--fps", type=int, default=30,
    help="Screen capture target FPS (default: 30, min: 1, max: 30)")
parser.add_argument("--quality", type=int, default=60,
    help="JPEG quality 1-95 (default: 60)")
parser.add_argument("--scale", type=float, default=0.5,
    help="Screen scale factor 0.1-1.0 (default: 0.5)")
parser.add_argument("--no-capture", action="store_true",
    help="Disable screen capture entirely")
args = parser.parse_args()

# ─── Logging ──────────────────────────────────────────────────────────────
log_level = logging.DEBUG if args.verbose else logging.INFO
logging.basicConfig(level=log_level, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
TOKEN_FILE = Path(args.token_file) if args.token_file else BASE_DIR / "trusted_tokens.json"
HTTP_PORT = args.port
BIND_ADDRESS = args.bind
WS_PORT = 8765

CAPTURE_FPS = max(1, min(30, args.fps))
JPEG_QUALITY = max(1, min(95, args.quality))
SCREEN_SCALE = max(0.1, min(1.0, args.scale))
ENABLE_CAPTURE = not args.no_capture

logger.info("Config: port=%d, bind=%s, capture=%s, fps=%d, quality=%d, scale=%.2f",
    HTTP_PORT, BIND_ADDRESS, ENABLE_CAPTURE, CAPTURE_FPS, JPEG_QUALITY, SCREEN_SCALE)

# ─── Network helpers (UNCHANGED) ────────────────────────────────────────────
def get_local_addresses():
    addresses = set()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            addresses.add(sock.getsockname()[0])
    except Exception:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, family=socket.AF_INET):
            addresses.add(info[4][0])
    except Exception:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, family=socket.AF_INET6):
            addr = info[4][0]
            if addr and not addr.startswith("::1"):
                addresses.add(addr.split("%", 1)[0])
    except Exception:
        pass
    return sorted(
        addr for addr in addresses if not addr.startswith("127.") and not addr.startswith("::1")
    )

# ─── Token management (UNCHANGED) ───────────────────────────────────────────
def load_tokens():
    try:
        default_token = secrets.token_hex(16)
        tokens = {
            default_token: {
                "name": "android-client",
                "created": datetime.utcnow().isoformat() + "Z",
                "permissions": ["move", "click", "scroll", "keyboard"],
            }
        }
        save_tokens(tokens)
        logger.info("Generated new access token and wrote to %s", TOKEN_FILE.resolve())
        return tokens
    except Exception as exc:
        logger.exception("Failed to generate or save token: %s", exc)
        if TOKEN_FILE.exists():
            try:
                with TOKEN_FILE.open("r", encoding="utf-8") as fh:
                    return json.load(fh)
            except Exception:
                pass
        return {}

def save_tokens(tokens):
    with TOKEN_FILE.open("w", encoding="utf-8") as fh:
        json.dump(tokens, fh, indent=2)

tokens = load_tokens()


# ═══════════════════════════════════════════════════════════════════════════
# FIXED: SCREEN CAPTURE ENGINE — Robust cursor visibility
# ═══════════════════════════════════════════════════════════════════════════

class ScreenCaptureEngine:
    """
    Background thread captures screen, compresses to JPEG,
    and broadcasts base64 frames to all WebSocket clients.

    Uses MSS (with thread-local instances) for hardware cursor capture,
    with a highly visible software cursor overlay as fallback/enhancement.
    """

    def __init__(self, fps=10, quality=60, scale=0.5):
        self.fps = fps
        self.quality = quality
        self.scale = scale
        self.frame_interval = 2.0 / fps
        self.subscribers = set()
        self._lock = threading.Lock()
        self._running = False
        self._thread = None
        self._frame_counter = 0
        self._last_frame_b64 = None
        self._pil = None
        self._loop = None
        self._mss_available = False
        self._load_backends()

    def _load_backends(self):
        """Load both PIL and MSS backends."""
        # Load PIL (always needed for compression)
        try:
            from PIL import Image, ImageDraw
            self._pil = Image
            self._draw = ImageDraw
            logger.info("[Capture] PIL loaded")
        except ImportError:
            logger.error("[Capture] PIL not available. Install: pip install Pillow")
            return

        # Load MSS (for hardware cursor capture)
        try:
            import mss
            # Test MSS works
            with mss.mss() as sct:
                mon = sct.monitors[0]
                _ = sct.grab(mon)
            self._mss_available = True
            logger.info("[Capture] MSS loaded — hardware cursor capture available")
        except Exception as exc:
            logger.warning("[Capture] MSS unavailable (%s). Cursor may not be visible on some systems.", exc)
            self._mss_available = False

    def start(self):
        if self._running or self._pil is None:
            logger.warning("[Capture] Cannot start: pil=%s running=%s", self._pil, self._running)
            return
        self._running = True
        try:
            self._loop = asyncio.get_event_loop()
        except Exception as exc:
            logger.error("[Capture] Could not get event loop: %s", exc)
            self._running = False
            return
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        logger.info("[Capture] Engine started at %d FPS", self.fps)

    def stop(self):
        logger.info("[Capture] Stopping...")
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        logger.info("[Capture] Stopped")

    def subscribe(self, ws):
        with self._lock:
            self.subscribers.add(ws)
        count = len(self.subscribers)
        logger.info("[Capture] Subscriber added. Total: %d", count)
        if self._last_frame_b64:
            try:
                asyncio.create_task(self._send_frame_to(ws, self._last_frame_b64, self._frame_counter))
            except Exception as exc:
                logger.error("[Capture] Failed to send initial frame: %s", exc)

    def unsubscribe(self, ws):
        with self._lock:
            self.subscribers.discard(ws)
        logger.debug("[Capture] Subscriber left. Total: %d", len(self.subscribers))

    def _capture_loop(self):
        logger.info("[Capture] Loop started, fps=%d, mss=%s", self.fps, self._mss_available)
        err_count = 0

        # Create thread-local MSS instance if available
        sct = None
        if self._mss_available:
            try:
                import mss
                sct = mss.mss()
            except Exception as exc:
                logger.error("[Capture] Failed to create MSS instance: %s", exc)
                sct = None

        while self._running:
            t0 = time.monotonic()
            frame_b64 = None
            try:
                if sct:
                    frame_b64 = self._capture_with_mss(sct)
                else:
                    frame_b64 = self._capture_with_pil()

                if frame_b64:
                    err_count = 0
                else:
                    err_count += 1
                    logger.warning("[Capture] Empty frame (err #%d)", err_count)
            except Exception as exc:
                err_count += 1
                logger.error("[Capture] Capture exception #%d: %s", err_count, exc)

            if err_count > 10:
                logger.error("[Capture] Too many errors, stopping")
                break

            if frame_b64:
                self._frame_counter += 1
                self._last_frame_b64 = frame_b64
                try:
                    if self._loop and self._loop.is_running():
                        asyncio.run_coroutine_threadsafe(
                            self._broadcast_frame(frame_b64, self._frame_counter),
                            self._loop
                        )
                        if self._frame_counter <= 5 or self._frame_counter % 60 == 0:
                            logger.info("[Capture] Frame #%d broadcasted", self._frame_counter)
                except Exception as exc:
                    logger.error("[Capture] Broadcast schedule error: %s", exc)

            elapsed = time.monotonic() - t0
            sleep_time = self.frame_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

        if sct:
            try:
                sct.close()
            except Exception:
                pass
        logger.info("[Capture] Loop ended. Total frames: %d", self._frame_counter)

    def _draw_cursor_overlay(self, img, x, y):
        """Draw a highly visible cursor overlay on the image."""
        try:
            draw = self._draw.Draw(img)
            w, h = img.size

            # Clamp coordinates to image bounds
            x = max(0, min(w - 1, x))
            y = max(0, min(h - 1, y))

            # Highly visible cursor: white outline + red cross + yellow center
            size = 18

            # White outline (thicker, for contrast against any background)
            outline_width = 4
            outline_color = (255, 255, 255)

            # Horizontal line with outline
            draw.line([(x - size - 2, y - outline_width//2), (x + size + 2, y - outline_width//2)], 
                     fill=outline_color, width=outline_width)
            draw.line([(x - size - 2, y + outline_width//2), (x + size + 2, y + outline_width//2)], 
                     fill=outline_color, width=outline_width)

            # Vertical line with outline
            draw.line([(x - outline_width//2, y - size - 2), (x - outline_width//2, y + size + 2)], 
                     fill=outline_color, width=outline_width)
            draw.line([(x + outline_width//2, y - size - 2), (x + outline_width//2, y + size + 2)], 
                     fill=outline_color, width=outline_width)

            # Red cross (inner)
            cross_width = 2
            cross_color = (255, 0, 0)
            draw.line([(x - size, y), (x + size, y)], fill=cross_color, width=cross_width)
            draw.line([(x, y - size), (x, y + size)], fill=cross_color, width=cross_width)

            # Yellow center dot (very visible)
            dot_radius = 5
            dot_outline = 2
            draw.ellipse([(x - dot_radius - dot_outline, y - dot_radius - dot_outline), 
                         (x + dot_radius + dot_outline, y + dot_radius + dot_outline)], 
                        fill=(255, 255, 255))
            draw.ellipse([(x - dot_radius, y - dot_radius), 
                         (x + dot_radius, y + dot_radius)], 
                        fill=(255, 255, 0))

            # Debug log cursor position occasionally
            if self._frame_counter % 60 == 0:
                logger.info("[Capture] Cursor overlay at (%d, %d) on %dx%d image", x, y, w, h)

        except Exception as exc:
            logger.error("[Capture] Cursor overlay failed: %s", exc)

    def _capture_with_mss(self, sct):
        """Capture using MSS — includes hardware cursor on most systems."""
        try:
            monitor = sct.monitors[0]  # All monitors
            screenshot = sct.grab(monitor)

            # Convert BGRA to RGB PIL Image
            img = self._pil.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

            # Always add software cursor overlay as well (in case MSS didn't capture it)
            try:
                _load_pyautogui()
                x, y = pyautogui.position()
                self._draw_cursor_overlay(img, x, y)
            except Exception:
                pass

            return self._compress_image(img)
        except Exception as exc:
            logger.error("[Capture] MSS capture failed: %s", exc)
            return None

    def _capture_with_pil(self):
        """Fallback using pyautogui screenshot — does NOT capture hardware cursor."""
        try:
            _load_pyautogui()
            img = pyautogui.screenshot()

            # Get cursor position and draw overlay (essential since pyautogui doesn't capture cursor)
            try:
                x, y = pyautogui.position()
                self._draw_cursor_overlay(img, x, y)
            except Exception as exc:
                logger.warning("[Capture] Cursor overlay failed in PIL mode: %s", exc)

            return self._compress_image(img)
        except Exception as exc:
            logger.error("[Capture] PIL/pyautogui capture failed: %s", exc)
            return None

    def _compress_image(self, img):
        if self.scale < 1.0:
            new_size = (int(img.width * self.scale), int(img.height * self.scale))
            img = img.resize(new_size, self._pil.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=self.quality, optimize=True)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("ascii")

    async def _broadcast_frame(self, frame_b64, frame_id):
        payload = {
            "type": "screen",
            "frame_id": frame_id,
            "format": "jpeg",
            "data": frame_b64,
            "timestamp": time.time(),
        }
        with self._lock:
            current_subs = list(self.subscribers)
        if not current_subs:
            return
        dead = []
        for ws in current_subs:
            if ws.closed:
                dead.append(ws)
                continue
            try:
                await ws.send_json(payload)
            except Exception as exc:
                logger.debug("[Capture] Send to client failed: %s", exc)
                dead.append(ws)
        if dead:
            with self._lock:
                for ws in dead:
                    self.subscribers.discard(ws)
        if frame_id % 60 == 0:
            logger.info("[Capture] Frame #%d sent to %d clients", frame_id, len(current_subs))

    async def _send_frame_to(self, ws, frame_b64, frame_id):
        if ws.closed:
            return
        try:
            await ws.send_json({
                "type": "screen",
                "frame_id": frame_id,
                "format": "jpeg",
                "data": frame_b64,
                "timestamp": time.time(),
            })
        except Exception:
            pass


class MouseControlServer:
    def __init__(self):
        self.screen_width, self.screen_height = _load_pyautogui().size()
        self.active_connections = set()
        # NEW: Optional screen capture engine (doesn't break anything if disabled)
        self.capture_engine = None
        if ENABLE_CAPTURE:
            self.capture_engine = ScreenCaptureEngine(
                fps=CAPTURE_FPS,
                quality=JPEG_QUALITY,
                scale=SCREEN_SCALE,
            )
            self.capture_engine.start()
        logger.info("Screen size detected: %dx%d", self.screen_width, self.screen_height)
        logger.info("Trust token file: %s", TOKEN_FILE.resolve())

    async def websocket_handler(self, request):
        peer = request.remote or "unknown"
        logger.info("Incoming WebSocket connection from %s", peer)

        ws = web.WebSocketResponse()
        await ws.prepare(request)

        try:
            msg = await ws.receive(timeout=10)
            if msg.type != web.WSMsgType.TEXT:
                await ws.close()
                return ws

            data = json.loads(msg.data)
            token = data.get("token")
            name = data.get("name", "android-client")
            # NEW: Client can opt out of screen capture
            wants_screen = data.get("screen", True)

            if not self.verify_token(token):
                logger.warning("Invalid token from %s", peer)
                await ws.send_json({"type": "error", "message": "Invalid token."})
                await ws.close()
                return ws

            logger.info("Authenticated client '%s' from %s (screen=%s)", name, peer, wants_screen)
            self.active_connections.add(ws)

            # NEW: Send screen capture feature info in handshake
            await ws.send_json({
                "type": "handshake_ack",
                "screen_width": self.screen_width,
                "screen_height": self.screen_height,
                "permissions": tokens[token]["permissions"],
                "features": {
                    "screen_capture": self.capture_engine is not None,
                    "capture_fps": CAPTURE_FPS if self.capture_engine else 0,
                },
            })

            # NEW: Subscribe to screen capture if available and client wants it
            if self.capture_engine and wants_screen:
                self.capture_engine.subscribe(ws)

            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    await self.process_command(msg.data, ws)
                elif msg.type == web.WSMsgType.ERROR:
                    logger.error("WebSocket connection error from %s: %s", peer, ws.exception())
                    break
                elif msg.type in (web.WSMsgType.CLOSE, web.WSMsgType.CLOSED, web.WSMsgType.CLOSING):
                    break

        except asyncio.TimeoutError:
            logger.warning("Handshake timeout from %s", peer)
        except Exception as exc:
            logger.exception("Unexpected error for %s: %s", peer, exc)
        finally:
            # NEW: Unsubscribe from screen capture on disconnect
            if self.capture_engine:
                self.capture_engine.unsubscribe(ws)
            self.active_connections.discard(ws)
            await ws.close()

        return ws

    @staticmethod
    def verify_token(token):
        return token in tokens

    async def process_command(self, message, websocket):
        try:
            cmd = json.loads(message)
        except json.JSONDecodeError:
            await websocket.send_json({"type": "error", "message": "Invalid JSON."})
            return

        cmd_type = cmd.get("type")
        if cmd_type == "move":
            await self.handle_move(cmd)
        elif cmd_type == "click":
            await self.handle_click(cmd)
        elif cmd_type == "double_click":
            pyautogui.doubleClick()
        elif cmd_type == "right_click":
            pyautogui.rightClick()
        elif cmd_type == "mouse_down":
            button = cmd.get("button", "left")
            pyautogui.mouseDown(button=button)
        elif cmd_type == "mouse_up":
            button = cmd.get("button", "left")
            pyautogui.mouseUp(button=button)
        elif cmd_type == "scroll":
            amount = int(cmd.get("amount", 0))
            pyautogui.scroll(amount)
        elif cmd_type == "key":
            key = cmd.get("key")
            if key:
                self._safe_key_press(key)
        elif cmd_type == "type":
            text = cmd.get("text", "")
            if text:
                try:
                    pyautogui.write(text)
                except Exception:
                    for ch in text:
                        try:
                            pyautogui.press(ch)
                        except Exception:
                            pass
        elif cmd_type == "hotkey":
            keys = cmd.get("keys", [])
            if isinstance(keys, list) and keys:
                pyautogui.hotkey(*keys)
        # NEW: Client can dynamically toggle screen stream
        elif cmd_type == "screen_toggle":
            enabled = cmd.get("enabled", True)
            if self.capture_engine:
                if enabled:
                    self.capture_engine.subscribe(websocket)
                else:
                    self.capture_engine.unsubscribe(websocket)
        elif cmd_type == "ping":
            await websocket.send_json({"type": "pong"})
        else:
            await websocket.send_json({"type": "error", "message": f"Unknown command: {cmd_type}"})

    async def handle_move(self, cmd):
        mode = cmd.get("mode", "relative")
        if mode == "absolute":
            dx = float(cmd.get("dx", 0))
            dy = float(cmd.get("dy", 0))
            x = int(dx * self.screen_width)
            y = int(dy * self.screen_height)
            pyautogui.moveTo(x, y)
        else:
            dx = int(cmd.get("dx", 0))
            dy = int(cmd.get("dy", 0))
            pyautogui.moveRel(dx, dy)

    def _safe_key_press(self, key):
        """Safely press a key, handling special characters and mapping."""
        key = str(key)
        if not key:
            return

        # Single character (letter, number, symbol) — use write for reliability
        if len(key) == 1:
            try:
                pyautogui.write(key)
                return
            except Exception:
                pass

        # Multi-character or special key — map and use press()
        key_lower = key.lower().strip()
        key_map = {
            'space': 'space',
            ' ': 'space',
            'enter': 'return',
            'return': 'return',
            'backspace': 'backspace',
            'delete': 'delete',
            'del': 'delete',
            'tab': 'tab',
            'esc': 'esc',
            'escape': 'esc',
            'up': 'up',
            'down': 'down',
            'left': 'left',
            'right': 'right',
            'pageup': 'pageup',
            'pagedown': 'pagedown',
            'home': 'home',
            'end': 'end',
            'insert': 'insert',
            'capslock': 'capslock',
            'numlock': 'numlock',
            'scrolllock': 'scrolllock',
            'printscreen': 'printscreen',
            'pause': 'pause',
            'break': 'pause',
            'playpause': 'playpause',
            'volumemute': 'volumemute',
            'volumedown': 'volumedown',
            'volumeup': 'volumeup',
            'f1': 'f1', 'f2': 'f2', 'f3': 'f3', 'f4': 'f4', 'f5': 'f5',
            'f6': 'f6', 'f7': 'f7', 'f8': 'f8', 'f9': 'f9', 'f10': 'f10',
            'f11': 'f11', 'f12': 'f12',
        }
        mapped = key_map.get(key_lower, key_lower)
        try:
            pyautogui.press(mapped)
        except Exception:
            logger.debug("Failed to press key: %s (mapped: %s)", key, mapped)

    async def handle_click(self, cmd):
        button = cmd.get("button", "left")
        clicks = int(cmd.get("clicks", 1))
        interval = float(cmd.get("interval", 0.0))
        pyautogui.click(button=button, clicks=clicks, interval=interval)


# ─── HTTP Handlers (UNCHANGED + one new endpoint) ─────────────────────────

async def serve_http(request):
    try:
        html_path = BASE_DIR / "client.html"
        text = html_path.read_text(encoding="utf-8")
        token_value = ""
        try:
            token_value = list(tokens.keys())[0]
        except Exception:
            token_value = ""

        def _replace_token(match):
            before = match.group(1)
            return f'{before} value="{token_value}"'

        new_text = re.sub(r'(\]*id\s*=\s*"tokenInput"[^>]*)value\s*=\s*"[^"]*"', _replace_token, text, flags=re.IGNORECASE)
        if new_text == text:
            new_text = re.sub(r'(\]*id\s*=\s*"tokenInput"[^>]*)(>)', lambda m: f"{m.group(1)} value=\"{token_value}\"{m.group(2)}", text, flags=re.IGNORECASE)

        return web.Response(text=new_text, content_type="text/html")
    except Exception as exc:
        logger.exception("Error serving client.html: %s", exc)
        return web.FileResponse(str(BASE_DIR / "client.html"))


async def get_token(request):
    token_value = ""
    try:
        token_value = list(tokens.keys())[0]
    except Exception:
        token_value = ""
    return web.json_response({"token": token_value})


# NEW: Screen info endpoint
async def get_screen_info(request):
    return web.json_response({
        "enabled": ENABLE_CAPTURE,
        "fps": CAPTURE_FPS,
        "quality": JPEG_QUALITY,
        "scale": SCREEN_SCALE,
        "screen_width": _load_pyautogui().size()[0],
        "screen_height": _load_pyautogui().size()[1],
    })


# ─── Main (UNCHANGED structure, just engine cleanup added) ────────────────

async def main():
    server = MouseControlServer()
    app = web.Application()
    app.router.add_get("/", serve_http)
    app.router.add_get("/api/token", get_token)
    app.router.add_get("/api/screen", get_screen_info)  # NEW
    app.router.add_get("/ws", server.websocket_handler)

    local_ips = get_local_addresses()
    logger.info("Local addresses: %s", ", ".join(local_ips) if local_ips else "localhost")
    logger.info("HTTP + WebSocket server listening on port %d", HTTP_PORT)

    web_runner = web.AppRunner(app)
    await web_runner.setup()

    bind_hosts = []

    if BIND_ADDRESS not in ("0.0.0.0", "::"):
        try:
            site = web.TCPSite(web_runner, BIND_ADDRESS, HTTP_PORT)
            await site.start()
            bind_hosts.append(BIND_ADDRESS)
            logger.info("Bound to %s on port %d", BIND_ADDRESS, HTTP_PORT)
        except OSError as exc:
            logger.error("Could not bind %s on port %d: %s", BIND_ADDRESS, HTTP_PORT, exc)
            raise RuntimeError(f"Could not bind server to {BIND_ADDRESS}:{HTTP_PORT}")
    else:
        try:
            site_v6 = web.TCPSite(web_runner, "::", HTTP_PORT)
            await site_v6.start()
            bind_hosts.append("::")
            logger.info("Bound to IPv6 :: on port %d", HTTP_PORT)
        except OSError as exc:
            logger.warning("Could not bind IPv6 :: on port %d: %s", HTTP_PORT, exc)

        try:
            site_v4 = web.TCPSite(web_runner, "0.0.0.0", HTTP_PORT)
            await site_v4.start()
            bind_hosts.append("0.0.0.0")
            logger.info("Bound to IPv4 0.0.0.0 on port %d", HTTP_PORT)
        except OSError as exc:
            logger.warning("Could not bind IPv4 0.0.0.0 on port %d: %s", HTTP_PORT, exc)

    if not bind_hosts:
        raise RuntimeError(f"Could not bind server on port {HTTP_PORT} for IPv4 or IPv6")

    token_list = list(tokens.keys())
    logger.info("Use this token from your Android device: %s", token_list[0])

    ngrok_url = os.environ.get("NGROK_URL", "") or f"http://localhost:{HTTP_PORT}"
    if local_ips:
        fallback = f"http://{local_ips[0]}:{HTTP_PORT}"
    else:
        fallback = None

    connection_base = ngrok_url or fallback
    if connection_base is None:
        connection_base = f"http://localhost:{HTTP_PORT}"

    sep = "&" if "?" in connection_base else "?"
    connection_url = f"{connection_base}{sep}token={token_list[0]}"

    generate_terminal_qr(connection_url)

    if not ngrok_url and fallback:
        logger.info("If using public IPv6, open http://[::]:%d/ on the remote device", HTTP_PORT)

    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Shutdown requested")
    finally:
        # NEW: Clean shutdown of capture engine
        if server.capture_engine:
            server.capture_engine.stop()
        await web_runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
