# Remote Mouse Controller

Control your Windows PC's mouse and keyboard from an Android phone anywhere, anytime. A lightweight cross-network remote control application using WebSocket and ngrok tunneling.

## Features

✨ **Cross-Network Support** — Control your PC from anywhere using ngrok tunneling  
🚀 **Responsive Controls** — Low-latency mouse movements and keyboard input  
🔐 **Token-Based Authentication** — Secure WebSocket connections with trusted token verification  
📱 **Web-Based Interface** — No app installation needed, just open in your browser  
⚡ **Fast Performance** — Optimized for snappy responsiveness with minimal delay  
🖱️ **Full Input Support** — Mouse movements, clicks, scrolling, and keyboard hotkeys  

## Requirements

- **Windows PC** with Python 3.9+
- **Android device** with a modern browser
- **ngrok account** (free tier available) for remote access
- **Internet connection** on both devices

## Quick Start

### Windows Users

#### Easiest Method: Batch Launcher

```powershell
start_with_ngrok.bat
```

This script will:
- Auto-find Python on your system (or create a virtual environment)
- Install dependencies automatically
- Search for ngrok across your system
- Guide you through ngrok setup (first time only)
- Generate a secure access token
- Start the server and display the public URL

**That's it!** Copy the URL shown and open it on your Android device.

#### Manual Setup (Optional)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python launch_with_ngrok.py
```

### Linux / macOS Users

#### Easiest Method: Shell Script

```bash
chmod +x setup_linux.sh start_with_ngrok.sh
./start_with_ngrok.sh
```

This script will:
- Auto-detect your Linux distribution (Ubuntu, Fedora, Arch, macOS, etc.)
- Install Python and venv if needed
- Create and activate virtual environment
- Install dependencies automatically
- Search for ngrok on your system
- Start the server and display the public URL

#### Manual Setup (Optional)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python launch_with_ngrok.py
```

### Connect from Android Device

1. Open your browser on Android
2. Paste the URL displayed in the terminal
3. Enter the access token (displayed in terminal)
4. Tap **Connect**
5. Use the touchpad to control your PC

## Setup for Remote Access (ngrok)

### 1. Get Your ngrok Auth Token (One-time setup)

1. Create a free account at https://ngrok.com
2. Copy your authtoken from https://dashboard.ngrok.com/get-started/your-authtoken
3. Run the launcher and paste the token when prompted:
   ```powershell
   start_with_ngrok.bat
   # or
   python launch_with_ngrok.py
   ```

### 2. Use ngrok Environment Variable (Optional)

Set `NGROK_PATH` to skip the ngrok search:
```powershell
set NGROK_PATH=C:\path\to\ngrok.exe
start_with_ngrok.bat
```

### How It Works

- Your Windows server runs locally on port 8080
- ngrok creates a secure HTTPS tunnel to your server
- The public URL is displayed in the terminal
- Your Android device connects through the ngrok tunnel

## File Structure

```
.
├── start_with_ngrok.bat        # Easy launcher for Windows (recommended!)
├── start_with_ngrok.sh         # Easy launcher for Linux/macOS (recommended!)
├── setup_windows.bat           # Windows setup script
├── setup_linux.sh              # Linux/macOS setup script
├── launch_with_ngrok.py        # Python launcher script for ngrok
├── secure_mouse_server.py      # Main WebSocket server
├── android_controller.html     # Web UI for Android browser
├── requirements.txt            # Python dependencies (pinned versions)
├── .gitignore                  # Ignores tokens & virtual env
├── LICENSE                     # MIT License
└── README.md                   # This file
```

## Access Token & Security

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

## Configuration

### Add More Tokens

Edit `trusted_tokens.json` to add additional access tokens:

