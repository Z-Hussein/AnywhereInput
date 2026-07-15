"""SettingsPanel - server config form."""

from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QSpinBox,
    QVBoxLayout,
)


class SettingsPanel(QFrame):
    """Server configuration panel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        port_box = QGroupBox("Server")
        port_layout = QFormLayout(port_box)
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1024, 65535)
        self.port_spin.setValue(8008)
        port_layout.addRow("Port:", self.port_spin)
        layout.addWidget(port_box)

        capture_box = QGroupBox("Screen Capture")
        capture_layout = QFormLayout(capture_box)
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 120)
        self.fps_spin.setValue(30)
        capture_layout.addRow("FPS:", self.fps_spin)

        quality_spin = QSpinBox()
        quality_spin.setRange(1, 95)
        quality_spin.setValue(85)
        capture_layout.addRow("Quality (JPEG):", quality_spin)

        scale_spin = QDoubleSpinBox()
        scale_spin.setRange(0.1, 1.0)
        scale_spin.setSingleStep(0.1)
        scale_spin.setValue(1.0)
        capture_layout.addRow("Scale:", scale_spin)
        self.quality_spin = quality_spin
        self.scale_spin = scale_spin
        layout.addWidget(capture_box)

        # Tunnel selection
        tunnel_box = QGroupBox("Tunnel")
        tunnel_layout = QHBoxLayout(tunnel_box)
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
        tunnel_layout.addWidget(self.tunnel_combo)
        layout.addWidget(tunnel_box)

        self._port_spin = self.port_spin
        self._fps_spin = self.fps_spin
        self._quality_spin = quality_spin
        self._scale_spin = scale_spin
        self._tunnel_combo = self.tunnel_combo

    def get_params(self) -> dict:
        return {
            "port": self._port_spin.value(),
            "fps": self._fps_spin.value(),
            "quality": self._quality_spin.value(),
            "scale": self._scale_spin.value(),
            "tunnel": self._tunnel_combo.currentData(),
        }
