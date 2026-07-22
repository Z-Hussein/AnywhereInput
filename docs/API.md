# WebSocket API

## Authentication

Connect to `/ws` and send:

```json
{"type": "auth", "token": "your-token-here"}
```

Supported `type` values:
- `"auth"` — authenticate with an existing token
- `"handshake"` — same as auth (alias)
- **Connection requests** — if a pending connection request exists, send `{ "token": "<req_id>::<client_name>" }` to complete it (requires admin approval on the server side).

### Auth Response

On success:

```json
{"type": "auth_ok", "server_os": "linux"}
```

On failure (403 or invalid token): WebSocket is closed with `WS_CLOSE_AUTH_FAILED`.

---

## Commands (Client → Server)

### Mouse Move (Relative)

```json
{"type": "move", "mode": "relative", "dx": 10, "dy": 15}
```

### Mouse Move (Absolute)

```json
{"type": "move", "mode": "absolute", "dx": 0.5, "dy": 0.5}
```

Values are `0.0`–`1.0` representing screen percentage.

### Mouse Click

```json
{"type": "click", "button": "left", "clicks": 1}
```

Buttons: `left`, `right`, `middle`. Clicks: `1` or `2`.

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

---

## Server Events (Server → Client)

### Screen Frame

```json
{"type": "screen", "data": "<base64-jpeg>"}
```

### Screen Capture Status

```json
{"type": "screen_status", "status": "rebuilding", "message": "Reconnecting to display..."}
```

Status values: `healthy`, `degraded`, `rebuilding`, `failed`, `offline`.

### Engine Recovery / Error Signals

```json
{"error": "capture_error", "message": "Input engine is recovering.", "recovering": true}
{"error": "capture_engine_offline", "message": "Input engine is offline. Retry shortly."}
```

---

## HTTP Endpoints

### Health Check

#### GET `/health`

Unauthenticated endpoint for load balancers and monitoring probes.

Response:

```json
{
  "status": "ok",
  "uptime_s": 342.7,
  "clients": 2,
  "screen": "healthy",
  "tunnel": "https://abc123.trycloudflare.com"
}
```

### Token Management

#### GET `/api/tokens`

List all active tokens (values are truncated to first 12 chars).

Response:

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

#### POST `/api/tokens`

Create a new token. Send JSON body:

```json
{
  "name": "guest-device",
  "permissions": ["move", "click", "scroll"],
  "allowed_ips": ["192.168.1.0/24"]
}
```

- `name` or `label` (alias) — human-readable label
- `permissions` — list of allowed command types; defaults to all if omitted
- `allowed_ips` — optional IP allowlist for the token

Response (201):

```json
{
  "token": "<new-token>",
  "name": "guest-device",
  "permissions": ["move", "click", "scroll"]
}
```

#### PATCH `/api/tokens/{token}`

Update an existing token's name or permissions. `{token}` is the **full** token value (not the truncated one).

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

#### DELETE `/api/tokens/{token}`

Revoke a token. `{token}` is the **full** token value.

Response: `{"ok": true}` or 404 if not found.

### Blocked IPs

#### GET `/api/tokens/{token_id}/blocked-ips`

Return the list of blocked IPs for a given token.

Response:

```json
{"blocked_ips": ["10.0.0.5", "192.168.1.100"]}
```

#### DELETE `/api/tokens/{token_id}/blocked-ips/{ip}`

Remove an IP from the block list.

Response:

```json
{"ok": true, "message": "IP 10.0.0.5 unblocked"}
```

### Connected Clients

#### GET `/api/clients`

List currently connected WebSocket clients.

Response:

```json
{
  "clients": [
    {
      "id": "<hex-client-id>",
      "ip": "192.168.x.x:54321",
      "token": "abc123...",
      "full_token": "<full-value>",
      "connected": true
    }
  ]
}
```

Note: the response does **not** include a `count` field (the clients array length is the count).

#### POST `/api/clients/{client_id}/kick`

Kick a connected client and add their IP to the token's block list. `{client_id}` is the hex ID returned by `GET /api/clients`.

Response:

```json
{"ok": true, "message": "Client kicked, IP 10.0.0.5 added to block list"}
```

### Screen & Engine Info

#### GET `/api/screen`

Returns screen dimensions:

```json
{"width": 1920, "height": 1080}
```

#### GET `/api/monitors`

Returns monitor information:

```json
{
  "monitors": [{"index": 1, "left": 0, "top": 0, "width": 1920, "height": 1080, "primary": true}],
  "current": 1,
  "auto_track": true
}
```

#### POST `/api/monitor/{index}`

Switches the capture monitor:

Response:

```json
{"success": true, "monitor": 1, "auto_track": false}
```

Returns 400 if the index is invalid.

#### GET `/api/engine`

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
