"""HTTP helpers for registered compound-turn verbs (1.2.0)."""

from __future__ import annotations

from campaign_rpg_engine import Session
from campaign_rpg_engine.turn_verbs.registry import (
    get_turn_verb_registration,
    list_registered_turn_verbs,
)

from backend.plugin_registry import is_turn_verb_visible_in_catalog


def get_turn_verbs_catalog(session: Session) -> dict[str, object]:
    verbs: list[dict[str, str]] = []
    for verb_id in list_registered_turn_verbs():
        if not is_turn_verb_visible_in_catalog(session, verb_id):
            continue
        reg = get_turn_verb_registration(verb_id)
        verbs.append(
            {
                "id": verb_id,
                "description": reg.description if reg else "",
            }
        )
    return {"ok": True, "verbs": verbs}
