<div align="center">

<img src="https://capsule-render.vercel.app/api?type=soft&color=0:10b981,100:059669&height=120&section=header&text=Changelog&fontSize=50&fontColor=ffffff&animation=fadeIn" alt="Changelog" />

<h3>What's new, what's fixed, and why it matters</h3>

<p>
  <a href="#-latest">🚀 Latest</a> •
  <a href="#-all-releases">📦 All Releases</a> •
  <a href="#-versioning">🏷️ Versioning</a>
</p>

</div>

---

## 🚀 [1.3.0] — 2026-07-20

> **The "Security & Reliability" Release** — Rate limiting, audit logging, capture mode presets, adaptive streaming, and 43 crash bugs fixed.

### ✨ What's New

| Feature | Why You'll Love It |
|---------|-------------------|
| **Rate Limiting** | Per-IP limits on WebSocket auth (10/s), API (30/s), and token creation (5/10s). Localhost excluded for admin app. |
| **Audit Logging** | JSON-lines rotating log (`logs/audit.log`) for all security events: token created/revoked/rotated, client connected/disconnected/kicked, IP blocked/unblocked, connection requested/approved/declined. |
| **Capture Mode Presets** | Admin app Screen Capture group now has a Mode dropdown: Balanced (60fps/q70), Quality (60fps/q90), Performance (30fps/q55), Low Bandwidth (15fps/q60). Auto-detects matching mode when spinners change. |
| **Custom Capture Modes** | Save your own profiles with Save/Delete buttons. Stored in `capture_modes.json`. |
| **Structured Logging** | Rotating file handler (10MB × 5 files) + console handler. `-v` for DEBUG, `--quiet` for file-only. |
| **`--low-bandwidth` Flag** | Mobile data preset: 15fps, 60% quality, half scale. Adaptive streaming auto-adjusts further. |
| **Adaptive Streaming** | Per-client backpressure (skip frames for slow clients), auto-reduce FPS when frames delayed, slow recovery. |
| **Real-Time FPS & Bandwidth Metrics** | Engine status API (`/api/engine`) now returns live FPS estimate (moving average over last 5s) and bandwidth consumption (bytes/sec sent to clients). Admin dashboard top bar displays both values. |
| **Global IP Blocking via TokenManager** | Dedicated `POST /api/blocked-ips` endpoint adds IPs to `TokenManager.blocked_ips`, blocking all connections from that IP regardless of token. Separate from per-token allow/block lists. |
| **328 Tests** | 6 new test files covering capture modes, rate limiter, logging config, screen capture utils, token handlers, request handlers, CLI arg parsing. Zero failures. |

### 🔒 Security

| Feature | Why It Matters |
|---------|---------------|
| **Rate Limiting** | Prevents brute-force token auth and API abuse from external IPs |
| **Audit Trail** | Full accountability log for all security-relevant actions |
| **Zero-Trust Tokens** | All tokens cleared on server start — fresh session every restart |
| **Stale Token Cleanup** | Client-side URL token comparison, localStorage clear on auth error |
| **Kick vs. Block IP Separation** | Kick action now revokes only the specific client's token (creates tombstone with empty permissions), NOT global IP block. Dedicated global IP block via `TokenManager.blocked_ips` prevents kicking one client from blocking others on the same local network |
| **Tombstone Token Rejection** | Revoked tokens stored as tombstones with empty `permissions` lists; `validate()` explicitly rejects any token lacking permissions, preventing reuse of revoked tokens |

### 🐛 Fixed

| Bug | The Fix |
|-----|---------|
| **`requests` not imported** in `tunnel_manager.py` | `import requests` with fallback to `None` |
| **`_fcntl` undefined** in `tunnel_manager.py` | `import fcntl` with fallback to `None` |
| **`Optional`/`logging` not imported** in `screen_capture/utils.py` | Added both imports |
| **`io` not imported** in `screen_capture/base.py` | Added `import io` |
| **`CaptureEngineState` not imported** in `screen_capture/backends/windows.py` | Added to import from `models` |
| **`log` undefined** in `admin/_approval_dialog.py` | Added module-level logger |
| **`.admin_app` wrong module** in `launcher.py` | Changed to `.admin` |
| **Bare `log` instead of `self.log`** in `admin/_main_window.py:684,735` | Changed to `self.log` |
| **`log.debug()` on `AuditLogger`** in `_token_handlers.py` and `_request_handlers.py` | Split into `audit_log` (audit events) + `log` (debug/info messages) |
| **`host_header` UnboundLocalError** in `server_ws.py` | Moved definition before `if origin:` block |
| **Dead `_conc_limiter.add_connection()`** reference | Removed (class was deleted) |
| **`anywhereinput-server` entry point** wrong module path | Fixed `anywhereinput.server_core:main` → `anywhereinput.server.server_core:main` |
| **Client stale token reuse** | URL token comparison discards stale localStorage tokens; auth error clears localStorage |
| **Admin app rate limit 429** | Localhost IPs excluded from rate limiter |
| **Revoked token bypassed auth** | Tombstone tokens (empty `permissions`) were accepted by `validate()`. Added explicit permission check: `if not token_data.get("permissions"): return False` |
| **Kick action blocked global IP** | Kick added client IP to server-level `_blocked_ips`, blocking all clients from that IP. Fixed: kick now only revokes the specific token; global IP block requires dedicated endpoint |
| **Unblock IP button raised QMetaObject error** | `_refresh_blocked` missing `@pyqtSlot()` decorator caused silent dispatch failure when called from background thread via `QMetaObject.invokeMethod()`. Added decorator + return value check in `_unblock_ip` |
| **Global IP check on WS connect removed** | Redundant `blocked_ips` check removed from `server_ws.py`; connection blocking now handled entirely by token validation and `TokenManager.blocked_ips` |
| **Dashboard FPS/bandwidth always showed "-"** | `/api/engine` returned no FPS or bandwidth fields; capturer tracked frame counts but not real-time FPS, server tracked no bandwidth. Added FPS moving-average to `CaptureStats`, per-client bandwidth tracking in broadcast loop, exposed both on `/api/engine`, fixed dashboard to read new field paths |
| **Duplicate `self._blocked_ips` on server core** | Removed stale set attribute from `server_core.py` — global IP blocking now handled exclusively via `TokenManager.blocked_ips` |

