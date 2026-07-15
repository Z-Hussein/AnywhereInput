"""Tests for admin_app TokenStore (non-Qt, pure Python)."""

import sys
import json
from pathlib import Path
from unittest import mock

src = Path(__file__).parent.parent / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))


def test_token_store_create_and_list():
    """TokenStore.create() generates a token; list_all() returns it."""
    from anywhereinput.admin import QT_AVAILABLE

    if not QT_AVAILABLE:
        assert TS is None
    else:
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmppath = f.name

        store = TS(path=tmppath)
        token = store.create(name="test-token")
        assert len(token) > 0

        listed = store.list_all()
        assert len(listed) == 1
        assert listed[0]["name"] == "test-token"


def test_token_store_create_with_permissions():
    """create() with explicit permissions stores them."""

    if not QT_AVAILABLE:
        return

    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmppath = f.name

    store = TS(path=tmppath)
    token = store.create(name="limited", permissions=["move"])

    listed = store.list_all()
    assert len(listed) == 1
    assert listed[0]["permissions"] == ["move"]


def test_token_store_create_with_allowed_ips():
    """create() with allowed_ips stores them."""
    from anywhereinput.admin import QT_AVAILABLE

    if not QT_AVAILABLE:
        return

    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmppath = f.name

    store = TS(path=tmppath)
    token = store.create(name="ip-limited", allowed_ips=["192.168.1.0/24"])

    listed = store.list_all()
    assert len(listed) == 1
    assert "192.168.1.0/24" in listed[0]["allowed_ips"]


def test_token_store_revoke():
    """revoke() removes a token."""
    from anywhereinput.admin import QT_AVAILABLE

    if not QT_AVAILABLE:
        return

    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmppath = f.name

    store = TS(path=tmppath)
    token = store.create(name="revoke-me")

    assert store.revoke(token) is True
    listed = store.list_all()
    assert len(listed) == 0


def test_token_store_revoke_nonexistent():
    """revoke() on nonexistent token returns False."""
    from anywhereinput.admin import QT_AVAILABLE

    if not QT_AVAILABLE:
        return

    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmppath = f.name

    store = TS(path=tmppath)
    assert store.revoke("totally-nonexistent-token") is False


def test_token_store_update():
    """update() changes token fields."""
    from anywhereinput.admin import QT_AVAILABLE

    if not QT_AVAILABLE:
        return

    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmppath = f.name

    store = TS(path=tmppath)
    token = store.create(name="original")

    assert store.update(token, name="updated") is True
    listed = store.list_all()
    assert len(listed) == 1
    assert listed[0]["name"] == "updated"


def test_token_store_update_nonexistent():
    """update() on nonexistent token returns False."""
    from anywhereinput.admin import QT_AVAILABLE

    if not QT_AVAILABLE:
        return

    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmppath = f.name

    store = TS(path=tmppath)
    assert store.update("nonexistent") is False


def test_token_store_update_partial():
    """update() only changes specified fields."""
    from anywhereinput.admin import QT_AVAILABLE

    if not QT_AVAILABLE:
        return

    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmppath = f.name

    store = TS(path=tmppath)
    token = store.create(name="orig", permissions=["move", "click"])

    store.update(token, name="new")
    listed = store.list_all()
    assert len(listed) == 1
    assert listed[0]["name"] == "new"
    assert listed[0]["permissions"] == ["move", "click"]


def test_token_store_persistence_load():
    """save()/load() round-trips correctly."""
    from anywhereinput.admin import QT_AVAILABLE

    if not QT_AVAILABLE:
        return

    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmppath = f.name

    store1 = TS(path=tmppath)
    token = store1.create(name="persistent")

    store2 = TS(path=tmppath)
    listed = store2.list_all()
    assert len(listed) == 1
    assert listed[0]["name"] == "persistent"


def test_token_store_load_corrupted_json():
    """load() handles corrupted JSON gracefully."""
    from anywhereinput.admin import QT_AVAILABLE

    if not QT_AVAILABLE:
        return

    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmppath = f.name
        f.write(b"{{{{invalid json{{")

    store = TS(path=tmppath)
    assert store._data == {}


def test_token_store_list_all_returns_masked_token():
    """list_all() masks the full token in display."""
    from anywhereinput.admin import QT_AVAILABLE

    if not QT_AVAILABLE:
        return

    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmppath = f.name

    store = TS(path=tmppath)
    token = store.create(name="masked")

    listed = store.list_all()
    assert len(listed) == 1
    display_token = listed[0]["token"]
    assert display_token.endswith("...")
    assert display_token != token


def test_token_store_get_all():
    """get_all() returns a copy of internal data."""
    from anywhereinput.admin import QT_AVAILABLE

    if not QT_AVAILABLE:
        return

    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmppath = f.name

    store = TS(path=tmppath)
    token = store.create(name="copy")

    data = store.get_all()
    assert token in data


def test_token_store_get_all_is_copy():
    """get_all() returns a copy, not the internal dict."""
    from anywhereinput.admin import QT_AVAILABLE

    if not QT_AVAILABLE:
        return

    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmppath = f.name

    store = TS(path=tmppath)
    token = store.create(name="orig")

    copy = store.get_all()
    del copy[token]

    listed = store.list_all()
    assert len(listed) == 1