```json
{
  "token_generated_and_filled_automatilly_with_each_start": 
  {
    "name": "android-client",
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

### Change Server Port

Edit the `HTTP_PORT` variable in `secure_mouse_server.py`:

```python
HTTP_PORT = 8080  # Change this to your desired port
```

## Usage

### Touchpad Controls

- **Drag** — Move the mouse pointer
- **Tap** — Left click
- **Long tap** — Right click (coming soon)

### Buttons

- **Left Click** — Single left mouse click
- **Right Click** — Single right mouse click
- **Double Click** — Double-click action
- **Scroll Up/Down** — Scroll on the PC
- **Center** — Move mouse to center of screen
- **Keyboard** — Send individual key presses
- **Ctrl+Alt+Del** — Send system keyboard shortcut

## Network Modes

### Local Network (Same WiFi)

```
http://PC_ip_Adresse:8080/
```

No setup needed, just connect to your PC's local IP address.

### Remote Access (Different Networks)

```
https://abc123def456.ngrok.io/
```

Requires ngrok authentication token. Run `python launch_with_ngrok.py`.

## Architecture

### Server (Windows PC)

- **Framework**: aiohttp (async HTTP/WebSocket server)
- **Mouse Control**: pyautogui library
- **Authentication**: Token-based WebSocket handshake
- **Port**: 8080 (configurable)

### Client (Android Browser)

- **Interface**: HTML5 + CSS3 (responsive design)
- **Communication**: WebSocket protocol
- **Input Handling**: Pointer Events API
- **Commands**: JSON-based command protocol

## Supported Mouse Commands

```json
{
  "type": "move",
  "mode": "relative",  // or "absolute"
  "dx": 10,
  "dy": 15
}
```

```json
{
  "type": "click",
  "button": "left",    // or "right"
  "clicks": 1
}
```

```json
{
  "type": "scroll",
  "amount": 120  // positive = up, negative = down
}
```

```json
{
  "type": "key",
  "key": "enter"
}
```

```json
{
  "type": "hotkey",
  "keys": ["ctrl", "c"]
}
```

## Troubleshooting

### ngrok URL Not Showing

1. Check your ngrok auth token is correct
2. Visit https://dashboard.ngrok.com/get-started/your-authtoken
3. Make sure token is pasted without the `$` prefix

### Can't Connect from Android

1. Verify your server is running: `python secure_mouse_server.py`
2. Check firewall allows port 8080
3. Try opening `http://localhost:8080` on the PC first
4. For remote access, verify ngrok tunnel is active

### Mouse Moving Too Slow

This shouldn't happen with the current optimized settings. If it does:

1. Check your network latency
2. Reduce the distance of drag movements on touchpad
3. Try connecting to a closer server or local network

### Connection Timeout

1. Make sure both PC and Android device have internet
2. Check if ngrok account is still active
3. Verify ngrok auth token hasn't expired

## Performance

- **Local Network**: <50ms latency typical
- **Remote (ngrok)**: 100-200ms depending on network
- **Mouse Update Rate**: ~60 Hz
- **Screen Compatibility**: Works with any resolution

## Security

⚠️ **Important**: This project is designed for personal use with trusted devices.

- Uses token-based authentication
- WebSocket connections validated before commands processed
- HTTPS/WSS encryption with ngrok
- No sensitive data stored locally

For production use, consider:
- More robust authentication (OAuth, JWT)
- Rate limiting on commands
- Logging and monitoring
- IP whitelisting

## Limitations

- **Server:** Cross-platform (Windows, Linux, macOS)
- **Client:** Android browser must support WebSocket and Pointer Events
- **Performance:** Network latency affects responsiveness
- **ngrok:** Free tier has bandwidth limitations
- **Bandwidth:** Not suitable for high-bandwidth activities (gaming, video)

## Platform Support

- ✅ **Windows 10, 11** (server)
- ✅ **Linux** (Ubuntu, Debian, Fedora, Arch, etc.) (server)
- ✅ **macOS** (Intel & Apple Silicon) (server)
- ✅ **Android 6+** (client browser)
- ✅ **Python 3.9, 3.10, 3.11**
- ✅ **Local WiFi networks**
- ✅ **ngrok remote tunneling**

## License

MIT License — See LICENSE file for details

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add your feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

## Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check existing issues for solutions
- Review the troubleshooting section above

## Acknowledgments

Built with:
- [aiohttp](https://github.com/aio-libs/aiohttp) — Async HTTP framework
- [pyautogui](https://github.com/asweigart/pyautogui) — Mouse and keyboard automation
- [ngrok](https://ngrok.com) — Public tunneling service

---

**Made with ❤️ for remote control enthusiasts**