### 📦 Dependencies

| Change | Why |
|--------|-----|
| **pyyaml removed** | Was listed in pyproject.toml but never imported anywhere |
| **PyQt6 optional** | Moved to `[project.optional-dependencies] app` — not needed for headless server |
| **Python 3.13/3.14** | Added to classifiers (tested and confirmed working) |

### ⚡ Performance

| Setting | Before | After | Why |
|---------|--------|-------|-----|
| Default FPS | 120 | **60** | Better balance of smoothness vs CPU/battery |
| Default Quality | 40 | **70** | Crisper image with minimal latency increase |
| Default Scale | 0.7 | **0.8** | Better readability on mobile devices |
| Adaptive streaming | None | **Per-client backpressure** | Slow clients don't block fast ones |

---

## 🚀 [1.2.7] — 2026-07-16

> **The "Polish & Reliability" Release** — Cloudflare tunnel fixes, kick improvements, blocked IP management, and UI polish.

### ✨ What's New

| Feature | Why You'll Love It |
|---------|-------------------|
| **🚫 Blocked IPs Management** | View and unblock kicked IPs directly from the token editor in the admin app. Each token shows a "Blocked IPs (kicked clients)" table with Unblock buttons. |
| **🖱️ Kick + Auto-Block IP** | Admin kick button now properly extracts real client IP (handles IPv4/IPv6) and adds it to the token's block list — client can't reconnect with same token from that IP. |
| **🔄 Auto Token Cleanup** | Tokens are cleared from `trusted_tokens.json` on server shutdown — fresh start every session. |
| **🖥️ Admin App Icon** | Desktop admin app (`--app`) now uses favicon.ico for taskbar/dock icon. |

### 🔧 Changed

| Area | Before | After | Why |
|------|--------|-------|-----|
| **Cloudflare binary** | Downloaded to package dir (broken in pipx) | Downloaded to platform data dir (`~/.local/share/anywhereinput/`) | Works with pipx installs |
| **Client toggle** | "Request a new connection?" link non-functional | Properly toggles between request form and connect form | Users can switch between flows |
| **Error handling** | `print()` to console | `safe_print()` + `QMessageBox` dialogs | Users see errors, logs are clean |

### 🐛 Fixed

| Bug | The Fix |
|-----|---------|
| **Cloudflare binary not found** | Binary was saved as `cloudflared-linux-amd64` but code expected `cloudflared` — now renamed on download. |
| **Cloudflare binary location** | Stored in pipx package dir (not found at runtime) | Moved to persistent user data directory per platform. |
| **Kick not working** | Client ID was WebSocket repr (`<WebSocketResponse ...>`) | Duplicate `/api/clients` route removed; proper client ID from metadata used. |
| **Kick IP not blocked** | IPv6 addresses truncated to first hextet (`2003`) | Proper IPv4/IPv6 parsing for block list. |
| **Connection request IP** | Always showed `127.0.0.1` for tunneled clients | Now uses `_get_client_ip()` which handles X-Forwarded-For headers. |
| **Duplicate `/api/clients` route** | First route returned WebSocket repr as client ID | Removed duplicate from server_core.py; token_handlers version is correct. |
| **Admin app icon** | Generic gear icon in taskbar/dock | Now uses branded favicon.ico. |
| **ngrok references** | Scattered in docs/comments | Fully removed — only 4 providers remain. |

### 🗑️ Removed

- Debug logging from launcher (`[DEBUG]` prefix removed from production output).

---

## 🚀 [1.2.6] - 2026-07-15

> **The "Stream & Secure" Release** - 120 FPS streaming, complete IP access control, mobile touch support, and blocked IPs management.

### ✨ What's New

