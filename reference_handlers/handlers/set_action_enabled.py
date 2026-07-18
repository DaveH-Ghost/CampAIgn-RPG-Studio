"""set_action_enabled reference handler — show/hide an action on the current object."""

from __future__ import annotations

from campaign_rpg_engine.area_edit import parse_bool_field


def validate_set_action_enabled_params(params: dict[str, str]) -> str | None:
    target = (params.get("target") or "").strip()
    if not target:
        return "set_action_enabled requires target <action_name|_self>."
    if "enabled" not in params:
        return "set_action_enabled requires enabled true|false."
    _, err = parse_bool_field(params["enabled"], field_name="enabled")
    return err


def set_action_enabled(session, area, agent, obj, action) -> str | None:
    del session, area, agent
    params = action.handler_params
    target = (params.get("target") or "").strip()
    if target == "_self":
        target = action.name
    enabled, err = parse_bool_field(params.get("enabled", ""), field_name="enabled")
    if err:
        return err
    assert enabled is not None
    target_action = obj.actions.get(target)
    if target_action is None:
        return f"No action '{target}' on {obj.name}."
    target_action.enabled = enabled
    return None
