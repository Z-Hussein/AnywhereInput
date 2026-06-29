# Changelog

All notable changes to AnywhereInput will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- HTTPS on local network (self-signed cert or local CA)
- WebSocket reconnection with exponential backoff
- Input validation and rate limiting on WebSocket commands
- Encrypted token storage (not plaintext JSON)
- Graceful capture engine recovery on crash
- Persistent client settings (localStorage)
- Clipboard sync between devices (text first)
- File transfer via drag & drop
- Keyboard layout selection (QWERTY, AZERTY, etc.)
- Dark / light theme toggle
- iOS Safari-specific optimizations
- Docker image for one-liner deployment

---

## [1.0.0] - 2026-06-28

### Added
- **5 tunnel providers**: Cloudflare, Tailscale, Pinggy, Zrok2, ngrok (was 4)
- **Tailscale P2P support** — peer-to-peer via tailnet IP, no public URL needed
- `launch_tailscale.bat` — Windows direct launcher for Tailscale
- Modular tunnel infrastructure (`tunnel_manager.py`) with abstract provider base class
- Linux `run.sh` enhanced: auto-setup on first run, tunnel process cleanup before launch
- Unicode art banner in Linux launcher with version display
- TTY detection in `run.sh` — auto-launches Cloudflare if no terminal
- Multi-monitor support (`--monitor N`) with auto cursor tracking across monitors
- Screen info API endpoint (`GET /api/screen`, `GET /api/monitors`, `POST /api/monitor/{index}`)
- Token API endpoint (`GET /api/token`)
- Direct launcher batch files for all 5 tunnel providers in Windows
- Centralized YAML config (`config/settings.yaml`) with server, capture, auth, and tunnel defaults

### Changed
- Unified entry point: `anywhereinput` CLI command via `pyproject.toml` entry points
- Split monolithic server into focused modules: `server.py`, `auth.py`, `screen_capture.py`, `tunnel_manager.py`, `client.py`, `qr_display.py`, `zrok2_repair.py`
- Replaced eager package imports in `__init__.py` to eliminate `RuntimeWarning` on `python -m` execution
- Cloudflare tunnel: ARM architecture detection, absolute path resolution for binary downloads
- Pinggy tunnel: updated SSH endpoint from `qr@a.pinggy.io` to `free.pinggy.io -T` per official docs; URL regex updated for `.run.pinggy-free.link` and `.free.pinggy.net` domains
- Zrok2 tunnel: fixed URL extraction using non-blocking I/O with `select()` + `fcntl`, JSON log parsing with raw newline handling
- Ngrok tunnel: updated domain matcher from `.ngrok-free.app` to `.ngrok-free.dev` (ngrok v3)
- Tailscale availability check via `tailscale status --json` with multiple API field fallbacks
- Linux launcher uses `anywhereinput` CLI command instead of `python -m`
- Provider menu: availability indicators (✓/?) shown next to each provider, auto-checks installed status
- Kill orphaned tunnel processes before starting new ones (cloudflared, zrok2, ngrok)

### Fixed
- Cloudflare binary path resolution — downloads now saved to project root with correct architecture filename and absolute path
- Zrok2 URL capture — was failing because of blocking pipe reads; switched to non-blocking `select()` + raw byte parsing
- Ngrok domain matching — `.ngrok-free.dev` wasn't matched by the old `.ngrok-free.app` regex
- Pinggy SSH host — `qr@a.pinggy.io` didn't work; corrected to official endpoint `free.pinggy.io`
- RuntimeWarning: `'anywhereinput.server' found in sys.modules` — removed eager imports from package `__init__.py
