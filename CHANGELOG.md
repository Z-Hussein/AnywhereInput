# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-06-20

### Added
- Initial release of Remote Mouse Controller
- WebSocket-based server for mouse and keyboard control
- Android browser client with touchpad interface
- ngrok integration for cross-network access
- Token-based authentication system
- Support for multiple mouse buttons (left, right)
- Keyboard input and hotkey support
- Scroll wheel support
- Responsive HTML5 interface
- Cross-platform ngrok launcher

### Features
- Real-time mouse movement with low latency
- Left/right mouse clicks and double-clicks
- Keyboard key presses and key combinations
- Scroll wheel support (up/down)
- Screen-relative absolute positioning
- Connection status display
- Support for IPv4 and IPv6

### Performance
- Optimized pyautogui settings for responsive control
- Efficient WebSocket message handling
- Sub-50ms latency on local networks

## [Unreleased]

### Added
- Added `qr_display.py` helper for terminal QR code generation
- Added `--bind` option in `secure_server.py` for custom host binding
- Added local IPv4/IPv6 address detection and status logging in `secure_server.py`
- Added automatic `trusted_tokens.json` generation on server startup
- Added token injection into the served `client.html` page
- Improved `start_with_ngrok.bat` Python discovery across drives (C..Z) and ngrok search locations (bundled, PATH)
- Added `--ngrok-path` CLI and `NGROK_PATH` environment variable support in `launch_with_ngrok.py`
- Added token rotation support via Ctrl+N / `n` in `launch_with_ngrok.py`
- Added `.gitignore` entries to ignore `trusted_tokens.json`, `.venv`, and ngrok artifacts

### Changed
- Removed hardcoded default token from `README.md`; launcher now prefers the token generated in `trusted_tokens.json`

### Planned
- Finish server-side terminal QR code integration and use the correct `generate_terminal_qr()` helper
- Replace `trusted_tokens.json` with TOTP-based auth, session expiry, rate limiting, and IP pinning
- Add `auth.py` for authentication/session management
- Add local-mode default launchers (`start.bat` / `start.sh`) with remote ngrok compatibility and OS config storage
- Add Cloudflare tunnel support via `tunnel_providers.py`
- Add optional HTTPS local mode and audit logging in `~/.anywhereinput`
- Restructure documentation into `docs/` and update `README.md`
- Add install scripts and cross-platform packaging support
- Add GitHub Actions release workflow and standalone binary packaging
