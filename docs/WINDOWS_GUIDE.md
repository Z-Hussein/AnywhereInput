# Windows Complete Guide

## 1. Prerequisites

### Install Python 3.9+
1. Download from [python.org/downloads](https://www.python.org/downloads/)
2. Run the installer - **check "Add Python to PATH"** before clicking Install
3. Verify: open a new Command Prompt or PowerShell and run:
   ```cmd
   python --version
   pip --version
   ```

### Required System Components (pre-installed on modern Windows)
- **OpenSSH Client** - used by Pinggy tunnel (built into Windows 10 21H1+): `ssh -V` to verify
- **.NET Desktop Runtime** - required by pyautogui for screen capture: [download](https://dotnet.microsoft.com/download/dotnet/)
- **Graphics drivers** - ensure your GPU driver is up to date for screen capture

---

## 2. Quick Start (5 minutes)

```powershell
# 1. Extract AnywhereInput anywhere, e.g.:
C:\Tools\AnywhereInput

# 2. Open Command Prompt or PowerShell in that folder and run:
scripts\windows\setup.bat

# 3. After setup completes, start the server:
scripts\windows\run.bat
```

You'll see a menu - pick a tunnel provider, get a URL on your phone, enter the token, and connect. 🎉

---

## 3. Tunnel Providers

| # | Provider | Free? | Account? | Install Needed? | Best For |
|---|----------|-------|----------|-----------------|----------|
| [1] | **Cloudflare** ✅ Recommended | Yes | No | Auto-downloaded | Fastest, most reliable |
| [2] | Tailscale | 10 devices | Yes | [Install script](https://tailscale.com/download/windows) | Same-network access |
| [3] | Pinggy.io | Yes (60min/session) | No | None (uses `ssh`) | Quick no-setup access |
| [4] | Zrok2 | 5GB/day | Yes | [Installer](https://docs.zrok.io/docs/installation/) | Privacy-focused |
| [5] | Local only | Yes | No | None | Same WiFi network only |

### Tunnel Setup Details

#### Cloudflare (Auto - no setup needed)
Just select it in the menu. `cloudflared.exe` downloads automatically on first use (~30MB). Stored in the project root.

#### Tailscale
```powershell
# Install from https://tailscale.com/download/windows
# Open PowerShell and run:
tailscale up
# Follow the browser auth flow. Verify:
tailscale status
```
Both your PC and phone must be on the same tailnet. AnywhereInput will display your server's `100.x.x.x` tailnet IP - connect to `http://<IP>:8008` directly from any device on the tailnet.

#### Pinggy.io
No setup needed - uses your built-in `ssh`. Session expires after 60 minutes, no account required.

#### Zrok2
```powershell
# Install: https://docs.zrok.io/docs/installation/
# Sign up at https://account.zrok.io/signup
zrok enable <YOUR_TOKEN>
```

---

## 4. Daily Usage

### Standard Launch
```cmd
scripts\windows\run.bat
```
Interactive menu - pick your tunnel provider each time.

### Direct Launch (skip the menu)
| File | Tunnel |
|------|--------|
| `launch_cloudflare.bat` | Cloudflare |
| `launch_tailscale.bat` | Tailscale |
| `launch_pinggy.bat` | Pinggy.io |
| `launch_zrok2.bat` | Zrok2 |
| `launch_local.bat` | Local only |

Just double-click or run: `scripts\windows\launch_cloudflare.bat`

### Stopping the Server
Press **Ctrl+C** in the terminal. You'll see `"✅ Server stopped"`.

### Rotating the Access Token
Press **`n`** (the letter n) while the server is running. All existing connections are dropped and a new token is generated.

### Configuration Files
Use the `config` command to generate and manage reference config files:

```cmd
anywhereinput config list      # List available configs
anywhereinput config init      # Generate default config files
anywhereinput config view      # Show contents in terminal
anywhereinput config edit      # Open in your editor
```

---

## 5. Command-Line Options

```cmd
anywhereinput --host 127.0.0.1 --port 8008 --fps 120 --quality 40 --scale 0.7 --tunnel cloudflare
```

| Flag | Default | Description |
|------|---------|-------------|
| `--host` | `127.0.0.1` | Bind address (use `127.0.0.1` to restrict to localhost) |
| `--port` | `8008` | HTTP port |
| `--fps` | `120` | Screen capture FPS (1–120) |
| `--quality` | `40` | JPEG quality 1–95 |
| `--scale` | `0.7` | Stream scale factor (0.1=small, 1.0=full) |
| `--no-capture` | off | Disable screen capture (test connectivity only) |
| `--monitor` | `0` | Fixed monitor index (0=auto-track cursor) |

---

## 6. Connecting from Your Phone

1. Open the server and note the **URL** and **Token**
2. On your phone, open Chrome/Safari and navigate to the URL
3. Enter the token and tap **Connect**
4. Use the touchpad area to move/click, keyboard button for typing, scroll buttons for scrolling
5. Tap anywhere on the live screen stream to move cursor there

### Touchpad Controls
| Action | How |
|--------|-----|
| Move cursor | Drag on the touchpad area |
| Left click | Tap (tap-to-click) or Left Click button |
| Right click | Long-press touchpad (600ms) or Right Click button |
| Double click | Double Click button |
| Scroll | Two-finger drag on touchpad or Scroll buttons |

---

## 7. Troubleshooting

### "Python not found"
Reinstall Python - ensure **"Add Python to PATH"** is checked during setup. Then open a **new** terminal window.

### "pip install failed" / virtual environment errors
Run `scripts\windows\setup.bat` as Administrator (right-click → Run as Administrator).

### Screen capture shows black screen
- Update your GPU drivers
- Run `run.bat` as Administrator
- Test connectivity with the `--no-capture` flag

### Cloudflared download fails
Manually download from [github.com/cloudflare/cloudflared](https://github.com/cloudflare/cloudflared/releases/latest) and place `cloudflared.exe` in the project root folder.

### Tailscale not connecting
- Install from https://tailscale.com/download/windows
- Run `tailscale up` and follow the browser auth flow
- Verify: `tailscale status` shows you as connected
- Both devices must be on the same tailnet

### Server won't stop (Ctrl+C hangs)
The terminal may need focus. Click inside the window first, then press Ctrl+C. As a last resort, find and kill the process:
```powershell
# Find the PID
Get-Process anywhereinput
# Kill it
Stop-Process -Id <PID>
```

### "Port already in use"
Another instance is running. Kill it (see above) or start with `--port 9009` (or any free port).

---

## 8. API Reference

For developers building custom clients:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/ws` | WebSocket connection (send `{"type": "auth", "token": "..."}`) |
| GET | `/api/screen` | Screen dimensions → `{"width": 1920, "height": 1080}` |
| GET | `/api/engine` | Input + screen engine status (`state`, `failure_count`, `screen_engine`) |
| GET | `/api/monitors` | Monitor info → `{"monitors": [...], "current": 0, "auto_track": true}` |
| POST | `/api/monitor/{index}` | Switch capture monitor |
| GET | `/api/tokens` | List all tokens (masked values) |
| POST | `/api/tokens` | Create a new token |
| PATCH | `/api/tokens/{token}` | Update token name or permissions |
| DELETE | `/api/tokens/{token}` | Revoke a token |
| GET | `/api/clients` | List connected WebSocket clients |

**WebSocket command format:**
```json
{
  "type": "move",
  "mode": "relative",
  "dx": 10,
  "dy": -5
}
```
Message types: `move`, `click`, `scroll`, `key`, `hotkey`, `mouse_down`, `mouse_up`, `screen_toggle`, `ping` (pong response).

Server may also emit `screen` frames, `screen_status` updates, and recovery errors (`capture_error`, `capture_engine_offline`).
