"""Unified tunnel provider management."""

import json
import os
import sys
import subprocess
import platform
import shutil
import time
import requests
import threading
import re
import socket
from pathlib import Path
from typing import Optional, Callable
from abc import ABC, abstractmethod


class TunnelProvider(ABC):
    """Abstract base for tunnel providers."""

    @abstractmethod
    def start(self, local_port: int, on_url: Callable[[str], None]) -> subprocess.Popen:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass


class CloudflareTunnel(TunnelProvider):
    """Cloudflare Tunnel (free, no account)."""

    _SCRIPT_DIR = Path(__file__).resolve().parent.parent  # project root

    def __init__(self):
        self.binary = self._find_or_download()
        # Ensure absolute path for reliable subprocess execution
        if not os.path.isabs(self.binary):
            resolved = Path(self.binary).resolve()
            if resolved.is_file():
                self.binary = str(resolved)
            else:
                candidate = self._SCRIPT_DIR / self.binary
                if candidate.exists():
                    self.binary = str(candidate.resolve())

    def _find_or_download(self) -> str:
        name = "cloudflared.exe" if platform.system() == "Windows" else "cloudflared"

        # Check PATH first
        path = shutil.which(name)
        if path:
            return path

        # Check project root (absolute, regardless of cwd)
        local = self._SCRIPT_DIR / name
        if local.exists():
            return str(local.resolve())
        # Auto-download
        return self._download()

    def _download(self) -> str:
        print("[Cloudflare] Downloading cloudflared...")
        system = platform.system().lower()

        if system == "windows":
            url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
            filename = "cloudflared.exe"
        elif system == "darwin":
            url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-amd64.tgz"
            filename = "cloudflared-darwin-amd64.tgz"
        else:
            machine = platform.machine().lower()
            if "arm" in machine or "aarch64" in machine:
                url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64"
            else:
                url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
            filename = "cloudflared-linux-amd64" if system != "darwin" else "cloudflared-darwin-amd64.tgz"

        target = self._SCRIPT_DIR / filename
        try:
            r = requests.get(url, timeout=60)
            r.raise_for_status()

            with open(target, 'wb') as f:
                f.write(r.content)

            if system != "windows":
                os.chmod(target, 0o755)

        except Exception as e:
            raise FileNotFoundError(f"cloudflared download failed: {e}")

        # Darwin: extract tgz to cloudflared
        if system == "darwin" and filename.endswith(".tgz"):
            import tarfile
            extracted_name = None
            with tarfile.open(target, 'r:gz') as tar:
                for member in tar.getmembers():
                    if member.isfile() and 'cloudflared' in member.name.lower():
                        extracted_name = member.name
                        tar.extract(member, self._SCRIPT_DIR)
                        break
            target.unlink()
            executable = "cloudflared"
        else:
            # Linux: rename to cloudflared
            exec_path = self._SCRIPT_DIR / "cloudflared"
            Path(target).rename(exec_path)
            executable = "cloudflared"

        abs_path = str((self._SCRIPT_DIR / executable).resolve())
        print(f"[Cloudflare] Saved to {abs_path}")
        return abs_path

    def start(self, local_port: int, on_url: Callable[[str], None]) -> subprocess.Popen:
        if not os.path.isfile(self.binary) and shutil.which(self.binary) is None:
            error_msg = f"cloudflared binary not found at '{self.binary}'"
            print(f"\n❌ {error_msg}")
            print("   Run this project's setup again, or install cloudflared manually:")
            system = platform.system()
            if system == "Windows":
                print("     1. Download: https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe")
                print("     2. Place in project root or add to PATH")
            elif system == "Darwin":
                print("     brew install cloudflare/cloudflare/cloudflared")
            else:  # Linux
                print("     curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared")
                print("     chmod +x cloudflared")
            raise FileNotFoundError(error_msg)
        cmd = [self.binary, "tunnel", "--url", f"http://localhost:{local_port}"]
        
        print(f"[Cloudflare] Starting: {' '.join(cmd)}")
        
        # Platform-specific process group creation
        popen_kwargs = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
            "text": True,
            "bufsize": 1,
            "stdin": subprocess.DEVNULL,
        }
        if platform.system() == "Windows":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            popen_kwargs["preexec_fn"] = os.setsid
        
        try:
            proc = subprocess.Popen(cmd, **popen_kwargs)
        except Exception as e:
            error_msg = f"Failed to start cloudflared: {e}"
            print(f"❌ {error_msg}")
            raise RuntimeError(error_msg)

        def reader():
            try:
                line_count = 0
                for line in proc.stdout:
                    line = line.strip()
                    if line:
                        line_count += 1
                        print(f"[cloudflared] {line}")
                        if "trycloudflare.com" in line or "https://" in line:
                            match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
                            if match:
                                print(f"✅ [Cloudflare] Tunnel URL: {match.group(0)}")
                                on_url(match.group(0))
                if line_count == 0:
                    print("⚠️  [Cloudflare] No output received from cloudflared")
                    returncode = proc.poll()
                    if returncode is not None:
                        print(f"❌ [Cloudflare] Process exited with code {returncode}")
            except Exception as e:
                print(f"❌ [Cloudflare] Reader error: {e}")

        import threading
        reader_thread = threading.Thread(target=reader, daemon=True)
        reader_thread.start()
        
        # Give it a moment to start
        import time
        time.sleep(1)
        if proc.poll() is not None:
            error_msg = f"cloudflared process exited immediately with code {proc.returncode}"
            print(f"❌ [Cloudflare] {error_msg}")
            raise RuntimeError(error_msg)
        
        return proc

    def is_available(self) -> bool:
        try:
            self._find_or_download()
            return True
        except FileNotFoundError:
            return False


