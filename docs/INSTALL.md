# Installation Guide

## Install from PyPI (Recommended for all platforms)

The easiest way to install on any OS with Python 3.9+:

```bash
pip install anywhereinput
anywhereinput --tunnel cloudflare
```

This installs the latest published release from https://pypi.org/project/anywhereinput/

To upgrade later:
```bash
pip install --upgrade anywhereinput
```

### Ubuntu: install with pipx (recommended for CLI isolation)

```bash
sudo apt update
sudo apt install -y pipx
pipx ensurepath
```

Open a new terminal, then:

```bash
pipx install anywhereinput
anywhereinput --tunnel cloudflare
```

Upgrade later:

```bash
pipx upgrade anywhereinput
```

If `pipx install anywhereinput` reports existing files in `~/.local/bin` and
`anywhereinput` still fails with `ModuleNotFoundError`, remove stale wrappers
from older `pip --user` installs and reinstall with pipx:

```bash
rm -f ~/.local/bin/anywhereinput ~/.local/bin/ai-server
pipx install --force anywhereinput
anywhereinput --version
```

---

## Install from Source (for development or scripts)

```bash
git clone https://github.com/your-repo/AnywhereInput.git
cd AnywhereInput
pip install -e .
```

---

## Windows (scripts)

### Quick Start (Automatic)
1. Download and extract the repository to any folder (e.g., `C:\Tools\AnywhereInput`)
2. Run `scripts\windows\setup.bat` (right-click → **Run as Administrator**)
3. Wait for dependencies to install (~1-2 minutes)
4. Run `scripts\windows\run.bat` to start

### Manual Setup
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
pip install -e .
anywhereinput --tunnel cloudflare
```

## Linux

### Quick Start
```bash
chmod +x scripts/unix/setup.sh scripts/unix/run.sh
./scripts/unix/setup.sh
./scripts/unix/run.sh
```

### Manual Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
anywhereinput --tunnel cloudflare
```

## macOS

### Quick Start
```bash
chmod +x scripts/linux/setup.sh scripts/linux/run.sh
./scripts/linux/setup.sh
./scripts/linux/run.sh
```

### Manual Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
anywhereinput --tunnel cloudflare
```

> **Note:** macOS uses the same Linux scripts since Python packaging is identical. The only difference may be screen capture permissions — grant "Screen Recording" access to Terminal in **System Settings > Privacy & Security**.

## Tunnel Provider Requirements

| Provider | Additional Software Needed |
|---|---|
| **Cloudflare** | Auto-downloads on first run (cloudflared binary, ~30MB) |
| **Tailscale** | Install client: `curl -fsSL https://tailscale.com/install.sh \| sh` then `sudo tailscaled start && sudo tailscale up` |
| **Pinggy.io** | Requires OpenSSH (`ssh` command). Pre-installed on Windows 10+, macOS, and all Linux distros |
| **Zrok2** | Install from [docs.zrok.io](https://docs.zrok.io/docs/installation/) and run `zrok2 enable <TOKEN>` |
| **ngrok** | Download binary from [ngrok.com/download](https://ngrok.com/download) and configure authtoken via `ngrok config add-authtoken YOUR_TOKEN` |
| **Local only** | Nothing — connects over your LAN/WiFi network |

## Requirements
- **Python**: 3.9, 3.10, 3.11, or 3.12+
- **OS**: Windows 10/11, Linux (Ubuntu 20+, Debian, Arch, Fedora, etc.), or macOS 12+
- **GPU**: Integrated or dedicated GPU for screen capture (AMD GPUs supported)
- **One tunnel provider** installed and configured as needed above
# Installation Guide

## Install from PyPI (Recommended for all platforms)

The easiest way to install on any OS with Python 3.9+:

```bash
pip install anywhereinput
anywhereinput --tunnel cloudflare
```

This installs the latest published release from https://pypi.org/project/anywhereinput/

To upgrade later:
```bash
pip install --upgrade anywhereinput
```

### Ubuntu: install with pipx (recommended for CLI isolation)

```bash
sudo apt update
sudo apt install -y pipx
pipx ensurepath
```

Open a new terminal, then:

```bash
pipx install anywhereinput
anywhereinput --tunnel cloudflare
```

Upgrade later:

```bash
pipx upgrade anywhereinput
```

---

## Install from Source (for development or scripts)

```bash
git clone https://github.com/your-repo/AnywhereInput.git
cd AnywhereInput
pip install -e .
```

---

## Windows (scripts)

### Quick Start (Automatic)
1. Download and extract the repository to any folder (e.g., `C:\Tools\AnywhereInput`)
2. Run `scripts\windows\setup.bat` (right-click → **Run as Administrator**)
3. Wait for dependencies to install (~1-2 minutes)
4. Run `scripts\windows\run.bat` to start

### Manual Setup
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
pip install -e .
anywhereinput --tunnel cloudflare
```

## Linux

### Quick Start
```bash
chmod +x scripts/unix/setup.sh scripts/unix/run.sh
./scripts/unix/setup.sh
./scripts/unix/run.sh
```

### Manual Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
anywhereinput --tunnel cloudflare
```

## macOS

### Quick Start
```bash
chmod +x scripts/linux/setup.sh scripts/linux/run.sh
./scripts/linux/setup.sh
./scripts/linux/run.sh
```

### Manual Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
anywhereinput --tunnel cloudflare
```

> **Note:** macOS uses the same Linux scripts since Python packaging is identical. The only difference may be screen capture permissions — grant "Screen Recording" access to Terminal in **System Settings > Privacy & Security**.

## Tunnel Provider Requirements

| Provider | Additional Software Needed |
|---|---|
| **Cloudflare** | Auto-downloads on first run (cloudflared binary, ~30MB) |
| **Tailscale** | Install client: `curl -fsSL https://tailscale.com/install.sh \| sh` then `sudo tailscaled start && sudo tailscale up` |
| **Pinggy.io** | Requires OpenSSH (`ssh` command). Pre-installed on Windows 10+, macOS, and all Linux distros |
| **Zrok2** | Install from [docs.zrok.io](https://docs.zrok.io/docs/installation/) and run `zrok2 enable <TOKEN>` |
| **ngrok** | Download binary from [ngrok.com/download](https://ngrok.com/download) and configure authtoken via `ngrok config add-authtoken YOUR_TOKEN` |
| **Local only** | Nothing — connects over your LAN/WiFi network |

## Requirements
- **Python**: 3.9, 3.10, 3.11, or 3.12+
- **OS**: Windows 10/11, Linux (Ubuntu 20+, Debian, Arch, Fedora, etc.), or macOS 12+
- **GPU**: Integrated or dedicated GPU for screen capture (AMD GPUs supported)
- **One tunnel provider** installed and configured as needed above
