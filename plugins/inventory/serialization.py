"""Serialize/deserialize inventory item payloads."""

from __future__ import annotations

from typing import Any

from campaign_rpg_engine import ObjectAction


def serialize_action(action: ObjectAction) -> dict[str, Any]:
    return {
        "name": action.name,
        "range": action.range,
        "result": action.result,
        "passive_result": action.passive_result,
        "handler_id": action.handler_id,
        "handler_params": dict(action.handler_params),
        "kind": action.kind,
        "halt_movement": action.halt_movement,
        "delete_after_trigger": action.delete_after_trigger,
        "trigger_exceptions": list(action.trigger_exceptions),
    }


def deserialize_action(data: dict[str, Any]) -> ObjectAction:
    return ObjectAction(
        name=str(data.get("name", "")),
        range=int(data.get("range", 1)),
        result=str(data.get("result", "")),
        passive_result=str(data.get("passive_result", "")),
        handler_id=data.get("handler_id"),
        handler_params={
            str(k): str(v) for k, v in dict(data.get("handler_params", {})).items()
        },
        kind=data.get("kind", "interact"),
        halt_movement=bool(data.get("halt_movement", False)),
        delete_after_trigger=bool(data.get("delete_after_trigger", True)),
        trigger_exceptions=[
            str(x) for x in list(data.get("trigger_exceptions", []))
        ],
    )


def deserialize_actions(raw: Any) -> dict[str, ObjectAction]:
    if not isinstance(raw, dict):
        return {}
    actions: dict[str, ObjectAction] = {}
    for name, payload in raw.items():
        if isinstance(payload, dict):
            actions[str(name)] = deserialize_action(payload)
    return actions


def serialize_object(obj) -> dict[str, Any]:
    return {
        "item_id": obj.id,
        "name": obj.name,
        "description": obj.description,
        "passive_description": obj.passive_description,
        "appearance": obj.appearance,
        "width": obj.width,
        "height": obj.height,
        "blocks_movement": obj.blocks_movement,
        "movement_exceptions": list(obj.movement_exceptions),
        "hidden": obj.hidden,
        "private_data": obj.private_data,
        "actions": {
            name: serialize_action(action) for name, action in obj.actions.items()
        },
    }
