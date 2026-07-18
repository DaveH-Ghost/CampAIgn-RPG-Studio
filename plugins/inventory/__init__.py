"""Inventory plugin — pick up objects into per-agent storage and drop them back."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

from campaign_rpg_engine.action_outcome import ActionOutcome
from campaign_rpg_engine.llm.schemas import AgentCompoundTurn

_PLUGIN_DIR = Path(__file__).resolve().parent


def _import_plugin_module(relative_name: str):
    qualified = f"studio_plugin_inventory.{relative_name}"
    if qualified in sys.modules:
        return sys.modules[qualified]
    path = _PLUGIN_DIR / f"{relative_name}.py"
    spec = importlib.util.spec_from_file_location(qualified, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load inventory plugin module {relative_name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[qualified] = module
    spec.loader.exec_module(module)
    return module


state = _import_plugin_module("state")
serialization = _import_plugin_module("serialization")
handlers = _import_plugin_module("handlers")
interact = _import_plugin_module("interact")
social = _import_plugin_module("social")
from_template = _import_plugin_module("from_template")

PLUGIN_ID = state.PLUGIN_ID
PLUGIN_LABEL = "Inventory"
PLUGIN_VERSION = "2"
PLUGIN_DESCRIPTION = (
    "Carry objects off the map. Add pick_up with handler inventory_pick_up; "
    "inventory_add_from_template grants a library object template into inventory; "
    "inventory-only actions (e.g. drink with inventory_consume) work from inventory "
    "via turn verb matching the action name. Drop, give, and show via turn verbs."
)

_HANDLER_ID = "inventory_pick_up"
_HANDLER_ADD_FROM_TEMPLATE = "inventory_add_from_template"

_ADD_FROM_TEMPLATE_PARAM_FIELDS = [
    {
        "name": "template_id",
        "label": "Object template",
        "type": "template_id",
        "required": True,
        "kind": "object",
    },
]
_DROP_VERB = "drop"
_GIVE_VERB = "give"
_SHOW_VERB = "show"


def _drop_positions(agent, area):
    ax, ay = agent.position
    yield (ax, ay)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            pos = (ax + dx, ay + dy)
            if area.is_valid_position(pos):
                yield pos


def _format_inventory_prompt(session, agent_id: str) -> str:
    items = state.agent_items(session, agent_id)
    if not items:
        return "Items in your Inventory:\n(none)"

    lines = ["Items in your Inventory:"]
    for item in items:
        name = item.get("name") or item.get("item_id")
        item_id = item.get("item_id", "")
        verb_tags = " ".join(
            f"[{verb}]"
            for verb in interact.inventory_verbs_for_item(
                item,
                drop_verb=_DROP_VERB,
                social_verbs=(_GIVE_VERB, _SHOW_VERB),
            )
        )
        lines.append(f"- {name} ({item_id}) {verb_tags}")

    lines.extend(
        [
            "",
            'To use a carried item, use "action": "verb", "target": "<item_id>", '
            '"verb": "<action name>" (same name as the bracketed tag, e.g. drink).',
            f'To drop: "verb": "{_DROP_VERB}", target = item id only.',
            f'To give or show to another agent within range {social.SOCIAL_RANGE}: "verb": "{_GIVE_VERB}" or '
            f'"{_SHOW_VERB}", target = "<agent_id> <item_id>" (recipient first).',
            "Example give: "
            f'"action": "verb", "verb": "{_GIVE_VERB}", '
            '"target": "agent_shopkeeper_01 obj_mug_01"',
            "Use agent ids from passive vision and item ids from this list.",
            "Do not use action interact for give/show.",
        ]
    )
    return "\n".join(lines)


def _drop_item(session, agent, item_id: str) -> dict[str, Any]:
    if not state.plugin_enabled(session):
        return {"ok": False, "message": "Inventory plugin is not enabled."}
    item_id = (item_id or "").strip()
    if not item_id:
        return {"ok": False, "message": "Missing item id."}

    items, index = state.find_item(session, agent.id, item_id)
    if index is None:
        return {"ok": False, "message": f"You are not carrying {item_id!r}."}

    item = items[index]
    area = session.get_area_for_agent(agent)
    if area is None:
        return {"ok": False, "message": "Agent is not in an area."}

    actions = serialization.deserialize_actions(item.get("actions"))
    created = None
    message = ""
    for position in _drop_positions(agent, area):
        result = session.create_object(
            name=str(item.get("name", "Item")),
            position=position,
            description=str(item.get("description", "")),
            passive_description=str(item.get("passive_description", "")),
            appearance=str(item.get("appearance", "")),
            width=int(item.get("width", 1)),
            height=int(item.get("height", 1)),
            blocks_movement=bool(item.get("blocks_movement", True)),
            movement_exceptions=[
                str(x) for x in list(item.get("movement_exceptions", []))
            ],
            hidden=bool(item.get("hidden", False)),
            actions=actions or None,
            object_id=item_id,
        )
        if result.ok and result.object is not None:
            created = result.object
            message = result.message
            break
        message = result.message

    if created is None:
        return {"ok": False, "message": message or "Could not drop item here."}

    if item.get("private_data"):
        created.private_data = str(item["private_data"])

    remaining = items[:index] + items[index + 1 :]
    state.set_agent_items(session, agent.id, remaining)
    return {
        "ok": True,
        "message": f"Dropped {created.name} ({created.id}).",
        "object_id": created.id,
    }


def _validate_drop(turn: AgentCompoundTurn) -> str | None:
    if not (turn.target or "").strip():
        return "ERR:INVALID_TARGET: drop requires target item id"
    return None


def _drop_turn_verb(session, agent, area, turn):
    del area
    result = _drop_item(session, agent, (turn.target or "").strip())
    if not result.get("ok"):
        return result.get("message", "Could not drop item.")
    name = str(result.get("message", "You drop an item."))
    return ActionOutcome(
        result=name,
        passive_result=f"{agent.name} drops something.",
    )


def _inventory_prompt_slot(session, agent, area, ctx_prompt, options):
    del area, ctx_prompt, options
    if not state.plugin_enabled(session):
        return ""
    return _format_inventory_prompt(session, agent.id)


def _build_panel(session):
    agent = session.get_active_agent()
    items = state.agent_items(session, agent.id)
    sections: list[dict[str, Any]] = [
        {
            "type": "text",
            "content": (
                f"Carried by {agent.name}: {len(items)} item"
                f"{'' if len(items) == 1 else 's'}."
            ),
        },
    ]
    if not items:
        sections.append(
            {
                "type": "text",
                "content": (
                    "No items yet. On an object, add action pick_up with handler "
                    f"{_HANDLER_ID!r}, then interact in range."
                ),
            }
        )
    else:
        for item in items:
            label = item.get("name") or item.get("item_id")
            item_id = item.get("item_id", "")
            sections.append(
                {
                    "type": "key_value_list",
                    "items": [{"key": str(label), "value": str(item_id)}],
                }
            )
            for verb in interact.inventory_verbs_for_item(item, drop_verb=_DROP_VERB):
                if verb == _DROP_VERB:
                    sections.append(
                        {
                            "type": "button",
                            "id": "drop_item",
                            "label": f"Drop {label}",
                            "params": {"item_id": item_id},
                        }
                    )
                else:
                    sections.append(
                        {
                            "type": "button",
                            "id": "use_item",
                            "label": f"{verb.title()} {label}",
                            "params": {"item_id": item_id, "action": verb},
                        }
                    )
    sections.append(
        {
            "type": "text",
            "content": (
                f'Inventory turns: action "verb", target = item id, verb = action name '
                f'or "{_DROP_VERB}". Give/show: target = "<agent_id> <item_id>" (range {social.SOCIAL_RANGE}).'
            ),
        }
    )
    return {
        "title": "Inventory",
        "description": PLUGIN_DESCRIPTION,
        "sections": sections,
    }


def _drop_item_action(session, params):
    agent = session.get_active_agent()
    item_id = str(params.get("item_id", "")).strip()
    return _drop_item(session, agent, item_id)


def _use_item_action(session, params):
    agent = session.get_active_agent()
    item_id = str(params.get("item_id", "")).strip()
    action_name = str(params.get("action", "")).strip()
    area = session.get_area_for_agent(agent)
    if area is None:
        return {"ok": False, "message": "Agent is not in an area."}
    outcome = interact.use_inventory_item(session, agent, area, item_id, action_name)
    if isinstance(outcome, str):
        return {"ok": False, "message": outcome}
    return {"ok": True, "message": outcome.result or "Done."}


def _give_turn_verb(session, agent, area, turn):
    del area
    outcome = social.give_carried_item(session, agent, turn.target or "")
    if isinstance(outcome, str):
        return outcome
    return outcome


def _show_turn_verb(session, agent, area, turn):
    del area
    outcome = social.show_carried_item(session, agent, turn.target or "")
    if isinstance(outcome, str):
        return outcome
    return outcome


def register(ctx):
    interact.apply_perception_patch()
    interact._REGISTERED_INVENTORY_VERBS.clear()

    def on_session_loaded(session, **payload):
        del payload
        if state.plugin_enabled(session):
            state.ensure_inventory_state(session)
            interact.register_all_carried_action_verbs(ctx, session)

    ctx.on("session_loaded", on_session_loaded)

    def inventory_pick_up(session, area, agent, obj, action) -> str | None:
        del area, action
        if session is None:
            return "Inventory pick up requires a session."
        if not state.plugin_enabled(session):
            return "Inventory plugin is not enabled."
        items = state.agent_items(session, agent.id)
        if any(item.get("item_id") == obj.id for item in items):
            return f"You are already carrying {obj.name}."
        item = serialization.serialize_object(obj)
        items.append(item)
        state.set_agent_items(session, agent.id, items)
        delete_result = session.delete_object(obj.id)
        if not delete_result.ok:
            items.pop()
            state.set_agent_items(session, agent.id, items)
            return delete_result.message
        interact.register_item_action_verbs(ctx, item)
        return None

    def validate_add_from_template_params(params: dict[str, str]) -> str | None:
        template_id = (params.get("template_id") or "").strip()
        if not template_id:
            return "inventory_add_from_template requires template_id."
        return None

    def inventory_add_from_template(session, area, agent, obj, action) -> str | None:
        del area, obj
        if session is None:
            return "inventory_add_from_template requires a session."
        if not state.plugin_enabled(session):
            return "Inventory plugin is not enabled."
        template_id = (action.handler_params.get("template_id") or "").strip()
        from backend.entity_templates_api import get_entity_template

        loaded = get_entity_template(template_id)
        if not loaded.get("ok"):
            return str(loaded.get("message") or f"Template {template_id!r} not found.")
        template = loaded["template"]
        if not isinstance(template, dict):
            return f"Template {template_id!r} is invalid."
        try:
            item = from_template.item_from_object_template(session, agent, template)
        except ValueError as exc:
            return str(exc)
        items = state.agent_items(session, agent.id)
        items.append(item)
        state.set_agent_items(session, agent.id, items)
        interact.register_item_action_verbs(ctx, item)
        return None

    ctx.register_handler(
        _HANDLER_ID,
        inventory_pick_up,
        description="Pick up object into agent inventory (inventory plugin)",
    )
    ctx.register_handler(
        _HANDLER_ADD_FROM_TEMPLATE,
        inventory_add_from_template,
        description="Add an object template into agent inventory (inventory plugin)",
        validate_params=validate_add_from_template_params,
        param_fields=_ADD_FROM_TEMPLATE_PARAM_FIELDS,
        summary_template="inventory_add_from_template {template_id}",
    )
    ctx.register_handler(
        handlers._HANDLER_CONSUME,
        handlers.inventory_consume,
        description="Consume a carried item (inventory plugin; not usable on the map)",
    )

    ctx.register_turn_verb(
        _DROP_VERB,
        _drop_turn_verb,
        description="Drop a carried item (target = inventory item id)",
        validate_turn=_validate_drop,
    )
    ctx.register_turn_verb(
        _GIVE_VERB,
        _give_turn_verb,
        description="Give a carried item to another agent (target = agent_id item_id)",
        validate_turn=social.validate_agent_item_turn_target,
        path_range=social.SOCIAL_RANGE,
        path_target_from_turn=social.path_target_agent_from_turn,
    )
    ctx.register_turn_verb(
        _SHOW_VERB,
        _show_turn_verb,
        description="Show a carried item to another agent (target = agent_id item_id)",
        validate_turn=social.validate_agent_item_turn_target,
        path_range=social.SOCIAL_RANGE,
        path_target_from_turn=social.path_target_agent_from_turn,
    )

    ctx.register_prompt_slot(
        "inventory",
        _inventory_prompt_slot,
        description="Lists carried items and inventory verbs",
    )

    def _player_turn_assist(session):
        if not state.plugin_enabled(session):
            return []
        agent_id = getattr(session, "active_agent_id", None)
        if not agent_id:
            return []
        rows: list[dict[str, Any]] = []
        for item in state.agent_items(session, agent_id):
            item_id = str(item.get("item_id", "")).strip()
            if not item_id:
                continue
            rows.append(
                {
                    "id": item_id,
                    "label": str(item.get("name") or item_id),
                    "verbs": interact.inventory_verbs_for_item(
                        item,
                        drop_verb=_DROP_VERB,
                    ),
                }
            )
        return rows

    ctx.register_player_turn_assist(_player_turn_assist)
    ctx.set_panel_builder(_build_panel)
    ctx.register_panel_action("drop_item", _drop_item_action)
    ctx.register_panel_action("use_item", _use_item_action)