| Feature | Why You'll Love It |
|---------|-------------------|
| **🔐 Complete IP Access Control** | Global block list, per-token allow/block lists (CIDR + exact IPs). Admin kick button disconnects client AND adds their IP to the token's block list. |
| **🚫 Blocked IPs Management** | View and unblock kicked IPs directly from the token editor in the admin app. Each token shows a "Blocked IPs (kicked clients)" table with Unblock buttons. |
| **👆 Mobile Touch Support** | Tap-to-move, double-tap-to-click, drag-to-move, long-press right-click, two-finger scroll - the screen stream works like a native touchscreen. |
| **👥 Admin Client Dialog** | Table view of connected clients (IP, Token, Kick button). Open from Clients tab → "Manage Clients". |
| **⚡ Stream Performance** | 120 FPS target, quality 40, scale 0.7. JPEG encoding optimized (non-progressive, subsampling=1, no optimize pass). Precise frame timing with remainder compensation. Binary WebSocket frames. |
| **🖥️ Headless Fallback** | Test pattern frames when no display available - perfect for CI/testing. |
| **🧹 Auto Token Cleanup** | Tokens are cleared from `trusted_tokens.json` on server shutdown - fresh start every session. |

### 🔧 Changed

| Setting | Before | After | Why |
|---------|--------|-------|-----|
| **FPS** | 30 | **120** | 4× smoother streaming |
| **Quality** | 95 | **40** | Faster encode/decode, lower latency |
| **Scale** | 1.0 | **0.7** | 51% less bandwidth, minimal quality loss |
| **JPEG encoding** | Progressive, optimize=True | **Non-progressive, no optimize** | Faster encode/decode |
| **Frame timing** | Fixed sleep | **Precise with remainder comp.** | Stable 120 FPS |
| **IP validation** | Stub | **Full CIDR + exact match** | Security that actually works |

### 🐛 Fixed

| Bug | The Fix |
|-----|---------|
| **IP allowlist not enforced** | Was stored but never validated at WebSocket connect. Now checked at auth time. |
| **Stream spam logs** | "Frame delayed" logs throttled to once per 10 min (only when >150% of target interval). |
| **Black screen in headless** | Test-pattern fallback when MSS fails. |
| **MSS handle thread-affinity** | Improved cross-thread handling for Linux/macOS. |
| **IP validation at auth time** | Global block, per-token block, per-token allow all enforced at WebSocket connect. |

### 🗑️ Removed

- Debug logging from launcher (`[DEBUG]` prefix removed from production output).

---

## 🚀 [1.2.5] -

> **The "It Just Works" Release** - smoother mouse, smarter watch mode, and no more ngrok.

### ✨ What's New

| Feature | Why You'll Love It |
|---------|-------------------|
| **🖱️ Direct-delta mouse** | Feels like a real USB mouse - no smoothing lag, no EMA drift. Raw pointer deltas sent instantly. |
| **⌨️ Watch-mode keyboard button** | Fullscreen watching? The keyboard button stays visible. Tap it, type, done. |
| **🛡️ CSS hardening for Watch Mode** | `pointer-events: none` on the stream + `touch-action: none` on the container = no more accidental mis-taps. |
| **🔐 Connection Request flow** | Don't have a token? Request access. Admin approves from the desktop app. Zero friction for guests. |
| **⚡ Auto-connect from URL** | Share `?token=abc123` - recipient opens the link and connects automatically. No copy-paste. |
| **🔄 "Already have a token?" toggle** | Switches between "request access" and "connect directly" forms instantly. |
| **🚫 Duplicate request guard** | Rapid clicks or page reloads can't spam the server with duplicate connection requests. |

### 🐛 Fixed

| Bug | The Fix |
|-----|---------|
| **Screen capture flapping** | `capture()` was tearing down/rebuilding on every frame when called from a different thread. Added `_handle_cross_thread_verified` flag - one fix, stable stream. |
| **Silent Cloudflare disconnects** | Dead WebSockets lingered forever. Added 30s heartbeat + async cleanup - connections now die when they should. |
| **Tailscale IP detection** | `socket.getaddrinfo()` lied. Now parses `tailscale status --json` directly - finds your 100.x tailnet IP every time. |
| **Admin app crash on decline** | `_decline_request` was accidentally nested inside another function. One indentation fix, crash gone. |
| **Approve button fired 4×** | PyQt6's `QDialogButtonBox.accepted` signal was quadruple-firing. Replaced with explicit `QPushButton` wiring - one click, one action. |
| **Dialog closed without accepting** | `_on_ok` forgot to call `self.accept()`. Added it - the caller now actually knows you clicked OK. |
| **"Already have a token?" did nothing** | Missing click handler. Wired to `_showExistingTokenUI()` - the form now actually appears. |
| **Wrong form on token toggle** | Was showing the request form instead of the connect form. Fixed - you see server URL + access token fields as intended. |
| **Mouse felt sluggish** | EMA smoothing at 0.95 meant ~150ms lag per move. Set to 0.0 - instant response, zero overshoot. |
| **Stream info invisible in watch mode** | Opacity bumped from 0.7 → 0.85, added `backdrop-blur`. Readable over any content. |

### 🗑️ Removed

- **ngrok tunnel provider** - The remaining four (Cloudflare, Tailscale, Pinggy, Zrok2) plus local-only cover every use case. An own-domain option is planned.

---

## [1.2.4] - 2026-07-07

### 🐛 Fixed

