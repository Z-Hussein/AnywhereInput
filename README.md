# AnywhereInput

AnywhereInput is a lightweight open-source remote control tool for Windows, Linux, and macOS. Run a Python server on your PC and control it from any browser — no app or account needed. It supports mouse, keyboard, scrolling, and real-time screen capture.

> Control your Windows, Linux, or macOS PC from any phone, tablet, or browser. No app install, no account, no cloud dependency.

## Why This Exists

Every remote control tool forces you through something:

| Tool | Friction |
|------|----------|
| **TeamViewer / Chrome Remote Desktop** | Account creation, bloated client, corporate telemetry |
| **VNC / RDP** | Port forwarding, firewall rules, VPN setup |
| **Dedicated apps** | App store, permissions, updates |

AnywhereInput does none of that. Open a browser, paste a link, control your PC. The server is yours. The connection is direct. The client is the web.

## Compare

| | AnywhereInput | TeamViewer | Chrome RDP | VNC |
|---|---|---|---|---|
| App install | ✅ None | ❌ Required | ❌ Required | ❌ Required |
| Account | ✅ None | ❌ Required | ❌ Google | ✅ None |
| Setup time | ~30 sec | ~5 min | ~3 min | ~10 min |
| Open source | ✅ Yes | ❌ No | ❌ No | ⚠️ Partial |
| Screen capture | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |

## What It Does

| Feature | Detail |
|---|---|
| **Mouse** | Move, click (left/right), double-click, scroll |
| **Keyboard** | Single keys, hotkey combos (Ctrl+C, Ctrl+Alt+Del, etc.) |
| **Screen Capture** | Real-time JPEG stream from server to browser |
| **Screen Overlay Click** | Tap anywhere on the live screen to move cursor |
| **Touchpad Gestures** | Two-finger scroll, long-press right click, tap-to-click |
| **Settings** | Adjustable sensitivity, FPS counter, stream toggle |
| **Access** | Same WiFi (local IP) or anywhere (ngrok tunnel) |
| **Security** | Token-based WebSocket auth, auto-rotated per session |
| **Client** | Any modern browser — Android, iOS, tablet, another laptop |
| **Performance** | ~60Hz mouse updates, configurable screen stream FPS |

## Quick Start (60 Seconds)

### Windows

```batch
start_with_ngrok.bat
```

Copy the URL. Open it on your phone. Done.

The script will:
- Auto-find Python on your system (or create a virtual environment)
- Install dependencies automatically
- Search for ngrok across your system
- Guide you through ngrok setup (first time only)
- Generate a secure access token
- Start the server and display the public URL

### Linux / macOS

```bash
chmod +x setup_linux.sh start_with_ngrok.sh
./start_with_ngrok.sh
```

Copy the URL. Open it on your phone. Done.

The script will:
- Auto-detect your Linux distribution (Ubuntu, Fedora, Arch, macOS, etc.)
- Install Python and venv if needed
- Create and activate virtual environment
- Install dependencies automatically
- Search for ngrok on your system
- Start the server and display the public URL

### Manual Setup

**Windows:**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python launch_with_ngrok.py
```

**Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python launch_with_ngrok.py
```

### Connect from Your Device

1. Open your browser on any device
2. Paste the URL displayed in the terminal
3. Enter the access token (displayed in terminal)
4. Tap **Connect**
5. Use the touchpad to control your PC, or tap the screen stream to move the cursor

## How It Works

```
+--------------------------------+      WebSocket      +--------------------------------+
|  Your Device                   | <-----------------> |  Your PC                       |
|  (Any Browser)                 |    (Token Auth)     |  (Python Server)               |
|                                |                     |  - aiohttp HTTP/WebSocket      |
|  Screen Stream (JPEG) <--------+                     |  - pyautogui mouse/keyboard    |
|  Touchpad / Keyboard --------->+                     |  - MSS/PIL screen capture      |
+--------------------------------+                     +--------------------------------+
                                |
                                v
                        +--------------------------------+
                        |  ngrok Tunnel                  |  (Optional, for remote)
                        |  (HTTPS/WSS)                   |
                        +--------------------------------+
```

