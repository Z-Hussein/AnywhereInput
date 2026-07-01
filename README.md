# AnywhereInput

**Control your Windows, Linux, or macOS PC from any browser.** No app install, no account, no cloud dependency.

[AnywhereInput](https://www.anywhereinput.com) is a lightweight open-source remote control tool. Run a Python server on your PC and control it from any browser — no app or account needed. It supports mouse, keyboard, scrolling, real-time screen capture, and minimal-config tunnel support with **5 providers**.

---

## Why AnywhereInput?

Every remote control tool forces you through friction:

| Tool | Friction |
|---|---|
| TeamViewer / Chrome Remote Desktop | Account creation, bloated client, corporate telemetry |
| VNC / RDP | Port forwarding, firewall rules, VPN setup |
| Dedicated apps | App store, permissions, updates |

**AnywhereInput does none of that.** Open a browser, paste a link, control your PC. The server is yours. The connection is direct. The client is the web.

---

## Quick Start

### Windows (Recommended)
```batch
scripts\windows\setup.bat
scripts\windows\run.bat
```

### Linux / macOS
```bash
chmod +x scripts/unix/setup.sh scripts/unix/run.sh
./scripts/unix/setup.sh
./scripts/unix/run.sh
```

### pip — install from PyPI (any platform)
```bash
pip install anywhereinput
anywhereinput --tunnel [cloudflare,tailscale,pinggy,zrok2,ngrok]
anywhereinput
```

### Ubuntu (recommended): pipx install from PyPI
```bash
sudo apt update
sudo apt install -y pipx
pipx ensurepath

# Open a new terminal, then install and run
pipx install anywhereinput
anywhereinput --tunnel cloudflare
```



> Package on PyPI: https://pypi.org/project/anywhereinput/

---

## Important Notes

- See docs/IMPORTANT.md for critical security, tunnel, and troubleshooting notes.
- See IMPORTANT.md in the repository root for quick operator guidance before first run.
- Client monitor selection supports all detected displays from the monitor dropdown (including Auto mode).

---

## Tunnel Providers

| Provider | Cost | Account | Setup | Notes |
|---|---|---|---|---|
| **[Cloudflare](https://www.cloudflare.com/) Tunnel** | Free | ❌ No | Auto-downloaded | Fastest globally, random URL per session |
| **Tailscale** | Free | ✅ Yes (free) | Install + log in once | Peer-to-peer via tailnet IP — both devices on same tailnet |
| **[Pinggy.io](https://pinggy.io/)** | Free | ❌ No | Uses SSH client | 60 min session timeout, works behind firewalls |
| **[Zrok2](https://docs.zrok.io/)** | Free (5 GB/day) | ✅ Yes | Manual install | Open source, zero-trust architecture |
| **[ngrok](https://ngrok.com/)** | Free tier | ✅ Yes | Download + config | Reliable, large ecosystem, session limits on free |

---

## Features at a Glance

### Control
- **Mouse** — Move, click (left/right), double-click, scroll
- **Keyboard** — Single keys, hotkey combos (Ctrl+C, Ctrl+Alt+Del, etc.)
- **Screen Capture** — Real-time JPEG stream from server to browser
- **Screen Overlay Click** — Tap anywhere on the live screen to move cursor there
- **Touchpad Gestures** — Two-finger scroll, long-press right click, tap-to-click

### Settings
- Adjustable mouse sensitivity (0.3x – 3.0x)
- FPS counter overlay
- Stream quality & scale control
- Screen capture toggle

### Performance
- ~60 Hz mouse updates
- Configurable screen stream FPS (1–30), JPEG quality (1–95), scale (0.1–1.0)
- Multi-monitor support with auto cursor tracking across monitors

---

## Architecture

```
┌─────────────────+─────────────────────────────────┐
│                 │                                 │
│  Your Device    │      Your PC                    │
│  (Any Browser)  │      (Python Server)            │
│                 │         - aiohttp HTTP/WS        │
│  Screen Stream  ├──────►|  - MSS/PIL capture       │
│  <─────────────+------►|  - pyautogui input       │
│                 │         └─────────────────────────┘
└─────────────────+─────────────────────────────────┘
                    │
                    ▼
          +─────────────────+
          │ Tunnel Provider │ (Optional, for remote)
          │ Cloudflare /    │
          │ Tailscale /     │
          │ Pinggy /        │
          │ Zrok2 / ngrok   │
          └─────────────────+
```

---

## CLI Options

| Flag | Default | Description |
|---|---|---|
| `--host HOST` | `127.0.0.1` | Server host bind address |
| `--port PORT` | `8008` | Server port |
| `--fps FPS` | `10` | Screen capture FPS (1–30) |
| `--quality Q` | `60` | JPEG quality (1–95) |
| `--scale F` | `0.5` | Screen scale factor (0.1–1.0) |
| `--no-capture` | — | Disable screen capture entirely |
| `--monitor N` | `0` | Monitor to capture (0=auto, 1+=fixed) |
| `--tunnel P` | — | Tunnel provider: `cloudflare`, `tailscale`, `pinggy`, `zrok2`, `ngrok` |

Example:
```bash
anywhereinput --fps 15 --quality 75 --scale 0.7 --tunnel cloudflare
```

---

## How It Works

1. Run the server on your PC (`run.sh` or `run.bat`)
2. Select your tunnel provider from the menu
3. Open a browser on any device (phone, tablet, laptop)
4. Paste the URL displayed in the terminal
5. Enter the access token and tap **Connect**
6. Use the touchpad to control your PC, or tap the screen stream to move the cursor

---

## Client Controls

| Action | How |
|---|---|
| Move cursor | Drag on the touchpad area |
| Left click | Tap touchpad or tap Left Click button |
| Right click | Long-press touchpad (600ms) or Right Click button |
| Double click | Double Click button |
| Scroll | Two-finger drag, or Scroll Up/Down buttons |
| Keyboard | Tap Keyboard, type text, send |
| Hotkeys | Pre-mapped: Ctrl+A through Ctrl+F, Ctrl+Alt+Del |
| Center mouse | Tap Center button |
| Screen overlay click | Tap anywhere on the live screen stream |

---

## WebSocket API

### Authentication
Connect to `/ws` and send:
```json
{"type": "auth", "token": "***"}
```

### Commands
```json
{"type": "move", "mode": "relative", "dx": 10, "dy": 15}
{"type": "move", "mode": "absolute", "dx": 0.5, "dy": 0.5}
{"type": "click", "button": "left", "clicks": 1}
{"type": "scroll", "amount": 15}
{"type": "key", "key": "enter"}
{"type": "hotkey", "keys": ["ctrl", "c"]}
{"type": "screen_toggle", "enabled": true}
{"type": "ping"}
```

### HTTP Endpoints
| Endpoint | Description |
|---|---|
| `GET /api/screen` | Returns screen dimensions |
| `GET /api/monitors` | Returns all monitor info + current selection |
| `POST /api/monitor/{index}` | Switch capture monitor |
| `GET /api/token` | Returns the current active token |

---

## Access Methods

### Local Network (same WiFi)
No tunnel needed. Just open your browser and navigate to:
```
http://<your-pc-ip>:8008
```

### Remote Access
Use any supported tunnel provider above for secure remote access from anywhere.

---

## Security

> ⚠️ Designed for personal/trusted use. Not hardened for production.

- ✅ Auto-generated 32-char token on each server start
- ✅ Token rotation via **Ctrl+N** or `n` + Enter
- ✅ HTTPS/WSS encryption when using any tunnel provider
- ✅ No data stored on external servers
- ❌ Single token per session
- ❌ No rate limiting
- ❌ No IP whitelist
- ❌ No logging/monitoring

For enterprise-grade security, add a reverse proxy with OAuth or mTLS.

---

## System Requirements

| Component | Minimum |
|---|---|
| Server OS | Windows 10/11, Linux, macOS |
| Python | 3.9+ |
| Client | Any browser with WebSocket + Pointer Events + Touch Events |
| Internet | Required on both devices for remote access |

## Dependencies

```
pyautogui>=0.9.54
aiohttp>=3.8.0
requests>=2.28.0
pyotp>=2.8.0
qrcode[pil]>=0.12.0
mss>=9.0.0
Pillow>=9.0.0
pyyaml>=6.0
click>=8.0
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Tunnel URL not showing | Check internet; verify provider status; try another provider |
| Can't connect from device | Check firewall allows port 8008; test `http://localhost:8008` on PC first |
| Connection timeout | Verify both devices have internet; check tunnel provider status |
| Mouse moving too slow / lag | Check network latency; reduce drag distance; try local network |
| Screen capture shows black cursor | Install `mss`; on Linux, ensure X11 display is accessible |
| Screen stream is blank | Check server logs; try `--no-capture`; ensure Pillow is installed |
| Keyboard double-typing | Client uses 50ms debounce; check mobile keyboard autocorrect |
| Zrok2 "not enabled" error | Run `zrok2 enable <TOKEN>` or use `zrok2_repair.py` |
| Cloudflared not found | Auto-downloads on first run; if fails, install manually: `winget install --id Cloudflare.cloudflared` (Windows) or `brew install cloudflared` (macOS) |
| Python not found | Install Python 3.9+ from [python.org](https://python.org), ensure it's on PATH |

---

## Getting Started Guide

### Cloudflare Tunnel
1. Run `run.bat` / `./run.sh` and select **Cloudflare Tunnel**
2. The launcher auto-downloads cloudflared if not found
3. Wait 10–20 seconds for the tunnel to establish
4. Copy the URL (`https://xxx.trycloudflare.com`)

### Tailscale
1. Install [Tailscale](https://tailscale.com/download) on both PC and device
2. Log in to the same account on both devices
3. Run `run.bat` / `./run.sh` and select **Tailscale**
4. Your PC displays its Tailnet IP — connect from any other tailnet device

### Pinggy.io
1. Ensure you have an SSH client installed:
   - Windows: Enable OpenSSH Client in Settings > Apps > Optional Features
   - Linux: `sudo apt-get install openssh-client`
   - macOS: Built-in
2. Run `run.bat` / `./run.sh` and select **Pinggy**
3. If prompted for a password, press ENTER (blank password)
4. Copy the URL (`https://xxx.a.free.pinggy.link`)

### Zrok2
1. Download zrok from [github.com/openziti/zrok/releases](https://github.com/openziti/zrok/releases)
2. Run `zrok invite` to create an account (one-time)
3. Run `zrok2 enable <TOKEN>` (get token from [zrok.io dashboard](https://docs.zrok.io))
4. Run `run.bat` / `./run.sh` and select **Zrok2**

### ngrok
1. Download ngrok from [ngrok.com/download](https://ngrok.com/download)
2. Sign up at [dashboard.ngrok.com/signup](https://dashboard.ngrok.com/signup)
3. Get your auth token from [your authtoken page](https://dashboard.ngrok.com/get-started/your-authtoken)
4. Run `run.bat` / `./run.sh` and select **ngrok**

---

## Roadmap

- ✅ Unified tunnel launcher (5 providers)
- ✅ Tailscale peer-to-peer support
- ✅ Auto-download cloudflared binary on all platforms
- ✅ Zrok2 environment check and auto-enable
- ✅ Pinggy SSH tunnel with URL parsing
- ✅ Terminal QR code generation
- ❌ Android/iOS companion app
- ❌ Video streaming mode
- ❌ File transfer over tunnel
- ❌ Enterprise SSO integration

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

---

## License

MIT License — See [LICENSE](LICENSE)
