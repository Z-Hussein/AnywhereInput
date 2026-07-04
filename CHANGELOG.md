# Changelog

All notable changes to AnywhereInput will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


### Planned
- Admin controls (start with IP allowlist + per-client input permissions).
- Persistent client settings.
- Audio streaming


## [1.1.6] - 2026-07-04

### Fixed
- Screen-capture state callback deadlock that could block engine-status requests while transitioning states.
- Shutdown noise during Ctrl+C by draining pending asyncio tasks before loop close.
- Tunnel process cleanup now handles interrupt timing more gracefully during stop.


## [1.1.5] - 2026-07-04

### Added
- New `--help-tunnels` command for concise provider-specific guidance.
- Explicit `--tunnel local` mode for local-network operation with no tunnel.
- Engine status API endpoint: `GET /api/engine` (state, failure count, recovery timer, last error).
- Client engine-state badge in the stream header (`HEALTHY`, `DEGRADED`, `RECOVERING`, `OFFLINE`).
- Screen capture status overlay in the web client for recovery/error states (`screen_status` events).

### Changed
- `anywhereinput` with no arguments now behaves like launcher scripts:
  - Interactive provider menu in TTY terminals.
  - Automatic Cloudflare startup when running non-interactively (no TTY).
- CLI help output redesigned with a modern, multi-line usage layout and grouped sections (`Network`, `Streaming`, `Connectivity`).
- Interactive CLI flow now prints the launcher banner for parity with `run.sh` and `run.bat` UX.
- Runtime dependencies are now pinned to exact versions for reproducible installs and stronger supply-chain control.
- Removed unused runtime dependencies (`pyotp`, `click`) to reduce attack surface.
- `MouseWorker` now includes resilience controls:
  - Input-error classification (`transient`, `degraded`, `failed`)
  - Exponential backoff cooldown on repeated failures
  - Bounded command age (TTL) to drop stale queued inputs safely
- WebSocket command handling now emits engine-aware recovery errors:
  - `capture_error` while recovering/degraded
  - `capture_engine_offline` when offline
- Frontend now disables touch/input controls while engine is recovering/offline and re-enables on healthy state.
- Screen broadcast loop now emits additive `screen_status` updates during capture recovery windows without interrupting normal `screen` frame flow.
- Screen-capture state changes are now propagated to clients through a thread-safe server broadcast path.
- `GET /api/engine` now includes `screen_engine` state metadata alongside existing input-engine fields.

### Fixed
- Removed command/help mismatches by unifying documented and accepted tunnel values across parser choices, examples, and tunnel help text.
- Full pytest run no longer requires manual server startup (`tests/ws_test.py` is now self-contained).


---

## [1.1.4] - 2026-07-01

### Added
- Ubuntu-specific installation guidance using `pipx` (`apt install pipx`, `pipx install anywhereinput`) in docs.

### Changed
- Linux launcher now installs dependencies via `python -m pip` from the project virtual environment for better compatibility.
- Linux launcher now starts the server via `python -m anywhereinput.server` to avoid broken entrypoint wrapper scripts.

### Fixed
- Resolved startup failures where launcher-selected executables could trigger `ModuleNotFoundError: No module named 'anywhereinput'`.
- Improved self-repair flow when package import checks fail inside `.venv`.

---

## [1.1.3] - 2026-07-01

### Changed
- Provider-aware host handling for tunnel startup to use correct local upstream addresses.
- Automatic bind host selection for Tailscale (fallback to `0.0.0.0` when loopback would fail remote access).

### Fixed
- Tunnel startup/address mismatches caused by provider-specific host expectations (`localhost` vs `0.0.0.0`/tailnet-reachable bind).

---

## [1.1.2] - 2026-07-01

### Changed
- Token file now only stores the most recent token (prevents accumulation of old tokens)
- Automatically cleans up legacy token files with multiple entries on first load

### Fixed
- `trusted_tokens.json` bloating with every session (now single-token storage)

---

## [1.1.1] - 2026-07-01

### Added
- `--version` flag to CLI for displaying version information
- Comprehensive CLI help text with usage examples and tunnel provider descriptions
- Tunnel provider reference in help output explaining each tunnel option

### Changed
- Improved `--help` output with RawDescriptionHelpFormatter for better readability
- Enhanced CLI error messages with more context and guidance
- Better argument parser configuration with detailed help text for all flags
- CLI now displays project links (GitHub, PyPI, Docs) in help footer

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

## [1.0.0] - 2026-06-23

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

## [1.0.0] - 2026-06-21

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