| Bug | Fix |
|-----|-----|
| **Slow queue age check kills keyboard input** | Bogus `qsize()` comparison in MouseWorker loop removed; `_enqueued_at` based aging is correct. |
| **Tailscale tunnel always reports failure** | Added `NO_PROCESS` sentinel; `TailscaleTunnel.start()` returns it on success instead of `None`. |
| **WebSocket double-auth race** | `authSent` flag prevents duplicate auth sends. |
| **admin_app.py wrong project root** | Path calculation corrected to `.parent.parent.parent`. |
| **Legacy token file format crash on validate()** | `_load_tokens()` normalizes non-dict values into safe dicts. |
| **Cloudflare partial file on download failure** | Writes to `.tmp` first, atomic rename on success. |
| **Token rotation thread busy-loop in non-TTY mode** | Added `sys.stdin.isatty()` guard before starting rotation thread. |
| **Separate move+click WS frames** | Merged into single compound message `{type: "click", mode: "absolute", x, y}`. |
| **safe_print fallback wrong signature** | Changed to `def safe_print(*args, **kwargs)`. |
| **Class-level mutable DEFAULT_PERMISSIONS** | Replaced with immutable tuple + `@classmethod` returning fresh copy each call. |
| **QR code crash on all platforms** | `print_ascii(target=...)` doesn't exist on any version of qrcode. Replaced with working `out=StringIO()` approach that captures ASCII art to string buffer and pipes through `safe_print`. Works across all qrcode versions (8.2, 7.x, 6.x) and never bypasses safe_print's encoding fallback. |
| **Screen stream dying silently** | MSS grab can silently return garbage/empty frames when OS drops display session. Added `ScreenRecoveryMonitor` - background self-healing module that monitors frame health on Windows and Linux. |

### ✨ Added

- **`screen_recovery.py`** - self-healing screen capture monitor (cross-platform, no OS-specific code):
  - Tracks valid-frame timestamps; forces engine teardown + rebuild after 8s silence (no clients) or 15 consecutive None frames.
  - Detects reconnection events (clients disconnect → reconnect) and immediately triggers recovery sweep.
  - Guards against infinite stuck states - monitors engines stuck in FAILED/DEGRADED past cooldown.
  - Monitors monitor list staleness - forces rebuild if list is empty after 60s idle.
  - Uses `call_soon_threadsafe` to schedule teardown/rebuild on event loop thread (never runs MSS teardown from worker thread).
  - Respects 4s cooldown between recovery sweeps to prevent hammering.
- Server wiring - `_broadcast_screen` feeds frame results into recovery monitor; client connect/disconnect triggers reconnection sweeps; monitor starts on server `start()` and stops on shutdown.

---

## [1.2.4] - 2026-07-07

### 🐛 Fixed

- **Slow queue age check kills keyboard input** - bogus `qsize()` comparison in MouseWorker loop removed; `_enqueued_at` based aging is correct.
- **Tailscale tunnel always reports failure** - added `NO_PROCESS` sentinel; `TailscaleTunnel.start()` returns it on success instead of `None`.
- **WebSocket double-auth race** - `authSent` flag prevents duplicate auth sends.
- **admin_app.py wrong project root** - path calculation corrected to `.parent.parent.parent`.
- **Legacy token file format crash on validate()** - `_load_tokens()` normalizes non-dict values into safe dicts.
- **Cloudflare partial file on download failure** - writes to `.tmp` first, atomic rename on success.
- **Token rotation thread busy-loop in non-TTY mode** - added `sys.stdin.isatty()` guard before starting rotation thread.
- **Separate move+click WS frames** - merged into single compound message `{type: "click", mode: "absolute", x, y}`.
- **safe_print fallback wrong signature** - changed to `def safe_print(*args, **kwargs)`.
- **Class-level mutable DEFAULT_PERMISSIONS** - replaced with immutable tuple + `@classmethod` returning fresh copy each call.
- **QR code crash on all platforms** - `print_ascii(target=...)` doesn't exist on any version of qrcode; the kwarg only works on unreleased forks. Replaced with working `out=StringIO()` approach that captures ASCII art to string buffer and pipes it through `safe_print`. Works across all qrcode versions (8.2, 7.x, 6.x) and never bypasses safe_print's encoding fallback.
- **Screen stream dying silently after a while** - MSS grab can silently return garbage/empty frames without raising when OS drops display session (Windows session lock, GPU idle, monitor reconfig). Server kept broadcasting blank frames indefinitely because nothing detected the silent failure. Added `ScreenRecoveryMonitor` (`screen_recovery.py`) - background self-healing module that monitors frame health on both Windows and Linux.

### ✨ Added

- **`screen_recovery.py`** - self-healing screen capture monitor (cross-platform, no OS-specific code):
  - Tracks valid-frame timestamps; forces engine teardown + rebuild after 8s silence (no clients) or 15 consecutive None frames.
  - Detects reconnection events (clients disconnect → reconnect) and immediately triggers recovery sweep.
  - Guards against infinite stuck states - monitors for engines stuck in FAILED/DEGRADED past cooldown.
  - Monitors monitor list staleness - forces rebuild if monitor list is empty after 60s idle.
  - Uses `call_soon_threadsafe` to schedule teardown/rebuild on event loop thread (never runs MSS teardown from worker thread).
  - Respects 4s cooldown between recovery sweeps to prevent hammering.
- Server wiring - `_broadcast_screen` now feeds frame results into recovery monitor; client connect/disconnect events trigger reconnection sweeps; monitor starts on server `start()` and stops on shutdown.

---

## [1.2.3] - 2026-07-07

### 🐛 Fixed

