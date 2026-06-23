#!/usr/bin/env python3
"""
AnywhereInput - Unified Tunnel Launcher - Creator: Z-Hussein
Supports: Cloudflare Tunnel, Pinggy, Zrok, and ngrok
"""

import subprocess
import time
import sys
import os
import re
import json
import signal
import argparse
import threading
import platform
import shutil
import tempfile
import urllib.request

# Parse command-line arguments
parser = argparse.ArgumentParser(
    description="Launch AnywhereInput with a tunnel provider",
    epilog="Example: python launch_with_tunnel.py --provider cloudflare --port 8008"
)
parser.add_argument("--provider", type=str, default="cloudflare",
                    choices=["cloudflare", "pinggy", "zrok", "zrok2", "ngrok"],
                    help="Tunnel provider to use (default: cloudflare)")
parser.add_argument("--port", type=int, default=8008,
                    help="Server port to tunnel (default: 8008)")
parser.add_argument("--auto-token", action="store_true",
                    help="Skip token input and use auto-generated token from server")
parser.add_argument("--ngrok-path", type=str, default=None,
                    help="Explicit path to ngrok executable (ngrok provider only)")
parser.add_argument("--cloudflared-path", type=str, default=None,
                    help="Explicit path to cloudflared executable (cloudflare provider only)")
parser.add_argument("--zrok-path", type=str, default=None,
                    help="Explicit path to zrok executable (zrok/zrok2 provider only)")
parser.add_argument("--pinggy-token", type=str, default=None,
                    help="Pinggy auth token for longer sessions (pinggy provider only)")
parser.add_argument("-v", "--verbose", action="store_true",
                    help="Enable verbose output")
args = parser.parse_args()

PORT_TO_TUNNEL = args.port
PROVIDER = args.provider
VERBOSE = args.verbose

processes = []
server_proc = None
server_lock = threading.Lock()


def cleanup():
    """Kill all spawned processes."""
    for proc in processes:
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except:
            try:
                proc.kill()
            except:
                pass


