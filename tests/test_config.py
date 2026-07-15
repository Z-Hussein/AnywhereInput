"""Tests for config file validation and schema coverage."""
import json
import sys
from pathlib import Path
from unittest import mock

src = Path(__file__).parent.parent / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))


def _config_dir():
    return Path(__file__).parent.parent / "config"


def test_settings_yaml_exists():
    """settings.yaml must exist in config/."""
    assert (_config_dir() / "settings.yaml").exists()


def test_recovery_yaml_exists():
    """recovery.yaml must exist in config/."""
    assert (_config_dir() / "recovery.yaml").exists()


def test_settings_yaml_has_required_sections():
    """settings.yaml has all expected top-level sections."""
    try:
        import yaml
    except ImportError:
        import subprocess
        result = subprocess.run(
            [sys.executable, "-c", "import yaml"],
            capture_output=True
        )
        if result.returncode != 0:
            pytest.skip("PyYAML not installed")
        import yaml

    config_path = _config_dir() / "settings.yaml"
    with open(config_path) as f:
        data = yaml.safe_load(f)

    expected_sections = {"server", "screen_capture", "auth", "mouse", "tunnels"}
    assert expected_sections.issubset(set(data.keys()))


def test_settings_server_section():
    """settings.yaml server section has host, port, debug."""
    try:
        import yaml
    except ImportError:
        pytest.importorskip("yaml")

    config_path = _config_dir() / "settings.yaml"
    with open(config_path) as f:
        data = yaml.safe_load(f)

    srv = data.get("server", {})
    assert "host" in srv
    assert "port" in srv
    assert "debug" in srv
    assert isinstance(srv["port"], int)


def test_settings_screen_capture_section():
    """settings.yaml screen_capture section has expected fields."""
    try:
        import yaml
    except ImportError:
        pytest.importorskip("yaml")

    config_path = _config_dir() / "settings.yaml"
    with open(config_path) as f:
        data = yaml.safe_load(f)

    sc = data.get("screen_capture", {})
    for field in ("enabled", "fps", "quality", "scale"):
        assert field in sc, f"Missing field '{field}' in screen_capture config"


def test_settings_auth_section():
    """settings.yaml auth section has expected fields."""
    try:
        import yaml
    except ImportError:
        pytest.importorskip("yaml")

    config_path = _config_dir() / "settings.yaml"
    with open(config_path) as f:
        data = yaml.safe_load(f)

    auth = data.get("auth", {})
    assert "token_length" in auth
    assert isinstance(auth["token_length"], int)


def test_settings_tunnel_cloudflare():
    """settings.yaml has cloudflare tunnel config."""
    try:
        import yaml
    except ImportError:
        pytest.importorskip("yaml")

    config_path = _config_dir() / "settings.yaml"
    with open(config_path) as f:
        data = yaml.safe_load(f)

    tunnels = data.get("tunnels", {})
    cf = tunnels.get("cloudflare", {})
    assert "auto_download" in cf
    assert "binary_name" in cf


def test_settings_tunnel_pinggy():
    """settings.yaml has pinggy tunnel config."""
    try:
        import yaml
    except ImportError:
        pytest.importorskip("yaml")

    config_path = _config_dir() / "settings.yaml"
    with open(config_path) as f:
        data = yaml.safe_load(f)

    tunnels = data.get("tunnels", {})
    pg = tunnels.get("pinggy", {})
    assert "ssh_host" in pg
    assert "ssh_port" in pg


def test_recovery_yaml_structure():
    """recovery.yaml has the expected health check and recovery fields."""
    try:
        import yaml
    except ImportError:
        pytest.importorskip("yaml")

    config_path = _config_dir() / "recovery.yaml"
    with open(config_path) as f:
        data = yaml.safe_load(f)

    engine = data.get("capture_engine_recovery", {})
    assert "health_check_interval" in engine
    assert "max_failures" in engine
    assert "base_backoff_seconds" in engine
    assert "max_backoff_seconds" in engine


def test_recovery_yaml_fallback_section():
    """recovery.yaml has fallback config with queue settings."""
    try:
        import yaml
    except ImportError:
        pytest.importorskip("yaml")

    config_path = _config_dir() / "recovery.yaml"
    with open(config_path) as f:
        data = yaml.safe_load(f)

    engine = data.get("capture_engine_recovery", {})
    fallback = engine.get("fallback", {})
    assert "queue_commands" in fallback
    assert "max_queue_size" in fallback
    assert "queue_timeout_seconds" in fallback