### Server (Your PC)

- **Framework**: aiohttp (async HTTP/WebSocket server)
- **Mouse Control**: pyautogui library
- **Screen Capture**: MSS (hardware cursor) + Pillow (JPEG compression, cursor overlay)
- **Authentication**: Token-based WebSocket handshake
- **Port**: 8008 (configurable)
- **Screen Stream**: Configurable FPS (1-30), JPEG quality (1-95), scale (0.1-1.0)

### Client (Any Browser)

- **Interface**: HTML5 + CSS3 (responsive design)
- **Communication**: WebSocket protocol
- **Input Handling**: Pointer Events API + Touch Events
- **Commands**: JSON-based command protocol
- **Screen Rendering**: Base64 JPEG frames via `<img>` element

## How to Use

### Touchpad Controls

| Action | How |
|---|---|
| Move cursor | Drag on the touchpad area |
| Left click | Tap touchpad or tap Left Click button |
| Right click | Tap Right Click button, or long-press on touchpad (600ms) |
| Double click | Tap Double Click button |
| Scroll | Two-finger drag on touchpad, or Scroll Up/Down buttons |
| Keyboard | Tap Keyboard, type, send |
| Hotkeys | Pre-mapped: Ctrl+A, Ctrl+C, Ctrl+V, Ctrl+Z, Ctrl+X, Ctrl+S, Ctrl+F, Ctrl+Alt+Del |
| Center mouse | Tap Center button |
| Screen overlay click | Tap anywhere on the live screen stream to move cursor there |

### Buttons

- **Left Click** — Single left mouse click
- **Right Click** — Single right mouse click
- **Double Click** — Double-click action
- **Scroll Up/Down** — Scroll on the PC
- **Center** — Move mouse to center of screen
- **Keyboard** — Send individual key presses
- **Settings** — Toggle screen capture, FPS counter, tap-to-click, long-press, sensitivity

### Settings Panel

| Setting | Description |
|---|---|
| Screen Capture | Pause/resume the live screen stream |
| Mouse Sensitivity | Adjust touchpad sensitivity (0.3x – 3.0x) |
| Show FPS Counter | Toggle FPS overlay on screen stream |
| Tap to Click | Enable/disable tap-to-click on touchpad |
| Long Press = Right Click | Enable/disable long-press right click |

## Supported Commands

### Mouse Move (Relative)
```json
{
  "type": "move",
  "mode": "relative",
  "dx": 10,
  "dy": 15
}
```

### Mouse Move (Absolute)
```json
{
  "type": "move",
  "mode": "absolute",
  "dx": 0.5,
  "dy": 0.5
}
```

### Mouse Click
```json
{
  "type": "click",
  "button": "left",
  "clicks": 1
}
```

### Scroll
```json
{
  "type": "scroll",
  "amount": 15
}
```

### Key Press
```json
{
  "type": "key",
  "key": "enter"
}
```

### Hotkey
```json
{
  "type": "hotkey",
  "keys": ["ctrl", "c"]
}
```

### Screen Toggle
```json
{
  "type": "screen_toggle",
  "enabled": true
}
```

### Ping (Keepalive)
```json
{
  "type": "ping"
}
```

## Network Modes

### Local Network (Same WiFi)
```
http://<your-pc-ip>:8008/
```
No setup needed. Just connect to your PC's local IP address.

### Remote Access (Different Networks)
```
https://abc123def456.ngrok.io/
```
Requires a free ngrok account. Run `python launch_with_ngrok.py`.

## Security

> ⚠️ **Designed for personal/trusted use. Not hardened for production.**

### Token Generation

- A new access token is **auto-generated** on each server start
- Token is saved to `trusted_tokens.json` (auto-ignored by `.gitignore`)
- Never commit tokens to version control

### Token Rotation

While the app is running, press **Ctrl+N** (or type `n` + Enter) to:
- Restart the server
- Generate a new token
- Display the new token in the console

