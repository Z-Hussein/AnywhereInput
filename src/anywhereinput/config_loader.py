"""YAML configuration loader for AnywhereInput.

Loads config/settings.yaml (project defaults) and config/local_settings.yaml
(user overrides, gitignored). Merges them so local_settings takes precedence.
CLI arguments override both.

Usage:
    from anywhereinput.config_loader import load_settings
    settings = load_settings()
    fps = settings.get("screen_capture", {}).get("fps", DEFAULT_FPS)
"""

from pathlib import Path
from typing import Any, Dict, Optional

try:
    import yaml  # type: ignore[import-untyped]
except ImportError:
    yaml = None  # type: ignore[assignment]

from .logging_config import get_logger

log = get_logger(__name__)

# Paths relative to this file's package
_PACKAGE_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _PACKAGE_DIR.parent.parent
CONFIG_DIR = _PROJECT_ROOT / "config"

SETTINGS_YAML = CONFIG_DIR / "settings.yaml"
LOCAL_SETTINGS_YAML = CONFIG_DIR / "local_settings.yaml"


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Merge *override* into *base*, returning a new dict.

    Nested dicts are merged recursively; all other values are overwritten.
    """
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _load_yaml_file(path: Path) -> Optional[Dict[str, Any]]:
    """Load a single YAML file. Returns None if missing or unreadable."""
    if not path.exists():
        return None
    if yaml is None:
        log.warning("PyYAML not installed — skipping config file %s", path.name)
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data is None:
            return {}
        if not isinstance(data, dict):
            log.warning(
                "Config file %s did not parse as a mapping — skipping", path.name
            )
            return None
        return data
    except Exception as exc:
        log.warning("Failed to load config %s: %s", path.name, exc)
        return None


def load_settings(
    settings_path: Optional[Path] = None,
    local_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Load and merge configuration files.

    Priority (highest wins):
        1. CLI arguments (handled by caller via argparse defaults)
        2. config/local_settings.yaml  (user overrides, gitignored)
        3. config/settings.yaml        (project defaults)

    Args:
        settings_path: Override path for the project settings file.
        local_path: Override path for the local settings file.

    Returns:
        Merged configuration dict.
    """
    base_path = settings_path or SETTINGS_YAML
    local_path = local_path or LOCAL_SETTINGS_YAML

    base = _load_yaml_file(base_path) or {}
    local = _load_yaml_file(local_path)

    if local is not None:
        log.info("Loaded user overrides from %s", local_path.name)
        merged = _deep_merge(base, local)
    else:
        merged = base

    return merged


def save_settings(settings: Dict[str, Any], path: Optional[Path] = None) -> bool:
    """Save configuration to a YAML file.

    Args:
        settings: Configuration dict to save.
        path: Target file path. Defaults to config/local_settings.yaml.

    Returns:
        True on success, False on failure.
    """
    if yaml is None:
        log.error("PyYAML not installed — cannot save config")
        return False

    target = path or LOCAL_SETTINGS_YAML
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            yaml.dump(settings, f, default_flow_style=False, sort_keys=False)
        log.info("Saved settings to %s", target)
        return True
    except Exception as exc:
        log.error("Failed to save config to %s: %s", target, exc)
        return False


def get_setting(settings: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Traverse nested dict keys to retrieve a value.

    Example:
        get_setting(cfg, "screen_capture", "fps", default=120)
    """
    current: Any = settings
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return default
        if current is None:
            return default
    return current
