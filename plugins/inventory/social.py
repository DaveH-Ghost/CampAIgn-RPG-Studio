"""Agent-to-agent inventory actions (give, show)."""

from __future__ import annotations

from typing import Any

from campaign_rpg_engine.action_outcome import ActionOutcome
from campaign_rpg_engine.grid import chebyshev_distance

import sys

state = sys.modules["studio_plugin_inventory.state"]

SOCIAL_RANGE = 1


def parse_agent_item_target(raw: str) -> tuple[str, str] | str:
    """
    Parse composite turn target for give/show.

    Format: ``"<agent_id> <item_id>"`` (recipient first, inventory item second).
    """
    cleaned = (raw or "").strip()
    if not cleaned:
        return (
            "ERR:INVALID_TARGET: give/show require target "
            "'<agent_id> <item_id>'"
        )
    parts = cleaned.split()
    if len(parts) != 2:
        return (
            "ERR:INVALID_TARGET: give/show target must be two ids separated "
            "by a space: '<agent_id> <item_id>'"
        )
    agent_id, item_id = parts[0], parts[1]
    if not agent_id.startswith("agent_"):
        return (
            f"ERR:INVALID_TARGET: first token must be an agent id (agent_*), "
            f"got {agent_id!r}"
        )
    if not item_id.startswith("obj_"):
        return (
            f"ERR:INVALID_TARGET: second token must be an item id (obj_*), "
            f"got {item_id!r}"
        )
    return agent_id, item_id


def validate_agent_item_turn_target(turn) -> str | None:
    parsed = parse_agent_item_target(turn.target or "")
    if isinstance(parsed, str):
        return parsed
    return None


def path_target_agent_from_turn(turn) -> str | None:
    parsed = parse_agent_item_target(turn.target or "")
    if isinstance(parsed, str):
        return None
    return parsed[0]


def _agents_share_area(session, agent_a, agent_b) -> bool:
    area_a = session.get_area_for_agent(agent_a)
    area_b = session.get_area_for_agent(agent_b)
    return area_a is not None and area_a is area_b


def _resolve_agent_item_target(session, actor, raw_target: str) -> tuple[Any, dict[str, Any], int] | str:
    parsed = parse_agent_item_target(raw_target)
    if isinstance(parsed, str):
        return parsed
    recipient_id, item_id = parsed

    recipient = session.get_agent(recipient_id)
    if recipient is None:
        return f"Agent {recipient_id!r} not found."
    if recipient.id == actor.id:
        return "You cannot target yourself."
    if not _agents_share_area(session, actor, recipient):
        return f"{recipient.name} is not in your area."

    distance = chebyshev_distance(actor.position, recipient.position)
    if distance > SOCIAL_RANGE:
        return (
            f"{recipient.name} is too far away "
            f"(range {SOCIAL_RANGE}, distance {distance})."
        )

    items, index = state.find_item(session, actor.id, item_id)
    if index is None:
        return f"You are not carrying {item_id!r}."

    return recipient, items[index], index


def format_show_event_text(actor_name: str, item: dict[str, Any]) -> str:
    obj_name = str(item.get("name") or item.get("item_id") or "something")
    passive = str(item.get("passive_description", "")).strip()
    description = str(item.get("description", "")).strip()
    if passive:
        return f"{actor_name} shows you {obj_name}, it is {passive}"
    if description:
        return f"{actor_name} shows you {obj_name}, it is {description}"
    return f"{actor_name} shows you {obj_name}"


def give_carried_item(session, actor, raw_target: str) -> ActionOutcome | str:
    if not state.plugin_enabled(session):
        return "Inventory plugin is not enabled."

    resolved = _resolve_agent_item_target(session, actor, raw_target)
    if isinstance(resolved, str):
        return resolved
    recipient, item, index = resolved
    item_name = str(item.get("name") or item.get("item_id"))

    actor_items, _ = state.find_item(session, actor.id, str(item["item_id"]))
    transferred = dict(item)
    remaining = actor_items[:index] + actor_items[index + 1 :]
    state.set_agent_items(session, actor.id, remaining)

    recipient_items = state.agent_items(session, recipient.id)
    if any(existing.get("item_id") == transferred.get("item_id") for existing in recipient_items):
        state.set_agent_items(session, actor.id, actor_items)
        return f"{recipient.name} is already carrying {item_name}."

    recipient_items.append(transferred)
    state.set_agent_items(session, recipient.id, recipient_items)

    return ActionOutcome(
        result=f"You give {item_name} to {recipient.name}.",
        passive_result=f"{actor.name} gives {item_name} to {recipient.name}.",
    )


def show_carried_item(session, actor, raw_target: str) -> ActionOutcome | str:
    if not state.plugin_enabled(session):
        return "Inventory plugin is not enabled."

    resolved = _resolve_agent_item_target(session, actor, raw_target)
    if isinstance(resolved, str):
        return resolved
    recipient, item, _index = resolved
    item_name = str(item.get("name") or item.get("item_id"))

    event_text = format_show_event_text(actor.name, item)
    event_result = session.emit_area_event(event_text, agent_ids=[recipient.id])
    if not event_result.ok:
        return event_result.message

    return ActionOutcome(
        result=f"You show {item_name} to {recipient.name}.",
        passive_result=f"{actor.name} shows {item_name} to {recipient.name}.",
        passive_witness_exclude_agent_ids=(recipient.id,),
    )
