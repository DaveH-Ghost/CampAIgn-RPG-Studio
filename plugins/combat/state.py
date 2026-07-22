"""Combat plugin enablement and extension state."""

from __future__ import annotations

from typing import Any

PLUGIN_ID = "combat"
_STUDIO_PLUGINS_KEY = "_studio_plugins"
PRIVATE_KEY = "combat_plugin"
DEFAULT_HP = 10


def plugin_enabled(session) -> bool:
    raw = session.extensions.get(_STUDIO_PLUGINS_KEY) or {}
    enabled = raw.get("enabled") or []
    return PLUGIN_ID in enabled


def ensure_combat_state(session) -> dict[str, Any]:
    ext = session.get_extension(PLUGIN_ID)
    if not isinstance(ext, dict):
        ext = {"active": False, "by_agent": {}}
        session.set_extension(PLUGIN_ID, ext)
    if "active" not in ext:
        ext["active"] = False
    by_agent = ext.get("by_agent")
    if not isinstance(by_agent, dict):
        by_agent = {}
        ext["by_agent"] = by_agent
    return ext


def combat_active(session) -> bool:
    return bool(ensure_combat_state(session).get("active"))


def set_combat_active(session, active: bool) -> None:
    ext = ensure_combat_state(session)
    ext["active"] = bool(active)


def agent_combat_row(session, agent_id: str) -> dict[str, Any]:
    ext = ensure_combat_state(session)
    by_agent = ext["by_agent"]
    row = by_agent.get(agent_id)
    if not isinstance(row, dict):
        row = {"equipped_weapon": None, "equipped_armor": None}
        by_agent[agent_id] = row
    if "equipped_weapon" not in row:
        row["equipped_weapon"] = None
    if "equipped_armor" not in row:
        row["equipped_armor"] = None
    return row


def get_equipped_weapon_id(session, agent_id: str) -> str | None:
    raw = agent_combat_row(session, agent_id).get("equipped_weapon")
    return str(raw).strip() if raw else None


def get_equipped_armor_id(session, agent_id: str) -> str | None:
    raw = agent_combat_row(session, agent_id).get("equipped_armor")
    return str(raw).strip() if raw else None


def set_equipped_weapon(session, agent_id: str, item_id: str | None) -> None:
    agent_combat_row(session, agent_id)["equipped_weapon"] = item_id


def set_equipped_armor(session, agent_id: str, item_id: str | None) -> None:
    agent_combat_row(session, agent_id)["equipped_armor"] = item_id


def is_item_equipped(session, agent_id: str, item_id: str) -> bool:
    item_id = str(item_id).strip()
    if not item_id:
        return False
    row = agent_combat_row(session, agent_id)
    return row.get("equipped_weapon") == item_id or row.get("equipped_armor") == item_id
