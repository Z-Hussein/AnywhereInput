"""ServerProcessWorker - subprocess management."""

import os
import subprocess
import threading
from typing import Optional

from anywhereinput._constants import (
    DEFAULT_PORT,
    DEFAULT_FPS,
    DEFAULT_QUALITY,
    DEFAULT_SCALE,
)
from PyQt6.QtCore import QThread, pyqtSignal

from ._utils import _PROJECT_ROOT


class ServerProcessWorker(QThread):
    """Runs `anywhereinput` server as a subprocess and streams output."""

    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)  # "running", "stopped"

    def __init__(
        self,
        port: int = DEFAULT_PORT,
        tunnel: str = "local",
        fps: int = DEFAULT_FPS,
        quality: int = DEFAULT_QUALITY,
        scale: float = DEFAULT_SCALE,
    ):
        super().__init__()
        self._port = port
        self._tunnel = tunnel
        self._fps = fps
        self._quality = quality
        self._scale = scale
        self._proc: Optional[subprocess.Popen[str]] = None
        self._running = False

    def run(self) -> None:
        cmd = [
            "anywhereinput",
            "--tunnel",
            self._tunnel,
            "--host",
            "127.0.0.1",
            "--port",
            str(self._port),
            "--fps",
            str(self._fps),
            "--quality",
            str(self._quality),
            "--scale",
            str(self._scale),
            "--log-level",
            "INFO",
        ]
        cmd_str = " ".join(cmd)
        self.log_signal.emit(f"[CMD] {cmd_str}")

        try:
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"

            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=0,
                cwd=str(_PROJECT_ROOT),
                env=env,
            )
        except Exception as e:
            self.log_signal.emit(f"[ERR] Failed to start server: {e}")
            return

        self._running = True
        self.status_signal.emit("running")

        def reader():
            for line in iter(self._proc.stdout.readline, ""):
                stripped = line.rstrip("\n\r")
                if stripped:
                    self.log_signal.emit(stripped)

        t = threading.Thread(target=reader, daemon=True)
        t.start()

        self._proc.wait()
        self._running = False
        self.status_signal.emit("stopped")
        self.log_signal.emit("[INFO] Server process exited.")

    def stop(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                try:
                    self._proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    pass
            if self._proc.stdout:
                try:
                    self._proc.stdout.close()
                except Exception:
                    pass
        self._running = False

    @property
    def is_running(self) -> bool:
        if self._proc is None:
            return False
        return self._proc.poll() is None
