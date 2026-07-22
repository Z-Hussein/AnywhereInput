<div align="center">

<!-- Animated Header -->
<img src="https://capsule-render.vercel.app/api?type=waving&color=0:667eea,100:764ba2&height=200&section=header&text=AnywhereInput&fontSize=70&fontColor=ffffff&animation=fadeIn&fontAlignY=35" alt="AnywhereInput" />

<h3 align="center">🖱️ Control Your PC From Any Browser - No Install, No Account</h3>

<p align="center">
  <a href="https://www.anywhereinput.com">🌐 Website</a> •
  <a href="#-quick-start">🚀 Quick Start</a> •
  <a href="#-Features-at-a-Glance">✨ Features</a> •
  <a href="#-How-It-Works">⚙️ How It Works</a> •
  <a href="#-tunnel-providers">🔒 Tunnels</a>
</p>

<!-- Badges -->
<p align="center">
  <a href="https://pypi.org/project/anywhereinput/">
    <img src="https://img.shields.io/pypi/v/anywhereinput?style=for-the-badge&logo=pypi&logoColor=white&color=blue" alt="PyPI Version" />
  </a>
  <a href="https://pypi.org/project/anywhereinput/">
    <img src="https://img.shields.io/pypi/pyversions/anywhereinput?style=for-the-badge&logo=python&logoColor=white&color=3776AB" alt="Python Versions" />
  </a>
  <a href="https://github.com/z-hussein/anywhereinput/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge&logo=open-source-initiative&logoColor=white" alt="License: MIT" />
  </a>
  <a href="#">
    <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-4B0082?style=for-the-badge&logo=windows-terminal&logoColor=white" alt="Platforms" />
  </a>
  <a href="#">
    <img src="https://img.shields.io/badge/Stars-%E2%AD%90%20Star%20Us-yellow?style=for-the-badge&logo=github&logoColor=white" alt="Star Us" />
  </a>
</p>

<!-- Animated Typing -->
<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&size=22&duration=3000&pause=1000&color=667EEA&center=true&vCenter=true&width=600&lines=Mouse+%E2%86%92+Browser;Keyboard+%E2%86%92+Browser;Screen+%E2%86%92+Browser;Your+PC+%E2%86%92+Anywhere" alt="Typing SVG" />

</div>

---

## 🎯 The Problem

Every remote control tool forces you through **friction**:

| Tool | What's Wrong |
|------|-------------|
| TeamViewer / Chrome Remote Desktop | 😤 Account creation, bloated client, corporate telemetry |
| VNC / RDP | 🔧 Port forwarding, firewall rules, VPN setup |
| Dedicated Apps | 📱 App store, permissions, updates, storage |

**AnywhereInput does none of that.**

Open a browser → paste a link → control your PC. That's it.

> *"The server is yours. The connection is direct. The client is the web."*

---

## 🚀 Quick Start

### ⚡ One-Liner (Recommended)
```bash
pip install anywhereinput
anywhereinput --tunnel cloudflare
```

### 🪟 Windows
```batch
scripts\windows\setup.bat
scripts\windows\run.bat
```

### 🐧 Linux / 🍎 macOS
```bash
chmod +x scripts/unix/setup.sh scripts/unix/run.sh
./scripts/unix/setup.sh
./scripts/unix/run.sh
```

### 🖥️ Desktop GUI (No Terminal Needed)
```bash
pip install anywhereinput[app]
anywhereinput --app
```

> 💡 **Ubuntu?** Use `pipx` for isolated installs: `pipx install anywhereinput`

---

## ✨ Features at a Glance

<div align="center">

| 🖱️ **Control** | 📺 **Stream** | 🔒 **Security** | ⚡ **Performance** |
|---|---|---|---|
| Move, click, scroll | Real-time JPEG screen | Per-token permissions | Up to 120 Hz updates |
| Keyboard & hotkeys | Multi-monitor support | IP allowlists/blocklists | Configurable FPS |
| Touchpad gestures | Screen overlay click | Auto-rotating tokens | JPEG quality control |
| Two-finger scroll | Live recovery status | HTTPS/WSS encryption | Bandwidth scaling |
| **Tap-to-click on stream** | | **Kick + block clients** | **IP block/deny lists** |

</div>

### 🎮 Client Controls

| Action | How |
|--------|-----|
| **Move cursor** | Drag on touchpad area |
| **Left click** | Tap touchpad or Left Click button |
| **Right click** | Long-press touchpad (600ms) or Right Click button |
| **Double click** | Double Click button |
| **Scroll** | Two-finger drag, or Scroll Up/Down buttons |
| **Keyboard** | Tap Keyboard → type → send |
| **Hotkeys** | Ctrl+A–F, Ctrl+Alt+Del, and more |
| **Screen click** | Tap anywhere on the live screen stream |

