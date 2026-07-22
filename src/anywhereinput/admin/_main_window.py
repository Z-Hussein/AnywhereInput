"""MainWindow - main admin window with tabs."""

from PyQt6.QtWidgets import QMainWindow

from .main_window import (
    get_icon_path,
    setup_ui,
    start_server,
    stop_server,
    reconnect_tunnel,
    copy_server_url,
    reset_copy_button,
    open_in_browser,
    refresh_tokens,
    filter_token_table,
    new_token,
    token_context_menu,
    select_all_tokens,
    clear_selection,
    remove_selected_multi,
    filter_clients,
    kick_client,
    block_client_ip,
    open_client_dialog,
    filter_pending,
    approve_request,
    decline_request,
    on_log,
    filter_logs,
    clear_logs,
    export_logs,
    on_status_changed,
    start_auto_refresh,
    stop_auto_refresh,
    auto_refresh_tick,
    show_info,
    open_config_folder,
)


def _get_icon_path():
    return get_icon_path()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AnywhereInput Admin")
        self.setMinimumSize(1100, 700)
        self._log_lines = []
        self._current_requests = []
        self._current_clients = []
        self._current_tokens = []
        self._server_start_time = None
        self._tunnel_url = None
        self._server_thread = None
        self._auto_refresh_timer = None
        self._last_params = None
        self._active_notifications = []
        self._pending_count = 0
        self._notified_request_ids = set()
        self._info_dialog = None
        self._tray_icon = None
        from ._token_store import TokenStore

        self._store = TokenStore()
        self.init_ui()

    def init_ui(self):
        setup_ui(self)

    # ── Delegate all methods to the respective modules ──────────────

    def _start_server(self):
        start_server(self)

    def _stop_server(self):
        stop_server(self)

    def _reconnect_tunnel(self):
        reconnect_tunnel(self)

    def _copy_server_url(self):
        copy_server_url(self)

    def _reset_copy_button(self):
        reset_copy_button(self)

    def _open_browser(self):
        open_in_browser(self)

    def _refresh_tokens(self):
        refresh_tokens(self)

    def _filter_token_table(self, text):
        filter_token_table(self, text)

    def _new_token(self):
        new_token(self)

    def _select_all_tokens(self):
        select_all_tokens(self)

    def _clear_selection(self):
        clear_selection(self)

    def _remove_selected_multi(self):
        remove_selected_multi(self)

    def _token_context_menu(self, pos):
        token_context_menu(self, pos)

    def _on_mode_changed(self, index):
        pass

    def _filter_clients(self, text):
        filter_clients(self, text)

    def _kick_client(self, token_id, name):
        kick_client(self, token_id, name)

    def _block_client_ip(self, ip):
        block_client_ip(self, ip)

    def _open_client_dialog(self):
        open_client_dialog(self)

    def _filter_pending(self, text):
        filter_pending(self, text)

    def _approve_request(self, token_id):
        approve_request(self, token_id)

    def _deny_request(self, token_id):
        decline_request(self, token_id)

    def _on_log(self, text):
        on_log(self, text)

    def _filter_logs(self):
        filter_logs(self)

    def _clear_logs(self):
        clear_logs(self)

    def _export_logs(self):
        export_logs(self)

    def _on_status_changed(self, status):
        on_status_changed(self, status)

    def _start_auto_refresh(self):
        start_auto_refresh(self)

    def _stop_auto_refresh(self):
        stop_auto_refresh(self)

    def _auto_refresh_tick(self):
        auto_refresh_tick(self)

    def _show_info(self):
        show_info(self)

    def _open_config_folder(self):
        open_config_folder(self)
