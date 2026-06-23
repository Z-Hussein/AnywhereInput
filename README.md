# AnywhereInput

> **Control your Windows, Linux, or macOS PC from any phone, tablet, or browser. No app install, no account, no cloud dependency.**

AnywhereInput is a lightweight open-source remote control tool. Run a Python server on your PC and control it from any browser — no app or account needed. It supports mouse, keyboard, scrolling, real-time screen capture, and **zero-config tunnel support** with multiple providers.

---

## Why This Exists

Every remote control tool forces you through something:

| Tool | Friction |
|------|----------|
| **TeamViewer / Chrome Remote Desktop** | Account creation, bloated client, corporate telemetry |
| **VNC / RDP** | Port forwarding, firewall rules, VPN setup |
| **Dedicated apps** | App store, permissions, updates |

AnywhereInput does none of that. Open a browser, paste a link, control your PC. The server is yours. The connection is direct. The client is the web.

---

## Compare

| | AnywhereInput | TeamViewer | Chrome RDP | VNC |
|---|:---:|:---:|:---:|:---:|
| App install | ✅ None | ❌ Required | ❌ Required | ❌ Required |
| Account | ✅ None | ❌ Required | ❌ Google | ✅ None |
| Setup time | ~30 sec | ~5 min | ~3 min | ~10 min |
| Open source | ✅ Yes | ❌ No | ❌ No | ⚠️ Partial |
| Screen capture | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| Multiple tunnel providers | ✅ Yes | ❌ No | ❌ No | ❌ No |

---

## What It Does

| Feature | Detail |
|---------|--------|
| **Mouse** | Move, click (left/right), double-click, scroll |
| **Keyboard** | Single keys, hotkey combos (Ctrl+C, Ctrl+Alt+Del, etc.) |
| **Screen Capture** | Real-time JPEG stream from server to browser |
| **Screen Overlay Click** | Tap anywhere on the live screen to move cursor |
| **Touchpad Gestures** | Two-finger scroll, long-press right click, tap-to-click |
| **Settings** | Adjustable sensitivity, FPS counter, stream toggle |
| **Access** | Same WiFi (local IP) or anywhere (tunnel support) |
| **Security** | Token-based WebSocket auth, auto-rotated per session |
| **Client** | Any modern browser — Android, iOS, tablet, another laptop |
| **Performance** | ~60Hz mouse updates, configurable screen stream FPS |

---

## Quick Start (60 Seconds)

### Windows — Universal Launcher (Recommended)

```batch
run.bat
```

Then pick your tunnel provider from the menu:
1. **Cloudflare Tunnel** — FREE, no account, fastest globally
2. **Pinggy.io** — FREE, uses your SSH client, no install needed
3. **Zrok2** — FREE, open source, 5 GB daily
4. **ngrok** — Free tier, requires account

### Linux / macOS — Universal Launcher (Recommended)

```bash
chmod +x run.sh
./run.sh
```

Then pick your tunnel provider from the menu.

### Direct Provider Launchers

| Provider | Windows | Linux/macOS |
|----------|---------|-------------|
| **Cloudflare** | `launch_with_cloudflare.bat` | `python launch_with_tunnel.py --provider cloudflare` |
| **Pinggy** | `launch_with_pinggy.bat` | `python launch_with_tunnel.py --provider pinggy` |
| **Zrok2** | `launch_with_zrok2.bat` | `python launch_with_tunnel.py --provider zrok2` |
| **ngrok** | `start_with_ngrok.bat` | `./start_with_ngrok.sh` |

### Legacy Setup (Manual)

**Windows:**
```batch
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python launch_with_tunnel.py --provider cloudflare
```

**Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python launch_with_tunnel.py --provider cloudflare
```

### Connect from Your Device

1. Open your browser on any device
2. Paste the URL displayed in the terminal
3. Enter the access token (displayed in terminal)
4. Tap **Connect**
5. Use the touchpad to control your PC, or tap the screen stream to move the cursor

---

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
                        |  Tunnel Provider               |  (Optional, for remote)
                        |  Cloudflare / Pinggy / Zrok2   |
                        |  / ngrok                       |
                        +--------------------------------+
```

### Server (Your PC)

