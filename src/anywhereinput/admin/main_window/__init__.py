"""MainWindow internal components — re-exports for convenience."""

from ._ui_helpers import (  # noqa: F401
    escape_html,
    get_icon_path,
    make_separator_v,
    make_empty_state,
    show_info,
    open_config_folder,
)
from ._server_control import (  # noqa: F401
    start_server,
    stop_server,
    reconnect_tunnel,
    copy_server_url,
    reset_copy_button,
    open_in_browser,
    start_auto_refresh,
    stop_auto_refresh,
    auto_refresh_tick,
)
from ._token_management import (  # noqa: F401
    refresh_tokens,
    populate_token_table,
    filter_token_table,
    make_permission_badges,
    make_action_widget,
    new_token,
    edit_token_by_row,
    revoke_token,
    copy_token,
    token_context_menu,
    duplicate_token,
    select_all_tokens,
    clear_selection,
    remove_selected_multi,
)
from ._client_management import (  # noqa: F401
    refresh_clients,
    populate_client_cards,
    populate_client_cards_error,
    filter_clients,
    make_client_card,
    client_context_menu,
    copy_to_clipboard,
    kick_client,
    block_client_ip,
    open_client_dialog,
)
from ._request_management import (  # noqa: F401
    refresh_requests,
    populate_pending_cards,
    filter_pending,
    make_request_card,
    approve_request,
    get_request_token,
    decline_request,
)
from ._log_management import (  # noqa: F401
    on_log,
    detect_log_level,
    apply_log_filters,
    LOG_COLORS,
    filter_logs,
    clear_logs,
    export_logs,
)
from ._notifications import (  # noqa: F401
    show_connection_notification,
    approve_request_by_id,
    decline_request_by_id,
)
from ._metrics import on_status_changed, update_dashboard, format_uptime  # noqa: F401
from ._ui_setup import setup_ui  # noqa: F401
