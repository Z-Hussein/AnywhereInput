#!/usr/bin/env python3
"""
Launch the mouse controller app with ngrok tunnel.
"""
import subprocess
import time
import sys
import os
import requests
import signal
import argparse
import threading
import platform

# Parse command-line arguments
parser = argparse.ArgumentParser(
    description="Launch AnywhereInput with ngrok tunnel",
    epilog="Example: python launch_with_ngrok.py --port 9000 --region us --auto-token"
)
parser.add_argument("--port", type=int, default=8008,
                    help="Server port to tunnel (default: 8008)")
parser.add_argument("--region", type=str, default=None,
                    help="ngrok region (us, eu, au, ap, sa, jp, in) - default: auto")
parser.add_argument("--auto-token", action="store_true",
                    help="Skip token input and use auto-generated token from server")
parser.add_argument("--ngrok-path", type=str, default=None,
                    help="Explicit path to ngrok executable (optional)")
parser.add_argument("-v", "--verbose", action="store_true",
                    help="Enable verbose output")
args = parser.parse_args()

PORT_TO_TUNNEL = args.port
NGROK_REGION = args.region
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
    print("\n\nStopping servers...")
    cleanup()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def get_ngrok_url(timeout=60):
    """Poll ngrok API for the public URL."""
    for i in range(timeout):
        try:
            resp = requests.get("http://127.0.0.1:4040/api/tunnels", timeout=2)
            data = resp.json()
            if data.get("tunnels") and len(data["tunnels"]) > 0:
                tunnel_url = data["tunnels"][0].get("public_url")
                if tunnel_url:
                    return tunnel_url
        except requests.exceptions.RequestException:
            pass
        except Exception as e:
            pass
        time.sleep(1)
    return None


def read_token_from_file(timeout=15):
    """Wait for trusted_tokens.json and return the first token or None."""
    try:
        import json
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

