"""Inventory extension state helpers."""

from __future__ import annotations

import sys
from typing import Any

PLUGIN_ID = "inventory"
_STUDIO_PLUGINS_KEY = "_studio_plugins"


def plugin_enabled(session) -> bool:
    raw = session.extensions.get(_STUDIO_PLUGINS_KEY) or {}
    enabled = raw.get("enabled") or []
    return PLUGIN_ID in enabled


def ensure_inventory_state(session) -> dict[str, Any]:
    ext = session.get_extension(PLUGIN_ID)
    if not isinstance(ext, dict):
        ext = {"by_agent": {}}
        session.set_extension(PLUGIN_ID, ext)
    by_agent = ext.get("by_agent")
    if not isinstance(by_agent, dict):
        by_agent = {}
        ext["by_agent"] = by_agent
    return ext


def agent_items(session, agent_id: str) -> list[dict[str, Any]]:
    ext = ensure_inventory_state(session)
    by_agent = ext.get("by_agent", {})
    items = by_agent.get(agent_id, [])
    return list(items) if isinstance(items, list) else []


def set_agent_items(session, agent_id: str, items: list[dict[str, Any]]) -> None:
    ext = ensure_inventory_state(session)
    ext["by_agent"][agent_id] = items
    # Drop / give / consume may remove an equipped item — clear combat slots eagerly.
    combat_equip = sys.modules.get("studio_plugin_combat.equip")
    if combat_equip is not None:
        combat_equip.clear_stale_equipment(session, agent_id)


def find_item(session, agent_id: str, item_id: str) -> tuple[list[dict[str, Any]], int | None]:
    items = agent_items(session, agent_id)
    for index, item in enumerate(items):
        if item.get("item_id") == item_id:
            return items, index
    return items, None
