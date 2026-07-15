# WebSocket API

## Authentication
Connect to `/ws` and send:
```json
{"type": "auth", "token": "your-token-here"}
```

## Commands

### Mouse Move (Relative)
```json
{"type": "move", "mode": "relative", "dx": 10, "dy": 15}
```

### Mouse Move (Absolute)
```json
{"type": "move", "mode": "absolute", "dx": 0.5, "dy": 0.5}
```
Values are 0.0-1.0 representing screen percentage.

### Mouse Click
```json
{"type": "click", "button": "left", "clicks": 1}
```
Buttons: `left`, `right`, `middle`. Clicks: 1 or 2.

### Scroll
```json
{"type": "scroll", "amount": 15}
```
Positive = up, negative = down.

### Key Press
```json
{"type": "key", "key": "enter"}
```

### Hotkey Combo
```json
{"type": "hotkey", "keys": ["ctrl", "c"]}
```

### Screen Toggle
```json
{"type": "screen_toggle", "enabled": true}
```

### Restart Stream Capture
```json
{"type": "screen_restart"}
```
Forces the capture engine to tear down and rebuild. Use when the stream freezes or shows a black/dead screen.

### Ping
```json
{"type": "ping"}
```
Server responds with `{"type": "pong"}`.

## Server Events

### Screen Frame
```json
{"type": "screen", "data": "<base64-jpeg>"}
```

### Screen Capture Status
```json
{"type": "screen_status", "status": "rebuilding", "message": "Reconnecting to display..."}
```
Status values include: `healthy`, `degraded`, `rebuilding`, `failed`, `offline`.

### Engine Recovery/Error Signals
```json
{"error": "capture_error", "message": "Input engine is recovering.", "recovering": true}
{"error": "capture_engine_offline", "message": "Input engine is offline. Retry shortly."}
```

## HTTP Endpoints

### Token Management

#### GET /api/tokens
List all active tokens (values are truncated to first 12 chars).
```json
{
  "tokens": [
    {
      "token": "abc123...",
      "full_token": "<full-value>",
      "name": "manual",
      "created": "2026-07-06T11:00:00+00:00",
      "permissions": ["move", "click", "scroll"]
    }
  ]
}
```

#### POST /api/tokens
Create a new token. Send JSON body:
```json
{
  "name": "guest-device",
  "permissions": ["move", "click", "scroll"]
}
```
Response (201):
```json
{
  "token": "<new-token>",
  "name": "guest-device",
  "permissions": ["move", "click", "scroll"]
}
```
Accepted fields: `name` / `label`, `permissions`. Permissions default to all if omitted.

#### PATCH /api/tokens/{token}
Update an existing token's name or permissions. `{token}` is the **full** token value.
Request body:
```json
{
  "name": "renamed",
  "permissions": ["move", "ping"]
}
```
Response (200):
```json
{"ok": true, "token": {"name": "renamed", ...}}
```

#### DELETE /api/tokens/{token}
Revoke a token. `{token}` is the **full** token value.
Response: `{"ok": true}` or 404 if not found.

### Connected Clients

#### GET /api/clients
List currently connected WebSocket clients.
```json
{
  "count": 2,
  "clients": [
    {"id": "<identifier>", "ip": "192.168.x.x:54321", "connected": true}
  ]
}
```

---

### Screen & Engine Info

#### GET /api/screen
Returns screen dimensions:
```json
{"width": 1920, "height": 1080}
```

#### GET /api/monitors
Returns monitor information:
```json
{
  "monitors": [{"index": 1, "left": 0, "top": 0, "width": 1920, "height": 1080, "primary": true}],
  "current": 1,
  "auto_track": true
}
```

### POST /api/monitor/{index}
Switches the capture monitor:
```json
{"success": true, "monitor": 1, "auto_track": false}
```

### GET /api/engine
Returns input engine state plus screen capture engine state:
```json
{
  "state": "healthy",
  "failure_count": 0,
  "cooldown_seconds": 0.0,
  "last_error": null,
  "screen_engine": {
    "state": "healthy",
    "enabled": true
  }
}
```
