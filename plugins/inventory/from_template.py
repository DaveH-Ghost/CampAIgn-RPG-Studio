"""Build inventory item payloads from object templates (inventory plugin)."""

from __future__ import annotations

import sys
from typing import Any

from campaign_rpg_engine import Object
from campaign_rpg_engine.area_edit import generate_object_id
from campaign_rpg_engine.session_persistence import deserialize_object_action
from campaign_rpg_engine.world_edit_api import collect_object_ids_in_session

state = sys.modules["studio_plugin_inventory.state"]
serialization = sys.modules["studio_plugin_inventory.serialization"]


def _all_reserved_item_ids(session) -> frozenset[str]:
    ids = set(collect_object_ids_in_session(session))
    ext = state.ensure_inventory_state(session)
    for items in (ext.get("by_agent") or {}).values():
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict) and item.get("item_id"):
                ids.add(str(item["item_id"]))
    return frozenset(ids)


def _actions_from_template(template: dict[str, Any]) -> dict[str, Any]:
    actions = {}
    for name, detail in (template.get("actions_detail") or {}).items():
        if not isinstance(detail, dict):
            continue
        action = deserialize_object_action(str(name), detail)
        actions[str(name)] = action
    return actions


def item_from_object_template(session, agent, template: dict[str, Any]) -> dict[str, Any]:
    """Create a serialized inventory item from an object template (never places on map)."""
    if template.get("kind") != "object":
        raise ValueError("Template kind must be 'object'.")

    area = session.get_area_for_agent(agent)
    if area is None:
        raise ValueError("Agent is not in an area.")

    name = str(template.get("name") or "Item")
    actions = _actions_from_template(template)
    obj = Object(
        id=generate_object_id(
            area,
            name,
            reserved_ids=_all_reserved_item_ids(session),
        ),
        name=name,
        description=str(template.get("description", "")),
        passive_description=str(template.get("passive_description", "")),
        position=agent.position,
        appearance=str(template.get("appearance", "")),
        width=int(template.get("width", 1)),
        height=int(template.get("height", 1)),
        blocks_movement=bool(template.get("blocks_movement", True)),
        movement_exceptions=[str(x) for x in list(template.get("movement_exceptions", []))],
        hidden=bool(template.get("hidden", False)),
        private_data=str(template.get("private_data", "")),
        actions=actions,
    )
    return serialization.serialize_object(obj)
