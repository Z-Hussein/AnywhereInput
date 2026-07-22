"""init_ui() — builds top bar, overview cards, tabs, status bar."""

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from .._status_bar import StatusBar
from .._settings_panel import SettingsPanel
from .._activity_log import ActivityLog
from ._ui_helpers import get_icon_path, make_separator_v, make_empty_state


def setup_ui(window) -> None:
    icon_path = get_icon_path()
    if icon_path:
        from PyQt6.QtGui import QIcon

        window.setWindowIcon(QIcon(icon_path))

    central = QWidget()
    window.setCentralWidget(central)
    main_layout = QVBoxLayout(central)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.setSpacing(0)

    # ═══════════════════════════════════════════════════════════════════
    # LEVEL 1: Top Bar
    # ═══════════════════════════════════════════════════════════════════
    top_bar = QWidget()
    top_bar.setFixedHeight(48)
    top_bar.setStyleSheet(
        "QWidget { background: #0f172a; border-bottom: 1px solid #1e293b; }"
    )
    top_layout = QHBoxLayout(top_bar)
    top_layout.setContentsMargins(12, 0, 12, 0)
    top_layout.setSpacing(12)

    app_name = QLabel("AnywhereInput")
    app_name.setFont(QFont("Sans", 14, QFont.Weight.Bold))
    app_name.setStyleSheet("color: #e2e8f0; background: transparent; border: none;")
    top_layout.addWidget(app_name)

    version_lbl = QLabel("v1.3.0")
    version_lbl.setFont(QFont("Sans", 9))
    version_lbl.setStyleSheet("color: #475569; background: transparent; border: none;")
    top_layout.addWidget(version_lbl)

    top_layout.addStretch()

    # Start / Stop buttons in top bar
    window.start_btn = QPushButton("Start Server")
    window.start_btn.setFixedHeight(28)
    window.start_btn.setStyleSheet(
        "QPushButton {"
        "  background: #166534;"
        "  color: white;"
        "  font-weight: bold;"
        "  border: none;"
        "  border-radius: 4px;"
        "  padding: 0 12px;"
        "  font-size: 11px;"
        "}"
        "QPushButton:hover { background: #15803d; }"
        "QPushButton:disabled { background: #334155; color: #64748b; }"
    )
    window.start_btn.clicked.connect(
        lambda: _lazy_import("_server_control", "start_server")(window)
    )
    top_layout.addWidget(window.start_btn)

    window.stop_btn = QPushButton("Stop Server")
    window.stop_btn.setFixedHeight(28)
    window.stop_btn.setEnabled(False)
    window.stop_btn.setStyleSheet(
        "QPushButton {"
        "  background: #991b1b;"
        "  color: white;"
        "  font-weight: bold;"
        "  border: none;"
        "  border-radius: 4px;"
        "  padding: 0 12px;"
        "  font-size: 11px;"
        "}"
        "QPushButton:hover { background: #b91c1c; }"
        "QPushButton:disabled { background: #334155; color: #64748b; }"
    )
    window.stop_btn.clicked.connect(
        lambda: _lazy_import("_server_control", "stop_server")(window)
    )
    top_layout.addWidget(window.stop_btn)

    # Status indicator
    window._status_indicator = QLabel("Offline")
    window._status_indicator.setFont(QFont("Sans", 9, QFont.Weight.Bold))
    window._status_indicator.setStyleSheet(
        "color: #ef4444; background: transparent; border: none; padding: 0 4px;"
    )
    top_layout.addWidget(window._status_indicator)

    info_btn = QPushButton("?")
    info_btn.setFixedSize(26, 26)
    info_btn.setToolTip("App Guide")
    info_btn.setStyleSheet(
        "QPushButton {"
        "  background: transparent;"
        "  border: 1px solid #334155;"
        "  border-radius: 4px;"
        "  color: #64748b;"
        "  font-size: 11px;"
        "  font-weight: bold;"
        "}"
        "QPushButton:hover { background: #1e293b; color: #94a3b8; border-color: #475569; }"
    )
    info_btn.clicked.connect(lambda: _lazy_import("_ui_helpers", "show_info")(window))
    top_layout.addWidget(info_btn)

    main_layout.addWidget(top_bar)

    # ═══════════════════════════════════════════════════════════════════
    # LEVEL 2: Overview Cards
    # ═══════════════════════════════════════════════════════════════════
    overview_container = QWidget()
    overview_container.setStyleSheet(
        "QWidget { background: #0f172a; border-bottom: 1px solid #1e293b; }"
    )
    overview_layout = QHBoxLayout(overview_container)
    overview_layout.setContentsMargins(12, 8, 12, 8)
    overview_layout.setSpacing(8)

    def _make_card(label: str) -> tuple:
        """Create a metric card widget. Returns (widget, value_label)."""
        card = QWidget()
        card.setStyleSheet(
            "QWidget { background: #1e293b; border: 1px solid #1e293b; border-radius: 6px; }"
        )
        card.setFixedHeight(52)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(10, 6, 10, 6)
        card_layout.setSpacing(0)
        lbl = QLabel(label)
        lbl.setFont(QFont("Sans", 8))
        lbl.setStyleSheet("color: #64748b; background: transparent; border: none;")
        card_layout.addWidget(lbl)
        val = QLabel("-")
        val.setFont(QFont("Monospace", 11, QFont.Weight.Bold))
        val.setStyleSheet("color: #e2e8f0; background: transparent; border: none;")
        card_layout.addWidget(val)
        return card, val

    # URL card
    url_card, window._overview_url_lbl = _make_card("URL")
    window._overview_url_lbl.setFont(QFont("Monospace", 9))
    window._overview_url_lbl.setTextInteractionFlags(
        Qt.TextInteractionFlag.TextSelectableByMouse
    )
    overview_layout.addWidget(url_card, 2)

    # Copy URL button (overlaid on URL card)
    window.copy_url_btn = QPushButton("Copy")
    window.copy_url_btn.setFixedSize(36, 18)
    window.copy_url_btn.setEnabled(False)
    window.copy_url_btn.setStyleSheet(
        "QPushButton {"
        "  background: #0f172a;"
        "  border: 1px solid #334155;"
        "  border-radius: 3px;"
        "  color: #64748b;"
        "  font-size: 9px;"
        "  padding: 0;"
        "}"
        "QPushButton:hover { background: #334155; color: #94a3b8; }"
    )
    window.copy_url_btn.clicked.connect(
        lambda: _lazy_import("_server_control", "copy_server_url")(window)
    )

    # URL label for the old reference (used in _copy_server_url, etc.)
    window.url_lbl = window._overview_url_lbl

    # Clients card
    clients_card, window.dash_clients_lbl = _make_card("Clients")
    overview_layout.addWidget(clients_card)

    # Pending card
    pending_card, window.dash_pending_lbl = _make_card("Pending")
    overview_layout.addWidget(pending_card)

    # Uptime card
    uptime_card, window.uptime_lbl = _make_card("Uptime")
    overview_layout.addWidget(uptime_card)

    # Tunnel card
    tunnel_card, window._overview_tunnel_lbl = _make_card("Tunnel")
    window._overview_tunnel_lbl.setFont(QFont("Sans", 9))
    overview_layout.addWidget(tunnel_card, 1)

    # FPS card
    fps_card, window.dash_fps_lbl = _make_card("FPS")
    overview_layout.addWidget(fps_card)

    # Bandwidth card
    bw_card, window.dash_bw_lbl = _make_card("Bandwidth")
    overview_layout.addWidget(bw_card)

    main_layout.addWidget(overview_container)

    # ═══════════════════════════════════════════════════════════════════
    # LEVEL 3: Tabs
    # ═══════════════════════════════════════════════════════════════════
    window.tabs = QTabWidget()
    window.tabs.setStyleSheet(
        "QTabWidget::pane { border: none; background: #0f172a; }"
        "QTabBar::tab {"
        "  background: #0f172a;"
        "  color: #64748b;"
        "  border: none;"
        "  border-bottom: 2px solid transparent;"
        "  padding: 8px 16px;"
        "  font-size: 11px;"
        "}"
        "QTabBar::tab:selected { color: #e2e8f0; border-bottom-color: #3b82f6; }"
        "QTabBar::tab:hover { color: #94a3b8; }"
    )

    # ── Clients Tab ──────────────────────────────────────────────────
    clients_tab = QWidget()
    clients_ly = QVBoxLayout(clients_tab)
    clients_ly.setContentsMargins(8, 8, 8, 8)
    clients_ly.setSpacing(6)

    pending_header = QHBoxLayout()
    pending_title = QLabel("Pending Requests")
    pending_title.setFont(QFont("Sans", 11, QFont.Weight.Bold))
    pending_title.setStyleSheet("color: #e2e8f0;")
    pending_header.addWidget(pending_title)
    pending_header.addStretch()
    window.pending_count_lbl = QLabel("0")
    window.pending_count_lbl.setStyleSheet(
        "background: #92400e; color: #fef3c7; border-radius: 10px;"
        "padding: 2px 8px; font-size: 11px; font-weight: bold;"
    )
    pending_header.addWidget(window.pending_count_lbl)
    clients_ly.addLayout(pending_header)

    window.pending_search_input = QLineEdit()
    window.pending_search_input.setPlaceholderText("Search requests...")
    window.pending_search_input.textChanged.connect(
        lambda text: _lazy_import("_request_management", "filter_pending")(window, text)
    )
    clients_ly.addWidget(window.pending_search_input)

    window.pending_scroll = QScrollArea()
    window.pending_scroll.setWidgetResizable(True)
    window.pending_scroll.setHorizontalScrollBarPolicy(
        Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    )
    window.pending_scroll.setFrameShape(QFrame.Shape.NoFrame)
    window.pending_scroll.setMaximumHeight(250)
    window.pending_container = QWidget()
    window.pending_layout = QVBoxLayout(window.pending_container)
    window.pending_layout.setContentsMargins(0, 0, 0, 0)
    window.pending_layout.setSpacing(4)
    window.pending_layout.addStretch()
    window.pending_scroll.setWidget(window.pending_container)
    clients_ly.addWidget(window.pending_scroll)

    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.HLine)
    sep.setFrameShadow(QFrame.Shadow.Sunken)
    sep.setStyleSheet("color: #1e293b;")
    clients_ly.addWidget(sep)

    conn_header = QHBoxLayout()
    conn_title = QLabel("Connected Clients")
    conn_title.setFont(QFont("Sans", 11, QFont.Weight.Bold))
    conn_title.setStyleSheet("color: #e2e8f0;")
    conn_header.addWidget(conn_title)
    conn_header.addStretch()
    manage_btn = QPushButton("Manage")
    manage_btn.setFixedHeight(24)
    manage_btn.setStyleSheet(
        "QPushButton {"
        "  background: #1e293b; border: 1px solid #334155;"
        "  border-radius: 3px; color: #94a3b8; font-size: 11px; padding: 2px 8px;"
        "}"
        "QPushButton:hover { background: #334155; }"
    )
    manage_btn.clicked.connect(
        lambda: _lazy_import("_client_management", "open_client_dialog")(window)
    )
    conn_header.addWidget(manage_btn)
    clients_ly.addLayout(conn_header)

    window.clients_search_input = QLineEdit()
    window.clients_search_input.setPlaceholderText("Search clients...")
    window.clients_search_input.textChanged.connect(
        lambda text: _lazy_import("_client_management", "filter_clients")(window, text)
    )
    clients_ly.addWidget(window.clients_search_input)

    window.clients_scroll = QScrollArea()
    window.clients_scroll.setWidgetResizable(True)
    window.clients_scroll.setHorizontalScrollBarPolicy(
        Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    )
    window.clients_scroll.setFrameShape(QFrame.Shape.NoFrame)
    window.clients_container = QWidget()
    window.clients_layout = QVBoxLayout(window.clients_container)
    window.clients_layout.setContentsMargins(0, 0, 0, 0)
    window.clients_layout.setSpacing(4)
    window.clients_layout.addStretch()
    window.clients_scroll.setWidget(window.clients_container)
    clients_ly.addWidget(window.clients_scroll)

    window.tabs.addTab(clients_tab, "Clients")

    # ── Tokens Tab ───────────────────────────────────────────────────
    token_tab = QWidget()
    token_ly = QVBoxLayout(token_tab)
    token_ly.setContentsMargins(8, 8, 8, 8)
    token_ly.setSpacing(4)

    token_search_row = QHBoxLayout()
    window.token_search_input = QLineEdit()
    window.token_search_input.setPlaceholderText("Search tokens...")
    window.token_search_input.textChanged.connect(
        lambda text: _lazy_import("_token_management", "filter_token_table")(
            window, text
        )
    )
    token_search_row.addWidget(window.token_search_input)
    token_ly.addLayout(token_search_row)

    window.token_table = QTableWidget()
    window.token_table.setColumnCount(6)
    window.token_table.setHorizontalHeaderLabels(
        ["Select", "Name", "Token", "Permissions", "IPs", "Actions"]
    )
    window.token_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    window.token_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    window.token_table.customContextMenuRequested.connect(
        lambda pos: _lazy_import("_token_management", "token_context_menu")(window, pos)
    )
    for col in range(window.token_table.columnCount()):
        header_item = window.token_table.horizontalHeaderItem(col)
        if header_item:
            header_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    header = window.token_table.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    token_ly.addWidget(window.token_table)

    window.token_empty_state = make_empty_state(
        icon="",
        title="No tokens yet",
        description="Create a token to allow devices to connect to your server.",
        button_text="+ New Token",
        button_callback=lambda: _lazy_import("_token_management", "new_token")(window),
    )
    token_ly.addWidget(window.token_empty_state)
    window.token_empty_state.setVisible(False)

    token_btns = QHBoxLayout()

    new_token_btn = QPushButton("+ New Token")
    new_token_btn.clicked.connect(
        lambda: _lazy_import("_token_management", "new_token")(window)
    )
    token_btns.addWidget(new_token_btn)

    select_all_btn = QPushButton("Select All")
    select_all_btn.clicked.connect(
        lambda: _lazy_import("_token_management", "select_all_tokens")(window)
    )
    token_btns.addWidget(select_all_btn)

    clear_select_btn = QPushButton("Clear Select")
    clear_select_btn.clicked.connect(
        lambda: _lazy_import("_token_management", "clear_selection")(window)
    )
    token_btns.addWidget(clear_select_btn)

    remove_selected_btn = QPushButton("Remove Selected")
    remove_selected_btn.clicked.connect(
        lambda: _lazy_import("_token_management", "remove_selected_multi")(window)
    )
    token_btns.addWidget(remove_selected_btn)

    refresh_btn = QPushButton("Refresh")
    refresh_btn.clicked.connect(
        lambda: _lazy_import("_token_management", "refresh_tokens")(window)
    )
    token_btns.addWidget(refresh_btn)
    token_btns.addStretch()
    token_ly.addLayout(token_btns)

    window.tabs.addTab(token_tab, "Tokens")

    # ── Activity Tab ─────────────────────────────────────────────────
    activity_tab = QWidget()
    activity_ly = QVBoxLayout(activity_tab)
    activity_ly.setContentsMargins(0, 0, 0, 0)
    window.activity_log = ActivityLog()
    activity_ly.addWidget(window.activity_log)
    window.tabs.addTab(activity_tab, "Activity")

    # ── Settings Tab ─────────────────────────────────────────────────
    settings_tab = QWidget()
    settings_ly = QVBoxLayout(settings_tab)
    settings_ly.setContentsMargins(12, 12, 12, 12)
    window.settings_panel = SettingsPanel()
    settings_ly.addWidget(window.settings_panel)
    settings_ly.addStretch()
    window.tabs.addTab(settings_tab, "Settings")

    # ── Logs Tab ─────────────────────────────────────────────────────
    logs_tab = QWidget()
    logs_ly = QVBoxLayout(logs_tab)
    logs_ly.setContentsMargins(8, 8, 8, 8)
    logs_ly.setSpacing(4)

    toolbar = QHBoxLayout()
    toolbar.setSpacing(6)

    window.log_filter_input = QLineEdit()
    window.log_filter_input.setPlaceholderText("Search logs...")
    window.log_filter_input.setFixedWidth(160)
    window.log_filter_input.textChanged.connect(
        lambda _text: _lazy_import("_log_management", "filter_logs")(window)
    )
    toolbar.addWidget(window.log_filter_input)

    toolbar.addWidget(make_separator_v())

    window.log_level_combo = QComboBox()
    window.log_level_combo.setFixedWidth(90)
    for level in ["All", "INFO", "WARN", "ERROR", "CLIENT", "TOKEN"]:
        window.log_level_combo.addItem(level)
    window.log_level_combo.currentTextChanged.connect(
        lambda _text: _lazy_import("_log_management", "filter_logs")(window)
    )
    toolbar.addWidget(window.log_level_combo)

    toolbar.addWidget(make_separator_v())

    window.auto_scroll_cb = QCheckBox("Auto Scroll")
    window.auto_scroll_cb.setChecked(True)
    window.auto_scroll_cb.setStyleSheet("color: #94a3b8; font-size: 11px;")
    toolbar.addWidget(window.auto_scroll_cb)

    toolbar.addStretch()

    clear_btn = QPushButton("Clear")
    clear_btn.setFixedHeight(24)
    clear_btn.setStyleSheet(
        "QPushButton {"
        "  background: #1e293b; border: 1px solid #334155;"
        "  border-radius: 3px; color: #94a3b8; font-size: 11px; padding: 2px 8px;"
        "}"
        "QPushButton:hover { background: #334155; }"
    )
    clear_btn.clicked.connect(
        lambda: _lazy_import("_log_management", "clear_logs")(window)
    )
    toolbar.addWidget(clear_btn)

    logs_ly.addLayout(toolbar)

    window.log_text = QTextEdit()
    window.log_text.setFont(QFont("Monospace", 9))
    window.log_text.setReadOnly(True)
    window.log_text.setStyleSheet(
        "QTextEdit {"
        "  background: #0d1117;"
        "  color: #c9d1d9;"
        "  border: 1px solid #30363d;"
        "  border-radius: 4px;"
        "  padding: 4px;"
        "}"
    )
    logs_ly.addWidget(window.log_text)

    window.tabs.addTab(logs_tab, "Logs")

    main_layout.addWidget(window.tabs, 1)

    # ═══════════════════════════════════════════════════════════════════
    # Bottom Status Bar
    # ═══════════════════════════════════════════════════════════════════
    window.status_bar = StatusBar()
    window.status_bar.set_reconnect_callback(
        lambda: _lazy_import("_server_control", "reconnect_tunnel")(window)
    )
    main_layout.addWidget(window.status_bar)


def _lazy_import(module_name: str, func_name: str):
    """Lazy import to avoid circular imports at module level."""
    import importlib

    mod = importlib.import_module(
        f".{module_name}", package="anywhereinput.admin.main_window"
    )
    return getattr(mod, func_name)
