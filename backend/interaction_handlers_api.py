"""Interaction handlers API for campaign-rpg-studio (V0.6.1)."""

from __future__ import annotations

from campaign_rpg_engine import Session, handler_catalog_entry, list_registered_handlers

from backend.plugin_registry import is_handler_visible_in_catalog


def get_interaction_handlers_catalog(session: Session) -> dict[str, object]:
    handlers = []
    for handler_id in list_registered_handlers():
        if not is_handler_visible_in_catalog(session, handler_id):
            continue
        entry = handler_catalog_entry(handler_id)
        if entry is None:
            continue
        handlers.append(entry)
    return {"handlers": handlers}
