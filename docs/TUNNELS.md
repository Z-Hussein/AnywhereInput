# Tunnel Provider Guide

## Cloudflare Tunnel (Recommended)
- **Cost**: Free
- **Account**: Not required
- **Setup**: Automatic download on first run
- **Pros**: Fastest globally, random URLs, no signup
- **Cons**: URL changes every session

### Linux Setup
```bash
# cloudflared is auto-downloaded on first tunnel use — nothing to install manually
# If you want it upfront:
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared
chmod +x /usr/local/bin/cloudflared
cloudflared --version
```

### Windows Setup
```powershell
# cloudflared is auto-downloaded on first tunnel use — nothing to install manually
# If you want it upfront:
irm https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe -OutFile $env:USERPROFILE\cloudflared.exe
$env:PATH += ";$env:USERPROFILE"
cloudflared --version
```

---

## Tailscale
- **Cost**: Free (10 devices on free tier)
- **Account**: Required (free tier available at https://tailscale.com)
- **Setup**: Install Tailscale, log in once — both server and client must be on the same tailnet

### Linux Setup
```bash
# 1. Install tailscaled (official script works on Ubuntu/Debian, Arch, Fedora, etc.)
curl -fsSL https://tailscale.com/install.sh | sh

# 2. Log in to your account
sudo tailscaled start
sudo tailscale up

# 3. Verify connection
tailscale status
# You should see yourself listed with a 100.x.x.x address

# That's it — AnywhereInput will auto-detect your tailnet IP when you select Tailscale as the tunnel
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

# That's it — AnywhereInput will auto-detect your tailnet IP when you select Tailscale as the tunnel
```

---

## Pinggy.io
- **Cost**: Free (60-minute session timeout, no account needed)
- **Account**: Not required
- **Setup**: Requires OpenSSH client — built into Windows 10+, macOS, and all Linux distros

### Linux Setup
```bash
# SSH is pre-installed on virtually all Linux distributions. Verify:
ssh -V
# If not installed:
sudo apt install openssh-client   # Debian/Ubuntu
sudo dnf install openssh-clients   # Fedora/RHEL
```
That's all you need — AnywhereInput uses your existing `ssh` client to create the tunnel.

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

## Zrok2
- **Cost**: Free (5GB/day on the public environment)
- **Account**: Required (free at https://account.zrok.io/signup)
- **Setup**: Sign up, get a token, enable it with `zrok2 enable <TOKEN>`

### Linux Setup
```bash
# 1. Install zrok2 via the official script
curl -sSL https://install.zrok.io | sh

# 2. Verify installation
zrok --version

# 3. Sign up at https://account.zrok.io/signup (if you haven't already)
#    Then get your access token from the dashboard

# 4. Enable the zrok environment with your token
zrok enable <YOUR_TOKEN>

# That's it — AnywhereInput will detect zrok automatically when you select Zrok2 as the tunnel
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

# That's it — AnywhereInput will detect zrok automatically when you select Zrok2 as the tunnel
```

---

## ngrok
- **Cost**: Free tier (unlimited tunnels, but sessions expire after 2 hours on free)
- **Account**: Required (free at https://ngrok.com/signup)
- **Setup**: Download binary + set authtoken from your ngrok dashboard

### Linux Setup
```bash
# 1. Download ngrok for Linux
curl -sSL https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz | tar xz -C /usr/local/bin/
# Or for ARM devices:
curl -sSL https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-arm64.tgz | tar xz -C /usr/local/bin/

# 2. Authenticate with your ngrok account (get authtoken from https://dashboard.ngrok.com/get-started/your-authtoken)
ngrok config add-authtoken YOUR_AUTHTOKEN_HERE

# 3. Verify
ngrok version
```

### Windows Setup
```powershell
# 1. Download ngrok for Windows
irm https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-win-amd64.zip -OutFile $env:TEMP\ngrok.zip
Expand-Archive -Path $env:TEMP\ngrok.zip -DestinationPath $env:USERPROFILE -Force
$env:PATH += ";$env:USERPROFILE"

# 2. Authenticate with your ngrok account (get authtoken from https://dashboard.ngrok.com/get-started/your-authtoken)
ngrok config add-authtoken YOUR_AUTHTOKEN_HERE

# 3. Verify
ngrok version
```
