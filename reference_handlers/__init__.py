"""Reference interaction handlers for CLI, tests, and campaign-rpg-studio (V0.6.1).

Apps copy this pattern; they do not import behavior from campaign-rpg-studio.

Handler implementations live under ``handlers/`` (one module per handler).
"""

from __future__ import annotations

from campaign_rpg_engine import register_interaction_handler

from .handlers.delete_self import delete_self
from .handlers.move_area import move_area, validate_move_area_params
from .handlers.random_move_self import random_move_self

__all__ = [
    "delete_self",
    "move_area",
    "random_move_self",
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