def test_token_store_default_path():
    """TokenStore without path argument defaults to admin_tokens.json in project root."""
    from anywhereinput.admin import QT_AVAILABLE, _PROJECT_ROOT

    if not QT_AVAILABLE:
        return

    default = _PROJECT_ROOT / "admin_tokens.json"
    assert str(default).endswith("admin_tokens.json")


def test_token_store_empty_initialization():
    """New TokenStore starts with empty data."""
    from anywhereinput.admin import QT_AVAILABLE

    if not QT_AVAILABLE:
        return

    import tempfile
    import os

    tmppath = tempfile.mktemp(suffix=".json")
    if os.path.exists(tmppath):
        os.unlink(tmppath)

    store = TS(path=tmppath)
    assert store._data == {}


def test_token_store_default_permissions():
    """create() without permissions uses default list."""
    from anywhereinput.admin import QT_AVAILABLE

    if not QT_AVAILABLE:
        return

    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmppath = f.name

    store = TS(path=tmppath)
    token = store.create(name="default-perms")

    listed = store.list_all()
    expected_perms = ["move", "click", "scroll", "keyboard", "screen_toggle"]
    assert listed[0]["permissions"] == expected_perms


def test_token_store_multiple_tokens():
    """TokenStore handles multiple tokens correctly."""
    from anywhereinput.admin import QT_AVAILABLE

    if not QT_AVAILABLE:
        return

    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmppath = f.name

    store = TS(path=tmppath)
    t1 = store.create(name="first")
    t2 = store.create(name="second")
    t3 = store.create(name="third")

    listed = store.list_all()
    assert len(listed) == 3
    names = {t["name"] for t in listed}
    assert names == {"first", "second", "third"}


def test_token_store_revoke_then_create():
    """After revoking all tokens, can create new ones."""
    from anywhereinput.admin import QT_AVAILABLE

    if not QT_AVAILABLE:
        return

    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmppath = f.name

    store = TS(path=tmppath)
    t1 = store.create(name="one")
    t2 = store.create(name="two")
    store.revoke(t1)
    store.revoke(t2)

    listed = store.list_all()
    assert len(listed) == 0

    t3 = store.create(name="new-start")
    assert len(store.list_all()) == 1


# Stub tests when Qt is not available
def test_admin_app_qt_not_available_stubs():
    """When Qt is not available, all classes should be None."""
    from anywhereinput.admin import (
        QT_AVAILABLE,
        ServerProcessWorker,
        TokenStore,
        EngineStatusWidget,
        TokenManagerDialog,
        ClientListDialog,
        SettingsPanel,
        MainWindow,
        run_admin_app,
    )

    if not QT_AVAILABLE:
        assert ServerProcessWorker is None
        assert TokenStore is not None  # TokenStore is always real (pure Python)
        assert EngineStatusWidget is None
        assert TokenManagerDialog is None
        assert ClientListDialog is None
        assert SettingsPanel is None
        assert MainWindow is None


def test_run_admin_app_quits_without_qt():
    """run_admin_app exits with code 1 when Qt is not available."""
    from anywhereinput.admin import QT_AVAILABLE, run_admin_app
    import pytest

    if QT_AVAILABLE:
        pytest.skip("Qt is available in this environment")

    with mock.patch("anywhereinput.admin.safe_print_stderr"):
        with mock.patch("sys.exit", side_effect=SystemExit(1)) as mock_exit:
            try:
                run_admin_app()
            except SystemExit as e:
                assert e.code == 1


def test_server_process_worker_command():
    """ServerProcessWorker.run() builds correct subprocess command."""
    import pytest
    from anywhereinput.admin import QT_AVAILABLE, ServerProcessWorker

    if not QT_AVAILABLE:
        return

    import tempfile
    import subprocess as sp

    logs = []

    class FakeProc:
        def __init__(self):
            self.stdout = iter(
                [
                    "[INFO] Local: http://127.0.0.1:8008\n",
                    "[INFO] Ready.\n",
                ]
            )
            self._exited = False

        def poll(self):
            if not self._exited:
                return None
            return 0

        def wait(self):
            self._exited = True

    with mock.patch(
        "anywhereinput.admin._server_worker.subprocess.Popen",
        return_value=FakeProc(),
    ):
        worker = ServerProcessWorker(port=9008, tunnel="local", fps=24)

        log_sig_calls = []

        def capture_log(text):
            log_sig_calls.append(text)

        worker.log_signal = type("Signal", (), {"emit": capture_log})()
        worker.status_signal = type("Signal", (), {"emit": lambda s, x: None})()

        cmd = [
            sys.executable,
            "-m",
            "anywhereinput",
            "--tunnel",
            "local",
            "--host",
            "127.0.0.1",
            "--port",
            "9008",
            "--fps",
            "24",
            "--quality",
            "85",
            "--scale",
            "1.0",
        ]
        assert worker._proc is None


# Re-import TokenStore for tests that need it
from anywhereinput.admin import QT_AVAILABLE, TokenStore as _TS, ServerProcessWorker

if QT_AVAILABLE:
    TS = _TS
else:
    TS = None
