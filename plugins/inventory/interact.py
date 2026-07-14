"""Run object actions on carried items and hide inventory-only actions on the grid."""

from __future__ import annotations

from typing import Any

from campaign_rpg_engine import Object, ObjectAction, run_interaction_handler
from campaign_rpg_engine.action_outcome import ActionOutcome
from campaign_rpg_engine.interact_templates import InteractTemplateContext, format_interact_template

import sys

state = sys.modules["studio_plugin_inventory.state"]
serialization = sys.modules["studio_plugin_inventory.serialization"]
handlers_mod = sys.modules["studio_plugin_inventory.handlers"]

_HANDLER_CONSUME = handlers_mod._HANDLER_CONSUME
deserialize_actions = serialization.deserialize_actions

_HANDLER_PICK_UP = "inventory_pick_up"
_REGISTERED_INVENTORY_VERBS: set[str] = set()
_PERCEPTION_PATCHED = False


def is_grid_only_handler(handler_id: str | None) -> bool:
    return handler_id == _HANDLER_PICK_UP


def is_inventory_only_handler(handler_id: str | None) -> bool:
    if not handler_id or is_grid_only_handler(handler_id):
        return False
    return handler_id.startswith("inventory_")


def item_as_object(item: dict[str, Any], agent) -> Object:
    return Object(
        id=str(item.get("item_id", "")),
        name=str(item.get("name", "Item")),
        description=str(item.get("description", "")),
        passive_description=str(item.get("passive_description", "")),
        position=agent.position,
        appearance=str(item.get("appearance", "")),
        width=int(item.get("width", 1)),
        height=int(item.get("height", 1)),
        blocks_movement=bool(item.get("blocks_movement", True)),
        movement_exceptions=[
            str(x) for x in list(item.get("movement_exceptions", []))
        ],
        hidden=bool(item.get("hidden", False)),
        private_data=str(item.get("private_data", "")),
        actions=deserialize_actions(item.get("actions")),
    )


def is_inventory_item_action(payload: dict[str, Any]) -> bool:
    if payload.get("kind", "interact") != "interact":
        return False
    if is_grid_only_handler(payload.get("handler_id")):
        return False
    return is_inventory_only_handler(payload.get("handler_id"))


def inventory_verbs_for_item(
    item: dict[str, Any],
    *,
    drop_verb: str,
    social_verbs: tuple[str, ...] = (),
) -> list[str]:
    verbs = [drop_verb, *social_verbs]
    for name, payload in sorted(item.get("actions", {}).items()):
        if name == "pick_up" or not isinstance(payload, dict):
            continue
        if is_inventory_item_action(payload):
            verbs.append(str(name))
    return verbs


def _resolve_agent_area(session, agent_id: str) -> str:
    if session is None:
        return ""
    return session.agent_area.get(agent_id) or ""


def _handler_consumes_item(action: ObjectAction) -> bool:
    if action.handler_id == _HANDLER_CONSUME:
        return False
    return action.handler_id == "delete_self"


def use_inventory_item(
    session, agent, area, item_id: str, action_name: str
) -> ActionOutcome | str:
    if not state.plugin_enabled(session):
        return "Inventory plugin is not enabled."

    item_id = (item_id or "").strip()
    action_name = (action_name or "").strip()
    if not item_id:
        return "Missing item id."
    if not action_name:
        return "Missing action name."

    items, index = state.find_item(session, agent.id, item_id)
    if index is None:
        return f"You are not carrying {item_id!r}."

    item = items[index]
    actions = deserialize_actions(item.get("actions"))
    action = actions.get(action_name)
    if action is None:
        return f"'{action_name}' is not an action on that item."
    if action.kind != "interact":
        return f"'{action_name}' cannot be used from inventory."
    if is_grid_only_handler(action.handler_id):
        return f"'{action_name}' is only available on the map."

    obj = item_as_object(item, agent)
    area_id = _resolve_agent_area(session, agent.id)
    actor_start = agent.position

    if action.handler_id:
        handler_result = run_interaction_handler(session, area, agent, obj, action)
        if isinstance(handler_result, ActionOutcome):
            if _handler_consumes_item(action):
                remaining = items[:index] + items[index + 1 :]
                state.set_agent_items(session, agent.id, remaining)
            return handler_result
        if handler_result:
            return ActionOutcome(result=handler_result)

    if _handler_consumes_item(action):
        remaining = items[:index] + items[index + 1 :]
        state.set_agent_items(session, agent.id, remaining)

    template_ctx = InteractTemplateContext(
        actor=agent.name,
        object_name=obj.name,
        object_start=actor_start,
        object_end=actor_start,
        actor_start=actor_start,
        actor_end=agent.position,
        object_start_area=area_id,
        object_end_area=area_id,
        actor_start_area=area_id,
        actor_end_area=area_id,
    )
    return ActionOutcome(
        result=format_interact_template(action.result, template_ctx),
        passive_result=format_interact_template(action.passive_result, template_ctx),
    )


def register_item_action_verbs(ctx, item: dict[str, Any]) -> None:
    for name, payload in item.get("actions", {}).items():
        if name == "pick_up" or not isinstance(payload, dict):
            continue
        if is_inventory_item_action(payload):
            ensure_inventory_action_turn_verb(ctx, str(name))


def register_all_carried_action_verbs(ctx, session) -> None:
    for agent_id in state.ensure_inventory_state(session).get("by_agent", {}):
        for item in state.agent_items(session, str(agent_id)):
            register_item_action_verbs(ctx, item)


def ensure_inventory_action_turn_verb(ctx, action_name: str) -> None:
    if action_name in _REGISTERED_INVENTORY_VERBS:
        return
    _REGISTERED_INVENTORY_VERBS.add(action_name)

    def validate_turn(turn):
        if not (turn.target or "").strip():
            return f"ERR:INVALID_TARGET: {action_name} requires target item id"
        return None

    def executor(session, agent, area, turn):
        outcome = use_inventory_item(
            session,
            agent,
            area,
            (turn.target or "").strip(),
            action_name,
        )
        if isinstance(outcome, str):
            return outcome
        return outcome

    ctx.register_turn_verb(
        action_name,
        executor,
        description=f"Use carried item action {action_name!r} (inventory plugin)",
        validate_turn=validate_turn,
    )


def apply_perception_patch() -> None:
    """Hide inventory-only handlers from passive-vision interaction lists."""
    global _PERCEPTION_PATCHED
    if _PERCEPTION_PATCHED:
        return

    import campaign_rpg_engine.perception as perception

    original_get = perception.get_object_interactions_reachable_after_move
    original_available = perception.get_available_interactions

    def filtered_get(agent, area, obj):
        interactions = original_get(agent, area, obj)
        return [
            (name, action)
            for name, action in interactions
            if not is_inventory_only_handler(action.handler_id)
        ]

    def filtered_available(agent, area):
        interactions = original_available(agent, area)
        return [
            entry
            for entry in interactions
            if not is_inventory_only_handler(entry[3].handler_id)
        ]

    perception.get_object_interactions_reachable_after_move = filtered_get
    perception.get_available_interactions = filtered_available
    _PERCEPTION_PATCHED = True
