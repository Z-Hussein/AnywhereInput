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
import signal
import atexit
import weakref
from pathlib import Path
from typing import Optional, Callable
from abc import ABC, abstractmethod


class TunnelProvider(ABC):
    """Abstract base for tunnel providers."""

    @abstractmethod
    def start(self, local_host: str, local_port: int, on_url: Callable[[str], None]) -> subprocess.Popen:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass


class CloudflareTunnel(TunnelProvider):
    """Cloudflare Tunnel (free, no account)."""

    _SCRIPT_DIR = Path(__file__).resolve().parent.parent  # project root

    def __init__(self):
        self.binary = self._find_or_download()
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
        path = shutil.which(name)
        if path:
            return path
        local = self._SCRIPT_DIR / name
        if local.exists():
            return str(local.resolve())
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

        if system == "darwin" and filename.endswith(".tgz"):
            import tarfile
            with tarfile.open(target, 'r:gz') as tar:
                for member in tar.getmembers():
                    if member.isfile() and 'cloudflared' in member.name.lower():
                        tar.extract(member, self._SCRIPT_DIR)
                        break
            target.unlink()
            executable = "cloudflared"
        else:
            exec_path = self._SCRIPT_DIR / "cloudflared"
            Path(target).rename(exec_path)
            executable = "cloudflared"

        abs_path = str((self._SCRIPT_DIR / executable).resolve())
        print(f"[Cloudflare] Saved to {abs_path}")
        return abs_path

    def start(self, local_host: str, local_port: int, on_url: Callable[[str], None]) -> subprocess.Popen:
        if not os.path.isfile(self.binary) and shutil.which(self.binary) is None:
            error_msg = f"cloudflared binary not found at '{self.binary}'"
            print(f"\n❌ {error_msg}")
            raise FileNotFoundError(error_msg)

        cmd = [self.binary, "tunnel", "--url", f"http://{local_host}:{local_port}"]

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
            raise RuntimeError(f"Failed to start cloudflared: {e}")

        def reader():
            try:
                line_count = 0
                url_found = False
                last_non_url_line = ""
                for line in proc.stdout:
                    line = line.strip()
                    if line:
                        line_count += 1
                        match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
                        if match:
                            url_found = True
                            print(f"✅ [Cloudflare] Tunnel URL: {match.group(0)}")
                            on_url(match.group(0))
                            continue

                        # Stay silent during normal operation; keep only last line for failure context.
                        last_non_url_line = line
                if line_count == 0:
                    returncode = proc.poll()
                    if returncode is not None:
                        print(f"❌ [Cloudflare] Process exited with code {returncode}")
                elif not url_found:
                    returncode = proc.poll()
                    if returncode is not None and returncode != 0:
                        print(f"❌ [Cloudflare] Failed to establish tunnel (exit code {returncode})")
                        if last_non_url_line:
                            print(f"   Last cloudflared output: {last_non_url_line}")
            except Exception as e:
                print(f"❌ [Cloudflare] Reader error: {e}")

        threading.Thread(target=reader, daemon=True).start()
        time.sleep(1)
        if proc.poll() is not None:
            raise RuntimeError(f"cloudflared exited immediately with code {proc.returncode}")
        return proc

    def is_available(self) -> bool:
        try:
            self._find_or_download()
            return True
        except FileNotFoundError:
            return False


