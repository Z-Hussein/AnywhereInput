"""SettingsPanel - server config form with category-based layout."""

from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)
from PyQt6.QtGui import QFont

from anywhereinput._constants import (
    DEFAULT_PORT,
    DEFAULT_FPS,
    DEFAULT_QUALITY,
    DEFAULT_SCALE,
)
from anywhereinput.config_loader import load_settings, save_settings, get_setting
from ._capture_modes import CaptureModeManager


def _category_header(title: str) -> QLabel:
    """Create a styled category header label."""
    lbl = QLabel(title)
    lbl.setFont(QFont("Sans", 10, QFont.Weight.Bold))
    lbl.setStyleSheet(
        "color: #64748b;" "padding: 4px 0 2px 0;" "border-bottom: 1px solid #334155;"
    )
    return lbl


def _separator() -> QFrame:
    """Create a thin horizontal separator."""
    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.HLine)
    sep.setFrameShadow(QFrame.Shadow.Sunken)
    sep.setStyleSheet("color: #1e293b;")
    sep.setFixedHeight(1)
    return sep


class SettingsPanel(QFrame):
    """Server configuration panel with category-based layout."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._mode_mgr = CaptureModeManager()
        self._suppress_mode_change = False
        self._suppress_save = False
        self._cfg = load_settings()
        self.init_ui()
        self._populate_modes()
        self._connect_signals()
        self._load_from_yaml()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)

        # ── General ────────────────────────────────────────────────────────
        layout.addWidget(_category_header("General"))

        general_form = QFormLayout()
        general_form.setContentsMargins(8, 4, 8, 4)
        general_form.setSpacing(4)
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1024, 65535)
        self.port_spin.setValue(DEFAULT_PORT)
        general_form.addRow("Port:", self.port_spin)
        layout.addLayout(general_form)

        layout.addWidget(_separator())

        # ── Capture ────────────────────────────────────────────────────────
        layout.addWidget(_category_header("Capture"))

        capture_form = QFormLayout()
        capture_form.setContentsMargins(8, 4, 8, 4)
        capture_form.setSpacing(4)

        # Mode selector row
        mode_row = QHBoxLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.setMinimumWidth(160)
        mode_row.addWidget(self.mode_combo, 1)

        self.save_mode_btn = QPushButton("Save")
        self.save_mode_btn.setFixedWidth(55)
        self.save_mode_btn.setToolTip(
            "Save current settings as a new mode (or overwrite)"
        )
        mode_row.addWidget(self.save_mode_btn)

        self.delete_mode_btn = QPushButton("Del")
        self.delete_mode_btn.setFixedSize(35, 24)
        self.delete_mode_btn.setToolTip("Delete selected custom mode")
        mode_row.addWidget(self.delete_mode_btn)

        capture_form.addRow("Mode:", mode_row)

        # FPS
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 120)
        self.fps_spin.setValue(DEFAULT_FPS)
        capture_form.addRow("FPS:", self.fps_spin)

        # Quality
        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(1, 95)
        self.quality_spin.setValue(DEFAULT_QUALITY)
        capture_form.addRow("Quality (JPEG):", self.quality_spin)

        # Scale
        self.scale_spin = QDoubleSpinBox()
        self.scale_spin.setRange(0.1, 1.0)
        self.scale_spin.setSingleStep(0.1)
        self.scale_spin.setValue(DEFAULT_SCALE)
        capture_form.addRow("Scale:", self.scale_spin)

        layout.addLayout(capture_form)

        layout.addWidget(_separator())

        # ── Network ────────────────────────────────────────────────────────
        layout.addWidget(_category_header("Network"))

        network_form = QFormLayout()
        network_form.setContentsMargins(8, 4, 8, 4)
        network_form.setSpacing(4)
        self.tunnel_combo = QComboBox()
        tunnel_opts = [
            ("Local (no tunnel)", "local"),
            ("Cloudflare", "cloudflare"),
            ("Tailscale", "tailscale"),
            ("Pinggy.io", "pinggy"),
            ("Zrok2", "zrok2"),
        ]
        for label, val in tunnel_opts:
            self.tunnel_combo.addItem(label, val)
        network_form.addRow("Tunnel:", self.tunnel_combo)
        layout.addLayout(network_form)

    def _populate_modes(self):
        self._suppress_mode_change = True
        self.mode_combo.clear()
        for mode in self._mode_mgr.modes:
            label = mode.name
            if not mode.built_in:
                label += " *"
            self.mode_combo.addItem(label, mode.name)
        self._suppress_mode_change = False
        # Select Balanced by default
        idx = self.mode_combo.findData("Balanced")
        if idx >= 0:
            self.mode_combo.setCurrentIndex(idx)
        self._apply_mode("Balanced")

    def _connect_signals(self):
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        self.save_mode_btn.clicked.connect(self._on_save_mode)
        self.delete_mode_btn.clicked.connect(self._on_delete_mode)
        # When user tweaks spinners, switch to Custom
        self.fps_spin.valueChanged.connect(self._on_spin_changed)
        self.quality_spin.valueChanged.connect(self._on_spin_changed)
        self.scale_spin.valueChanged.connect(self._on_spin_changed)
        # Auto-save to YAML on any value change
        self.port_spin.valueChanged.connect(self._save_to_yaml)
        self.fps_spin.valueChanged.connect(self._save_to_yaml)
        self.quality_spin.valueChanged.connect(self._save_to_yaml)
        self.scale_spin.valueChanged.connect(self._save_to_yaml)
        self.tunnel_combo.currentIndexChanged.connect(self._save_to_yaml)

    # ── Mode selection ────────────────────────────────────────────────────────

    def _on_mode_changed(self, index: int):
        if self._suppress_mode_change:
            return
        name = self.mode_combo.currentData()
        if name:
            self._apply_mode(name)

    def _apply_mode(self, name: str):
        mode = self._mode_mgr.get(name)
        if not mode:
            return
        self._suppress_mode_change = True
        self.fps_spin.setValue(mode.fps)
        self.quality_spin.setValue(mode.quality)
        self.scale_spin.setValue(mode.scale)
        self._suppress_mode_change = False
        self._update_delete_btn()

    def _on_spin_changed(self):
        if self._suppress_mode_change:
            return
        # User tweaked a spinner - auto-detect matching mode
        fps = self.fps_spin.value()
        quality = self.quality_spin.value()
        scale = self.scale_spin.value()

        matched = None
        for m in self._mode_mgr.modes:
            if m.fps == fps and m.quality == quality and m.scale == scale:
                matched = m.name
                break

        self._suppress_mode_change = True
        if matched:
            idx = self.mode_combo.findData(matched)
            if idx >= 0:
                self.mode_combo.setCurrentIndex(idx)
        else:
            custom_idx = self.mode_combo.findData("Custom")
            if custom_idx < 0:
                self.mode_combo.addItem("Custom *", "Custom")
                custom_idx = self.mode_combo.count() - 1
            self.mode_combo.setCurrentIndex(custom_idx)
        self._suppress_mode_change = False
        self._update_delete_btn()

    # ── Save / Delete ─────────────────────────────────────────────────────────

    def _on_save_mode(self):
        from PyQt6.QtWidgets import QInputDialog

        current_name = self.mode_combo.currentData() or ""
        # Pre-fill with current name if it's a custom mode
        if self._mode_mgr.is_custom(current_name):
            prefill = current_name
        else:
            prefill = ""

        name, ok = QInputDialog.getText(
            self,
            "Save Capture Mode",
            "Mode name:",
            text=prefill,
        )
        if not ok or not name.strip():
            return
        name = name.strip()

        fps = self.fps_spin.value()
        quality = self.quality_spin.value()
        scale = self.scale_spin.value()

        if self._mode_mgr.get(name) and self._mode_mgr.is_custom(name):
            # Overwriting existing custom mode
            reply = QMessageBox.question(
                self,
                "Overwrite Mode",
                f'Mode "{name}" already exists. Overwrite?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self._mode_mgr.save_custom(name, fps, quality, scale)
        self._populate_modes()
        # Select the saved mode
        idx = self.mode_combo.findData(name)
        if idx >= 0:
            self.mode_combo.setCurrentIndex(idx)
        self._apply_mode(name)

    def _on_delete_mode(self):
        name = self.mode_combo.currentData()
        if not name or self._mode_mgr.is_custom(name) is False:
            return

        reply = QMessageBox.question(
            self,
            "Delete Mode",
            f'Delete mode "{name}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._mode_mgr.delete(name)
        self._populate_modes()

    def _update_delete_btn(self):
        name = self.mode_combo.currentData()
        self.delete_mode_btn.setEnabled(
            name is not None and self._mode_mgr.is_custom(name)
        )

    # ── YAML persistence ──────────────────────────────────────────────────────

    def _load_from_yaml(self):
        """Load settings from YAML config into the form widgets."""
        self._suppress_mode_change = True
        self._suppress_save = True
        self.port_spin.setValue(
            get_setting(self._cfg, "server", "port", default=DEFAULT_PORT)
        )
        self.fps_spin.setValue(
            get_setting(self._cfg, "screen_capture", "fps", default=DEFAULT_FPS)
        )
        self.quality_spin.setValue(
            get_setting(self._cfg, "screen_capture", "quality", default=DEFAULT_QUALITY)
        )
        self.scale_spin.setValue(
            get_setting(self._cfg, "screen_capture", "scale", default=DEFAULT_SCALE)
        )
        tunnel = get_setting(self._cfg, "server", "tunnel", default="local")
        idx = self.tunnel_combo.findData(tunnel)
        if idx >= 0:
            self.tunnel_combo.setCurrentIndex(idx)
        self._suppress_save = False
        self._suppress_mode_change = False

    def _save_to_yaml(self):
        """Save current form values to local_settings.yaml."""
        if self._suppress_save:
            return
        settings = {
            "server": {
                "host": "0.0.0.0",
                "port": self.port_spin.value(),
                "tunnel": self.tunnel_combo.currentData() or "local",
            },
            "screen_capture": {
                "enabled": True,
                "fps": self.fps_spin.value(),
                "quality": self.quality_spin.value(),
                "scale": self.scale_spin.value(),
            },
        }
        save_settings(settings)

    # ── Public API ────────────────────────────────────────────────────────────

    def get_params(self) -> dict:
        return {
            "port": self.port_spin.value(),
            "fps": self.fps_spin.value(),
            "quality": self.quality_spin.value(),
            "scale": self.scale_spin.value(),
            "tunnel": self.tunnel_combo.currentData(),
        }
