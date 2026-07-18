"""Reference interaction handlers for CLI, tests, and campaign-rpg-studio (V0.6.1).

Apps copy this pattern; they do not import behavior from campaign-rpg-studio.

Handler implementations live under ``handlers/`` (one module per handler).
"""

from __future__ import annotations

from campaign_rpg_engine import register_interaction_handler

from .handlers.delete_self import delete_self
from .handlers.move_area import move_area, validate_move_area_params
from .handlers.random_move_self import random_move_self
from .handlers.sequence import sequence, validate_sequence_params
from .handlers.set_action_enabled import (
    set_action_enabled,
    validate_set_action_enabled_params,
)
from .handlers.set_object_text import set_object_text, validate_set_object_text_params
from .handlers.spawn_from_template import (
    spawn_from_template,
    validate_spawn_from_template_params,
)

__all__ = [
    "delete_self",
    "move_area",
    "random_move_self",
    "sequence",
    "set_action_enabled",
    "set_object_text",
    "spawn_from_template",
    "register_reference_handlers",
]


MOVE_AREA_PARAM_FIELDS = [
    {
        "name": "dest-area",
        "label": "Destination area",
        "type": "area_id",
        "required": True,
    },
    {
        "name": "dest-at",
        "label": "Destination tile",
        "type": "coord",
        "required": True,
        "default": "0,0",
    },
]

SET_OBJECT_TEXT_PARAM_FIELDS = [
    {
        "name": "set_pdesc",
        "label": "New passive description",
        "type": "textarea",
        "placeholder": "Leave blank to keep; [none] or [empty] to clear",
    },
    {
        "name": "set_desc",
        "label": "New detailed description",
        "type": "textarea",
        "placeholder": "Leave blank to keep; [none] or [empty] to clear",
    },
]

SET_ACTION_ENABLED_PARAM_FIELDS = [
    {
        "name": "target",
        "label": "Action name (_self = this action)",
        "type": "text",
        "required": True,
        "default": "_self",
        "placeholder": "_self or another action name",
    },
    {
        "name": "enabled",
        "label": "Enabled",
        "type": "select",
        "required": True,
        "default": "false",
        "options": [
            {"value": "true", "label": "true (show)"},
            {"value": "false", "label": "false (hide)"},
        ],
    },
]

SEQUENCE_PARAM_FIELDS = [
    {
        "name": "handler_1",
        "label": "Handler 1",
        "type": "handler_ref",
        "required": True,
        "param_prefix": "1_",
        "exclude_handlers": ["sequence"],
        "summary_key": "1",
    },
    {
        "name": "handler_2",
        "label": "Handler 2",
        "type": "handler_ref",
        "param_prefix": "2_",
        "exclude_handlers": ["sequence"],
        "summary_key": "2",
    },
    {
        "name": "handler_3",
        "label": "Handler 3",
        "type": "handler_ref",
        "param_prefix": "3_",
        "exclude_handlers": ["sequence"],
        "summary_key": "3",
    },
]

SPAWN_FROM_TEMPLATE_PARAM_FIELDS = [
    {
        "name": "template_id",
        "label": "Object template",
        "type": "template_id",
        "required": True,
        "kind": "object",
    },
    {
        "name": "dest-area",
        "label": "Destination area (optional)",
        "type": "area_id",
        "optional": True,
        "empty_label": "(actor's area)",
    },
    {
        "name": "dest-at",
        "label": "Destination tile (optional)",
        "type": "text",
        "placeholder": "x,y — leave blank to spawn near the acting agent",
    },
]


def register_reference_handlers() -> None:
    """Register demo handlers idempotently (safe to call multiple times)."""
    register_interaction_handler(
        "delete_self",
        delete_self,
        description="Remove the interacted object from the area",
    )
    register_interaction_handler(
        "random_move_self",
        random_move_self,
        description="Move the interacted object to a different random in-bounds grid position",
    )
    register_interaction_handler(
        "move_area",
        move_area,
        description="Transfer the interacting agent to another area at dest-at (requires dest-area, dest-at)",
        validate_params=validate_move_area_params,
        param_fields=MOVE_AREA_PARAM_FIELDS,
        summary_template="move_area → {dest-area} ({dest-at})",
    )
    register_interaction_handler(
        "set_object_text",
        set_object_text,
        description="Update this object's passive and/or detailed description",
        validate_params=validate_set_object_text_params,
        param_fields=SET_OBJECT_TEXT_PARAM_FIELDS,
        summary_template="set_object_text",
    )
    register_interaction_handler(
        "set_action_enabled",
        set_action_enabled,
        description="Show or hide an action on this object (target=_self or action name)",
        validate_params=validate_set_action_enabled_params,
        param_fields=SET_ACTION_ENABLED_PARAM_FIELDS,
        summary_template="set_action_enabled {target}={enabled}",
    )
    register_interaction_handler(
        "sequence",
        sequence,
        description="Run handler_1, handler_2, … in order (nested params use 1_/2_/… prefixes)",
        validate_params=validate_sequence_params,
        param_fields=SEQUENCE_PARAM_FIELDS,
        summary_template="sequence",
    )
    register_interaction_handler(
        "spawn_from_template",
        spawn_from_template,
        description="Spawn an object template into the world (near agent, or dest-area/dest-at)",
        validate_params=validate_spawn_from_template_params,
        param_fields=SPAWN_FROM_TEMPLATE_PARAM_FIELDS,
        summary_template="spawn_from_template {template_id}",
    )