def test_settings_port_in_valid_range():
    """settings.yaml server port is within valid TCP range."""
    try:
        import yaml
    except ImportError:
        pytest.importorskip("yaml")

    config_path = _config_dir() / "settings.yaml"
    with open(config_path) as f:
        data = yaml.safe_load(f)

    port = data["server"]["port"]
    assert 1024 <= port <= 65535


def test_settings_screen_fps_in_range():
    """settings.yaml screen capture FPS is within reasonable range."""
    try:
        import yaml
    except ImportError:
        pytest.importorskip("yaml")

    config_path = _config_dir() / "settings.yaml"
    with open(config_path) as f:
        data = yaml.safe_load(f)

    fps = data["screen_capture"]["fps"]
    assert 1 <= fps <= 120


def test_recovery_health_check_interval_positive():
    """recovery.yaml health_check_interval must be positive."""
    try:
        import yaml
    except ImportError:
        pytest.importorskip("yaml")

    config_path = _config_dir() / "recovery.yaml"
    with open(config_path) as f:
        data = yaml.safe_load(f)

    interval = data["capture_engine_recovery"]["health_check_interval"]
    assert interval > 0


def test_recovery_max_failures_positive():
    """recovery.yaml max_failures must be positive."""
    try:
        import yaml
    except ImportError:
        pytest.importorskip("yaml")

    config_path = _config_dir() / "recovery.yaml"
    with open(config_path) as f:
        data = yaml.safe_load(f)

    assert data["capture_engine_recovery"]["max_failures"] > 0


def test_recovery_max_backoff_greater_than_base():
    """recovery.yaml max_backoff_seconds >= base_backoff_seconds."""
    try:
        import yaml
    except ImportError:
        pytest.importorskip("yaml")

    config_path = _config_dir() / "recovery.yaml"
    with open(config_path) as f:
        data = yaml.safe_load(f)

    engine = data["capture_engine_recovery"]
    assert engine["max_backoff_seconds"] >= engine["base_backoff_seconds"]


def test_config_local_settings_gitignored():
    """config/local_settings.yaml should be in .gitignore (not committed)."""
    project_root = Path(__file__).parent.parent
    gitignore_path = project_root / ".gitignore"

    if gitignore_path.exists():
        content = gitignore_path.read_text()
        assert "local_settings.yaml" in content or "**/local_settings.yaml" in content


def test_recovery_yaml_windows_section():
    """recovery.yaml has windows-specific config."""
    try:
        import yaml
    except ImportError:
        pytest.importorskip("yaml")

    config_path = _config_dir() / "recovery.yaml"
    with open(config_path) as f:
        data = yaml.safe_load(f)

    engine = data["capture_engine_recovery"]
    windows = engine.get("windows", {})
    assert "detect_uac" in windows
    assert "detect_session_lock" in windows
    assert "wake_on_recovery" in windows


def test_settings_logging_section():
    """settings.yaml has a logging section with level and format."""
    try:
        import yaml
    except ImportError:
        pytest.importorskip("yaml")

    config_path = _config_dir() / "settings.yaml"
    with open(config_path) as f:
        data = yaml.safe_load(f)

    log_cfg = data.get("logging", {})
    assert "level" in log_cfg
    assert "format" in log_cfg


def test_settings_mouse_section():
    """settings.yaml has mouse section with sensitivity and acceleration."""
    try:
        import yaml
    except ImportError:
        pytest.importorskip("yaml")

    config_path = _config_dir() / "settings.yaml"
    with open(config_path) as f:
        data = yaml.safe_load(f)

    mouse = data.get("mouse", {})
    assert "sensitivity" in mouse
    assert "acceleration" in mouse
    assert isinstance(mouse["sensitivity"], (int, float))


def test_settings_tunnels_zrok2():
    """settings.yaml has zrok2 tunnel config with auto_enable."""
    try:
        import yaml
    except ImportError:
        pytest.importorskip("yaml")

    config_path = _config_dir() / "settings.yaml"
    with open(config_path) as f:
        data = yaml.safe_load(f)

    tunnels = data.get("tunnels", {})
    zrok2 = tunnels.get("zrok2", {})
    assert "auto_enable" in zrok2
