"""Tests for admin capture mode presets."""

import json
import tempfile
from pathlib import Path

from anywhereinput.admin._capture_modes import (
    BUILT_IN_MODES,
    CaptureMode,
    CaptureModeManager,
)


class TestCaptureMode:
    def test_to_dict(self):
        m = CaptureMode("Test", fps=30, quality=50, scale=0.5)
        d = m.to_dict()
        assert d == {"name": "Test", "fps": 30, "quality": 50, "scale": 0.5}
        assert "built_in" not in d

    def test_built_in_flag(self):
        m = CaptureMode("X", fps=10, quality=10, scale=0.1, built_in=True)
        assert m.built_in is True


class TestBuiltInModes:
    def test_count(self):
        assert len(BUILT_IN_MODES) == 4

    def test_names(self):
        names = [m.name for m in BUILT_IN_MODES]
        assert "Balanced" in names
        assert "Quality" in names
        assert "Performance" in names
        assert "Low Bandwidth" in names

    def test_all_built_in_flag(self):
        for m in BUILT_IN_MODES:
            assert m.built_in is True

    def test_balanced_values(self):
        b = next(m for m in BUILT_IN_MODES if m.name == "Balanced")
        assert b.fps == 60
        assert b.quality == 70
        assert b.scale == 0.8


class TestCaptureModeManager:
    def _make_manager(self, tmp_path):
        path = tmp_path / "modes.json"
        return CaptureModeManager(path=path)

    def test_init_loads_builtins(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        assert len(mgr.modes) == 4

    def test_get_builtin(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        m = mgr.get("Balanced")
        assert m is not None
        assert m.fps == 60

    def test_get_nonexistent(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        assert mgr.get("Nope") is None

    def test_save_custom(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        result = mgr.save_custom("MyMode", 30, 50, 0.5)
        assert result is True
        assert len(mgr.modes) == 5
        m = mgr.get("MyMode")
        assert m is not None
        assert m.fps == 30
        assert m.quality == 50
        assert m.scale == 0.5
        assert m.built_in is False

    def test_save_overwrites_custom(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        mgr.save_custom("MyMode", 30, 50, 0.5)
        mgr.save_custom("MyMode", 60, 80, 0.9)
        m = mgr.get("MyMode")
        assert m.fps == 60
        assert len(mgr.modes) == 5  # no duplicate

    def test_cannot_overwrite_builtin(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        result = mgr.save_custom("Balanced", 1, 1, 0.1)
        assert result is False

    def test_delete_custom(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        mgr.save_custom("MyMode", 30, 50, 0.5)
        result = mgr.delete("MyMode")
        assert result is True
        assert mgr.get("MyMode") is None
        assert len(mgr.modes) == 4

    def test_cannot_delete_builtin(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        result = mgr.delete("Balanced")
        assert result is False
        assert len(mgr.modes) == 4

    def test_is_custom(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        mgr.save_custom("MyMode", 30, 50, 0.5)
        assert mgr.is_custom("MyMode") is True
        assert mgr.is_custom("Balanced") is False
        assert mgr.is_custom("Nonexistent") is False

    def test_persistence(self, tmp_path):
        path = tmp_path / "modes.json"
        mgr1 = CaptureModeManager(path=path)
        mgr1.save_custom("Persist", 25, 40, 0.6)
        # Reload from disk
        mgr2 = CaptureModeManager(path=path)
        m = mgr2.get("Persist")
        assert m is not None
        assert m.fps == 25
        assert len(mgr2.modes) == 5

    def test_loads_corrupted_json(self, tmp_path):
        path = tmp_path / "modes.json"
        path.write_text("NOT JSON {{{")
        mgr = CaptureModeManager(path=path)
        assert len(mgr.modes) == 4  # builtins still loaded

    def test_loads_missing_file(self, tmp_path):
        path = tmp_path / "nonexistent.json"
        mgr = CaptureModeManager(path=path)
        assert len(mgr.modes) == 4

    def test_name_collision_with_builtin_not_duplicated(self, tmp_path):
        path = tmp_path / "modes.json"
        # Manually write a custom mode with same name as built-in
        path.write_text(json.dumps({"custom_modes": [{"name": "Balanced", "fps": 1, "quality": 1, "scale": 0.1}]}))
        mgr = CaptureModeManager(path=path)
        # Should not duplicate - built-in wins
        balanced = mgr.get("Balanced")
        assert balanced.fps == 60  # built-in value, not the corrupted one
        assert len(mgr.modes) == 4
