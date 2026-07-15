"""Unified tunnel provider management."""

import json
import os
import subprocess
import platform
import shutil
import time
import requests
import threading
import re
import signal
import atexit
import weakref
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Callable, Union, Any

from anywhereinput import safe_print, safe_print_stderr

_fcntl: Any = None
try:
    import fcntl as _fcntl
except ImportError:
    pass


def _get_data_dir() -> Path:
    """Get platform-appropriate user data directory for storing downloaded binaries."""
    if platform.system() == "Windows":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~\\AppData\\Local")
    elif platform.system() == "Darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    data_dir = Path(base) / "anywhereinput"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


# Sentinel to indicate "success" for tunnel providers that don't spawn a process
class _NoProcessTunnel:
    pass


NO_PROCESS = _NoProcessTunnel()


class TunnelProvider(ABC):
    """Abstract base for tunnel providers."""

    @abstractmethod
    def start(
        self, local_host: str, local_port: int, on_url: Callable[[str], None]
    ) -> Union[subprocess.Popen, _NoProcessTunnel, None]:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass


class CloudflareTunnel(TunnelProvider):
    """Cloudflare Tunnel (free, no account)."""

    _DATA_DIR = _get_data_dir()

    def __init__(self):
        self.binary = self._find_or_download()
        # Ensure binary is absolute path and exists
        self.binary = self._resolve_binary_path(self.binary)

    def _resolve_binary_path(self, binary: str) -> str:
        """Resolve binary path to absolute path, checking multiple locations."""
        # If already absolute and exists, use it
        if os.path.isabs(binary) and os.path.isfile(binary):
            return binary
        # Try resolving relative to data dir
        candidate = self._DATA_DIR / binary
        if candidate.is_file():
            return str(candidate.resolve())
        # Try with .exe extension on Windows
        if platform.system() == "Windows" and not binary.endswith(".exe"):
            candidate = self._DATA_DIR / (binary + ".exe")
            if candidate.is_file():
                return str(candidate.resolve())
        # Fall back to original (will fail later with clear error)
        return binary

    def _find_or_download(self) -> str:
        name = "cloudflared.exe" if platform.system() == "Windows" else "cloudflared"
        # Check system PATH first
        path = shutil.which(name)
        if path and os.path.isfile(path):
            return path
        # Check data directory
        local = self._DATA_DIR / name
        if local.is_file():
            return str(local.resolve())
        # Download if not found
        return self._download()

    def _download(self) -> str:
        safe_print("[Cloudflare] Downloading cloudflared...")
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
            filename = (
                "cloudflared-linux-amd64"
                if system != "darwin"
                else "cloudflared-darwin-amd64.tgz"
            )

        temp_target = self._DATA_DIR / f".{filename}.tmp"
        try:
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            with open(temp_target, "wb") as f:
                f.write(r.content)
            if system != "windows":
                os.chmod(temp_target, 0o755)
        except Exception as e:
            temp_target.unlink(missing_ok=True)  # clean up partial file
            raise FileNotFoundError(f"cloudflared download failed: {e}")

        if system == "darwin" and filename.endswith(".tgz"):
            import tarfile

            with tarfile.open(temp_target, "r:gz") as tar:
                for member in tar.getmembers():
                    if member.isfile() and "cloudflared" in member.name.lower():
                        tar.extract(member, self._DATA_DIR)
                        break
            temp_target.unlink(missing_ok=True)
            executable = "cloudflared"
        else:
            # Rename to standard executable name
            if system == "windows":
                executable = "cloudflared.exe"
            else:
                executable = "cloudflared"
            final_target = self._DATA_DIR / executable
            temp_target.rename(final_target)

        abs_path = str((self._DATA_DIR / executable).resolve())
        safe_print(f"[Cloudflare] Saved to {abs_path}")
        return abs_path

    def start(
        self, local_host: str, local_port: int, on_url: Callable[[str], None]
    ) -> Union[subprocess.Popen, _NoProcessTunnel]:
        # Re-resolve binary path in case it was moved
        self.binary = self._resolve_binary_path(self.binary)

        if not os.path.isfile(self.binary) and shutil.which(self.binary) is None:
            error_msg = f"cloudflared binary not found at '{self.binary}'"
            safe_print(f"\n❌ {error_msg}")
            safe_print(f"   Data directory: {self._DATA_DIR}")
            safe_print(f"   Files in data dir: {list(self._DATA_DIR.iterdir()) if self._DATA_DIR.exists() else 'N/A'}")
            raise FileNotFoundError(error_msg)

        cmd = [self.binary, "tunnel", "--url", f"http://{local_host}:{local_port}"]

        popen_kwargs: dict[str, Any] = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
            "text": True,
            "bufsize": 1,
            "stdin": subprocess.DEVNULL,
        }
        if platform.system() == "Windows":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
        else:
            popen_kwargs["preexec_fn"] = os.setsid  # type: ignore[assignment]

        try:
            proc = subprocess.Popen(cmd, **popen_kwargs)  # type: ignore[arg-type]
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
                        match = re.search(
                            r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line
                        )
                        if match:
                            url_found = True
                            safe_print(f"✅ [Cloudflare] Tunnel URL: {match.group(0)}")
                            on_url(match.group(0))
                            continue

                        # Stay silent during normal operation; keep only last line for failure context.
                        last_non_url_line = line
                if line_count == 0:
                    returncode = proc.poll()
                    if returncode is not None:
                        safe_print(
                            f"❌ [Cloudflare] Process exited with code {returncode}"
                        )
                elif not url_found:
                    returncode = proc.poll()
                    if returncode is not None and returncode != 0:
                        safe_print(
                            f"❌ [Cloudflare] Failed to establish tunnel (exit code {returncode})"
                        )
                        if last_non_url_line:
                            safe_print(
                                f"   Last cloudflared output: {last_non_url_line}"
                            )
            except Exception as e:
                safe_print(f"❌ [Cloudflare] Reader error: {e}")

        threading.Thread(target=reader, daemon=True).start()
        time.sleep(1)
        if proc.poll() is not None:
            raise RuntimeError(
                f"cloudflared exited immediately with code {proc.returncode}"
            )
        return proc

    def is_available(self) -> bool:
        try:
            self._find_or_download()
            return True
        except FileNotFoundError:
            return False


