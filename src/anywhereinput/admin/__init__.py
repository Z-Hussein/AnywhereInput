"""AnywhereInput desktop admin app package."""

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
    from ._token_dialog import TokenManagerDialog
    from ._approval_dialog import ApprovalDialog
    from ._client_dialog import ClientListDialog
    from ._settings_panel import SettingsPanel
    from ._main_window import MainWindow
else:
    ServerProcessWorker = None  # type: ignore[misc, assignment]
    TokenManagerDialog = None  # type: ignore[misc, assignment]
    ApprovalDialog = None  # type: ignore[misc, assignment]
    ClientListDialog = None  # type: ignore[misc, assignment]
    SettingsPanel = None  # type: ignore[misc, assignment]
    MainWindow = None  # type: ignore[misc, assignment]

try:
    from ._tray_app import run_admin_app, _cleanup_and_quit
except ImportError:
    run_admin_app = None  # type: ignore
    _cleanup_and_quit = None  # type: ignore

__all__ = [
    "QT_AVAILABLE",
    "_PROJECT_ROOT",
    "ServerProcessWorker",
    "TokenStore",
    "TokenManagerDialog",
    "ApprovalDialog",
    "ClientListDialog",
    "SettingsPanel",
    "MainWindow",
    "run_admin_app",
    "_cleanup_and_quit",
]
