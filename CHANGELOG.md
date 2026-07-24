# Changelog

Format is loosely based on Keep a Changelog. Sections: Added, Changed, Fixed, Removed, Dependencies.

---

## [1.3.0] - 2026-07-20

### Added
- Rate limiting: per-IP limits on WebSocket auth (10/s), API (30/s), token creation (5/10s). Localhost excluded for admin app.
- Audit logging: JSONL rotating log (`logs/audit.log`) for all security events
- Capture mode presets in admin app: Balanced, Quality, Performance, Low Bandwidth + custom save/delete
- Structured logging with rotating file handler (10MB x 5 files)
- `--low-bandwidth` flag (mobile preset: 15fps, q60, half scale)
- Adaptive streaming: per-client backpressure, auto-FPS adjustment
- Real-time FPS and bandwidth metrics via `/api/engine`
- Global IP blocking endpoint (`POST /api/blocked-ips`)
- 6 new test files, 328 total tests

### Changed
- Default FPS: 120 → 60
- Default quality: 40 → 70
- Default scale: 0.7 → 0.8
- Split `AuditLogger.log` into `audit_log` (security events) + `log` (debug/info)

### Fixed
- Missing imports in tunnel_manager.py, screen_capture/utils.py, screen_capture/base.py
- Admin app logging references (`_main_window.py`, `_token_handlers.py`, `_request_handlers.py`)
- `host_header` UnboundLocalError in server_ws.py
- Wrong entry point path for `anywhereinput-server`
- Tombstone tokens (revoked) bypassing auth validation - now rejected explicitly
- Kick action incorrectly adding client IP to global block list - fixed, kick only revokes the specific token
- Dashboard FPS/bandwidth showing "-" - added moving-average FPS and per-client bandwidth tracking
- Duplicate `self._blocked_ips` on server core - removed stale set attribute
- Global WS connect IP check was redundant with TokenManager.blocked_ips

### Removed
- pyyaml from runtime deps (was listed but never imported)
- PyQt6 moved to optional `[app]` extra

---

## [1.2.7] - 2026-07-16

### Fixed
- Cloudflare binary not found: was saved as `cloudflared-linux-amd64` but code expected `cloudflared`. Renamed on download.
- Cloudflare binary location stored in pipx package dir - moved to platform data directory (`~/.local/share/anywhereinput/`)
- Kick using WebSocket repr instead of proper client ID. Duplicate `/api/clients` route removed.
- IPv6 addresses truncated in IP block list. Now parses both v4 and v6 correctly.
- Connection request always showed `127.0.0.1` for tunneled clients - now uses proper IP extraction from X-Forwarded-For.
- Admin app icon was generic gear - now uses favicon.ico.

---

## [1.2.6] - 2026-07-15

### Added
- Complete IP access control: global block list, per-token allow/block lists with CIDR support
- Blocked IPs management in admin app token editor
- Mobile touch support: tap-to-move, double-tap-to-click, long-press right-click, two-finger scroll
- Admin client dialog: table view of connected clients

### Changed
- FPS: 30 → 120, quality: 95 → 40, scale: 1.0 → 0.7
- JPEG encoding: non-progressive, no optimize pass for faster encode/decode
- Precise frame timing with remainder compensation instead of fixed sleep

### Fixed
- IP allowlist wasn't enforced at WebSocket connect - now checked at auth time
- "Frame delayed" logs spamming (throttled to once per 10 min when >150% target interval)
- Black screen in headless mode - test-pattern fallback added

---

## [1.2.5] - 2026-07-XX

### Added
- Direct-delta mouse (no EMA smoothing, instant response)
- Watch-mode keyboard button always visible in fullscreen
- CSS hardening for watch mode (pointer-events/touch-action)
- Connection request flow: guests can request access, admin approves from desktop app
- Auto-connect from URL (`?token=abc123`)
- Toggle between "request access" and "connect directly" forms

### Fixed
- Screen capture state tearing down/rebuilding every frame - fixed cross-thread verified flag
- Dead WebSockets lingering - added 30s heartbeat + async cleanup
- Tailscale IP detection - now parses `tailscale status --json` directly
- Admin app crash on decline (indentation bug)
- Approve button firing 4× - replaced with explicit QPushButton wiring
- Mouse lag from EMA smoothing at 0.95 (~150ms) → removed

### Removed
- ngrok tunnel provider (four remaining + local cover all use cases)

---

## [1.2.4] - 2026-07-07

### Fixed
- Queue age check killing keyboard input in MouseWorker loop
- Tailscale tunnel always reporting failure - added NO_PROCESS sentinel
- WebSocket double-auth race condition - authSent flag prevents duplicates
- admin_app.py wrong project root path
- Legacy token file format crash on validate() - normalizes non-dict values
- Cloudflare partial file on download failure - atomic write via .tmp
- Token rotation busy-loop in non-TTY mode - added isatty guard
- Separate move+click WebSocket frames → merged into single compound message
- safe_print fallback wrong signature
- Class-level mutable DEFAULT_PERMISSIONS → immutable tuple + classmethod

### Fixed (continued)
- QR code crash on all platforms - replaced broken print_ascii() with StringIO approach
- **Added:** `screen_recovery.py` - self-healing screen capture monitor:
  - Monitors frame health, forces engine teardown/rebuild after failures
  - Guards against infinite stuck states, monitors monitor list staleness
  - Uses call_soon_threadsafe for thread-safe scheduling

