"""Inventory-specific interaction handlers."""

from __future__ import annotations

import sys

state = sys.modules["studio_plugin_inventory.state"]

_HANDLER_CONSUME = "inventory_consume"


def inventory_consume(session, area, agent, obj, action) -> str | None:
    """Remove a carried item (eat, drink, etc.). Fails if the object is still on the grid."""
    del area, action
    if session is None:
        return "inventory_consume requires a session."
    items, index = state.find_item(session, agent.id, obj.id)
    if index is None:
        return f"You must pick up {obj.name} before you can use it that way."
    remaining = items[:index] + items[index + 1 :]
    state.set_agent_items(session, agent.id, remaining)
    return None


__all__ = ["_HANDLER_CONSUME", "inventory_consume"]
