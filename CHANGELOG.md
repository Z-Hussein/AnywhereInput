# Changelog

All notable changes to AnywhereInput will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Multi-monitor screen capture support
- Clipboard sync between devices
- File transfer via drag & drop
- iOS Safari-specific optimizations
- Docker image for one-liner deployment
- Custom domain support (ngrok alternative)
- Audio streaming from server to client
- Keyboard layout selection
- Touchpad pinch-to-zoom gesture
- Dark/light theme toggle
- Connection history / saved servers
- Biometric auth (WebAuthn) option

## [2.0.0] - 2026-06-21

### Added
- Real-time screen capture streaming from server to browser client via WebSocket
- Screen overlay click - tap anywhere on the live stream to move cursor to absolute position
- Two-finger scroll gesture on touchpad area
- Long-press right click (600ms hold) with haptic feedback via navigator.vibrate()
- Settings panel with toggles for screen capture, FPS counter, tap-to-click, long-press
- Adjustable mouse sensitivity slider (0.3x to 3.0x)
- Hardware cursor capture via MSS backend with thread-local instances
- Highly visible software cursor overlay (white outline + red cross + yellow center dot)
- Screen info API endpoint (GET /api/screen) returning capture config
- Keepalive ping/pong every 10 seconds to prevent WebSocket timeout
- Screen stream watchdog - auto-reconnects stalled streams after 4 seconds
- CLI flags for screen capture: --fps, --quality, --scale, --no-capture
- Connection status bar with color coding (connecting/disconnected/connected)
- Auto-connect from URL parameters (?token=, ?host=, ?port=)
- Visual feedback on keyboard input (green flash for chars, blue for special keys)

### Changed
- Increased scroll speed: button scroll 5 -> 15, touchpad scroll 3 -> 12
- Rewrote keyboard input handling to hybrid approach:
  - Primary: beforeinput event for virtual keyboard compatibility
  - Secondary: keydown for special keys and physical keyboards
  - Fallback: input event with 50ms deduplication debounce
- Improved error handling and logging throughout screen capture engine
- Cursor drawing now uses thick white outline for visibility on any background

### Fixed
- Mouse cursor not visible on client screen stream
- MSS thread-safety issue by using thread-local instances per capture thread
- Silent cursor overlay failures now properly logged
- Screen capture backend fallback: MSS -> PIL/pyautogui

### Dependencies
- Added mss for hardware-accelerated screen capture with cursor
- Added Pillow for JPEG compression and cursor overlay rendering

## [1.0.0] - 2026-02-18

### Added
- Initial release of AnywhereInput
- Token-based WebSocket authentication with auto-generated tokens
- Mouse control: move (relative), click, double-click, right-click, scroll
- Keyboard input: single keys and hotkey combinations (Ctrl+C, Ctrl+Alt+Del, etc.)
- ngrok tunneling support for remote access
- Cross-platform server (Windows, Linux, macOS)
- Browser-based client requiring no app installation
- Setup scripts for Windows (.bat) and Linux/macOS (.sh)
- Python launcher script for automatic ngrok integration
- QR code display in terminal for quick mobile connection