def signal_handler(sig, frame):
    print("\n\n[*] Stopping all servers...")
    cleanup()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def read_token_from_file(timeout=15):
    """Wait for trusted_tokens.json and return the first token or None."""
    try:
        token_path = os.path.join(os.path.dirname(__file__), "trusted_tokens.json")
        for _ in range(timeout):
            if os.path.exists(token_path):
                try:
                    with open(token_path, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                        if isinstance(data, dict) and len(data) > 0:
                            return list(data.keys())[0]
                except Exception:
                    pass
            time.sleep(1)
    except Exception:
        pass
    return None


# ═══════════════════════════════════════════════════════════════════════════
# PROVIDER: CLOUDFLARE TUNNEL
# ═══════════════════════════════════════════════════════════════════════════

def find_cloudflared():
    """Find cloudflared binary across common locations."""
    system = platform.system()
    paths = []

    if args.cloudflared_path:
        paths.insert(0, args.cloudflared_path)
    if os.environ.get("CLOUDFLARED_PATH"):
        paths.insert(0, os.environ.get("CLOUDFLARED_PATH"))

    if system == "Windows":
        paths += [
            os.path.join(os.path.dirname(__file__), "cloudflared.exe"),
            os.path.join(os.path.expanduser("~"), "AppData", "Local", "cloudflared", "cloudflared.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\cloudflared\cloudflared.exe"),
            os.path.join(os.path.expanduser("~"), "Downloads", "cloudflared-windows-amd64.exe"),
            os.path.join(os.path.expanduser("~"), "Downloads", "cloudflared.exe"),
            r"C:\Program Files\Cloudflare\cloudflared.exe",
            r"C:\Program Files (x86)\Cloudflare\cloudflared.exe",
            "cloudflared.exe",
            "cloudflared",
        ]
    else:
        paths += [
            os.path.join(os.path.dirname(__file__), "cloudflared"),
            os.path.join(os.path.expanduser("~"), ".local", "bin", "cloudflared"),
            os.path.join(os.path.expanduser("~"), "bin", "cloudflared"),
            os.path.join(os.path.expanduser("~"), "Downloads", "cloudflared"),
            "/usr/local/bin/cloudflared",
            "/usr/bin/cloudflared",
            "/opt/cloudflare/bin/cloudflared",
            "cloudflared",
        ]

    for path in paths:
        if not os.path.isabs(path) and path in ("cloudflared", "cloudflared.exe"):
            which = shutil.which("cloudflared")
            if which:
                return which
            continue
        if os.path.exists(path):
            return path

    which = shutil.which("cloudflared")
    if which:
        return which

    return None


def get_cloudflare_url(proc, timeout=60):
    """Parse cloudflared stdout/stderr to extract the tunnel URL."""
    url_pattern = re.compile(r'(https://[a-zA-Z0-9-]+\.trycloudflare\.com)')

    for i in range(timeout):
        try:
            if proc.stdout:
                try:
                    line = proc.stdout.readline()
                    if line:
                        line_str = line if isinstance(line, str) else line.decode('utf-8', errors='replace')
                        if VERBOSE:
                            print(f"[cloudflared] {line_str.strip()}")
                        match = url_pattern.search(line_str)
                        if match:
                            return match.group(1)
                except Exception:
                    pass
            if proc.stderr:
                try:
                    line = proc.stderr.readline()
                    if line:
                        line_str = line if isinstance(line, str) else line.decode('utf-8', errors='replace')
                        if VERBOSE:
                            print(f"[cloudflared stderr] {line_str.strip()}")
                        match = url_pattern.search(line_str)
                        if match:
                            return match.group(1)
                except Exception:
                    pass
        except Exception:
            pass
        time.sleep(1)
    return None


def install_cloudflared_windows():
    """Download and install cloudflared on Windows."""
    print("[*] cloudflared not found. Attempting to download...")
    print("[*] Downloading from GitHub releases...")

    try:
        target = os.path.join(os.path.dirname(__file__), "cloudflared.exe")
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
        urllib.request.urlretrieve(url, target)
        print(f"[+] Downloaded to: {target}")
        return target
    except Exception as e:
        print(f"[!] Download failed: {e}")
        return None


def install_cloudflared_linux():
    """Download and install cloudflared on Linux/macOS."""
    print("[*] cloudflared not found. Attempting to download...")
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "darwin":
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-amd64"
        binary_name = "cloudflared"
    elif "arm" in machine or "aarch64" in machine:
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64"
        binary_name = "cloudflared"
    else:
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
        binary_name = "cloudflared"

    try:
        target = os.path.join(os.path.dirname(__file__), binary_name)
        print(f"[*] Downloading from: {url}")
        urllib.request.urlretrieve(url, target)
        os.chmod(target, 0o755)
        print(f"[+] Downloaded to: {target}")
        return target
    except Exception as e:
        print(f"[!] Download failed: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════
# PROVIDER: PINGGY (SSH-based, zero install)
# ═══════════════════════════════════════════════════════════════════════════

def get_pinggy_url(proc, timeout=90):
    """Parse pinggy SSH output to extract the tunnel URL."""
    url_patterns = [
        re.compile(r'(https?://[a-zA-Z0-9-]+\.a\.free\.pinggy\.link)'),
        re.compile(r'(https?://[a-zA-Z0-9-]+\.a\.pinggy\.link)'),
        re.compile(r'(https?://[a-zA-Z0-9-]+\.free\.pinggy\.io)'),
        re.compile(r'(https?://[a-zA-Z0-9-]+\.pinggy\.io)'),
    ]

    for i in range(timeout):
        try:
            if proc.stdout:
                try:
                    line = proc.stdout.readline()
                    if line:
                        line_str = line if isinstance(line, str) else line.decode('utf-8', errors='replace')
                        if VERBOSE:
                            print(f"[pinggy] {line_str.strip()}")
                        for pattern in url_patterns:
                            match = pattern.search(line_str)
                            if match:
                                return match.group(1)
                except Exception:
                    pass
            if proc.stderr:
                try:
                    line = proc.stderr.readline()
                    if line:
                        line_str = line if isinstance(line, str) else line.decode('utf-8', errors='replace')
                        if VERBOSE:
                            print(f"[pinggy stderr] {line_str.strip()}")
                        for pattern in url_patterns:
                            match = pattern.search(line_str)
                            if match:
                                return match.group(1)
                except Exception:
                    pass
        except Exception:
            pass
        time.sleep(1)
    return None


# ═══════════════════════════════════════════════════════════════════════════
# PROVIDER: ZROK (v1 and v2)
# ═══════════════════════════════════════════════════════════════════════════

def find_zrok():
    """Find zrok or zrok2 binary."""
    if args.zrok_path:
        return args.zrok_path
    if os.environ.get("ZROK_PATH"):
        return os.environ.get("ZROK_PATH")

    # Try zrok2 first (newer version), then zrok
    for binary_name in ["zrok2", "zrok"]:
        which = shutil.which(binary_name)
        if which:
            return which

        paths = [
            os.path.join(os.path.dirname(__file__), binary_name),
            os.path.join(os.path.dirname(__file__), binary_name + ".exe"),
            os.path.join(os.path.expanduser("~"), ".local", "bin", binary_name),
            os.path.join(os.path.expanduser("~"), "bin", binary_name),
            os.path.join(os.path.expanduser("~"), "bin", binary_name + ".exe"),
            "/usr/local/bin/" + binary_name,
            "/usr/bin/" + binary_name,
        ]
        for path in paths:
            if os.path.exists(path):
                return path

    return None


def strip_ansi(text):
    """Remove ANSI escape sequences and terminal control codes from text."""
    text = re.sub(r"\x1b\[[0-9;?]*[a-zA-Z]", "", text)
    text = re.sub(r'\x1b\][^\x07]*\x07', '', text)
    text = re.sub(r'\x1b[()[\]\\]', '', text)
    text = re.sub(r'[\u2500-\u257F]', '-', text)
    text = re.sub(r'[\u2580-\u259F]', '', text)
    text = re.sub(r'[\u2800-\u28FF]', '', text)
    text = text.replace('\u2550', '=').replace('\u2551', '|')
    text = text.replace('\u2554', '+').replace('\u2557', '+')
    text = text.replace('\u255A', '+').replace('\u255D', '+')
    text = text.replace('\u2560', '+').replace('\u2563', '+')
    text = text.replace('\u2566', '+').replace('\u2569', '+')
    text = text.replace('\u256C', '+')
    return text


def get_zrok_url(proc, timeout=90):
    """Parse zrok output to extract the public share URL."""
    url_patterns = [
        re.compile(r'https?://[a-zA-Z0-9-]+\.shares\.zrok\.io'),
        re.compile(r'https?://[a-zA-Z0-9-]+\.share\.zrok\.io'),
        re.compile(r'https?://[a-zA-Z0-9-]+\.zrok\.io'),
        re.compile(r'https?://[a-zA-Z0-9-]+\.zrok\.link'),
    ]

    all_output = []

    for i in range(timeout):
        got_any = False
        try:
            if proc.stdout:
                try:
                    while True:
                        line = proc.stdout.readline()
                        if not line:
                            break
                        line_str = line if isinstance(line, str) else line.decode('utf-8', errors='replace')
                        all_output.append(line_str)
                        got_any = True

                        clean = strip_ansi(line_str)
                        if clean.strip():
                            print(f"[zrok] {clean.rstrip()}")

                        for text in [line_str, clean]:
                            for pattern in url_patterns:
                                match = pattern.search(text)
                                if match:
                                    url = match.group(0)
                                    print(f"[+] Found zrok URL: {url}")
                                    return url
                except Exception:
                    pass

            if proc.stderr:
                try:
                    while True:
                        line = proc.stderr.readline()
                        if not line:
                            break
                        line_str = line if isinstance(line, str) else line.decode('utf-8', errors='replace')
                        all_output.append(line_str)
                        got_any = True

                        clean = strip_ansi(line_str)
                        if clean.strip():
                            print(f"[zrok] {clean.rstrip()}")

                        for text in [line_str, clean]:
                            for pattern in url_patterns:
                                match = pattern.search(text)
                                if match:
                                    url = match.group(0)
                                    print(f"[+] Found zrok URL: {url}")
                                    return url
                except Exception:
                    pass
        except Exception:
            pass

        if got_any:
            continue
        time.sleep(1)

    combined = strip_ansi(''.join(all_output))
    for pattern in url_patterns:
        match = pattern.search(combined)
        if match:
            url = match.group(0)
            print(f"[+] Found zrok URL in combined output: {url}")
            return url

    return None


# ═══════════════════════════════════════════════════════════════════════════
# PROVIDER: NGROK (existing, preserved)
# ═══════════════════════════════════════════════════════════════════════════

def find_ngrok():
    """Find ngrok binary (preserved from original launch_with_ngrok.py)."""
    system = platform.system()
    paths = []

    if args.ngrok_path:
        paths.insert(0, args.ngrok_path)
    if os.environ.get("NGROK_PATH"):
        paths.insert(0, os.environ.get("NGROK_PATH"))

    if system == "Windows":
        paths += [
            os.path.join(os.path.dirname(__file__), "ngrok.exe"),
            os.path.join(os.path.expanduser("~"), "AppData", "Local", "ngrok", "ngrok.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\ngrok\ngrok.exe"),
            os.path.join(os.path.expanduser("~"), "Downloads", "ngrok-v3-stable-windows-amd64", "ngrok.exe"),
            os.path.join(os.path.expanduser("~"), "Downloads", "ngrok.exe"),
            r"C:\Program Files\ngrok\ngrok.exe",
            r"C:\Program Files (x86)\ngrok\ngrok.exe",
            "ngrok",
            "ngrok.exe"
        ]
    else:
        paths += [
            os.path.join(os.path.dirname(__file__), "ngrok"),
            os.path.join(os.path.expanduser("~"), ".local", "bin", "ngrok"),
            os.path.join(os.path.expanduser("~"), "bin", "ngrok"),
            os.path.join(os.path.expanduser("~"), "Downloads", "ngrok"),
            os.path.join(os.path.expanduser("~"), "Downloads", "ngrok-stable-linux-amd64", "ngrok"),
            "/usr/local/bin/ngrok",
            "/usr/bin/ngrok",
            "/snap/bin/ngrok",
            "ngrok"
        ]

    for path in paths:
        if not os.path.isabs(path) and path in ("ngrok", "ngrok.exe"):
            which = shutil.which("ngrok")
            if which:
                return which
            continue
        if os.path.exists(path):
            return path

    which = shutil.which("ngrok")
    if which:
        return which
    return None


def get_ngrok_url(timeout=60):
    """Poll ngrok API for the public URL (preserved from original)."""
    for i in range(timeout):
        try:
            import requests
            resp = requests.get("http://127.0.0.1:4040/api/tunnels", timeout=2)
            data = resp.json()
            if data.get("tunnels") and len(data["tunnels"]) > 0:
                tunnel_url = data["tunnels"][0].get("public_url")
                if tunnel_url:
                    return tunnel_url
        except Exception:
            pass
        time.sleep(1)
    return None


# ═══════════════════════════════════════════════════════════════════════════
# SERVER MANAGEMENT (shared across all providers)
# ═══════════════════════════════════════════════════════════════════════════

def start_server():
    """Start the AnywhereInput server. - This is shared across all tunnel providers."""
    global server_proc
    print(f"[*] Starting AnywhereInput server on port {PORT_TO_TUNNEL}...")
    with server_lock:
        server_proc = subprocess.Popen(
            [sys.executable, "secure_server.py", "--port", str(PORT_TO_TUNNEL)] + (["--verbose"] if VERBOSE else []),
            cwd=os.path.dirname(__file__),
            stdout=subprocess.PIPE if VERBOSE else subprocess.DEVNULL,
            stderr=subprocess.STDOUT if VERBOSE else subprocess.DEVNULL,
            text=True,
        )
        processes.append(server_proc)

    time.sleep(2)

    if server_proc.poll() is not None:
        print("[!] ERROR: Server exited immediately.")
        cleanup()
        sys.exit(1)

    import socket
    for attempt in range(10):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', PORT_TO_TUNNEL))
            sock.close()
            if result == 0:
                print(f"[+] Server confirmed listening on 127.0.0.1:{PORT_TO_TUNNEL}")
                break
            else:
                if attempt == 9:
                    print(f"[!] WARNING: Port {PORT_TO_TUNNEL} does not appear to be listening.")
                    print(f"[!] The tunnel may fail to connect. Check if another process is using the port.")
                time.sleep(0.5)
        except Exception:
            time.sleep(0.5)


def restart_server_and_reload_token():
    """Terminate and restart the server to regenerate the token."""
    global server_proc
    print("\n[*] Restarting server to generate a new token...")
    with server_lock:
        try:
            if server_proc and server_proc.poll() is None:
                server_proc.terminate()
                try:
                    server_proc.wait(timeout=3)
                except Exception:
                    server_proc.kill()
        except Exception:
            pass

        server_proc = subprocess.Popen(
            [sys.executable, "secure_server.py", "--port", str(PORT_TO_TUNNEL)] + (["--verbose"] if VERBOSE else []),
            cwd=os.path.dirname(__file__),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        try:
            if processes:
                processes[0] = server_proc
        except Exception:
            pass

    new_token = read_token_from_file(timeout=15)
    if new_token:
        print(f"[*] New token: {new_token}")
    else:
        print("[!] Could not read new token from trusted_tokens.json")


def key_listener_thread():
    """Listen for Ctrl+N (or 'n') to restart server and renew token."""
    system = platform.system()
    if system == "Windows":
        try:
            import msvcrt
            print("[*] Press Ctrl+N (or 'n') to renew token, Ctrl+C to exit.")
            while True:
                if msvcrt.kbhit():
                    ch = msvcrt.getch()
                    if ch == b"\x0e" or ch.lower() == b"n":
                        restart_server_and_reload_token()
                time.sleep(0.1)
        except Exception:
            pass
    else:
        print("[*] Type 'n' and press Enter to renew token, Ctrl+C to exit.")
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                if line.strip().lower() == "n":
                    restart_server_and_reload_token()
            except Exception:
                break


# ═══════════════════════════════════════════════════════════════════════════
# MAIN LAUNCH LOGIC
# ═══════════════════════════════════════════════════════════════════════════

def launch_cloudflare():
    """Launch with Cloudflare Tunnel (TryCloudflare - no account needed)."""
    print("=" * 70)
    print(" Provider: Cloudflare Tunnel (TryCloudflare)")
    print(" Cost: FREE - No account, no bandwidth limits")
    print(" URL: Random per session (e.g., https://xxx.trycloudflare.com)")
    print("=" * 70)
    print()

    cloudflared = find_cloudflared()

    if not cloudflared:
        print("[!] cloudflared not found.")
        system = platform.system()
        if system == "Windows":
            cloudflared = install_cloudflared_windows()
        else:
            cloudflared = install_cloudflared_linux()

    if not cloudflared:
        print()
        print("[!] ERROR: cloudflared could not be found or installed.")
        print()
        print("Manual installation:")
        print(" Windows: winget install --id Cloudflare.cloudflared")
        print(" macOS:   brew install cloudflared")
        print(" Linux:   See https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/")
        print()
        cleanup()
        sys.exit(1)

    print(f"[*] Using cloudflared: {cloudflared}")
    print(f"[*] Starting Cloudflare tunnel on port {PORT_TO_TUNNEL}...")
    print("[*] This may take 10-20 seconds to establish...")
    print()

    cmd = [cloudflared, "tunnel", "--url", f"http://127.0.0.1:{PORT_TO_TUNNEL}"]
    if VERBOSE:
        cmd.append("--loglevel")
        cmd.append("debug")

    tunnel_proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
    )
    processes.append(tunnel_proc)

    url = get_cloudflare_url(tunnel_proc, timeout=60)
    return url


def launch_pinggy():
    """Launch with Pinggy (SSH-based, zero install)."""
    print("=" * 70)
    print(" Provider: Pinggy.io")
    print(" Cost: FREE tier (60 min session timeout)")
    print(" URL: Random per session (e.g., https://xxx.a.free.pinggy.link)")
    print(" Note: Uses your existing SSH client - no binary needed!")
    print("=" * 70)
    print()

    ssh_cmd = shutil.which("ssh")
    if not ssh_cmd:
        print("[!] ERROR: SSH not found on your system.")
        print("[!] Pinggy requires an SSH client.")
        print()
        print("Install SSH:")
        print(" Windows: Enable OpenSSH Client in Windows Settings > Apps > Optional Features")
        print(" Linux:   sudo apt-get install openssh-client")
        print(" macOS:   Built-in, should already be available")
        print()
        cleanup()
        sys.exit(1)

    print(f"[*] Using SSH: {ssh_cmd}")
    print(f"[*] Starting Pinggy tunnel on port {PORT_TO_TUNNEL}...")
    print("[*] This may take 5-15 seconds to establish...")
    print()
    print("[!] IMPORTANT: If prompted for a password, just press ENTER (blank password)")
    print()

    local_host = "127.0.0.1"

    if args.pinggy_token:
        host = f"{args.pinggy_token}@free.pinggy.io"
    else:
        host = "qr@free.pinggy.io"

    null_device = "NUL" if platform.system() == "Windows" else "/dev/null"

    cmd = [
        ssh_cmd,
        "-p", "443",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=" + null_device,
        "-o", "ServerAliveInterval=30",
        "-o", "ServerAliveCountMax=3",
        "-o", "PasswordAuthentication=yes",
        "-o", "BatchMode=no",
        "-o", "ConnectTimeout=15",
        "-N",
        "-T",
        "-R", f"0:{local_host}:{PORT_TO_TUNNEL}",
        host,
    ]

    if VERBOSE:
        print(f"[*] SSH command: {' '.join(cmd)}")

    tunnel_proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
    )
    processes.append(tunnel_proc)

    time.sleep(2)

    try:
        if tunnel_proc.stdin:
            tunnel_proc.stdin.write("\n")
            tunnel_proc.stdin.flush()
    except Exception:
        pass

    url = get_pinggy_url(tunnel_proc, timeout=90)

    if not url:
        print("[*] Trying to retrieve URL from process output...")
        url = get_pinggy_url(tunnel_proc, timeout=30)

    return url


def launch_zrok():
    """Launch with Zrok (OpenZiti-based, open source)."""
    print("=" * 70)
    print(" Provider: Zrok (OpenZiti)")
    print(" Cost: FREE (5GB daily, 25 environments)")
    print(" URL: Persistent if using reserved shares")
    print(" Note: Requires 'zrok invite' once to create account")
    print("=" * 70)
    print()

    zrok = find_zrok()
    if not zrok:
        print("[!] ERROR: zrok/zrok2 not found.")
        print()
        print("Install zrok:")
        print(" 1. Download from https://github.com/openziti/zrok/releases")
        print(" 2. Extract to a folder in your PATH, or place in this directory")
        print(" 3. Run: zrok invite   (one-time account setup)")
        print(" 4. Run: zrok enable   (one-time environment setup)")
        print()
        cleanup()
        sys.exit(1)

    zrok_version = "zrok2" if "zrok2" in os.path.basename(zrok).lower() else "zrok"
    print(f"[*] Using {zrok_version}: {zrok}")

    # Check zrok status BEFORE trying to share
    print("[*] Checking zrok environment status...")
    try:
        result = subprocess.run([zrok, "status"], capture_output=True, text=True, timeout=10)
        status_output = (result.stdout or "") + (result.stderr or "")

        if "not enabled" in status_output.lower():
            print()
            print("[!] ERROR: Your zrok environment is NOT ENABLED.")
            print()
            print("You need to enable it before you can create shares.")
            print()
            print("Steps to fix:")
            print(" 1. Get your environment token from https://zrok.io")
            print("    (or run: zrok invite  if you don't have an account)")
            print()
            print(" 2. Enable your environment:")
            print(f"    {zrok} enable <YOUR_TOKEN>")
            print()
            print(" 3. Then run this launcher again.")
            print()

            # Offer to enable right now
            token = input("[?] Paste your zrok enable token here (or press Enter to abort): ").strip()
            if token:
                print(f"[*] Enabling zrok environment...")
                enable_result = subprocess.run([zrok, "enable", token], capture_output=True, text=True, timeout=30)
                if enable_result.returncode != 0:
                    print(f"[!] Enable failed: {enable_result.stderr or enable_result.stdout}")
                    cleanup()
                    sys.exit(1)
                print("[+] zrok environment enabled successfully!")
            else:
                cleanup()
                sys.exit(1)

        elif "enabled" in status_output.lower() or result.returncode == 0:
            print("[+] zrok environment is enabled.")
        else:
            print(f"[!] Could not determine zrok status. Output:")
            print(f"    {status_output[:500]}")
    except Exception as e:
        print(f"[!] Could not check zrok status: {e}")
        print("[*] Continuing anyway...")

    print(f"[*] Starting Zrok public share on port {PORT_TO_TUNNEL}...")
    print(f"[*] Target backend: 127.0.0.1:{PORT_TO_TUNNEL} (IPv4 to avoid ::1 issues)")
    print()

    if zrok_version == "zrok2":
        cmd = [zrok, "share", "public", f":{PORT_TO_TUNNEL}"]
    else:
        cmd = [zrok, "share", "public", "--backend-mode", "proxy", f"127.0.0.1:{PORT_TO_TUNNEL}"]

    if VERBOSE:
        print(f"[*] Command: {' '.join(cmd)}")

    tunnel_proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
    )
    processes.append(tunnel_proc)

    url = get_zrok_url(tunnel_proc, timeout=60)

    if not url:
        print()
        print("[!] Could not automatically detect zrok URL from output.")
        print("[!] This can happen if zrok prints the URL in an unexpected format.")
        print()
        print("[*] zrok should have printed a URL like:")
        print("    https://xxxxxxxxxx.share.zrok.io")
        print("    https://xxxxxxxxxx.zrok.io")
        print()
        manual_url = input("[?] Paste the zrok URL here (or press Enter to abort): ").strip()
        if manual_url:
            if not manual_url.startswith("http"):
                manual_url = "https://" + manual_url
            url = manual_url
            print(f"[*] Using manually entered URL: {url}")

    return url


