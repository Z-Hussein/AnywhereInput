# Installation Guide

## Install from PyPI (Recommended for all platforms)

The easiest way to install on any OS with Python 3.9+:

```bash
pip install anywhereinput
anywhereinput --tunnel cloudflare   # or: tailscale, pinggy, zrok2, local
```

### What gets installed

| Package | What It Does | System Pre-requisites |
|---------|-------------|-----------------------|
| **pyautogui** | Keyboard/mouse automation | Linux: `libx11-dev libxrandr-dev` |
| **aiohttp** | HTTP server + WebSocket | None |
| **requests** | Tunnel provider helpers | None |
| **qrcode[pil]** | QR code generation for sharing | None |
| **mss** | Screen capture (X11/Wayland/Win/mac) | None |
| **Pillow** | JPEG encoding for screen stream | Linux: `libjpeg-dev zlib1g-dev` |

> 💡 **Ubuntu/Debian:** Use the pipx method below — it handles system dependencies correctly.
> **Windows/macOS:** Everything installs automatically via pip.

### Upgrading

```bash
pip install --upgrade anywhereinput
```

---

## Platform-Specific Instructions

### Windows

#### Quick Start (Automatic)
1. Download and extract the repository to any folder (e.g., `C:\Tools\AnywhereInput`)
2. Run `scripts\windows\setup.bat` (right-click → **Run as Administrator**)
3. Wait for dependencies to install (~1-2 minutes)
4. Run `scripts\windows\run.bat` to start

#### Manual Setup
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
pip install anywhereinput
anywhereinput --tunnel cloudflare
```

> **Pre-requirement:** Install Python 3.9+ from [python.org](https://www.python.org/downloads/) — make sure to check **"Add Python to PATH"** during installation.

### Ubuntu/Debian (Linux)

#### Recommended: pipx (isolated install, handles system deps)
```bash
sudo apt update
sudo apt install -y pipx
pipx ensurepath   # adds ~/.local/bin to PATH
```
Open a new terminal, then:
```bash
pipx install anywhereinput
anywhereinput --tunnel cloudflare
```

> **Why pipx?** It installs the package in its own virtualenv, keeping system Python clean. No `sudo pip`, no dependency conflicts with other tools.

#### Alternative: venv + pip (requires manual system deps)
```bash
# System libs for Pillow JPEG encoding and pyautogui X11 capture
sudo apt install -y libjpeg-dev zlib1g-dev libxrandr-dev
python3 -m venv .venv
source .venv/bin/activate
pip install anywhereinput
anywhereinput --tunnel cloudflare
```

#### If pipx reports existing files / ModuleNotFoundError
```bash
rm -f ~/.local/bin/anywhereinput ~/.local/bin/anywhereinput-server
pipx install --force anywhereinput
anywhereinput --version
```

### Arch Linux / CachyOS

#### Recommended: pipx (isolated install)
```bash
sudo pacman -S python-pipx
pipx ensurepath   # adds ~/.local/bin to PATH
```
Open a new terminal, then:
```bash
pipx install anywhereinput
anywhereinput --tunnel cloudflare
```

#### Alternative: venv + pip (requires manual system deps)
```bash
# System libs for Pillow JPEG encoding, pyautogui X11 capture, and XRandR
sudo pacman -S python python-pip libjpeg-turbo zlib libxrandr
python3 -m venv .venv
source .venv/bin/activate
pip install anywhereinput
anywhereinput --tunnel cloudflare
```

> **CachyOS:** Works identically — CachyOS is Arch-based and uses the same packages and pacman commands.

### macOS

#### Quick Start
```bash
chmod +x scripts/unix/setup.sh scripts/unix/run.sh
./scripts/unix/setup.sh
./scripts/unix/run.sh
```

#### Manual Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install anywhereinput
anywhereinput --tunnel cloudflare
```

> **Note:** macOS uses the same Linux scripts since Python packaging is identical. The only difference may be screen capture permissions — grant **"Screen Recording"** access to Terminal in **System Settings > Privacy & Security**.

---

## Tunnel Provider Requirements

| Provider | Additional Software Needed |
|---|---|
| **Cloudflare** | Auto-downloads on first run (`cloudflared` binary, ~30MB) |
| **Tailscale** | Install client: `curl -fsSL https://tailscale.com/install.sh \| sh` then `sudo tailscaled start && sudo tailscale up` |
| **Pinggy.io** | Requires OpenSSH (`ssh` command). Pre-installed on Windows 10+, macOS, and all Linux distros |
| **Zrok2** | Install from [docs.zrok.io](https://docs.zrok.io/docs/installation/) and run `zrok2 enable <TOKEN>` |
| **Local only** | Nothing — connects over your LAN/WiFi network |

---

## Headless / Server-Only Mode

`anywhereinput --app` requires a desktop display (X11 on Linux, Windows GUI, or macOS). On headless servers accessed via SSH:

```bash
# No GUI needed — the server runs fine in terminal-only mode
anywhereinput --tunnel cloudflare   # or tailscale / pinggy / zrok2 / local
```

The server still accepts browser connections from any device that can reach the tunnel URL. The `--app` GUI is optional and only needed for token management via a visual window.

### Running as a systemd Service (Linux)

A template service file is provided in `contrib/` for running AnywhereInput as a background daemon:

```bash
# Install the service unit
sudo cp contrib/anywhereinput-server.service /etc/systemd/system/
sudo systemctl daemon-reload

# Start as your user (replace $USER with your username)
sudo systemctl enable --now anywhereinput@$USER

# Check status and logs
systemctl status anywhereinput@$USER
journalctl -u anywhereinput@$USER -f

# Stop / restart
sudo systemctl stop anywhereinput@$USER
sudo systemctl restart anywhereinput@$USER
```

The `%i` in the service file expands to your username, so `anywhereinput@USERNAME` runs under user `USERNAME`. The server starts with `--tunnel local` by default — edit `ExecStart` in the service file to change the tunnel provider.

---

## Install from Source (for development or scripts)

```bash
git clone https://github.com/Z-Hussein/AnywhereInput.git
cd AnywhereInput
pip install -e .
```

---

## Desktop Admin App (Optional GUI)

```bash
pip install anywhereinput[app]    # includes PyQt6
anywhereinput --app               # visual GUI for token management
```

> ⚠️ Requires a desktop display (X11/Wayland on Linux, or native Windows/macOS). On headless servers, skip `--app` — the server and CLI work fine without it.

---

## Requirements

- **Python**: 3.9, 3.10, 3.11, 3.12, 3.13, or 3.14
- **OS**: Windows 10/11, Linux (Ubuntu 20+, Debian, Arch, Fedora, etc.), or macOS 12+
- **GPU**: Integrated or dedicated GPU for screen capture (AMD GPUs supported)
- **Internet**: Required for tunnel providers; local mode works offline
