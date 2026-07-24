<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:667eea,100:764ba2&height=150&section=header&text=Installation%20Guide&fontSize=50&fontColor=ffffff&animation=fadeIn" alt="Installation Guide" />

</div>

# Installation Guide 🚀

Install from PyPI (recommended on all platforms):

```bash
pip install anywhereinput
anywhereinput --tunnel cloudflare   # or: tailscale, pinggy, zrok2, local
```

---

## ⚙️ Dependencies

| Package | Purpose | Notes |
|---------|---------|-------|
| **pyautogui** | Keyboard/mouse automation | Linux: needs libx11-dev, libxrandr-dev |
| **aiohttp** | HTTP server + WebSocket | None |
| **requests** | Tunnel helpers | None |
| **qrcode[pil]** | QR code generation | None |
| **mss** | Screen capture | None |
| **Pillow** | JPEG encoding for screen stream | Linux: needs libjpeg-dev, zlib1g-dev |

Optional for GUI: PyQt6 (`pip install anywhereinput[app]`).

### Upgrading

```bash
pip install --upgrade anywhereinput
```

---

## 🪟 Windows

### Quick start (automatic)

1. Extract repo to a folder (e.g., `C:\Tools\AnywhereInput`)
2. Run `scripts\windows\setup.bat` as Administrator
3. Wait for deps to install (~1-2 min)
4. Run `scripts\windows\run.bat`

### Manual setup

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
pip install anywhereinput
anywhereinput --tunnel cloudflare
```

Python 3.9+ required — make sure **"Add Python to PATH"** is checked during installer.

---

## 🐧 Ubuntu / Debian (Linux)

### Recommended: pipx

```bash
sudo apt update && sudo apt install -y pipx
pipx ensurepath
# Open a new terminal, then:
pipx install anywhereinput
anywhereinput --tunnel cloudflare
```

> 💡 pipx installs in its own venv so there's no dependency conflict with system Python.

### Alternative: venv + pip

```bash
sudo apt install -y libjpeg-dev zlib1g-dev libxrandr-dev
python3 -m venv .venv
source .venv/bin/activate
pip install anywhereinput
anywhereinput --tunnel cloudflare
```

If pipx complains about existing files:

```bash
rm -f ~/.local/bin/anywhereinput ~/.local/bin/anywhereinput-server
pipx install --force anywhereinput
```

---

## 🏛️ Arch Linux / CachyOS

### pipx (recommended)

```bash
sudo pacman -S python-pipx
pipx ensurepath
# New terminal:
pipx install anywhereinput
anywhereinput --tunnel cloudflare
```

### venv alternative

```bash
sudo pacman -S python python-pip libjpeg-turbo zlib libxrandr
python3 -m venv .venv
source .venv/bin/activate
pip install anywhereinput
anywhereinput --tunnel cloudflare
```

---

## 🍎 macOS

```bash
chmod +x scripts/unix/setup.sh scripts/unix/run.sh
./scripts/unix/setup.sh
./scripts/unix/run.sh
```

Or manual:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install anywhereinput
anywhereinput --tunnel cloudflare
```

> 📌 Grant **"Screen Recording"** access to Terminal in **System Settings > Privacy & Security** if the stream is blank.

---

## 🔒 Tunnel requirements

| Provider | What you need |
|----------|---------------|
| **Cloudflare** | Auto-downloads `cloudflared` on first run (~30MB) |
| **Tailscale** | Install client + `tailscale up` (free tier: 10 devices) |
| **Pinggy.io** | OpenSSH (pre-installed on all modern systems) |
| **Zrok2** | Install from docs.zrok.io, run `zrok enable <TOKEN>` |
| **Local only** | Nothing — works on LAN/WiFi |

---

## 🖥️ Headless / server-only mode

`--app` requires a desktop display. On headless servers via SSH:

```bash
anywhereinput --tunnel cloudflare
# (or tailscale / pinggy / zrok2 / local)
```

The server accepts browser connections regardless. `--app` is optional for token management.

### systemd service (Linux)

A template is in `contrib/`:

```bash
sudo cp contrib/anywhereinput-server.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now anywhereinput@$USER
systemctl status anywhereinput@$USER
journalctl -u anywhereinput@$USER -f
```

`%i` expands to your username. Default tunnel is `local` — edit `ExecStart` to change it.

---

## 📦 Install from source

```bash
git clone https://github.com/Z-Hussein/AnywhereInput.git
cd AnywhereInput
pip install -e .
```

---

## ✅ Requirements

- **Python**: 3.9+ (tested up through 3.14)
- **OS**: Windows 10/11, Linux (Ubuntu 20+, Debian, Arch, Fedora, etc.), macOS 12+
- **GPU**: Integrated or dedicated GPU for screen capture (AMD GPUs supported)
- **Internet**: For tunnel providers; local mode works offline