def launch_ngrok():
    """Launch with ngrok (preserved from original)."""
    print("=" * 70)
    print(" Provider: ngrok")
    print(" Cost: Free tier (random URLs, session limits)")
    print(" URL: Random per session (e.g., https://xxx.ngrok.io)")
    print("=" * 70)
    print()

    ngrok = find_ngrok()
    if not ngrok:
        print("[!] ERROR: ngrok not found.")
        print()
        print("Install ngrok:")
        print(" 1. Download from https://ngrok.com/download")
        print(" 2. Sign up for free at https://dashboard.ngrok.com/signup")
        print(" 3. Add your authtoken: ngrok config add-authtoken <token>")
        print()
        cleanup()
        sys.exit(1)

    print(f"[*] Using ngrok: {ngrok}")

    token = ""
    if not args.auto_token:
        token = input("[?] Enter ngrok auth token (or press Enter if already configured): ").strip()
    if token:
        if token.startswith("$"):
            token = token[1:]
        print("[*] Configuring ngrok...")
        result = subprocess.run([ngrok, "config", "add-authtoken", token],
                                capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            print(f"[!] Warning: ngrok auth config returned: {result.stderr}")

    print(f"[*] Starting ngrok tunnel on port {PORT_TO_TUNNEL}...")

    cmd = [ngrok, "http", str(PORT_TO_TUNNEL)]
    tunnel_proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    processes.append(tunnel_proc)

    url = get_ngrok_url(timeout=60)
    return url


# ═══════════════════════════════════════════════════════════════════════════
# DISPLAY RESULTS
# ═══════════════════════════════════════════════════════════════════════════

def display_success(url, token):
    """Display connection info and QR code."""
    print()
    print("=" * 70)
    print(f"SUCCESS! Your public URL is:")
    print(f"\n {url}\n")
    print("=" * 70)
    print()
    print("Next steps:")
    print(" 1. Open this URL in your device browser:")
    print(f" {url}")
    print()
    print(" 2. In the app, enter:")
    print(f" Server URL: {url}")
    print(" Port: (leave blank)")
    print(f" Token: {token}")
    print()
    print("=" * 70)
    print()
    print("Press Ctrl+C to stop all servers.")
    print()


def display_failure(provider, extra_help=""):
    """Display troubleshooting info."""
    print()
    print("=" * 70)
    print(f"[!] ERROR: Could not get {provider} URL after waiting.")
    print("=" * 70)
    print()

    if provider == "cloudflare":
        print("Troubleshooting:")
        print(" 1. Check your internet connection")
        print(" 2. Try running cloudflared manually:")
        print(f" cloudflared tunnel --url http://localhost:{PORT_TO_TUNNEL}")
        print(" 3. Cloudflare may be experiencing an outage")
        print(" 4. Try another provider: --provider pinggy")
    elif provider == "pinggy":
        print("Troubleshooting:")
        print(" 1. Check your internet connection")
        print(" 2. Ensure port 443 outbound is not blocked by firewall")
        print(" 3. Try running SSH manually:")
        local_host = "127.0.0.1"
        print(f" ssh -p 443 -o StrictHostKeyChecking=no -R0:{local_host}:{PORT_TO_TUNNEL} qr@free.pinggy.io")
        print(" 4. If prompted for password, just press ENTER (blank password)")
        print(" 5. Try another provider: --provider cloudflare")
    elif provider == "zrok":
        print("Troubleshooting:")
        print(" 1. Run 'zrok status' to check if your environment is enabled")
        print(" 2. Run 'zrok enable' if needed")
        print(" 3. Try running zrok manually:")
        print(f" zrok share public localhost:{PORT_TO_TUNNEL}")
        print(" 4. Try another provider: --provider cloudflare")
    elif provider == "ngrok":
        print("Troubleshooting:")
        print(" 1. Check that your ngrok auth token is correct")
        print(" Visit: https://dashboard.ngrok.com/get-started/your-authtoken")
        print(" 2. Try running ngrok manually:")
        print(f" ngrok http {PORT_TO_TUNNEL}")
        print(" 3. Try another provider: --provider cloudflare")

    if extra_help:
        print()
        print(extra_help)
    print()


# ═══════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    start_server()

    token = read_token_from_file(timeout=15)
    if not token:
        print("[!] Warning: Could not read token from file.")
        token = ""

    listener = threading.Thread(target=key_listener_thread, daemon=True)
    listener.start()

    url = None
    extra_help = ""

    if PROVIDER == "cloudflare":
        url = launch_cloudflare()
    elif PROVIDER == "pinggy":
        url = launch_pinggy()
        if not url:
            extra_help = "\nPinggy tip: The URL is printed by the SSH server after connection.\nIf you see a password prompt, just press ENTER (blank password).\nThe URL format is: https://xxx.a.free.pinggy.link"
    elif PROVIDER == "zrok":
        url = launch_zrok()
        if not url:
            extra_help = "\nZrok tip: Make sure you ran 'zrok enable <token>' first.\nThe URL format is: https://xxx.share.zrok.io (v2) or https://xxx.zrok.io (v1)"
    elif PROVIDER == "zrok2":
        url = launch_zrok()
        if not url:
            extra_help = "\nZrok2 tip: Make sure you ran 'zrok2 enable <token>' first.\nThe URL format is: https://xxx.shares.zrok.io"
    elif PROVIDER == "ngrok":
        url = launch_ngrok()

    if url:
        os.environ["NGROK_URL"] = url
        os.environ["TUNNEL_URL"] = url

        token = read_token_from_file(timeout=5) or token
        display_success(url, token)

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n[*] Stopping...")
            cleanup()
    else:
        display_failure(PROVIDER, extra_help)
        cleanup()
        sys.exit(1)