# Start the mouse server
print("[*] Starting mouse server...")
with server_lock:
    server_proc = subprocess.Popen(
        [sys.executable, "secure_server.py", "--port", str(PORT_TO_TUNNEL)] + (["--verbose"] if VERBOSE else []),
        cwd=os.path.dirname(__file__),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    processes.append(server_proc)
# Give the server a little time to start and create trusted_tokens.json
time.sleep(1)

if server_proc.poll() is not None:
    print("[!] ERROR: Mouse server exited immediately.")
    if server_proc.stdout is not None:
        output = server_proc.stdout.read()
        if output:
            print(output.strip())
    cleanup()
    sys.exit(1)

# Wait for trusted_tokens.json to be created by the server and read the token
token_from_file = None
try:
    import json
    token_path = os.path.join(os.path.dirname(__file__), "trusted_tokens.json")
    for _ in range(15):  # wait up to ~15 seconds
        if os.path.exists(token_path):
            try:
                with open(token_path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                    if isinstance(data, dict) and len(data) > 0:
                        token_from_file = list(data.keys())[0]
                        break
            except Exception:
                pass
        time.sleep(1)
except Exception:
    token_from_file = None


def restart_server_and_reload_token():
    """Terminate and restart the mouse server to regenerate the token."""
    global server_proc, token_from_file
    print("\n[*] Restarting mouse server to generate a new token...")
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

        # Start a fresh server
        server_proc = subprocess.Popen(
            [sys.executable, "secure_server.py", "--port", str(PORT_TO_TUNNEL)] + (["--verbose"] if VERBOSE else []),
            cwd=os.path.dirname(__file__),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        # Replace processes list entry if present
        try:
            if processes:
                processes[0] = server_proc
        except Exception:
            pass

    # Wait for token file and display
    new_token = read_token_from_file(timeout=15)
    if new_token:
        token_from_file = new_token
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
                    # ctrl-N is ASCII 14
                    if ch == b"\x0e" or ch.lower() == b"n":
                        restart_server_and_reload_token()
                time.sleep(0.1)
        except Exception:
            pass
    else:
        # Fallback: user can type 'n' + Enter
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


# Start key listener thread
listener = threading.Thread(target=key_listener_thread, daemon=True)
listener.start()

# Find ngrok
import os
import glob
import shutil

system = platform.system()
ngrok_paths = []
if system == "Windows":
    ngrok_paths = [
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
    ngrok_paths = [
        os.path.join(os.path.dirname(__file__), "ngrok"),
        os.path.join(os.path.dirname(__file__), "ngrok.exe"),
        os.path.join(os.path.expanduser("~"), ".local", "bin", "ngrok"),
        os.path.join(os.path.expanduser("~"), "bin", "ngrok"),
        os.path.join(os.path.expanduser("~"), "Downloads", "ngrok"),
        os.path.join(os.path.expanduser("~"), "Downloads", "ngrok-stable-linux-amd64", "ngrok"),
        "/usr/local/bin/ngrok",
        "/usr/bin/ngrok",
        "/snap/bin/ngrok",
        "ngrok"
    ]

# If user passed explicit ngrok path via CLI, prefer it
if args.ngrok_path:
    ngrok_paths.insert(0, args.ngrok_path)

# If NGROK_PATH env var is set, prefer that too
if os.environ.get("NGROK_PATH"):
    ngrok_paths.insert(0, os.environ.get("NGROK_PATH"))

ngrok_cmd = None
print("[*] Searching for ngrok...")
for path in ngrok_paths:
    try:
        # Use shutil.which for simple names
        if not os.path.isabs(path) and path in ("ngrok", "ngrok.exe"):
            which = shutil.which("ngrok")
            if which:
                ngrok_cmd = which
                print(f"    ✓ Found in PATH: {which}")
                break
            else:
                print(f"    ✗ Not found in PATH: {path}")
                continue

        if os.path.exists(path):
            ngrok_cmd = path
            print(f"    ✓ Found at: {path}")
            break
        else:
            print(f"    ✗ Not found: {path}")
    except Exception as e:
        print(f"    ✗ Error checking {path}: {e}")

# Try PATH if not found locally
if not ngrok_cmd:
    try:
        which = shutil.which("ngrok")
        if which:
            ngrok_cmd = which
            print(f"    ✓ Found in PATH: {ngrok_cmd}")
    except:
        pass

if not ngrok_cmd:
    print()
    print("[!] ERROR: ngrok not found in any of these locations:")
    if system == "Windows":
        print("    1. C:\\Users\\<USERNAME>\\AppData\\Local\\ngrok\\ngrok.exe")
        print("    2. C:\\Program Files\\ngrok\\ngrok.exe")
        print("    3. System PATH")
        print("    4. ./ngrok.exe")
    else:
        print("    1. ./ngrok")
        print("    2. ~/.local/bin/ngrok or ~/bin/ngrok")
        print("    3. /usr/local/bin/ngrok or /usr/bin/ngrok")
        print("    4. System PATH")
    print()
    print("Solutions:")
    print("    a) Download: https://ngrok.com/download")
    if system == "Windows":
        print("    b) Run installer and make sure to extract to AppData\\Local\\ngrok\\")
        print("    c) Or add ngrok folder to your PATH environment variable")
        print("    d) Or place ngrok.exe in: " + os.path.join(os.path.dirname(__file__), "ngrok.exe"))
    else:
        print("    b) Make the ngrok binary executable: chmod +x ~/Downloads/ngrok")
        print("    c) Add the ngrok directory to your PATH: export PATH=\"$PATH:~/.local/bin\"")
        print("    d) Or place ngrok in: " + os.path.join(os.path.dirname(__file__), "ngrok"))
    print()
    cleanup()
    sys.exit(1)

print(f"[*] Using ngrok: {ngrok_cmd}")

# Get auth token
print()
token = ""
if not args.auto_token:
    token = input("[?] Enter ngrok auth token (or press Enter if already configured): ").strip()
if token:
    if token.startswith("$"):
        token = token[1:]
    print("[*] Configuring ngrok...")
    result = subprocess.run([ngrok_cmd, "config", "add-authtoken", token], 
                           capture_output=True, text=True, timeout=5)
    if result.returncode != 0:
        print(f"[!] Warning: ngrok auth config returned: {result.stderr}")

# Start ngrok - capture output for debugging
ngrok_cmd_args = [ngrok_cmd, "http", str(PORT_TO_TUNNEL)]
if NGROK_REGION:
    ngrok_cmd_args.extend(["--region", NGROK_REGION])
    print(f"[*] Starting ngrok tunnel on port {PORT_TO_TUNNEL} (region: {NGROK_REGION})...")
else:
    print(f"[*] Starting ngrok tunnel on port {PORT_TO_TUNNEL}...")
ngrok_proc = subprocess.Popen(
    ngrok_cmd_args,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)
processes.append(ngrok_proc)

# Give ngrok time to start
time.sleep(3)

# Get and display the URL
print("[*] Waiting for tunnel URL (up to 60 seconds)...")
url = get_ngrok_url(timeout=60)

if url:
    print()
    print("=" * 70)
    print(f"SUCCESS! Your public ngrok URL is:")
    print(f"\n  {url}\n")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  1. Open this URL in your Android browser:")
    print(f"     {url}")
    print()
    print("  2. In the app, enter:")
    print("     Server URL: " + url)
    print("     Port: (leave blank)")
    # Always read the current token from trusted_tokens.json right before displaying
    token_display = ""
    try:
        import json
        token_path = os.path.join(os.path.dirname(__file__), "trusted_tokens.json")
        if os.path.exists(token_path):
            with open(token_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                if isinstance(data, dict) and len(data) > 0:
                    token_display = list(data.keys())[0]
    except Exception:
        token_display = ""

    print(f"     Token: {token_display}")
    print()
    print("=" * 70)
    print()
    print("Press Ctrl+C to stop all servers.")
    print()
    
    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nStopping...")
        cleanup()
else:
    print()
    print("[!] ERROR: Could not get ngrok URL after 60 seconds.")
    print()
    print("Troubleshooting steps:")
    print("  1. Check that your ngrok auth token is correct")
    print("     Visit: https://dashboard.ngrok.com/get-started/your-authtoken")
    print()
    print("  2. Try running ngrok manually in another terminal:")
    print(f"     {ngrok_cmd} http {PORT_TO_TUNNEL}")
    print()
    print("  3. Check the ngrok status page:")
    print("     Open http://127.0.0.1:4040 in your browser")
    print()
    cleanup()
    sys.exit(1)
