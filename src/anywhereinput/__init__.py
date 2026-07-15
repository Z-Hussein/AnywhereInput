"""
AnywhereInput - Remote control your PC from any browser.

Screen streaming, pixel-perfect touch mapping, keyboard input, and mouse control.
Zero-config tunnel support: Cloudflare, Tailscale, Pinggy, Zrok2.
"""

import sys as _sys
import builtins as _builtins_mod

__version__ = "1.2.7"
__author__ = "Z-Hussein"
__license__ = "MIT"

# ── Safe print for Windows consoles that can't encode Unicode/emoji ──────────

_builtins_print = getattr(_builtins_mod, "print", None)
if _builtins_print is None:
    _builtins_print = __builtins__["print"] if isinstance(__builtins__, dict) else None


def safe_print(*args, **kwargs):
    """Print without crashing on Windows CP1252/GBK/etc. consoles."""
    _safe_write(_sys.stdout, *args, **kwargs)


def safe_print_stderr(*args, **kwargs):
    """Same as safe_print but writes to stderr."""
    _safe_write(_sys.stderr, *args, **kwargs)


def _safe_write(file, *args, **kwargs):
    if file not in (_sys.stdout, _sys.stderr):
        if _builtins_print:
            _builtins_print(*args, **kwargs)
        return
    # Try normal print first
    try:
        if _builtins_print:
            _builtins_print(*args, **kwargs)
        else:
            file.write(_sys.stdout.__class__._repr(*args))
        return
    except (UnicodeEncodeError, UnicodeError):
        pass
    # Fall back: encode each arg with replacement chars
    lines = []
    end = kwargs.get("end", "\n")
    sep = kwargs.get("sep", " ")
    for arg in args:
        if not isinstance(arg, str):
            arg = str(arg)
        enc = getattr(file, "encoding", None) or "utf-8"
        encoded = arg.encode(enc, errors="replace").decode(enc, errors="replace")
        lines.append(encoded)
    flat = sep.join(lines) + end
    try:
        file.write(flat)
        file.flush()
    except Exception:
        pass