class TailscaleTunnel(TunnelProvider):
    """Tailscale tailnet — peer-to-peer via Tailscale IP."""

    def start(self, local_host: str, local_port: int, on_url: Callable[[str], None]) -> subprocess.Popen:
        try:
            hostname = socket.gethostname()
            addrs = socket.getaddrinfo(hostname, None, family=socket.AF_INET)
            for addr_info in addrs:
                ip = addr_info[4][0]
                if ip.startswith("100."):
                    print(f"\n🔷 Tailscale network active")
                    print(f"   Tailnet IP: {ip}")
                    print(f"   Server port: {local_port}")
                    on_url(f"{ip}:{local_port}")
                    break
            else:
                print("\n⚠️  Tailscale is installed but no tailnet IP detected.")
                return None
        except Exception as e:
            print(f"\n⚠️  Could not get tailnet IP: {e}")
            return None
        return None

    def is_available(self) -> bool:
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

    def start(self, local_host: str, local_port: int, on_url: Callable[[str], None]) -> subprocess.Popen:
        cmd = [
            "ssh", "-p", "443",
            "-o", "StrictHostKeyChecking=no",
            "-o", "ServerAliveInterval=30",
            f"-R0:{local_host}:{local_port}",
            "free.pinggy.io", "-T"
        ]

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
                matches = re.findall(
                    r'https?://[a-zA-Z0-9._-]+\.(?:pinggy-free\.link|free\.pinggy\.net|free\.pinggy\.io)',
                    line
                )
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
        text = re.sub(r'\x1b\[[0-9;?]*[a-zA-Z]', '', text)
        text = re.sub(r'\x1b\][^\x07]*\x07', '', text)
        return text

    def start(self, local_host: str, local_port: int, on_url: Callable[[str], None]) -> subprocess.Popen:
        try:
            result = subprocess.run(
                [self.binary, "status"],
                capture_output=True, text=True, timeout=10
            )
            output = (result.stdout or "") + (result.stderr or "")
            if "not enabled" in output.lower():
                print("\n⚠️  zrok environment is NOT enabled.")
                return None
        except Exception:
            pass

        cmd = [self.binary, "share", "public", f"{local_host}:{local_port}", "--headless"]

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

        if platform.system() != "Windows":
            import fcntl
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
                        chunk = proc.stdout.read(4096)
                except Exception:
                    chunk = None

                if not chunk:
                    if proc.poll() is not None:
                        break
                    if platform.system() == "Windows":
                        time.sleep(0.1)
                    continue

                buf += chunk
                lines = buf.split("\n")
                buf = lines[-1]

                for line in lines[:-1]:
                    line = line.strip()
                    if not line:
                        continue
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

    def start(self, local_host: str, local_port: int, on_url: Callable[[str], None]) -> subprocess.Popen:
        cmd = [self.binary, "http", f"{local_host}:{local_port}", "--log=stdout"]

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
                if "url=" in line:
                    match = re.search(r'url=https://([a-zA-Z0-9-]+)\.ngrok-free\.(dev|app)', line)
                    if match:
                        on_url(f"https://{match.group(1)}.ngrok-free.{match.group(2)}")

        threading.Thread(target=reader, daemon=True).start()
        return proc

    def is_available(self) -> bool:
        return shutil.which("ngrok") is not None


