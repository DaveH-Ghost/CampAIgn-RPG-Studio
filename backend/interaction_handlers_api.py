"""Interaction handlers API for campaign-rpg-studio (V0.6.1)."""

from __future__ import annotations

from campaign_rpg_engine import get_handler_registration, list_registered_handlers


def get_interaction_handlers_catalog() -> dict[str, object]:
    handlers = []
    for handler_id in list_registered_handlers():
        reg = get_handler_registration(handler_id)
        handlers.append(
            {
                "id": handler_id,
                "description": reg.description if reg else "",
            }
        )
    return {"handlers": handlers}
