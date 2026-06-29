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

### Ping
```json
{"type": "ping"}
```
Server responds with `{"type": "pong"}`.

## HTTP Endpoints

### GET /api/screen
Returns screen dimensions:
```json
{"width": 1920, "height": 1080}
```

### GET /api/monitors
Returns monitor information:
```json
{
  "monitors": [{"index": 0, "name": "Primary", "width": 1920, "height": 1080}],
  "current": 0,
  "auto_track": true
}
```

### POST /api/monitor/{index}
Switches the capture monitor:
```json
{"success": true, "monitor": 1, "auto_track": false}
```

### GET /api/token
Returns the current active token:
```json
{"token": "<current-token>"}
```
