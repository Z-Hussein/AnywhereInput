"""Safe print utilities for Windows consoles."""

import logging
import sys as _sys
import builtins as _builtins_mod

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
    except Exception as e:
        log = logging.getLogger("anywhereinput.legacy")
        log.debug("Safe write failed: %s", e)
