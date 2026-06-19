# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-06-19

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
- Improved `start_with_ngrok.bat` Python discovery across drives (C..Z) and ngrok search (bundled, drives, PATH)
- Added `--ngrok-path` CLI and `NGROK_PATH` env support in `launch_with_ngrok.py`
- Added Ctrl+N (`n`) in launcher to restart server and regenerate token (token rotation)
- Added `.gitignore` entries to ignore `trusted_tokens.json` and `.venv`

### Changed
- Removed hardcoded default token from `README.md`; launcher now prefers `trusted_tokens.json` token

### Planned
- macOS server support
- Linux server support  
- iOS app support
- Screen sharing capability
- Multi-device simultaneous control
- Custom gesture recognition
- Game controller input mapping
- Recording and playback of commands