class TailscaleTunnel(TunnelProvider):
    """Tailscale tailnet — no public URL, peer-to-peer via Tailscale IP.

    Both server and client must be on the same tailnet. The server prints
    its Tailnet IP so the client can connect directly to port 8008.
    No extra binary needed if tailscaled is already running.
    """

    def start(self, local_port: int, on_url: Callable[[str], None]) -> subprocess.Popen:
        # Print the server's tailnet IP — no background process to manage
        try:
            hostname = socket.gethostname()
            addrs = socket.getaddrinfo(hostname, None, family=socket.AF_INET)
            for addr_info in addrs:
                ip = addr_info[4][0]
                if ip.startswith("100."):
                    print(f"\n🔷 Tailscale network active")
                    print(f"   Tailnet IP: {ip}")
                    print(f"   Server port: {local_port}")
                    print(f"   Connect from another tailnet device to {ip}:{local_port}")
                    on_url(f"{ip}:{local_port}")
                    break
            else:
                print("\n⚠️  Tailscale is installed but no tailnet IP detected.")
                print("   Make sure you're logged in: tailscale status")
                return None
        except Exception as e:
            print(f"\n⚠️  Could not get tailnet IP: {e}")
            return None
        # No subprocess to manage — just a message
        return None

    def is_available(self) -> bool:
        """Check if tailscale binary exists and the node is connected."""
        if shutil.which("tailscale") is None:
            return False
        try:
            result = subprocess.run(
                ["tailscale", "status", "--json"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                self_data = data.get("Self", {})
                return (
                    self_data.get("Status") == "authenticated"
                    or self_data.get("Online") is True
                    or (self_data.get("BackendState") == "Running" and len(self_data.get("TailscaleIPs", [])) > 0)
                )
        except Exception:
            pass
        return False


class PinggyTunnel(TunnelProvider):
    """Pinggy.io tunnel (SSH-based, no install)."""

    def start(self, local_port: int, on_url: Callable[[str], None]) -> subprocess.Popen:
        # Use official pinggy SSH endpoint per their docs
        cmd = [
            "ssh", "-p", "443",
            "-o", "StrictHostKeyChecking=no",
            "-o", "ServerAliveInterval=30",
            "-R0:localhost:{}".format(local_port),
            "free.pinggy.io", "-T"
        ]
        
        # Platform-specific process group creation
        popen_kwargs = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
            "text": True,
            "bufsize": 1,
            "stdin": subprocess.DEVNULL,
        }
        if platform.system() == "Windows":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            popen_kwargs["preexec_fn"] = os.setsid
        
        proc = subprocess.Popen(cmd, **popen_kwargs)

        def reader():
            for line in proc.stdout:
                line = line.strip()
                if "pinggy" in line.lower():
                    matches = re.findall(r'https?://[a-zA-Z0-9._-]+\.(?:pinggy-free\.link|free\.pinggy\.net|free\.pinggy\.io)', line)
                    for match in matches:
                        on_url(match)

        threading.Thread(target=reader, daemon=True).start()
        return proc

    def is_available(self) -> bool:
        return shutil.which("ssh") is not None




class Zrok2Tunnel(TunnelProvider):
    """Zrok2 tunnel (open source, requires account)."""

    def __init__(self):
        self.binary = shutil.which("zrok") or shutil.which("zrok2") or "zrok"
        self._proc: Optional[subprocess.Popen] = None

    @staticmethod
    def _strip_ansi(text: str) -> str:
        """Strip ANSI escape sequences from text."""
        text = re.sub(r'\x1b\[[0-9;?]*[a-zA-Z]', '', text)
        text = re.sub(r'\x1b\][^\x07]*\x07', '', text)
        return text

    def start(self, local_port: int, on_url: Callable[[str], None]) -> subprocess.Popen:
        # Check if zrok environment is enabled
        try:
            result = subprocess.run(
                [self.binary, "status"],
                capture_output=True, text=True, timeout=10
            )
            output = (result.stdout or "") + (result.stderr or "")
            if "not enabled" in output.lower():
                print("\n⚠️  zrok environment is NOT enabled.")
                print("   Run 'zrok2 enable <TOKEN>' first, or use the free zrok.io service.")
                return None
        except Exception:
            pass

        cmd = [self.binary, "share", "public", f"localhost:{local_port}", "--headless"]
        
        # Platform-specific process group creation
        popen_kwargs = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
            "text": True,
            "bufsize": 1,
            "stdin": subprocess.DEVNULL,
        }
        if platform.system() == "Windows":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            popen_kwargs["preexec_fn"] = os.setsid
        
        proc = subprocess.Popen(cmd, **popen_kwargs)
        self._proc = proc

        # Non-blocking I/O setup (Unix-specific)
        if platform.system() != "Windows":
            import fcntl
            # Make stdout non-blocking so we can use select() with timeouts
            fd = proc.stdout.fileno()
            flags = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        buf = ""

        def reader():
            nonlocal buf
            while True:
                try:
                    if platform.system() != "Windows":
                        import select
                        rlist, _, _ = select.select([proc.stdout], [], [], 1.0)
                        if not rlist:
                            if proc.poll() is not None:
                                break
                            continue
                        chunk = proc.stdout.read(4096)
                    else:
                        # On Windows, just do blocking read (no fcntl/select)
                        chunk = proc.stdout.read(4096)
                except Exception:
                    chunk = None
                
                if not chunk:
                    if proc.poll() is not None:
                        break
                    if platform.system() == "Windows":
                        import time
                        time.sleep(0.1)
                    continue

                buf += chunk
                lines = buf.split("\n")
                buf = lines[-1]

                for line in lines[:-1]:
                    line = line.strip()
                    if not line:
                        continue

                    # Extract zrok hostname anywhere in the line (zrok2 outputs structured JSON)
                    m = re.search(r'[a-zA-Z0-9._-]+\.zrok\.(?:io|net)', line)
                    if m:
                        on_url(f"https://{m.group(0)}")
                        return

        threading.Thread(target=reader, daemon=True).start()
        return proc

    def is_available(self) -> bool:
        return shutil.which("zrok") is not None or shutil.which("zrok2") is not None
