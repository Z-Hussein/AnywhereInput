"""Tests for safe_print / safe_print_stderr in __init__.py (Windows encoding resilience)."""
import sys
from pathlib import Path
from unittest import mock

src = Path(__file__).parent.parent / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

import pytest


def test_module_version():
    """__version__ should be set."""
    from anywhereinput import __version__
    assert isinstance(__version__, str)
    parts = __version__.split(".")
    assert len(parts) >= 2


def test_module_author():
    """__author__ should be set."""
    from anywhereinput import __author__
    assert isinstance(__author__, str)
    assert len(__author__) > 0


def test_module_license():
    """__license__ should be set."""
    from anywhereinput import __license__
    assert isinstance(__license__, str)


def test_safe_print_is_callable():
    """safe_print must be callable."""
    from anywhereinput import safe_print
    assert callable(safe_print)


def test_safe_print_stderr_is_callable():
    """safe_print_stderr must be callable."""
    from anywhereinput import safe_print_stderr
    assert callable(safe_print_stderr)


def test_safe_print_does_not_crash_with_emoji():
    """safe_print handles emoji without crashing."""
    from anywhereinput import safe_print
    # Should not raise UnicodeEncodeError on any platform
    try:
        safe_print("🦾 hello \u00e9\u00e8\u00ea")
    except Exception:
        pytest.fail("safe_print crashed with emoji")


def test_safe_print_stderr_does_not_crash_with_emoji():
    """safe_print_stderr handles emoji without crashing."""
    from anywhereinput import safe_print_stderr
    try:
        safe_print_stderr("\u274c error \ud83d\udea8")
    except Exception:
        pytest.fail("safe_print_stderr crashed with emoji")


def test_safe_print_with_various_types():
    """safe_print handles int, float, bool, None without crashing."""
    from anywhereinput import safe_print
    try:
        safe_print(42, 3.14, True, None)
    except Exception:
        pytest.fail("safe_print crashed with mixed types")


def test_safe_print_with_tuple():
    """safe_print handles tuple arguments without crashing."""
    from anywhereinput import safe_print
    try:
        safe_print((1, 2, 3))
    except Exception:
        pytest.fail("safe_print crashed with tuple")


def test_safe_print_with_dict():
    """safe_print handles dict arguments without crashing."""
    from anywhereinput import safe_print
    try:
        safe_print({"key": "value"})
    except Exception:
        pytest.fail("safe_print crashed with dict")


def test_safe_print_with_list():
    """safe_print handles list arguments without crashing."""
    from anywhereinput import safe_print_stderr
    try:
        safe_print_stderr([1, 2, 3])
    except Exception:
        pytest.fail("safe_print_stderr crashed with list")


def test_safe_print_with_empty_args():
    """safe_print works with no arguments (prints newline)."""
    from anywhereinput import safe_print
    try:
        safe_print()
    except Exception:
        pytest.fail("safe_print crashed with empty args")


def test_safe_print_stderr_with_empty_args():
    """safe_print_stderr works with no arguments."""
    from anywhereinput import safe_print_stderr
    try:
        safe_print_stderr()
    except Exception:
        pytest.fail("safe_print_stderr crashed with empty args")


def test_safe_print_with_sep_end_kwargs():
    """safe_print passes sep and end through correctly."""
    from anywhereinput import safe_print
    try:
        safe_print("a", "b", sep="|", end="!")
    except Exception:
        pytest.fail("safe_print crashed with sep/end kwargs")


def test_safe_print_stderr_with_long_string():
    """safe_print_stderr handles very long strings."""
    from anywhereinput import safe_print_stderr
    try:
        safe_print_stderr("x" * 10000)
    except Exception:
        pytest.fail("safe_print_stderr crashed with long string")


def test_safe_print_with_newlines():
    """safe_print handles strings containing newlines."""
    from anywhereinput import safe_print
    try:
        safe_print("line1\nline2\r\nline3")
    except Exception:
        pytest.fail("safe_print crashed with embedded newlines")


def test_safe_print_stderr_with_special_chars():
    """safe_print_stderr handles backslashes and special chars."""
    from anywhereinput import safe_print_stderr
    try:
        safe_print_stderr("\\n\\t\\r\\\\/")
    except Exception:
        pytest.fail("safe_print_stderr crashed with special chars")


def test_module_imports_cleanly():
    """The anywhereinput package must import without side effects."""
    # Re-import should not raise
    import importlib
    import anywhereinput
    importlib.reload(anywhereinput)
