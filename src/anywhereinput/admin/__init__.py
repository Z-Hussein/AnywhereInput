"""AnywhereInput desktop admin app package."""

import sys as _sys

# ---------------------------------------------------------------------------
# Qt imports (optional - app won't crash if PyQt6 is missing)
# ---------------------------------------------------------------------------
try:
    from PyQt6.QtWidgets import QApplication  # noqa: F401

    QT_AVAILABLE = True
except ImportError:
    QApplication = None  # type: ignore[assignment,misc]
    QT_AVAILABLE = False

from ._token_store import TokenStore
from ._utils import _PROJECT_ROOT

if QT_AVAILABLE:
    from ._server_worker import ServerProcessWorker
    from ._engine_status import EngineStatusWidget
    from ._token_dialog import TokenManagerDialog
    from ._approval_dialog import ApprovalDialog
    from ._client_dialog import ClientListDialog
    from ._settings_panel import SettingsPanel
    from ._main_window import MainWindow
else:
    ServerProcessWorker = None  # type: ignore[misc, assignment]
    EngineStatusWidget = None  # type: ignore[misc, assignment]
    TokenManagerDialog = None  # type: ignore[misc, assignment]
    ApprovalDialog = None  # type: ignore[misc, assignment]
    ClientListDialog = None  # type: ignore[misc, assignment]
    SettingsPanel = None  # type: ignore[misc, assignment]
    MainWindow = None  # type: ignore[misc, assignment]

__all__ = [
    "QT_AVAILABLE",
    "_PROJECT_ROOT",
    "ServerProcessWorker",
    "TokenStore",
    "EngineStatusWidget",
    "TokenManagerDialog",
    "ApprovalDialog",
    "ClientListDialog",
    "SettingsPanel",
    "MainWindow",
    "run_admin_app",
]


def run_admin_app():
    """Entry point for `anywhereinput --app`."""
    if not QT_AVAILABLE:
        from anywhereinput import safe_print_stderr

        safe_print_stderr("\u274c PyQt6 is required for the admin app.")
        safe_print_stderr("   Install it with: pip install PyQt6")
        _sys.exit(1)

    from ._main_window import MainWindow as _MainWindow, _get_icon_path
    from PyQt6.QtGui import QIcon

    app = QApplication(_sys.argv)
    app.setStyle("Fusion")

    # Set application icon from favicon.ico for OS taskbar/dock
    icon_path = _get_icon_path()
    if icon_path:
        app.setWindowIcon(QIcon(icon_path))

    window = _MainWindow()
    window.show()

    _sys.exit(app.exec())