- **QR code not displaying on Windows** - `qrcode.print_ascii()` writes directly to `sys.stdout`, bypassing `safe_print`. On Windows OEM codepages (CP1252, CP936/GBK, etc.) this silently failed with no visible output. QR ASCII art is now rendered to a `StringIO` buffer first and piped through `safe_print`. Emoji chars in the QR header (`📱`, `🔗`) removed since they were also potential crash points on legacy consoles.
- **Screen capture validation failing on Windows with DPI scaling >100%** - `_get_windows_dpi_scale()` used an incorrect ctypes call (`GetDpiForWindow(hdc)` expects a HWND, not an HDC), which could raise or return invalid values. Replaced with `GetDeviceCaps(hdc, LOGPIXELSX)` via the desktop window handle. The validation overlap check comparing MSS logical pixels against pyautogui physical pixels was removed - these are fundamentally different coordinate spaces on Windows and cannot be meaningfully compared; validation now simply confirms pyautogui didn't crash on position read.

---

## [1.2.2] - 2026-07-07

### 🐛 Fixed

- **Screen capture engine validation failure on Windows with DPI scaling >100%** - pyautogui.position() returns physical pixels while MSS monitor coordinates are logical pixels, causing a mismatch that made `_validate_engine()` fail and the entire screen capture pipeline abort. Added `_get_windows_dpi_scale()` (via ctypes `GetDpiForSystem` / `GetDpiForWindow`) to detect DPI scaling on Windows; all pyautogui coordinate reads in validation, monitor auto-tracking, and cursor overlay now convert physical → logical pixels when DPI ≠ 100%. On Linux/macOS the scale factor is always 1.0 with zero overhead.
- **UnicodeEncodeError when printing emoji characters on Windows consoles** - `print()` calls across 6 modules (`server.py`, `qr_display.py`, `tunnel_manager.py`, `zrok2_repair.py`, `admin_app.py`, `auth.py`) used emoji/special Unicode characters that crash the process when the Windows console uses a legacy codepage (CP1252, CP936/GBK, etc.) instead of UTF-8. Introduced `safe_print()` / `safe_print_stderr()` utility in `__init__.py` that falls back to `errors='replace'` encoding, producing visible output with `?` placeholders instead of a fatal crash. All 70+ print calls replaced.
- **Launcher banner box-drawing chars breaking on Windows** - the ASCII art banner used Unicode block elements (`░█▀`) that couldn't render on OEM console codepages; replaced with clean `===` bordered text layout.

### Changed

- Launcher menu and startup banner now use `safe_print()` for all output, ensuring the app starts and runs correctly on any Windows console configuration without requiring locale/encoding workarounds.

---

## [1.2.1] - 2026-07-07

### 🐛 Fixed

- **Admin app crashes on startup when PyQt6 is missing** (`NameError: name 'QThread' is not defined`) - `ServerProcessWorker` and other Qt-dependent classes were defined at module level outside the `try/except ImportError` guard for PyQt6, causing a `NameError` when importing `admin_app` without PyQt6. Fixed by wrapping all Qt-dependent class definitions inside an `if QT_AVAILABLE:` block with corresponding stubs in the `else` branch so the module imports cleanly regardless of whether PyQt6 is installed.

---

## [1.2.1] - 2026-07-06

### 🔐 Security

- **Server-side input permission enforcement** - tokens with restricted permissions (e.g., no `move`) now receive `permission_denied` errors on guarded WebSocket commands; previously, the server only validated the token at connect time and never checked per-message permissions.
  - Permission checks applied to: `move`, `click`, `double_click`, `mouse_down`, `mouse_up`, `scroll`, `key`, `type`, `hotkey`, `screen_toggle`.
  - Each connected WebSocket now tracks its authenticated token; permissions are looked up on every guarded message.
  - Custom permissions set via the admin app are now persisted to disk (`_save_tokens()` called after `create_token`).

### ✨ Added

- **Desktop admin app (`anywhereinput --app`)** - a PyQt6 GUI that replaces the terminal launcher for users who want a visual interface. Runs server, manages tokens, and monitors clients from one window.
  - Server lifecycle control: start/stop with live log streaming.
  - Tunnel selection dropdown (Cloudflare, Tailscale, Pinggy.io, Zrok2, ngrok, Local).
  - Per-client input permissions (`move`, `click`, `scroll`, `keyboard`, `screen_toggle`, `ping`).
- **IP allowlist management** - per-token IP restrictions with CIDR and single-host support (empty = allow all).
- **Connected clients monitor** - live engine status polling for the running server instance.
- **`[app]` optional dependency group** - install with `pip install anywhereinput[app]` to get PyQt6 for the desktop app.

### 🐛 Fixed

