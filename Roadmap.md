# AnywhereInput Product Roadmap

## Phase 1: Foundation (Current - v1.0.0)

**Status: In Progress**

### Core Features (Done)
- [x] Mouse control (move, click, double-click, right-click, scroll)
- [x] Keyboard input + hotkey combos
- [x] Token-based WebSocket auth
- [x] ngrok tunneling for remote access
- [x] Cross-platform server (Windows, Linux, macOS)
- [x] Browser client (no app install)
- [x] Real-time screen capture streaming
- [x] Touchpad gestures (two-finger scroll, long-press right click)
- [x] Settings panel (sensitivity, FPS, toggles)
- [x] Hardware + software cursor capture

### Immediate Fixes (Before any user testing)
- [ ] Fix HTTPS on local network (self-signed cert or local tunnel)
- [ ] Add WebSocket reconnection with exponential backoff
- [ ] Input validation on dx/dy (clamp to reasonable bounds)
- [ ] Rate limiting on commands (prevent spam)
- [ ] Encrypt token storage (at rest, not plaintext JSON)
- [ ] Graceful capture recovery (restart engine on crash, not just stop)
- [ ] Persistent client settings (localStorage)
- [ ] Connection history / saved servers list

---

## Phase 2: Security & Reliability (v1.1.0)

**Target: 2-3 weeks**

### Security Hardening
- [ ] mTLS or OAuth2 option for enterprise users
- [ ] IP whitelist / blocklist
- [ ] Session timeout (auto-disconnect after idle)
- [ ] Audit log (who connected, when, from where)
- [ ] Token rotation UI (not just Ctrl+N)
- [ ] Optional password protection layer

### Reliability
- [ ] Auto-reconnect on connection drop
- [ ] Connection quality indicator (latency, packet loss)
- [ ] Fallback capture backends (MSS -> PIL -> scrot)
- [ ] Server health check endpoint
- [ ] Client offline mode queue (buffer commands, send on reconnect)

### UX Polish
- [ ] Onboarding flow (first-run wizard)
- [ ] Dark/light theme toggle
- [ ] Keyboard layout selection (QWERTY, AZERTY, etc.)
- [ ] Customizable hotkey buttons
- [ ] Pinch-to-zoom on screen stream
- [ ] Drag-and-drop file transfer (basic)

---

## Phase 3: Scale & Monetization Prep (v1.2.0)

**Target: 1-2 months**

### Infrastructure
- [ ] Replace ngrok dependency with built-in STUN/TURN (WebRTC or custom relay)
- [ ] Multi-monitor support (select which monitor to stream)
- [ ] Clipboard sync (text only first)
- [ ] Audio streaming (server to client)
- [ ] Higher quality capture option (lossless PNG mode for design work)

### Team/Collaboration Features
- [ ] Multiple simultaneous viewers (read-only mode)
- [ ] Screen recording / session replay
- [ ] Annotation tools (draw on screen stream)

### Telemetry & Analytics (privacy-first)
- [ ] Opt-in usage analytics
- [ ] Error reporting (Sentry integration)
- [ ] Performance metrics (latency, FPS, bandwidth)

---


*Last updated: 2026-06-21*