class TailscaleTunnel(TunnelProvider):
    """Tailscale tailnet - peer-to-peer via Tailscale IP."""

    def start(
        self, local_host: str, local_port: int, on_url: Callable[[str], None]
    ) -> Union[subprocess.Popen, _NoProcessTunnel, None]:
        # Use `tailscale status --json` instead of socket.getaddrinfo(hostname)
        # - the latter is unreliable because hostname resolution often returns
        # the loopback or LAN IP, never the 100.x tailnet address.
        try:
            result = subprocess.run(
                ["tailscale", "status", "--json"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                safe_print(
                    "⚠️  Tailscale status returned non-zero - is the daemon running?"
                )
                return None

            data = json.loads(result.stdout)
            self_data = data.get("Self", {})
            tailnet_ips = self_data.get("TailscaleIPs", [])

            if not tailnet_ips:
                # Try BackendState as fallback
                backend_state = self_data.get("BackendState", "")
                online = self_data.get("Online")
                safe_print(
                    f"⚠️  No Tailscale IPs found (BackendState={backend_state}, Online={online})"
                )
                return None

            # Pick the IPv4 tailnet IP
            ip = next((a for a in tailnet_ips if ":" not in a), tailnet_ips[0])
            safe_print("\n🔷 Tailscale network active")
            safe_print(f"   Tailnet IP: {ip}")
            safe_print(f"   Server port: {local_port}")
            on_url(f"{ip}:{local_port}")
        except Exception as e:
            safe_print_stderr(f"\n⚠️  Could not get tailnet IP: {e}")
            return None
        return NO_PROCESS

    def is_available(self) -> bool:
        if shutil.which("tailscale") is None:
            return False
        try:
            result = subprocess.run(
                ["tailscale", "status", "--json"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                self_data = data.get("Self", {})
                authenticated = self_data.get("Status") == "authenticated"
                online = self_data.get("Online") is True
                backend_running = (
                    self_data.get("BackendState") == "Running"
                    and len(self_data.get("TailscaleIPs", [])) > 0
                )
                return authenticated or online or backend_running
        except Exception:
            pass
        return False


class PinggyTunnel(TunnelProvider):
    """Pinggy.io tunnel (SSH-based, no install)."""

    def start(
        self, local_host: str, local_port: int, on_url: Callable[[str], None]
    ) -> Union[subprocess.Popen, _NoProcessTunnel, None]:
        cmd = [
            "ssh",
            "-p",
            "443",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "ServerAliveInterval=30",
            f"-R0:{local_host}:{local_port}",
            "free.pinggy.io",
            "-T",
        ]

        popen_kwargs: dict[str, Any] = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
            "text": True,
            "bufsize": 1,
            "stdin": subprocess.DEVNULL,
        }
        if platform.system() == "Windows":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
        else:
            popen_kwargs["preexec_fn"] = os.setsid  # type: ignore[assignment]

        proc = subprocess.Popen(cmd, **popen_kwargs)  # type: ignore[arg-type]

        def reader():
            for line in proc.stdout:
                line = line.strip()
                matches = re.findall(
                    r"https?://[a-zA-Z0-9._-]+\.(?:pinggy-free\.link|free\.pinggy\.net|free\.pinggy\.io)",
                    line,
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
        text = re.sub(r"\x1b\[[0-9;?]*[a-zA-Z]", "", text)
        text = re.sub(r"\x1b\][^\x07]*\x07", "", text)
        return text

    def start(
        self, local_host: str, local_port: int, on_url: Callable[[str], None]
    ) -> Union[subprocess.Popen, _NoProcessTunnel, None]:
        try:
            result = subprocess.run(
                [self.binary, "status"], capture_output=True, text=True, timeout=10
            )
            output = (result.stdout or "") + (result.stderr or "")
            if "not enabled" in output.lower():
                safe_print("\n⚠️  zrok environment is NOT enabled.")
                return None
        except Exception:
            pass

        cmd = [
            "zrok2",
            "share",
            "public",
            f"{local_host}:{local_port}",
            "--headless",
        ]

        popen_kwargs: dict[str, Any] = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
            "text": True,
            "bufsize": 1,
            "stdin": subprocess.DEVNULL,
        }
        if platform.system() == "Windows":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
        else:
            popen_kwargs["preexec_fn"] = os.setsid  # type: ignore[assignment]

        proc = subprocess.Popen(cmd, **popen_kwargs)  # type: ignore[arg-type]
        self._proc = proc

        if _fcntl is not None and proc.stdout is not None:
            fd = proc.stdout.fileno()
            flags = _fcntl.fcntl(fd, _fcntl.F_GETFL)
            _fcntl.fcntl(fd, _fcntl.F_SETFL, flags | os.O_NONBLOCK)

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
                    m = re.search(r"[a-zA-Z0-9._-]+\.zrok\.(?:io|net)", line)
                    if m:
                        # Don't return - keep reading for potential reconnect/updates.
                        on_url(f"https://{m.group(0)}")

        threading.Thread(target=reader, daemon=True).start()
        return proc

    def is_available(self) -> bool:
        return shutil.which("zrok") is not None or shutil.which("zrok2") is not None


class TunnelManager:
    """Manages all tunnel providers with automatic cleanup."""

    PROVIDERS = {
        "cloudflare": CloudflareTunnel,
        "tailscale": TailscaleTunnel,
        "pinggy": PinggyTunnel,
        "zrok2": Zrok2Tunnel,
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
                    except KeyboardInterrupt:
                        return
                    except subprocess.TimeoutExpired:
                        proc.kill()
                else:
                    try:
                        os.killpg(os.getpgid(pid), signal.SIGTERM)
                        proc.wait(timeout=3)
                    except KeyboardInterrupt:
                        return
                    except (ProcessLookupError, OSError, subprocess.TimeoutExpired):
                        proc.kill()
                        proc.wait(timeout=1)
        except BaseException:
            pass

    def list_providers(self):
        return {name: cls().is_available() for name, cls in self.PROVIDERS.items()}

    def start(
        self,
        provider: str,
        bind_host: str,
        local_port: int,
        on_url: Callable[[str], None],
    ) -> bool:
        if provider not in self.PROVIDERS:
            safe_print(f"Unknown provider: {provider}")
            return False

        tunnel = self.PROVIDERS[provider]()  # type: ignore[abstract]
        if not tunnel.is_available():
            safe_print(f"Provider '{provider}' is not available on this system.")
            return False

        def url_handler(url: str):
            self.url = url
            on_url(url)

        try:
            upstream_host = self._resolve_upstream_host(provider, bind_host)
            result = tunnel.start(upstream_host, local_port, url_handler)
            if result is not None and result is not NO_PROCESS:
                # Clean up any previously active tunnel before setting new one
                self.stop()
                self.active_tunnel = result  # type: ignore[assignment]
                self._all_procs.add(self.active_tunnel)
                return True
            elif result is NO_PROCESS:
                # Provider like Tailscale works without a process object - success!
                return True
            else:
                safe_print(f"⚠️  {provider} tunnel returned no process - stopped.")
                return False
        except Exception as e:
            safe_print(f"❌ Failed to start {provider} tunnel: {e}")
            return False

    def stop(self) -> None:
        if self.active_tunnel:
            self._kill_process_group(self.active_tunnel)
            self.active_tunnel = None
            self.url = None
