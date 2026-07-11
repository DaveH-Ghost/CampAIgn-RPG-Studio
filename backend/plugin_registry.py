"""Installed plugin registry and per-session enablement (1.2.0)."""

from __future__ import annotations

from typing import Any

from campaign_rpg_engine import unregister_event_listeners

from backend.plugin_context import PluginManifest

_STUDIO_PLUGINS_KEY = "_studio_plugins"

_REGISTRY: dict[str, PluginManifest] = {}


def _default_studio_plugin_state() -> dict[str, Any]:
    return {"enabled": [], "config": {}}


def get_studio_plugin_state(session) -> dict[str, Any]:
    raw = session.extensions.get(_STUDIO_PLUGINS_KEY)
    if not isinstance(raw, dict):
        raw = _default_studio_plugin_state()
        session.extensions[_STUDIO_PLUGINS_KEY] = raw
    if "enabled" not in raw or not isinstance(raw["enabled"], list):
        raw["enabled"] = []
    if "config" not in raw or not isinstance(raw["config"], dict):
        raw["config"] = {}
    return raw


def is_plugin_enabled(session, plugin_id: str) -> bool:
    state = get_studio_plugin_state(session)
    return plugin_id in state["enabled"]


def plugin_id_owning_handler(handler_id: str) -> str | None:
    for manifest in list_installed_plugins():
        if handler_id in manifest.handler_ids:
            return manifest.plugin_id
    return None


def plugin_id_owning_turn_verb(verb_id: str) -> str | None:
    for manifest in list_installed_plugins():
        if verb_id in manifest.turn_verb_ids:
            return manifest.plugin_id
    return None


def plugin_id_owning_prompt_slot(slot_name: str) -> str | None:
    for manifest in list_installed_plugins():
        for name, _, _ in manifest.prompt_slots:
            if name == slot_name:
                return manifest.plugin_id
    return None


def is_handler_visible_in_catalog(session, handler_id: str) -> bool:
    owner = plugin_id_owning_handler(handler_id)
    if owner is None:
        return True
    return is_plugin_enabled(session, owner)


def is_turn_verb_visible_in_catalog(session, verb_id: str) -> bool:
    owner = plugin_id_owning_turn_verb(verb_id)
    if owner is None:
        return True
    return is_plugin_enabled(session, owner)


def is_prompt_slot_visible_in_catalog(session, slot_name: str) -> bool:
    owner = plugin_id_owning_prompt_slot(slot_name)
    if owner is None:
        return True
    return is_plugin_enabled(session, owner)


def list_installed_plugins() -> list[PluginManifest]:
    return [_REGISTRY[pid] for pid in sorted(_REGISTRY)]


def get_plugin_manifest(plugin_id: str) -> PluginManifest | None:
    return _REGISTRY.get(plugin_id)


def register_plugin_manifest(manifest: PluginManifest) -> None:
    if manifest.plugin_id in _REGISTRY:
        raise ValueError(f"Duplicate plugin id {manifest.plugin_id!r}")
    _REGISTRY[manifest.plugin_id] = manifest


def clear_plugin_registry_for_tests() -> None:
    _REGISTRY.clear()


def bind_enabled_plugin(session, plugin_id: str) -> str | None:
    manifest = _REGISTRY.get(plugin_id)
    if manifest is None:
        return f"Unknown plugin {plugin_id!r}."
    from campaign_rpg_engine.events.registry import register_event_listener

    unregister_event_listeners(plugin_id)
    for event, listener in manifest.event_listeners:
        register_event_listener(event, listener, plugin_id=plugin_id)
    return None


def unbind_enabled_plugin(session, plugin_id: str) -> None:
    del session
    unregister_event_listeners(plugin_id)


def sync_enabled_plugins_for_session(session) -> None:
    """Bind listeners for all plugins enabled in *session*."""
    state = get_studio_plugin_state(session)
    for plugin_id in state["enabled"]:
        if plugin_id in _REGISTRY:
            bind_enabled_plugin(session, plugin_id)


def enable_plugin(session, plugin_id: str) -> dict[str, Any]:
    if plugin_id not in _REGISTRY:
        return {"ok": False, "message": f"Unknown plugin {plugin_id!r}."}
    state = get_studio_plugin_state(session)
    if plugin_id not in state["enabled"]:
        state["enabled"].append(plugin_id)
    err = bind_enabled_plugin(session, plugin_id)
    if err:
        return {"ok": False, "message": err}
    from campaign_rpg_engine import emit_session_event

    emit_session_event(session, "session_loaded")
    return {"ok": True, "message": f"Enabled plugin {plugin_id!r}."}


def disable_plugin(session, plugin_id: str) -> dict[str, Any]:
    state = get_studio_plugin_state(session)
    state["enabled"] = [pid for pid in state["enabled"] if pid != plugin_id]
    unbind_enabled_plugin(session, plugin_id)
    return {"ok": True, "message": f"Disabled plugin {plugin_id!r}."}


def run_panel_action(session, plugin_id: str, action_id: str, params: dict) -> dict[str, Any]:
    manifest = _REGISTRY.get(plugin_id)
    if manifest is None:
        return {"ok": False, "message": f"Unknown plugin {plugin_id!r}."}
    if not is_plugin_enabled(session, plugin_id):
        return {"ok": False, "message": f"Plugin {plugin_id!r} is not enabled."}
    handler = manifest.panel_actions.get(action_id)
    if handler is None:
        return {"ok": False, "message": f"Unknown panel action {action_id!r}."}
    try:
        result = handler(session, params)
    except Exception as exc:
        return {"ok": False, "message": str(exc)}
    if not isinstance(result, dict):
        return {"ok": True, "message": "Action completed."}
    return result


def get_plugin_panel(session, plugin_id: str) -> dict[str, Any]:
    manifest = _REGISTRY.get(plugin_id)
    if manifest is None:
        return {"ok": False, "message": f"Unknown plugin {plugin_id!r}."}
    if manifest.panel_builder is not None:
        try:
            panel = dict(manifest.panel_builder(session))
        except Exception as exc:
            return {"ok": False, "message": str(exc)}
    else:
        panel = dict(manifest.panel)
    return {
        "ok": True,
        "panel": panel,
        "enabled": is_plugin_enabled(session, plugin_id),
    }


def list_plugins_catalog(session) -> dict[str, Any]:
    state = get_studio_plugin_state(session)
    plugins = [
        manifest.to_catalog_dict(enabled=manifest.plugin_id in state["enabled"])
        for manifest in list_installed_plugins()
    ]
    return {"ok": True, "plugins": plugins}
