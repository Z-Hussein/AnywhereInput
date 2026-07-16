"""Tests for config file validation and schema coverage (reference configs)."""
import sys
from pathlib import Path

src = Path(__file__).parent.parent / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))


def _example_file(name: str) -> Path:
    """Get path to example config file (reference config, not loaded at runtime)."""
    return Path(__file__).parent.parent / "config" / f"{name}.example"


def test_settings_yaml_example_exists():
    """settings.yaml.example must exist in config/ as reference."""
    assert _example_file("settings.yaml").exists()


def test_recovery_yaml_example_exists():
    """recovery.yaml.example must exist in config/."""
    assert _example_file("recovery.yaml").exists()


def _load_example_yaml(name: str):
    """Load an example YAML config file."""
    try:
        import yaml
    except ImportError:
        import pytest
        pytest.importorskip("yaml")

    config_path = _example_file(name)
    with open(config_path) as f:
        return yaml.safe_load(f)


def test_settings_yaml_example_has_required_sections():
    """settings.yaml.example has all expected top-level sections."""
    data = _load_example_yaml("settings.yaml")
    expected_sections = {"server", "screen_capture", "auth", "mouse", "tunnels"}
    assert expected_sections.issubset(set(data.keys()))


def test_settings_server_section():
    """settings.yaml.example server section has host, port, debug."""
    data = _load_example_yaml("settings.yaml")
    srv = data.get("server", {})
    assert "host" in srv
    assert "port" in srv
    assert "debug" in srv
    assert isinstance(srv["port"], int)


def test_settings_screen_capture_section():
    """settings.yaml.example screen_capture section has expected fields."""
    data = _load_example_yaml("settings.yaml")
    sc = data.get("screen_capture", {})
    for field in ("enabled", "fps", "quality", "scale"):
        assert field in sc, f"Missing field '{field}' in screen_capture config"


def test_settings_auth_section():
    """settings.yaml.example auth section has expected fields."""
    data = _load_example_yaml("settings.yaml")
    auth = data.get("auth", {})
    assert "token_length" in auth
    assert isinstance(auth["token_length"], int)


def test_settings_tunnel_cloudflare():
    """settings.yaml.example has cloudflare tunnel config."""
    data = _load_example_yaml("settings.yaml")
    tunnels = data.get("tunnels", {})
    cf = tunnels.get("cloudflare", {})
    assert "auto_download" in cf
    assert "binary_name" in cf


def test_settings_tunnel_pinggy():
    """settings.yaml.example has pinggy tunnel config."""
    data = _load_example_yaml("settings.yaml")
    tunnels = data.get("tunnels", {})
    pg = tunnels.get("pinggy", {})
    assert "ssh_host" in pg
    assert "ssh_port" in pg


def test_recovery_yaml_example_structure():
    """recovery.yaml.example has the expected health check and recovery fields."""
    data = _load_example_yaml("recovery.yaml")
    engine = data.get("capture_engine_recovery", {})
    assert "health_check_interval" in engine
    assert "max_failures" in engine
    assert "base_backoff_seconds" in engine
    assert "max_backoff_seconds" in engine


def test_recovery_yaml_example_fallback_section():
    """recovery.yaml.example has fallback config with queue settings."""
    data = _load_example_yaml("recovery.yaml")
    engine = data.get("capture_engine_recovery", {})
    fallback = engine.get("fallback", {})
    assert "queue_commands" in fallback
    assert "max_queue_size" in fallback
    assert "queue_timeout_seconds" in fallback


def test_settings_port_in_valid_range():
    """settings.yaml.example server port is within valid TCP range."""
    data = _load_example_yaml("settings.yaml")
    port = data["server"]["port"]
    assert 1024 <= port <= 65535


def test_settings_screen_fps_in_range():
    """settings.yaml.example screen capture FPS is within reasonable range."""
    data = _load_example_yaml("settings.yaml")
    fps = data["screen_capture"]["fps"]
    assert 1 <= fps <= 120


def test_recovery_health_check_interval_positive():
    """recovery.yaml.example health_check_interval must be positive."""
    data = _load_example_yaml("recovery.yaml")
    interval = data["capture_engine_recovery"]["health_check_interval"]
    assert interval > 0


def test_recovery_max_failures_positive():
    """recovery.yaml.example max_failures must be positive."""
    data = _load_example_yaml("recovery.yaml")
    assert data["capture_engine_recovery"]["max_failures"] > 0


def test_recovery_max_backoff_greater_than_base():
    """recovery.yaml.example max_backoff_seconds >= base_backoff_seconds."""
    data = _load_example_yaml("recovery.yaml")
    engine = data["capture_engine_recovery"]
    assert engine["max_backoff_seconds"] >= engine["base_backoff_seconds"]


def test_config_local_settings_gitignored():
    """config/local_settings.yaml should be in .gitignore (not committed)."""
    project_root = Path(__file__).parent.parent
    gitignore_path = project_root / ".gitignore"

    if gitignore_path.exists():
        content = gitignore_path.read_text()
        assert "local_settings.yaml" in content or "**/local_settings.yaml" in content


def test_recovery_yaml_example_windows_section():
    """recovery.yaml.example has windows-specific config."""
    data = _load_example_yaml("recovery.yaml")
    engine = data["capture_engine_recovery"]
    windows = engine.get("windows", {})
    assert "detect_uac" in windows
    assert "detect_session_lock" in windows
    assert "wake_on_recovery" in windows


def test_settings_logging_section():
    """settings.yaml.example has a logging section with level and format."""
    data = _load_example_yaml("settings.yaml")
    log_cfg = data.get("logging", {})
    assert "level" in log_cfg
    assert "format" in log_cfg


def test_settings_mouse_section():
    """settings.yaml.example has mouse section with sensitivity and acceleration."""
    data = _load_example_yaml("settings.yaml")
    mouse = data.get("mouse", {})
    assert "sensitivity" in mouse
    assert "acceleration" in mouse
    assert isinstance(mouse["sensitivity"], (int, float))


def test_settings_tunnels_zrok2():
    """settings.yaml.example has zrok2 tunnel config with auto_enable."""
    data = _load_example_yaml("settings.yaml")
    tunnels = data.get("tunnels", {})
    zrok2 = tunnels.get("zrok2", {})
    assert "auto_enable" in zrok2