class TunnelManager:
    """Manages all tunnel providers with automatic cleanup."""

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
        self._all_procs = weakref.WeakSet()
        atexit.register(self._cleanup_all)

    @staticmethod
    def resolve_bind_host(provider: Optional[str], requested_host: str) -> str:
        """Choose a server bind host that works for the selected provider."""
        if provider == "tailscale" and requested_host in ("127.0.0.1", "localhost"):
            # Tailnet clients need a non-loopback bind target.
            return "0.0.0.0"
        return requested_host

    @staticmethod
    def _resolve_upstream_host(provider: str, bind_host: str) -> str:
        """Choose which local address the tunnel process should dial."""
        if provider == "tailscale":
            return bind_host

        # For local tunnel agents, prefer loopback when server listens on all interfaces.
        if bind_host in ("0.0.0.0", "::", "localhost"):
            return "127.0.0.1"
        return bind_host

    def _cleanup_all(self):
        """Kill all tracked subprocesses on exit."""
        for proc in list(self._all_procs):
            try:
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=1)
            except Exception:
                pass

    def _kill_process_group(self, proc):
        """Kill process and its children."""
        if proc is None:
            return
        try:
            pid = proc.pid
            if pid:
                if platform.system() == "Windows":
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                else:
                    try:
                        os.killpg(os.getpgid(pid), signal.SIGTERM)
                        proc.wait(timeout=3)
                    except (ProcessLookupError, OSError, subprocess.TimeoutExpired):
                        proc.kill()
                        proc.wait(timeout=1)
        except Exception:
            pass

    def list_providers(self):
        return {name: cls().is_available() for name, cls in self.PROVIDERS.items()}

    def start(self, provider: str, bind_host: str, local_port: int, on_url: Callable[[str], None]) -> bool:
        if provider not in self.PROVIDERS:
            print(f"Unknown provider: {provider}")
            return False

        tunnel = self.PROVIDERS[provider]()
        if not tunnel.is_available():
            print(f"Provider '{provider}' is not available on this system.")
            return False

        def url_handler(url: str):
            self.url = url
            on_url(url)

        try:
            upstream_host = self._resolve_upstream_host(provider, bind_host)
            self.active_tunnel = tunnel.start(upstream_host, local_port, url_handler)
            if self.active_tunnel is not None:
                self._all_procs.add(self.active_tunnel)
            return True
        except Exception as e:
            print(f"❌ Failed to start {provider} tunnel: {e}")
            return False

    def stop(self) -> None:
        if self.active_tunnel:
            self._kill_process_group(self.active_tunnel)
            self.active_tunnel = None
            self.url = None"""Unified tunnel provider management."""

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
import atexit
import weakref
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
        path = shutil.which(name)
        if path:
            return path
        local = self._SCRIPT_DIR / name
        if local.exists():
            return str(local.resolve())
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

        if system == "darwin" and filename.endswith(".tgz"):
            import tarfile
            with tarfile.open(target, 'r:gz') as tar:
                for member in tar.getmembers():
                    if member.isfile() and 'cloudflared' in member.name.lower():
                        tar.extract(member, self._SCRIPT_DIR)
                        break
            target.unlink()
            executable = "cloudflared"
        else:
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
            raise FileNotFoundError(error_msg)

        cmd = [self.binary, "tunnel", "--url", f"http://127.0.0.1:{local_port}"]

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
            raise RuntimeError(f"Failed to start cloudflared: {e}")

        def reader():
            try:
                line_count = 0
                url_found = False
                last_non_url_line = ""
                for line in proc.stdout:
                    line = line.strip()
                    if line:
                        line_count += 1
                        match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
                        if match:
                            url_found = True
                            print(f"✅ [Cloudflare] Tunnel URL: {match.group(0)}")
                            on_url(match.group(0))
                            continue

                        # Stay silent during normal operation; keep only last line for failure context.
                        last_non_url_line = line
                if line_count == 0:
                    returncode = proc.poll()
                    if returncode is not None:
                        print(f"❌ [Cloudflare] Process exited with code {returncode}")
                elif not url_found:
                    returncode = proc.poll()
                    if returncode is not None and returncode != 0:
                        print(f"❌ [Cloudflare] Failed to establish tunnel (exit code {returncode})")
                        if last_non_url_line:
                            print(f"   Last cloudflared output: {last_non_url_line}")
            except Exception as e:
                print(f"❌ [Cloudflare] Reader error: {e}")

        threading.Thread(target=reader, daemon=True).start()
        time.sleep(1)
        if proc.poll() is not None:
            raise RuntimeError(f"cloudflared exited immediately with code {proc.returncode}")
        return proc

    def is_available(self) -> bool:
        try:
            self._find_or_download()
            return True
        except FileNotFoundError:
            return False


