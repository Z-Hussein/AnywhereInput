"""Tests for config_loader module."""
import sys
import tempfile
from pathlib import Path

import pytest

src = Path(__file__).parent.parent / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

yaml = pytest.importorskip("yaml")

from anywhereinput.config_loader import (
    _deep_merge,
    _load_yaml_file,
    load_settings,
    save_settings,
    get_setting,
)


# ---------------------------------------------------------------------------
# _deep_merge
# ---------------------------------------------------------------------------


def test_deep_merge_empty():
    assert _deep_merge({}, {}) == {}


def test_deep_merge_base_only():
    assert _deep_merge({"a": 1, "b": 2}, {}) == {"a": 1, "b": 2}


def test_deep_merge_override_only():
    assert _deep_merge({}, {"a": 1}) == {"a": 1}


def test_deep_merge_override_values():
    result = _deep_merge({"a": 1}, {"a": 2})
    assert result == {"a": 2}


def test_deep_merge_nested():
    base = {"server": {"host": "127.0.0.1", "port": 8008}}
    override = {"server": {"port": 9000}}
    result = _deep_merge(base, override)
    assert result == {"server": {"host": "127.0.0.1", "port": 9000}}


def test_deep_merge_new_keys():
    base = {"a": 1}
    override = {"b": 2}
    result = _deep_merge(base, override)
    assert result == {"a": 1, "b": 2}


def test_deep_merge_does_not_mutate_input():
    base = {"a": {"b": 1}}
    override = {"a": {"c": 2}}
    result = _deep_merge(base, override)
    assert base == {"a": {"b": 1}}
    assert result == {"a": {"b": 1, "c": 2}}


# ---------------------------------------------------------------------------
# _load_yaml_file
# ---------------------------------------------------------------------------


def test_load_yaml_file_missing():
    result = _load_yaml_file(Path("/nonexistent/file.yaml"))
    assert result is None


def test_load_yaml_file_valid(tmp_path):
    config_file = tmp_path / "test.yaml"
    config_file.write_text("server:\n  port: 9000\n")
    result = _load_yaml_file(config_file)
    assert result == {"server": {"port": 9000}}


def test_load_yaml_file_empty(tmp_path):
    config_file = tmp_path / "empty.yaml"
    config_file.write_text("")
    result = _load_yaml_file(config_file)
    assert result == {}


def test_load_yaml_file_not_mapping(tmp_path):
    config_file = tmp_path / "list.yaml"
    config_file.write_text("- item1\n- item2\n")
    result = _load_yaml_file(config_file)
    assert result is None


# ---------------------------------------------------------------------------
# load_settings
# ---------------------------------------------------------------------------


def test_load_settings_no_files(tmp_path):
    result = load_settings(
        settings_path=tmp_path / "nope.yaml",
        local_path=tmp_path / "nope.yaml",
    )
    assert result == {}


def test_load_settings_base_only(tmp_path):
    base = tmp_path / "settings.yaml"
    base.write_text("server:\n  port: 9000\n")
    result = load_settings(settings_path=base, local_path=tmp_path / "nope.yaml")
    assert result == {"server": {"port": 9000}}


def test_load_settings_local_overrides_base(tmp_path):
    base = tmp_path / "settings.yaml"
    base.write_text("server:\n  port: 8008\n  host: '127.0.0.1'\n")
    local = tmp_path / "local.yaml"
    local.write_text("server:\n  port: 9000\n")
    result = load_settings(settings_path=base, local_path=local)
    assert result["server"]["port"] == 9000
    assert result["server"]["host"] == "127.0.0.1"


def test_load_settings_local_adds_keys(tmp_path):
    base = tmp_path / "settings.yaml"
    base.write_text("server:\n  port: 8008\n")
    local = tmp_path / "local.yaml"
    local.write_text("server:\n  host: '0.0.0.0'\n")
    result = load_settings(settings_path=base, local_path=local)
    assert result["server"]["port"] == 8008
    assert result["server"]["host"] == "0.0.0.0"


# ---------------------------------------------------------------------------
# save_settings / load_settings round-trip
# ---------------------------------------------------------------------------


def test_save_and_load_round_trip(tmp_path):
    settings = {"server": {"port": 7777}, "screen_capture": {"fps": 60}}
    target = tmp_path / "local_settings.yaml"
    assert save_settings(settings, path=target) is True
    assert target.exists()

    loaded = load_settings(settings_path=tmp_path / "nope.yaml", local_path=target)
    assert loaded["server"]["port"] == 7777
    assert loaded["screen_capture"]["fps"] == 60


# ---------------------------------------------------------------------------
# get_setting
# ---------------------------------------------------------------------------


def test_get_setting_simple():
    cfg = {"server": {"port": 8008}}
    assert get_setting(cfg, "server", "port") == 8008


def test_get_setting_nested_missing():
    cfg = {"server": {}}
    assert get_setting(cfg, "server", "port", default=8008) == 8008


def test_get_setting_top_level_missing():
    cfg = {}
    assert get_setting(cfg, "server", "port", default=8008) == 8008


def test_get_setting_none_value():
    cfg = {"server": {"port": None}}
    assert get_setting(cfg, "server", "port", default=8008) == 8008


def test_get_setting_non_dict_parent():
    cfg = {"server": "not-a-dict"}
    assert get_setting(cfg, "server", "port", default=8008) == 8008


# ---------------------------------------------------------------------------
# Integration: settings.yaml is loadable
# ---------------------------------------------------------------------------


def test_settings_yaml_is_loadable():
    """Verify that config/settings.yaml loads and has expected structure."""
    settings_path = Path(__file__).parent.parent / "config" / "settings.yaml"
    if not settings_path.exists():
        pytest.skip("config/settings.yaml not found")
    data = _load_yaml_file(settings_path)
    assert data is not None
    assert "server" in data
    assert "screen_capture" in data
    assert isinstance(data["server"]["port"], int)


def test_settings_yaml_defaults_match_constants():
    """Verify settings.yaml defaults match _constants.py values."""
    from anywhereinput._constants import DEFAULT_FPS, DEFAULT_QUALITY, DEFAULT_SCALE

    settings_path = Path(__file__).parent.parent / "config" / "settings.yaml"
    if not settings_path.exists():
        pytest.skip("config/settings.yaml not found")
    data = _load_yaml_file(settings_path)
    sc = data.get("screen_capture", {})
    assert sc.get("fps") == DEFAULT_FPS
    assert sc.get("quality") == DEFAULT_QUALITY
    assert sc.get("scale") == DEFAULT_SCALE
