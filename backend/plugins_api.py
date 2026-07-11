"""HTTP routes for Studio plugins (1.2.0)."""

from __future__ import annotations

from backend.plugin_registry import (
    disable_plugin,
    enable_plugin,
    get_plugin_panel,
    list_plugins_catalog,
    run_panel_action,
    sync_enabled_plugins_for_session,
)
from backend.snapshot_compat import normalize_state_snapshot


def on_session_imported(session) -> None:
    sync_enabled_plugins_for_session(session)
    from campaign_rpg_engine import emit_session_event

    emit_session_event(session, "session_loaded")


def get_plugins_catalog(session) -> dict[str, object]:
    return list_plugins_catalog(session)


def _snapshot(session) -> dict[str, object]:
    return normalize_state_snapshot(session.snapshot(include_private=True))


def post_enable_plugin(session, plugin_id: str) -> dict[str, object]:
    result = enable_plugin(session, plugin_id)
    if result.get("ok"):
        result["snapshot"] = _snapshot(session)
    return result


def post_disable_plugin(session, plugin_id: str) -> dict[str, object]:
    result = disable_plugin(session, plugin_id)
    if result.get("ok"):
        result["snapshot"] = _snapshot(session)
    return result


def get_plugin_panel_route(session, plugin_id: str) -> dict[str, object]:
    return get_plugin_panel(session, plugin_id)


def post_plugin_action(session, plugin_id: str, body: dict) -> dict[str, object]:
    action_id = str(body.get("action_id", "")).strip()
    params = body.get("params") if isinstance(body.get("params"), dict) else {}
    result = run_panel_action(session, plugin_id, action_id, params)
    if result.get("ok"):
        result["snapshot"] = _snapshot(session)
    return result
