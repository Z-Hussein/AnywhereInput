<div align="center">

<!-- Animated Header -->
<img src="https://capsule-render.vercel.app/api?type=waving&color=0:667eea,100:764ba2&height=200&section=header&text=AnywhereInput&fontSize=70&fontColor=ffffff&animation=fadeIn&fontAlignY=35" alt="AnywhereInput" />

<h3 align="center">🖱️ Control Your PC From Any Browser - No Install, No Account, No headache</h3>

<p align="center">
  <a href="https://www.anywhereinput.com">🌐 Website</a> •
  <a href="docs/INSTALL.md">🚀 Quick Start</a> •
  <a href="docs/USAGE.md">⚙️ How It Works</a> •
  <a href="docs/TUNNELS.md">🔒 Tunnels</a>
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
<div align="center">

<p style="margin-top: 12px; font-size: 14px;">If this project helps you, consider supporting it:</p>
<div style="display: flex; gap: 10px; justify-content: center; align-items: center; flex-wrap: wrap; margin-top: 8px;">
  <a href="https://www.buymeacoffee.com/z.hussein" target="_blank">
    <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me a Coffee" style="border:0;height:38px;"></a>
  <a href="https://liberapay.com/z-hussein/donate" target="_blank">
    <img src="https://liberapay.com/assets/widgets/donate.svg" alt="Donate via Liberapay" style="border:0;height:38px;"></a>
  <a href='https://ko-fi.com/E6D223QDRL' target='_blank'><img height='36' style='border:0px;height:38px;' src='https://storage.ko-fi.com/cdn/kofi6.png?v=6' border='0' alt='Buy Me a Coffee at ko-fi.com' /></a>
</div>

</div>
</p>

# AnywhereInput


The host machine runs a Python server and any browser on any device becomes the input + display client. Built-in tunnel support (Cloudflare, Tailscale, Pinggy, Zrok2) handles NAT/firewall traversal without touching your router.

PyPI: https://pypi.org/project/anywhereinput/

---

## Quick Start

### pip install

```bash
pip install anywhereinput
anywhereinput --tunnel cloudflare
```

Paste the printed URL into any browser on another device. That's it - your screen shows up in the tab, fully controllable with mouse and keyboard.

### GUI (optional)

```bash
pip install anywhereinput[app]
anywhereinput --app
```

Opens a PyQt6 window for token management and server controls.

### pipx (Linux)

```bash
sudo apt install pipx && pipx ensurepath
pipx install anywhereinput
anywhereinput --tunnel cloudflare
```

### Windows / macOS

Use the scripts in `scripts/windows/` (`.bat`) or `scripts/unix/` (`.sh`). They handle dependency setup and launch.

---

## What it does

- Screen capture via `mss` + Pillow, JPEG stream at configurable FPS up to 120
- Mouse + keyboard input forwarded from browser WebSocket back to the host OS via pyautogui
- Tunnel providers: Cloudflare, Tailscale, Pinggy, Zrok2 - spawns the binary and negotiates the tunnel automatically
- Local-only mode for LAN use (no internet required)
- Multi-monitor support (`--monitor N`)
- Per-launch 32-char auth tokens, IP allow/block lists, per-token permissions
- Audit logging (JSONL), rate limiting, structured log rotation

---

## Install

```bash
pip install anywhereinput            # core server + client UI
pip install anywhereinput[app]       # + optional PyQt6 admin app
```

System requirements: Python 3.9+, any OS with a display server (Wayland/X11 on Linux, regular desktop on Windows/macOS). Client side just needs a browser that supports WebSocket + Pointer Events (basically anything modern).

Runtime deps: pyautogui, aiohttp, requests, Pillow, mss, pyyaml. Optional for GUI: PyQt6.

---

## Usage

```bash
anywhereinput --tunnel local          # same network, no tunnel
anywhereinput --tunnel cloudflare     # auto Cloudflare tunnel (no account needed)
anywhereinput --tunnel tailscale      # Tailscale peer-to-peer
anywhereinput --tunnel pinggy         # SSH-based tunnel
anywhereinput --tunnel zrok2          # Zrok2 open-source tunnel

# CLI flags override config file values:
anywhereinput --fps 60 --quality 70 --scale 0.8 --tunnel cloudflare
```

Tunnel selection prompts interactively if you just run `anywhereinput` with no flags (in a terminal). Runs non-interactively as Cloudflare tunnel if there's no TTY.

### Config files

Config loads from YAML at startup. CLI flags take priority.

```bash
anywhereinput config init      # create defaults
anywhereinput config edit      # open in $EDITOR
```

User overrides go in `config/local_settings.yaml` (gitignored). Project defaults are in `config/settings.yaml`.

See [docs/USAGE.md](docs/USAGE.md) for the full config guide.

---

## CLI Reference

| Flag | Default | Description |
|------|---------|-------------|
| `--host HOST` | 127.0.0.1 | Bind address |
| `--port PORT` | 8008 | Server port |
| `--fps FPS` | 120 | Capture FPS (1-120) |
| `--quality Q` | 40 | JPEG quality (1-95). Lower = faster encode, blurrier image |
| `--scale F` | 0.7 | Scale factor for capture (0.1-1.0) |
| `--low-bandwidth` | - | Mobile preset: 15fps, q60, half scale |
| `--no-capture` | - | Disable screen capture |
| `--monitor N` | 0 | Monitor index (0=auto) |
| `--tunnel P` | interactive | Provider: cloudflare, tailscale, pinggy, zrok2, local |
| `-v / --verbose` | - | DEBUG logging (`-vv` for extra) |
| `--quiet` | - | Console silent, write to file only |
| `--log-level L` | INFO | Log level |
| `--version` | - | Show version |