class TailscaleTunnel(TunnelProvider):
    """Tailscale tailnet — peer-to-peer via Tailscale IP."""

    def start(self, local_port: int, on_url: Callable[[str], None]) -> subprocess.Popen:
        try:
            hostname = socket.gethostname()
            addrs = socket.getaddrinfo(hostname, None, family=socket.AF_INET)
            for addr_info in addrs:
                ip = addr_info[4][0]
                if ip.startswith("100."):
                    print(f"\n🔷 Tailscale network active")
                    print(f"   Tailnet IP: {ip}")
                    print(f"   Server port: {local_port}")
                    on_url(f"{ip}:{local_port}")
                    break
            else:
                print("\n⚠️  Tailscale is installed but no tailnet IP detected.")
                return None
        except Exception as e:
            print(f"\n⚠️  Could not get tailnet IP: {e}")
            return None
        return None

    def is_available(self) -> bool:
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
        cmd = [
            "ssh", "-p", "443",
            "-o", "StrictHostKeyChecking=no",
            "-o", "ServerAliveInterval=30",
            f"-R0:localhost:{local_port}",
            "free.pinggy.io", "-T"
        ]

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
                matches = re.findall(
                    r'https?://[a-zA-Z0-9._-]+\.(?:pinggy-free\.link|free\.pinggy\.net|free\.pinggy\.io)',
                    line
                )
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
        text = re.sub(r'\x1b\[[0-9;?]*[a-zA-Z]', '', text)
        text = re.sub(r'\x1b\][^\x07]*\x07', '', text)
        return text

    def start(self, local_port: int, on_url: Callable[[str], None]) -> subprocess.Popen:
        try:
            result = subprocess.run(
                [self.binary, "status"],
                capture_output=True, text=True, timeout=10
            )
            output = (result.stdout or "") + (result.stderr or "")
            if "not enabled" in output.lower():
                print("\n⚠️  zrok environment is NOT enabled.")
                return None
        except Exception:
            pass

        cmd = [self.binary, "share", "public", f"localhost:{local_port}", "--headless"]

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

        if platform.system() != "Windows":
            import fcntl
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
                        chunk = proc.stdout.read(4096)
                except Exception:
                    chunk = None

                if not chunk:
                    if proc.poll() is not None:
                        break
                    if platform.system() == "Windows":
                        time.sleep(0.1)
                    continue

                buf += chunk
                lines = buf.split("\n")
                buf = lines[-1]

                for line in lines[:-1]:
                    line = line.strip()
                    if not line:
                        continue
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
                if "url=" in line:
                    match = re.search(r'url=https://([a-zA-Z0-9-]+)\.ngrok-free\.(dev|app)', line)
                    if match:
                        on_url(f"https://{match.group(1)}.ngrok-free.{match.group(2)}")

        threading.Thread(target=reader, daemon=True).start()
        return proc

    def is_available(self) -> bool:
        return shutil.which("ngrok") is not None


class TunnelManager:
    """Manages all tunnel providers with automatic cleanup."""

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
        self._all_procs = weakref.WeakSet()
        atexit.register(self._cleanup_all)

    def _cleanup_all(self):
        """Kill all tracked subprocesses on exit."""
        for proc in list(self._all_procs):
            try:
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=1)
            except Exception:
                pass

    def _kill_process_group(self, proc):
        """Kill process and its children."""
        if proc is None:
            return
        try:
            pid = proc.pid
            if pid:
                if platform.system() == "Windows":
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                else:
                    try:
                        os.killpg(os.getpgid(pid), signal.SIGTERM)
                        proc.wait(timeout=3)
                    except (ProcessLookupError, OSError, subprocess.TimeoutExpired):
                        proc.kill()
                        proc.wait(timeout=1)
        except Exception:
            pass

    def list_providers(self):
        return {name: cls().is_available() for name, cls in self.PROVIDERS.items()}

    def start(self, provider: str, local_port: int, on_url: Callable[[str], None]) -> bool:
        if provider not in self.PROVIDERS:
            print(f"Unknown provider: {provider}")
            return False

        tunnel = self.PROVIDERS[provider]()
        if not tunnel.is_available():
            print(f"Provider '{provider}' is not available on this system.")
            return False

        def url_handler(url: str):
            self.url = url
            on_url(url)

        try:
            self.active_tunnel = tunnel.start(local_port, url_handler)
            if self.active_tunnel is not None:
                self._all_procs.add(self.active_tunnel)
            return True
        except Exception as e:
            print(f"❌ Failed to start {provider} tunnel: {e}")
            return False

    def stop(self) -> None:
        if self.active_tunnel:
            self._kill_process_group(self.active_tunnel)
            self.active_tunnel = None
            self.url = None