class NgrokTunnel(TunnelProvider):
    """ngrok tunnel (requires account)."""

    def __init__(self):
        self.binary = shutil.which("ngrok") or "ngrok"

    def start(self, local_port: int, on_url: Callable[[str], None]) -> subprocess.Popen:
        cmd = [self.binary, "http", str(local_port), "--log=stdout"]
        
        # Platform-specific process group creation
        popen_kwargs = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
            "text": True,
            "bufsize": 1,
            "stdin": subprocess.DEVNULL,
        }
        if platform.system() == "Windows":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            popen_kwargs["preexec_fn"] = os.setsid
        
        proc = subprocess.Popen(cmd, **popen_kwargs)

        # ngrok v3 uses "tunnels.session" for session-level URLs and "tunnels.tunnel" for tunnel-level URLs.
        # Output format: url=https://xxx.ngrok-free.dev  (domain is .ngrok-free.dev, not .ngrok-free.app)

        def reader():
            for line in proc.stdout:
                line = line.strip()
                if "url=" in line:
                    match = re.search(r'url=https://([a-zA-Z0-9-]+)\.ngrok-free\.(dev|app)', line)
                    if match:
                        on_url(f"https://{match.group(1)}.ngrok-free.{match.group(2)}")

        import threading
        threading.Thread(target=reader, daemon=True).start()
        return proc

    def is_available(self) -> bool:
        return shutil.which("ngrok") is not None