### Fixed (continued)
- MouseWorker smoothing 0.95 → 0.0 (eliminated ~150ms input lag)
- Server-side batching too aggressive - reduced from 20 items to 3 per tick, interval from 8ms to 1ms
- Stream frame interval delay - captures immediately instead of sleeping 1/fps between frames
- Broadcast no longer blocks on slow clients → fire-and-forget async sends
- Client mouse moves sent instantly on every pointermove (was buffered)
- JPEG encoding: LANCZOS → NEAREST, disabled optimize pass, enabled progressive for client decode

---

## [1.2.3] - 2026-07-07

### Fixed
- QR code not displaying on Windows OEM codepages - now renders to StringIO first
- Screen capture validation failing with DPI scaling >100% on Windows - uses GetDeviceCaps instead of incorrect ctypes call, removed invalid logical/physical pixel comparison

---

## [1.2.2] - 2026-07-07

### Fixed
- Screen capture engine validation failure on Windows DPI >100% - added `_get_windows_dpi_scale()` for physical→logical conversion
- UnicodeEncodeError on Windows legacy consoles - introduced `safe_print()`/`safe_print_stderr()` with errors='replace' fallback, replaced 70+ print calls across all modules
- Launcher banner box-drawing chars breaking on OEM codepages → clean `===` bordered text

---

## [1.2.1] - 2026-07-07

### Fixed
- Admin app crashes when PyQt6 missing - Qt-dependent classes moved inside `if QT_AVAILABLE:` guard with stubs in else branch

### Added
- Server-side input permission enforcement (was only validated at connect, now per-message)
- Desktop admin app (`anywhereinput --app`) via PyQt6: server lifecycle, tunnel selection, token management, client monitoring
- IP allowlist management with CIDR support
- `[app]` optional dependency group

### Fixed (continued)
- Screen capture silently stopping - fixed thread-affinity tracking for `_sct` handle
- HEALTHY/REBUILDING infinite loop on Linux - ensure `_sct` is nulled in cleanup
- No startup validation for screen capture → added 3-attempt init verification
- Broadcast exceptions silently swallowed → now sets engine state to DEGRADED, sends persistent status notifications
- WebSocket auth failures silent → sends error message before closing
- Malformed JSON handled silently → catches parse errors, replies with message
- Cloudflare tunnel origin validation returning 403 - moved checks before Host header comparison
- Admin app capture settings ignored → forwards all params to CLI subprocess
- Static file serving corrupted binary assets → text as UTF-8, binary as raw bytes
- Token save failures silently lost tokens → added IOError handling

---

## [1.1.6] - 2026-07-04

### Fixed
- Screen-capture state callback deadlock blocking engine-status requests during state transitions
- Shutdown noise on Ctrl+C - drain pending asyncio tasks before loop close
- Tunnel process cleanup handles interrupt timing better during stop

---

## [1.1.5] - 2026-07-04

### Added
- `--help-tunnels` command, explicit `--tunnel local` mode
- Engine status API (`GET /api/engine`)
- Client engine-state badge in stream header (HEALTHY, DEGRADED, RECOVERING, OFFLINE)
- Screen capture status overlay for recovery/error states

### Changed
- `anywhereinput` with no args now behaves like launcher scripts (interactive provider menu in TTY, automatic Cloudflare when non-TTY)
- MouseWorker: input-error classification, exponential backoff, bounded command TTL
- Frontend disables touch/input while engine recovering/offline
- Runtime deps pinned to exact versions

### Fixed
- Command/help mismatches across tunnel providers unified
- `ws_test.py` is now self-contained (no manual server startup needed)

---

## [1.1.4] - 2026-07-01

### Added
- Ubuntu pipx installation guidance

### Changed
- Linux launcher uses `python -m pip` from venv for compatibility
- Linux launcher starts via `python -m anywhereinput.server` instead of broken entrypoint scripts

### Fixed
- Startup failures from launcher-selected executibles triggering ModuleNotFoundError
- Improved self-repair flow when package import checks fail

---

## [1.1.3] - 2026-07-01

### Fixed
- Tunnel startup/address mismatches (localhost vs 0.0.0.0) - provider-aware host handling added

---

## [1.1.2] - 2026-07-01

### Changed
- Single-token storage in `trusted_tokens.json` (no accumulation)
- Auto-purge multi-entry token files on first load

### Fixed
- Token file bloating every session

---

## [1.1.1] - 2026-07-01

### Added
- `--version` flag
- Redesigned `--help` with usage examples, tunnel descriptions, project links

---

## [1.0.0] - 2026-06-28

### Added
- Unified tunnel launcher (Cloudflare, Tailscale, Pinggy, Zrok2)
- Multi-monitor support (`--monitor N`)
- Screen info and token APIs
- Centralized YAML config
- Windows `.bat` launchers per provider
- Linux `run.sh` auto-setup
- ARM architecture detection for Cloudflare binary

### Fixed
- Cloudflare binary path resolution
- Zrok2 URL capture (blocking → non-blocking)
- Ngrok domain matching (`.ngrok-free.dev`)
- Pinggy SSH host (`free.pinggy.io`)
- RuntimeWarning from eager imports in `__init__.py`

---

## [0.4.0] - 2026-06-23

### Added
- Unified tunnel launcher with Cloudflare auto-download, Pinggy via SSH, Zrok2 repair tool
- Path overrides for custom installs
- Windows one-click launchers per provider

---

## [0.3.0] - 2026-06-21

### Added
- Real-time JPEG screen capture + stream
- Screen overlay click (tap-to-move)
- Two-finger scroll, long-press right-click
- Hardware cursor capture + overlay
- Keepalive ping, stream watchdog
- Auto-connect via URL parameters
- Visual feedback on keyboard input

---

## [0.2.0] - 2026-06-18

Initial release: token auth, mouse/keyboard forwarding, ngrok tunneling, cross-platform server, browser client, setup scripts, QR code terminal display.
