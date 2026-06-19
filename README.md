# AnywhereInput

> Control your Windows, Linux, or macOS PC from any phone, tablet, or browser — no app install, no account, no cloud dependency.

[Demo GIF placeholder — 10s setup-to-control] `feel free to add ;) `

## Why This Exists

Every remote control tool forces you through something:
- **TeamViewer / Chrome Remote Desktop** → Account creation, bloated client, corporate telemetry
- **VNC / RDP** → Port forwarding, firewall rules, VPN setup
- **Dedicated apps** → App store, permissions, updates

AnywhereInput does none of that. Open a browser, paste a link, control your PC. The server is yours. The connection is direct. The client is the web.

## Compare

|             | AnywhereInput | TeamViewer | Chrome RDP | VNC        |
| ----------- | ------------- | ---------- | ---------- | ---------- |
| App install | ❌ None        | ✅ Required | ✅ Required | ✅ Required |
| Account     | ❌ None        | ✅ Required | ✅ Google   | ❌ None     |
| Setup time  | ~30 sec       | ~5 min     | ~3 min     | ~10 min    |
| Open source | ✅ Yes         | ❌ No       | ❌ No       | ✅ Partial  |

This isn't about bashing competitors — it's about showing you why AnywhereInput is worth trying first. No sign-ups, no installs, no waiting. Just a browser, a link, and control.

## What It Does

| Feature | Detail |
|---------|--------|
| 🖱️ **Mouse** | Move, click (left/right), double-click, scroll |
| ⌨️ **Keyboard** | Single keys, hotkey combos (Ctrl+C, Ctrl+Alt+Del, etc.) |
| 🌐 **Access** | Same WiFi (local IP) or anywhere (ngrok tunnel) |
| 🔒 **Security** | Token-based WebSocket auth, auto-rotated per session |
| 📱 **Client** | Any modern browser — Android, iOS, tablet, another laptop |
| ⚡ **Performance** | ~60Hz mouse updates, <50ms local / <200ms remote |

## Quick Start (60 Seconds)

### Windows
```bash
start_with_ngrok.bat
```
Copy the URL. Open it on your phone. Done.

The script will:
- Auto-find Python on your system (or create a virtual environment)
- Install dependencies automatically
- Search for ngrok across your system
- Guide you through ngrok setup (first time only)
- Generate a secure access token
- Start the server and display the public URL

### Linux / macOS
```bash
chmod +x setup_linux.sh start_with_ngrok.sh
./start_with_ngrok.sh
```
Copy the URL. Open it on your phone. Done.

The script will:
- Auto-detect your Linux distribution (Ubuntu, Fedora, Arch, macOS, etc.)
- Install Python and venv if needed
- Create and activate virtual environment
- Install dependencies automatically
- Search for ngrok on your system
- Start the server and display the public URL

### Manual Setup (If You Prefer)

**Windows:**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python launch_with_ngrok.py
```

**Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python launch_with_ngrok.py
```

### Connect from Your Device

1. Open your browser on any device
2. Paste the URL displayed in the terminal
3. Enter the access token (displayed in terminal)
4. Tap **Connect**
5. Use the touchpad to control your PC

## How It Works

- Your PC server runs locally on port 8080
- ngrok creates a secure HTTPS tunnel to your server
- The public URL is displayed in the terminal
- Your device connects through the ngrok tunnel

## How to Use

### Touchpad Controls

| Action | How |
|--------|-----|
| Move cursor | Drag on the touchpad area |
| Left click | Tap touchpad or tap Left Click button |
| Right click | Tap Right Click button |
| Double click | Tap Double Click button |
| Scroll | Scroll Up / Down buttons |
| Keyboard | Tap Keyboard, type, send |
| Hotkeys | Pre-mapped: Ctrl+Alt+Del, etc. |
| Center mouse | Tap Center button |

### Buttons

- **Left Click** — Single left mouse click
- **Right Click** — Single right mouse click
- **Double Click** — Double-click action
- **Scroll Up/Down** — Scroll on the PC
- **Center** — Move mouse to center of screen
- **Keyboard** — Send individual key presses
- **Ctrl+Alt+Del** — Send system keyboard shortcut

## Architecture

```
┌─────────────────┐      WebSocket      ┌─────────────────┐
│  Your Device    │ ◄─────────────────► │  Your PC        │
│  (Any Browser)  │    (Token Auth)     │  (Python Server)│
└─────────────────┘                     └─────────────────┘
                            │
                            ▼
                    ┌─────────────────┐
                    │  ngrok Tunnel   │  (Optional, for remote)
                    │  (HTTPS/WSS)    │
                    └─────────────────┘
```

### Server (Your PC)

- **Framework**: aiohttp (async HTTP/WebSocket server)
- **Mouse Control**: pyautogui library
- **Authentication**: Token-based WebSocket handshake
- **Port**: 8080 (configurable)

### Client (Any Browser)

- **Interface**: HTML5 + CSS3 (responsive design)
- **Communication**: WebSocket protocol
- **Input Handling**: Pointer Events API
- **Commands**: JSON-based command protocol

## Supported Commands

### Mouse Move
```json
{
  "type": "move",
  "mode": "relative",
  "dx": 10,
  "dy": 15
}
```

### Mouse Click
```json
{
  "type": "click",
  "button": "left",
  "clicks": 1
}
```

### Scroll
```json
{
  "type": "scroll",
  "amount": 120
}
```

### Key Press
```json
{
  "type": "key",
  "key": "enter"
}
```

### Hotkey
```json
{
  "type": "hotkey",
  "keys": ["ctrl", "c"]
}
```