- **Framework**: aiohttp (async HTTP/WebSocket server)
- **Mouse Control**: pyautogui library
- **Screen Capture**: MSS (hardware cursor) + Pillow (JPEG compression, cursor overlay)
- **Authentication**: Token-based WebSocket handshake
- **Port**: 8008 (configurable)
- **Screen Stream**: Configurable FPS (1-30), JPEG quality (1-95), scale (0.1-1.0)
- **QR Display**: Terminal QR code for quick mobile scanning (`qr_display.py`) (Needs adjustment - not functional yet)

### Client (Any Browser)

- **Interface**: HTML5 + CSS3 (responsive design)
- **Communication**: WebSocket protocol
- **Input Handling**: Pointer Events API + Touch Events
- **Commands**: JSON-based command protocol
- **Screen Rendering**: Base64 JPEG frames via `<img>` element

---

## How to Use

### Touchpad Controls

| Action | How |
|--------|-----|
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
|---------|-------------|
| Screen Capture | Pause/resume the live screen stream |
| Mouse Sensitivity | Adjust touchpad sensitivity (0.3x – 3.0x) |
| Show FPS Counter | Toggle FPS overlay on screen stream |
| Tap to Click | Enable/disable tap-to-click on touchpad |
| Long Press = Right Click | Enable/disable long-press right click |

---

## Supported Commands

### Mouse Move (Relative)
```json
{"type": "move", "mode": "relative", "dx": 10, "dy": 15}
```

### Mouse Move (Absolute)
```json
{"type": "move", "mode": "absolute", "dx": 0.5, "dy": 0.5}
```

### Mouse Click
```json
{"type": "click", "button": "left", "clicks": 1}
```

### Scroll
```json
{"type": "scroll", "amount": 15}
```

### Key Press
```json
{"type": "key", "key": "enter"}
```

### Hotkey
```json
{"type": "hotkey", "keys": ["ctrl", "c"]}
```

### Screen Toggle
```json
{"type": "screen_toggle", "enabled": true}
```

### Ping (Keepalive)
```json
{"type": "ping"}
```

---

## Network Modes

### Local Network (Same WiFi)
```
http://<your-pc-ip>:8008/
```
No setup needed. Just connect to your PC's local IP address.

### Remote Access (Different Networks)

Use any of the supported tunnel providers:

| Provider | Cost | Account | Install | Notes |
|----------|------|---------|---------|-------|
| **Cloudflare Tunnel** | FREE | ❌ No | Auto-downloaded | Fastest globally, random URL per session |
| **Pinggy.io** | FREE | ❌ No | ❌ None (uses SSH) | 60 min session timeout |
| **Zrok2** | FREE | ✅ Yes (OpenZiti) | Manual | 5 GB daily, open source, zero-trust |
| **ngrok** | Free tier | ✅ Yes | Manual | Random URLs, session limits |

---

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
- HTTPS/WSS encryption when using any tunnel provider
- No data stored on external servers

### Known Limitations
- Single token per session
- No rate limiting
- No IP whitelist
- No logging and monitoring

If you need enterprise-grade security, add a reverse proxy with OAuth or mTLS.

---

## Requirements

| Component | Minimum |
|-----------|---------|
| Server OS | Windows 10/11, Linux, macOS |
| Python | 3.9, 3.10, 3.11, 3.12 |
| Client | Any browser with WebSocket + Pointer Events + Touch Events |
| Remote access | Any supported tunnel provider (see above) |
| Internet | Required on both devices for remote access |

### Python Dependencies
```
pyautogui>=0.9.54
aiohttp>=3.8.0
requests>=2.28.0
pyotp>=2.8.0
qrcode[pil]>=0.12.0
```

---

## File Structure

