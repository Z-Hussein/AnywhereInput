<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:667eea,100:764ba2&height=150&section=header&text=Tunnel%20Providers&fontSize=50&fontColor=ffffff&animation=fadeIn" alt="Tunnel Providers" />

</div>

# Tunnel Provider Guide 🔒

## ☁️ Cloudflare Tunnel (Recommended)

| Detail | Value |
|--------|-------|
| **Cost** | Free |
| **Account** | Not required |
| **Setup** | Automatic download on first run |
| **Best for** | Fastest globally, random URLs, no signup |
| **Note** | URL changes every session |

### Debian / Ubuntu Setup

```bash
# cloudflared is auto-downloaded on first tunnel use - nothing to install manually
# If you want it upfront:
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared
chmod +x /usr/local/bin/cloudflared
cloudflared --version
```

### Arch Linux / CachyOS Setup

```bash
# cloudflared is in the AUR
yay -S cloudflared
# or
paru -S cloudflared
# Then verify:
cloudflared --version
```

### Windows Setup

```powershell
# cloudflared is auto-downloaded on first tunnel use - nothing to install manually
# If you want it upfront:
irm https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe -OutFile $env:USERPROFILE\cloudflared.exe
$env:PATH += ";$env:USERPROFILE"
cloudflared --version
```

---

## 🔗 Tailscale

| Detail | Value |
|--------|-------|
| **Cost** | Free (10 devices on free tier) |
| **Account** | Required (free at https://tailscale.com) |
| **Setup** | Install Tailscale, log in once — both server and client must be on the same tailnet |

### Debian / Ubuntu Setup

```bash
# 1. Install tailscaled via official script (works on Debian/Ubuntu/Fedora)
curl -fsSL https://tailscale.com/install.sh | sh

# 2. Log in to your account
sudo tailscaled start
sudo tailscale up

# 3. Verify connection
tailscale status
# You should see yourself listed with a 100.x.x.x address

# That's it - AnywhereInput will auto-detect your tailnet IP when you select Tailscale as the tunnel
```

### Arch Linux / CachyOS Setup

```bash
# tailscaled is in the official repos
sudo pacman -S tailscale
sudo systemctl enable --now tailscaled
sudo tailscale up
# Verify:
tailscale status
```

### Windows Setup

```powershell
# 1. Download and install Tailscale
irm https://tailscale.com/installers/tailscale-2.2.0.msi -OutFile $env:TEMP\tailscale.msi
msiexec /i $env:TEMP\tailscale.msi /quiet

# 2. Log in to your account (opens a browser window)
& "C:\Program Files\Tailscale\Tailscale.exe" auth

# Alternatively, from any terminal:
tailscale up

# 3. Verify connection
tailscale status
# You should see yourself listed with a 100.x.x.x address

# That's it - AnywhereInput will auto-detect your tailnet IP when you select Tailscale as the tunnel
```

---

## 🌐 Pinggy.io

| Detail | Value |
|--------|-------|
| **Cost** | Free (60-minute session timeout, no account needed) |
| **Account** | Not required |
| **Setup** | Requires OpenSSH client — built into Windows 10+, macOS, and all Linux distros |

> ℹ️ More info: [pinggy.io/help/ssh](https://pinggy.io/help/ssh)

### Debian / Ubuntu Setup

```bash
# SSH is pre-installed on virtually all Debian/Ubuntu systems. Verify:
ssh -V
# If not installed:
sudo apt install openssh-client   # Debian/Ubuntu
sudo dnf install openssh-clients   # Fedora/RHEL
```
That's all you need — AnywhereInput uses your existing `ssh` client to create the tunnel.

### Arch Linux / CachyOS Setup

```bash
# SSH is pre-installed on Arch. Verify:
ssh -V
# If not installed:
sudo pacman -S openssh
```

### Windows Setup

```powershell
# OpenSSH is built into Windows 10 (21H1+) and Windows 11:
ssh -V
# Should output something like: OpenSSH_for_Windows_9.x...

# If not installed, add it via Settings > Apps > Optional Features > Add "OpenSSH Client"
# Or from an elevated PowerShell:
Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0
```
That's all you need — AnywhereInput uses your existing `ssh` client to create the tunnel.

---

## 🛡️ Zrok2

| Detail | Value |
|--------|-------|
| **Cost** | Free (5GB/day on the public environment) |
| **Account** | Required (free at https://account.zrok.io/signup) |
| **Setup** | Sign up, get a token, enable it with `zrok2 enable <TOKEN>` |

### Debian / Ubuntu Setup

```bash
# 1. Install zrok via the official script (official installer URL: docs.zrok.io/docs/installation/)
curl -sSL https://install.zrok.io | sh

# 2. Verify installation
zrok --version

# 3. Sign up at https://account.zrok.io/signup (if you haven't already)
#    Then get your access token from the dashboard

# 4. Enable the zrok environment with your token
zrok enable <YOUR_TOKEN>

# That's it - AnywhereInput will detect zrok automatically when you select Zrok2 as the tunnel
```

### Arch Linux / CachyOS Setup

```bash
# Install via AUR
yay -S zrok-bin
# or
paru -S zrok-bin
# Verify:
zrok --version
# Sign up and enable (same as above)
```

### Windows Setup

```powershell
# 1. Download and install zrok (official installer)
irm https://install.zrok.io/install.ps1 | iex

# 2. Verify installation
zrok --version

# 3. Sign up at https://account.zrok.io/signup (if you haven't already)
#    Then get your access token from the dashboard

# 4. Enable the zrok environment with your token
zrok enable <YOUR_TOKEN>

# That's it - AnywhereInput will detect zrok automatically when you select Zrok2 as the tunnel
```

> ⚠️ The project formerly called "Zrok" is now maintained by ZrokLabs. The `zrok` CLI binary (not `zrok2`) is what you install — the tunnel provider name in AnywhereInput's menu remains `Zrok2` for consistency with earlier naming.

---

*Choose whichever fits your setup. No vendor lock-in.*
