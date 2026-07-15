"""Pytest configuration for AnywhereInput - mocks pyautogui/mss/PIL before imports."""
import sys
from pathlib import Path

src = Path(__file__).parent.parent / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

import types

# ═══ Mock pyautogui ══════════════════════════════════════════════════════
class _PG:
    FAILSAFE = False
    @staticmethod
    def size(): return (1920, 1080)
    @staticmethod
    def position(): return (960, 540)
    @staticmethod
    def moveTo(*a, **k): pass
    @staticmethod
    def mouseDown(*a, **k): pass
    @staticmethod
    def mouseUp(*a, **k): pass
    @staticmethod
    def click(*a, **k): pass
    @staticmethod
    def scroll(*a, **k): pass
    @staticmethod
    def press(*a, **k): pass
    @staticmethod
    def typewrite(*a, **k): pass
    @staticmethod
    def hotkey(*a, **k): pass

_pg = types.ModuleType('pyautogui')
for _n in dir(_PG):
    if not _n.startswith('_'): setattr(_pg, _n, getattr(_PG, _n))
sys.modules['pyautogui'] = _pg

# ═══ Mock PIL / PIL.ImageDraw ════════════════════════════════════════════
class _Img:
    """Minimal fake Pillow Image that writes a JPEG header to file_obj."""
    Resampling = type('R', (), {'NEAREST': 0, 'BILINEAR': 2, 'BICUBIC': 3, 'LANCZOS': 4})

    def __init__(self, w=1920, h=1080):
        self.width, self.height = w, h
        self.size = (w, h)
        self.format = "JPEG"

    @classmethod
    def new(cls, mode, size, color=None):
        """Create a new image - used by headless fallback."""
        w, h = size if isinstance(size, tuple) else (size, size)
        return cls(w, h)

    @classmethod
    def frombytes(cls, mode, size, data, *args, **kwargs):
        return cls(size[0], size[1])

    @staticmethod
    def open(f, *args, **kwargs):
        img = _Img()
        img.format = "JPEG"
        img.size = (1920, 1080)
        return img

    def save(self, file_obj, fmt="JPEG", quality=95, **kw):
        # Write a minimal valid JPEG (FF D8 FF E0 header) to the buffer
        # Make it large enough (>100 bytes) to pass server validation
        h = b'\xff\xd8\xff\xe0' + b'\x00' * 150
        if hasattr(file_obj, 'write'):
            file_obj.write(h)

    def resize(self, size_or_tuple, resampling=None, **kw):
        s = size_or_tuple if isinstance(size_or_tuple, tuple) else (size_or_tuple[0], size_or_tuple[1])
        return _Img(s[0], s[1])
        s = size_or_tuple if isinstance(size_or_tuple, tuple) else (size_or_tuple[0], size_or_tuple[1])
        return _Img(size[0], size[1])

_PIL = types.ModuleType('PIL')
_PIL.Image = _Img
sys.modules['PIL'] = _PIL

class _ID(types.ModuleType):
    @staticmethod
    def Draw(*a, **k):
        d = types.SimpleNamespace()
        d.line = lambda *a2, **k2: None
        d.ellipse = lambda *a2, **k2: None
        return d
sys.modules['PIL.ImageDraw'] = _ID('PIL.ImageDraw')

# ═══ Mock mss ════════════════════════════════════════════════════════════
class _MSS:
    class _Sct:
        # mss always returns a virtual-desktop entry at index 0 (same dims as real monitors),
        # followed by real physical monitors.  The ScreenCapture code skips index 0 via
        # `monitor_count = max(0, len(monitors) - 1)` so we need ≥2 valid entries here.
        # Virtual desktop has combined width; each monitor must have unique (left,top,w,h)
        # to survive the dedup step in _build_engine.
        monitors = [
            {"left": 0, "top": 0, "width": 3840, "height": 1080},   # virtual desktop
            {"left": 0, "top": 0, "width": 1920, "height": 1080},   # monitor 1
        ]
        def grab(self, region=None):
            s = types.SimpleNamespace()
            s.left = 0; s.top = 0; s.width = 1920; s.height = 1080; s.size = (1920, 1080)
            # Generate non-black frame data (simple pattern) to avoid black-frame detection
            # Use a small repeating pattern instead of full gradient for speed
            frame_size = 1920 * 1080 * 4
            # Create pattern: 4 bytes per pixel (BGRA), repeating every 4 pixels
            pattern = bytes([i % 256 for i in range(4)]) * (frame_size // 4)
            s.bgra = pattern
            s.raw = s.bgra
            return s
        def close(self): pass
    @staticmethod
    def mss():
        return _MSS._Sct()
sys.modules['mss'] = _MSS

# ═══ Mock screeninfo ═════════════════════════════════════════════════════
class _Mon:
    def __init__(self):
        self.left, self.top = 0, 0
        self.width, self.height = 1920, 1080
        self.index = 0
        self.primary = True
_si = types.ModuleType('screeninfo')
_si.get_monitors = lambda: [_Mon()]
sys.modules['screeninfo'] = _si

# ═══ Fixtures ──────────────────────────────────────────────────────────────

import socket
import pytest


@pytest.fixture
def free_tcp_port():
    """Allocate and return a free TCP port on 127.0.0.1; close it immediately.

    Used by ws_test.py for ephemeral WebSocket server binding.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    sock.close()
    yield port
    # No cleanup needed - port is already released when the socket closed