- **Screen capture silently stops after a while** - MSS handle created in the server thread was being used by `run_in_executor` worker threads, but `_sct_thread_id` was cleared to `None` after successful rebuild with a comment claiming "Linux handles are fine across threads." This caused the thread-affinity check in `capture()` to silently skip its guard, leading to corrupted/black grabs that returned `None` frames and eventually killed the stream. Fixed by keeping `_sct_thread_id` set to the actual build-thread ID so the affinity check stays active, adding a post-capture black-frame detector, and properly discarding stale handles before rebuild decisions.
- **Screen capture infinite HEALTHY/REBUILDING loop** - on Linux the executor worker thread differs from the init thread; after a failed rebuild attempt the state reset to REBUILDING which immediately triggered another check, creating an endless cycle. Fixed by ensuring `_sct` is nulled in `_attempt_rebuild()` cleanup so subsequent `capture()` calls see `_sct is None` and skip the grab entirely rather than looping.
- **Screen capture failure not detected on startup** - no validation was run when the server initialized, so if MSS couldn't connect to the display (Wayland session lock, GPU reset, etc.), the server would still report "ready" but screen capture was dead from second one. Added a 3-attempt init verification that disables capture with a clear error log if it fails.
- **Screen broadcast exceptions silently swallowed** - `_broadcast_screen` caught all exceptions and just printed to stdout without updating engine state, so clients kept showing "HEALTHY" while the stream was dead. Now sets screen engine state to DEGRADED on loop errors and uses persistent `screen_status` notifications (stays visible 15s for degraded/failed states).
- **Screen capture post-broadcast state notifications faded too quickly** - server sent `screen_status` messages with transient client-side overlays that auto-hid after a few seconds, making the user think everything was fine. Fixed by extending display time to 15 seconds for degraded/failed states and adding `persist: true` flag so the overlay won't auto-hide while the engine is unhealthy.
- **WebSocket auth failures silently closed** - invalid tokens would close the connection without any message to the client, leaving the user confused. Now sends `{type: "error", message: "Authentication failed: ..."}` before closing.
- **Malformed WebSocket JSON handled silently** - bad messages from clients caused unhandled exceptions in `msg.json()` that were lost. Now catches the parse error and replies with a clear error message.
- **Cloudflare tunnel origin validation returning 403** - tunnel provider origins were checked inside an `elif` that only ran when `Host` header was empty, but it was never empty. Moved tunnel-origin checks to run before same-origin host comparison.
- **WebSocket `onopen` race condition on Cloudflare tunnels** - tunnel proxies can fire `onopen` before the upgrade completes; added `readyState === WebSocket.OPEN` guard before sending auth message in `app.js`.
- **Admin app capture settings ignored** - `SettingsPanel` exposed FPS, quality, and scale spinners but they were never passed to the server subprocess. Fixed: `ServerProcessWorker` now accepts and forwards all four params (`fps`, `quality`, `scale`, plus existing `port`, `tunnel`) to the actual `anywhereinput` CLI command.
- **Admin app client list said "requires custom API endpoint"** - after we added `/api/clients` it still displayed stale documentation. Updated to actually call the endpoint and show real client data (IP, count, engine status).
- **Static file serving corrupted binary assets** - `client.py::static_file` used `'rb'` mode but then decoded with `latin-1` for non-text files, which could corrupt PNG/JPG assets. Now serves text files as UTF-8 strings and binary files as raw bytes via `body=` parameter.
- **Token save failures silently lost tokens** - `_save_tokens()` in `auth.py` had no `try/except`; a full disk or permission error would cause the server to keep running with an empty token store. Added IOError handling that prints a visible warning.

### ⚡ Latency - Stream & Input Speed

- **Mouse input lag eliminated** - `MouseWorker.smoothing` was set to `0.95`, meaning each mouse move took ~60 ticks (~150ms) to reach its target. Set to `0.0` for direct movement on the very tick it arrives.
- **Server-side input batching too aggressive** - `MouseWorker.run()` batched up to 20 queued items per tick, so each mouse move could wait behind 19 others before being processed. Reduced batch size to 3 and tick interval from 8ms to 1ms.
- **Stream frame interval delay removed** - `_broadcast_screen` slept `1/fps` seconds between captures (up to 33ms at 30fps). Now captures immediately with only a 2ms guard against CPU spinning, delivering frames as fast as the capture hardware allows.
- **Server-to-client send no longer blocks on slow clients** - `_broadcast_to_all` awaited each `ws.send_str()` sequentially, so one dead/slow client blocked others. Replaced with fire-and-forget `_broadcast_to_all_async()` that queues sends and cleans up dead connections asynchronously.
- **Client mouse movement now sent instantly on every pointermove** - previously buffered moves were only flushed every 16ms via a `setTimeout` loop. Now each `pointermove` fires a WS message immediately; the timer loop still flushes any gaps but isn't the delivery path anymore.
- **JPEG encoding sped up** - replaced LANCZOS downscaling with NEAREST (negligible visual quality loss at streaming distances), disabled `optimize=True` header pass, and enabled progressive JPEG for faster client decode.
- **Client frame skip to prevent GPU overload** - server may now send >60fps; added `_pendingFrames` counter so the client keeps only the latest frame every other tick, preventing browser rendering backlog that would otherwise delay input processing.
- `conftest.py` was duplicated (220 lines = 2× content), causing pytest import confusion. Truncated to single copy.
- Mock mss monitors in `conftest.py`: virtual desktop entry `{}` had no dimensions, so `_build_engine` validation filtered it out and dedup collapsed all entries to one → `monitor_count` returned 0 for tests. Fixed by giving the virtual-desktop entry real combined display dimensions (`3840×1080`) so it survives validation.
- `client.html` was duplicated (two full HTML documents), causing `<script>` to load twice and `AnywhereInputClient` redeclaration error. Truncated to single copy.
- `app.js` class definition was duplicated, causing "Identifier 'AnywhereInputClient' has already been declared" SyntaxError. Fixed by removing the duplicate.

