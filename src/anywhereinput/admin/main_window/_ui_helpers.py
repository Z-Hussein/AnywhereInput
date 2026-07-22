"""Standalone UI helper functions — no window dependency."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtGui import QFont


def escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def get_icon_path() -> str:
    """Get path to the favicon.ico for use as app icon."""
    from pathlib import Path

    pkg_static = (
        Path(__file__).resolve().parent.parent.parent / "static" / "favicon.ico"
    )
    if pkg_static.exists():
        return str(pkg_static)
    dev_static = (
        Path(__file__).resolve().parents[4]
        / "src"
        / "anywhereinput"
        / "static"
        / "favicon.ico"
    )
    if dev_static.exists():
        return str(dev_static)
    return ""


def make_separator_v() -> QFrame:
    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.VLine)
    sep.setFrameShadow(QFrame.Shadow.Sunken)
    sep.setStyleSheet("color: #334155;")
    sep.setFixedHeight(20)
    return sep


def make_empty_state(
    icon: str,
    title: str,
    description: str,
    button_text: str = "",
    button_callback=None,
) -> QWidget:
    """Build a rich empty state widget with icon, title, description, and optional action button."""
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(20, 24, 20, 24)
    layout.setSpacing(6)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

    icon_lbl = QLabel(icon)
    icon_lbl.setFont(QFont("Sans", 28))
    icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_lbl.setStyleSheet("background: transparent;")
    layout.addWidget(icon_lbl)

    title_lbl = QLabel(title)
    title_lbl.setFont(QFont("Sans", 11, QFont.Weight.Bold))
    title_lbl.setStyleSheet("color: #e2e8f0; background: transparent;")
    title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(title_lbl)

    desc_lbl = QLabel(description)
    desc_lbl.setFont(QFont("Sans", 9))
    desc_lbl.setStyleSheet("color: #64748b; background: transparent;")
    desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    desc_lbl.setWordWrap(True)
    layout.addWidget(desc_lbl)

    if button_text and button_callback:
        layout.addSpacing(4)
        btn = QPushButton(button_text)
        btn.setFixedHeight(26)
        btn.setStyleSheet(
            "QPushButton {"
            "  background: #1e293b;"
            "  border: 1px solid #334155;"
            "  border-radius: 4px;"
            "  color: #94a3b8;"
            "  font-size: 11px;"
            "  padding: 2px 12px;"
            "}"
            "QPushButton:hover { background: #334155; border-color: #475569; }"
        )
        btn.clicked.connect(button_callback)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    return widget


def show_info(window) -> None:
    if window._info_dialog is None:
        from PyQt6.QtWidgets import QDialog

        window._info_dialog = QDialog(window)
        window._info_dialog.setWindowTitle("AnywhereInput - Guide")
        window._info_dialog.setMinimumSize(520, 620)
        layout = QVBoxLayout(window._info_dialog)
        from .._info_panel import InfoPanel

        window.info_text = InfoPanel()
        layout.addWidget(window.info_text)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(window._info_dialog.accept)
        layout.addWidget(close_btn)
    window._info_dialog.show()
    window._info_dialog.raise_()
    window._info_dialog.activateWindow()


def open_config_folder() -> None:
    from .._utils import _PROJECT_ROOT
    import subprocess
    import platform

    config_dir = _PROJECT_ROOT
    system = platform.system()
    if system == "Darwin":
        subprocess.Popen(["open", str(config_dir)])
    elif system == "Windows":
        subprocess.Popen(["explorer", str(config_dir)])
    else:
        subprocess.Popen(["xdg-open", str(config_dir)])