## Network Modes

### Local Network (Same WiFi)
```
http://<your-pc-ip>:8080/
```
No setup needed, just connect to your PC's local IP address.

### Remote Access (Different Networks)
```
https://abc123def456.ngrok.io/
```
Requires ngrok authentication token. Run `python launch_with_ngrok.py`.

## Security

⚠️ **Designed for personal/trusted use. Not hardened for production.**

### Token Generation
- A new access token is **auto-generated** on each server start
- Token is saved to `trusted_tokens.json` (auto-ignored by `.gitignore`)
- Never commit tokens to version control

### Token Rotation
While the app is running, press **Ctrl+N** (or type `n` + Enter) to:
- Restart the server
- Generate a new token
- Display the new token in the console

This is useful for security if you suspect token compromise.

### What You Get
- Auto-generated token on every server start
- Token rotation via Ctrl+N (or `n` + Enter)
- HTTPS/WSS encryption when using ngrok
- No data stored on external servers

### Known Limitations
- Single token per session
- No rate limiting
- No IP whitelist
- No logging and monitoring

If you need enterprise-grade security, add a reverse proxy with OAuth or mTLS.

## Requirements

| Component | Minimum |
|-----------|---------|
| Server OS | Windows 10/11, Linux, macOS |
| Python | 3.9, 3.10, 3.11 |
| Client | Any browser with WebSocket + Pointer Events |
| Remote access | Free ngrok account |
| Internet | Required on both devices for remote access |

## File Structure

```
.
├── start_with_ngrok.bat        # Easy launcher for Windows (recommended!)
├── start_with_ngrok.sh         # Easy launcher for Linux/macOS (recommended!)
├── setup_windows.bat           # Windows setup script
├── setup_linux.sh              # Linux/macOS setup script
├── launch_with_ngrok.py        # Python launcher script for ngrok
├── secure_mouse_server.py      # Main WebSocket server
├── android_controller.html     # Web UI for browser
├── requirements.txt            # Python dependencies (pinned versions)
├── .gitignore                  # Ignores tokens & virtual env
├── LICENSE                     # MIT License
└── README.md                   # This file
```

## Configuration

### Change Server Port
Edit the `HTTP_PORT` variable in `secure_mouse_server.py`:
```python
HTTP_PORT = 8080  # Change this to your desired port
```

### Add More Tokens
Edit `trusted_tokens.json` to add additional access tokens:
```json
{
  "token_generated_and_filled_automatically_with_each_start": {
    "name": "phone-1",
    "created": "auto-generated",
    "permissions": ["move", "click", "scroll", "keyboard"]
  },
  "your_new_token_here": {
    "name": "phone-2",
    "created": "2026-06-18",
    "permissions": ["move", "click", "scroll", "keyboard"]
  }
}
```

### Skip ngrok Search
Set `NGROK_PATH` to skip the ngrok search:

**Windows:**
```powershell
set NGROK_PATH=C:\path	o
grok.exe
start_with_ngrok.bat
```

**Linux / macOS:**
```bash
export NGROK_PATH=/usr/local/bin/ngrok
./start_with_ngrok.sh
```

## Performance

- **Local Network**: <50ms latency typical
- **Remote (ngrok)**: 100-200ms depending on network
- **Mouse Update Rate**: ~60 Hz
- **Screen Compatibility**: Works with any resolution

## Troubleshooting

| Problem | Fix |
|---------|-----|
| ngrok URL not showing | Verify auth token at [dashboard.ngrok.com](https://dashboard.ngrok.com/get-started/your-authtoken) — paste without `$` prefix |
| Can't connect from device | Check firewall allows port 8080; test `http://localhost:8080` on the PC first; verify ngrok tunnel is active for remote access |
| Connection timeout | Verify both devices have internet; check ngrok account status; verify ngrok auth token hasn't expired |
| Mouse moving too slow / lag | Check your network latency; reduce the distance of drag movements on touchpad; try connecting to a closer server or local network |

## Limitations

- **Server:** Cross-platform (Windows, Linux, macOS)
- **Client:** Browser must support WebSocket and Pointer Events
- **Performance:** Network latency affects responsiveness
- **ngrok:** Free tier has bandwidth limitations
- **Bandwidth:** Not suitable for high-bandwidth activities (gaming, video)
- **Security:** Not hardened for production or untrusted networks

## Roadmap / Contributing

- [ ] QR code display in terminal for instant mobile scan
- [ ] iOS Safari optimization
- [ ] File transfer (drag & drop)
- [ ] Docker image for one-liner deploy
- [ ] Custom domain support (replace ngrok)
- [ ] Long tap for right click on touchpad

PRs welcome!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add your feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

For issues, questions, or suggestions, open an issue on GitHub and check existing issues for solutions.

## Platform Support

- ✅ **Windows 10, 11** (server)
- ✅ **Linux** (Ubuntu, Debian, Fedora, Arch, etc.) (server)
- ✅ **macOS** (Intel & Apple Silicon)** (server)
- ✅ **Android 6+** (client browser)
- ✅ **iOS / iPadOS** (client browser)
- ✅ **Any modern browser** (client)
- ✅ **Local WiFi networks**
- ✅ **ngrok remote tunneling**

## License

MIT License — See [LICENSE](LICENSE) for details.

## Acknowledgments

Built with:
- [aiohttp](https://github.com/aio-libs/aiohttp) — Async HTTP framework
- [pyautogui](https://github.com/asweigart/pyautogui) — Mouse and keyboard automation
- [ngrok](https://ngrok.com) — Public tunneling service

---

**Made with ❤️ for remote control enthusiasts**