---

## [1.1.6] - 2026-07-04

### 🐛 Fixed

- Screen-capture state callback deadlock that could block engine-status requests while transitioning states.
- Shutdown noise during Ctrl+C by draining pending asyncio tasks before loop close.
- Tunnel process cleanup now handles interrupt timing more gracefully during stop.

---

## [1.1.5] - 2026-07-04

### ✨ Added

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

### 🐛 Fixed

- Removed command/help mismatches by unifying documented and accepted tunnel values across parser choices, examples, and tunnel help text.
- Full pytest run no longer requires manual server startup (`tests/ws_test.py` is now self-contained.)

---

## [1.1.4] - 2026-07-01

### ✨ Added

- Ubuntu-specific installation guidance using `pipx` (`apt install pipx`, `pipx install anywhereinput`) in docs.

### Changed

- Linux launcher now installs dependencies via `python -m pip` from the project virtual environment for better compatibility.
- Linux launcher now starts the server via `python -m anywhereinput.server` to avoid broken entrypoint wrapper scripts.

### 🐛 Fixed

- Resolved startup failures where launcher-selected executables could trigger `ModuleNotFoundError: No module named 'anywhereinput'`.
- Improved self-repair flow when package import checks fail inside `.venv`.

---

## [1.1.3] - 2026-07-01

### Changed

- Provider-aware host handling for tunnel startup to use correct local upstream addresses.
- Automatic bind host selection for Tailscale (fallback to `0.0.0.0` when loopback would fail remote access).

### 🐛 Fixed

- Tunnel startup/address mismatches caused by provider-specific host expectations (`localhost` vs `0.0.0.0`/tailnet-reachable bind).

---

## [1.1.2] - 2026-07-01

### Changed

- **Single-token storage** - `trusted_tokens.json` now stores only the most recent token. No accumulation.
- **Legacy cleanup** - automatically purges multi-entry token files on first load.

### 🐛 Fixed

- **Token file bloating with every session** (now single-token storage)

---

## [1.1.1] - 2026-07-01

> **The "I Need Help" Release** - better CLI, clearer errors, version flag.

### ✨ What's New

| Feature | Description |
|---------|-------------|
| **`--version`** | Shows installed version. Simple, but you asked for it. |
| **Comprehensive `--help`** | Usage examples, tunnel provider descriptions, project links in footer. |

### Changed

- `RawDescriptionHelpFormatter` for readable multi-line help.
- Better error messages with context and guidance.
- All flags have detailed help text.

---

## [1.0.0] - 2026-06-28

> **The Big One** - 5 tunnel providers, multi-monitor support, and a launcher that works everywhere.

### ✨ What's New

| Feature | The Pitch |
|---------|-----------|
| **5 tunnel providers** | Cloudflare (no account), Tailscale (P2P), Pinggy (SSH), Zrok2 (open source), ngrok (legacy). Pick your privacy level. |
| **Tailscale P2P** | No public URL. Your 100.x tailnet IP, direct peer-to-peer. Both devices on the same tailnet = connected. |
| **Multi-monitor support** | `--monitor N` or auto-track. Cursor follows you across displays. |
| **Screen info API** | `GET /api/screen`, `GET /api/monitors`, `POST /api/monitor/{index}`. Build tools on top of AnywhereInput. |
| **Token API** | `GET /api/token` - programmatic access to the current session token. |
| **Centralized YAML config** | `config/settings.yaml` - server, capture, auth, and tunnel defaults in one place. |
| **One-click Windows launchers** | `.bat` files for every provider. Double-click, done. |
| **Linux `run.sh` auto-setup** | First run installs deps, creates venv, shows banner. No manual steps. |
| **ARM support** | Cloudflare binary auto-detects architecture (x64, arm64). |

### Changed

- **Unified entry point** - `anywhereinput` CLI command via `pyproject.toml` entry points.
- **Modular server** - `server.py`, `auth.py`, `screen_capture.py`, `tunnel_manager.py`, `client.py`, `qr_display.py`, `zrok2_repair.py`. Each does one thing.
- **No more `RuntimeWarning`** - eager imports removed from `__init__.py`.
- **Cloudflare tunnel** - ARM architecture detection, absolute path resolution for binary downloads.
- **Pinggy tunnel** - updated SSH endpoint from `qr@a.pinggy.io` to `free.pinggy.io -T` per official docs; URL regex updated for `.run.pinggy-free.link` and `.free.pinggy.net` domains.
- **Zrok2 tunnel** - fixed URL extraction using non-blocking I/O with `select()` + `fcntl`, JSON log parsing with raw newline handling.
- **Ngrok tunnel** - updated domain matcher from `.ngrok-free.app` to `.ngrok-free.dev` (ngrok v3).
- **Tailscale availability check** - via `tailscale status --json` with multiple API field fallbacks.
- **Linux launcher uses `anywhereinput` CLI command** instead of `python -m`.
- **Provider menu** - availability indicators (✓/?) shown next to each option, auto-checks installed status.
- **Kill orphaned tunnel processes** before starting new ones (cloudflared, zrok2, ngrok).

### 🐛 Fixed

