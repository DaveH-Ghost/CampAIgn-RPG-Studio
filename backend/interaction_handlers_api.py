"""Interaction handlers API for campaign-rpg-studio (V0.6.1)."""

from __future__ import annotations

from campaign_rpg_engine import Session, get_handler_registration, list_registered_handlers

from backend.plugin_registry import is_handler_visible_in_catalog


def get_interaction_handlers_catalog(session: Session) -> dict[str, object]:
    handlers = []
    for handler_id in list_registered_handlers():
        if not is_handler_visible_in_catalog(session, handler_id):
            continue
        reg = get_handler_registration(handler_id)
        handlers.append(
            {
                "id": handler_id,
                "description": reg.description if reg else "",
            }
        )
    return {"handlers": handlers}