```
.
├── run.bat                          # Universal launcher for Windows (menu-based)
├── run.sh                           # Universal launcher for Linux/macOS (menu-based)
├── launch_with_tunnel.py            # Unified tunnel launcher (Python, all providers)
├── launch_with_cloudflare.bat       # Direct Cloudflare launcher (Windows)
├── launch_with_pinggy.bat           # Direct Pinggy launcher (Windows)
├── launch_with_zrok2.bat            # Direct Zrok2 launcher (Windows)
├── start_with_ngrok.bat             # Direct ngrok launcher (Windows)
├── start_with_ngrok.sh              # Direct ngrok launcher (Linux/macOS)
├── setup_windows.bat                # Windows setup script (venv + deps)
├── setup_linux.sh                   # Linux/macOS setup script (venv + deps)
├── launch_with_ngrok.py             # Legacy ngrok-only launcher
├── secure_server.py                 # Main WebSocket server + screen capture engine
├── client.html                      # Web UI with screen stream, touchpad, keyboard
├── qr_display.py                    # Terminal QR code generator
├── zrok2_repair.py                  # Zrok2 diagnostic & repair tool
├── requirements.txt                 # Python dependencies
├── .gitignore                       # Ignores tokens, venv, tunnel binaries
├── CHANGELOG.md                     # Version history
├── CONTRIBUTING.md                  # Contribution guidelines
├── Roadmap.md                       # Future plans
├── LICENSE                          # MIT License
└── README.md                        # This file
```

---

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
|------|---------|-------|-------------|
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

### Skip Binary Search
Set environment variables to skip auto-detection:

**Cloudflared:**
```bash
set CLOUDFLARED_PATH=C:\path\to\cloudflared.exe    # Windows
export CLOUDFLARED_PATH=/usr/local/bin/cloudflared      # Linux/macOS
```

**ngrok:**
```bash
set NGROK_PATH=C:\path\to\ngrok.exe                  # Windows
export NGROK_PATH=/usr/local/bin/ngrok                  # Linux/macOS
```

**Zrok:**
```bash
export ZROK_PATH=/usr/local/bin/zrok2                  # Linux/macOS
```

---

## Tunnel Provider Setup

### Cloudflare Tunnel (Recommended — No Account)
1. Run `run.bat` (Windows) or `./run.sh` (Linux/macOS)
2. Select **1) Cloudflare Tunnel**
3. The launcher will auto-download `cloudflared` if not found
4. Wait 10-20 seconds for the tunnel to establish
5. Copy the URL (e.g., `https://xxx.trycloudflare.com`)

### Pinggy.io (No Install — Uses SSH)
1. Ensure you have an SSH client installed
   - **Windows**: Enable OpenSSH Client in Settings > Apps > Optional Features
   - **Linux**: `sudo apt-get install openssh-client`
   - **macOS**: Built-in
2. Run `run.bat` or `./run.sh` and select **2) Pinggy**
3. If prompted for a password, just press **ENTER** (blank password)
4. Copy the URL (e.g., `https://xxx.a.free.pinggy.link`)

