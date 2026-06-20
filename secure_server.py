import asyncio
import json
import logging
import secrets
import socket
import argparse
from pathlib import Path

import pyautogui
import re
from datetime import datetime
from aiohttp import web

# Parse command-line arguments first
parser = argparse.ArgumentParser(
    description="Remote Mouse Controller Server",
    epilog="Example: python secure_mouse_server.py --port 9000 --token-file ./my_tokens.json -v"
)
parser.add_argument("--port", type=int, default=8080,
                    help="HTTP port for the server (default: 8080)")
parser.add_argument("--bind", default="0.0.0.0",
                    help="Bind address (default: 0.0.0.0, use :: for IPv6)")
parser.add_argument("--token-file", type=str, default=None,
                    help="Custom path for token file (default: ./trusted_tokens.json)")
parser.add_argument("-v", "--verbose", action="store_true",
                    help="Enable verbose (DEBUG) logging")
args = parser.parse_args()

# Configure logging based on verbosity
log_level = logging.DEBUG if args.verbose else logging.INFO
logging.basicConfig(level=log_level, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
TOKEN_FILE = Path(args.token_file) if args.token_file else BASE_DIR / "trusted_tokens.json"
HTTP_PORT = args.port
BIND_ADDRESS = args.bind
WS_PORT = 8765

logger.info("Configuration: port=%d, bind=%s, token-file=%s", HTTP_PORT, BIND_ADDRESS, TOKEN_FILE)

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0  # Disable 100ms delay between commands for faster response
pyautogui.POINT_NAMES = False  # No extra processing


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


def load_tokens():
    # Always regenerate a fresh token on server start. This ensures a
    # new token is required each time the server restarts.
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
        # Fallback: try to read existing tokens if present
        if TOKEN_FILE.exists():
            try:
                with TOKEN_FILE.open("r", encoding="utf-8") as fh:
                    return json.load(fh)
            except Exception:
                pass
        # As a last resort return an empty dict so server fails safely
        return {}


def save_tokens(tokens):
    with TOKEN_FILE.open("w", encoding="utf-8") as fh:
        json.dump(tokens, fh, indent=2)


tokens = load_tokens()


class MouseControlServer:
    def __init__(self):
        self.screen_width, self.screen_height = pyautogui.size()
        self.active_connections = set()
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

            if not self.verify_token(token):
                logger.warning("Invalid token from %s", peer)
                await ws.send_json({"type": "error", "message": "Invalid token."})
                await ws.close()
                return ws

            logger.info("Authenticated client '%s' from %s", name, peer)
            self.active_connections.add(ws)
            await ws.send_json(
                {
                    "type": "handshake_ack",
                    "screen_width": self.screen_width,
                    "screen_height": self.screen_height,
                    "permissions": tokens[token]["permissions"],
                }
            )

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
            # Press mouse button (for paint modes)
            button = cmd.get("button", "left")
            pyautogui.mouseDown(button=button)
        elif cmd_type == "mouse_up":
            # Release mouse button
            button = cmd.get("button", "left")
            pyautogui.mouseUp(button=button)
        elif cmd_type == "scroll":
            amount = int(cmd.get("amount", 0))
            pyautogui.scroll(amount)
        elif cmd_type == "key":
            key = cmd.get("key")
            if key:
                pyautogui.press(key)
        elif cmd_type == "type":
            # Type a string of text (sent from the client as live-typing)
            text = cmd.get("text", "")
            if text:
                try:
                    pyautogui.write(text)
                except Exception:
                    # If pyautogui.write fails for any character, fall back
                    # to pressing individual keys.
                    for ch in text:
                        try:
                            pyautogui.press(ch)
                        except Exception:
                            pass
        elif cmd_type == "hotkey":
            keys = cmd.get("keys", [])
            if isinstance(keys, list) and keys:
                pyautogui.hotkey(*keys)
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

    async def handle_click(self, cmd):
        button = cmd.get("button", "left")
        clicks = int(cmd.get("clicks", 1))
        interval = float(cmd.get("interval", 0.0))
        pyautogui.click(button=button, clicks=clicks, interval=interval)


async def serve_http(request):
    # Read the HTML template and inject the first trusted token so the
    # Android UI auto-fills the correct access token instead of a
    # hardcoded value.
    try:
        html_path = BASE_DIR / "android_controller.html"
        text = html_path.read_text(encoding="utf-8")
        token_value = ""
        try:
            token_value = list(tokens.keys())[0]
        except Exception:
            token_value = ""

        # Replace the value attribute of the token input if present.
        # This looks for id="tokenInput" and replaces the value attribute.
        def _replace_token(match):
            before = match.group(1)
            return f'{before} value="{token_value}"'

        new_text = re.sub(r'(<input[^>]*id\s*=\s*"tokenInput"[^>]*)value\s*=\s*"[^"]*"', _replace_token, text, flags=re.IGNORECASE)
        # If there was no value= attribute, insert one after the id attribute
        if new_text == text:
            new_text = re.sub(r'(<input[^>]*id\s*=\s*"tokenInput"[^>]*)(>)', lambda m: f"{m.group(1)} value=\"{token_value}\"{m.group(2)}", text, flags=re.IGNORECASE)

        return web.Response(text=new_text, content_type="text/html")
    except Exception as exc:
        logger.exception("Error serving android_controller.html: %s", exc)
        return web.FileResponse(str(BASE_DIR / "android_controller.html"))


async def get_token(request):
    """Return the current token as JSON."""
    token_value = ""
    try:
        token_value = list(tokens.keys())[0]
    except Exception:
        token_value = ""
    return web.json_response({"token": token_value})


async def main():
    server = MouseControlServer()
    app = web.Application()
    app.router.add_get("/", serve_http)
    app.router.add_get("/api/token", get_token)
    app.router.add_get("/ws", server.websocket_handler)

    local_ips = get_local_addresses()
    logger.info("Local addresses: %s", ", ".join(local_ips) if local_ips else "localhost")
    logger.info("HTTP + WebSocket server listening on port %d", HTTP_PORT)

    web_runner = web.AppRunner(app)
    await web_runner.setup()

    bind_hosts = []

    # If user specified a custom bind address, use only that
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
        # Default: try both IPv6 and IPv4
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
    logger.info("If using public IPv6, open http://[<PUBLIC_IPV6>]:%d/ on the remote device", HTTP_PORT)

    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Shutdown requested")
    finally:
        await web_runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
