"""delete_self reference handler."""

from __future__ import annotations


def delete_self(session, area, agent, obj, action) -> str | None:
    del session, agent, action
    area.remove_object(obj.id)
    return None