This is useful if you suspect token compromise.

### What You Get

- Auto-generated token on every server start
- Token rotation via Ctrl+N (or `n` + Enter)
- HTTPS/WSS encryption when using ngrok
- No data stored on external servers

### Known Limitations

- Single token per session
- No rate limiting
- No IP whitelist
- No logging and monitoring

If you need enterprise-grade security, add a reverse proxy with OAuth or mTLS.

## Requirements

| Component | Minimum |
|---|---|
| Server OS | Windows 10/11, Linux, macOS |
| Python | 3.9, 3.10, 3.11, 3.12 |
| Client | Any browser with WebSocket + Pointer Events + Touch Events |
| Remote access | Free ngrok account |
| Internet | Required on both devices for remote access |

## File Structure

```
.
├── start_with_ngrok.bat        # Easy launcher for Windows (recommended!)
├── start_with_ngrok.sh         # Easy launcher for Linux/macOS (recommended!)
├── setup_windows.bat           # Windows setup script
├── setup_linux.sh              # Linux/macOS setup script
├── launch_with_ngrok.py        # Python launcher script for ngrok
├── secure_server.py            # Main WebSocket server + screen capture engine
├── client.html                 # Web UI with screen stream, touchpad, keyboard
├── requirements.txt            # Python dependencies (pinned versions)
├── .gitignore                  # Ignores tokens & virtual env
├── LICENSE                     # MIT License
└── README.md                   # This file
```

## Configuration

### Change Server Port

Edit the `HTTP_PORT` variable in `secure_server.py`:
```python
HTTP_PORT = 8008  # Change this to your desired port
```

Or use the CLI flag:
```bash
python secure_server.py --port 9000
```

### Screen Capture Settings
```bash
python secure_server.py --fps 15 --quality 75 --scale 0.7
```

| Flag | Default | Range | Description |
|---|---|---|---|
| `--fps` | 10 | 1-30 | Screen capture frames per second |
| `--quality` | 60 | 1-95 | JPEG compression quality |
| `--scale` | 0.5 | 0.1-1.0 | Screen resize factor (lower = smaller file, faster) |
| `--no-capture` | false | — | Disable screen capture entirely |

### Add More Tokens

Edit `trusted_tokens.json` to add additional access tokens:
```json
{
  "token_generated_and_filled_automatically_with_each_start": {
    "name": "phone-1",
    "created": "auto-generated",
    "permissions": ["move", "click", "scroll", "keyboard"]
  },
  "your_new_token_here": {
    "name": "phone-2",
    "created": "2026-06-18",
    "permissions": ["move", "click", "scroll", "keyboard"]
  }
}
```

### Skip ngrok Search

Set `NGROK_PATH` to skip the ngrok search:

**Windows:**
```batch
set NGROK_PATH=C:\\path\\to\\ngrok.exe
start_with_ngrok.bat
```

**Linux / macOS:**
```bash
export NGROK_PATH=/usr/local/bin/ngrok
./start_with_ngrok.sh
```

## Performance

- **Local Network**: <50ms latency typical
- **Remote (ngrok)**: 100-200ms depending on network
- **Mouse Update Rate**: ~60 Hz
- **Screen Stream**: Configurable 1-30 FPS, ~50-200KB per frame at 0.5x scale
- **Screen Compatibility**: Works with any resolution

## Troubleshooting

| Problem | Fix |
|---|---|
| ngrok URL not showing | Verify auth token at dashboard.ngrok.com — paste without `$` prefix |
| Can't connect from device | Check firewall allows port 8008; test `http://localhost:8008` on the PC first; verify ngrok tunnel is active for remote access |
| Connection timeout | Verify both devices have internet; check ngrok account status; verify ngrok auth token hasn't expired |
| Mouse moving too slow / lag | Check your network latency; reduce the distance of drag movements on touchpad; try connecting to a closer server or local network |
| Screen capture not showing cursor | Install `mss` (`pip install mss`); on Linux, ensure X11 display is accessible; check server logs for `[Capture] Cursor overlay at (...)` messages |
| Screen stream is blank | Check server logs for capture errors; try `--no-capture` to disable and verify basic connectivity first; ensure `Pillow` is installed |
| Scroll feels too slow / fast | Adjust scroll values in `client.html` or use the Scroll Up/Down buttons instead of touchpad |
| Keyboard input double-typing | The client uses deduplication (50ms debounce); if issues persist, check your mobile keyboard settings for autocorrect/prediction |

