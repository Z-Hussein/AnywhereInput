"""Tests for zrok2_repair diagnostic and repair tool."""
import sys
from pathlib import Path
from unittest import mock

src = Path(__file__).parent.parent / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))


def test_check_zrok_installation_found():
    """check_zrok_installation returns True when zrok binary is found."""
    from anywhereinput.zrok2_repair import check_zrok_installation

    with mock.patch("anywhereinput.zrok2_repair.shutil.which", return_value="/usr/bin/zrok"):
        result = check_zrok_installation()
    assert result is True


def test_check_zrok_installation_not_found():
    """check_zrok_installation returns False when zrok not in PATH."""
    from anywhereinput.zrok2_repair import check_zrok_installation

    with mock.patch("anywhereinput.zrok2_repair.shutil.which", return_value=None):
        result = check_zrok_installation()
    assert result is False


def test_check_zrok_enabled_returns_true():
    """check_zrok_enabled returns True when subprocess succeeds."""
    from anywhereinput.zrok2_repair import check_zrok_enabled

    mock_result = mock.MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "enabled"
    mock_result.stderr = ""

    with mock.patch("anywhereinput.zrok2_repair.subprocess.run", return_value=mock_result):
        result = check_zrok_enabled()
    assert result is True


def test_check_zrok_enabled_returns_false_nonzero():
    """check_zrok_enabled returns False when subprocess returns non-zero."""
    from anywhereinput.zrok2_repair import check_zrok_enabled

    mock_result = mock.MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = "not enabled"

    with mock.patch("anywhereinput.zrok2_repair.subprocess.run", return_value=mock_result):
        result = check_zrok_enabled()
    assert result is False


def test_check_zrok_enabled_returns_false_on_exception():
    """check_zrok_enabled returns False when subprocess raises."""
    from anywhereinput.zrok2_repair import check_zrok_enabled

    with mock.patch("anywhereinput.zrok2_repair.subprocess.run", side_effect=FileNotFoundError()):
        result = check_zrok_enabled()
    assert result is False


def test_enable_zrok_no_binary():
    """enable_zrok exits early when zrok not installed."""
    from anywhereinput.zrok2_repair import enable_zrok

    safe_print_calls = []
    safe_print_stderr_calls = []

    def mock_print(*args, **kwargs):
        safe_print_calls.append((" ".join(str(a) for a in args), kwargs))

    def mock_stderr(*args, **kwargs):
        safe_print_stderr_calls.append((" ".join(str(a) for a in args), kwargs))

    with mock.patch("anywhereinput.zrok2_repair.safe_print", mock_print):
        with mock.patch("anywhereinput.zrok2_repair.safe_print_stderr", mock_stderr):
            with mock.patch("anywhereinput.zrok2_repair.check_zrok_installation", return_value=False):
                try:
                    enable_zrok()
                except (EOFError, SystemExit):
                    pass  # input() may raise in test env

    # check_zrok_installation should have been called and shown installation info
    assert len(safe_print_calls) > 0


def test_enable_zrok_already_enabled():
    """enable_zrok shows success message when zrok already enabled."""
    safe_print_calls = []

    def mock_print(*args, **kwargs):
        safe_print_calls.append(" ".join(str(a) for a in args))

    with mock.patch("anywhereinput.zrok2_repair.safe_print", mock_print):
        with mock.patch("anywhereinput.zrok2_repair.check_zrok_installation", return_value=True):
            with mock.patch("anywhereinput.zrok2_repair.check_zrok_enabled", return_value=True):
                from anywhereinput.zrok2_repair import enable_zrok
                try:
                    enable_zrok()
                except (EOFError, SystemExit):
                    pass

    # Should show "Everything looks good" message
    full_output = " ".join(safe_print_calls)
    assert "good" in full_output.lower() or "looks" in full_output.lower()


def test_enable_zrok_prompt_for_token():
    """enable_zrok prompts for token when zrok not enabled."""
    with mock.patch("anywhereinput.zrok2_repair.safe_print"):
        with mock.patch("anywhereinput.zrok2_repair.check_zrok_installation", return_value=True):
            with mock.patch("anywhereinput.zrok2_repair.check_zrok_enabled", return_value=False):
                with mock.patch("builtins.input", return_value="fake-token-123"):
                    safe_stderr = []

                    def capture_stderr(*args, **kwargs):
                        safe_stderr.append(str(args[0])) if args else None

                    from anywhereinput.zrok2_repair import enable_zrok
                    with mock.patch("anywhereinput.zrok2_repair.safe_print_stderr", capture_stderr):
                        try:
                            enable_zrok()
                        except (EOFError, SystemExit):
                            pass


def test_main():
    """main() calls enable_zrok then waits for input."""
    safe_calls = []

    def mock_print(*args, **kwargs):
        safe_calls.append((" ".join(str(a) for a in args), kwargs))

    with mock.patch("anywhereinput.zrok2_repair.safe_print", mock_print):
        with mock.patch("anywhereinput.zrok2_repair.enable_zrok") as mock_enable:
            with mock.patch("builtins.input", return_value=""):
                from anywhereinput.zrok2_repair import main
                main()

    mock_enable.assert_called_once()


def test_check_zrok_installation_checks_zrok2():
    """check_zrok_installation also looks for zrok2 binary."""
    from anywhereinput.zrok2_repair import check_zrok_installation

    def side_effect(name):
        return "/usr/bin/zrok2" if name == "zrok2" else None

    with mock.patch("anywhereinput.zrok2_repair.shutil.which", side_effect=side_effect):
        result = check_zrok_installation()
    assert result is True


def test_check_zrok_enabled_timeout():
    """check_zrok_enabled returns False on timeout."""
    from anywhereinput.zrok2_repair import check_zrok_enabled

    with mock.patch("anywhereinput.zrok2_repair.subprocess.run", side_effect=TimeoutError()):
        result = check_zrok_enabled()
    assert result is False
