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
- Connection history / saved servers
- Multi-monitor support (select which screen to stream)
- Clipboard sync between devices (text first)
- File transfer via drag & drop
- Audio streaming from server to client
- Keyboard layout selection (QWERTY, AZERTY, etc.)
- Touchpad pinch-to-zoom gesture
- Dark / light theme toggle
- iOS Safari-specific optimizations
- Docker image for one-liner deployment
- Biometric auth (WebAuthn) option

---

## [2.1.0] - 2026-06-23

### Added
- Unified tunnel launcher (`launch_with_tunnel.py`) supporting four providers:
  - **Cloudflare Tunnel** (`--provider cloudflare`) — no account needed, auto-downloads `cloudflared`
  - **Pinggy** (`--provider pinggy`) — no install required, tunnels via your existing SSH client
  - **Zrok** (`--provider zrok` / `zrok2`) — self-hostable, privacy-first option
  - **ngrok** (`--provider ngrok`) — existing support now unified under the same entry point
- `launch_with_cloudflare.bat` — Windows one-click launcher for Cloudflare (no account)
- `launch_with_pinggy.bat` — Windows one-click launcher for Pinggy (uses SSH)
- `launch_with_zrok2.bat` — Windows one-click launcher for Zrok
- `run.bat` / `run.sh` — bare server start scripts (no tunnel, local network only)
- `zrok2_repair.py` — utility to remove a broken Zrok token and re-enroll with a new one
- `--provider` CLI flag on `launch_with_tunnel.py` with choices: `cloudflare`, `pinggy`, `zrok`, `zrok2`, `ngrok`
- `--auto-token` flag to skip manual token entry and use auto-generated token from server
- `--pinggy-token` flag for longer Pinggy sessions (paid tier)
- Explicit path overrides: `--cloudflared-path`, `--zrok-path`, `--ngrok-path`

### Changed
- `launch_with_tunnel.py` now the recommended entry point for remote access; individual launchers delegate to it
- All Windows `.bat` launchers auto-detect Python across common install paths on all drive letters
- All `.bat` launchers create and activate a venv automatically on first run

---

## [2.0.0] - 2026-06-21

### Added
- Real-time screen capture streaming from server to browser client via WebSocket
- Screen overlay click — tap anywhere on the live stream to move cursor to absolute position
- Two-finger scroll gesture on touchpad area
- Long-press right click (600ms hold) with haptic feedback via `navigator.vibrate()`
- Settings panel with toggles for screen capture, FPS counter, tap-to-click, long-press
- Adjustable mouse sensitivity slider (0.3x – 3.0x)
- Hardware cursor capture via MSS backend with thread-local instances
- Highly visible software cursor overlay (white outline + red cross + yellow center dot)
- Screen info API endpoint (`GET /api/screen`) returning current capture config
- Keepalive ping/pong every 10 seconds to prevent WebSocket timeout
- Screen stream watchdog — auto-reconnects stalled streams after 4 seconds
- CLI flags for screen capture: `--fps`, `--quality`, `--scale`, `--no-capture`
- Connection status bar with color coding (connecting / connected / disconnected)
- Auto-connect via URL parameters (`?token=`, `?host=`, `?port=`)
- Visual feedback on keyboard input (green flash for chars, blue for special keys)

### Changed
- Increased scroll speed: button scroll 5 → 15, touchpad scroll 3 → 12
- Rewrote keyboard input handling to a hybrid approach:
  - Primary: `beforeinput` event for virtual keyboard compatibility
  - Secondary: `keydown` for special keys and physical keyboards
  - Fallback: `input` event with 50ms deduplication debounce
- Improved error handling and logging throughout the screen capture engine
- Cursor overlay now uses thick white outline for visibility on any background

### Fixed
- Mouse cursor not visible on client screen stream
- MSS thread-safety issue — now uses thread-local instances per capture thread
- Silent cursor overlay failures now properly logged
- Screen capture backend fallback: MSS → PIL/pyautogui

### Dependencies
- Added `mss` for hardware-accelerated screen capture with cursor
- Added `Pillow` for JPEG compression and cursor overlay rendering

---

## [1.0.0] - 2026-06-18

### Added
- Initial release of AnywhereInput
- Token-based WebSocket authentication with auto-generated tokens per session
- Mouse control: move (relative + absolute), click, double-click, right-click, scroll
- Keyboard input: single keys and hotkey combinations (Ctrl+C, Ctrl+Alt+Del, etc.)
- ngrok tunneling support for remote access beyond local network
- Cross-platform server: Windows, Linux, macOS
- Browser-based client — no app install required
- Setup scripts for Windows (`.bat`) and Linux/macOS (`.sh`)
- `launch_with_ngrok.py` — Python launcher with automatic ngrok detection and setup
- QR code display in terminal for instant mobile connection (still needs adjustment)
