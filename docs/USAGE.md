<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:667eea,100:764ba2&height=150&section=header&text=Usage%20Guide&fontSize=50&fontColor=ffffff&animation=fadeIn" alt="Usage Guide" />

</div>

# Usage Guide ⚙️

## 🖱️ Touchpad Controls

| Action | How |
|--------|-----|
| Move cursor | Drag on touchpad area |
| Left click | Tap touchpad (if enabled) or Left Click button |
| Right click | Long-press touchpad (600ms) or Right Click button |
| Double click | Double Click button |
| Scroll | Two-finger drag on touchpad, or Scroll buttons |
| Center mouse | Center button |

## 📺 Screen Overlay

Tap anywhere on the live screen stream to move the cursor to that location and click. (Only functional on the main display for now.)

## ⌨️ Keyboard

- Tap **Keyboard** button to open text input
- Type text and tap **Send**
- Use **Enter**, **Esc**, **Tab**, **Backspace** buttons
- Use hotkey buttons for common shortcuts

## ⚙️ Settings Panel

Tap the gear icon to access:

- **Screen Capture**: Toggle live stream
- **Mouse Sensitivity**: 0.3x to 3.0x
- **Show FPS Counter**: Display stream performance
- **Tap to Click**: Enable/disable tap-to-click
- **Long Press = Right Click**: Enable/disable long-press gesture

## 🔑 Token Permissions (Admin App)

When managing tokens via `anywhereinput --app` or the token API, you can restrict what each token is allowed to do:

| Permission | Allows |
|-----------|--------|
| `move` | Mouse movement (relative + absolute) |
| `click` | Click, double-click, mouse_down, mouse_up |
| `scroll` | Scroll wheel input |
| `keyboard` | Key press, text typing, hotkeys |
| `screen_toggle` | Enable/disable screen capture stream |
| `ping` | Health check pings (always allowed) |

### IP Allowlist

In the admin app's token editor, set an IP allowlist to restrict which network addresses can use a token:

- Leave empty = allow all IPs
- Single host: `192.x.x.x`
- CIDR range: `192.x.x.x/24`

---

## 📝 Configuration File Management

AnywhereInput includes a `config` command to create, view, and edit configuration files. These config files **are loaded at startup** and become the server defaults. CLI flags override YAML values.

### Config load order (highest wins)

1. **CLI flags** — `--fps`, `--quality`, etc. override everything
2. **`config/local_settings.yaml`** — user overrides (gitignored)
3. **`config/settings.yaml`** — project defaults

### Commands

```bash
# List available config files
anywhereinput config list

# Generate default config files from examples
anywhereinput config init

# Also generate recovery.yaml (capture engine settings)
anywhereinput config init --recovery

# View a config file in the terminal
anywhereinput config view            # shows both settings and recovery
anywhereinput config view --settings   # show settings only
anywhereinput config view --recovery   # show recovery only

# Edit a config file in your default editor ($EDITOR)
anywhereinput config edit
```

### Example: change a setting via YAML

```bash
# 1. Generate config files
anywhereinput config init

# 2. Edit settings.yaml
anywhereinput config edit --settings
# Change: fps: 120 → fps: 60

# 3. Start server - reads from YAML automatically
anywhereinput --tunnel local
# FPS is now 60 (from YAML), not 120 (default)
```

### Example: user-specific overrides

```bash
# Create local overrides (not committed to git)
cat > config/local_settings.yaml << 'EOF'
server:
  port: 9000
screen_capture:
  fps: 30
  quality: 50
EOF

# Start server - uses local_settings.yaml values
anywhereinput --tunnel local
# Port is 9000, FPS is 30
```

> 💡 `config/local_settings.yaml` is gitignored — perfect for machine-specific settings.

---

## 🔄 Graceful Restart

The server supports graceful restart via SIGHUP. Connected clients are notified before shutdown and automatically reconnect.

### Trigger a restart

```bash
# Find the server PID
pgrep -f server_core

# Send SIGHUP
kill -HUP <PID>

# Or if running as a service
systemctl restart anywhereinput
```

### What happens

1. Server broadcasts `{"type": "server_restarting"}` to all connected clients
2. Clients display "Server is restarting - reconnecting in 3s..."
3. Server closes all WebSocket connections with close code 1012
4. Process re-execs with the same CLI arguments
5. Config files are re-read from disk (picks up changes to `settings.yaml`)
6. Clients automatically reconnect to the new server

### Config changes on restart

```bash
# 1. Edit settings while server is running
anywhereinput config edit --settings
# Change: fps: 60 → fps: 30

# 2. Send SIGHUP to apply changes
kill -HUP $(pgrep -f server_core)

# 3. Server restarts with new config - no manual restart needed
```