### Zrok2 (Open Source — Requires Account)
1. Download zrok from [github.com/openziti/zrok/releases](https://github.com/openziti/zrok/releases)
2. Run `zrok invite` to create an account (one-time)
3. Run `zrok2 enable <YOUR_TOKEN>` (get token from [zrok.io](https://zrok.io) dashboard)
4. Run `run.bat` or `./run.sh` and select **3) Zrok2**
5. If issues occur, run `zrok2_repair.py` (Windows) or `python zrok2_repair.py`

### ngrok (Requires Account)
1. Download ngrok from [ngrok.com/download](https://ngrok.com/download)
2. Sign up for free at [dashboard.ngrok.com/signup](https://dashboard.ngrok.com/signup)
3. Get your auth token from [dashboard.ngrok.com/get-started/your-authtoken](https://dashboard.ngrok.com/get-started/your-authtoken)
4. Run `run.bat` or `./run.sh` and select **4) ngrok**
5. Paste your auth token when prompted

---

## Performance

- **Local Network**: <50ms latency typical
- **Remote (tunnel)**: 100-300ms depending on provider and network
- **Mouse Update Rate**: ~60 Hz
- **Screen Stream**: Configurable 1-30 FPS, ~50-200KB per frame at 0.5x scale
- **Screen Compatibility**: Works with any resolution

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Tunnel URL not showing | Check internet connection; verify provider status; try another provider |
| Can't connect from device | Check firewall allows port 8008; test `http://localhost:8008` on the PC first; verify tunnel is active |
| Connection timeout | Verify both devices have internet; check tunnel provider status |
| Mouse moving too slow / lag | Check network latency; reduce drag distance on touchpad; try local network |
| Screen capture not showing cursor | Install `mss` (`pip install mss`); on Linux, ensure X11 display is accessible |
| Screen stream is blank | Check server logs; try `--no-capture` to verify basic connectivity; ensure `Pillow` is installed |
| Scroll feels too slow / fast | Adjust scroll values in `client.html` or use buttons |
| Keyboard input double-typing | Client uses deduplication (50ms debounce); check mobile keyboard autocorrect settings |
| Zrok2 "not enabled" error | Run `zrok2 enable <TOKEN>` or use `zrok2_repair.py` |
| Cloudflared not found | The launcher auto-downloads it; if it fails, install manually via `winget install --id Cloudflare.cloudflared` (Windows) or `brew install cloudflared` (macOS) |
| Python not found | Install Python 3.9+ from [python.org](https://python.org) and ensure it's on your PATH |

---

## Changelog

### [v1.0.0] — 2026-06-23 — Multi-Provider Tunnel Support

- **New**: Unified tunnel launcher (`launch_with_tunnel.py`) supporting 4 providers:
  - Cloudflare Tunnel (no account, auto-download)
  - Pinggy.io (SSH-based, zero install)
  - Zrok2 (open source, 5 GB daily)
  - ngrok (free tier, random URLs)
- **New**: Provider selection menu in `run.bat`, `run.sh`, and direct batch files
- **New**: Auto-download of `cloudflared` binary on Windows/Linux/macOS
- **New**: Zrok2 environment check and auto-enable (interactive)
- **New**: Pinggy SSH tunnel with auto-retry and URL parsing
- **New**: Terminal QR code generation (`qr_display.py`)
- **New**: Zrok2 diagnostic and repair tool (`zrok2_repair.py`)
- **New**: Cloudflare, Pinggy, Zrok2, and ngrok direct launch batch files
- **New**: Setup scripts for Windows and Linux/macOS

### [v1.0.0] — 2026-06-18 — Screen Capture & Touchpad Overhaul

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
- **Dependencies**: Added `mss`, `Pillow`, `qrcode[pil]`, `pyotp`

### [v1.0.0] — 2026-06-10 — First Release

- Token-based WebSocket auth
- Mouse move (relative), click, double-click, right-click, scroll
- Keyboard input, hotkey combos
- ngrok tunneling support
- Cross-platform server (Windows/Linux/macOS)
- Browser client (no app install)

---

## Limitations

- **Server:** Cross-platform (Windows, Linux, macOS)
- **Client:** Browser must support WebSocket, Pointer Events, and Touch Events
- **Performance:** Network latency affects responsiveness
- **Bandwidth:** Not suitable for high-bandwidth activities (gaming, video streaming)
- **Security:** Not hardened for production or untrusted networks
- **Screen Capture:** Single monitor only (primary); multi-monitor support planned
- **Clipboard:** No clipboard sync yet

---

## Roadmap / Contributing

- Audio streaming
- Multi-monitor screen capture support
- Custom domain support
- File transfer (drag & drop)
- Docker image for one-liner deploy
- Keyboard layout selection

PRs welcome!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add your feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

For issues, questions, or suggestions, open an issue on GitHub and check existing issues for solutions.

---

## Platform Support

- ✅ **Windows 10, 11** (server)
- ✅ **Linux** (Ubuntu, Debian, Fedora, Arch, etc.) (server)
- ✅ **macOS** (Intel & Apple Silicon) (server)
- ✅ **Android 6+** (client browser)
- ✅ **iOS / iPadOS** (client browser)
- ✅ **Any modern browser** (client)
- ✅ **Local WiFi networks**
- ✅ **Cloudflare Tunnel**
- ✅ **Pinggy.io**
- ✅ **Zrok2**
- ✅ **ngrok**

---

## License

MIT License — See [LICENSE](LICENSE) for details.

---

## Acknowledgments

Built with:

- [aiohttp](https://docs.aiohttp.org/) — Async HTTP framework
- [pyautogui](https://pyautogui.readthedocs.io/) — Mouse and keyboard automation
- [mss](https://github.com/BoboTiG/python-mss) — Multi-screen screenshot (hardware cursor capture)
- [Pillow](https://python-pillow.org/) — Image processing and JPEG compression
- [qrcode](https://github.com/lincolnloop/python-qrcode) — Terminal QR generation
- [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) — Public tunneling
- [Pinggy.io](https://pinggy.io/) — SSH-based tunneling
- [Zrok](https://zrok.io/) — Open-source zero-trust sharing
- [ngrok](https://ngrok.com/) — Public tunneling service

---

**Made with love for remote control enthusiasts**
