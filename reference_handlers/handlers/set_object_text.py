"""set_object_text reference handler — update object pdesc and/or desc."""

from __future__ import annotations

_CLEAR_SENTINELS = frozenset({"none", "empty"})


def _resolve_set_text(raw: str) -> str:
    """Map ``[none]`` / ``[empty]`` (any case) to empty string; otherwise use raw text."""
    stripped = raw.strip()
    if len(stripped) >= 2 and stripped[0] == "[" and stripped[-1] == "]":
        inner = stripped[1:-1].strip().lower()
        if inner in _CLEAR_SENTINELS:
            return ""
    return raw


def validate_set_object_text_params(params: dict[str, str]) -> str | None:
    set_pdesc = params.get("set_pdesc")
    set_desc = params.get("set_desc")
    if set_pdesc is None and set_desc is None:
        return "set_object_text requires set_pdesc and/or set_desc."
    return None


def set_object_text(session, area, agent, obj, action) -> str | None:
    del session, agent
    params = action.handler_params
    if "set_pdesc" in params:
        obj.passive_description = _resolve_set_text(params["set_pdesc"])
    if "set_desc" in params:
        obj.description = _resolve_set_text(params["set_desc"])
        area.invalidate_object_knowledge(obj.id)
    return None