## Changelog

### v2.0.0 — Screen Capture & Touchpad Overhaul
- **New**: Real-time screen capture streaming from server to browser
- **New**: Screen overlay click — tap anywhere on the stream to move cursor
- **New**: Two-finger scroll on touchpad
- **New**: Long-press right click (600ms) with haptic feedback
- **New**: Settings panel — toggle screen capture, FPS counter, tap-to-click, long-press, sensitivity slider
- **New**: Adjustable mouse sensitivity (0.3x – 3.0x)
- **New**: Hardware cursor capture via MSS backend
- **New**: Highly visible software cursor overlay (white outline + red cross + yellow dot)
- **New**: Screen info API (`GET /api/screen`)
- **New**: Keepalive ping/pong to prevent WebSocket timeout
- **New**: Screen stream watchdog — auto-reconnects stalled streams
- **New**: CLI flags for screen capture (`--fps`, `--quality`, `--scale`, `--no-capture`)
- **Improved**: Hybrid keyboard input (beforeinput + keydown + input with deduplication)
- **Improved**: Visual feedback on keyboard input (border flash)
- **Improved**: Connection status bar with color coding
- **Improved**: Scroll speed increased (buttons: 5→15, touchpad: 3→12)
- **Dependencies**: Added `mss`, `Pillow`

### v1.0.0 — Initial Release
- Token-based WebSocket auth
- Mouse move (relative), click, double-click, right-click, scroll
- Keyboard input, hotkey combos
- ngrok tunneling support
- Cross-platform server (Windows/Linux/macOS)
- Browser client (no app install)

## Limitations

- **Server:** Cross-platform (Windows, Linux, macOS)
- **Client:** Browser must support WebSocket, Pointer Events, and Touch Events
- **Performance:** Network latency affects responsiveness
- **ngrok:** Free tier has bandwidth limitations
- **Bandwidth:** Not suitable for high-bandwidth activities (gaming, video streaming)
- **Security:** Not hardened for production or untrusted networks
- **Screen Capture:** Single monitor only (primary); multi-monitor support planned
- **Clipboard:** No clipboard sync yet

## Roadmap / Contributing

- Multi-monitor screen capture support
- Clipboard sync (copy/paste between devices)
- File transfer (drag & drop)
- iOS Safari optimization
- Docker image for one-liner deploy
- Custom domain support (replace ngrok)
- Audio streaming
- Keyboard layout selection

PRs welcome!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add your feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

For issues, questions, or suggestions, open an issue on GitHub and check existing issues for solutions.

## Platform Support

- ✅ **Windows 10, 11** (server)
- ✅ **Linux** (Ubuntu, Debian, Fedora, Arch, etc.) (server)
- ✅ **macOS** (Intel & Apple Silicon) (server)
- ✅ **Android 6+** (client browser)
- ✅ **iOS / iPadOS** (client browser)
- ✅ **Any modern browser** (client)
- ✅ **Local WiFi networks**
- ✅ **ngrok remote tunneling**

## License

MIT License — See [LICENSE](LICENSE) for details.

## Acknowledgments

Built with:

- [aiohttp](https://docs.aiohttp.org/) — Async HTTP framework
- [pyautogui](https://pyautogui.readthedocs.io/) — Mouse and keyboard automation
- [mss](https://python-mss.readthedocs.io/) — Multi-screen screenshot (hardware cursor capture)
- [Pillow](https://python-pillow.org/) — Image processing and JPEG compression
- [ngrok](https://ngrok.com/) — Public tunneling service

---

**Made with love for remote control enthusiasts**
