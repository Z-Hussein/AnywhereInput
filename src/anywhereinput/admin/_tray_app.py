"""Tray application entry point for the admin GUI."""

import sys as _sys

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPalette, QColor

from ._utils import is_first_run, mark_setup_completed

_cleaned_up = False


def _cleanup_and_quit(window, tray_icon=None):
    """Stop server, timers, and quit the application."""
    global _cleaned_up
    if _cleaned_up:
        return
    _cleaned_up = True
    if window._server_thread and window._server_thread.isRunning():
        window._server_thread.stop()
        window._server_thread.quit()
        window._server_thread.wait(3000)
    from .main_window import stop_auto_refresh

    stop_auto_refresh(window)
    if tray_icon:
        tray_icon.hide()
    QApplication.instance().quit()


def run_admin_app():
    """Entry point for `anywhereinput --app`."""
    try:
    from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
    from PyQt6.QtGui import QIcon, QAction
    from PyQt6.QtCore import Qt, QThread, pyqtSignal
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    # Dummy placeholders so the module loads without PyQt6
    QApplication = None  # type: ignore
    QSystemTrayIcon = None  # type: ignore
    QMenu = None  # type: ignore
    QIcon = None  # type: ignore
    QAction = None  # type: ignore
    Qt = None  # type: ignore
    QThread = None  # type: ignore
    pyqtSignal = None  # type: ignore

    from ._main_window import MainWindow, _get_icon_path

    app = QApplication(_sys.argv)
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(24, 32, 48))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(226, 232, 240))
    palette.setColor(QPalette.ColorRole.Base, QColor(30, 41, 59))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(30, 41, 59))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(30, 41, 59))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(226, 232, 240))
    palette.setColor(QPalette.ColorRole.Text, QColor(226, 232, 240))
    palette.setColor(QPalette.ColorRole.Button, QColor(30, 41, 59))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(226, 232, 240))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Link, QColor(96, 165, 250))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(59, 130, 246))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)

    icon_path = _get_icon_path()
    if icon_path:
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()

    # First-run wizard
    if is_first_run():
        from ._welcome_wizard import WelcomeWizard

        wizard = WelcomeWizard()
        if wizard.exec() == 1:
            port = wizard.result_port
            tunnel = wizard.result_tunnel
            window.settings_panel.port_spin.setValue(port)
            idx = window.settings_panel.tunnel_combo.findData(tunnel)
            if idx >= 0:
                window.settings_panel.tunnel_combo.setCurrentIndex(idx)
            mark_setup_completed()

    tray_icon = QSystemTrayIcon(QIcon(icon_path) if icon_path else QIcon(), app)
    tray_menu = QMenu()
    show_action = tray_menu.addAction("Show")
    show_action.triggered.connect(window.show)
    show_action.triggered.connect(window.raise_)
    show_action.triggered.connect(window.activateWindow)
    quit_action = tray_menu.addAction("Quit")
    quit_action.triggered.connect(lambda: _cleanup_and_quit(window, tray_icon))
    tray_icon.setContextMenu(tray_menu)
    tray_icon.setToolTip("AnywhereInput Admin")
    tray_icon.activated.connect(
        lambda reason: (
            window.show()
            if reason == QSystemTrayIcon.ActivationReason.DoubleClick
            else None
        )
    )
    tray_icon.show()

    window._tray_icon = tray_icon

    def close_event(event):
        _cleanup_and_quit(window, tray_icon)
        event.accept()

    window.closeEvent = close_event

    app.aboutToQuit.connect(lambda: _cleanup_and_quit(window, tray_icon))

    window.show()
    _sys.exit(app.exec())
