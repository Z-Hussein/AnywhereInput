# Important Notes

This document summarizes the most important operational and security details for AnywhereInput.

## Security and Access

- Treat every session token as sensitive.
- Do not share terminal screenshots that include the token.
- Tokens are generated per server start.
- If you suspect exposure, stop the server and start it again to issue a new token.
- Tunnel URLs are public entry points. Security depends on the token.

## Connection Behavior

- The client should only disconnect when:
  - The server is stopped (for example with Ctrl+C), or
  - The user explicitly disconnects from the client UI.
- If you see unexpected disconnects, check:
  - Tunnel health,
  - Local CPU saturation during capture,
  - Browser console WebSocket close code and reason.

## Tunnel Logging

- Cloudflare tunnel output is intentionally minimized.
- Normal startup should show only essential lines (URL and app output).
- Detailed Cloudflare diagnostics are only surfaced when startup fails.

## Monitor Selection

- Monitor dropdown is populated from detected displays.
- Auto mode follows cursor across displays.
- Fixed monitor modes are listed as individual options.
- If monitor list looks wrong, reconnect and reopen settings after stream starts.

## Mobile UI

- Client layout is responsive and adapts to viewport changes.
- Safe-area insets are handled for modern phones.
- Orientation changes and browser UI chrome changes are handled dynamically.

## Publish and Build

Before publishing:

1. Run tests.
2. Build wheel and sdist.
3. Run Twine checks.

Recommended commands:

python3 -m pytest tests/
python3 -m build --sdist --wheel
python3 -m twine check dist/*

## Known Constraints

- Designed for personal or trusted environments.
- Not intended as a hardened enterprise remote access stack.
- Add external auth/proxy controls if you require enterprise security posture.