### Fullscreen (Watch Mode) Controls

In fullscreen mode the touchpad is hidden and the entire screen image acts as the touchpad. Swipe moves the cursor - behaves exactly like a plugged mouse.

| Action | How |
|--------|-----|
| **Move cursor** | Swipe anywhere on the stream |
| **Left click** | Tap the stream |
| **Right click** | Long-press (600ms) on the stream |
| **Scroll** | Two-finger drag on the stream |
| **Keyboard** | ⌨️ button always visible in bottom-right |

### Touch / Mobile Controls (Screen Stream)

The live screen stream supports touch gestures for mobile/tablet clients:

| Gesture | Action |
|---------|--------|
| **Single tap** | Move mouse to tap position |
| **Double tap** (same spot, <500ms) | Left-click at that position |
| **Drag** | Move mouse (relative) |
| **Long press** (600ms) | Right-click |
| **Two-finger drag** | Scroll |
| **Two-finger pinch** | Scroll (alternative) |

---

## 🔒 Tunnel Providers

Choose your path. No vendor lock-in.

| Provider | Cost | Account | Setup | Best For |
|----------|------|---------|-------|----------|
| **[Cloudflare](https://www.cloudflare.com/)** | 🆓 Free | ❌ No | Auto-download | 🌍 Global access, random URL/session |
| **[Tailscale](https://tailscale.com/)** | 🆓 Free | ✅ Yes (free) | Install once | 🏠 Peer-to-peer, same tailnet |
| **[Pinggy.io](https://pinggy.io/)** | 🆓 Free | ❌ No | SSH client | 🔥 Works behind strict firewalls |
| **[Zrok2](https://docs.zrok.io/)** | 🆓 Free (5GB/day) | ✅ Yes | Manual install | 🛡️ Open source, zero-trust |
| **Local only** | 🆓 Free | ❌ No | None | 📡 Same WiFi/LAN |

---

## ⚙️ How It Works

```
┌─────────────────┐      ┌─────────────────────────────┐
│  Your Device    │      │      Your PC                │
│  (Any Browser)  │◄────►│  Python Server              │
│                 │  WS  │  ├─ aiohttp HTTP/WebSocket  │
│  Screen Stream  │◄────►│  ├─ MSS/PIL capture         │
│  <──────────────┘      │  └─ pyautogui input         │
└─────────────────┘      └─────────────────────────────┘
           │
           ▼
  ┌─────────────────────────────────────────────┐
  │ Tunnel Provider  ← Optional                 │
  │  (Cloudflare / Tailscale / Pinggy / Zrok2)  │
  └─────────────────────────────────────────────┘
```

1. **Run** the server on your PC
2. **Select** tunnel provider (or stay local)
3. **Open** browser on any device
4. **Paste** the URL
5. **Enter** access token → **Connect**
6. **Control** your PC from anywhere

---

## 📡 WebSocket API

### Authentication
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
```

### Server Events
```json
{"type": "screen", "data": "<base64-jpeg>"}
{"type": "screen_status", "status": "rebuilding", "message": "Reconnecting..."}
{"error": "capture_error", "message": "Input engine recovering.", "recovering": true}
```

### HTTP Endpoints
| Endpoint | Description |
|----------|-------------|
| `GET /api/screen` | Screen dimensions |
| `GET /api/engine` | Input engine health |
| `GET /api/monitors` | All monitors + current selection |
| `POST /api/monitor/{index}` | Switch capture monitor |
| `GET /api/tokens` | List tokens (masked) |
| `POST /api/tokens` | Create token with permissions |
| `PATCH /api/tokens/{token}` | Update token |
| `DELETE /api/tokens/{token}` | Revoke token |
| `GET /api/clients` | Connected WebSocket clients |
| `POST /api/clients/{client_id}/kick` | Kick client + add IP to block list |

---

## 🛠️ CLI Options

```bash
anywhereinput [OPTIONS]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--host HOST` | `127.0.0.1` | Server bind address |
| `--port PORT` | `8008` | Server port |
| `--fps FPS` | `120` | Screen capture FPS (1–120) |
| `--quality Q` | `40` | JPEG quality (1–95). Lower = faster encode/decode but blurrier. Default 40 is optimal for remote control. |
| `--scale F` | `0.7` | Scale factor for capture (0.1–1.0). Lower = smaller image = much less data to transmit. 0.5 = half resolution. |
| `--no-capture` | - | Disable screen capture |
| `--monitor N` | `0` | Monitor (0=auto, 1+=fixed) |
| `--tunnel P` | interactive | Provider: `cloudflare`, `tailscale`, `pinggy`, `zrok2`, `local` |
| `--help-tunnels` | - | Show tunnel help |
| `--version` | - | Show version |

**Example:**
```bash
anywhereinput --fps 120 --quality 40 --scale 0.7 --tunnel cloudflare
```

---

## 🛡️ Security

> ⚠️ **Designed for personal/trusted use. Not hardened for production.**

- ✅ **Auto-generated** 32-char token on each start
- ✅ **Per-token** input permissions (`move`, `click`, `scroll`, `keyboard`, `screen_toggle`, `ping`)
- ✅ **IP allowlist** per token (CIDR + single-host)
- ✅ **IP block/deny list** - global + per-token (CIDR + single-host)
- ✅ **Kick + block clients** from admin UI - disconnects client and adds their IP to token's block list
- ✅ **Blocked IPs management** - view and unblock kicked IPs per token in the admin app token editor
- ✅ **Token rotation** via `n` + Enter or Ctrl+N
- ✅ **HTTPS/WSS** encryption via tunnel providers
- ✅ **Zero external data storage**
- ⚠️ Single active token per session - rotation invalidates all previous
- ❌ No rate limiting (add reverse proxy for production)
- ❌ No audit logging

For enterprise-grade security, add a reverse proxy with **OAuth** or **mTLS**.

---

## 📦 System Requirements

| Component | Minimum |
|-----------|---------|
| **Server OS** | Windows 10/11, Linux, macOS |
| **Python** | 3.9+ |
| **Client** | Any browser with WebSocket + Pointer/Touch Events |
| **Internet** | Required on both devices for remote access |

### Dependencies
```toml
pyautogui==0.9.54
aiohttp==3.14.1
requests==2.34.2
qrcode[pil]==8.2
mss==10.2.0
Pillow==12.3.0
pyyaml==6.0.3
PyQt6==6.11.0
```

---

## 🧰 Troubleshooting

| Problem | Fix |
|---------|-----|
| Tunnel URL not showing | Check internet; try another provider |
| Can't connect from device | Check firewall (port 8008); test `localhost:8008` first |
| Connection timeout | Verify both devices online; check tunnel status |
| Mouse lag | Reduce drag distance; try local network |
| Black cursor on capture | Install `mss`; ensure X11 accessible on Linux |
| Blank screen stream | Check server logs; try `--no-capture`; verify Pillow |
| Keyboard double-typing | 50ms debounce active; check autocorrect |
| Zrok2 "not enabled" | Run `zrok2 enable <TOKEN>` or use `zrok2_repair.py` |
| Cloudflared missing | Auto-downloads on first run; or install manually |
| Python not found | Install 3.9+ from [python.org](https://python.org) |

---

## 🗺️ Roadmap

### ✅ Completed (v1.2.7)
- [x] Blocked IPs management in admin app - view/unblock kicked clients per token
- [x] Auto token cleanup on shutdown - fresh session every start
- [x] IPv6 address extraction fix for block list matching
- [x] Duplicate `/api/clients` route removed (was returning WebSocket repr)
- [x] Unified tunnel launcher (4 providers)
- [x] Tailscale peer-to-peer support
- [x] Auto-download cloudflared
- [x] Zrok2 environment check & auto-enable
- [x] Pinggy SSH tunnel with URL parsing
- [x] Terminal QR code generation
- [x] Desktop admin app (`--app`) with token management
- [x] Per-token input permissions & IP allowlists
- [x] Connection Request flow (client approval)
- [x] Direct-mouse cursor tracking in both normal and fullscreen modes
- [x] Always-visible keyboard button in fullscreen mode
- [x] Multi-token session support (with permissions settings)

### 🚧 Coming Soon
- [ ] File transfer over tunnel
- [ ] Enterprise SSO integration

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

---

## 📄 License

**MIT License** - See [LICENSE](LICENSE)

---

<div align="center">

<!-- Footer Banner -->
<img src="https://capsule-render.vercel.app/api?type=waving&color=0:764ba2,100:667eea&height=100&section=footer&fontSize=20&fontColor=ffffff&animation=fadeIn" alt="Footer" />

<p align="center">
  <sub>Built with ❤️ for developers who value simplicity over complexity.</sub>
</p>

<p align="center">
  <a href="https://www.anywhereinput.com">🌐 Website</a> •
  <a href="https://pypi.org/project/anywhereinput/">📦 PyPI</a> •
  <a href="https://github.com/Z-Hussein/anywhereinput">⭐ Star on GitHub</a>
</p>

</div>