class TunnelManager:
    """Manages all tunnel providers."""

    PROVIDERS = {
        "cloudflare": CloudflareTunnel,
        "tailscale": TailscaleTunnel,
        "pinggy": PinggyTunnel,
        "zrok2": Zrok2Tunnel,
        "ngrok": NgrokTunnel,
    }

    def __init__(self):
        self.active_tunnel: Optional[subprocess.Popen] = None
        self.url: Optional[str] = None

    def list_providers(self):
        return {name: cls().is_available() for name, cls in self.PROVIDERS.items()}

    def start(self, provider: str, local_port: int, on_url: Callable[[str], None]) -> bool:
        if provider not in self.PROVIDERS:
            print(f"Unknown provider: {provider}")
            return False

        tunnel = self.PROVIDERS[provider]()
        if not tunnel.is_available():
            print(f"Provider '{provider}' is not available on this system.")
            system = platform.system()
            if provider == "cloudflare":
                print("Tip: Install cloudflared:")
                if system == "Windows":
                    print("  1. Download: https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe")
                    print("  2. Place in project root or add to PATH")
                elif system == "Darwin":
                    print("  brew install cloudflare/cloudflare/cloudflared")
                else:
                    print("  curl -L --output cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 && chmod +x cloudflared")
            elif provider == "tailscale":
                print("Tip: Install and start Tailscale:")
                if system == "Windows":
                    print("  1. Download: https://tailscale.com/download/windows")
                    print("  2. Run installer and login")
                elif system == "Darwin":
                    print("  brew install tailscale")
                    print("  brew services start tailscale")
                    print("  tailscale up")
                else:
                    print("  curl -fsSL https://tailscale.com/install.sh | sh")
                    print("  sudo tailscaled start")
                    print("  sudo tailscale up")
            elif provider == "zrok2":
                print("Tip: Install Zrok2 (requires account):")
                print("  https://docs.zrok.io/docs/installation/")
            elif provider == "ngrok":
                print("Tip: Install ngrok (requires account):")
                print("  https://ngrok.com/download")
            return False

        def url_handler(url: str):
            self.url = url
            on_url(url)

        try:
            self.active_tunnel = tunnel.start(local_port, url_handler)
            if self.active_tunnel is None:
                print(f"⚠️  Provider '{provider}' returned no process (may be expected for some providers)")
            return True
        except Exception as e:
            print(f"❌ Failed to start {provider} tunnel: {e}")
            return False

    def stop(self) -> None:
        if self.active_tunnel:
            try:
                # Kill the entire process group to ensure child processes die too
                pid = self.active_tunnel.pid
                if pid:
                    import signal as sig
                    try:
                        os.killpg(os.getpgid(pid), sig.SIGKILL)
                    except (ProcessLookupError, OSError):
                        # Process already gone or no process group — fall back to normal kill
                        pass
            except Exception:
                pass
            finally:
                self.active_tunnel = None
                self.url = None
