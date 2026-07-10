"""move_area reference handler."""

from __future__ import annotations

from realm_fabric import parse_position


def validate_move_area_params(params: dict[str, str]) -> str | None:
    dest_area = params.get("dest-area", "").strip()
    dest_at = params.get("dest-at", "").strip()
    if not dest_area:
        return "move_area handler requires dest-area <area_id>."
    if not dest_at:
        return "move_area handler requires dest-at x,y."
    _, err = parse_position(dest_at)
    return err


def move_area(session, area, agent, obj, action) -> str | None:
    del area, obj
    if session is None:
        return "move_area requires a multi-area session."
    dest_area_id = action.handler_params.get("dest-area", "").strip()
    dest_at = action.handler_params.get("dest-at", "").strip()
    if not dest_area_id or not dest_at:
        return "move_area handler is missing dest-area or dest-at."

    position, err = parse_position(dest_at)
    if err:
        return err
    assert position is not None

    result = session.transfer_agent(agent.id, dest_area_id, position)
    if not result.ok:
        return result.message
    return None