---

## Security

- Auto-generated 32-char token per launch (fresh every restart)
- Per-token permissions: move, click, scroll, keyboard, screen_toggle, ping
- IP allowlist + block list (CIDR or single-host), per token and global
- Kick connected clients + add to block list
- Rate limiting on WebSocket auth, API endpoints, and token creation
- Audit trail in JSONL log for all security events
- HTTPS/WSS via tunnel providers
- No external data storage

For enterprise needs (OAuth, mTLS, SSO), put it behind a reverse proxy like Caddy or Nginx.

---

## How It Works

```
Browser (any device) <==WebSocket==> Python server (your PC)
                                    ├── aiohttp HTTP + WS server
                                    ├── mss/PIL screen capture
                                    └── pyautogui input forwarding
                              [optional tunnel]
                              Cloudflare / Tailscale / Pinggy / Zrok2
```

1. Pick a tunnel (or use local)
2. Run the server on your PC
3. Open the URL in any browser
4. Enter the token → connect
5. Control your PC

---

## WebSocket API

### Auth
```json
{"type": "auth", "token": "***"}
```

### Input commands
```json
{"type": "move", "mode": "relative", "dx": 10, "dy": 15}
{"type": "move", "mode": "absolute", "dx": 0.5, "dy": 0.5}
{"type": "click", "button": "left", "clicks": 1}
{"type": "scroll", "amount": 15}
{"type": "key", "key": "enter"}
{"type": "hotkey", "keys": ["ctrl", "c"]}
{"type": "screen_toggle", "enabled": true}
```

### Server events (to client)
```json
{"type": "screen", "data": "<base64-jpeg>"}
{"type": "screen_status", "status": "rebuilding", "message": "Reconnecting..."}
{"error": "capture_error", "message": "Input engine recovering.", "recovering": true}
```

### HTTP Endpoints (all require auth token)

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Uptime, client count, screen state |
| `GET /api/screen` | Screen dimensions |
| `GET /api/engine` | Input engine health + live FPS/bandwidth metrics |
| `GET /api/monitors` | All monitors + current selection |
| `POST /api/monitor/{index}` | Switch capture monitor |
| `GET /api/tokens` | List tokens (masked) |
| `POST /api/tokens` | Create token with permissions |
| `PATCH /api/tokens/{token}` | Update token |
| `DELETE /api/tokens/{token}` | Revoke token |
| `GET /api/clients` | Connected clients |
| `POST /api/clients/{id}/kick` | Kick client + block IP |

---

## Testing

```bash
pip install -e ".[dev]"
python -m pytest tests/ -v

# Individual suites:
python -m pytest tests/test_config_loader.py -v
python -m pytest tests/test_auth.py -v
python -m pytest tests/ws_test.py -v
```

Code quality checks: `black --check src/`, `flake8 src/`, `mypy src/anywhereinput`.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Config not loading | Check YAML syntax |
| Port in use | Use `--port` or check with `lsof -i :8008` |
| Tunnel URL not showing | Check internet connection; try a different provider |
| Can't connect from device | Check firewall (port 8008); test localhost first |
| Mouse lag | Reduce quality/scale, try LAN instead of tunnel |
| Black screen | Install `mss`; ensure display server is available on Linux |
| Blank stream | Check server logs; try `--no-capture` to isolate the issue |
| Keyboard double-typing | Check autocorrect in the browser; 50ms debounce is active |
| Cloudflare binary missing | Auto-downloads on first run, or install manually |
| Zrok2 "not enabled" | Run `zrok2 enable <TOKEN>` or use `zrok2_repair.py` |

---

## Roadmap

### Done in 1.3.1
- Rate limiting (per-IP: WebSocket auth, API, token creation)
- Audit logging (JSONL rotating log)
- Capture mode presets + custom modes in admin app
- Structured logging with rotating file handler
- `--low-bandwidth` flag
- Adaptive streaming (per-client backpressure, auto-FPS)
- Global IP blocking via TokenManager
- 328 tests covering the above
- Zero-trust token startup (clears all tokens on start)
- Kick action separated from global IP block
- Tombstone token rejection for revoked tokens

### Planned
- File transfer over tunnel
- Audio stream
- Docker support for headless deployment
- Enterprise SSO integration

---

## Compared to other tools

This solves a different problem than most remote desktop apps.

AnywhereInput wins when you need:
- Browser-only client (no install on the controlling device)
- No accounts or signup walls
- Access from behind strict NAT/firewall without port config
- Quick access ("poke at my desktop for 5 minutes")
- Works on phones, tablets, public computers

Other tools are better when you need:
- Lower latency / optimized video codecs (Sunshine/Moonlight/Parsec)
- Full remote desktop workflows with file transfer and session recording (TeamViewer, RustDesk)
- Audio forwarding (all of the above except AnywhereInput currently)
- Long sessions across multiple monitors at native quality

TL;DR: it's not a replacement for RDP or TeamViewer. It's the tool you reach for when those are too heavy for what you need.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

MIT - see [LICENSE](LICENSE)