| Bug | Fix |
|-----|-----|
| Cloudflare binary path resolution | Downloads now saved to project root with correct architecture filename and absolute path |
| Zrok2 URL capture | Was failing because of blocking pipe reads; switched to non-blocking `select()` + raw byte parsing |
| Ngrok domain matching | `.ngrok-free.dev` wasn't matched by the old `.ngrok-free.app` regex |
| Pinggy SSH host | `qr@a.pinggy.io` didn't work; corrected to official endpoint `free.pinggy.io` |
| RuntimeWarning: `'anywhereinput.server' found in sys.modules` | Removed eager imports from package `__init__.py` |

---

## [0.4.0] - 2026-06-23

> **The Tunnel Unification Release** - one launcher, four providers, zero config.

### ✨ What's New

| Feature | What It Does |
|---------|-------------|
| **Unified tunnel launcher** | `launch_with_tunnel.py --provider {cloudflare,pinggy,zrok,zrok2,ngrok}`. One script, every provider. |
| **Cloudflare auto-download** | No account, no install. Downloads `cloudflared` on first run. |
| **Pinggy via SSH** | Uses your existing SSH client. No additional software. |
| **Zrok2 repair tool** | `zrok2_repair.py` - remove broken tokens, re-enroll with new ones. |
| **Path overrides** | `--cloudflared-path`, `--zrok-path`, `--ngrok-path` for custom installs. |
| **Windows one-click launchers** | `.bat` files for Cloudflare, Pinggy, Zrok2. Double-click, tunnel starts. |

### Changed

- All Windows `.bat` launchers auto-detect Python across common install paths on all drive letters.
- All `.bat` launchers create and activate a venv automatically on first run.

---

## [0.3.0] - 2026-06-21

> **The Screen Sharing Release** - see your PC, tap to click, two-finger scroll.

### ✨ What's New

| Feature | The Experience |
|---------|---------------|
| **Real-time screen capture** | JPEG stream from server to browser. See your desktop on your phone. |
| **Screen overlay click** | Tap anywhere on the stream = cursor moves there. Intuitive. |
| **Two-finger scroll** | Natural gesture on the touchpad area. |
| **Long-press right click** | Hold for 600ms, feel the vibration. Right-click without a right mouse button. |
| **Settings panel** | Toggle screen capture, FPS counter, tap-to-click, long-press. Sensitivity slider (0.3x–3.0x). |
| **Hardware cursor capture** | MSS backend captures the real cursor, not a software overlay. |
| **Cursor overlay** | White outline + red cross + yellow center dot. Visible on any background. |
| **Keepalive ping** | Every 10 seconds. Prevents WebSocket timeout on idle connections. |
| **Stream watchdog** | Auto-reconnects stalled streams after 4 seconds. |
| **Auto-connect via URL** | `?token=***&host=...&port=...` - share a link, recipient connects instantly. |
| **Visual feedback on keyboard input** | Green flash for chars, blue for special keys. |

### Changed

- Increased scroll speed: button 5→15, touchpad 3→12.
- Rewrote keyboard input handling to a hybrid approach:
  - Primary: `beforeinput` event for virtual keyboard compatibility
  - Secondary: `keydown` for special keys and physical keyboards
  - Fallback: `input` event with 50ms deduplication debounce
- Improved error handling and logging throughout the screen capture engine.
- Cursor overlay now uses thick white outline for visibility on any background.

### 🐛 Fixed

- Mouse cursor not visible on client screen stream
- MSS thread-safety issue - now uses thread-local instances per capture thread
- Silent cursor overlay failures now properly logged
- Screen capture backend fallback: MSS → PIL/pyautogui

### Dependencies

- Added `mss` for hardware-accelerated screen capture with cursor
- Added `Pillow` for JPEG compression and cursor overlay rendering

---

## [0.2.0] - 2026-06-18

### ✨ What's New

- **Initial release of AnywhereInput**
- **Token-based WebSocket authentication** with auto-generated tokens per session
- **Mouse control**: move (relative + absolute), click, double-click, right-click, scroll
- **Keyboard input**: single keys and hotkey combinations (Ctrl+C, Ctrl+Alt+Del, etc.)
- **ngrok tunneling support** for remote access beyond local network
- **Cross-platform server**: Windows, Linux, macOS
- **Browser-based client** - no app install required
- **Setup scripts** for Windows (`.bat`) and Linux/macOS (`.sh`)
- **`launch_with_ngrok.py`** - Python launcher with automatic ngrok detection and setup
- **QR code display in terminal** for instant mobile connection

---

<div align="center">

## 🏷️ Versioning

This project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html):

| Component | Meaning |
|-----------|---------|
| **MAJOR** (X.0.0) | Breaking changes - read the migration notes |
| **MINOR** (0.X.0) | New features - safe to upgrade |
| **PATCH** (0.0.X) | Bug fixes - upgrade immediately |

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

**Want to see what's coming?** Check the [roadmap](README.md#-roadmap) and [open issues](https://github.com/Z-Hussein/AnywhereInput/issues).

**Found a bug?** [Open an issue](https://github.com/Z-Hussein/AnywhereInput/issues/new) - we fix fast.

**Want to contribute?** See [CONTRIBUTING.md](CONTRIBUTING.md).

<img src="https://capsule-render.vercel.app/api?type=soft&color=0:059669,100:10b981&height=80&section=footer&fontSize=20&fontColor=ffffff&animation=fadeIn" alt="Footer" />

</div>
